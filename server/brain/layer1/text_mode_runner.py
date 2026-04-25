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
import logging
import re
import uuid
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

    async def run(self) -> None:
        """Main loop — runs until session ends or WebSocket disconnects."""
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

    async def _init_processor(self) -> None:
        """Lazy-initialize the ADKTurnProcessor for this session."""
        from server.brain.adk_turn_processor import ADKTurnProcessor

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

        try:
            result = await asyncio.wait_for(
                self._processor.process_turn(user_text),
                timeout=_TURN_TIMEOUT_S,
            )
            # result is typically a string with optional [TOOL:...] tags
            bot_text, tools_fired = _extract_tools_from_text(result or "")

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
                "tools_fired": [t["name"] for t in tools_fired],
                "turn_idx": self._turn_idx,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
