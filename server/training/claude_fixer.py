"""
gemini_fixer.py — Gemini 2.5 Flash as the self-healing fix engine (Gemini 2.5 Pro for human review).

Called by validation_heal_loop.py after each failed validation run.
Analyzes confirmed failures (post-flaky-filter), generates code/prompt patches,
enforces diff gates (max 50 lines) and patch scope limits (sacred functions protected).

Safety guarantees:
- Full unified diff is logged to heal_history.json BEFORE any file is touched
- Max 50 total lines changed per iteration (patch too large → rejected)
- Forbidden patterns (forced-commits, tool validation, state machine) → rejected
- Prior failed fix attempts are fed back to Gemini so it avoids repeating them

Authentication: uses Vertex AI service account (GOOGLE_APPLICATION_CREDENTIALS).
No Anthropic / Claude API calls remain in this module.
"""

import asyncio
import json
import logging
import os
import re
import difflib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import anthropic  # For Claude patch generation (install: pip install anthropic)

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

GEMINI_FLASH_MODEL = "gemini-2.5-flash-lite"  # Flash-Lite — cheapest with Google Search grounding ($0.10/M)
GEMINI_PRO_MODEL   = "gemini-2.5-flash-lite"  # Also use Flash-Lite for human review (was Pro — same grounding, 3x cheaper)
CLAUDE_MODEL       = "claude-sonnet-4-20250514"  # Claude Sonnet 4 — for code patch generation (superior at precise diffs)
MAX_PATCH_LINES = 50                     # Max total lines changed per iteration
# Gemini 2.5 thinking models consume output tokens for their internal reasoning.
# The system prompt alone is 30KB+ of brain files. Set generous limits so the
# JSON response is never truncated mid-string.
MAX_TOKENS     = 16384                   # Flash: 16K leaves plenty of room after thinking overhead
MAX_TOKENS_PRO = 16384                   # Pro: same budget for the detailed human-review plan

# Vertex AI / GCP config (all pulled from env vars set in the systemd service)
_GCP_PROJECT  = os.environ.get("GCP_PROJECT_ID", "sailly-voice-agent-eu")
_GCP_REGION   = os.environ.get("GEMINI_REGION", "europe-west4")
_GCP_KEY_FILE = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/home/charles2/.ssh/sailly-voice-agent-key.json",
)

# Cached Vertex AI client (initialised once on first use)
_GEMINI_CLIENT = None

# Anthropic API key (for Claude patch generation)
_ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Files Claude is allowed to modify (validation source only)
TRAINING_DIR = Path("/home/charles2/sailly-google-fork/server/training")

ALLOWED_FILES = {
    "node_manager.py",          # Intent keywords, routing keywords (NOT the functions)
    "adk_turn_processor.py",    # Hallucination term lists only
    "response_variations.py",   # Response variation patterns
}

# Claude CANNOT touch these patterns — they define the sacred brain logic
FORBIDDEN_PATTERNS = [
    "def check_forced_commits",
    "def _validate_tool_call",
    "def ready_for_order_commit",
    "def ready_for_reservation_commit",
    "def select_node",
    "def _check_prerequisites",
    "class NodeManager",
    "class ConversationState",
    "class ADKTurnProcessor",
    "def process_turn",
]


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class Patch:
    file: str
    description: str
    old_text: str
    new_text: str
    diff: str = ""          # unified diff, populated after validation
    lines_changed: int = 0  # populated after validation


@dataclass
class FixProposal:
    analysis: str
    patches: List[Patch]
    confidence: float
    affected_scenarios: List[str]
    cost_usd: float = 0.0
    rejected: bool = False
    rejection_reason: str = ""
    iteration: int = 0
    timestamp: str = ""
    web_search_queries: List[str] = field(default_factory=list)
    web_search_insights: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["patches"] = [asdict(p) for p in self.patches]
        return d


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_unified_diff(old_text: str, new_text: str, filename: str) -> str:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3,
    ))
    return "".join(diff)


def _count_diff_lines(diff: str) -> int:
    """Count added + removed lines in a unified diff."""
    return sum(
        1 for line in diff.splitlines()
        if line.startswith("+") or line.startswith("-")
        if not line.startswith("+++") and not line.startswith("---")
    )


def _validate_proposal(proposal: FixProposal) -> tuple[bool, str]:
    """
    Enforce diff gate and scope limits.
    Returns (is_valid, rejection_reason).
    """
    total_lines = 0

    for patch in proposal.patches:
        # Check allowed files
        if patch.file not in ALLOWED_FILES:
            return False, f"File '{patch.file}' is not in the allowed modification list"

        # Check forbidden patterns
        combined = patch.old_text + patch.new_text
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in combined:
                return False, (
                    f"Scope violation: patch touches '{pattern}' in {patch.file}. "
                    "This function is protected and requires human review."
                )

        # Build diff and count lines
        patch.diff = _build_unified_diff(patch.old_text, patch.new_text, patch.file)
        patch.lines_changed = _count_diff_lines(patch.diff)
        total_lines += patch.lines_changed

    # Enforce max patch size
    if total_lines > MAX_PATCH_LINES:
        return False, (
            f"Patch too large: {total_lines} lines changed > {MAX_PATCH_LINES} limit. "
            "Request a smaller, more targeted fix."
        )

    return True, ""


def _read_brain_files() -> Dict[str, str]:
    """Read current source of all allowed brain files for context."""
    result = {}
    for fname in ALLOWED_FILES:
        path = TRAINING_DIR / fname
        if path.exists():
            result[fname] = path.read_text(encoding="utf-8")
        else:
            result[fname] = "(file not found)"
    return result


def _group_failures_by_pattern(failed_results: List[dict]) -> Dict[str, List[dict]]:
    """Group failures by dominant failure reason."""
    groups: Dict[str, List[dict]] = {}
    for r in failed_results:
        failures = r.get("one_live_failures") or []
        missing = r.get("one_live_missing_tools") or []

        if missing:
            pattern = f"missing_tool:{','.join(sorted(missing[:2]))}"
        elif any("timeout" in str(f).lower() for f in failures):
            pattern = "timeout"
        elif any("hallucin" in str(f).lower() for f in failures):
            pattern = "hallucination"
        elif any("language" in str(f).lower() for f in failures):
            pattern = "language"
        elif failures:
            pattern = "quality"
        else:
            pattern = "unknown"

        groups.setdefault(pattern, []).append(r)

    return groups


# ── JSON extraction helper ────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """
    Robustly extract a JSON object from a Gemini response.

    Handles three formats:
      1. Pure JSON  (when response_mime_type='application/json' is set)
      2. ```json ... ``` fenced block
      3. JSON buried in prose (grounding responses) — extracted by regex
    """
    text = text.strip()

    # 1. Try direct parse first (fastest path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fence
    if "```" in text:
        for fence_content in re.findall(r"```(?:json)?\s*([\s\S]*?)```", text):
            try:
                return json.loads(fence_content.strip())
            except json.JSONDecodeError:
                continue

    # 3. Extract the outermost JSON object using brace matching
    start = text.find("{")
    if start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\" and in_str:
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break

    raise json.JSONDecodeError("No valid JSON object found in response", text, 0)


# ── Gemini API helpers ────────────────────────────────────────────────────────

def _get_gemini_client():
    """Lazily initialise and cache the Vertex AI Gemini client."""
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT

    from google import genai
    from google.oauth2 import service_account as _sa

    credentials = _sa.Credentials.from_service_account_file(
        _GCP_KEY_FILE,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    _GEMINI_CLIENT = genai.Client(
        vertexai=True,
        project=_GCP_PROJECT,
        location=_GCP_REGION,
        credentials=credentials,
    )
    logger.info(
        f"[GeminiFixer] Vertex AI client initialised "
        f"(project={_GCP_PROJECT}, region={_GCP_REGION})"
    )
    return _GEMINI_CLIENT


async def _call_claude_for_patches(
    bucket_name: str,
    gemini_analysis: str,
    gemini_web_insights: str,
    brain_files: dict,
    failing_scenarios: list,
    prior_attempts: list,
    human_instruction: str | None = None,
) -> tuple[list, float]:
    """
    Call Claude Sonnet 4 to generate precise code patches based on Gemini's analysis.

    Claude is significantly better than Gemini at generating exact old_text/new_text diffs
    that apply cleanly to source files. Gemini does the web research; Claude does the coding.

    Returns: (patches_list, cost_usd)
    """
    if not _ANTHROPIC_API_KEY:
        logger.warning("[ClaudeFixer] ANTHROPIC_API_KEY not set — skipping Claude patch generation")
        return [], 0.0

    allowed_str = ", ".join(sorted(ALLOWED_FILES))
    forbidden_str = "\n".join(f"- {p}" for p in FORBIDDEN_PATTERNS)

    files_block = "\n\n".join(
        f"=== {fname} ===\n{content[:6000]}" for fname, content in brain_files.items()
    )

    prior_text = ""
    if prior_attempts:
        prior_text = "\n## PRIOR ATTEMPTS (do NOT repeat these exact changes):\n"
        for a in prior_attempts[-5:]:
            prior_text += f"\nAttempt {a.get('attempt', '?')} (outcome: {a.get('outcome', '?')}):\n"
            for p in a.get("patches", []):
                if isinstance(p, dict):
                    prior_text += f"  - {p.get('file', '?')}: {p.get('description', '?')}\n"

    instr_text = ""
    if human_instruction:
        instr_text = f"\n## HUMAN OPERATOR INSTRUCTION (follow this carefully):\n{human_instruction}\n"

    system_prompt = f"""You are an expert Python developer specializing in voice AI systems built on Google's ADK framework.

You are given a root cause analysis from a research model, and your job is to generate PRECISE code patches.
These patches use exact old_text/new_text replacement — they must match the source file character-for-character.

## CONSTRAINTS
- You may ONLY modify: {allowed_str}
- You CANNOT modify: {forbidden_str}
- Total lines changed across ALL patches: ≤ {MAX_PATCH_LINES} lines
- old_text MUST exist verbatim in the file (copy-paste exact, including indentation and quotes)
- Generate the MINIMUM changes needed — surgical fixes only

## RESPONSE FORMAT
Return ONLY valid JSON (no markdown fences):
{{
  "patches": [
    {{
      "file": "conversation_nodes.py",
      "description": "One sentence describing what this change does",
      "old_text": "exact text to find verbatim in the file",
      "new_text": "replacement text"
    }}
  ],
  "confidence": 0.0-1.0,
  "reasoning": "Why this approach will fix the root cause"
}}"""

    user_message = f"""## RESEARCH FINDINGS (from Gemini with Google Search):
{gemini_analysis}

## WEB INSIGHTS:
{gemini_web_insights}
{instr_text}
## FAILING BUCKET: {bucket_name}

## FAILING SCENARIOS (sample):
"""
    for r in failing_scenarios[:6]:
        sid = r.get("scenario_id", r.get("id", "unknown"))
        user_message += f"- {sid}\n"
        for f in r.get("failures", [])[:2]:
            user_message += f"  reason: {f}\n"

    user_message += prior_text

    user_message += f"""

## CURRENT SOURCE FILES:
{files_block}

## TASK
Generate surgical patches that fix the root cause identified above.
Every old_text must match EXACTLY what is in the source file shown above.
"""

    loop = asyncio.get_event_loop()

    def _call_sync():
        client = anthropic.Anthropic(api_key=_ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return message

    try:
        message = await loop.run_in_executor(None, _call_sync)
    except Exception as e:
        logger.error(f"[ClaudeFixer] API call failed: {e}")
        return [], 0.0

    response_text = message.content[0].text if message.content else ""
    # Estimate cost (Sonnet 4: $3/M input, $15/M output)
    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    cost_usd = (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0

    logger.info(f"[ClaudeFixer] Claude response: {input_tokens} in / {output_tokens} out tokens, cost=${cost_usd:.4f}")

    try:
        data = _extract_json(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"[ClaudeFixer] Failed to parse Claude response as JSON: {e}")
        return [], cost_usd

    patches = []
    for p in data.get("patches", []):
        if p.get("old_text") and p.get("new_text"):
            patches.append(Patch(
                file=p.get("file", ""),
                description=p.get("description", ""),
                old_text=p.get("old_text", ""),
                new_text=p.get("new_text", ""),
            ))

    logger.info(f"[ClaudeFixer] Generated {len(patches)} patches (confidence={data.get('confidence', 0):.0%})")
    return patches, cost_usd


async def _call_gemini_flash(
    system_prompt: str,
    user_message: str,
    use_search: bool = False,
    model: str | None = None,
    max_tokens: int | None = None,
) -> tuple[str, float, list[str]]:
    """
    Call Gemini via Vertex AI and return (response_text, cost_usd, web_search_queries).

    Args:
        system_prompt: System instruction for the model.
        user_message:  User turn content.
        use_search:    If True, attach the google_search grounding tool.
        model:         Override model name (defaults to GEMINI_FLASH_MODEL).
        max_tokens:    Override max output tokens (defaults to MAX_TOKENS).

    Returns:
        Tuple of (text, cost_usd, web_search_queries).
        web_search_queries is a list of queries the model issued (may be empty).
    """
    from google.genai import types as genai_types

    client  = _get_gemini_client()
    m       = model or GEMINI_FLASH_MODEL
    mt      = max_tokens or MAX_TOKENS

    contents = [
        genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        )
    ]

    tools = [genai_types.Tool(google_search=genai_types.GoogleSearch())] if use_search else None

    # Force JSON output when not using grounding tools — prevents code-fence wrapping
    # and ensures the response is always valid, complete JSON.
    # (response_mime_type is incompatible with tool use / grounding)
    extra: dict = {}
    if tools:
        extra["tools"] = tools
    else:
        extra["response_mime_type"] = "application/json"

    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.3,
        max_output_tokens=mt,
        **extra,
    )

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model=m,
            contents=contents,
            config=config,
        ),
    )

    # Extract text, skipping internal thinking parts (thought=True) if present
    text = ""
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text and not getattr(part, "thought", False):
                text += part.text

    # Extract grounding web-search queries (may be absent)
    web_search_queries: list[str] = []
    if response.candidates:
        gm = getattr(response.candidates[0], "grounding_metadata", None)
        if gm:
            qs = getattr(gm, "web_search_queries", None)
            if qs:
                web_search_queries = list(qs)

    # Token usage for cost calculation
    um = getattr(response, "usage_metadata", None)
    input_tokens  = int(getattr(um, "prompt_token_count",      0) or 0)
    output_tokens = int(getattr(um, "candidates_token_count",  0) or 0)

    # Pricing: Flash ~$0.075/MTok in, $0.30/MTok out; Pro ~$1.25/$5.00
    if m == GEMINI_PRO_MODEL:
        cost_usd = (input_tokens * 1.25 + output_tokens * 5.0) / 1_000_000
    else:
        cost_usd = (input_tokens * 0.075 + output_tokens * 0.30) / 1_000_000

    return text.strip(), cost_usd, web_search_queries


def _build_system_prompt(brain_files: Dict[str, str]) -> str:
    files_block = "\n\n".join(
        f"=== {fname} ===\n{content[:8000]}"  # Truncate large files
        for fname, content in brain_files.items()
    )
    allowed_str = ", ".join(sorted(ALLOWED_FILES))
    forbidden_str = "\n".join(f"- {p}" for p in FORBIDDEN_PATTERNS)

    return f"""You are an expert in voice AI systems, specifically the Sailly restaurant voice assistant (DOBOO Korean Restaurant, Bonn) built on Google's ADK framework with Pipecat and Gemini 2.5 Flash.

Your task: analyze validation test failures and generate MINIMAL, TARGETED code patches to fix them.

## CRITICAL CONSTRAINTS — READ CAREFULLY

You may ONLY modify these files:
{allowed_str}

You may ONLY modify:
- Node prompts (text strings in conversation_nodes.py)
- Keyword lists (Python lists/sets of strings)
- Hallucination term lists in adk_turn_processor.py (_HALLUCINATED_TERMS)
- Response variation patterns in response_variations.py

You CANNOT modify ANY of these (they are production-tested sacred logic):
{forbidden_str}

Violating these constraints will cause your patch to be AUTOMATICALLY REJECTED.

## PATCH SIZE LIMIT
Total lines changed across ALL patches must be ≤ {MAX_PATCH_LINES} lines.
If your fix requires more, pick the single most impactful change.

## BRAIN FILE SOURCES (current state)

{files_block}

## RESPONSE FORMAT
Respond ONLY with a valid JSON object matching this schema:
{{
  "analysis": "Root cause in 2-3 sentences. Be specific about which scenarios fail and why.",
  "patches": [
    {{
      "file": "conversation_nodes.py",
      "description": "One sentence describing what this change does",
      "old_text": "exact text to find and replace (must exist verbatim in the file)",
      "new_text": "replacement text"
    }}
  ],
  "confidence": 0.0-1.0,
  "affected_scenarios": ["scenario-id-1", "scenario-id-2"]
}}

Do NOT include any text before or after the JSON object.
"""


def _build_user_message(
    failed_results: List[dict],
    grouped: Dict[str, List[dict]],
    iteration: int,
    prior_fixes: List[dict],
    cost_spent: float,
) -> str:
    # Summary of failures
    failure_summary = f"## VALIDATION FAILURES — Iteration {iteration}\n\n"
    failure_summary += f"Total confirmed failures: {len(failed_results)}\n"
    failure_summary += f"Total API cost so far: ${cost_spent:.2f}\n\n"

    failure_summary += "### Failure groups:\n"
    for pattern, group in sorted(grouped.items(), key=lambda x: -len(x[1])):
        failure_summary += f"\n**{pattern}** ({len(group)} scenarios):\n"
        for r in group[:5]:  # Show up to 5 per group
            sid = r.get("scenario_id", "unknown")
            missing = r.get("one_live_missing_tools", [])
            failures = r.get("one_live_failures", [])[:3]
            composite = r.get("one_live_composite", 0)
            failure_summary += f"  - {sid}: composite={composite}, missing={missing}\n"
            for f in failures:
                failure_summary += f"    reason: {f}\n"

    # Transcript samples (top 3 worst)
    worst = sorted(failed_results, key=lambda r: r.get("one_live_composite", 100))[:3]
    failure_summary += "\n### Transcript samples (worst 3):\n"
    for r in worst:
        sid = r.get("scenario_id", "?")
        turns = r.get("one_live_turns", [])
        failure_summary += f"\n**{sid}** (composite {r.get('one_live_composite', 0)}):\n"
        if isinstance(turns, list):
            for t in turns[:6]:
                if isinstance(t, dict):
                    caller = t.get("caller_text", t.get("stt_transcript", ""))[:120]
                    bot = t.get("bot_response", "")[:120]
                    if caller:
                        failure_summary += f"  Caller: {caller}\n"
                    if bot:
                        failure_summary += f"  Bot:    {bot}\n"

    # Prior fix history
    if prior_fixes:
        failure_summary += "\n### PRIOR FIX ATTEMPTS (DO NOT repeat these approaches):\n"
        for i, fix in enumerate(prior_fixes[-5:], 1):  # Last 5 fixes
            outcome = fix.get("outcome", "unknown")
            patches = fix.get("patches", [])
            failure_summary += f"\nAttempt {i} (outcome: {outcome}):\n"
            for p in patches:
                failure_summary += f"  - {p.get('file', '?')}: {p.get('description', '?')}\n"

    failure_summary += "\n\nNow generate the minimal patch to fix the most impactful failure group."
    return failure_summary


# ── Public API ────────────────────────────────────────────────────────────────

async def analyze_and_fix(
    failed_results: List[dict],
    iteration: int,
    prior_fixes: List[dict],
    cost_spent: float,
    api_key: Optional[str] = None,
) -> FixProposal:
    """
    Analyze confirmed validation failures and generate code/prompt patches.

    Args:
        failed_results: List of failed scenario result dicts from ab_results.json
        iteration: Current heal loop iteration number
        prior_fixes: List of prior FixProposal.to_dict() results (for history context)
        cost_spent: Total USD spent so far in this heal run
        api_key: Deprecated — kept for backward-compat, ignored (uses Vertex AI service account)

    Returns:
        FixProposal with patches (may be rejected=True if validation fails)
    """
    brain_files = _read_brain_files()
    grouped = _group_failures_by_pattern(failed_results)

    system_prompt = _build_system_prompt(brain_files)
    user_message = _build_user_message(failed_results, grouped, iteration, prior_fixes, cost_spent)

    logger.info(
        f"[GeminiFixer] Iteration {iteration}: calling {GEMINI_FLASH_MODEL} "
        f"with {len(failed_results)} failures across {len(grouped)} pattern groups..."
    )

    response_text, cost_usd, _ = await _call_gemini_flash(system_prompt, user_message)

    # Parse Gemini's JSON response
    try:
        data = _extract_json(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"[GeminiFixer] Failed to parse Gemini response as JSON: {e}")
        logger.debug(f"[GeminiFixer] Raw response: {response_text[:500]}")
        return FixProposal(
            analysis="Gemini response was not valid JSON",
            patches=[],
            confidence=0.0,
            affected_scenarios=[],
            cost_usd=cost_usd,
            rejected=True,
            rejection_reason=f"JSON parse error: {e}",
            iteration=iteration,
            timestamp=datetime.now().isoformat(),
        )

    # Build Patch objects
    patches = []
    for p in data.get("patches", []):
        patches.append(Patch(
            file=p.get("file", ""),
            description=p.get("description", ""),
            old_text=p.get("old_text", ""),
            new_text=p.get("new_text", ""),
        ))

    proposal = FixProposal(
        analysis=data.get("analysis", ""),
        patches=patches,
        confidence=float(data.get("confidence", 0.5)),
        affected_scenarios=data.get("affected_scenarios", []),
        cost_usd=cost_usd,
        iteration=iteration,
        timestamp=datetime.now().isoformat(),
    )

    # Validate before returning
    is_valid, reason = _validate_proposal(proposal)
    if not is_valid:
        proposal.rejected = True
        proposal.rejection_reason = reason
        logger.warning(f"[GeminiFixer] Proposal REJECTED: {reason}")
    else:
        total_lines = sum(p.lines_changed for p in proposal.patches)
        logger.info(
            f"[GeminiFixer] Proposal ACCEPTED: {len(patches)} patches, "
            f"{total_lines} lines changed, confidence={proposal.confidence:.0%}"
        )
        for p in proposal.patches:
            logger.info(f"  {p.file}: {p.description} ({p.lines_changed} lines)")

    return proposal


async def analyze_and_fix_deep(
    bucket_name: str,
    failing_scenarios: List[dict],
    prior_cfv_attempts: List[dict],
    cost_spent: float,
    api_key: Optional[str] = None,  # Deprecated — kept for backward-compat, ignored
    human_instruction: Optional[str] = None,
) -> FixProposal:
    """
    Deep analysis using Gemini 2.5 Flash with Google Search grounding.

    Used by Crucial Fix Validation (CFV) after the standard 8-iteration fix loop
    fails to resolve a bucket. Forces orthogonal reasoning by grounding the model
    with live Google Search results so it can reference real-world patterns,
    library docs, and code examples it cannot derive from brain files alone.

    Google Search grounding is native to Gemini — no explicit tool-call loop required.
    """
    brain_files = _read_brain_files()
    files_block = "\n\n".join(
        f"=== {fname} ===\n{content[:8000]}" for fname, content in brain_files.items()
    )
    allowed_str = ", ".join(sorted(ALLOWED_FILES))
    forbidden_str = "\n".join(f"- {p}" for p in FORBIDDEN_PATTERNS)

    human_instr_block = f"\n## HUMAN OPERATOR INSTRUCTION:\n{human_instruction}\nThis guidance MUST inform your analysis and patch approach.\n" if human_instruction else ""

    system_prompt = f"""You are an expert researcher specializing in voice AI systems built on Google's ADK framework.

You are in CRUCIAL FIX mode — standard iterative fixes have already been tried for the bucket "{bucket_name}" and failed. You MUST find a genuinely different root cause using diverse web research.

YOU HAVE GOOGLE SEARCH GROUNDING. Conduct broad research across multiple source types:
1. **GitHub repos & issues** — search for similar bugs in google-adk, pipecat, livekit-agents, voicebot frameworks
2. **Competitor solutions** — how do Voiceflow, Retell AI, Bland AI, Vapi, and similar voice AI platforms handle this type of failure?
3. **AI newsletters & blogs** — The Batch, Import AI, Latent Space, AI practitioners on Substack
4. **Academic papers** — conversational AI, intent disambiguation, tool routing, dialogue state machines
5. **Twitter/X & Reddit** — r/MachineLearning, r/LanguageTechnology, r/LocalLLaMA, AI practitioner threads
6. **Stack Overflow & forums** — related error patterns and community solutions for this class of issue

Focus your searches specifically on the failure pattern described below.
{human_instr_block}
## RESPONSE FORMAT
Return ONLY a JSON object (no markdown, no prose outside JSON):
{{
  "analysis": "3-4 sentences: root cause + what your research revealed from diverse sources",
  "web_search_insights": "Key findings from GitHub, competitors, papers, Reddit, etc. that change the approach",
  "research_sources": ["source type 1 found relevant", "competitor X handles this by..."],
  "proposed_approach": "High-level description of the fix approach informed by research",
  "confidence": 0.0-1.0,
  "affected_scenarios": ["scenario-id-1"]
}}
NOTE: Do NOT include patches in this response — a separate code model (Claude) will generate the patches.
"""

    # Build failure summary for this bucket
    prior_attempts_text = ""
    if prior_cfv_attempts:
        prior_attempts_text = "\n### PRIOR CFV ATTEMPTS (DO NOT repeat these approaches):\n"
        for i, attempt in enumerate(prior_cfv_attempts[-5:], 1):
            outcome = attempt.get("outcome", "unknown")
            patches = attempt.get("patches", [])
            web_queries = attempt.get("web_search_queries", [])
            prior_attempts_text += f"\nCFV Attempt {i} (outcome: {outcome}):\n"
            if web_queries:
                prior_attempts_text += f"  Web searches used: {', '.join(web_queries)}\n"
            for p in patches:
                prior_attempts_text += f"  - {p.get('file', '?')}: {p.get('description', '?')}\n"

    user_message = f"""## CRUCIAL FIX VALIDATION — Bucket: {bucket_name}

Total API cost so far: ${cost_spent:.2f}
Failing scenarios in this bucket: {len(failing_scenarios)}

### Failing scenarios:
"""
    for r in failing_scenarios[:10]:
        sid = r.get("scenario_id", r.get("id", "unknown"))
        missing = r.get("one_live_missing_tools", [])
        failures = r.get("one_live_failures", r.get("failures", []))[:3]
        composite = r.get("one_live_composite", r.get("composite", 0))
        turns = r.get("one_live_turns", r.get("turns", []))
        user_message += f"\n**{sid}** (composite={composite}, missing={missing}):\n"
        for f in (failures or []):
            user_message += f"  reason: {f}\n"
        if isinstance(turns, list):
            for t in turns[:4]:
                if isinstance(t, dict):
                    caller = t.get("caller_text", t.get("stt_transcript", ""))[:120]
                    bot = t.get("bot_response", "")[:120]
                    if caller:
                        user_message += f"  Caller: {caller}\n"
                    if bot:
                        user_message += f"  Bot:    {bot}\n"

    user_message += prior_attempts_text
    user_message += f"""

## YOUR TASK
1. Use your Google Search grounding to research the bucket "{bucket_name}" failure across GitHub, competitor platforms, AI newsletters, papers, Reddit, and Stack Overflow
2. Analyze the failures deeply with your research findings from these diverse sources
3. Identify a genuinely DIFFERENT root cause theory than all prior attempts
4. Return the JSON response with your analysis and proposed approach — a separate code model will generate the actual patches
"""

    logger.info(
        f"[GeminiFixer/Deep] Bucket '{bucket_name}': calling {GEMINI_FLASH_MODEL} with Google Search "
        f"(research phase — Claude will generate patches) cost so far: ${cost_spent:.2f}..."
    )

    response_text, cost_usd, web_search_queries = await _call_gemini_flash(
        system_prompt,
        user_message,
        use_search=True,
    )

    # Parse Gemini's research response
    try:
        data = _extract_json(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"[GeminiFixer/Deep] Failed to parse response as JSON: {e}")
        return FixProposal(
            analysis="Gemini deep response was not valid JSON",
            patches=[],
            confidence=0.0,
            affected_scenarios=[],
            cost_usd=cost_usd,
            rejected=True,
            rejection_reason=f"JSON parse error: {e}",
            iteration=0,
            timestamp=datetime.now().isoformat(),
            web_search_queries=web_search_queries,
        )

    gemini_analysis = data.get("analysis", "")
    gemini_insights = data.get("web_search_insights", "") + "\n" + "\n".join(data.get("research_sources", []))
    gemini_proposed = data.get("proposed_approach", "")

    # Phase 2: Claude Sonnet 4 generates the actual patches
    logger.info(
        f"[ClaudeFixer] Bucket '{bucket_name}': calling Claude {CLAUDE_MODEL} for patch generation..."
    )
    claude_patches, claude_cost = await _call_claude_for_patches(
        bucket_name=bucket_name,
        gemini_analysis=gemini_analysis + "\n\nProposed approach: " + gemini_proposed,
        gemini_web_insights=gemini_insights,
        brain_files=brain_files,
        failing_scenarios=failing_scenarios,
        prior_attempts=prior_cfv_attempts,
        human_instruction=human_instruction,
    )
    cost_usd += claude_cost

    patches = claude_patches  # Use Claude's patches instead of Gemini's

    proposal = FixProposal(
        analysis=data.get("analysis", ""),
        patches=patches,
        confidence=float(data.get("confidence", 0.5)),
        affected_scenarios=data.get("affected_scenarios", []),
        cost_usd=cost_usd,
        iteration=0,
        timestamp=datetime.now().isoformat(),
        web_search_queries=web_search_queries,
        web_search_insights=data.get("web_search_insights", ""),
    )

    is_valid, reason = _validate_proposal(proposal)
    if not is_valid:
        proposal.rejected = True
        proposal.rejection_reason = reason
        logger.warning(f"[GeminiFixer/Deep] Proposal REJECTED: {reason}")
    else:
        total_lines = sum(p.lines_changed for p in proposal.patches)
        logger.info(
            f"[GeminiFixer/Deep] Proposal ACCEPTED: {len(patches)} patches, "
            f"{total_lines} lines changed, confidence={proposal.confidence:.0%}, "
            f"web_searches={len(web_search_queries)}"
        )

    return proposal


def apply_patches(proposal: FixProposal) -> List[str]:
    """
    Apply all patches in the proposal to the training source files.
    Returns list of (file, error) for any patches that failed to apply.

    Raises if proposal.rejected is True (caller must check before calling).
    """
    if proposal.rejected:
        raise ValueError(f"Cannot apply rejected proposal: {proposal.rejection_reason}")

    errors = []
    for patch in proposal.patches:
        path = TRAINING_DIR / patch.file
        if not path.exists():
            errors.append(f"{patch.file}: file not found")
            continue

        content = path.read_text(encoding="utf-8")
        if patch.old_text not in content:
            errors.append(
                f"{patch.file}: old_text not found verbatim — "
                "patch may have already been applied or file changed"
            )
            continue

        new_content = content.replace(patch.old_text, patch.new_text, 1)
        path.write_text(new_content, encoding="utf-8")
        logger.info(f"[ClaudeFixer] Applied patch to {patch.file}")

    return errors


def revert_patches(proposal: FixProposal) -> List[str]:
    """
    Revert all patches in the proposal (apply in reverse).
    Returns list of errors for patches that failed to revert.
    """
    errors = []
    for patch in proposal.patches:
        path = TRAINING_DIR / patch.file
        if not path.exists():
            errors.append(f"{patch.file}: file not found for revert")
            continue

        content = path.read_text(encoding="utf-8")
        if patch.new_text not in content:
            errors.append(f"{patch.file}: new_text not found — may have already been reverted")
            continue

        original = content.replace(patch.new_text, patch.old_text, 1)
        path.write_text(original, encoding="utf-8")
        logger.info(f"[ClaudeFixer] Reverted patch in {patch.file}")

    return errors


async def create_human_review_plan(review_json: dict, api_key: Optional[str] = None) -> dict:
    """
    Use Gemini 2.5 Pro with Google Search grounding to generate a structured remediation plan
    for a bucket that has exhausted all automated fix attempts.

    Returns a dict with keys:
      root_cause_analysis, web_research_findings, fix_plan (list of steps),
      risk_assessment, estimated_confidence, web_search_queries, cost_usd
    """
    bucket_name = review_json.get("bucket_name", "unknown")
    total_attempts = review_json.get("total_cfv_attempts", 0)

    system_prompt = """You are a senior AI systems engineer specializing in conversational AI and restaurant ordering bots.
You have deep expertise in Google ADK (Agent Development Kit), dialogue state machines, LLM hallucination patterns,
and production test validation frameworks. You also have access to live Google Search grounding.

Your task is to create a comprehensive remediation plan for a CRITICAL BUG in a restaurant voice ordering bot.
This bucket of test scenarios has FAILED all automated fix attempts. You must:
1. Diagnose the root cause with high confidence using the evidence provided
2. Use your Google Search grounding to research known patterns for this class of bug
3. Produce a concrete, step-by-step fix plan with actual code changes

Respond ONLY with a JSON object — no markdown fences, no prose outside JSON."""

    user_message = f"""CRITICAL: Bucket '{bucket_name}' has failed {total_attempts} automated fix attempts.
All standard fixes have been exhausted. We need a deep expert analysis.

=== FULL REVIEW PACKAGE ===
{json.dumps(review_json, indent=2, default=str)[:12000]}

=== TASK ===
Analyze ALL available evidence and produce a comprehensive remediation plan.
Use your search grounding to research:
1. Similar ADK/Gemini conversational AI bugs
2. Known patterns in restaurant ordering voice assistants
3. State machine issues in multi-turn dialogue
4. Tool-call sequencing problems

Return a JSON object:
{{
  "root_cause_analysis": "Detailed explanation of why this bucket fails",
  "primary_failure_mode": "concise category label (e.g. 'State machine premature reset')",
  "web_research_findings": ["Finding 1", "Finding 2", ...],
  "fix_plan": [
    {{
      "step": 1,
      "file": "conversation_nodes.py",
      "description": "What change to make",
      "rationale": "Why this should fix the root cause",
      "patches": [
        {{
          "file": "conversation_nodes.py",
          "description": "Short description",
          "old_text": "exact text to replace",
          "new_text": "replacement text"
        }}
      ]
    }}
  ],
  "risk_assessment": "Low/Medium/High — what could break",
  "estimated_confidence": 0.75,
  "web_search_queries": ["query1", "query2"],
  "additional_notes": "Anything else the human engineer should know"
}}"""

    logger.info(
        f"[GeminiFixer/Pro] Bucket '{bucket_name}': calling {GEMINI_PRO_MODEL} for human review plan "
        f"({total_attempts} failed attempts)..."
    )

    response_text, cost_usd, web_search_queries = await _call_gemini_flash(
        system_prompt,
        user_message,
        use_search=True,
        model=GEMINI_PRO_MODEL,
        max_tokens=MAX_TOKENS_PRO,
    )
    logger.info(f"[GeminiFixer/Pro] Plan generated. Cost: ${cost_usd:.4f}")

    try:
        data = _extract_json(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"[GeminiFixer/Pro] Failed to parse response as JSON: {e}")
        return {
            "root_cause_analysis": f"Gemini Pro response parse error: {e}",
            "primary_failure_mode": "parse_error",
            "web_research_findings": [],
            "fix_plan": [],
            "risk_assessment": "Unknown",
            "estimated_confidence": 0.0,
            "web_search_queries": web_search_queries,
            "cost_usd": cost_usd,
            "raw_response": response_text[:2000],
        }

    data["web_search_queries"] = list(set(web_search_queries + data.get("web_search_queries", [])))
    data["cost_usd"] = cost_usd
    return data
