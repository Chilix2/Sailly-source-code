"""
Layer 1 — Headless text-mode turn runner.

Used by /ws/demo_text for regression testing without audio.

Protocol (WebSocket JSON messages):

  Client → Server:
    {"type": "user_text", "text": "Ich möchte Bulgogi bestellen"}
    {"type": "end_session"}

  Server → Client (per turn):
    {"type": "session_init", "call_sid": "..."}
    {"type": "bot_text", "text": "Guten Tag, wie kann ich helfen?",
                          "tools_fired": [...], "turn_idx": 0}
    {"type": "tool_event", "name": "create_order", "args": {...}, "turn_idx": 1}
    {"type": "error", "message": "..."}
    {"type": "session_end", "turn_count": N}

This runner is TEST ONLY — it bypasses audio, TTS, and STT entirely.
The LLM path (brain_service.py → adk_turn_processor.py) is exercised in full.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Maximum time to wait for the LLM to produce a response for one turn
_TURN_TIMEOUT_S = 30.0

# Sentinel to signal end-of-session
_END_SESSION = object()


class TextModeRunner:
    """Runs one headless session over a WebSocket.

    The caller drives the turn loop by sending user_text messages.
    The runner:
      1. Feeds text to the LLM (via ADKTurnProcessor)
      2. Collects the text response (strip TTS markup)
      3. Captures any tool calls that fired
      4. Returns the result as a bot_text message
    """

    def __init__(self, websocket, tenant_id: str = "doboo"):
        self._ws = websocket
        self._tenant_id = tenant_id
        self._call_sid = f"headless-{uuid.uuid4().hex[:8]}"
        self._turn_idx = 0
        self._processor = None
        self._started_at = datetime.now(timezone.utc)
        self._transcripts: list[dict] = []
        self._tool_calls: list[dict] = []
        self._turn_metrics: list[dict] = []  # for google_turn_metrics
        self._should_end: bool = False       # set True when bot fires end_call
        self._consecutive_hard_fails: int = 0  # stop loop on repeated pipeline errors

    async def run(self) -> None:
        """Main loop — runs until session ends, WebSocket disconnects, or bot fires end_call."""
        try:
            await self._ws.send_json({
                "type": "session_init",
                "call_sid": self._call_sid,
            })
            await self._init_processor()

            while True:
                msg = await asyncio.wait_for(self._ws.receive_json(), timeout=120.0)
                if msg.get("type") == "end_session":
                    break
                if msg.get("type") == "user_text":
                    text = msg.get("text", "").strip()
                    if text:
                        await self._handle_turn(text)
                        if self._should_end:
                            logger.info(f"[TextMode] Bot requested end_call — closing session")
                            break

        except asyncio.TimeoutError:
            await self._ws.send_json({"type": "error", "message": "session idle timeout"})
        except Exception as exc:
            logger.warning(f"[TextMode] session error: {exc}", exc_info=True)
            try:
                await self._ws.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass
        finally:
            try:
                await self._ws.send_json({
                    "type": "session_end",
                    "turn_count": self._turn_idx,
                })
            except Exception:
                pass
            
            # Write call record to Postgres
            try:
                logger.info(f"[TextMode] Writing call to Postgres: {len(self._transcripts)} transcripts, {len(self._tool_calls)} tools")
                await self._write_call_to_postgres()
                logger.info(f"[TextMode] Successfully wrote call to Postgres")
            except Exception as db_err:
                logger.warning(f"[TextMode] Failed to write call to Postgres: {db_err}")

    async def _init_processor(self) -> None:
        """Lazy-initialize the ADKTurnProcessor for this session."""
        from server.brain.v4_turn_processor import V4TurnProcessor as ADKTurnProcessor

        # ADKTurnProcessor expects: (tenant_id, call_sid, session, caller_phone="", filler_cb=None)
        # In text mode, session is None (no Twilio/Pipecat session object)
        self._processor = ADKTurnProcessor(
            tenant_id=self._tenant_id,
            call_sid=self._call_sid,
            session=None,  # No audio session in headless mode
            caller_phone="",  # No phone in text mode
            filler_cb=None,  # No filler TTS in text mode
        )
        logger.info(f"[TextMode] processor ready (call_sid={self._call_sid})")

    async def _handle_turn(self, user_text: str) -> None:
        """Process one user utterance and send bot_text message."""
        if self._processor is None:
            await self._ws.send_json({"type": "error", "message": "processor not initialized"})
            return

        tools_fired: List[Dict[str, Any]] = []
        bot_text = ""
        turn_start = time.monotonic()

        # Record user turn
        now = datetime.now(timezone.utc)
        self._transcripts.append({
            "role": "user",
            "text": user_text,
            "timestamp": now.isoformat()
        })

        try:
            result = await asyncio.wait_for(
                self._processor.process_turn(user_text),
                timeout=_TURN_TIMEOUT_S,
            )
            llm_ms = int((time.monotonic() - turn_start) * 1000)

            if hasattr(result, 'clean_text'):
                bot_text = result.clean_text or ""
                tools_fired = [{"name": t} for t in (result.tools_called or [])]
                end_reason = getattr(result, 'end_reason', '')
                # Respect the bot's end-call signal
                if getattr(result, 'should_end', False):
                    self._should_end = True
                    logger.info(f"[TextMode] TurnResult.should_end=True (reason={end_reason})")
                # Hard-fail safety: stop after 3 consecutive pipeline errors
                if end_reason == "v4_hard_fail":
                    self._consecutive_hard_fails += 1
                    logger.warning(
                        f"[TextMode] v4_hard_fail #{self._consecutive_hard_fails} "
                        f"on turn {self._turn_idx}"
                    )
                    if self._consecutive_hard_fails >= 3:
                        self._should_end = True
                        logger.error(
                            f"[TextMode] 3 consecutive v4_hard_fails — ending session early"
                        )
                else:
                    self._consecutive_hard_fails = 0
            else:
                bot_text, tools_fired = _extract_tools_from_text(str(result) or "")

            # Detect end_call tool even if should_end wasn't set
            tool_names = [t["name"] for t in tools_fired]
            if "end_call" in tool_names:
                self._should_end = True
                logger.info(f"[TextMode] end_call tool detected — will close after this turn")

            # Record bot turn and tools
            bot_now = datetime.now(timezone.utc)
            self._transcripts.append({
                "role": "assistant",
                "text": bot_text,
                "timestamp": bot_now.isoformat()
            })
            for tool in tools_fired:
                self._tool_calls.append({
                    "tool": tool["name"],
                    "name": tool["name"]
                })

            # Record basic turn metrics (for google_turn_metrics)
            self._turn_metrics.append({
                "turn_number": self._turn_idx,
                "llm_latency_ms": llm_ms,
                "total_latency_ms": llm_ms,  # no STT/TTS in headless
                "tools_called": tool_names,
                "bot_text_len": len(bot_text),
                "timestamp": bot_now.isoformat(),
            })

            # Emit any tool events
            for tool in tools_fired:
                await self._ws.send_json({
                    "type": "tool_event",
                    "name": tool["name"],
                    "args": tool.get("args", {}),
                    "turn_idx": self._turn_idx,
                })

            await self._ws.send_json({
                "type": "bot_text",
                "text": bot_text,
                "tools_fired": tool_names,
                "turn_idx": self._turn_idx,
                "should_end": self._should_end,
            })

        except asyncio.TimeoutError:
            await self._ws.send_json({
                "type": "error",
                "message": f"turn {self._turn_idx} LLM timeout ({_TURN_TIMEOUT_S}s)",
                "turn_idx": self._turn_idx,
            })
        except Exception as exc:
            logger.error(f"[TextMode] turn error: {exc}", exc_info=True)
            await self._ws.send_json({
                "type": "error",
                "message": str(exc),
                "turn_idx": self._turn_idx,
            })
        finally:
            self._turn_idx += 1

    async def _write_call_to_postgres(self) -> None:
        """Write call record to Postgres, queryable by call_sid (matches builder.py)."""
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.debug("[TextMode] No DATABASE_URL — skipping Postgres write")
            return

        try:
            import asyncpg

            ended_at = datetime.now(timezone.utc)
            duration_secs = int((ended_at - self._started_at).total_seconds())
            n_user_turns = len([t for t in self._transcripts if t.get("role") == "user"])

            session_data = {
                "call_sid": self._call_sid,
                "tenant_id": self._tenant_id,
                "tenant": self._tenant_id,
                "from_number": "script_runner",
                "started_at": self._started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "duration_secs": duration_secs,
                "transcripts": self._transcripts,
                "tool_calls": self._tool_calls,
                "state": {},
            }

            conn = await asyncpg.connect(db_url)
            try:
                # Upsert google_calls — call_sid has a UNIQUE constraint
                call_row = await conn.fetchrow("""
                    INSERT INTO google_calls (
                        call_sid, caller_number, started_at, ended_at, duration_seconds,
                        total_turns, outcome, tenant_id, quality_score, session_data,
                        created_at, was_escalated
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (call_sid) DO UPDATE SET
                        ended_at        = EXCLUDED.ended_at,
                        duration_seconds= EXCLUDED.duration_seconds,
                        total_turns     = EXCLUDED.total_turns,
                        outcome         = EXCLUDED.outcome,
                        session_data    = EXCLUDED.session_data
                    RETURNING id
                """,
                    self._call_sid,
                    "script_runner",
                    self._started_at,
                    ended_at,
                    duration_secs,
                    n_user_turns,
                    "completed",
                    self._tenant_id,
                    5.0,
                    json.dumps(session_data),
                    datetime.now(timezone.utc),
                    False,
                )

                if not call_row:
                    logger.warning("[TextMode] google_calls upsert returned no row")
                    return

                call_id = call_row["id"]

                # Delete stale rows so re-runs replace them cleanly
                await conn.execute(
                    "DELETE FROM google_transcripts WHERE call_sid = $1",
                    self._call_sid,
                )

                # Insert transcripts — include call_sid so builder can query by it
                for turn_idx, transcript in enumerate(self._transcripts):
                    ts_raw = transcript.get("timestamp")
                    ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(timezone.utc)
                    await conn.execute("""
                        INSERT INTO google_transcripts
                            (call_id, call_sid, turn_number, role, content, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                        call_id,
                        self._call_sid,
                        turn_idx,
                        transcript.get("role", "unknown"),
                        transcript.get("text", "") or "",
                        ts,
                    )

                # Delete and re-insert tool calls
                await conn.execute(
                    "DELETE FROM google_tool_calls WHERE call_sid = $1",
                    self._call_sid,
                )
                for tool_call in self._tool_calls:
                    await conn.execute("""
                        INSERT INTO google_tool_calls
                            (call_id, call_sid, tool_name, called_at, success)
                        VALUES ($1, $2, $3, $4, $5)
                    """,
                        call_id,
                        self._call_sid,
                        tool_call.get("name", "unknown"),
                        datetime.now(timezone.utc),
                        True,
                    )

                logger.info(
                    f"[TextMode] Postgres write OK: {self._call_sid} | "
                    f"{len(self._transcripts)} transcripts | {len(self._tool_calls)} tools"
                )

                # Write turn metrics so call analysis shows latency/tools per turn
                if self._turn_metrics:
                    # Build a transcript lookup: turn_number → (user_text, bot_text)
                    turn_texts: dict[int, tuple[str, str]] = {}
                    for m in self._turn_metrics:
                        idx = m["turn_number"]
                        user_t = ""
                        bot_t = ""
                        # transcripts are interleaved: user@2*idx, assistant@2*idx+1
                        ut_idx = idx * 2
                        bt_idx = idx * 2 + 1
                        if ut_idx < len(self._transcripts):
                            user_t = self._transcripts[ut_idx].get("text", "")
                        if bt_idx < len(self._transcripts):
                            bot_t = self._transcripts[bt_idx].get("text", "")
                        turn_texts[idx] = (user_t, bot_t)

                    await conn.execute(
                        "DELETE FROM google_turn_metrics WHERE call_sid = $1",
                        self._call_sid,
                    )
                    for m in self._turn_metrics:
                        idx = m["turn_number"]
                        user_t, bot_t = turn_texts.get(idx, ("", ""))
                        await conn.execute("""
                            INSERT INTO google_turn_metrics
                                (call_id, call_sid, turn_number, user_text, bot_text,
                                 llm_latency_ms, total_latency_ms, tools_called,
                                 tenant_id, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        """,
                            call_id,
                            self._call_sid,
                            idx,
                            user_t,
                            bot_t,
                            m.get("llm_latency_ms"),
                            m.get("total_latency_ms"),
                            json.dumps(m.get("tools_called", [])),
                            self._tenant_id,
                            datetime.now(timezone.utc),
                        )
                    logger.info(f"[TextMode] {len(self._turn_metrics)} turn_metrics rows written")
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"[TextMode] Postgres write failed: {e}", exc_info=True)



_TOOL_TAG_RE = re.compile(r"\[TOOL:([^\]]+)\]")


def _extract_tools_from_text(raw: str) -> tuple[str, List[Dict[str, Any]]]:
    """Split [TOOL:name] tags out of response text.

    Returns (clean_text, tools_list).
    """
    tools: List[Dict[str, Any]] = []
    for match in _TOOL_TAG_RE.finditer(raw):
        tools.append({"name": match.group(1), "args": {}})
    clean = _TOOL_TAG_RE.sub("", raw).strip()
    return clean, tools
