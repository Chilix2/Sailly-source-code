"""Browser demo server — isolated Pipecat pipeline with validated ADK brain."""

import asyncio
import json
import os
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from typing import Optional
from dotenv import load_dotenv

from pipecat.frames.frames import (
    AudioRawFrame,
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    EndFrame,
    ErrorFrame,
    LLMTextFrame,
    TranscriptionFrame,
    TTSSpeakFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.google.tts import GeminiTTSService
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)

from server.barge_in_handler import BargeInHandler
from server.brain_service import BrowserBrainService
from server.browser_serializer import BrowserFrameSerializer
from server.sailly_gemini_tts import SaillyGeminiTTSService
from server.brain.observability.tts_timing_processor import TTSTimingProcessor
from server.configs.secrets import get_secret

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Install PII-redacting log formatter + attach build SHA to every record.
# Must run after basicConfig so our formatter wraps the stderr handler.
try:
    from server.core.obs import install_log_redaction, log_boot_banner
    install_log_redaction()
    log_boot_banner(logger)
except Exception as _obs_err:  # pragma: no cover
    logger.warning(f"[BOOT] obs init failed (non-fatal): {_obs_err}")

# ── Active WebSocket connection tracker (for blue-green drain logic) ──────────
_active_ws_connections: set = set()

CASCADE_TTS_STYLE_PROMPT = (
    "Warm, natürlich und kompetent — wie eine freundliche Restaurantmitarbeiterin am Telefon."
)
DEFAULT_GEMINI_TTS_SPEAKING_RATE = 1.3


class BrowserToolsBroadcaster(FrameProcessor):
    """Intercepts [TOOLSDATA:...] marker frames emitted by BrowserBrainService.

    Sends {"type": "tools_called", "tools": [...]} over the browser WebSocket so
    the browser UI can display which tools were called per turn.  The marker frame
    is consumed here and NOT passed downstream, so TTS never speaks the tag.

    Also intercepts EndFrame to send {"type": "call_ended"} before the WebSocket
    closes — lets the browser UI distinguish a clean hangup from a crash.
    """

    _MARKER_RE = __import__("re").compile(r"^\[TOOLSDATA:([^\]]*)\]$")

    def __init__(self, websocket=None):
        super().__init__()
        self._ws = websocket

    async def _ws_send(self, payload: dict) -> None:
        if not self._ws:
            return
        try:
            await self._ws.send_text(json.dumps(payload))
        except Exception as exc:
            logger.warning(f"[BrowserToolsBroadcaster] WS send failed: {exc}")

    async def process_frame(self, frame: "Frame", direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMTextFrame) and frame.text:
            m = self._MARKER_RE.match(frame.text.strip())
            if m:
                tools = [t.strip() for t in m.group(1).split(",") if t.strip()]
                await self._ws_send({"type": "tools_called", "tools": tools})
                logger.debug(f"[BrowserToolsBroadcaster] Sent tools: {tools}")
                return  # consume — do NOT forward to TTS
        elif isinstance(frame, EndFrame):
            await self._ws_send({"type": "call_ended"})
            logger.info("[BrowserToolsBroadcaster] Sent call_ended signal to browser")
        await self.push_frame(frame, direction)


class STTWatchdog(FrameProcessor):
    """Monitors Deepgram STT health: if audio frames arrive but no transcription
    comes back within _TIMEOUT seconds, inject a German apology so the caller
    knows the line is still alive.

    Three gates prevent spurious alerts on normal user silence:
      Gate 1 — _first_transcript_received: only fires after at least one real STT result
      Gate 2 — _COOLDOWN (30s): minimum gap between repeat apology injections
      Gate 3 — _MIN_POST_STT_SEC (5s): won't fire within 5s of last successful STT
    """

    # Bug G: tightened — previous values still fired spuriously during normal silences.
    _TIMEOUT: float = 45.0          # was 30.0
    _COOLDOWN: float = 60.0         # was 30.0
    _MIN_POST_STT_SEC: float = 10.0  # was 5.0
    _APOLOGY = "Entschuldigung, ich habe gerade Verbindungsprobleme. Einen Moment bitte."

    def __init__(self):
        super().__init__()
        self._last_audio_at: float = 0.0
        self._last_transcript_at: float = time.time()
        self._last_apology_at: float = 0.0
        self._monitor_task: asyncio.Task | None = None
        self._first_transcript_received: bool = False

    async def process_frame(self, frame, direction):
        # CRITICAL: call super() first — pipecat drops frames if __started is False
        await super().process_frame(frame, direction)
        if isinstance(frame, AudioRawFrame):
            self._last_audio_at = time.time()
        elif isinstance(frame, TranscriptionFrame) and frame.text and frame.text.strip():
            self._last_transcript_at = time.time()
            self._first_transcript_received = True
        await self.push_frame(frame, direction)

    async def _monitor(self):
        while True:
            try:
                await asyncio.sleep(5.0)
                now = time.time()
                audio_age = now - self._last_audio_at
                transcript_age = now - self._last_transcript_at
                time_since_last_apology = now - self._last_apology_at
                if (
                    self._first_transcript_received
                    and self._last_audio_at > 0
                    and audio_age < 5.0
                    and transcript_age > self._TIMEOUT
                    and time_since_last_apology > self._COOLDOWN
                    and (now - self._last_transcript_at) > self._MIN_POST_STT_SEC
                ):
                    logger.critical(
                        f"[SF_GUARD][STTWatchdog] FIRING — transcript_age={transcript_age:.0f}s "
                        f"audio_age={audio_age:.1f}s cooldown_elapsed={time_since_last_apology:.0f}s "
                        f"(thresholds: timeout={self._TIMEOUT}s cooldown={self._COOLDOWN}s "
                        f"min_post_stt={self._MIN_POST_STT_SEC}s)"
                    )
                    self._last_apology_at = now
                    await self.push_frame(
                        TTSSpeakFrame(text=self._APOLOGY),
                        FrameDirection.DOWNSTREAM,
                    )
                else:
                    if transcript_age > self._TIMEOUT:
                        logger.info(
                            f"[SF_GUARD][STTWatchdog] BLOCKED — transcript_age={transcript_age:.0f}s "
                            f"but cooldown={time_since_last_apology:.0f}s min_post_stt={(now - self._last_transcript_at):.0f}s"
                        )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[STTWatchdog] Monitor error: {exc}")

    async def cleanup(self):
        if self._monitor_task:
            self._monitor_task.cancel()
        await super().cleanup()

    def set_task(self, task):
        if self._monitor_task:
            self._monitor_task.cancel()
        self._monitor_task = task


class STTConfidenceTracker(FrameProcessor):
    """Reads per-utterance confidence from ``TranscriptionFrame.result`` (the
    raw Deepgram payload) and stores a rolling window on ``brain_service`` so
    the brain can inject a reprompt / escalation when we have 3 low-confidence
    turns in a row.

    Design:
    - Fails open: if the result is missing or the field path changes, we
      treat confidence as unknown (None) and never flag a reprompt from
      missing data alone.
    - Window: keeps the last 6 confidences; the brain reads the tail to
      decide.
    - Threshold: 0.55 by default (matches Deepgram's "unreliable" floor for
      Nova-3 on 8 kHz telephony per their own docs).
    """

    LOW_CONFIDENCE_THRESHOLD: float = 0.55

    def __init__(self, brain_service):
        super().__init__()
        self._brain = brain_service

    @staticmethod
    def _extract_confidence(frame) -> float | None:
        result = getattr(frame, "result", None)
        if not result:
            return None
        try:
            alts = (
                result.get("channel", {})
                .get("alternatives", [])
            )
            if alts:
                conf = alts[0].get("confidence")
                if conf is not None:
                    return float(conf)
        except Exception:
            return None
        try:
            return float(getattr(result, "confidence", None))
        except Exception:
            return None

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame) and (frame.text or "").strip():
            conf = self._extract_confidence(frame)
            if conf is not None:
                try:
                    self._brain.record_stt_confidence(conf, text=frame.text)
                except Exception as e:
                    logger.debug(f"[STTConfidence] record failed: {e}")

            # B4: Flux EOT adapter — log turn-boundary decision for monitoring
            try:
                from server.brain.stt.flux_adapter import decide_turn_boundary
                _event_dict = {"confidence": conf, "transcript": frame.text or ""}
                _decision = decide_turn_boundary(_event_dict)
                if _decision.extend_stop_ms > 0 or _decision.is_end_of_turn:
                    logger.debug(
                        f"[FluxAdapter] EOT decision: is_eot={_decision.is_end_of_turn} "
                        f"extend={_decision.extend_stop_ms}ms reason={_decision.reason}"
                    )
            except Exception:
                pass
        await self.push_frame(frame, direction)


class TTSStreamWatchdog(FrameProcessor):
    """Monitors TTS stream health: if BotStartedSpeakingFrame arrives but
    BotStoppedSpeakingFrame does not follow within TIMEOUT_SEC seconds, push an
    ErrorFrame to signal a stalled TTS stream (silent pipeline death).

    CRITICAL: must call super().process_frame() first (pipecat boot-time validator).
    """

    TIMEOUT_SEC: float = 40.0  # increased from 15s: TTS 429 retries + streaming can take 5-10s

    def __init__(self):
        super().__init__()
        self._active_since: float | None = None
        self._watchdog_task: asyncio.Task | None = None
        self._lifecycle_log: list[str] = []  # track TTS stream lifecycle events for debugging

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, BotStartedSpeakingFrame):
            self._active_since = time.monotonic()
            self._lifecycle_log.append(f"BotStartedSpeaking @ {self._active_since:.3f}")
            if self._watchdog_task and not self._watchdog_task.done():
                self._watchdog_task.cancel()
            self._watchdog_task = asyncio.create_task(self._watch())
        elif isinstance(frame, BotStoppedSpeakingFrame):
            if self._active_since is not None:
                elapsed = time.monotonic() - self._active_since
                self._lifecycle_log.append(f"BotStoppedSpeaking @ {time.monotonic():.3f} (duration={elapsed:.3f}s)")
                logger.debug(f"[TTSWatchdog] TTS lifecycle: {' → '.join(self._lifecycle_log)}")
            self._active_since = None
            if self._watchdog_task and not self._watchdog_task.done():
                self._watchdog_task.cancel()
            self._watchdog_task = None
            self._lifecycle_log = []  # reset for next utterance
        await self.push_frame(frame, direction)

    async def _watch(self):
        try:
            await asyncio.sleep(self.TIMEOUT_SEC)
            if self._active_since is not None:
                elapsed = time.monotonic() - self._active_since
                logger.error(
                    f"[TTSWatchdog] TTS stream active for {elapsed:.1f}s without BotStoppedSpeakingFrame "
                    f"(timeout={self.TIMEOUT_SEC}s) — pipeline may be silently stalled. "
                    f"Lifecycle: {' → '.join(self._lifecycle_log)}. Pushing ErrorFrame."
                )
                await self.push_frame(ErrorFrame(error="TTS stream timeout"), FrameDirection.DOWNSTREAM)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"[TTSWatchdog] Watch error: {exc}")

    async def cleanup(self):
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
        await super().cleanup()


class SilenceReprompt(FrameProcessor):
    """Caller-silence timeout with reprompt + graceful hangup.

    State machine:
      * Bot finishes speaking (BotStoppedSpeakingFrame) → start a
        `REPROMPT_AFTER_S` timer.
      * Caller says anything (UserStartedSpeakingFrame / TranscriptionFrame) →
        cancel the timer.
      * Timer fires once → inject a single reprompt line via LLMTextFrame
        ("Sind Sie noch da? Falls nicht, beende ich das Gespräch gleich.")
        and start a second `HANGUP_AFTER_S` timer.
      * Second timer fires → push EndFrame, which triggers the same
        finalisation path as a client hangup.
      * If the caller speaks at any point, both timers reset.

    Deliberately ignorant of content — this runs in addition to the STT
    watchdog (which handles Deepgram silence) and the TTS watchdog (which
    handles stalled synthesis). Those tolerate short silences; this one
    ends the call.
    """

    REPROMPT_AFTER_S: float = 12.0
    HANGUP_AFTER_S: float = 8.0
    REPROMPT_TEXT: str = "Sind Sie noch da? Falls nicht, beende ich das Gespräch gleich."

    def __init__(self, call_sid: str = ""):
        super().__init__()
        self._timer_task: asyncio.Task | None = None
        self._reprompted: bool = False
        self._call_sid = call_sid  # Sprint B: track call_sid for structured log context

    def _cancel_timer(self) -> None:
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = None

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        from pipecat.frames.frames import UserStartedSpeakingFrame

        if isinstance(frame, BotStoppedSpeakingFrame):
            self._reprompted = False
            self._cancel_timer()
            self._timer_task = asyncio.create_task(self._wait_and_reprompt())
        elif isinstance(frame, (UserStartedSpeakingFrame, TranscriptionFrame)):
            self._reprompted = False
            self._cancel_timer()
        elif isinstance(frame, EndFrame):
            self._cancel_timer()

        await self.push_frame(frame, direction)

    async def _wait_and_reprompt(self) -> None:
        try:
            await asyncio.sleep(self.REPROMPT_AFTER_S)
            _sid = f" call={self._call_sid}" if self._call_sid else ""
            logger.warning(
                f"[SilenceReprompt]{_sid} Caller silent for {self.REPROMPT_AFTER_S:.0f}s — reprompting"
            )
            self._reprompted = True
            await self.push_frame(LLMTextFrame(text=self.REPROMPT_TEXT), FrameDirection.DOWNSTREAM)
            await asyncio.sleep(self.HANGUP_AFTER_S)
            logger.warning(
                f"[SilenceReprompt]{_sid} Still silent after reprompt ({self.HANGUP_AFTER_S:.0f}s) — ending call"
            )
            await self.push_frame(EndFrame(), FrameDirection.DOWNSTREAM)
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # pragma: no cover — best-effort observability
            logger.error(f"[SilenceReprompt] timer error: {exc!r}")

    async def cleanup(self):
        self._cancel_timer()
        await super().cleanup()


app = FastAPI(title="Sailly Browser Demo")

# Mount the Twilio Media Streams adapter (/voice + /ws/twilio). Safe to mount
# unconditionally — the /voice webhook is a no-op unless Twilio points at it.
try:
    from server.telephony.twilio_handler import router as _twilio_router
    app.include_router(_twilio_router, tags=["telephony"])
    logger.info("[DEMO] Twilio telephony router mounted at /voice + /ws/twilio")
except Exception as _te:  # pragma: no cover — don't let a telephony import kill the demo
    logger.warning(f"[DEMO] Twilio router not mounted: {_te!r}")

if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


async def _preflight_model_availability():
    """Verify every configured Gemini model actually responds before accepting calls.

    Fails LOUD at boot rather than silently 404-ing on every production call.
    Prevents gemini-2.0-flash-class regressions where a deprecated model gets
    deployed without anyone noticing until callers start experiencing failures.
    """
    import google.auth
    import google.auth.transport.requests
    from google import genai as _genai

    _project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    _region = os.environ.get("GEMINI_REGION", "europe-west4")
    _slot_model = os.environ.get("SLOT_EXTRACTOR_MODEL", "gemini-2.5-flash-lite")
    _main_model = os.environ.get("MAIN_LLM_MODEL", "gemini-2.5-flash")

    models_to_check = [
        ("slot_extractor", _slot_model),
        ("main_llm", _main_model),
    ]

    try:
        _creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        _client = _genai.Client(
            vertexai=True,
            project=_project,
            location=_region,
            credentials=_creds,
        )
    except Exception as e:
        logger.warning(f"[PREFLIGHT] Could not init Gemini client for preflight: {e} — skipping")
        return

    failures = []
    for name, model_id in models_to_check:
        try:
            from google.genai import types as _gt
            resp = await _client.aio.models.generate_content(
                model=model_id,
                contents="ping",
                config=_gt.GenerateContentConfig(max_output_tokens=1, temperature=0.0),
            )
            _ = resp  # success
            logger.info(f"[PREFLIGHT] {name} ({model_id}) — OK")
        except Exception as e:
            failures.append((name, model_id, str(e)))
            logger.error(f"[PREFLIGHT] {name} ({model_id}) — FAILED: {e}")

    if failures:
        raise RuntimeError(
            f"[PREFLIGHT] {len(failures)} model(s) unavailable at boot: {failures}. "
            "Fix model config before deploying."
        )


@app.on_event("startup")
async def _startup_background_tasks():
    """Launch long-running housekeeping tasks (GDPR purge, etc.).

    Registered as a startup hook rather than at import time so tests that
    import the module don't kick off background DB traffic.
    """
    await _preflight_model_availability()

    # Best-effort schema migrations — ``ensure_turn_metrics_table`` contains
    # idempotent ``ADD COLUMN IF NOT EXISTS`` statements for the tenant_id /
    # stt_confidence / build_sha columns the admin viewer + metrics pipeline
    # now depend on.  Failures are logged but do not block startup.
    try:
        from server.database import ensure_turn_metrics_table
        await ensure_turn_metrics_table()
    except Exception as e:
        logger.warning(f"[DEMO] turn_metrics migration failed (non-fatal): {e!r}")

    try:
        from server.transcript_purge import purge_task
        purge_task.start()
    except Exception as e:  # pragma: no cover
        logger.warning(f"[DEMO] transcript purge task not started: {e!r}")

    # Phase 9 B4 — load rate-limit override list at startup
    try:
        from server.brain.rate_limit import load_overrides as _load_rl
        _load_rl()
    except Exception as _e:
        logger.warning(f"[DEMO] rate_limit override load failed: {_e!r}")

    # Phase 9 B2 — configure structured logging (no-op if already done)
    try:
        from server.brain.logging_config import configure_logging as _cfg_log
        _cfg_log()
    except Exception as _e:
        logger.warning(f"[DEMO] logging_config failed: {_e!r}")

    # Phase 9 A4 — start SLA monitor background task
    try:
        import asyncio as _asyncio
        from server.brain.observability.sla_monitor import start_monitor as _start_sla
        _asyncio.create_task(_start_sla())
    except Exception as _e:
        logger.warning(f"[DEMO] SLA monitor not started: {_e!r}")


@app.get("/")
async def index():
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {"message": "Sailly Browser Demo running"}


@app.websocket("/ws/demo")
async def websocket_demo(websocket: WebSocket):
    """Handle browser demo WebSocket connection."""
    await websocket.accept()
    conn_id = id(websocket)
    _active_ws_connections.add(conn_id)
    logger.info(f"[DEMO] New WebSocket connection (active: {len(_active_ws_connections)})")

    brain = None
    try:
        try:
            handshake = await websocket.receive_json()
            tenant_id = handshake.get("tenant", "doboo")
            logger.info(f"[DEMO] Handshake: tenant={tenant_id}")
        except Exception as e:
            logger.error(f"[DEMO] Handshake error: {e}")
            await websocket.send_json(
                {"error": "Invalid handshake", "message": str(e)}
            )
            return

        deepgram_api_key = get_secret("deepgram-api-key", default="")
        google_project_id = os.environ.get(
            "GOOGLE_CLOUD_PROJECT", "sailly-voice-agent-eu"
        )
        google_credentials_path = os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "/home/charles2/.ssh/sailly-voice-agent-key.json",
        )

        if not deepgram_api_key:
            logger.error("[DEMO] deepgram-api-key secret not configured")
            await websocket.send_json({"error": "Server config error: Deepgram key missing"})
            return

        # Transport — NO VAD here; VAD lives on the context aggregator per Pipecat 0.0.108 API
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                serializer=BrowserFrameSerializer(),
                audio_in_enabled=True,
                audio_out_enabled=True,
            ),
        )
        logger.info("[DEMO] Transport created")

        # STT (Deepgram) — model and language come from tenant config.
        # Model defaults to flux-general-de on EU endpoint for German tenants.
        _stt_lang = "de"
        _stt_keywords: list = []
        _tc = None
        try:
            from server.core.tenant_config import TenantRegistry
            _tc = TenantRegistry().load_tenant(tenant_id)
            _stt_lang = _tc.stt_language or "de"
            from server.brain.stt.keyterm_loader import get_keyterms_for_tenant
            _stt_keywords = get_keyterms_for_tenant(tenant_id)
        except Exception as _tl_err:
            logger.warning(f"[DEMO] could not resolve tenant={tenant_id}: {_tl_err!r}")
        logger.info(
            f"[DEMO] STT language={_stt_lang} keywords=({len(_stt_keywords)}): "
            f"{_stt_keywords[:10]}{'…' if len(_stt_keywords) > 10 else ''}"
        )
        from server.brain.stt.deepgram_client import build_stt_settings, get_stt_endpoint
        _dg_settings_kwargs: dict = build_stt_settings(_tc) if _tc is not None else dict(
            model="nova-3", language=_stt_lang, endpointing=700,
            interim_results=True, punctuate=True, smart_format=True,
        )
        if _stt_keywords:
            _dg_settings_kwargs["keyterm"] = _stt_keywords
        _stt_endpoint = get_stt_endpoint(_tc) if _tc is not None else None
        _dg_kwargs: dict = dict(api_key=deepgram_api_key, settings=DeepgramSTTService.Settings(**_dg_settings_kwargs))
        if _stt_endpoint:
            _dg_kwargs["base_url"] = _stt_endpoint
        stt = DeepgramSTTService(**_dg_kwargs)
        logger.info(f"[DEMO] STT service created (model={_dg_settings_kwargs.get('model')}, endpoint={_stt_endpoint or 'default'})")

        brain = BrowserBrainService(tenant_id=tenant_id)
        logger.info("[DEMO] Brain service created")

        # Send session init with call_sid to browser (for harness correlation)
        try:
            await websocket.send_json({
                "type": "session_init",
                "call_sid": brain.call_sid,
            })
            logger.info(f"[DEMO] Session init sent: call_sid={brain.call_sid}")
        except Exception as e:
            logger.warning(f"[DEMO] Failed to send session_init: {e}")

        # TTS — global Vertex AI endpoint (no location): regional endpoints do not resolve
        # named Gemini voices like "Kore" and return 404.
        tts = SaillyGeminiTTSService(
            credentials_path=google_credentials_path,
            project_id=google_project_id,
            cascade_speaking_rate=DEFAULT_GEMINI_TTS_SPEAKING_RATE,
            settings=GeminiTTSService.Settings(
                model="gemini-2.5-flash-tts",
                language="de-DE",
                voice="Kore",
                prompt=CASCADE_TTS_STYLE_PROMPT,
            ),
        )
        # Give brain a direct reference to TTS so it can call update_for_turn()
        # before each LLM turn (adaptive style conditioning).
        brain.tts_service = tts
        logger.info("[DEMO] TTS service created")

        # Context aggregator with VAD (not on transport) — matches production
        context = LLMContext()
        context_aggregator = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(
                vad_analyzer=SileroVADAnalyzer(
                    params=VADParams(
                        min_volume=0.3,  # raised from 0.2 — filters background noise on telephony (vol-03)
                        start_secs=0.4,  # barge-in fires ~50ms after speech — keep fast
                        stop_secs=0.8,   # raised from 0.55 — allows natural pauses in long monologues without adding too much latency on short turns
                        # Architecture note: Silero VAD is NOT redundant with Deepgram
                        # endpointing — they serve different roles.
                        # Silero: fast barge-in (~50ms after speech onset, vs 300-600ms for
                        #   Deepgram's first partial) and noise gating (prevents keyboard/
                        #   room noise from producing spurious STT transcripts).
                        # Deepgram endpointing=700: authoritative turn-end inside the audio
                        #   stream; drives is_final=True which flushes the aggregator.
                        # Turn boundary = max(stop_secs, endpointing) = max(800ms, 700ms) = 800ms.
                        # Do NOT remove Silero — without it barge-in degrades by 250-550ms
                        # and noise gating is lost.
                    )
                ),
            ),
        )
        logger.info("[DEMO] Context aggregator created")

        barge_handler = BargeInHandler()
        stt_watchdog = STTWatchdog()
        stt_watchdog.set_task(asyncio.ensure_future(stt_watchdog._monitor()))
        stt_confidence_tracker = STTConfidenceTracker(brain_service=brain)
        tts_watchdog = TTSStreamWatchdog()
        silence_reprompt = SilenceReprompt(call_sid=getattr(brain, "call_sid", ""))
        tools_broadcaster = BrowserToolsBroadcaster(websocket=websocket)
        # Phase 9 A1: stamp tts_first_byte_at on the first TTSAudioRawFrame per turn
        tts_timing = TTSTimingProcessor(
            state_provider=lambda: getattr(
                getattr(brain, "turn_processor", None), "state", None
            )
        )

        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                stt_watchdog,           # alert + apology if Deepgram stops delivering transcripts
                stt_confidence_tracker, # capture per-utterance Deepgram confidence for reprompt logic
                silence_reprompt,       # caller-silence reprompt (12s) → graceful end_call (+8s)
                barge_handler,          # suppress interruptions during greeting, enable after
                context_aggregator.user(),
                brain,
                tools_broadcaster,      # intercept [TOOLSDATA:...] markers → WS tools_called message
                tts,
                tts_timing,             # Phase 9 A1: stamp tts_first_byte_at on first audio chunk
                tts_watchdog,           # alert + ErrorFrame if TTS stream dies mid-sentence
                transport.output(),
                context_aggregator.assistant(),
            ]
        )
        logger.info("[DEMO] Pipeline created")

        runner = PipelineRunner()
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_out_sample_rate=24000,
                allow_interruptions=True,
                enable_metrics=True,
            ),
            idle_timeout_secs=120,
        )

        # Cancel the pipeline immediately when the browser tab closes the WS
        # (e.g. user clicks hang-up). Without this, the pipeline runs until
        # the 120s idle_timeout fires, and the call won't land in
        # google_calls / google_turn_metrics until then.
        @transport.event_handler("on_client_disconnected")
        async def _on_client_disconnected(_transport, _client):
            logger.info("[DEMO] Client disconnected → cancelling pipeline")
            try:
                await task.cancel()
            except Exception as e:
                logger.warning(f"[DEMO] task.cancel() failed: {e}")

        logger.info("[DEMO] Starting pipeline")
        await runner.run(task)
        logger.info("[DEMO] Pipeline ended normally")

    except WebSocketDisconnect:
        logger.info("[DEMO] WebSocket disconnected")
    except Exception as e:
        logger.error(f"[DEMO] Error: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        _active_ws_connections.discard(conn_id)
        if brain is not None:
            try:
                await brain._finalize_session("client_disconnect")
                logger.info("[DEMO] Session finalized")
            except Exception as fin_err:
                logger.warning(f"[DEMO] Session finalize error: {fin_err}")
            # Capture low-quality calls as production failure scenarios for the validation heal loop
            try:
                _capture_production_failure_if_needed(brain, conn_id)
            except Exception as cap_err:
                logger.debug(f"[DEMO] Failure capture skipped: {cap_err}")
        logger.info(f"[DEMO] Call ended (active: {len(_active_ws_connections)})")


# ── TEST ONLY: WebSocket text injection endpoint for regression harness ────────
# CRITICAL: This endpoint MUST be disabled in production. It allows direct text
# injection for testing purposes, bypassing audio/STT.
@app.websocket("/ws/demo_text")
async def websocket_demo_text(websocket: WebSocket):
    """
    Dev-only text injection endpoint for regression harness.
    Accepts JSON {"type": "user_text", "text": "..."} instead of binary audio.
    This endpoint is TEST ONLY and should be disabled in production via firewall rules.
    """
    logger.info("[DEMO_TEXT] Connection attempt — accepting")
    await websocket.accept()
    conn_id = id(websocket)
    _active_ws_connections.add(conn_id)
    logger.info(f"[DEMO_TEXT] New WebSocket connection (active: {len(_active_ws_connections)})")

    brain = None
    try:
        # Handshake (same as /ws/demo)
        try:
            handshake = await websocket.receive_json()
            tenant_id = handshake.get("tenant", "doboo")
            logger.info(f"[DEMO_TEXT] Handshake: tenant={tenant_id}")
        except Exception as e:
            logger.error(f"[DEMO_TEXT] Handshake error: {e}")
            await websocket.send_json(
                {"error": "Invalid handshake", "message": str(e)}
            )
            return

        deepgram_api_key = get_secret("deepgram-api-key", default="")
        google_project_id = os.environ.get(
            "GOOGLE_CLOUD_PROJECT", "sailly-voice-agent-eu"
        )
        google_credentials_path = os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "/home/charles2/.ssh/sailly-voice-agent-key.json",
        )

        if not deepgram_api_key:
            logger.error("[DEMO_TEXT] deepgram-api-key secret not configured")
            await websocket.send_json({"error": "Server config error: Deepgram key missing"})
            return

        # Use a text-passthrough transport instead of audio
        from pipecat.transports.base_transport import BaseTransport, TransportParams
        from pipecat.frames.frames import Frame, TranscriptionFrame, AudioRawFrame

        class TextInjectTransport(BaseTransport):
            """Minimal transport that accepts text frames instead of audio."""
            def __init__(self, websocket, params):
                super().__init__(params)
                self._ws = websocket
                self._input_queue = asyncio.Queue()

            async def _send_message(self, frame: Frame):
                if isinstance(frame, (TranscriptionFrame, AudioRawFrame)):
                    # Serialize outgoing frames as JSON for the harness
                    if isinstance(frame, TranscriptionFrame):
                        msg = {
                            "type": "transcript",
                            "speaker": "bot",
                            "text": frame.text
                        }
                        await self._ws.send_json(msg)

            async def _read_message(self):
                try:
                    msg = await asyncio.wait_for(self._ws.recv(), timeout=60)
                    if isinstance(msg, str):
                        data = json.loads(msg)
                        if data.get("type") == "user_text":
                            # Inject as a fake transcription frame
                            return TranscriptionFrame(
                                text=data.get("text", ""),
                                confidence=1.0,
                                language="de"
                            )
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.warning(f"[DEMO_TEXT] Read error: {e}")
                return None

            def input(self):
                return self._input_queue

            def output(self):
                return self._input_queue

        # Create a minimal transport using standard FastAPI adapter (reuse existing)
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                serializer=BrowserFrameSerializer(),
                audio_in_enabled=False,  # no real audio
                audio_out_enabled=True,
            ),
        )
        logger.info("[DEMO_TEXT] Transport created (text mode)")

        # For text mode, we bypass STT and inject text directly
        # so we use a "pass-through" STT that just echoes the text
        class TextPassthroughSTT:
            """Fake STT for text injection — emits transcript frames directly."""
            def __init__(self):
                self._input = asyncio.Queue()

            async def _process(self, frame):
                if isinstance(frame, TranscriptionFrame):
                    # Forward as-is
                    await self.push_frame(frame)

            def input(self):
                return self._input

        _stt_lang = "de"
        try:
            from server.core.tenant_config import TenantRegistry
            _tc = TenantRegistry().load_tenant(tenant_id)
            _stt_lang = _tc.stt_language or "de"
        except Exception as _tl_err:
            logger.warning(f"[DEMO_TEXT] could not resolve tenant={tenant_id}: {_tl_err!r}")

        # Use real STT but with text injection (Deepgram will receive synthetic "audio")
        _tc_text = None
        _stt_keywords_text: list = []
        try:
            from server.core.tenant_config import TenantRegistry as _TR2
            _tc_text = _TR2().load_tenant(tenant_id)
            from server.brain.stt.keyterm_loader import get_keyterms_for_tenant as _gkt
            _stt_keywords_text = _gkt(tenant_id)
        except Exception as _tl_err2:
            logger.warning(f"[DEMO_TEXT] could not resolve tenant={tenant_id}: {_tl_err2!r}")
        from server.brain.stt.deepgram_client import build_stt_settings as _bss, get_stt_endpoint as _gse
        _dg_text_kwargs: dict = _bss(_tc_text) if _tc_text is not None else dict(
            model="nova-3", language=_stt_lang, endpointing=700,
            interim_results=True, punctuate=True, smart_format=True,
        )
        if _stt_keywords_text:
            _dg_text_kwargs["keyterm"] = _stt_keywords_text
        _stt_endpoint_text = _gse(_tc_text) if _tc_text is not None else None
        _dg_svc_kwargs: dict = dict(api_key=deepgram_api_key, settings=DeepgramSTTService.Settings(**_dg_text_kwargs))
        if _stt_endpoint_text:
            _dg_svc_kwargs["base_url"] = _stt_endpoint_text
        stt = DeepgramSTTService(**_dg_svc_kwargs)
        logger.info(f"[DEMO_TEXT] STT service created (model={_dg_text_kwargs.get('model')}, endpoint={_stt_endpoint_text or 'default'})")

        brain = BrowserBrainService(tenant_id=tenant_id)
        logger.info("[DEMO_TEXT] Brain service created")

        # Send session init with call_sid
        try:
            await websocket.send_json({
                "type": "session_init",
                "call_sid": brain.call_sid,
            })
            logger.info(f"[DEMO_TEXT] Session init sent: call_sid={brain.call_sid}")
        except Exception as e:
            logger.warning(f"[DEMO_TEXT] Failed to send session_init: {e}")

        tts = SaillyGeminiTTSService(
            credentials_path=google_credentials_path,
            project_id=google_project_id,
            cascade_speaking_rate=DEFAULT_GEMINI_TTS_SPEAKING_RATE,
            settings=GeminiTTSService.Settings(
                model="gemini-2.5-flash-tts",
                language="de-DE",
                voice="Kore",
                prompt=CASCADE_TTS_STYLE_PROMPT,
            ),
        )
        brain.tts_service = tts
        logger.info("[DEMO_TEXT] TTS service created")

        # Context aggregator with VAD
        context = LLMContext()
        context_aggregator = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(
                vad_analyzer=SileroVADAnalyzer(
                    params=VADParams(
                        min_volume=0.3,  # raised from 0.2 — filters background noise on telephony (vol-03)
                        start_secs=0.4,
                        stop_secs=0.8,
                    )
                ),
            ),
        )
        logger.info("[DEMO_TEXT] Context aggregator created")

        barge_handler = BargeInHandler()
        stt_watchdog = STTWatchdog()
        stt_watchdog.set_task(asyncio.ensure_future(stt_watchdog._monitor()))
        stt_confidence_tracker = STTConfidenceTracker(brain_service=brain)
        tts_watchdog = TTSStreamWatchdog()
        silence_reprompt = SilenceReprompt(call_sid=getattr(brain, "call_sid", ""))
        tools_broadcaster = BrowserToolsBroadcaster(websocket=websocket)
        # Phase 9 A1: stamp tts_first_byte_at on the first TTSAudioRawFrame per turn
        tts_timing = TTSTimingProcessor(
            state_provider=lambda: getattr(
                getattr(brain, "turn_processor", None), "state", None
            )
        )

        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                stt_watchdog,
                stt_confidence_tracker,
                silence_reprompt,
                barge_handler,
                context_aggregator.user(),
                brain,
                tools_broadcaster,
                tts,
                tts_timing,             # Phase 9 A1: stamp tts_first_byte_at on first audio chunk
                tts_watchdog,
                transport.output(),
            ]
        )
        logger.info("[DEMO_TEXT] Pipeline created")

        runner = PipelineRunner()
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_out_sample_rate=24000,
                allow_interruptions=True,
                enable_metrics=True,
            ),
            idle_timeout_secs=120,
        )

        @transport.event_handler("on_client_disconnected")
        async def _on_client_disconnected(_transport, _client):
            logger.info("[DEMO_TEXT] Client disconnected → cancelling pipeline")
            try:
                await task.cancel()
            except Exception as e:
                logger.warning(f"[DEMO_TEXT] task.cancel() failed: {e}")

        logger.info("[DEMO_TEXT] Starting pipeline")
        await runner.run(task)
        logger.info("[DEMO_TEXT] Pipeline ended normally")

    except WebSocketDisconnect:
        logger.info("[DEMO_TEXT] WebSocket disconnected")
    except Exception as e:
        logger.error(f"[DEMO_TEXT] Error: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        _active_ws_connections.discard(conn_id)
        if brain is not None:
            try:
                await brain._finalize_session("client_disconnect")
                logger.info("[DEMO_TEXT] Session finalized")
            except Exception as fin_err:
                logger.warning(f"[DEMO_TEXT] Session finalize error: {fin_err}")
        logger.info(f"[DEMO_TEXT] Call ended (active: {len(_active_ws_connections)})")


@app.websocket("/ws/headless")
async def websocket_headless(websocket: WebSocket, tenant: str = "doboo"):
    """
    Headless text-injection endpoint for regression harness (Task B1).

    Accepts JSON {"type": "user_text", "text": "..."} messages.
    Returns {"type": "bot_text", "text": "...", "tools_fired": [...]} per turn.
    No audio, no STT, no TTS — pure LLM path only.

    TEST ONLY — disable in production via firewall/nginx.
    """
    await websocket.accept()
    conn_id = id(websocket)
    _active_ws_connections.add(conn_id)
    logger.info(f"[HEADLESS] New connection (tenant={tenant})")
    try:
        from server.brain.layer1.text_mode_runner import TextModeRunner
        runner = TextModeRunner(websocket=websocket, tenant_id=tenant)
        await runner.run()
    except Exception as exc:
        logger.error(f"[HEADLESS] Unhandled error: {exc}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        _active_ws_connections.discard(conn_id)
        logger.info(f"[HEADLESS] Connection closed (active: {len(_active_ws_connections)})")


# ── Dashboard API routes (Redis-backed monitoring & live trace) ───────────────
# These mirror the production voice agent's /api/dashboard/* routes so the
# dashboard works even when the production agent is unavailable.
# Nginx already routes /api/dashboard/ to port 3003 (production); these endpoints
# on port 8080 are reachable via /demo-api/dashboard/* for the demo-specific data.

@app.get("/api/dashboard/monitor")
async def demo_monitor_overview(window: Optional[int] = Query(None)):
    """Live pipeline health from Redis — covers browser demo calls."""
    try:
        from server.monitoring import get_monitor_overview_bundle
        bundle = await get_monitor_overview_bundle(window_secs=window)
        return JSONResponse(content=bundle)
    except Exception as e:
        logger.error(f"[DEMO] monitor overview error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/dashboard/monitor/calls")
async def demo_monitor_calls(
    window: int = Query(86400, ge=60, le=86400 * 14),
    limit: int = Query(100, ge=1, le=500),
):
    """Recent completed calls from Redis (includes browser demo calls)."""
    try:
        from server.monitoring import get_recent_monitoring_calls
        rows = await get_recent_monitoring_calls(window_secs=window, limit=limit)
        return JSONResponse(content={"calls": rows, "count": len(rows)})
    except Exception as e:
        logger.error(f"[DEMO] monitor calls error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/dashboard/live/{call_sid}/trace")
async def demo_live_call_trace(
    call_sid: str,
    tenant: Optional[str] = Query(None),
):
    """Live call timeline for one call from Redis."""
    try:
        from server.session import get_redis
        from server.live_call_trace import fetch_live_trace

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        r = await get_redis(redis_url)
        resolved_tenant = tenant if tenant and tenant != "_" else None
        events = await fetch_live_trace(r, resolved_tenant, call_sid)
        return JSONResponse(content={"events": events, "call_sid": call_sid})
    except Exception as e:
        logger.error(f"[DEMO] live trace error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


def _capture_production_failure_if_needed(brain, conn_id: int) -> None:
    """
    If the session had enough turns but poor quality indicators, write a failure
    record to /tmp/validation_runs/production_failures/ so the heal loop can harvest it.
    Failure criteria: session had >= 3 turns AND ended abnormally (no goodbye detected).
    """
    import time as _time
    try:
        state = brain.state if hasattr(brain, "state") else None
        if state is None:
            return
        # Require minimum meaningful conversation
        turn_count = getattr(state, "turn_count", 0)
        if turn_count < 3:
            return
        # Check if call ended properly (goodbye detected = success)
        ended_properly = getattr(state, "goodbye_detected", False) or getattr(state, "end_call_requested", False)
        if ended_properly:
            return
        # Gather transcript for context
        transcript = []
        if hasattr(state, "conversation_history"):
            transcript = [
                {"role": m.get("role", ""), "content": m.get("content", "")}
                for m in (state.conversation_history or [])
                if m.get("content")
            ]
        if not transcript:
            return
        failures_dir = os.path.join("/tmp/validation_runs", "production_failures")
        os.makedirs(failures_dir, exist_ok=True)
        record = {
            "source": "browser_demo",
            "captured_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
            "conn_id": conn_id,
            "turn_count": turn_count,
            "transcript": transcript,
            "tenant": getattr(state, "tenant_id", "doboo"),
            "failure_type": "incomplete_call",
            "scenario_id": f"prod-fail-{conn_id}",
        }
        out_path = os.path.join(failures_dir, f"fail_{conn_id}_{int(_time.time())}.json")
        with open(out_path, "w") as f:
            import json as _json
            _json.dump(record, f, indent=2)
        logger.info(f"[DEMO] Production failure captured → {out_path}")
    except Exception as e:
        logger.debug(f"[DEMO] Failure capture error: {e}")


# Phase 9 B5 — Health endpoints mounted via router
try:
    from server.brain.health import router as health_router
    app.include_router(health_router)
except Exception as _he:
    logger.warning(f"[DEMO] health_router mount failed: {_he!r}")


@app.get("/healthz")
async def healthz():
    """Extended health check — includes active WebSocket connection count for blue-green drain logic."""
    port = int(os.environ.get("DEMO_PORT", "8080"))
    return {
        "status": "ok",
        "service": "sailly-browser-demo",
        "port": port,
        "active_ws_connections": len(_active_ws_connections),
    }


@app.get("/active-calls")
async def active_calls():
    """Phase 9 C3 — active call count for rolling deploy drain logic."""
    return {"count": len(_active_ws_connections)}


@app.post("/voice")
async def twilio_voice_entry(request: Request):
    """
    Phase 9 B4 — Twilio voice webhook entry point with per-caller rate limiting.

    Twilio POSTs here when a call arrives.  Rate-limited callers receive a
    TwiML Say + Hangup.  Allowed callers are forwarded to the media-streams
    router (mounted via twilio_handler if available).
    """
    from fastapi.responses import Response as _Response
    try:
        form = await request.form()
        from_number = str(form.get("From") or "")
    except Exception:
        from_number = ""

    from server.brain.rate_limit import check_rate_limit, rate_limit_response_xml
    if not check_rate_limit(from_number):
        logger.warning(
            "rate_limited_call",
            extra={"phone_tail": from_number[-4:] if from_number else ""},
        )
        return _Response(content=rate_limit_response_xml(), media_type="application/xml")

    # Delegate to Twilio handler for normal call flow
    twiml = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<Response>"
        "<Connect><Stream url='wss://{host}/ws/twilio'/></Connect>"
        "</Response>"
    ).format(host=request.headers.get("host", "localhost"))
    return _Response(content=twiml, media_type="application/xml")


# ─────────────────────────────────────────────────────────────────────────────
# Admin endpoints — menu 86 (out-of-stock) management.
#
# These endpoints are protected by a shared secret (ADMIN_API_TOKEN env var).
# The dashboard front-end calls them; they can also be POSTed by operations
# tooling (e.g. a simple curl from the kitchen tablet).
#
# Data model: Redis hash per tenant, ``menu_unavailable:{tenant_id}``.
#   field = dish name (canonical, any case — we store as given and match
#           case-insensitively at read time)
#   value = ISO8601 timestamp of when it was taken down
# ─────────────────────────────────────────────────────────────────────────────


def _check_admin_token(token: Optional[str]) -> bool:
    expected = os.getenv("ADMIN_API_TOKEN", "").strip()
    if not expected:
        # No token configured → refuse all admin writes. Deliberately fail
        # closed so a missing env var can't accidentally expose 86 controls.
        return False
    return bool(token) and token.strip() == expected


async def _get_redis():
    import redis.asyncio as aioredis
    return aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )


@app.get("/api/admin/menu/86/{tenant_id}")
async def list_86_items(tenant_id: str):
    """Return the current set of 86'd dishes for a tenant.

    Read-only — no auth required (dashboards may poll this to show a banner
    like "3 items out of stock").
    """
    key = f"menu_unavailable:{tenant_id}"
    try:
        r = await _get_redis()
        try:
            data = await r.hgetall(key)
        finally:
            await r.aclose()
    except Exception as e:
        logger.warning(f"[ADMIN-86] list failed: {e!r}")
        return JSONResponse(status_code=503, content={"error": "redis_unavailable"})
    return {"tenant_id": tenant_id, "unavailable": data or {}}


@app.post("/api/admin/menu/86/{tenant_id}/{dish_name}")
async def mark_dish_unavailable(tenant_id: str, dish_name: str, request: Request):
    """Mark `dish_name` as unavailable for `tenant_id` (kitchen 86's it).

    Header `X-Admin-Token` must match ADMIN_API_TOKEN. The value stored is
    the ISO-8601 UTC timestamp so the dashboard can show "86'd 3h ago".
    """
    if not _check_admin_token(request.headers.get("x-admin-token")):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    key = f"menu_unavailable:{tenant_id}"
    import datetime as _dt
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    try:
        r = await _get_redis()
        try:
            await r.hset(key, dish_name.strip(), ts)
        finally:
            await r.aclose()
    except Exception as e:
        logger.warning(f"[ADMIN-86] mark failed: {e!r}")
        return JSONResponse(status_code=503, content={"error": "redis_unavailable"})
    logger.info(f"[ADMIN-86] tenant={tenant_id!r} dish={dish_name!r} → 86'd at {ts}")
    return {"ok": True, "tenant_id": tenant_id, "dish": dish_name, "since": ts}


@app.post("/api/admin/purge/transcripts")
async def admin_purge_transcripts(request: Request):
    """Run the GDPR transcript purge synchronously. Returns row counts.

    Useful for ops to force-drain right after a retention-policy change
    without waiting for the 6-hour background tick.
    """
    if not _check_admin_token(request.headers.get("x-admin-token")):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    try:
        from server.transcript_purge import purge_task
        summary = await purge_task.purge_once()
        return {"ok": True, **summary}
    except Exception as e:
        logger.error(f"[ADMIN-PURGE] failed: {e!r}")
        return JSONResponse(status_code=500, content={"error": repr(e)})


@app.delete("/api/admin/menu/86/{tenant_id}/{dish_name}")
async def restore_dish_available(tenant_id: str, dish_name: str, request: Request):
    """Restore a previously 86'd dish (kitchen got restocked)."""
    if not _check_admin_token(request.headers.get("x-admin-token")):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    key = f"menu_unavailable:{tenant_id}"
    try:
        r = await _get_redis()
        try:
            removed = await r.hdel(key, dish_name.strip())
        finally:
            await r.aclose()
    except Exception as e:
        logger.warning(f"[ADMIN-86] restore failed: {e!r}")
        return JSONResponse(status_code=503, content={"error": "redis_unavailable"})
    logger.info(f"[ADMIN-86] tenant={tenant_id!r} dish={dish_name!r} → restored")
    return {"ok": True, "removed": bool(removed)}


def _check_admin_role(token: Optional[str], required: str = "read") -> bool:
    """RBAC over the single admin token.

    Tokens take the form ``<role>:<secret>`` where ``role`` is one of
    ``read`` / ``write`` / ``admin``.  For backwards compatibility, a bare
    token (no colon) is treated as ``admin``.  The secret is compared
    against ``ADMIN_API_TOKEN`` env var as before.
    """
    if not token:
        return False
    role, _, secret = token.strip().partition(":")
    if not secret:
        role, secret = "admin", token.strip()
    expected = os.getenv("ADMIN_API_TOKEN", "").strip()
    if not expected or secret != expected:
        return False
    levels = {"read": 0, "write": 1, "admin": 2}
    return levels.get(role, -1) >= levels.get(required, 0)


@app.delete("/api/admin/subject")
async def delete_subject_data(request: Request):
    """GDPR right-to-erasure endpoint.

    Requires admin role.  Deletes all call data tied to a phone number
    across Redis (sessions, transcripts, CRM, transfer context) and
    Postgres (google_calls + cascaded google_transcripts / google_turn_metrics
    / tool_calls via ON DELETE CASCADE).

    Query params:
      - phone: E.164 phone number (required)
      - tenant_id: Optional, restrict deletion to one tenant's data
    """
    if not _check_admin_role(request.headers.get("x-admin-token"), required="admin"):
        return JSONResponse(status_code=401, content={"error": "unauthorized_admin"})
    phone = (request.query_params.get("phone") or "").strip()
    tenant_id = (request.query_params.get("tenant_id") or "").strip() or None
    if not phone:
        return JSONResponse(status_code=400, content={"error": "phone_required"})

    deleted = {"postgres_calls": 0, "redis_keys": 0}

    try:
        from server.database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            res = await conn.execute(
                "DELETE FROM google_calls WHERE caller = $1 OR from_number = $1",
                phone,
            )
            try:
                deleted["postgres_calls"] = int(res.split()[-1])
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[ADMIN-ERASURE] postgres cascade failed: {e}")

    try:
        r = await _get_redis()
        try:
            pattern_keys = [f"caller:{phone}", f"crm:caller:{phone}"]
            if tenant_id:
                pattern_keys.append(f"caller:{tenant_id}:{phone}")
            removed = 0
            for k in pattern_keys:
                try:
                    removed += await r.delete(k)
                except Exception:
                    continue
            deleted["redis_keys"] = int(removed)
        finally:
            await r.aclose()
    except Exception as e:
        logger.warning(f"[ADMIN-ERASURE] redis delete failed: {e}")

    logger.info(
        f"[ADMIN-ERASURE] phone=*** tenant={tenant_id!r} deleted={deleted}"
    )
    return {"ok": True, "phone_masked": True, "deleted": deleted}


@app.get("/api/admin/transfer/{call_sid}")
async def get_transfer_context(call_sid: str):
    """Return the warm-transfer context for ``call_sid`` as JSON.

    Written by ``tools.executor._transfer_to_human`` to Redis under
    ``transfer_ctx:{call_sid}`` with 1h TTL.  Read-only; intended for a
    human agent opening this URL right after a warm transfer.
    """
    try:
        r = await _get_redis()
        try:
            raw = await r.get(f"transfer_ctx:{call_sid}")
        finally:
            await r.aclose()
    except Exception as e:
        logger.warning(f"[ADMIN-TRANSFER] redis read failed: {e!r}")
        return JSONResponse(status_code=503, content={"error": "redis_unavailable"})
    if not raw:
        return JSONResponse(status_code=404, content={"error": "not_found", "call_sid": call_sid})
    try:
        import json as _json
        return _json.loads(raw)
    except Exception:
        return JSONResponse(status_code=500, content={"error": "corrupt_payload"})


@app.get("/api/admin/call/{call_sid}/turns")
async def get_call_turns(call_sid: str):
    """JSON: per-turn metrics for a specific call.  Powers the turn-viewer UI.

    Joins ``google_turn_metrics`` with ``google_transcripts`` so each row
    includes the raw user text + ASR confidence + latencies + tool calls
    + build_sha that produced it.
    """
    try:
        from server.database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    turn_number, user_text, bot_text,
                    stt_latency_ms, llm_latency_ms, total_latency_ms,
                    tools_called, node_name, stage3_text,
                    stt_confidence, build_sha, tenant_id, created_at
                FROM google_turn_metrics
                WHERE call_sid = $1
                ORDER BY turn_number ASC
                """,
                call_sid,
            )
    except Exception as e:
        logger.warning(f"[ADMIN-TURNS] query failed: {e!r}")
        return JSONResponse(status_code=503, content={"error": "db_unavailable"})
    if not rows:
        return JSONResponse(
            status_code=404,
            content={"error": "no_turns", "call_sid": call_sid},
        )
    import json as _json
    turns = []
    for r in rows:
        tc = r["tools_called"]
        if isinstance(tc, str):
            try:
                tc = _json.loads(tc)
            except Exception:
                tc = []
        turns.append(
            {
                "turn_number": r["turn_number"],
                "user_text": r["user_text"] or "",
                "bot_text": r["bot_text"] or "",
                "stt_latency_ms": r["stt_latency_ms"],
                "llm_latency_ms": r["llm_latency_ms"],
                "total_latency_ms": r["total_latency_ms"],
                "tools_called": tc or [],
                "node_name": r["node_name"],
                "stt_confidence": r["stt_confidence"],
                "build_sha": r["build_sha"],
                "tenant_id": r["tenant_id"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )
    return {"call_sid": call_sid, "turn_count": len(turns), "turns": turns}


@app.get("/admin/call/{call_sid}", response_class=HTMLResponse)
async def render_call_viewer(call_sid: str):
    """Minimal HTML per-turn viewer for one call — the "open a call, see every
    turn with ASR / LLM / tools / latency" page.  Read-only.
    """
    try:
        from server.database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    turn_number, user_text, bot_text,
                    stt_latency_ms, llm_latency_ms, total_latency_ms,
                    tools_called, node_name, stt_confidence,
                    build_sha, tenant_id, created_at
                FROM google_turn_metrics
                WHERE call_sid = $1
                ORDER BY turn_number ASC
                """,
                call_sid,
            )
    except Exception as e:
        return HTMLResponse(
            status_code=503, content=f"<h1>DB unavailable</h1><p>{e}</p>"
        )
    if not rows:
        return HTMLResponse(
            status_code=404,
            content=(
                f"<h1>Kein Turn-Protokoll für {call_sid}</h1>"
                "<p>Call unbekannt oder zu alt (Daten purgt nach 90 Tagen).</p>"
            ),
        )
    from html import escape as _esc
    import json as _json

    def _fmt_conf(v) -> str:
        if v is None:
            return "—"
        try:
            return f"{float(v):.2f}"
        except Exception:
            return str(v)

    turn_rows_html = ""
    for r in rows:
        tc = r["tools_called"]
        if isinstance(tc, str):
            try:
                tc = _json.loads(tc)
            except Exception:
                tc = []
        tc = tc or []
        tc_str = ", ".join(
            t.get("name") if isinstance(t, dict) else str(t) for t in tc
        ) or "—"
        low_conf = (r["stt_confidence"] or 1.0) < 0.55
        highlight = ' style="background:#fff3f0"' if low_conf else ""
        turn_rows_html += f"""
<tr{highlight}>
  <td style="text-align:center">{r['turn_number']}</td>
  <td>{_esc(r['user_text'] or '—')}</td>
  <td style="color:#0b4a99">{_esc(r['bot_text'] or '—')}</td>
  <td style="text-align:center">{_fmt_conf(r['stt_confidence'])}</td>
  <td style="text-align:center">{r['stt_latency_ms'] or 0}</td>
  <td style="text-align:center">{r['llm_latency_ms'] or 0}</td>
  <td style="text-align:center">{r['total_latency_ms'] or 0}</td>
  <td>{_esc(tc_str)}</td>
  <td>{_esc(r['node_name'] or '—')}</td>
  <td style="font-family:monospace;font-size:0.8rem">{_esc(r['build_sha'] or '—')}</td>
</tr>
"""
    body = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<title>Call {_esc(call_sid)}</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1280px; margin: 1.5rem auto; padding: 0 1rem; color: #1a1a1a; }}
  h1 {{ font-size: 1.3rem; margin-bottom: 0.3rem; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1.2rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  th {{ text-align: left; background: #f5f5f5; padding: 6px 8px; border-bottom: 2px solid #ddd; font-weight: 600; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #eee; vertical-align: top; }}
  tr:hover {{ background: #fafafa; }}
  .hint {{ color: #888; font-size: 0.85rem; margin-top: 0.5rem; }}
</style></head><body>
<h1>Call Turn-Viewer</h1>
<div class="meta">Call-ID: <code>{_esc(call_sid)}</code> • Turns: {len(rows)} • Tenant: {_esc(rows[0]['tenant_id'] or '—')}</div>
<table>
  <thead><tr>
    <th>#</th><th>User</th><th>Bot</th><th>ASR conf</th>
    <th>STT ms</th><th>LLM ms</th><th>Total ms</th><th>Tools</th><th>Node</th><th>build</th>
  </tr></thead>
  <tbody>{turn_rows_html}</tbody>
</table>
<p class="hint">Zeilen mit rotem Hintergrund: ASR-Confidence &lt; 0.55.</p>
</body></html>"""
    return HTMLResponse(content=body)


@app.get("/admin/transfer/{call_sid}", response_class=HTMLResponse)
async def render_transfer_context(call_sid: str):
    """Minimal HTML viewer for a warm transfer.  Intended for a human agent
    who just picked up a forwarded call; shows the caller's intent, known
    slots, what's still missing, and the last few bot lines."""
    try:
        r = await _get_redis()
        try:
            raw = await r.get(f"transfer_ctx:{call_sid}")
        finally:
            await r.aclose()
    except Exception as e:
        return HTMLResponse(
            status_code=503,
            content=f"<h1>Redis unavailable</h1><p>{e}</p>",
        )
    if not raw:
        return HTMLResponse(
            status_code=404,
            content=(
                f"<h1>Kein Kontext für {call_sid}</h1>"
                "<p>Entweder war die Weiterleitung vor mehr als 1 Stunde "
                "oder die Call-ID stimmt nicht.</p>"
            ),
        )
    try:
        import json as _json
        from html import escape as _esc
        payload = _json.loads(raw)
    except Exception as e:
        return HTMLResponse(status_code=500, content=f"<h1>Corrupt payload</h1><p>{e}</p>")

    def _fmt_lines(block: str) -> str:
        if not block:
            return "<em>—</em>"
        return "<br>".join(_esc(line) for line in str(block).splitlines())

    transcript_html = ""
    for line in payload.get("recent_transcript") or []:
        transcript_html += f"<li>{_esc(str(line))}</li>"
    if not transcript_html:
        transcript_html = "<li><em>keine Einträge</em></li>"

    body = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<title>Transfer {_esc(call_sid)}</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }}
  .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 1rem; }}
  .card h2 {{ font-size: 1rem; margin: 0 0 0.5rem; color: #555; text-transform: uppercase; letter-spacing: 0.05em; }}
  .grid {{ display: grid; grid-template-columns: 150px 1fr; gap: 0.4rem 1rem; }}
  .grid dt {{ color: #888; font-weight: 500; }}
  .grid dd {{ margin: 0; font-weight: 500; }}
  ul.transcript {{ margin: 0; padding-left: 1.2rem; }}
  ul.transcript li {{ margin-bottom: 0.25rem; color: #444; }}
  .intent {{ display: inline-block; padding: 2px 10px; border-radius: 12px; background: #e7f0ff; color: #0b4a99; font-size: 0.85rem; font-weight: 600; }}
</style></head><body>
<h1>Warm-Transfer Kontext</h1>
<div class="meta">Call-ID: <code>{_esc(call_sid)}</code> • Gebaut: {_esc(str(payload.get("built_at") or ""))} • Grund: {_esc(str(payload.get("reason") or ""))}</div>

<div class="card">
  <h2>Absicht</h2>
  <span class="intent">{_esc(str(payload.get("intent") or "unknown"))}</span>
</div>

<div class="card">
  <h2>Bekannte Daten</h2>
  <dl class="grid">
    <dt>Name</dt><dd>{_esc(str(payload.get("customer_name") or "—"))}</dd>
    <dt>Telefon</dt><dd>{_esc(str(payload.get("phone_number") or payload.get("caller_phone") or "—"))}</dd>
    <dt>Adresse</dt><dd>{_esc(str(payload.get("delivery_address") or "—"))}</dd>
    <dt>Gericht</dt><dd>{_esc(str(payload.get("selected_dish") or "—"))}</dd>
    <dt>Menge</dt><dd>{_esc(str(payload.get("order_quantity") or "—"))}</dd>
  </dl>
  <h2 style="margin-top: 1rem">Slot-Zusammenfassung</h2>
  <p>{_fmt_lines(payload.get("slots_known", ""))}</p>
  <h2 style="margin-top: 1rem">Noch fehlend</h2>
  <p>{_fmt_lines(payload.get("slots_missing", ""))}</p>
</div>

<div class="card">
  <h2>Letzte Bot-Zeilen</h2>
  <ul class="transcript">{transcript_html}</ul>
</div>

</body></html>"""
    return HTMLResponse(content=body)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DEMO_PORT", "8080"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
