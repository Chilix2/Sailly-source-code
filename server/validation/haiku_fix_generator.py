"""
Fix Generator — Receives Grok audit + call metrics, generates targeted code fixes.

Model hierarchy (context-aware escalation):
  1. claude-haiku-4-5       (200K context, primary, fast + cheap)
  2. grok-4.3               (XAI API, larger context window, used if Haiku context > 160K tokens)
  3. claude-sonnet-4-6      (200K context, best reasoning, fallback if Grok fails)

Design principles:
  - Loads FULL source files (not snippets) for maximum context
  - Runs web research via XAI Grok before generating fixes
  - Injects verbatim code so old_code can be an exact substring
  - Integrates known_issues_advisor for institutional memory
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Model config ─────────────────────────────────────────────────────────────
DEFAULT_HAIKU_FIX_MODEL = "claude-haiku-4-5"   # primary — restored to Haiku per user request
_GROK_FALLBACK_MODEL    = "grok-4.3"            # fallback when context > 160K tokens
_SONNET_FALLBACK_MODEL  = "claude-sonnet-4-6"   # final fallback if Grok also fails

# Token budget: leave 20K for output. Haiku 4.5 = 200K input.
_HAIKU_MAX_CONTEXT_TOKENS  = 180_000   # chars / 3.5 ≈ token estimate
_GROK_MAX_CONTEXT_TOKENS   = 240_000   # Grok 4.3 has larger context

# Rough char→token ratio for Python/JSON source (conservative)
_CHARS_PER_TOKEN = 3.5

# Full source files to load (relative to project root) — ordered by diagnostic priority
_FULL_CONTEXT_FILES: List[str] = [
    "server/brain/v4_pipeline.py",            # core state machine — most bugs live here
    "server/brain/conversation_state.py",     # slot extractors, name/phone/date parsing
    "server/brain/context_doc_builder.py",    # COMMIT_TOOLS_REQUIRED_SLOTS and slot gate
    "server/brain/layer2/tool_calling.py",    # tool dispatch
    "server/brain/layer2/system_prompt.py",   # system prompt / LLM phrasing
    "server/brain/layer1/nodes/faq.py",       # FAQ / opening hours handlers
    "server/brain/layer1/nodes/complaint.py", # complaint handling
    "server/brain/layer1/nodes/escalation.py",# escalation / manager transfer
    "server/brain/layer1/nodes/reservation.py",  # reservation commit
]

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_full_file(rel_path: str) -> str:
    """Load entire source file, returning empty string if missing."""
    full_path = _PROJECT_ROOT / rel_path
    try:
        content = full_path.read_text(encoding="utf-8")
        return content
    except Exception as exc:
        logger.debug("[fixer] Could not read %s: %s", rel_path, exc)
        return ""


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def _gather_codebase_context(
    metric_scores: Dict[str, float],
    max_chars: int = 600_000,
) -> str:
    """
    Build full-file codebase context up to max_chars budget.
    Prioritises files based on which metrics are worst.
    """
    tool_acc    = metric_scores.get("tool_accuracy", 100)
    flow        = metric_scores.get("flow", 100)
    deterministic = metric_scores.get("deterministic", 100)

    # Determine priority order based on failing metrics
    priority = list(_FULL_CONTEXT_FILES)
    if deterministic < 60 and tool_acc >= 70:
        # Name/phone readback issues — lead with conversation_state
        priority = [p for p in priority if "conversation_state" in p] + \
                   [p for p in priority if "conversation_state" not in p]
    if tool_acc < 60:
        # Tool not firing — lead with tool_calling + context_doc_builder
        priority = [p for p in priority if any(x in p for x in ["tool_calling", "context_doc"])] + \
                   [p for p in priority if not any(x in p for x in ["tool_calling", "context_doc"])]

    snippets = []
    used_chars = 0
    for rel_path in priority:
        content = _load_full_file(rel_path)
        if not content:
            continue
        block = f"{'='*70}\n# FILE: {rel_path}  ({len(content.splitlines())} lines)\n{'='*70}\n{content}\n"
        if used_chars + len(block) > max_chars:
            # Partial load — take as much as fits
            remaining = max_chars - used_chars
            if remaining > 2000:
                partial = content[:remaining - 200]
                block = (f"{'='*70}\n# FILE: {rel_path}  [PARTIAL — first {remaining} chars of {len(content)} total]\n"
                         f"{'='*70}\n{partial}\n# ... truncated due to context budget ...\n")
                snippets.append(block)
                used_chars += len(block)
            break
        snippets.append(block)
        used_chars += len(block)

    logger.info("[fixer] Loaded %d source files, ~%d chars (~%dk tokens)",
                len(snippets), used_chars, used_chars // 1000 * _CHARS_PER_TOKEN // 1000)
    return "\n".join(snippets) if snippets else "(No source files loaded)"


def _strip_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"```.*", "", text, flags=re.DOTALL)
    return text.strip()


class HaikuFixGenerator:
    """
    Generates targeted code fixes using a model cascade:
    claude-haiku-4-5 → grok-4.3 → claude-sonnet-4-6
    """

    def __init__(self):
        # Anthropic client (Haiku + Sonnet)
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise RuntimeError("pip install anthropic") from exc
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self._anthropic = AsyncAnthropic(api_key=key)

        # XAI client (Grok — OpenAI-compatible)
        try:
            from openai import AsyncOpenAI
        except ImportError:
            self._xai = None
        else:
            xai_key = os.environ.get("XAI_API_KEY")
            self._xai = AsyncOpenAI(api_key=xai_key, base_url="https://api.x.ai/v1") if xai_key else None

        self.model = os.environ.get("HAIKU_FIX_MODEL", DEFAULT_HAIKU_FIX_MODEL)
        logger.info("[fixer] Primary fix model: %s | Grok fallback: %s | Sonnet fallback: %s",
                    self.model, _GROK_FALLBACK_MODEL, _SONNET_FALLBACK_MODEL)

    # ── Web research ──────────────────────────────────────────────────────────

    async def _web_research(
        self,
        batch_key: str,
        achtung_flags: List[dict],
        metric_scores: Dict[str, float],
        improvements: str,
    ) -> str:
        """
        Run XAI Grok web search to find root causes and best practices before fixing.
        Returns a research context block (empty string if XAI unavailable).
        """
        if not self._xai:
            logger.debug("[fixer] XAI client not available — skipping web research")
            return ""

        # Build a targeted search query
        low_metrics = [k for k, v in metric_scores.items() if isinstance(v, (int, float)) and v < 60]
        flag_codes = []
        for f in achtung_flags:
            m = re.search(r"Achtung Sailly: ([A-Z_]+)", f.get("flag", ""))
            if m:
                flag_codes.append(m.group(1))

        query_parts = [f"German voice bot restaurant {batch_key[:2]} phase validation fix 2026"]
        if low_metrics:
            query_parts.append(f"low {'+'.join(low_metrics)} score fix")
        if flag_codes:
            query_parts.append(f"flags: {' '.join(flag_codes[:3])}")
        if improvements:
            # Extract key technical terms
            tech_terms = re.findall(r"\b(?:tool call|slot|state|intent|flow|loop|name|phone|readback)\b",
                                    improvements[:200], re.IGNORECASE)
            if tech_terms:
                query_parts.append(" ".join(set(tech_terms[:4])))

        query = " | ".join(query_parts[:3])

        try:
            logger.info("[fixer] Web research query: %s", query)
            resp = await self._xai.chat.completions.create(
                model="grok-3-mini",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Research this technical problem and provide root cause analysis + best practices:\n\n"
                        f"{query}\n\n"
                        f"Context: This is a German restaurant voice bot (Sailly) with these failing metrics:\n"
                        f"{json.dumps(metric_scores)}\n"
                        f"Achtung flags: {flag_codes}\n\n"
                        f"Improvements needed: {improvements[:400]}\n\n"
                        f"Provide: (1) Most likely root cause in Python voice agent pipeline code, "
                        f"(2) Specific code patterns that fix this, (3) Common mistakes to avoid. "
                        f"Be technical and specific to Python async conversation state machines."
                    )
                }],
                extra_body={"search": True},
                max_tokens=1500,
                temperature=0.3,
            )
            research = resp.choices[0].message.content or ""
            logger.info("[fixer] Web research returned %d chars", len(research))
            return f"\n\nINTERNET RESEARCH CONTEXT (XAI Grok search — run before generating fixes):\n{research}\n"
        except Exception as exc:
            logger.warning("[fixer] Web research failed: %s", exc)
            return ""

    # ── Call reports ──────────────────────────────────────────────────────────

    async def _fetch_call_reports(self, call_sids: List[str]) -> str:
        """Fetch detailed 9-section call reports from Postgres (up to 5 calls, 15K chars each)."""
        try:
            from server.call_report.detailed_builder import build_detailed_call_report
        except ImportError as exc:
            logger.warning("[fixer] Could not import build_detailed_call_report: %s", exc)
            return ""
        reports: List[str] = []
        for sid in call_sids[:5]:
            try:
                md = await build_detailed_call_report(sid)
                reports.append(md[:15_000])
                logger.info("[fixer] Fetched call report for %s (%d chars)", sid, len(md))
            except Exception as exc:
                logger.warning("[fixer] Could not fetch report for %s: %s", sid, exc)
        return "\n\n---\n\n".join(reports)

    # ── Model cascade ─────────────────────────────────────────────────────────

    async def _call_anthropic(self, model: str, prompt: str) -> str:
        """Call Anthropic API (Haiku or Sonnet)."""
        response = await self._anthropic.messages.create(
            model=model,
            max_tokens=20_000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text if response.content else ""

    async def _call_grok(self, prompt: str) -> str:
        """Call XAI Grok via OpenAI-compatible API."""
        if not self._xai:
            raise RuntimeError("XAI client not configured")
        resp = await self._xai.chat.completions.create(
            model=_GROK_FALLBACK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=16_000,
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""

    async def _generate_with_cascade(self, prompt: str, context_chars: int) -> str:
        """
        Try models in order based on context size.
        Returns the raw text response from whichever model succeeds first.
        """
        context_tokens = _estimate_tokens(prompt)
        logger.info("[fixer] Prompt size: ~%d tokens (%d chars)", context_tokens, context_chars)

        # Choose primary model based on context size
        if context_tokens <= _HAIKU_MAX_CONTEXT_TOKENS:
            primary_model = self.model  # claude-haiku-4-5
        elif context_tokens <= _GROK_MAX_CONTEXT_TOKENS and self._xai:
            logger.info("[fixer] Context too large for Haiku (%d tokens) — escalating to Grok 4.3", context_tokens)
            primary_model = "grok"
        else:
            logger.info("[fixer] Context very large (%d tokens) — escalating to Sonnet 4.6", context_tokens)
            primary_model = _SONNET_FALLBACK_MODEL

        # Attempt 1: primary
        try:
            if primary_model == "grok":
                raw = await self._call_grok(prompt)
            else:
                raw = await self._call_anthropic(primary_model, prompt)
            logger.info("[fixer] Primary model (%s) succeeded (%d chars)", primary_model, len(raw))
            return raw
        except Exception as exc:
            logger.warning("[fixer] Primary model (%s) failed: %s — trying fallback", primary_model, exc)

        # Attempt 2: Grok 4.3 fallback (if not already tried)
        if primary_model != "grok" and self._xai:
            try:
                raw = await self._call_grok(prompt)
                logger.info("[fixer] Grok 4.3 fallback succeeded (%d chars)", len(raw))
                return raw
            except Exception as exc:
                logger.warning("[fixer] Grok 4.3 fallback failed: %s — trying Sonnet 4.6", exc)

        # Attempt 3: Sonnet 4.6 final fallback
        if primary_model != _SONNET_FALLBACK_MODEL:
            try:
                raw = await self._call_anthropic(_SONNET_FALLBACK_MODEL, prompt)
                logger.info("[fixer] Sonnet 4.6 fallback succeeded (%d chars)", len(raw))
                return raw
            except Exception as exc:
                logger.warning("[fixer] Sonnet 4.6 fallback failed: %s — trying OpenAI gpt-4o", exc)

        # Attempt 4: OpenAI gpt-4o as final fallback
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                from openai import AsyncOpenAI as _OAI
                _oai_client = _OAI(api_key=openai_key)
                resp = await _oai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4096,
                    temperature=0.2,
                )
                raw = resp.choices[0].message.content.strip()
                logger.info("[fixer] OpenAI gpt-4o fallback succeeded (%d chars)", len(raw))
                return raw
            except Exception as exc:
                logger.error("[fixer] OpenAI gpt-4o fallback failed: %s", exc)

        logger.error("[fixer] All models failed — returning empty")
        return ""

    # ── Main API ──────────────────────────────────────────────────────────────

    async def generate_fixes(
        self,
        grok_report: Dict[str, Any],
        call_metrics: Dict[str, Any],
        call_sids: Optional[List[str]] = None,
        batch_key: Optional[str] = None,
        attempt: int = 1,
        prior_fix_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Generate code fixes based on Grok audit + call metrics + full source context.

        Args:
            grok_report:        Grok audit result dict
            call_metrics:       Structured metrics from PostgresMetricsFetcher
            call_sids:          Call sids for full report fetching
            batch_key:          e.g. "G2.2_D4" — used for known_issues matching + research query
            attempt:            Current attempt number (1-8)
            prior_fix_history:  List of {attempt, score, fix_plan} from earlier attempts
        """
        t0 = time.time()
        logger.info("[fixer] Generating fixes — batch=%s attempt=%d model=%s",
                    batch_key or "?", attempt, self.model)

        metric_scores   = grok_report.get("metric_scores", {})
        composite       = grok_report.get("composite_score", 0)
        improvements    = grok_report.get("improvements", "")
        tool_analysis   = grok_report.get("tool_analysis", "")
        achtung_flags   = grok_report.get("achtung_flags", [])
        failed_tools    = call_metrics.get("failed_tool_calls", [])
        conv_issues     = call_metrics.get("conversation_issues", [])
        loop_detections = call_metrics.get("loop_detections", [])

        # ── Parallel fetch: web research + call reports + known issues ────────
        import asyncio
        research_task     = asyncio.create_task(
            self._web_research(batch_key or "unknown", achtung_flags, metric_scores, improvements)
        )
        call_reports_task = asyncio.create_task(
            self._fetch_call_reports(call_sids or [])
        )
        web_research_block, call_reports_raw = await asyncio.gather(
            research_task, call_reports_task
        )

        call_reports_block = ""
        if call_reports_raw:
            call_reports_block = (
                f"\nFULL CALL REPORTS (per-turn breakdown, transcripts, tools, flags — "
                f"{min(5, len(call_sids or []))} calls):\n{call_reports_raw}\n"
            )

        # ── Known issues advisor block ────────────────────────────────────────
        known_issues_block = ""
        try:
            from server.validation.known_issues_advisor import KnownIssuesAdvisor
            advisor = KnownIssuesAdvisor()
            known_issues_block = advisor.get_advice_block(grok_report, call_metrics, batch_key)
        except Exception as exc:
            logger.warning("[fixer] Known issues advisor failed: %s", exc)

        # ── Full source context ───────────────────────────────────────────────
        codebase_context = _gather_codebase_context(metric_scores)

        # ── Achtung flags ─────────────────────────────────────────────────────
        achtung_block = ""
        if achtung_flags:
            flags_text = "\n".join(
                f"  - {f.get('call_sid','')} turn {f.get('turn','?')}: {f.get('flag','')[:200]}"
                for f in achtung_flags
            )
            achtung_block = f"\nCONFIRMED CALLER-BOT ERROR FLAGS (MUST all be fixed):\n{flags_text}\n"

        loops_block = ""
        if loop_detections:
            loops_block = (f"\nBOT LOOPS DETECTED ({len(loop_detections)}):\n"
                          + json.dumps(loop_detections[:5], indent=2, ensure_ascii=False) + "\n")

        # ── Prior fix history (sequential context) ────────────────────────────
        history_block = ""
        if prior_fix_history:
            history_lines = ["\nPRIOR FIX ATTEMPTS FOR THIS BATCH (do NOT repeat these):"]
            for h in prior_fix_history[-5:]:  # last 5 attempts
                score = h.get("score", "?")
                summary = h.get("summary", "")[:200]
                delta = h.get("score_delta", "?")
                history_lines.append(
                    f"  Attempt {h.get('attempt', '?')}: score={score} (delta={delta}): {summary}"
                )
                for fix in h.get("fixes", [])[:3]:
                    history_lines.append(
                        f"    - [{fix.get('file','')}] {fix.get('issue','')[:100]}"
                        f" → outcome: {fix.get('outcome','?')}"
                    )
            history_block = "\n".join(history_lines) + "\n"

        # ── Near-miss and high-metric constraints ────────────────────────────
        _ta = metric_scores.get('tool_accuracy', 0)
        _fl = metric_scores.get('flow', 0)
        _near_miss_warning = ""
        if composite >= 70:
            _near_miss_warning = f"""
╔══════════════════════════════════════════════════════════════════╗
║ ⚠️  NEAR-MISS: Score {composite:.1f} is CLOSE to target 80.              ║
║  ABSOLUTELY DO NOT make large changes — you will break it.       ║
║  ONLY ONE micro-fix allowed (max 10 lines total across all files) ║
║  DO NOT add new functions or restructure existing code.           ║
║  ONLY add ONE small guard condition or logging statement.         ║
╚══════════════════════════════════════════════════════════════════╝"""
        _tool_lock = ""
        if _ta >= 85:
            _tool_lock = f"\n⛔ tool_accuracy={_ta}/100 — DO NOT change ANY tool-calling or order/reservation commit logic. It is already excellent. Changes to tool calls WILL regress this metric."

        prompt = f"""You are a senior Python engineer specializing in German restaurant voice agent pipelines.
Your task: fix the code so the bot passes the scenario batch {batch_key or '(unknown)'}.
{_near_miss_warning}{_tool_lock}
CURRENT COMPOSITE SCORE: {composite:.1f}/100  (target: ≥80)

METRIC SCORES (with weights):
  tool_accuracy:  {_ta}/100  [weight 40%]  ← HIGHEST PRIORITY if < 70
  flow:           {_fl}/100  [weight 30%]
  linguistic:     {metric_scores.get('linguistic', 0)}/100  [weight 15%]
  deterministic:  {metric_scores.get('deterministic', 0)}/100  [weight 15%]

GROK AUDITOR IMPROVEMENTS NEEDED:
{improvements}

TOOL ANALYSIS:
{tool_analysis}
{achtung_block}{loops_block}
FAILED TOOL CALLS:
{json.dumps(failed_tools[:5], indent=2, ensure_ascii=False) if failed_tools else "None"}

CONVERSATION ISSUES:
{json.dumps(conv_issues[:5], indent=2, ensure_ascii=False) if conv_issues else "None"}
{web_research_block}{known_issues_block}{history_block}{call_reports_block}
FULL SOURCE CODE (verbatim — your old_code MUST be an exact substring of the file shown):
{codebase_context}

═══════════════════════════════════════════════════════════════════════
STRICT RULES — READ BEFORE GENERATING:
═══════════════════════════════════════════════════════════════════════
0. SIZE CONSTRAINT (MANDATORY — violations cause regression):
   - Score ≥ 70 (NEAR-MISS): MAX 1 fix, max 10 lines total. No new functions.
   - Score 50-69: MAX 2 fixes, max 30 lines per fix.
   - Score < 50: MAX 3 fixes, max 50 lines per fix.
   See HAIKU_REGRESSION_001 in known issues — large changes always regress near-miss batches.

1. STRATEGY by score:
   - tool_accuracy < 60: Fix tool-firing logic in v4_pipeline.py or context_doc_builder.py.
     Check COMMIT_TOOLS_REQUIRED_SLOTS — phone_number must NOT be required for create_order.
     Check intent routing — ensure ORDER/RESERVATION intents reach commit gate.
   - flow < 40 + BOT_LOOP flag: Fix loop in v4_pipeline.py dup-utterance or slot-ask handler.
     Add pickup detection before phone request.
   - deterministic < 50 + NAME_FALSCH/TELEFON_FALSCH: Fix extraction in conversation_state.py.
     Reject German day/month names as customer_name. Validate phone ≥7 digits.
   - No tools for complaint/refund/escalation: Add intent detection + tool routing in v4_pipeline.py.
   - Bot silent after greeting: Add FAQ fallback for unknown intents in faq.py.

2. Generate 2–5 FOCUSED fixes. Target the metric with the largest weight × deficit first.

3. EXACT SUBSTRING RULE: "old_code" MUST be a character-for-character match of text from
   the file shown above. Copy it exactly. If you cannot find the exact text, use a shorter
   unique excerpt. NEVER invent or paraphrase code.

4. "new_code" replaces "old_code" entirely. Match indentation exactly.

5. Python 3.12+ scoping: NEVER assign to a variable inside a function that has a module-level
   import with the same name. Use module-level imports or different local variable names.

6. Do NOT change test/validation files (scenario_generator.py, grok_auditor_integration.py, etc.)

7. Respond with ONLY valid JSON — no markdown fences, no explanations outside the JSON.

JSON schema:
{{
  "fixes": [
    {{
      "file": "server/brain/v4_pipeline.py",
      "line": 450,
      "issue": "Phone number loop: dup-utterance handler asks for phone even on pickup orders",
      "old_code": "<EXACT verbatim substring from the file shown above>",
      "new_code": "<replacement — keep indentation>",
      "reason": "Pickup orders don't need phone. Skip phone ask if pickup keywords present.",
      "outcome": null
    }}
  ],
  "summary": "What was fixed and why — max 3 sentences",
  "priority": "high"
}}"""

        # ── Call model cascade ────────────────────────────────────────────────
        context_chars = len(prompt)
        raw = await self._generate_with_cascade(prompt, context_chars)
        elapsed = time.time() - t0
        logger.info("[fixer] Model call complete in %.1fs", elapsed)

        if not raw:
            logger.error("[fixer] All models returned empty response")
            return self._default_fixes()

        logger.debug("[fixer] Raw response (%d chars): %.300s", len(raw), raw)

        cleaned = _strip_markdown(raw)
        try:
            fix_plan = json.loads(cleaned)
        except json.JSONDecodeError as json_err:
            logger.warning("[fixer] Primary JSON parse failed (%s) — attempting recovery", json_err)
            last_brace = cleaned.rfind("}")
            if last_brace > 0:
                try:
                    fix_plan = json.loads(cleaned[:last_brace + 1])
                    logger.info("[fixer] Recovered JSON from truncated response")
                except json.JSONDecodeError:
                    logger.error("[fixer] JSON recovery failed — full text:\n%s", cleaned[:2000])
                    return self._default_fixes()
            else:
                logger.error("[fixer] No closing brace — full text:\n%s", cleaned[:2000])
                return self._default_fixes()

        n = len(fix_plan.get("fixes", []))
        logger.info("[fixer] Generated %d fixes (priority=%s, model=%s)",
                    n, fix_plan.get("priority", "?"), self.model)

        # Hard-enforce fix count based on composite score to prevent regressions.
        # Haiku often ignores the SIZE CONSTRAINT in the prompt — so we enforce it here.
        _composite_now = grok_report.get("composite_score", 0)
        if _composite_now >= 70:
            _max_fixes = 1
        elif _composite_now >= 55:
            _max_fixes = 2
        elif _composite_now >= 40:
            _max_fixes = 3
        else:
            _max_fixes = 4
        if n > _max_fixes:
            fix_plan["fixes"] = fix_plan["fixes"][:_max_fixes]
            logger.warning("[fixer] Truncated fixes from %d → %d (composite=%.1f, max=%d)",
                           n, _max_fixes, _composite_now, _max_fixes)

        return fix_plan

    def _default_fixes(self) -> Dict[str, Any]:
        return {"fixes": [], "summary": "Fix generation failed", "priority": "low"}
