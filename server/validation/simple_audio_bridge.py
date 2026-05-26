"""
Bidirectional PCM bridge: OpenAI Realtime API ↔ Sailly `/ws/demo`.

Patched 2026-05-02 — fixes "call doesn't show up as a normal call in metrics
dashboard" + "voices overlap in recording" + "caller speaks before greeting".

Six problems addressed (see FIX comments inline):

  FIX 1: Sailly's wire format is `[uint32 LE counter] + PCM16`, not bare PCM.
         Without the counter, `BrowserFrameSerializer` either drops frames
         or eats the first 4 PCM samples as the counter, corrupting audio.

  FIX 2: A real browser mic sends fixed 4096-byte chunks (~128ms @ 16kHz)
         paced at real-time. OpenAI Realtime emits variable-sized bursts
         that arrive much faster than real-time. Deepgram STT and SileroVAD
         rely on wall-clock timing for endpointing — bursty frames trigger
         the `TurnAnalyzerUserTurnStopStrategy` no-VAD fallback (the
         documented 2ms phantom-turn bug).

  FIX 3: A real mic always sends audio — silence between turns included.
         Without continuous silence, Deepgram's connection goes cold and
         the first caller utterance gets clipped. The pump emits silence
         whenever the buffer is empty.

  FIX 4: With model `gpt-4o-realtime-preview-2024-12-17`, the audio event
         name is `response.audio.delta`, not `response.output_audio.delta`.
         The latter is for `gpt-realtime` (GA, Aug 2025). Listening for
         only the GA name on a preview-model session = zero audio out.
         We accept both for forward/backward compatibility.

  FIX 5: Handshake matches the real browser exactly (`tenant`, `voice`,
         `style`) so the `/ws/demo` handler initialises the same TTS
         conditioning path a real browser session would.

  FIX 6 (this patch): Caller AI was speaking before Sailly finished its
         greeting, and audio was overlapping in the recording. Three
         coordinated changes:

         (a) `turn_detection` now uses `eagerness: "low"` so the caller's
             VAD doesn't fire on micro-pauses inside the greeting, plus
             `interrupt_response: True` so the caller cancels itself when
             the bot starts a new utterance.

         (b) `_SaillyTalkingState` tracks whether the bot is currently
             mid-utterance based on the `transcript`/`bot_text` events
             we already receive. While the bot is talking, any in-flight
             caller audio deltas are dropped and `response.cancel` is
             sent to OpenAI. This is the cross-side gating that's missing
             when there's no acoustic feedback between two AIs.

         (c) `caller_responding` flag tracks OpenAI's response lifecycle
             so we only send `response.cancel` when there's actually a
             response to cancel (the API errors otherwise).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import struct
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote

try:
    import websockets
except ImportError as e:  # pragma: no cover
    raise ImportError("Install websockets: pip install websockets") from e

from server.audio_recorder import CALLER_RATE, CallerAudioRecorder, finalize_all

logger = logging.getLogger(__name__)

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
DEFAULT_REALTIME_MODEL = "gpt-4o-realtime-preview-2024-12-17"

# ── Browser wire-protocol constants (must match BrowserFrameSerializer) ───────
_SEND_SAMPLE_RATE = 16_000
_BYTES_PER_SAMPLE = 2
_CHUNK_BYTES = 4096                                            # 128 ms @ 16 kHz
_CHUNK_INTERVAL_S = _CHUNK_BYTES / (_SEND_SAMPLE_RATE * _BYTES_PER_SAMPLE)
_SILENCE_CHUNK = b"\x00" * _CHUNK_BYTES

# How long after the last bot transcript event we still consider the bot to be
# "talking". Bot transcript events arrive roughly every 200–400ms during
# streaming TTS; 900ms gives a safety margin for sparse partials without holding
# caller turns open forever after the agent actually finishes.
_BOT_TALKING_QUIET_AFTER_S = 0.9

# Pause after bot finishes speaking before triggering the next caller response.
# Prevents caller from firing during transient silence between bot's TTS and LLM.
_POST_BOT_SILENCE_S = 0.3

# Set of OpenAI Realtime event names that carry output audio bytes. The exact
# name depends on the model snapshot (preview vs GA). Listening for both keeps
# the bridge working across model upgrades. See FIX 4.
_OPENAI_AUDIO_DELTA_EVENTS: frozenset[str] = frozenset({
    "response.audio.delta",          # gpt-4o-realtime-preview-* (Dec 2024)
    "response.output_audio.delta",   # gpt-realtime (GA, Aug 2025+)
})


@dataclass
class BridgeResult:
    call_sid: str
    transcripts: list[dict[str, Any]]
    duration_sec: float
    caller_audio_url: str | None = None
    agent_audio_url: str | None = None
    error: str | None = None
    scenario_id: str = ""


class _AgentChunks:
    """Buffers agent-side PCM (same interface expected by finalize_all)."""

    def __init__(self) -> None:
        self.chunks: list[bytes] = []


# ─── Resampling helpers ───────────────────────────────────────────────────────


def _import_audioop():  # pragma: no cover — env dependent
    try:
        import audioop as _a  # type: ignore[import-not-found]

        return _a
    except ImportError:
        try:
            import audioop_lts as _a  # type: ignore[import-not-found]

            return _a
        except ImportError:
            return None


def _linear_pcm16_resample(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    """Chunk-wise linear resample (no cross-chunk state) — fallback only."""
    if not pcm or src_rate == dst_rate:
        return pcm
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    if not samples:
        return pcm
    ratio = dst_rate / src_rate
    out_len = max(1, int(len(samples) * ratio))
    out: list[int] = []
    for j in range(out_len):
        src_pos = j / ratio
        i = int(src_pos)
        frac = src_pos - i
        if i + 1 < len(samples):
            s = samples[i] * (1.0 - frac) + samples[i + 1] * frac
        else:
            s = float(samples[min(i, len(samples) - 1)])
        out.append(int(max(-32768, min(32767, round(s)))))
    return struct.pack(f"<{len(out)}h", *out)


class _PCM24kTo16k:
    """Stateful resampler for OpenAI (24 kHz) → Sailly mic path (16 kHz)."""

    def __init__(self) -> None:
        self._state: Any = None
        self._audioop = _import_audioop()

    def convert(self, pcm24: bytes) -> bytes:
        if not pcm24:
            return pcm24
        if self._audioop is not None:
            out, self._state = self._audioop.ratecv(
                pcm24, 2, 1, 24000, CALLER_RATE, self._state
            )
            return out
        return _linear_pcm16_resample(pcm24, 24000, CALLER_RATE)


# ─── Sailly audio pump (FIX 1, 2, 3) ──────────────────────────────────────────


class _SaillyAudioPump:
    """
    Reframes inbound PCM16/16kHz audio into 4096-byte chunks, prefixes each
    with a 4-byte LE chunk counter, paces sends at real time (~128ms/chunk),
    and emits silence whenever the buffer is empty.

    This matches BrowserFrameSerializer's wire format and the timing a real
    browser microphone produces.
    """

    def __init__(self, ws: Any) -> None:
        self._ws = ws
        self._buf = bytearray()
        self._counter = 0
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._stopped = False
        self._send_errors = 0

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="sailly-audio-pump")

    async def stop(self) -> None:
        self._stopped = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    async def push(self, pcm16: bytes) -> None:
        """Append PCM16/16kHz audio bytes to the outbound buffer."""
        if not pcm16:
            return
        async with self._lock:
            self._buf.extend(pcm16)

    async def drop_pending(self) -> None:
        """Discard any buffered audio that hasn't been sent yet.

        Called when we cancel an in-flight caller response — without this,
        the pump would keep playing the cancelled response's audio for
        another second or two.
        """
        async with self._lock:
            self._buf.clear()

    async def _next_chunk(self) -> bytes:
        async with self._lock:
            if len(self._buf) >= _CHUNK_BYTES:
                chunk = bytes(self._buf[:_CHUNK_BYTES])
                del self._buf[:_CHUNK_BYTES]
                return chunk
        return _SILENCE_CHUNK

    async def _loop(self) -> None:
        loop = asyncio.get_event_loop()
        next_t = loop.time()
        while not self._stopped:
            chunk = await self._next_chunk()
            header = struct.pack("<I", self._counter & 0xFFFFFFFF)
            try:
                await self._ws.send(header + chunk)
            except Exception as e:
                self._send_errors += 1
                if self._send_errors > 3:
                    logger.warning("[pump] giving up after repeated send errors: %s", e)
                    break
                await asyncio.sleep(0.05)
                continue
            self._counter += 1
            next_t += _CHUNK_INTERVAL_S
            delay = next_t - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            else:
                # Fell behind (slow link or GC pause). Reset clock to avoid a
                # catch-up burst that defeats real-time pacing.
                next_t = loop.time()


# ─── Sailly talking-state tracker (FIX 6b) ────────────────────────────────────


class _SaillyTalkingState:
    """Tracks whether Sailly's bot is currently emitting TTS audio.

    We can't observe Sailly's audio frames with semantic content, but the
    transcript JSON events bracket each utterance: a `transcript` event with
    `speaker == "bot"` (or a `bot_text` event) means a new bot turn is in
    progress; a quiet period of `quiet_after_s` with no new bot events means
    the bot has finished. We use this to gate caller barge-in: while the bot
    is talking, in-flight caller audio is dropped and `response.cancel` is
    sent so the recording doesn't have overlap.

    On a real phone call, acoustic feedback through the human's earpiece
    naturally suppresses double-talk. Between two AIs on separate WebSocket
    connections, that mechanism doesn't exist, so we synthesise it here.
    """

    def __init__(self, quiet_after_s: float = _BOT_TALKING_QUIET_AFTER_S) -> None:
        self._last_bot_event_t: float | None = None
        self._quiet_after_s = quiet_after_s

    def note_bot_event(self) -> None:
        """Mark that the bot just emitted a transcript/bot_text event."""
        self._last_bot_event_t = time.monotonic()

    def reset(self) -> None:
        """Clear the talking state (e.g. after a `call_ended` event)."""
        self._last_bot_event_t = None

    @property
    def bot_talking(self) -> bool:
        if self._last_bot_event_t is None:
            return False
        return (time.monotonic() - self._last_bot_event_t) < self._quiet_after_s


# ─── Handshake helpers ────────────────────────────────────────────────────────


async def _drain_until_session_init(sailly_ws: Any) -> str:
    while True:
        msg = await sailly_ws.recv()
        if isinstance(msg, bytes):
            continue
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            continue
        if data.get("type") == "session_init":
            sid = data.get("call_sid") or ""
            logger.info("[bridge] Sailly session_init call_sid=%s", sid)
            return sid
        if data.get("error"):
            raise RuntimeError(f"Sailly handshake error: {data}")


async def _openai_handshake_and_configure(
    openai_ws: Any,
    *,
    instructions: str,
) -> None:
    """Wait for `session.created`, then push our session config.

    FIX 6a: turn_detection now uses eagerness="low" + interrupt_response=True.
    These two together solve the "caller speaks first" and "voices overlap"
    problems on the OpenAI side:

      - eagerness="low" makes semantic VAD wait longer before deciding the
        agent has finished speaking. With "auto" (the default), micro-pauses
        inside the greeting ("Doboo…guten Tag…wie kann ich…") trigger the
        caller to respond mid-greeting.

      - interrupt_response=True lets the caller cancel its own in-flight
        response when it hears the agent start a new utterance. Without it,
        the caller would keep talking even after the agent jumps in to
        clarify or reprompt.
    """
    while True:
        raw = await openai_ws.recv()
        evt = json.loads(raw)
        et = evt.get("type")
        if et == "session.created":
            break
        if et == "error":
            raise RuntimeError(f"OpenAI session error: {evt}")

    session_update = {
        "type": "session.update",
        "session": {
            "instructions": instructions,
            "modalities": ["audio", "text"],
            "voice": "alloy",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {
                "type": "semantic_vad",
                "eagerness": "low",
                "interrupt_response": True,
                "create_response": False,  # Manual control: bot_turn_watcher triggers each response
            },
        },
    }
    await openai_ws.send(json.dumps(session_update))

    while True:
        raw = await openai_ws.recv()
        evt = json.loads(raw)
        et = evt.get("type")
        if et == "session.updated":
            logger.info("[bridge] OpenAI session.updated (eagerness=low, interrupt=on)")
            return
        if et == "error":
            raise RuntimeError(f"OpenAI session.update error: {evt}")


# ─── Main bridge entrypoint ───────────────────────────────────────────────────


async def connect_openai_to_sailly(
    *,
    scenario_id: str,
    caller_instructions: str,
    tenant_id: str,
    sailly_ws_url: str,
    openai_api_key: str,
    google_credentials_path: str | None = None,
    max_duration_sec: float = 180.0,
    realtime_model: str | None = None,
    voice: str = "Kore",
    style: str = "warm",
) -> BridgeResult:
    """
    Run one validation call: Sailly handles STT/TTS/LLM; OpenAI Realtime plays
    the caller. The bridge presents itself to Sailly as a real browser mic
    (correct framing, real-time pacing, continuous silence) and synthesises
    cross-side turn-taking that two AIs over WebSockets normally lack.
    """
    t0 = time.monotonic()
    transcripts: list[dict[str, Any]] = []
    model = realtime_model or os.environ.get(
        "OPENAI_REALTIME_MODEL", DEFAULT_REALTIME_MODEL
    )
    creds = google_credentials_path or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/home/charles2/.ssh/sailly-voice-agent-key.json",
    )

    call_sid = ""
    err: str | None = None
    caller_recorder = CallerAudioRecorder(call_sid="pending", credentials_path=creds)
    agent_buf = _AgentChunks()

    sailly_ws = None
    openai_ws = None
    pump: _SaillyAudioPump | None = None

    # Cross-side coordination state (FIX 6b/c).
    sailly_state = _SaillyTalkingState()
    caller_responding = False  # True while OpenAI is mid-response

    async def cancel_caller_response() -> None:
        """Send response.cancel + input_audio_buffer.clear + clear the pump's outbound buffer.

        Safe to call at any time; OpenAI just emits a benign error when
        there's nothing to cancel. We clear the pump and OpenAI's server-side
        buffer so audio that's already been forwarded but not yet sent gets
        discarded — otherwise the cancelled response continues playing for ~1s
        and the buffered audio can re-trigger VAD.
        """
        if not caller_responding or openai_ws is None:
            return
        try:
            await openai_ws.send(json.dumps({"type": "response.cancel"}))
            await openai_ws.send(json.dumps({"type": "input_audio_buffer.clear"}))
            logger.debug("[bridge] sent response.cancel + input_audio_buffer.clear (bot started talking)")
        except Exception as e:
            logger.debug("[bridge] response.cancel send failed: %s", e)
        if pump is not None:
            await pump.drop_pending()
        # Don't clear caller_responding here — wait for the response.cancelled
        # event from OpenAI so the flag stays accurate.

    try:
        # ─── 1. Sailly handshake ────────────────────────────────────────────
        sailly_ws = await websockets.connect(sailly_ws_url, max_size=None)
        await sailly_ws.send(
            json.dumps({"tenant": tenant_id, "voice": voice, "style": style})
        )
        call_sid = await _drain_until_session_init(sailly_ws)
        caller_recorder._call_sid = call_sid

        # ─── 2. Start audio pump immediately ────────────────────────────────
        # Streams silence at real-time pace so Sailly's Deepgram connection
        # warms up before OpenAI's handshake completes.
        pump = _SaillyAudioPump(sailly_ws)
        pump.start()

        # ─── 3. OpenAI Realtime handshake ───────────────────────────────────
        uri = f"{OPENAI_REALTIME_URL}?model={quote(model)}"
        openai_ws = await websockets.connect(
            uri,
            additional_headers={
                "Authorization": f"Bearer {openai_api_key}",
                "OpenAI-Beta": "realtime=v1",
            },
            max_size=None,
        )
        await _openai_handshake_and_configure(
            openai_ws, instructions=caller_instructions
        )

        # ─── 4. Bidirectional audio bridge ──────────────────────────────────

        async def sailly_to_openai() -> None:
            """Forward Sailly's bot TTS to OpenAI + track bot talking-state."""
            nonlocal caller_responding
            assert sailly_ws is not None and openai_ws is not None
            while True:
                msg = await sailly_ws.recv()
                if isinstance(msg, bytes):
                    # Sailly emits PCM16 LE 24kHz mono. OpenAI accepts 24kHz
                    # natively as input_audio_format=pcm16, no resample needed.
                    agent_buf.chunks.append(msg)
                    # Binary TTS chunks arrive between sparse transcript partials;
                    # refresh bot-talking state so caller audio isn't leaked early.
                    if msg:
                        sailly_state.note_bot_event()
                    b64 = base64.b64encode(msg).decode("ascii")
                    await openai_ws.send(
                        json.dumps({"type": "input_audio_buffer.append", "audio": b64})
                    )
                else:
                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        continue
                    mtype = data.get("type")

                    if mtype == "transcript":
                        speaker = data.get("speaker")
                        text = data.get("text") or ""
                        # FIX 6b: bot transcript event = bot is speaking now.
                        # Mark talking-state and cancel any in-flight caller
                        # response so the recording doesn't have overlap.
                        if speaker == "bot" and text:
                            sailly_state.note_bot_event()
                            if caller_responding:
                                await cancel_caller_response()
                        transcripts.append({"speaker": speaker, "text": text})

                    elif mtype == "bot_text":
                        # Streaming TTS text — same signal as `transcript`/bot.
                        if data.get("text"):
                            sailly_state.note_bot_event()
                            if caller_responding:
                                await cancel_caller_response()

                    elif mtype == "tools_called":
                        transcripts.append(
                            {"speaker": "tools", "text": data.get("tools")}
                        )

                    elif mtype == "call_ended":
                        sailly_state.reset()
                        # Sailly will close the socket shortly; let the recv
                        # loop exit naturally on the next iteration.

                    elif mtype == "error":
                        raise RuntimeError(f"Sailly WS error: {data}")

        downsample = _PCM24kTo16k()

        async def openai_to_sailly() -> None:
            """Forward OpenAI caller speech to the pump + track response state."""
            nonlocal caller_responding
            assert openai_ws is not None and pump is not None
            while True:
                raw = await openai_ws.recv()
                evt = json.loads(raw)
                et = evt.get("type")

                # ── Response lifecycle (FIX 6c) ────────────────────────────
                if et == "response.created":
                    caller_responding = True
                    logger.debug("[bridge] OpenAI response.created (caller starting)")
                    continue
                if et == "response.done":
                    caller_responding = False
                    logger.debug("[bridge] OpenAI response.done (caller finished)")
                    continue
                if et in ("response.cancelled", "response.canceled"):
                    caller_responding = False
                    logger.debug("[bridge] OpenAI response.cancelled (we cancelled it)")
                    continue

                # ── Audio deltas (FIX 4 + FIX 6b drop-while-bot-talking) ───
                if et in _OPENAI_AUDIO_DELTA_EVENTS:
                    delta = evt.get("delta") or evt.get("audio") or ""
                    if not delta:
                        continue
                    # If the bot is mid-utterance, drop this delta and cancel
                    # the in-flight caller response. The caller's semantic VAD
                    # will pick up the bot's full turn and respond after.
                    if sailly_state.bot_talking:
                        await cancel_caller_response()
                        continue
                    pcm24 = base64.b64decode(delta)
                    pcm16 = downsample.convert(pcm24)
                    caller_recorder.on_audio(pcm16)
                    await pump.push(pcm16)
                    continue

                if et in (
                    "response.audio.done",
                    "response.output_audio.done",
                ):
                    # End-of-utterance from OpenAI side. The pump fills the
                    # gap with silence until the next caller response starts.
                    continue

                if et == "input_audio_buffer.speech_started":
                    logger.debug("[bridge] OpenAI VAD: agent speech_started")
                    continue
                if et == "input_audio_buffer.speech_stopped":
                    logger.debug("[bridge] OpenAI VAD: agent speech_stopped")
                    continue

                if et == "error":
                    # OpenAI emits an error if we cancel a non-existent
                    # response. Log at debug, don't crash.
                    err_obj = evt.get("error") or {}
                    code = err_obj.get("code") or ""
                    if code in (
                        "response_cancel_not_active",
                        "response_already_done",
                    ):
                        logger.debug("[bridge] benign OpenAI error: %s", code)
                    else:
                        logger.warning("[bridge] OpenAI error event: %s", evt)

        async def bot_turn_watcher() -> None:
            """Trigger exactly one caller response per completed bot turn.
            
            With create_response=False, OpenAI does not auto-fire on VAD.
            We monitor sailly_state.bot_talking and manually send response.create
            after confirmed silence. This ensures hard half-duplex: the caller
            responds exactly once per bot utterance, not during LLM gaps.
            """
            was_talking = False
            initial_silence_confirmed = False
            fire_count = 0
            start_time = time.monotonic()
            
            while True:
                await asyncio.sleep(0.05)
                if openai_ws is None:
                    continue
                now_talking = sailly_state.bot_talking
                elapsed = time.monotonic() - start_time
                
                # Safety: fire at least once after 2 seconds to unblock
                if elapsed > 2.0 and fire_count == 0 and not caller_responding:
                    try:
                        await openai_ws.send(json.dumps({"type": "response.create"}))
                        fire_count += 1
                        logger.debug("[bridge] triggered caller response (safety timeout)")
                    except Exception as e:
                        logger.debug("[bridge] response.create failed: %s", e)
                
                # On first silence window (bot hasn't talked yet, or after bot finishes)
                if not now_talking and not initial_silence_confirmed and fire_count < 1:
                    initial_silence_confirmed = True
                    await asyncio.sleep(_POST_BOT_SILENCE_S)
                    if not sailly_state.bot_talking and not caller_responding:
                        try:
                            await openai_ws.send(json.dumps({"type": "response.create"}))
                            fire_count += 1
                            logger.debug("[bridge] triggered caller response (initial)")
                        except Exception as e:
                            logger.debug("[bridge] response.create failed: %s", e)
                
                # On subsequent bot turns: detect transition from talking → silent
                if was_talking and not now_talking and fire_count > 0:
                    await asyncio.sleep(_POST_BOT_SILENCE_S)
                    if not sailly_state.bot_talking and not caller_responding:
                        try:
                            await openai_ws.send(json.dumps({"type": "response.create"}))
                            logger.debug("[bridge] triggered caller response after bot turn")
                        except Exception as e:
                            logger.debug("[bridge] response.create failed: %s", e)
                
                # Track when bot starts talking again (reset initial flag)
                if now_talking:
                    initial_silence_confirmed = False
                    
                was_talking = now_talking

        await asyncio.wait_for(
            asyncio.gather(sailly_to_openai(), openai_to_sailly(), bot_turn_watcher()),
            timeout=max_duration_sec,
        )

    except asyncio.TimeoutError:
        logger.info("[bridge] Max duration %.1fs elapsed — stopping", max_duration_sec)
    except Exception as e:
        err = str(e)
        logger.exception("[bridge] Failed: %s", e)
    finally:
        if pump is not None:
            try:
                await pump.stop()
            except Exception:
                pass
        for ws in (sailly_ws, openai_ws):
            if ws is not None:
                try:
                    await ws.close()
                except Exception:
                    pass

    # ─── 5. Persist recordings ──────────────────────────────────────────────
    combined_url: str | None = None
    agent_url: str | None = None
    try:
        agent_shim = SimpleNamespace(chunks=agent_buf.chunks)
        combined_url, agent_url = await finalize_all(
            call_sid=call_sid or caller_recorder._call_sid,
            credentials_path=creds,
            caller_recorder=caller_recorder,
            agent_capture=agent_shim,  # type: ignore[arg-type]
        )
    except Exception as fin_e:
        logger.warning("[bridge] finalize_all failed: %s", fin_e)

    dur = time.monotonic() - t0
    return BridgeResult(
        call_sid=call_sid,
        transcripts=transcripts,
        duration_sec=dur,
        caller_audio_url=combined_url,
        agent_audio_url=agent_url,
        error=err,
        scenario_id=scenario_id,
    )
