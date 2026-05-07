"""
Postgres Metrics Fetcher — Fetches call transcripts, tool calls, and Achtung flags from Postgres.

Actual schema (confirmed from brain_service.py + text_mode_runner.py):
  google_transcripts: call_sid, role, content, turn_number, timestamp
  google_tool_calls:  call_sid, tool_name, success, error_message, turn_number, arguments, result_summary
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PostgresMetricsFetcher:
    """Fetches call transcripts, tool data, and caller-bot flags from Postgres."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.environ.get("DATABASE_URL", "")
        if not self.db_url:
            logger.warning("[postgres] DATABASE_URL not set — metrics fetching disabled")

    async def fetch_transcript(self, call_sid: str) -> Optional[str]:
        """
        Fetch formatted call transcript from google_transcripts.
        Returns None on error (logs warning).
        """
        if not self.db_url:
            return None
        try:
            import asyncpg
            conn = await asyncpg.connect(self.db_url)
            rows = await conn.fetch(
                """
                SELECT turn_number, role, content
                FROM google_transcripts
                WHERE call_sid = $1
                ORDER BY turn_number ASC
                """,
                call_sid,
            )
            await conn.close()

            if not rows:
                logger.warning("[postgres] No transcript rows for %s", call_sid)
                return None

            lines = []
            for row in rows:
                role_label = "Bot" if row["role"] in ("assistant", "agent") else "User"
                lines.append(f"[Turn {row['turn_number']}] {role_label}: {row['content']}")

            transcript = "\n".join(lines)
            logger.debug("[postgres] Fetched transcript for %s (%d turns)", call_sid, len(rows))
            return transcript

        except Exception as exc:
            logger.warning("[postgres] fetch_transcript(%s) failed: %s", call_sid, exc)
            return None

    async def fetch_batch_metrics(self, call_sids: List[str]) -> Dict[str, Any]:
        """
        Fetch enriched metrics for a batch of calls including:
        - Full transcripts (role + content)
        - Tool call results (success/failure)
        - [Achtung Sailly:] error flags injected by the caller bot
        """
        if not self.db_url:
            logger.warning("[postgres] No DATABASE_URL — returning empty metrics")
            return self._empty_metrics()

        try:
            import asyncpg
            conn = await asyncpg.connect(self.db_url)

            failed_tool_calls: List[Dict] = []
            conversation_issues: List[Dict] = []
            achtung_flags: List[Dict] = []
            loop_detections: List[Dict] = []
            transcripts_by_call: Dict[str, List[Dict]] = {}

            for call_sid in call_sids:
                # ── Transcripts ────────────────────────────────────────────
                try:
                    transcript_rows = await conn.fetch(
                        """
                        SELECT turn_number, role, content
                        FROM google_transcripts
                        WHERE call_sid = $1
                        ORDER BY turn_number ASC
                        """,
                        call_sid,
                    )
                    turns: List[Dict] = [
                        {
                            "turn": r["turn_number"],
                            "role": r["role"],
                            "content": r["content"],
                        }
                        for r in transcript_rows
                    ]
                    transcripts_by_call[call_sid] = turns

                    # Extract [Achtung Sailly:] flags from user/caller turns
                    for t in turns:
                        if t["role"] not in ("assistant", "agent"):
                            if "[achtung sailly" in t["content"].lower():
                                achtung_flags.append({
                                    "call_sid": call_sid,
                                    "turn": t["turn"],
                                    "flag": t["content"],
                                })

                    # Detect bot loops: same assistant content repeated consecutively
                    bot_turns = [t for t in turns if t["role"] in ("assistant", "agent")]
                    for i in range(1, len(bot_turns)):
                        prev = bot_turns[i - 1]["content"].strip()
                        curr = bot_turns[i]["content"].strip()
                        if prev and curr and prev == curr:
                            loop_detections.append({
                                "call_sid": call_sid,
                                "turn": bot_turns[i]["turn"],
                                "repeated_text": curr[:100],
                            })

                    # Short / empty bot responses
                    for t in turns:
                        if t["role"] in ("assistant", "agent") and len(t["content"].strip()) < 8:
                            conversation_issues.append({
                                "call_sid": call_sid,
                                "turn": t["turn"],
                                "issue": f"Very short bot response: {t['content']!r}",
                            })

                except Exception as exc:
                    logger.warning("[postgres] transcript fetch failed for %s: %s", call_sid, exc)

                # ── Tool calls ─────────────────────────────────────────────
                try:
                    tool_rows = await conn.fetch(
                        """
                        SELECT tool_name, success, error_message, turn_number, arguments
                        FROM google_tool_calls
                        WHERE call_sid = $1
                        ORDER BY turn_number ASC
                        """,
                        call_sid,
                    )
                    for r in tool_rows:
                        if not r["success"]:
                            failed_tool_calls.append({
                                "call_sid": call_sid,
                                "turn": r["turn_number"],
                                "tool": r["tool_name"],
                                "error": (r["error_message"] or "")[:120],
                            })
                except Exception as exc:
                    logger.warning("[postgres] tool_calls fetch failed for %s: %s", call_sid, exc)

            await conn.close()

            # Build per-call transcript summaries for Grok
            formatted_transcripts = []
            for call_sid, turns in transcripts_by_call.items():
                lines = [f"  [T{t['turn']}] {'Bot' if t['role'] in ('assistant','agent') else 'User'}: {t['content']}" for t in turns]
                formatted_transcripts.append(f"Call {call_sid}:\n" + "\n".join(lines))

            return {
                "total_calls": len(call_sids),
                "transcripts": formatted_transcripts,
                "failed_tool_calls": failed_tool_calls[:15],
                "conversation_issues": conversation_issues[:15],
                "achtung_flags": achtung_flags[:20],
                "loop_detections": loop_detections[:10],
            }

        except Exception as exc:
            logger.error("[postgres] fetch_batch_metrics failed: %s", exc)
            return self._empty_metrics()

    def _empty_metrics(self) -> Dict[str, Any]:
        return {
            "total_calls": 0,
            "transcripts": [],
            "failed_tool_calls": [],
            "conversation_issues": [],
            "achtung_flags": [],
            "loop_detections": [],
        }
