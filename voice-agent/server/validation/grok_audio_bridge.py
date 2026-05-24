"""
Bidirectional PCM bridge: Grok Realtime API ↔ Sailly `/ws/demo`.

Rewritten 2026-05-02 to eliminate the recording-duration bug and the
over-mitigated gating layers that were fighting each other. The previous
version had:

  - `caller_recorder.on_audio` called from the Grok handler (bursty arrival
    rate) → recorded WAV was timeline-compressed → 90s call → 60s recording
  - `grok_audio_buf` flush loop that pushed buffered chunks back-to-back
    into the recorder → further timeline compression
  - 3-state machine + 8s cooldown + RMS-based Sailly-talking detection +
    grace period buffer-and-flush — four overlapping mitigations doing
    similar work, with the cooldown long enough to swallow the agent's
    response

This version:

  - The pump owns the recording. `caller_recorder.on_audio` is called from
    inside `_SaillyAudioPump._loop`, so the WAV gets exactly what went on
    the wire, paced exactly as the wire saw it. Recording duration ≡ call
    duration, mechanically. Silence chunks ARE recorded (correctly — they
    represent the caller's silence during agent turns).
  - A single 3-state machine gates Grok→Sailly audio. No buffering: when
    we want to suppress overlap, we drop, period. Per the user decision
    "overlap suppression is more important than not dropping caller audio".
  - Pump starts immediately after Sailly's session_init so Deepgram warms
    up on silence pre-roll, identical to a real browser mic.
  - Cooldown is short (1.5s) and event-driven: exits on first bot
    transcript OR timeout, whichever fires first.
  - Binary-frame logs are at DEBUG, only summary heartbeats at INFO,
    so trace files stay readable.
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
from typing import Any, Literal

try:
    import websockets
except ImportError as e:  # pragma: no cover
    raise ImportError("Install websockets: pip install websockets") from e

from server.audio_recorder import CALLER_RATE, CallerAudioRecorder, finalize_all

logger = logging.getLogger(__name__)
diag = logging.getLogger("bridge.diag")

_T0 = time.monotonic()


def _t() -> float:
    return time.monotonic() - _T0


# ── Grok endpoint ────────────────────────────────────────────────────────────
GROK_REALTIME_URL = "wss://api.x.ai/v1/realtime"
GROK_MODEL = "grok-voice-think-fast-1.0"
_GROK_AUDIO_DELTA_EVENT = "response.output_audio.delta"

# ── Browser wire-protocol constants (must match BrowserFrameSerializer) ──────
_SEND_SAMPLE_RATE = 16_000
_BYTES_PER_SAMPLE = 2
_CHUNK_BYTES = 4096                                      # 128 ms @ 16 kHz
_CHUNK_INTERVAL_S = _CHUNK_BYTES / (_SEND_SAMPLE_RATE * _BYTES_PER_SAMPLE)
_SILENCE_CHUNK = b"\x00" * _CHUNK_BYTES

# ── Cooldown after Grok's response.done ──────────────────────────────────────
# Short enough that the agent's turn isn't suppressed; long enough that the
# tail of Grok's last audio delta has time to drain into the pump and be sent.
# Exits early if Sailly emits a bot transcript event before the timeout.
_COOLDOWN_TIMEOUT_S = 1.5


# ── Bridge state ─────────────────────────────────────────────────────────────
# grok_listening: Sailly→Grok audio flowing; Grok→Sailly audio flowing
# grok_speaking:  Grok is responding; Sailly→Grok blocked (don't disturb)
# cooldown:       brief window after Grok finishes; Grok→Sailly dropped to
#                 prevent tail-end overlap; Sailly→Grok flowing again
BridgeState = Literal["grok_listening", "grok_speaking", "cooldown"]


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


# ── Resampling ───────────────────────────────────────────────────────────────


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
    """Stateful resampler for Grok output (24 kHz) → Sailly mic (16 kHz)."""

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


# ── Sailly audio pump (also owns recording) ──────────────────────────────────


class _SaillyAudioPump:
    """
    Reframes inbound PCM16/16kHz audio into 4096-byte chunks, prefixes each
    with a 4-byte LE chunk counter, paces sends at real time (~128ms/chunk),
    and emits silence whenever the buffer is empty.

    KEY INVARIANT: the recorder is fed from inside this loop, so the caller
    WAV's timeline matches the call's wall-clock timeline exactly. Without
    this, audio that arrives in bursts (Grok dumps 5s of speech in 200ms)
    gets recorded "instantly" and the WAV duration is shorter than the call.
    """

    def __init__(
        self,
        ws: Any,
        recorder: CallerAudioRecorder | None = None,
    ) -> None:
        self._ws = ws
        self._recorder = recorder
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
        if not pcm16:
            return
        async with self._lock:
            self._buf.extend(pcm16)

    async def drop_pending(self) -> None:
        """Discard buffered audio that hasn't been sent yet."""
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
                    logger.warning("[pump] giving up: %s", e)
                    break
                await asyncio.sleep(0.05)
                continue

            # KEY LINE: record on the wire's clock, not on Grok's arrival
            # clock. The recorder sees real-time-paced audio and the WAV
            # ends up the right duration.
            if self._recorder is not None:
                try:
                    self._recorder.on_audio(chunk)
                except Exception:
                    pass

            self._counter += 1
            if self._counter % 80 == 0:                  # ~10s heartbeat
                async with self._lock:
                    buf_len = len(self._buf)
                diag.info(
                    "T=%.3f PUMP_HB counter=%d buf=%d", _t(), self._counter, buf_len
                )

            next_t += _CHUNK_INTERVAL_S
            delay = next_t - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            else:
                # Fell behind (slow link / GC). Reset so we don't burst.
                next_t = loop.time()


# ── Handshake helpers ────────────────────────────────────────────────────────


async def _drain_until_sailly_session_init(sailly_ws: Any) -> str:
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
            logger.info("[grok-bridge] Sailly session_init call_sid=%s", sid)
            return sid
        if data.get("error"):
            raise RuntimeError(f"Sailly handshake error: {data}")


async def _drain_until_grok_session_ready(grok_ws: Any) -> None:
    while True:
        msg = await grok_ws.recv()
        if isinstance(msg, bytes):
            continue
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            continue
        if data.get("type") == "session.updated":
            logger.info("[grok-bridge] Grok session.updated")
            return
        if data.get("error"):
            raise RuntimeError(f"Grok session config error: {data}")


# ── Main bridge ──────────────────────────────────────────────────────────────


async def connect_grok_to_sailly(
    *,
    scenario_id: str,
    caller_instructions: str,
    tenant_id: str,
    sailly_ws_url: str,
    xai_api_key: str,
    google_credentials_path: str | None = None,
    max_duration_sec: float = 180.0,
    voice: str = "Ara",
    sailly_voice: str = "Kore",
    sailly_style: str = "warm",
    grok_silence_duration_ms: int = 700,
) -> BridgeResult:
    """
    Run one validation call: Sailly is the agent, Grok plays the caller.

    The bridge presents itself to Sailly as a real browser mic (correct
    framing, real-time pacing, continuous silence) with a single 3-state
    machine to suppress double-talk between the two AIs.

    `grok_silence_duration_ms` controls how long Grok waits in silence
    before deciding the agent has finished. Default 700ms is conservative
    (Grok's own default is 200ms which is too eager — fires inside the
    greeting's micro-pauses).
    """
    t0 = time.monotonic()
    transcripts: list[dict[str, Any]] = []
    creds = google_credentials_path or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/home/charles2/.ssh/sailly-voice-agent-key.json",
    )

    call_sid = ""
    err: str | None = None
    caller_recorder = CallerAudioRecorder(call_sid="pending", credentials_path=creds)
    agent_buf = _AgentChunks()

    sailly_ws = None
    grok_ws = None
    pump: _SaillyAudioPump | None = None

    state: BridgeState = "grok_listening"
    cooldown_deadline = 0.0

    # Counters for end-of-call summary
    n_grok_audio_forwarded = 0
    n_grok_audio_dropped_speaking = 0
    n_grok_audio_dropped_cooldown = 0
    n_sailly_audio_to_grok = 0
    n_sailly_audio_blocked = 0

    def set_state(new: BridgeState, reason: str) -> None:
        nonlocal state
        if state != new:
            diag.info("T=%.3f STATE %s -> %s (%s)", _t(), state, new, reason)
            state = new

    try:
        # ─── 1. Sailly handshake ────────────────────────────────────────────
        sailly_ws = await websockets.connect(sailly_ws_url, max_size=None)
        await sailly_ws.send(
            json.dumps({"tenant": tenant_id, "voice": sailly_voice, "style": sailly_style})
        )
        call_sid = await _drain_until_sailly_session_init(sailly_ws)
        diag.info("T=%.3f SAILLY_INIT call_sid=%s", _t(), call_sid)
        caller_recorder._call_sid = call_sid

        # ─── 2. Start pump immediately so Deepgram warms on silence ─────────
        pump = _SaillyAudioPump(sailly_ws, recorder=caller_recorder)
        pump.start()

        # ─── 3. Grok handshake ──────────────────────────────────────────────
        grok_url = f"{GROK_REALTIME_URL}?model={GROK_MODEL}"
        grok_ws = await websockets.connect(
            grok_url,
            additional_headers={"Authorization": f"Bearer {xai_api_key}"},
            max_size=None,
        )
        session_update = {
            "type": "session.update",
            "session": {
                "instructions": caller_instructions,
                "voice": voice,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "silence_duration_ms": grok_silence_duration_ms,
                    "prefix_padding_ms": 300,
                },
                "audio": {
                    "input": {"format": {"type": "audio/pcm", "rate": 24000}},
                    "output": {"format": {"type": "audio/pcm", "rate": 24000}},
                },
            },
        }
        await grok_ws.send(json.dumps(session_update))
        await _drain_until_grok_session_ready(grok_ws)
        diag.info(
            "T=%.3f GROK_READY voice=%s silence_ms=%d",
            _t(), voice, grok_silence_duration_ms,
        )

        downsample = _PCM24kTo16k()

        # ─── 4. Bidirectional bridge ────────────────────────────────────────

        async def sailly_to_grok() -> None:
            """Forward Sailly's bot TTS to Grok, gated by state."""
            nonlocal n_sailly_audio_to_grok, n_sailly_audio_blocked
            assert sailly_ws is not None and grok_ws is not None
            while True:
                msg = await sailly_ws.recv()

                if isinstance(msg, bytes):
                    # Always record the agent side regardless of state — this
                    # captures Sailly's audio for the recording even when
                    # we're not forwarding it to Grok.
                    agent_buf.chunks.append(msg)

                    # Forward to Grok only while we want Grok to "hear" — i.e.
                    # while it's listening. During grok_speaking we hold off
                    # so we don't make Grok feel interrupted by its own bridge.
                    if state == "grok_listening" or state == "cooldown":
                        b64 = base64.b64encode(msg).decode("ascii")
                        await grok_ws.send(
                            json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": b64,
                            })
                        )
                        n_sailly_audio_to_grok += 1
                    else:
                        n_sailly_audio_blocked += 1
                    continue

                # JSON event
                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    continue
                mtype = data.get("type")
                speaker = data.get("speaker", "")
                text = (data.get("text") or "")[:80]

                if mtype == "transcript":
                    diag.info(
                        "T=%.3f SAILLY_JSON type=transcript speaker=%s text=%r",
                        _t(), speaker, text,
                    )
                    transcripts.append(
                        {"speaker": speaker, "text": data.get("text") or ""}
                    )
                    # Cooldown ends as soon as we see the agent producing
                    # transcript text — that's our signal the agent has
                    # something to say in response to Grok's last turn.
                    if speaker == "bot" and state == "cooldown":
                        set_state("grok_listening", "bot transcript after grok turn")

                elif mtype == "tools_called":
                    transcripts.append({"speaker": "tools", "text": data.get("tools")})

                elif mtype == "call_ended":
                    diag.info("T=%.3f SAILLY_JSON call_ended", _t())

                elif mtype == "error":
                    raise RuntimeError(f"Sailly WS error: {data}")

        async def cooldown_monitor() -> None:
            """If cooldown's timeout fires before a bot transcript, exit anyway."""
            while True:
                await asyncio.sleep(0.1)
                if state == "cooldown" and time.monotonic() > cooldown_deadline:
                    set_state("grok_listening", "cooldown timeout")

        async def grok_to_sailly() -> None:
            """Forward Grok caller speech to the pump, gated by state."""
            nonlocal n_grok_audio_forwarded, n_grok_audio_dropped_speaking
            nonlocal n_grok_audio_dropped_cooldown, cooldown_deadline
            assert grok_ws is not None and pump is not None
            while True:
                raw = await grok_ws.recv()

                # Grok can send raw binary PCM directly OR base64 inside JSON
                # depending on session config; handle both.
                if isinstance(raw, bytes):
                    if not raw:
                        continue
                    # Grok→Sailly audio is dropped during grok_speaking is
                    # impossible (we ARE in grok_speaking BECAUSE Grok is
                    # speaking), so the only suppression is during cooldown
                    # which catches the tail-end of Grok's response after
                    # we've already started transitioning out.
                    if state == "cooldown":
                        n_grok_audio_dropped_cooldown += 1
                        continue
                    pcm16 = downsample.convert(raw)
                    await pump.push(pcm16)
                    n_grok_audio_forwarded += 1
                    continue

                # JSON event
                try:
                    evt = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("[grok] bad JSON: %s", str(raw)[:120])
                    continue

                et = evt.get("type")

                if et is None:
                    # Grok occasionally emits untyped error envelopes
                    if evt.get("detail") or evt.get("error"):
                        raise RuntimeError(f"Grok API error: {evt}")
                    logger.warning("[grok] untyped event: %s", str(evt)[:120])
                    continue

                # Diagnostic — every event but the noisy audio deltas
                if et != _GROK_AUDIO_DELTA_EVENT:
                    diag.info("T=%.3f GROK_EVT type=%s state=%s", _t(), et, state)

                # State transitions
                if et == "response.created":
                    set_state("grok_speaking", "response.created")
                    continue

                if et == "response.done":
                    cooldown_deadline = time.monotonic() + _COOLDOWN_TIMEOUT_S
                    set_state("cooldown", "response.done")
                    # Drop anything still buffered in the pump from the tail
                    # of this response, so cooldown actually starts clean.
                    await pump.drop_pending()
                    continue

                # Audio delta in JSON form
                if et == _GROK_AUDIO_DELTA_EVENT:
                    delta = evt.get("delta") or ""
                    if not delta:
                        continue
                    if state == "cooldown":
                        n_grok_audio_dropped_cooldown += 1
                        continue
                    pcm24 = base64.b64decode(delta)
                    pcm16 = downsample.convert(pcm24)
                    await pump.push(pcm16)
                    n_grok_audio_forwarded += 1
                    continue

                # Useful but non-actionable
                if et == "conversation.item.input_audio_transcription.completed":
                    grok_heard = evt.get("transcript") or ""
                    diag.info("T=%.3f GROK_HEARD text=%r", _t(), grok_heard[:80])
                    transcripts.append({"speaker": "caller_heard", "text": grok_heard})
                    continue

                if et in (
                    "response.audio.done",
                    "response.output_audio.done",
                    "input_audio_buffer.speech_started",
                    "input_audio_buffer.speech_stopped",
                    "response.audio_transcript.delta",
                    "response.audio_transcript.done",
                ):
                    continue

                if et == "error":
                    diag.info("T=%.3f GROK_ERROR %s", _t(), str(evt)[:120])
                    logger.warning("[grok] error event: %s", evt)

        await asyncio.wait_for(
            asyncio.gather(
                sailly_to_grok(),
                grok_to_sailly(),
                cooldown_monitor(),
            ),
            timeout=max_duration_sec,
        )

    except asyncio.TimeoutError:
        logger.info(
            "[grok-bridge] Max duration %.1fs elapsed — stopping", max_duration_sec
        )
    except Exception as e:
        err = str(e)
        logger.exception("[grok-bridge] Failed: %s", e)
    finally:
        if pump is not None:
            try:
                await pump.stop()
            except Exception:
                pass
        for ws in (sailly_ws, grok_ws):
            if ws is not None:
                try:
                    await ws.close()
                except Exception:
                    pass

        # End-of-call counters — single line summary, easy to grep.
        diag.info(
            "T=%.3f BRIDGE_SUMMARY "
            "grok_fwd=%d grok_drop_spk=%d grok_drop_cd=%d "
            "sailly_to_grok=%d sailly_blocked=%d",
            _t(),
            n_grok_audio_forwarded,
            n_grok_audio_dropped_speaking,
            n_grok_audio_dropped_cooldown,
            n_sailly_audio_to_grok,
            n_sailly_audio_blocked,
        )

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
        logger.warning("[grok-bridge] finalize_all failed: %s", fin_e)

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
