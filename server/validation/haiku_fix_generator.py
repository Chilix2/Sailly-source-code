"""
Haiku 4.5 Fix Generator — Receives Grok audit + Google call metrics, generates targeted code fixes.

Key design principle:
  - Reads full detailed call reports via build_detailed_call_report (all 9 sections: overview, health, flags, per-turn, timeline, transcripts, tools, session, observations)
  - Also reads actual source files before generating fixes
  - Injects verbatim snippets so old_code can be an exact substring of the real file
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Anthropic Messages API — Claude Sonnet 4.6 for code reasoning (1M context window)
DEFAULT_HAIKU_FIX_MODEL = "claude-sonnet-4-6"

# Files to always load for context (relative to project root)
# These are the ACTUAL BUG SURFACE: state management, slot extraction, deterministic clarify.
# Skip test harness (scenario_generator) — that's not production code.
_CONTEXT_FILES: List[Tuple[str, int, int]] = [
    ("server/brain/v4_pipeline.py", 250, 660),        # Deterministic clarify gate + state machine
    ("server/brain/conversation_state.py", 100, 250), # Slot extractors (name, date, time, party_size)
    ("server/brain/context_doc_builder.py", 1, 150),  # Missing-slot computation
    ("server/brain/layer1/nodes/reservation.py", 1, 100),
    ("server/brain/adk_turn_processor.py", 1, 80),
]

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_file_snippet(rel_path: str, start_line: int = 1, end_line: int = 100) -> str:
    """Read lines [start_line..end_line] from a project file. Returns empty string if missing."""
    full_path = _PROJECT_ROOT / rel_path
    try:
        lines = full_path.read_text(encoding="utf-8").splitlines()
        selected = lines[start_line - 1 : end_line]
        return "\n".join(selected)
    except Exception as exc:
        logger.debug("[haiku] Could not read %s: %s", rel_path, exc)
        return ""


def _gather_codebase_context(metric_scores: Dict[str, float]) -> str:
    """
    Build a context block with verbatim file snippets.
    Prioritises files based on which metrics are weakest.
    """
    tool_acc = metric_scores.get("tool_accuracy", 100)
    deterministic = metric_scores.get("deterministic", 100)

    # Always load these
    snippets = []
    for rel_path, start, end in _CONTEXT_FILES:
        content = _read_file_snippet(rel_path, start, end)
        if content:
            snippets.append(f"--- {rel_path} (lines {start}–{end}) ---\n{content}")

    # If tool accuracy is low, also load the tool_calling layer
    if tool_acc < 70:
        extra = _read_file_snippet("server/brain/layer2/tool_calling.py", 1, 120)
        if extra:
            snippets.append("--- server/brain/layer2/tool_calling.py (lines 1–120) ---\n" + extra)

    # If deterministic score is low, load the system_prompt
    if deterministic < 60:
        extra = _read_file_snippet("server/brain/layer2/system_prompt.py", 1, 100)
        if extra:
            snippets.append("--- server/brain/layer2/system_prompt.py (lines 1–100) ---\n" + extra)

    if not snippets:
        return "(No source files could be read from project root)"

    return "\n\n".join(snippets)


def _strip_markdown(text: str) -> str:
    """Strip markdown code fences (with or without language tag) and extra whitespace."""
    text = text.strip()
    # Remove opening fence (including language tag like ```json or ```)
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    # Remove closing fence (anywhere in text)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    # Also handle case where closing fence is in the middle (malformed)
    text = re.sub(r"```.*", "", text, flags=re.DOTALL)
    return text.strip()


class HaikuFixGenerator:
    """Generates targeted code fixes using Claude Haiku 4.5."""

    def __init__(self):
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise RuntimeError("pip install anthropic") from exc

        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        self.client = AsyncAnthropic(api_key=key)
        self.model = os.environ.get("HAIKU_FIX_MODEL", DEFAULT_HAIKU_FIX_MODEL)
        logger.info("[haiku] Anthropic fix model: %s", self.model)

    async def _fetch_call_reports(self, call_sids: List[str]) -> str:
        """
        Fetch full detailed call analysis reports (all 9 sections) for each call_sid.

        Uses build_detailed_call_report from detailed_builder — queries Postgres
        for transcripts, turn metrics, tool calls, session blob, and Achtung flags.

        Returns a combined markdown string (up to 3 calls, ~12 000 chars each).
        """
        try:
            from server.call_report.detailed_builder import build_detailed_call_report
        except ImportError as exc:
            logger.warning("[haiku] Could not import build_detailed_call_report: %s", exc)
            return ""

        reports: List[str] = []
        for sid in call_sids[:3]:
            try:
                md = await build_detailed_call_report(sid)
                reports.append(md[:12_000])
                logger.info("[haiku] Fetched detailed call report for %s (%d chars)", sid, len(md))
            except Exception as exc:
                logger.warning("[haiku] Could not fetch report for %s: %s", sid, exc)

        if not reports:
            return ""
        return "\n\n---\n\n".join(reports)

    async def generate_fixes(
        self,
        grok_report: Dict[str, Any],
        call_metrics: Dict[str, Any],
        call_sids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate code fixes based on Grok audit + call metrics + full call reports.

        Args:
            grok_report:  Grok audit result dict
            call_metrics: Structured metrics from PostgresMetricsFetcher
            call_sids:    List of call_sid strings — used to fetch full detailed markdown
                          call reports via build_detailed_call_report (9-section analysis)

        Returns:
            {
                "fixes": [
                    {
                        "file": "server/brain/...",
                        "line": N,
                        "issue": "...",
                        "old_code": "<EXACT verbatim substring from file>",
                        "new_code": "...",
                        "reason": "..."
                    }
                ],
                "summary": "...",
                "priority": "high|medium|low"
            }
        """
        logger.info("[haiku] Generating fixes from Grok report + %d call_sids", len(call_sids or []))

        metric_scores = grok_report.get("metric_scores", {})
        composite = grok_report.get("composite_score", 0)
        improvements = grok_report.get("improvements", "")
        tool_analysis = grok_report.get("tool_analysis", "")
        achtung_flags = grok_report.get("achtung_flags", [])

        failed_tools = call_metrics.get("failed_tool_calls", [])
        conversation_issues = call_metrics.get("conversation_issues", [])
        loop_detections = call_metrics.get("loop_detections", [])

        # ── Full call reports (primary diagnostic input) ─────────────────
        call_reports_block = ""
        if call_sids:
            reports_md = await self._fetch_call_reports(call_sids)
            if reports_md:
                call_reports_block = f"\nFULL CALL REPORTS (per-turn breakdown, tool calls, transcripts, flags):\n{reports_md}\n"
                logger.info("[haiku] Injected %d call report(s) into prompt", len(call_sids[:3]))
            else:
                logger.warning("[haiku] No call reports fetched — falling back to raw transcript data")

        # ── Codebase source context ──────────────────────────────────────
        codebase_context = _gather_codebase_context(metric_scores)

        achtung_block = ""
        if achtung_flags:
            flags_text = "\n".join(f"  - {f.get('call_sid','')} turn {f.get('turn','?')}: {f.get('flag','')[:150]}" for f in achtung_flags)
            achtung_block = f"\nCONFIRMED CALLER-BOT ERROR FLAGS (MUST be fixed):\n{flags_text}\n"

        loops_block = ""
        if loop_detections:
            loops_block = f"\nBOT LOOPS DETECTED ({len(loop_detections)}):\n" + json.dumps(loop_detections[:5], indent=2) + "\n"

        prompt = f"""You are a senior Python voice-agent engineer. Based on the audit below and the ACTUAL source code, generate fixes.

COMPOSITE SCORE: {composite:.1f}/100

METRIC SCORES:
  tool_accuracy:  {metric_scores.get('tool_accuracy', 0)}/100  (weight 40%)
  flow:           {metric_scores.get('flow', 0)}/100  (weight 30%)
  linguistic:     {metric_scores.get('linguistic', 0)}/100  (weight 15%)
  deterministic:  {metric_scores.get('deterministic', 0)}/100  (weight 15%)

IMPROVEMENTS NEEDED:
{improvements}

TOOL ANALYSIS:
{tool_analysis}
{achtung_block}{loops_block}
FAILED TOOL CALLS:
{json.dumps(failed_tools[:5], indent=2, ensure_ascii=False) if failed_tools else "None"}

CONVERSATION ISSUES:
{json.dumps(conversation_issues[:5], indent=2, ensure_ascii=False) if conversation_issues else "None"}
{call_reports_block}
RELEVANT SOURCE CODE (verbatim — your old_code must be an EXACT substring from these files):
{codebase_context}

RULES FOR YOUR RESPONSE:
1. STRATEGY — determined by issue type, NOT score:
   - If tool_analysis mentions "loop", "missing check", "state", "slot", "advance", "not progressing": SURGICAL FIX REQUIRED.
     Target: server/brain/v4_pipeline.py or server/brain/conversation_state.py (layer1 state machine).
     Do NOT edit system_prompt.py. The bug is architectural, not in phrasing.
   - If tool_analysis mentions "tone", "wording", "register", "phrasing", "natural", "formal": PROMPT EDIT ALLOWED.
     Target: layer2/system_prompt.py is the right place.
   - Default: Surgical first. Always prefer code fixes that fix the root cause over prompt tweaks.
2. Generate 2–5 focused fixes. Target the lowest-scoring metrics first.
3. For each fix, "old_code" MUST be an EXACT verbatim substring from the file shown above.
   Do NOT invent or paraphrase code. Copy it character-for-character.
4. "new_code" replaces "old_code" entirely. Keep indentation consistent.
5. Only fix what is clearly wrong. Do not refactor healthy code.
6. Respond with valid JSON only (no markdown fences).

JSON format:
{{
  "fixes": [
    {{
      "file": "server/brain/layer2/system_prompt.py",
      "line": 42,
      "issue": "System prompt needs to emphasize: don't repeat questions, validate dates, confirm before executing",
      "old_code": "<exact text from the file above>",
      "new_code": "<replacement text with clearer behavioral instructions>",
      "reason": "Improves flow and deterministic correctness"
    }}
  ],
  "summary": "2-sentence summary of what was fixed",
  "priority": "high"
}}"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=20000,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text if response.content else ""
            logger.debug("[haiku] Raw response (%d chars): %.200s", len(raw), raw)

            cleaned = _strip_markdown(raw)
            
            # Try direct parse first
            try:
                fix_plan = json.loads(cleaned)
            except json.JSONDecodeError as json_err:
                # Try to find the last complete JSON object if truncated
                logger.warning("[haiku] Primary JSON parse failed, attempting recovery: %s", json_err)
                
                # Find last '}' character and try truncating there
                last_brace = cleaned.rfind('}')
                if last_brace > 0:
                    try:
                        fix_plan = json.loads(cleaned[:last_brace + 1])
                        logger.info("[haiku] Recovered JSON from truncated response")
                    except json.JSONDecodeError:
                        logger.error(
                            "[haiku] JSON parse failed even after truncation (%s) — full text:\n%s",
                            json_err, cleaned[:1500]
                        )
                        return self._default_fixes()
                else:
                    logger.error(
                        "[haiku] JSON parse failed (%s) — no closing brace found. Full text:\n%s",
                        json_err, cleaned[:1500]
                    )
                    return self._default_fixes()
            
            n_fixes = len(fix_plan.get("fixes", []))
            logger.info("[haiku] Generated %d fixes (priority=%s)", n_fixes, fix_plan.get("priority", "?"))
            return fix_plan

        except json.JSONDecodeError as exc:
            logger.error("[haiku] JSON parse failed: %s  raw=%.200s", exc, raw if 'raw' in dir() else '')
            return self._default_fixes()
        except Exception as exc:
            logger.error("[haiku] generate_fixes failed: %s", exc)
            return self._default_fixes()

    def _default_fixes(self) -> Dict[str, Any]:
        return {"fixes": [], "summary": "Fix generation failed", "priority": "low"}
