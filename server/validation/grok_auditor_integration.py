"""
Grok Auditor Integration — Score scenarios on tool accuracy, flow, linguistic quality,
deterministic correctness.

Scoring Model (Composite):
  - Tool Calling Accuracy: 40%  (primary focus)
  - Conversation Flow:     30%
  - Linguistic Quality:    15%
  - Deterministic Correct: 15%

If [Achtung Sailly:] flags are present, deterministic + flow are capped ≤ 40.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences that Grok-3-mini sometimes adds."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


class GrokAuditor:
    """Scores scenario batches using Grok API (grok-3-mini)."""

    METRIC_WEIGHTS = {
        "tool_accuracy": 0.40,
        "flow": 0.30,
        "linguistic": 0.15,
        "deterministic": 0.15,
    }

    def __init__(self):
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("pip install openai") from exc

        key = os.environ.get("XAI_API_KEY")
        if not key:
            raise RuntimeError("XAI_API_KEY not set")

        self.client = AsyncOpenAI(api_key=key, base_url="https://api.x.ai/v1")

    async def audit_scenario_batch(
        self,
        call_sids: List[str],
        batch_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Audit a batch of scenarios.

        Args:
            call_sids: List of call_sid strings
            batch_metrics: Pre-fetched metrics dict from PostgresMetricsFetcher.fetch_batch_metrics()
                           (if None, fetches internally)

        Returns:
            {
                "call_sids": [...],
                "metric_scores": {"tool_accuracy": X, "flow": X, "linguistic": X, "deterministic": X},
                "composite_score": float,
                "improvements": str,
                "tool_analysis": str,
                "achtung_flags": [...],
            }
        """
        logger.info("[grok] Auditing %d call_sids", len(call_sids))

        # Use pre-fetched metrics if provided, else fetch now
        if batch_metrics is None:
            from server.validation.postgres_metrics_fetcher import PostgresMetricsFetcher
            fetcher = PostgresMetricsFetcher()
            batch_metrics = await fetcher.fetch_batch_metrics(call_sids)

        transcripts = batch_metrics.get("transcripts", [])
        failed_tools = batch_metrics.get("failed_tool_calls", [])
        achtung_flags = batch_metrics.get("achtung_flags", [])
        loop_detections = batch_metrics.get("loop_detections", [])
        conv_issues = batch_metrics.get("conversation_issues", [])

        if not transcripts:
            logger.warning("[grok] No transcripts available — returning default scores")
            return self._default_report(call_sids)

        # Build sections
        transcript_block = "\n\n".join(transcripts[:5])  # up to 5 calls

        failed_tools_block = (
            json.dumps(failed_tools[:8], indent=2, ensure_ascii=False)
            if failed_tools else "None"
        )

        achtung_block = ""
        if achtung_flags:
            flags_text = "\n".join(f"  - {f['call_sid']} turn {f['turn']}: {f['flag'][:150]}" for f in achtung_flags)
            achtung_block = (
                f"\nCONFIRMED CALLER-BOT ERROR FLAGS ({len(achtung_flags)} total — highest priority):\n"
                f"{flags_text}\n"
                "IMPORTANT: Each [Achtung Sailly:] flag = a confirmed factual/logical error by the bot.\n"
                "Score 'deterministic' ≤ 40 and 'flow' ≤ 50 whenever these flags are present.\n"
            )

        loop_block = ""
        if loop_detections:
            loop_text = "\n".join(f"  - {l['call_sid']} turn {l['turn']}: repeated '{l['repeated_text']}'" for l in loop_detections)
            loop_block = f"\nBOT LOOP DETECTIONS ({len(loop_detections)}):\n{loop_text}\nScore 'flow' ≤ 30 when loops present.\n"

        prompt = f"""You are a German-language voice agent quality auditor for DOBOO Korean restaurant.
Audit the following {len(call_sids)} call(s) and score each metric 0-100:

1. tool_accuracy (0-100, weight 40%): Did the right tools fire at the right time? No spurious/missing calls?
2. flow (0-100, weight 30%): Natural conversation progression? No loops? Order/reservation readback present?
3. linguistic (0-100, weight 15%): Natural German, correct Sie-form, appropriate tone?
4. deterministic (0-100, weight 15%): Correct dates/times, correct prices, no factual errors, matches customer request?
{achtung_block}{loop_block}
CALL TRANSCRIPTS:
{transcript_block}

FAILED TOOL CALLS:
{failed_tools_block}

CONVERSATION ISSUES: {json.dumps(conv_issues[:5], ensure_ascii=False) if conv_issues else "None"}

Respond with valid JSON only (no markdown fences):
{{
  "tool_accuracy": <0-100>,
  "flow": <0-100>,
  "linguistic": <0-100>,
  "deterministic": <0-100>,
  "improvements": "<top 3-5 specific improvements needed>",
  "tool_analysis": "<details on tool calling: what fired, what should have fired differently>"
}}"""

        try:
            response = await self.client.chat.completions.create(
                model="grok-3-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.0,
            )

            raw = response.choices[0].message.content.strip()
            logger.debug("[grok] Raw response (%d chars): %s", len(raw), raw[:200])

            # Strip markdown fences Grok sometimes adds
            cleaned = _strip_markdown_fences(raw)
            scores = json.loads(cleaned)

            composite = sum(
                scores.get(metric, 0) * weight
                for metric, weight in self.METRIC_WEIGHTS.items()
            )

            report = {
                "call_sids": call_sids,
                "metric_scores": {
                    "tool_accuracy": scores.get("tool_accuracy", 0),
                    "flow": scores.get("flow", 0),
                    "linguistic": scores.get("linguistic", 0),
                    "deterministic": scores.get("deterministic", 0),
                },
                "composite_score": round(composite, 1),
                "improvements": scores.get("improvements", ""),
                "tool_analysis": scores.get("tool_analysis", ""),
                "achtung_flags": achtung_flags,
            }

            logger.info(
                "[grok] Audit done: composite=%.1f  tool=%d  flow=%d  linguistic=%d  deterministic=%d  flags=%d",
                composite,
                scores.get("tool_accuracy", 0),
                scores.get("flow", 0),
                scores.get("linguistic", 0),
                scores.get("deterministic", 0),
                len(achtung_flags),
            )
            return report

        except json.JSONDecodeError as exc:
            logger.error("[grok] JSON parse failed (raw=%r): %s", raw[:300], exc)
            return self._default_report(call_sids)
        except Exception as exc:
            logger.error("[grok] audit_scenario_batch failed: %s", exc)
            return self._default_report(call_sids)

    def _default_report(self, call_sids: List[str]) -> Dict[str, Any]:
        """Fallback when audit cannot run — explicitly marked as a failure, not neutral."""
        logger.warning("[grok] Using default report (audit unavailable) — scores are NOT real")
        return {
            "call_sids": call_sids,
            "metric_scores": {
                "tool_accuracy": 0,
                "flow": 0,
                "linguistic": 0,
                "deterministic": 0,
            },
            "composite_score": 0.0,
            "improvements": "AUDIT FAILED — transcript fetch or Grok call failed. Check logs.",
            "tool_analysis": "",
            "achtung_flags": [],
        }
