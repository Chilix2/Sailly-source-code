"""
src/transport.py — HeadlessClient for /ws/headless protocol

Reuses the protocol semantics from server/tests/regression/harness.py
"""
import asyncio
import json
import logging
import time
from typing import Optional

try:
    import websockets
except ImportError:
    websockets = None

logger = logging.getLogger(__name__)


class HeadlessClient:
    """WebSocket client for /ws/headless endpoint.

    Protocol:
      Client → Server:
        {"type": "user_text", "text": "..."}
        {"type": "end_session"}

      Server → Client:
        {"type": "session_init", "call_sid": "..."}
        {"type": "bot_text", "text": "...", "tools_fired": [...], "turn_idx": N}
        {"type": "tool_event", "name": "...", ...}
        {"type": "session_end", "turn_count": N}
        {"type": "error", "message": "..."}
    """

    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self.call_sid: Optional[str] = None
        self._pending_tools: list[str] = []

    async def connect(self) -> str:
        """Connect and perform handshake. Returns call_sid."""
        if not websockets:
            raise RuntimeError("websockets not installed")

        self.ws = await websockets.connect(self.url)
        deadline = time.monotonic() + 20.0

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for session_init")

            try:
                msg_raw = await asyncio.wait_for(self.ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                continue

            if isinstance(msg_raw, bytes):
                continue

            try:
                data = json.loads(msg_raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")
            if msg_type == "session_init":
                self.call_sid = data.get("call_sid") or ""
                logger.info(f"[HeadlessClient] Connected: call_sid={self.call_sid!r}")
                return self.call_sid

    async def send_utterance(self, text: str) -> None:
        """Send user text to the agent."""
        if self.ws is None:
            raise RuntimeError("Not connected")
        await self.ws.send(json.dumps({"type": "user_text", "text": text}))

    async def receive_bot_turn(self, timeout_s: float = 25.0) -> tuple[str, list[str]]:
        """Wait for the next bot_text message. Returns (text, tools_fired)."""
        if self.ws is None:
            raise RuntimeError("Not connected")

        self._pending_tools = []
        deadline = time.monotonic() + timeout_s

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=min(remaining, 1.0))
            except asyncio.TimeoutError:
                continue

            if isinstance(raw, bytes):
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")

            if msg_type == "bot_text":
                self._pending_tools = data.get("tools_fired", [])
                text = data.get("text", "")
                logger.debug(f"[HeadlessClient] Received bot_text: {text[:80]!r}")
                return text, self._pending_tools

            elif msg_type == "tool_event":
                name = data.get("name", "")
                if name and name not in self._pending_tools:
                    self._pending_tools.append(name)

            elif msg_type == "session_end":
                logger.info(f"[HeadlessClient] Session ended: {data.get('turn_count')} turns")
                return "", []

            elif msg_type == "error":
                msg = data.get("message", "Unknown error")
                logger.error(f"[HeadlessClient] Server error: {msg}")
                raise RuntimeError(f"Server error: {msg}")

        raise TimeoutError(f"No bot_text received within {timeout_s}s")

    async def end_session(self) -> None:
        """Send end_session message."""
        if self.ws is not None:
            try:
                await self.ws.send(json.dumps({"type": "end_session"}))
            except Exception as e:
                logger.warning(f"[HeadlessClient] Error sending end_session: {e}")

    async def close(self) -> None:
        """Close WebSocket."""
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
