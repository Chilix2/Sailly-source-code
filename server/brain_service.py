"""
Thin Pipecat wrapper around ADKTurnProcessor (validated brain).

Receives user text, delegates to ADKTurnProcessor.process_turn(),
emits LLMTextFrame for TTS + OutputTransportMessageFrame for browser transcript.
Wired to CallSession (Redis) for call history in dashboard.
Writes to PostgreSQL on session end so demo calls appear in Call History page.
"""

import asyncio
import json
import logging
import os
import re
import time
import time as _time
import uuid
from pathlib import Path

from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import (
    LLMContextFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
    LLMTextFrame,
    EndFrame,
    StartFrame,
    OutputTransportMessageFrame,
    TTSAudioRawFrame,
)

import re as _re

from server.sailly_gemini_tts import _CHARS_PER_SEC_DE


class LatencyTimer:
    """Monotonic timer for profiling pipeline stages across a turn.

    Emits [LAT-2026-04-20] logs with stage-to-stage deltas AND stores each
    mark's absolute monotonic time so the caller can compute per-stage ms
    for DB persistence (google_turn_metrics.stt_latency_ms, etc.).
    """
    def __init__(self, call_sid: str, turn: int):
        self._call_sid = call_sid
        self._turn = turn
        self._prev_name: str | None = None
        self._prev_t: float | None = None
        self.marks: dict[str, float] = {}  # mark_name → monotonic seconds

    def mark(self, name: str) -> None:
        """Record a timing mark. If not the first mark, log delta from previous."""
        t = _time.monotonic()
        self.marks[name] = t
        if self._prev_t is not None:
            delta_ms = (t - self._prev_t) * 1000
            logger.info(
                f"[LAT-2026-04-20] call={self._call_sid} turn={self._turn} "
                f"{self._prev_name}->{name}={delta_ms:.0f}ms"
            )
        self._prev_name = name
        self._prev_t = t

from server.brain.v4_turn_processor import V4TurnProcessor as ADKTurnProcessor
from server.brain.conversation_state import strip_tool_call_leakage as _strip_tool_call_leakage


def _sanitize_for_tts(text: str) -> str:
    """Trim, collapse whitespace and control chars before handing text to Gemini TTS.

    Returns an empty string when the fragment is too short to synthesize meaningfully
    (single letters / stray punctuation cause 9+ second silent timeouts at the API).
    """
    if not text:
        return ""
    # Drop control characters (keep newlines collapsed to space)
    cleaned = _re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    # Strip emotion tags (e.g., [warm], [empathetic]) — these are metadata, not spoken text
    cleaned = _re.sub(r"\s*\[[a-z]+\]\s*", " ", cleaned)
    # Collapse all whitespace runs (including newlines) to a single space
    cleaned = _re.sub(r"\s+", " ", cleaned).strip()
    # Skip fragments that are too short unless they end a sentence
    if len(cleaned) < 3 and not cleaned.endswith((".", "!", "?")):
        return ""
    return cleaned


from server.brain.tts_conditioning import build_tts_directive, TurnContext, TTSDirective, Situation

logger = logging.getLogger(__name__)


# German + English backchannels — short affirmative noises that should NOT
# spawn an LLM turn.  Match is done on the full lower-cased utterance after
# stripping punctuation so "mhm." / "mhm!" / "mhm," all match.
_BACKCHANNEL_UTTERANCES: frozenset = frozenset({
    "mhm", "hm", "hmm", "mmh", "mhmm",
    "uh-huh", "uhu", "aha", "a ja",
    "ja ja", "ja, ja", "jaja", "ja klar",
    "okay", "ok",
    "ah", "ach so", "achso",
})


def _is_backchannel(text: str) -> bool:
    if not text:
        return False
    cleaned = (
        text.lower().strip().strip(".,!?;:").replace("  ", " ")
    )
    if not cleaned or len(cleaned) > 12:
        return False
    return cleaned in _BACKCHANNEL_UTTERANCES


# META_FEEDBACK_RE — P0.3: caller/tester meta-feedback channel.
# Anchored to start of utterance (or after punctuation), includes 'fehler' as alias.
# Tolerates typos in "Sailly": Sally, Selly, Sallé.
_META_FEEDBACK_RE = re.compile(
    r"^[\s,]*"                                                  # optional leading whitespace/comma
    r"(achtung|attention|warnung|fehler)\s*,?\s*"               # trigger word (now includes 'fehler')
    r"(?:sailly|sally|selly|sall[eé])?\s*"                     # optional name (not required for 'fehler')
    r"[.:,]?\s*"                                                # optional separator
    r"(.+)",                                                    # captured feedback text
    re.IGNORECASE | re.DOTALL,
)

# Keep legacy alias for compatibility with any external callers
_ACHTUNG_SAILLY = _META_FEEDBACK_RE


def _is_achtung_sailly_marker(text: str) -> tuple[bool, str]:
    """Check if text is a caller/tester meta-feedback marker.

    Anchored to start of utterance. Accepts 'Achtung Sailly:', 'Fehler:', etc.
    Returns (is_marker, captured_text).
    """
    if not text:
        return False, ""
    match = _META_FEEDBACK_RE.match(text.strip())
    if match:
        return True, match.group(2).strip() if match.lastindex >= 2 else ""
    return False, ""



class BrowserBrainService(FrameProcessor):

    def __init__(self, tenant_id: str = "doboo", caller_phone: str = "browser_demo", call_sid_prefix: str = "demo", **kwargs):
        super().__init__(**kwargs)
        self.tenant_id = tenant_id
        self.call_sid = f"{call_sid_prefix}-{uuid.uuid4().hex[:12]}"
        self.session = None
        self.turn_processor = None
        # Sprint 0 — propagated to ADKTurnProcessor for caller-ID prefill.
        # For the browser demo this stays as "browser_demo" (ignored there);
        # for Twilio calls the handler sets it to the E.164 caller ID.
        self.caller_phone = caller_phone
        self._start_ts = time.time()
        # Per-turn metrics accumulator: each entry populated after a successful
        # process_turn call. Flushed to google_turn_metrics on finalize.
        self._turn_metrics: list[dict] = []
        self._turn_counter: int = 0
        # Phase 3 shadow: IntentSessionManager runs in parallel with legacy pipeline
        # and logs to google_context_documents. Does not affect live behaviour.
        self._intent_session_mgr = None
        try:
            from server.brain.intent_session_manager import IntentSessionManager
            self._intent_session_mgr = IntentSessionManager()
        except Exception as _ism_err:
            pass  # shadow mode is optional
        # Set by _init_session when a prior Redis session is successfully
        # restored — suppresses the turn-0 greeting so the caller is not
        # re-greeted after a mid-call WebSocket reconnect.
        self._greeting_suppressed: bool = False
        # Rolling STT confidence window — written by STTConfidenceTracker,
        # read by the brain turn loop so it can inject a reprompt / escalate
        # after N consecutive low-confidence turns.
        self._stt_confidences: list[float] = []
        self._last_stt_confidence: float | None = None
        self._consecutive_low_conf: int = 0
        # Barge-in tracking: timestamp when user last started speaking.
        # Used to suppress TTS chunks that arrive AFTER a barge-in event
        # so T(n) audio doesn't bleed into T(n+1) playback.
        self._barge_in_ts: float = 0.0
        self._current_tts_turn: int = -1  # which turn's TTS is currently streaming
        # Injected by main.py after construction so brain can call
        # tts_service.update_for_turn() before each LLM turn.
        self.tts_service = None

        # ------------------------------------------------------------------
        # Sprint 0 observability trackers (populated by the turn loop +
        # ADKTurnProcessor so persist_turn_metrics can read them).
        # ------------------------------------------------------------------
        self._last_prompt_tokens_in: int | None = None
        self._last_prompt_tokens_out: int | None = None
        self._current_max_output_tokens: int | None = None
        self._current_temperature: float | None = None
        self._current_top_p: float | None = None
        self._raw_utterance_in_prompt: bool | None = None
        self._last_prompt_head: str | None = None
        self._barge_in_attempted_this_turn: bool | None = None
        self._barge_in_succeeded_this_turn: bool | None = None
        self._barge_in_latency_ms: int | None = None
        self._loop_detected_this_turn: bool | None = None
        self._loop_reason_this_turn: str | None = None
        self._stream_aborted_at_sentence: int | None = None
        self._cross_turn_similarity_this_turn: float | None = None

        # Phase 8.6 EOT + audio observability (populated by Flux event handlers
        # and the FillerScheduler / BackchannelInjector when wired).
        self._last_tts_ttfb_ms: int | None = None
        self._last_tts_total_ms: int | None = None  # Phase 3: end-to-end TTS latency
        self._tts_start_time: float | None = None  # Phase 3: track when TTS generation begins
        self._last_eot_event_type: str | None = None
        self._last_eot_confidence: float | None = None
        self._last_eot_latency_ms: int | None = None
        
        # Phase 7: Barge-in sensitivity tuning
        # Environment variable controls how aggressive the barge-in detection is
        # Lower values = more aggressive (suppress TTS sooner)
        self._barge_in_grace_ms = int(
            os.environ.get("BARGE_IN_GRACE_MS", "200")  # Default 200ms grace period after TTS starts
        )
        self._last_backchannel_fired: bool = False
        self._last_eot_followed_immediately: bool = False

        # Phase 8.2 — FillerScheduler instance (lazy).
        # Pushes pre-baked PCM into the TTS pipeline when LLM > 400ms.
        self._filler_scheduler = None
        # Phase 8.3 — BackchannelInjector instance (lazy).
        # Plays backchannel ("mhm", "ja") at -10dB on caller hesitation pauses.
        self._backchannel_injector = None
        # Phase 8.4 — SpeculativeExecutor instance (lazy).
        # Fires Required workers on Flux EagerEndOfTurn events; cancels on
        # TurnResumed; reuses on EndOfTurn confirmation.
        self._speculative_executor = None

    # ------------------------------------------------------------------
    # STT confidence hook — populated by STTConfidenceTracker in the pipeline
    # ------------------------------------------------------------------
    _STT_LOW_CONFIDENCE_THRESHOLD: float = 0.55
    _STT_REPROMPT_AFTER_N: int = 3

    def record_stt_confidence(self, confidence: float, text: str = "") -> None:
        """Track the latest ASR confidence and the count of consecutive low
        confidences. Called from the STTConfidenceTracker processor."""
        try:
            c = float(confidence)
        except (TypeError, ValueError):
            return
        self._last_stt_confidence = c
        self._stt_confidences.append(c)
        if len(self._stt_confidences) > 12:
            self._stt_confidences = self._stt_confidences[-12:]
        if c < self._STT_LOW_CONFIDENCE_THRESHOLD:
            self._consecutive_low_conf += 1
        else:
            self._consecutive_low_conf = 0
        # Propagate to turn_processor.asr_confidence_window for confidence_guard
        tp = getattr(self, "turn_processor", None)
        if tp is not None:
            window = getattr(tp, "asr_confidence_window", None)
            if window is not None:
                window.append(c)
                if len(window) > 12:
                    del window[:-12]
        if c < self._STT_LOW_CONFIDENCE_THRESHOLD:
            logger.info(
                f"[STTConfidence] low conf={c:.2f} "
                f"streak={self._consecutive_low_conf} text='{(text or '')[:40]}'"
            )

    def should_inject_low_confidence_prompt(self) -> bool:
        """True when we've had ``_STT_REPROMPT_AFTER_N`` low-confidence turns
        in a row — the brain pipeline should speak a canned clarification
        instead of proceeding on noise."""
        return self._consecutive_low_conf >= self._STT_REPROMPT_AFTER_N

    def reset_low_confidence_streak(self) -> None:
        self._consecutive_low_conf = 0

    async def _init_session(self):
        try:
            from server.session import get_redis, CallSession
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
            r = await get_redis(redis_url)
            self.session = CallSession(self.call_sid, r, tenant_id=self.tenant_id)
            await self.session.start(caller="browser_demo", from_number="browser")
            logger.info(f"[BRAIN] Redis session started: {self.call_sid}")
        except Exception as e:
            logger.warning(f"[BRAIN] Redis session failed: {e}")
            self.session = None

        # WebSocket reconnect path — try to restore prior conversation state
        # from Redis before constructing a fresh processor.  If a prior
        # `adk_brain` blob exists for this call_sid, the caller picks up where
        # they left off (no re-greeting, no re-asking for known slots).
        self.turn_processor = None
        if self.session:
            try:
                restored = await ADKTurnProcessor.restore_from_session(
                    session=self.session,
                    tenant_id=self.tenant_id,
                    call_sid=self.call_sid,
                    caller_phone=self.caller_phone or "browser_demo",
                    filler_cb=self._emit_filler_tts,
                )
                if restored is not None:
                    self.turn_processor = restored
                    self._greeting_suppressed = True  # do not re-greet on reconnect
                    logger.info(
                        f"[BRAIN] Reconnect restore succeeded: "
                        f"turn={restored.turn_idx} node={restored.node_mgr.current_node_name}"
                    )
            except Exception as _restore_err:
                logger.warning(f"[BRAIN] restore_from_session threw (non-fatal): {_restore_err}")

        if self.turn_processor is None:
            self.turn_processor = ADKTurnProcessor(
                tenant_id=self.tenant_id,
                call_sid=self.call_sid,
                session=self.session,
                caller_phone=self.caller_phone or "browser_demo",
                filler_cb=self._emit_filler_tts,
            )
        logger.info(f"[BRAIN] ADKTurnProcessor ready: {self.call_sid}")

    async def _emit_filler_pcm(self, pcm: bytes) -> None:
        """Phase 8.2 — push pre-baked filler PCM directly into the TTS output
        path so the caller hears 'Einen Moment bitte' within ~400ms when the
        LLM is slow. Bypasses TTS synthesis (the audio is pre-baked at startup).
        """
        if not pcm:
            return
        try:
            await self.push_frame(TTSAudioRawFrame(
                audio=pcm, sample_rate=24000, num_channels=1,
            ))
            logger.info(f"[FillerScheduler] PCM filler pushed ({len(pcm)} bytes)")
        except Exception as e:
            logger.warning(f"[FillerScheduler] PCM push failed: {e}")

    def _get_filler_scheduler(self):
        """Lazy-init the FillerScheduler with the PCM callback."""
        if self._filler_scheduler is None:
            try:
                from server.brain.filler_scheduler import FillerScheduler
                self._filler_scheduler = FillerScheduler(
                    audio_callback=self._emit_filler_pcm,
                )
            except Exception as _fs_err:
                logger.debug(f"[BRAIN] FillerScheduler init failed: {_fs_err}")
                self._filler_scheduler = None
        return self._filler_scheduler

    def _get_backchannel_injector(self):
        """Lazy-init the BackchannelInjector with the PCM callback."""
        if self._backchannel_injector is None:
            try:
                from server.brain.backchannel_injector import BackchannelInjector
                self._backchannel_injector = BackchannelInjector(
                    audio_callback=self._emit_filler_pcm,
                )
            except Exception as _bi_err:
                logger.debug(f"[BRAIN] BackchannelInjector init failed: {_bi_err}")
                self._backchannel_injector = None
        return self._backchannel_injector

    def on_user_started_speaking(self) -> None:
        """Called by the audio pipeline when the user begins a new utterance.
        Resets per-turn backchannel state."""
        bi = self._get_backchannel_injector()
        if bi is not None:
            bi.reset_for_turn()

    async def on_user_silence_start(self) -> None:
        """Called when VAD detects silence onset during user utterance.
        Triggers the hesitation timer for backchannel playback."""
        bi = self._get_backchannel_injector()
        if bi is not None:
            await bi.on_user_silence_start_safe()

    async def on_user_speech_resume(self) -> None:
        """Called when VAD detects speech resuming after a pause."""
        bi = self._get_backchannel_injector()
        if bi is not None:
            await bi.on_speech_resume()

    def _get_speculative_executor(self):
        """Lazy-init the SpeculativeExecutor with the worker_router."""
        if self._speculative_executor is None:
            try:
                from server.brain.speculative_executor import SpeculativeExecutor
                from server.brain import worker_router as _wr
                self._speculative_executor = SpeculativeExecutor(worker_router=_wr)
            except Exception as _se_err:
                logger.debug(f"[BRAIN] SpeculativeExecutor init failed: {_se_err}")
                self._speculative_executor = None
        return self._speculative_executor

    async def on_flux_eager_eot(
        self,
        confidence: float | None = None,
        partial_text: str = "",
    ) -> None:
        """Called by the Flux EagerEndOfTurn handler.
        Suppresses any pending backchannel, fires speculative workers,
        and records EOT observability."""
        self._last_eot_event_type = "EagerEndOfTurn"
        if confidence is not None:
            self._last_eot_confidence = confidence
        bi = self._get_backchannel_injector()
        if bi is not None:
            bi.on_eager_eot()
            self._last_backchannel_fired = bi.backchannel_fired
            self._last_eot_followed_immediately = bi.eot_followed_immediately
        # Phase 8.4 — fire speculative workers on the partial text.
        try:
            se = self._get_speculative_executor()
            if se is not None and partial_text:
                turn_idx = getattr(self.turn_processor, "turn_idx", 0) if self.turn_processor else 0
                await se.on_eager_eot(
                    partial_text=partial_text,
                    turn_idx=turn_idx,
                    call_sid=self.call_sid,
                    tenant_id=self.tenant_id or "doboo",
                )
        except Exception as _se_err:
            logger.debug(f"[BRAIN] speculative_executor.on_eager_eot failed: {_se_err}")

    async def on_flux_turn_resumed(self) -> None:
        """Called when Flux emits TurnResumed — cancel speculative work."""
        try:
            se = self._get_speculative_executor()
            if se is not None:
                await se.on_turn_resumed()
        except Exception as _se_err:
            logger.debug(f"[BRAIN] speculative_executor.on_turn_resumed failed: {_se_err}")

    async def _emit_filler_tts(self, text: str) -> None:
        """Push a short filler text to the TTS pipeline immediately — used by the
        brain to fill silence BEFORE a slow tool (verify_address, create_order, …)
        runs. Applies WAITING_FILLER style conditioning for a calm, brief tone."""
        if not text or not text.strip():
            return
        try:
            _filler_ctx = TurnContext(is_waiting_filler=True)
            _filler_directive = build_tts_directive(_filler_ctx)
            if self.tts_service is not None:
                self.tts_service.update_for_turn(
                    prompt=_filler_directive.style_instruction,
                    speaking_rate=_filler_directive.prosody_rate_pct / 100.0,
                )
            clean_filler = text.strip()
            await self.push_frame(LLMFullResponseStartFrame())
            await self.push_frame(LLMTextFrame(text=f"{_filler_directive.inline_tag} {clean_filler}"))
            await self.push_frame(LLMFullResponseEndFrame())
        except Exception as e:
            logger.debug(f"[BRAIN] filler tts push failed (non-fatal): {e}")

    async def _send_to_browser(self, msg_type: str, **kwargs):
        """Send a JSON message to the browser via OutputTransportMessageFrame."""
        payload = {"type": msg_type, **kwargs}
        await self.push_frame(OutputTransportMessageFrame(message=payload))

    async def _persist_context_doc(self, turn_number: int, shadow_data: dict) -> None:
        """Persist v4 pipeline IntentSession classification to google_context_documents."""
        try:
            from server.database import get_pool
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO google_context_documents
                        (call_sid, tenant_id, turn_number,
                         intent, turn_type, intent_locked, lock_confidence,
                         reroute_fired, worker_profile, shadow_mode)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, FALSE)
                    """,
                    self.call_sid,
                    self.tenant_id,
                    turn_number,
                    shadow_data.get("intent"),
                    shadow_data.get("turn_type"),
                    shadow_data.get("intent_locked", False),
                    shadow_data.get("lock_confidence", 0.0),
                    shadow_data.get("reroute_fired", False),
                    shadow_data.get("worker_profile"),
                )
        except Exception as _db_err:
            pass  # shadow persistence is non-fatal

    async def process_frame(self, frame, direction):
        if isinstance(frame, StartFrame):
            await super().process_frame(frame, direction)
            await self.push_frame(frame, direction)
            asyncio.create_task(self._send_greeting())
            return

        elif isinstance(frame, LLMContextFrame):
            # Mark: STT final (user text ready)
            # Update barge-in timestamp so any TTS chunks still streaming from
            # the previous turn can detect they're stale and suppress themselves.
            self._barge_in_ts = time.time()
            self._current_tts_turn = self._turn_counter + 1
            timer = LatencyTimer(self.call_sid, self._turn_counter + 1)
            timer.mark("stt_final")
            
            # Phase 4: Track barge-in attempt
            self._barge_in_attempted_this_turn = True  # User spoke while bot was speaking
            
            user_text = self._extract_latest_user_text(frame.context)
            if not user_text or not user_text.strip():
                return

            # Backchannel filter — drop short acknowledgements like "mhm",
            # "uh-huh", "ja ja" so they don't spawn a full LLM turn.  The
            # InterruptionFrame has already fired upstream (so TTS already
            # paused), but we do NOT want the bot to repeat or restart the
            # whole sentence just because the caller grunted agreement.
            if _is_backchannel(user_text):
                logger.info(f"[BRAIN] Backchannel suppressed: {user_text!r}")
                return

            # Achtung Sailly marker filter (Fix 1.1 / E2) — caller meta-feedback
            # Short-circuit and respond with a fixed apology turn.
            # Fix E2: Do NOT early-return if the message ALSO contains a farewell —
            # let the normal turn_processor run so the farewell cascade can fire.
            is_marker, captured_text = _is_achtung_sailly_marker(user_text)
            _FAREWELL_QUICK_RE = re.compile(
                r"\b(tsch[uü]s{1,2}|auf wiedersehen|auf wiederhören|bye|das war.?s|"
                r"das reicht|zu ende|gespräch beendet|gespräch ist (zu |vorbei|beendet)|"
                r"gespräch ist vorbei)\b",
                re.IGNORECASE,
            )
            has_farewell = bool(_FAREWELL_QUICK_RE.search(user_text))
            if is_marker and not has_farewell:
                logger.info(
                    f"[META_FEEDBACK] marker detected: {captured_text[:120]!r}",
                    extra={"call_sid": self.call_sid, "meta_feedback": captured_text},
                )
                # Send user transcript to browser so caller sees their message
                await self._send_to_browser("transcript", speaker="user", text=user_text)
                # Short, neutral ack — does not pretend to act on the feedback
                bot_text = "Verstanden, ich habe das notiert."
                await self._send_to_browser("transcript", speaker="bot", text=bot_text)
                # Log to session if available
                if self.session:
                    try:
                        await self.session.add_transcript("user", user_text)
                        await self.session.add_transcript("bot", bot_text)
                    except Exception:
                        pass
                return  # Early exit — do NOT call turn_processor
            elif is_marker and has_farewell:
                logger.info(
                    f"[BRAIN][CALLER_FEEDBACK] Achtung+farewell — skipping early return so farewell cascade runs",
                    extra={"call_sid": self.call_sid},
                )

            logger.info(f"[BRAIN] User: '{user_text[:80]}'")

            # Send user transcript to browser
            await self._send_to_browser("transcript", speaker="user", text=user_text)

            if self.session:
                try:
                    await self.session.add_transcript("user", user_text)
                except Exception:
                    pass

            # Low-confidence ASR short-circuit — if we've seen N consecutive
            # sub-threshold transcripts, speak a canned clarification instead
            # of handing this noise to the LLM.  After the 3rd such turn the
            # caller hears "Entschuldigung, ich habe Sie nicht verstanden —
            # könnten Sie das bitte wiederholen?" once; on the 5th we escalate
            # to technical_issues_callback to avoid the classic "bot didn't
            # hear anything for 5 turns" failure mode.
            if self.should_inject_low_confidence_prompt():
                bot_text = (
                    "Entschuldigung, ich habe Sie gerade schlecht verstanden — "
                    "könnten Sie das bitte wiederholen?"
                )
                last_conf = (
                    f"{self._last_stt_confidence:.2f}"
                    if self._last_stt_confidence is not None else "n/a"
                )
                logger.warning(
                    f"[BRAIN] Low-confidence reprompt fired "
                    f"(streak={self._consecutive_low_conf}, last={last_conf})"
                )
                self.reset_low_confidence_streak()
                await self._send_to_browser("transcript", speaker="bot", text=bot_text)
                try:
                    _lc_ctx = TurnContext(
                        consecutive_reprompts=self._consecutive_low_conf,
                        asr_mean_confidence=self._last_stt_confidence or 0.5,
                    )
                    _lc_directive = build_tts_directive(_lc_ctx)
                    if self.tts_service is not None:
                        self.tts_service.update_for_turn(
                            prompt=_lc_directive.style_instruction,
                            speaking_rate=_lc_directive.prosody_rate_pct / 100.0,
                        )
                    await self.push_frame(LLMFullResponseStartFrame())
                    await self.push_frame(LLMTextFrame(text=f"{_lc_directive.inline_tag} {bot_text}"))
                    await self.push_frame(LLMFullResponseEndFrame())
                except Exception as _e:
                    logger.debug(f"[BRAIN] low-conf push failed: {_e}")
                return

            try:
                if not self.turn_processor:
                    await self._init_session()

                # Mark: brain start (about to call process_turn)
                timer.mark("brain_start")

                # ── Adaptive TTS conditioning ─────────────────────────────────
                # Build a TTSDirective from conversation state BEFORE streaming
                # begins. This selects the correct situation style (15 options)
                # and caller mood mirror, composing a per-turn style prompt and
                # speaking rate sent to SaillyGeminiTTSService.
                _state = getattr(self.turn_processor, "state", None)
                _slots = getattr(_state, "order_slots_ref", None) if _state else None
                _turn_ctx = TurnContext(
                    node_name=getattr(
                        getattr(self.turn_processor, "node_mgr", None),
                        "current_node_name", ""
                    ) or "",
                    turn_idx=getattr(self.turn_processor, "turn_idx", 0),
                    is_first_turn=(getattr(self.turn_processor, "turn_idx", 0) == 0),
                    is_returning_caller=bool(
                        _state and getattr(_state, "caller_id_phone", None)
                        and _state.caller_id_phone not in ("", "browser", "browser_demo")
                    ),
                    escalation_requested=bool(
                        _state and getattr(_state, "escalation_requested", False)
                    ),
                    verify_address_failed=bool(
                        _state and getattr(_state, "verify_address_failed", False)
                    ),
                    order_just_committed=bool(
                        _state and getattr(_state, "order_created", False)
                    ),
                    reservation_just_committed=bool(
                        _state and getattr(_state, "reservation_created", False)
                    ),
                    is_goodbye=bool(
                        _state
                        and getattr(_state, "order_created", False)
                        and getattr(_state, "phone_confirmed", False)
                        and getattr(_state, "address_confirmed", False)
                    ),
                    is_waiting_filler=False,
                    contains_readback=False,  # updated on first chunk below
                    consecutive_reprompts=self._consecutive_low_conf,
                    asr_mean_confidence=(
                        self._last_stt_confidence
                        if self._last_stt_confidence is not None else 1.0
                    ),
                    last_caller_utterance=getattr(_state, "last_user_utterance", "") or "",
                    recent_caller_utterances=list(
                        getattr(_state, "recent_caller_utterances", []) or []
                    ),
                    utterance_duration_ms=0,  # Phase 3: add Deepgram duration tracking
                )
                _directive = build_tts_directive(_turn_ctx, phase2_mood=True)

                # Sprint 0.4: give turn_processor a reference so
                # _collect_subsystem_status() can report tts_conditioning="applied".
                if self.turn_processor is not None:
                    self.turn_processor._last_tts_directive = _directive

                # Apply per-turn style prompt and speaking rate to TTS service
                if self.tts_service is not None:
                    self.tts_service.update_for_turn(
                        prompt=_directive.style_instruction,
                        speaking_rate=_directive.prosody_rate_pct / 100.0,
                    )

                # ── Streaming TTS callback ────────────────────────────────────
                # Sentence chunks arrive here as Gemini streams them. Each chunk
                # is sanitized and pushed as an LLMTextFrame immediately, so
                # the caller hears the first word ~300 ms after the first token
                # rather than waiting for the complete response.
                _streamed_chunks: list = []  # track what was already sent to TTS
                _full_response_buf: list = []

                _tts_turn_start: float = 0.0  # set on first TTS chunk, not at turn start
                _tts_streaming_start: float = time.time()  # Capture TTS process start BEFORE any LLM streaming
                _tts_last_chunk_time: float = 0.0  # Phase 3: track last TTS chunk for total latency

                async def _tts_push(chunk: str) -> None:
                    nonlocal _streamed_chunks, _full_response_buf, _tts_turn_start, _tts_last_chunk_time
                    # Capture when TTS actually starts streaming (not when turn processing started).
                    # This is the correct anchor for the barge-in comparison: we only want to
                    # suppress chunks if the user spoke AFTER audio started playing, not during
                    # the LLM generation window.
                    if not _streamed_chunks:
                        _tts_turn_start = time.time()
                        self._tts_start_time = _tts_turn_start  # Phase 3
                        # Cancel pending PCM filler — the LLM has produced its
                        # first chunk so the filler is no longer needed.
                        try:
                            _fs = self._get_filler_scheduler()
                            if _fs is not None:
                                _fs.cancel()
                        except Exception:
                            pass
                    # Phase 3: track timestamp of last chunk for end-to-end TTS latency
                    _tts_last_chunk_time = time.time()
                    # Barge-in suppression: if user started speaking AFTER this
                    # turn's TTS began streaming (after grace period), the caller has interrupted —
                    # suppress audio but STILL accumulate _full_response_buf so
                    # bot_text in the DB reflects the complete LLM response, not
                    # the truncated pre-barge-in portion. (PR-16c)
                    # Phase 7: Apply grace period — don't suppress too quickly
                    _grace_delta = (self._barge_in_ts - _tts_turn_start) * 1000  # ms
                    if _grace_delta > self._barge_in_grace_ms:
                        # Phase 4: Track that barge-in succeeded in suppressing audio
                        self._barge_in_succeeded_this_turn = True
                        self._barge_in_latency_ms = int(_grace_delta)
                        logger.debug(
                            f"[BRAIN] TTS chunk suppressed (barge-in): "
                            f"barge_in={self._barge_in_ts:.3f} tts_start={_tts_turn_start:.3f} "
                            f"latency={self._barge_in_latency_ms}ms (grace={self._barge_in_grace_ms}ms)"
                        )
                        clean = _sanitize_for_tts(chunk)
                        if clean:
                            _full_response_buf.append(clean)
                        return
                    clean = _sanitize_for_tts(chunk)
                    if not clean:
                        return
                    # Strip any [TOOL:...] tags that leaked into streaming chunks
                    clean, _had_leak = _strip_tool_call_leakage(clean)
                    if not clean:
                        return
                    _full_response_buf.append(clean)
                    if not _streamed_chunks:
                        # Open the TTS frame stream on first chunk and prepend
                        # the situation-aware inline tag from the directive.
                        # The tag is metadata for Gemini TTS and will be stripped
                        # by SaillyGeminiTTSService before synthesis, but it
                        # influences the emotional tone via the style prompt.
                        await self.push_frame(LLMFullResponseStartFrame())
                        timer.mark("tts_first_chunk")
                        # Update readback detection on first chunk now that we
                        # have actual text — refines situation if needed
                        _tag = _directive.inline_tag
                        if _slots is not None and _slots.has_readback_content(clean):
                            _tag = "[attentive]"
                        clean = f"{_tag} {clean}"
                    await self.push_frame(LLMTextFrame(text=clean))
                    _streamed_chunks.append(clean)

                _turn_started_ms = time.time() * 1000.0
                # Phase 8.2 — arm the PCM FillerScheduler for this turn.
                # Will fire 'Einen Moment bitte' after 400ms IF the LLM hasn't
                # produced a chunk yet AND the active profile is expected to
                # take longer (commit-tool turns, multi-intent turns).
                try:
                    _fs = self._get_filler_scheduler()
                    if _fs is not None:
                        await _fs.arm(requires_slow_tool=True)
                except Exception:
                    pass

                result = await self.turn_processor.process_turn(
                    user_text, tts_callback=_tts_push
                )
                _turn_elapsed_ms = int(time.time() * 1000.0 - _turn_started_ms)
                # PR-16c: prefer _full_response_buf (all chunks including post-barge-in)
                # over result.clean_text when it contains more data, so bot_text in
                # the DB reflects the complete LLM output rather than a barge-in cutoff.
                _full_buf_text = " ".join(_full_response_buf).strip()
                if _full_buf_text and len(_full_buf_text) > len(result.clean_text or ""):
                    result.clean_text = _full_buf_text
                logger.info(f"[BRAIN] Bot: '{result.clean_text[:80]}' tools={result.tools_called}")

                # Close the TTS stream if chunks were streamed, otherwise push
                # the full text now (tool-only turns or streaming disabled).
                if _streamed_chunks:
                    timer.mark("tts_text_pushed")
                    await self.push_frame(LLMFullResponseEndFrame())
                    # Phase 3: Measure TTS service readiness latency
                    # (from when we start the TTS process to when we've finished pushing all text).
                    # Note: This does NOT measure actual audio synthesis time (which happens
                    # asynchronously in Pipecat); it measures text-to-Pipecat-readiness time.
                    if _tts_streaming_start:
                        self._last_tts_total_ms = int((time.time() - _tts_streaming_start) * 1000)
                        logger.info(f"[Phase3] TTS service readiness latency: {self._last_tts_total_ms}ms")
                else:
                    tts_text = _sanitize_for_tts(result.clean_text)
                    if tts_text:
                        timer.mark("tts_text_pushed")
                        await self.push_frame(LLMFullResponseStartFrame())
                        await self.push_frame(LLMTextFrame(text=f"{_directive.inline_tag} {tts_text}"))
                        await self.push_frame(LLMFullResponseEndFrame())
                        # Phase 3: Measure TTS service readiness latency (non-streaming path)
                        if _tts_streaming_start:
                            self._last_tts_total_ms = int((time.time() - _tts_streaming_start) * 1000)
                            logger.info(f"[Phase3] TTS service readiness latency (non-streaming): {self._last_tts_total_ms}ms")
                    else:
                        logger.warning(
                            f"[BRAIN] Skipping TTS for empty/trivial fragment: {result.clean_text!r}"
                        )

                # Accumulate per-turn metrics for google_turn_metrics persistence
                try:
                    self._turn_counter += 1
                    # P0.1: read node_name from TurnResult (set by node_mgr.current_node_name)
                    node_name = getattr(result, "node_name", None)
                    if not node_name:
                        # Fallback to live node_mgr if TurnResult didn't carry it
                        try:
                            _tp = getattr(self, "turn_processor", None)
                            node_name = getattr(getattr(_tp, "node_mgr", None), "current_node_name", None)
                        except Exception:
                            pass

                    # Compute per-stage latencies from LatencyTimer marks.
                    # stt_latency_ms  = stt_final → brain_start
                    # llm_latency_ms  = brain_start → tts_first_chunk (or tts_text_pushed)
                    # total_latency_ms = stt_final → tts_first_chunk / tts_text_pushed
                    _m = timer.marks
                    _t_stt   = _m.get("stt_final")
                    _t_brain = _m.get("brain_start")
                    _t_tts   = _m.get("tts_first_chunk") or _m.get("tts_text_pushed")
                    _stt_ms  = int((_t_brain - _t_stt)  * 1000) if _t_brain and _t_stt  else None
                    _llm_ms  = int((_t_tts   - _t_brain) * 1000) if _t_tts   and _t_brain else _turn_elapsed_ms
                    _tot_ms  = int((_t_tts   - _t_stt)  * 1000) if _t_tts   and _t_stt  else _turn_elapsed_ms

                    # Collect validation breakdown + sprint 0 observability
                    # from ValidationRegistry if active
                    _validation_breakdown = {}
                    _validations_fired = None
                    _validations_completed = None
                    _validations_pending = None
                    _validation_cancellations = None
                    _validators_run = []  # Phase 5.5 per-validator tiles
                    _slot_state_json = None
                    _slot_state_diff = None
                    _slots_filled_count = None
                    _slots_confirmed_count = None
                    _slots_missing_required = None
                    _intent_flags_active = None
                    _prompt_had_multi_intent = None
                    _subsystems_fired = None
                    try:
                        _tp = getattr(self, "turn_processor", None)
                        if _tp is not None:
                            _vreg = getattr(_tp, "validation_registry", None)
                            if _vreg is not None:
                                _validation_breakdown = _vreg.metrics_dict()
                            _validations_fired = getattr(_tp, "_validations_fired_this_turn", None)
                            _validations_completed = getattr(_tp, "_validations_completed_this_turn", None)
                            _validations_pending = getattr(_tp, "_validations_pending_end_of_turn", None)
                            _validation_cancellations = getattr(_tp, "_validation_cancellations_this_turn", None)
                            # Phase 5.5 — per-validator trace tiles from new ValidationRegistry
                            _p55_layer_trace = getattr(_tp.state, "__p55_layer_trace__", None)
                            _validators_run = _p55_layer_trace.validators_run if _p55_layer_trace else []
                            # Slot snapshot + diff
                            _slots_ref = None
                            try:
                                _slots_ref = getattr(_tp.state, "order_slots_ref", None)
                            except Exception:
                                pass
                            if _slots_ref is not None:
                                try:
                                    _slot_state_json = _slots_ref.to_dict() if hasattr(_slots_ref, "to_dict") else None
                                except Exception:
                                    _slot_state_json = None
                                try:
                                    _slots_missing_required = _slots_ref.missing_required() if hasattr(_slots_ref, "missing_required") else None
                                except Exception:
                                    _slots_missing_required = None
                                # Counts (best-effort)
                                try:
                                    from server.brain.order_slots import SlotStatus as _SlotStatus
                                    _slots_filled_count = 0
                                    _slots_confirmed_count = 0
                                    for _f in _slots_ref.__dict__.values():
                                        if hasattr(_f, "status"):
                                            if hasattr(_f, "is_usable") and _f.is_usable():
                                                _slots_filled_count += 1
                                            if getattr(_f, "status", None) == _SlotStatus.CONFIRMED:
                                                _slots_confirmed_count += 1
                                except Exception:
                                    pass
                            # Intent flags (check common state flags).
                            # Skip methods like should_escalate (bool vs callable).
                            try:
                                _intent_flags_active = []
                                for f in (
                                    "order_intent", "reservation_intent",
                                    "faq_intent", "escalation_requested",
                                ):
                                    val = getattr(_tp.state, f, False)
                                    if callable(val):
                                        continue
                                    if val:
                                        _intent_flags_active.append(f)
                                # should_escalate is a method on ConversationState
                                try:
                                    if callable(getattr(_tp.state, "should_escalate", None)) \
                                            and _tp.state.should_escalate():
                                        _intent_flags_active.append("should_escalate")
                                except Exception:
                                    pass
                                _prompt_had_multi_intent = len(_intent_flags_active) > 1
                            except Exception:
                                pass
                            # Subsystems fired (Sprint 0.4)
                            try:
                                _subsystems_fired = _tp._collect_subsystem_status() if hasattr(_tp, "_collect_subsystem_status") else None
                            except Exception:
                                _subsystems_fired = None
                    except Exception:
                        pass

                    try:
                        from server.brain.layer1.persist import build_turn_metrics_extra as _build_turn_metrics_extra
                    except Exception:
                        _build_turn_metrics_extra = lambda _s: {}  # noqa: E731

                    self._turn_metrics.append({
                        "turn_number": self._turn_counter,
                        "user_text": user_text,
                        "bot_text": result.clean_text,
                        "tools_called": list(result.tools_called or []),
                        "stt_latency_ms": _stt_ms,
                        "llm_latency_ms": _llm_ms,
                        "total_latency_ms": _tot_ms,
                        "node_name": node_name,
                        "stage3_text": result.clean_text,
                        "stt_confidence": self._last_stt_confidence,
                        "validation_breakdown": _validation_breakdown,
                        "tts_situation": _directive.situation.value,
                        "tts_mood": _directive.mood.value,
                        "tts_inline_tag": _directive.inline_tag,
                        # Sprint 0 / Sprint 3.3: token counts from turn_processor
                        # (set by adk_turn_processor after build_context() returns the tuple).
                        "prompt_tokens_in": getattr(_tp, "_last_prompt_tokens_in", None) if _tp else None,
                        "prompt_tokens_out": getattr(self, "_last_prompt_tokens_out", None),
                        "max_output_tokens_config": getattr(self, "_current_max_output_tokens", None),
                        "temperature_config": getattr(self, "_current_temperature", None),
                        "top_p_config": getattr(self, "_current_top_p", None),
                        "slot_state_json": _slot_state_json,
                        "slot_state_diff": None,  # computed in adk_turn_processor if needed
                        "slots_filled_count": _slots_filled_count,
                        "slots_confirmed_count": _slots_confirmed_count,
                        "slots_missing_required": _slots_missing_required,
                        "validations_fired_this_turn": _validations_fired,
                        "validations_completed_this_turn": _validations_completed,
                        "validations_pending_end_of_turn": _validations_pending,
                        "validation_cancellations": _validation_cancellations,
                        "validators_run": _validators_run,
                        "raw_utterance_in_prompt": getattr(_tp, "_raw_utterance_in_prompt", None) if _tp else None,
                        "prompt_snapshot_head": getattr(_tp, "_last_prompt_head", None) if _tp else None,
                        "intent_flags_active": _intent_flags_active,
                        "node_active": node_name,
                        "prompt_had_multiple_intents": _prompt_had_multi_intent,
                        "mood_confidence": getattr(_directive, "mood_confidence", None),
                        "mood_signals_matched": getattr(_directive, "mood_signals", None),
                        "barge_in_attempted": getattr(self, "_barge_in_attempted_this_turn", None),
                        "barge_in_succeeded": getattr(self, "_barge_in_succeeded_this_turn", None),
                        "barge_in_latency_ms": getattr(self, "_barge_in_latency_ms", None),
                        "loop_detected_in_stream": getattr(self, "_loop_detected_this_turn", None),
                        "loop_reason": getattr(self, "_loop_reason_this_turn", None),
                        "stream_aborted_at_sentence": getattr(self, "_stream_aborted_at_sentence", None),
                        "cross_turn_similarity_max": getattr(self, "_cross_turn_similarity_this_turn", None),
                        "subsystems_fired": _subsystems_fired,
                        "tts_rate_pct": getattr(_directive, "prosody_rate_pct", None),
                        "tts_latency_ms": self._last_tts_total_ms,  # Phase 3: end-to-end TTS latency
                        # Phase 9 A1 — per-stage latency, token counts, and cost_eur
                        # from TurnTimings. build_turn_metrics_extra calls to_metrics_dict()
                        # internally and appends cost_eur computed from token counts.
                        **(_build_turn_metrics_extra(_tp.state)
                           if _tp and getattr(getattr(_tp, "state", None), "_turn_timings", None)
                           else {}),
                        # Phase 9 B1 — ERR_* codes collected during tool execution
                        "error_codes": (
                            getattr(_tp, "_current_turn_error_codes", None) or []
                        ) if _tp else [],
                        # Phase 8.6 — v4 per-stage latency and EOT observability.
                        # These are sourced from per-call trackers maintained in
                        # the ADKTurnProcessor / brain_service. Missing values
                        # become NULL in the DB.
                        "intent_classify_ms": getattr(_tp, "_last_intent_classify_ms", None) if _tp else None,
                        "worker_p50_ms": getattr(_tp, "_last_worker_p50_ms", None) if _tp else None,
                        "worker_p95_ms": getattr(_tp, "_last_worker_p95_ms", None) if _tp else None,
                        "context_build_ms": getattr(_tp, "_last_context_build_ms", None) if _tp else None,
                        "generator_ttft_ms": getattr(_tp, "_last_generator_ttft_ms", None) if _tp else None,
                        "tts_ttfb_ms": getattr(self, "_last_tts_ttfb_ms", None),
                        "eot_event_type": getattr(self, "_last_eot_event_type", None),
                        "eot_confidence": getattr(self, "_last_eot_confidence", None),
                        "eot_latency_ms": getattr(self, "_last_eot_latency_ms", None),
                        "backchannel_fired": getattr(self, "_last_backchannel_fired", False) or False,
                        "eot_followed_immediately": getattr(self, "_last_eot_followed_immediately", False) or False,
                        # Phase 0: Slot and validation diagnostics
                        "slot_extraction_latency_ms": getattr(_tp, "_last_slot_extraction_latency_ms", None) if _tp else None,
                        "slot_retention_status": getattr(_tp, "_last_slot_retention_status", None) if _tp else None,
                        "validation_passes": getattr(_tp, "_last_validation_passes", None) if _tp else None,
                    })
                except Exception as me:
                    logger.debug(f"[BRAIN] turn_metrics accumulate failed: {me}")

                # Phase 3 shadow: run IntentSessionManager and persist to context_docs
                try:
                    if self._intent_session_mgr is not None:
                        _turn_idx = getattr(self.turn_processor, "turn_idx", self._turn_counter) - 1
                        _intent_session = self._intent_session_mgr.process_turn(
                            user_text, turn_idx=_turn_idx
                        )
                        # Haiku fallback: when regex returns UNKNOWN, ask the LLM to
                        # classify the intent.  This implements the two-layer architecture
                        # documented in intent_classifier.py but never previously wired.
                        if _intent_session.primary_intent.value == "unknown":
                            try:
                                from server.brain.intent_classifier import classify_with_haiku as _classify_haiku
                                _haiku_result = await _classify_haiku(user_text, turn_idx=_turn_idx)
                                if _haiku_result.intent.value != "unknown":
                                    _intent_session.update(_haiku_result, _turn_idx)
                                    logger.info(
                                        f"[BRAIN] Haiku override: {_haiku_result.intent.value} "
                                        f"(conf={_haiku_result.confidence})"
                                    )
                            except Exception as _haiku_err:
                                logger.debug(f"[BRAIN] Haiku intent fallback failed: {_haiku_err}")
                        _shadow_dict = self._intent_session_mgr.to_shadow_dict(_turn_idx)
                        # Backfill intent classification into the most-recently-appended
                        # turn_metrics entry so the DB row carries intent/turn_type/worker_profile.
                        if self._turn_metrics:
                            self._turn_metrics[-1]["intent"] = (
                                _intent_session.primary_intent.value
                                if _intent_session.primary_intent else None
                            )
                            self._turn_metrics[-1]["turn_type"] = (
                                _intent_session.current_turn_type.value
                                if _intent_session.current_turn_type else None
                            )
                            self._turn_metrics[-1]["worker_profile"] = _intent_session.worker_profile
                        # Best-effort async persist — non-blocking
                        import asyncio as _asyncio
                        _asyncio.create_task(self._persist_context_doc(
                            turn_number=self._turn_counter,
                            shadow_data=_shadow_dict,
                        ))
                except Exception as _shadow_err:
                    logger.debug(f"[BRAIN] shadow intent session failed: {_shadow_err}")

                if self.session:
                    try:
                        await self.session.add_transcript("assistant", result.clean_text)
                    except Exception:
                        pass

                # Send bot transcript to browser
                await self._send_to_browser("transcript", speaker="bot", text=result.clean_text)

                if result.should_end:
                    # Phase 6: Farewell hardening — ensure TTS completes before call ends.
                    # Use streamed chars if available, else result.clean_text.
                    _spoken = "".join(_streamed_chunks) if _streamed_chunks else _sanitize_for_tts(result.clean_text) or ""
                    if _spoken:
                        # Minimum 5s (user-requested floor) + generous +3s buffer to cover:
                        # - TTS synthesis delay (~0.5–1s)
                        # - Network / playback jitter (~0.5–1s)
                        # - Slower speech rate for numbers/names in confirmations
                        _farewell_secs = max(5.0, len(_spoken) / _CHARS_PER_SEC_DE + 3.0)
                        logger.info(
                            f"[Phase6] Waiting {_farewell_secs:.1f}s for farewell TTS before EndFrame "
                            f"({len(_spoken)} chars at ~{_CHARS_PER_SEC_DE} chars/sec)"
                        )
                        await asyncio.sleep(_farewell_secs)
                    else:
                        logger.info("[Phase6] No farewell text; waiting 5s minimum before end")
                        await asyncio.sleep(5.0)
                    logger.info(f"[BRAIN] Ending: {result.end_reason}")
                    await self._finalize_session(result.end_reason)
                    await self.push_frame(EndFrame())
            except Exception as e:
                logger.error(f"[BRAIN] Turn error: {e}", exc_info=True)
                # Close any open TTS stream before emitting error audio
                if _streamed_chunks:
                    try:
                        await self.push_frame(LLMFullResponseEndFrame())
                    except Exception:
                        pass
                err_text = "Entschuldigung, ein technisches Problem. Bitte versuchen Sie es erneut."
                await self._send_to_browser("transcript", speaker="bot", text=err_text)
                tts_err = _sanitize_for_tts(err_text)
                if tts_err:
                    await self.push_frame(LLMFullResponseStartFrame())
                    await self.push_frame(LLMTextFrame(text=tts_err))
                    await self.push_frame(LLMFullResponseEndFrame())

        elif isinstance(frame, EndFrame):
            await self._finalize_session("client_hangup")
            await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _send_greeting(self):
        try:
            await asyncio.sleep(0.8)
            if not self.turn_processor:
                await self._init_session()

            # If _init_session restored a prior session from Redis the caller is
            # mid-call; do not re-greet. The pipeline will pick up at the next
            # user utterance using the restored state / slots / node pointer.
            if self._greeting_suppressed:
                logger.info(
                    f"[BRAIN-GREET] Suppressed — restored session (turn_idx="
                    f"{getattr(self.turn_processor, 'turn_idx', '?')})"
                )
                return

            logger.info("[BRAIN-GREET] Triggering turn-0 greeting via v4 pipeline")
            
            # Use fixed greeting from tenant config (doboo.yaml)
            greeting_text = None
            try:
                from server.core.tenant_config import get_tenant_registry
                registry = get_tenant_registry()
                tenant = registry.load_tenant(self.tenant_id or "doboo")
                if tenant and hasattr(tenant, 'greeting_line') and tenant.greeting_line:
                    greeting_text = tenant.greeting_line
                    logger.info(f"[BRAIN-GREET] Using tenant-configured greeting: '{greeting_text}'")
            except Exception as _e:
                logger.warning(f"[BRAIN-GREET] Failed to load tenant config: {_e}")
            
            # Fallback if no tenant config found
            if not greeting_text:
                greeting_text = (
                    "Hallo, hier ist Sailly, die KI-Assistentin vom DOBOO Korean Soulfood — "
                    "schön, dass Sie anrufen! Was kann ich für Sie tun?"
                )

            # EU AI Act Art. 50: the first bot line MUST contain "KI".
            if " KI" not in f" {greeting_text}":
                logger.warning(
                    "[BRAIN-GREET] v4 greeting missing 'KI' token — prepending disclosure"
                )
                greeting_text = (
                    "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO. " + greeting_text
                )

            if greeting_text:
                logger.info(f"[BRAIN-GREET] '{greeting_text[:120]}'")

                # Always try to add greeting to session transcript
                if self.session:
                    try:
                        await self.session.add_transcript("assistant", greeting_text)
                        logger.info("[BRAIN-GREET] Added greeting to session transcript")
                    except Exception as e:
                        logger.warning(f"[BRAIN-GREET] Failed to add greeting to session: {e}")
                else:
                    logger.warning("[BRAIN-GREET] Session not yet initialized")

                # Send bot transcript to browser
                await self._send_to_browser("transcript", speaker="bot", text=greeting_text)

                # Apply greeting-specific TTS conditioning before synthesis.
                # is_returning_caller is set if caller_id_phone is known from
                # a prior Redis session or Twilio caller-ID prefill.
                _greet_state = (
                    getattr(self.turn_processor, "state", None)
                    if self.turn_processor else None
                )
                _greet_ctx = TurnContext(
                    is_first_turn=True,
                    is_returning_caller=bool(
                        _greet_state
                        and getattr(_greet_state, "caller_id_phone", None)
                        and _greet_state.caller_id_phone not in ("", "browser", "browser_demo")
                    ),
                )
                _greet_directive = build_tts_directive(_greet_ctx)
                if self.tts_service is not None:
                    self.tts_service.update_for_turn(
                        prompt=_greet_directive.style_instruction,
                        speaking_rate=_greet_directive.prosody_rate_pct / 100.0,
                    )

                tts_greet = _sanitize_for_tts(greeting_text)
                if tts_greet:
                    await self.push_frame(LLMFullResponseStartFrame())
                    await self.push_frame(LLMTextFrame(text=f"{_greet_directive.inline_tag} {tts_greet}"))
                    await self.push_frame(LLMFullResponseEndFrame())
            else:
                logger.warning("[BRAIN-GREET] Empty greeting")
        except asyncio.TimeoutError:
            logger.warning("[BRAIN-GREET] Timed out (15s)")
        except Exception as e:
            logger.error(f"[BRAIN-GREET] Failed: {e}", exc_info=True)

    async def _finalize_session(self, reason: str = "unknown"):
        if not self.session:
            return
        session_ref = self.session
        self.session = None  # Prevent double-finalize
        try:
            session_data = await session_ref.end()
            # Merge tenant info into session data for consistent reporting
            if isinstance(session_data, dict):
                session_data["tenant_id"] = self.tenant_id
                session_data.setdefault("tenant", self.tenant_id)
            logger.info(f"[BRAIN] Session ended: {self.call_sid} reason={reason}")

            # ── Record monitoring metrics to Redis ─────────────────────────────
            try:
                from server.monitoring import record_call_metric, infer_outcome_from_session
                outcome = infer_outcome_from_session(session_data)
                outcome["end_reason"] = reason
                outcome["source"] = "browser_demo"
                outcome["tenant_id"] = self.tenant_id
                await record_call_metric(self.call_sid, "outcome", outcome)
                logger.info(f"[BRAIN] Monitoring recorded: intent={outcome.get('intent')}")
            except Exception as me:
                logger.warning(f"[BRAIN] Monitoring failed: {me}")

            # ── Write to PostgreSQL so Call History page shows demo calls ──────
            try:
                await self._write_call_to_postgres(session_data, reason)
            except Exception as pe:
                logger.warning(f"[BRAIN] PostgreSQL write failed (non-fatal): {pe}")

            # ── Capture failed calls as new validation scenarios ──────────────
            try:
                await self._capture_failed_call(session_data, reason)
            except Exception as ce:
                logger.warning(f"[BRAIN] Failure capture failed (non-fatal): {ce}")

            # ── CRM upsert for repeat-caller recognition (Sprint 2) ───────────
            # Skipped automatically for synthetic browser-demo sessions because
            # ``_phone_ok`` rejects the "browser_demo" placeholder.
            try:
                from server.brain.call_summary import persist_call_summary
                state = getattr(self.turn_processor, "_state", None) if self.turn_processor else None
                phone = getattr(self, "caller_phone", None)
                if state is not None and phone:
                    await persist_call_summary(phone, state, self.tenant_id)
            except Exception as crm_e:
                logger.debug(f"[BRAIN] CRM summary skipped: {crm_e!r}")

        except Exception as e:
            logger.warning(f"[BRAIN] Session finalize failed: {e}")

    async def _write_call_to_postgres(self, session_data: dict, reason: str):
        """Write demo call record to PostgreSQL google_calls table."""
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.info("[BRAIN] No DATABASE_URL — skipping PostgreSQL write")
            return

        import asyncpg
        from datetime import datetime, timezone

        def _parse_dt(val) -> datetime:
            """Parse an ISO string or return now if blank/invalid."""
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromisoformat(str(val))
            except Exception:
                return datetime.now(timezone.utc)

        now_dt = datetime.now(timezone.utc)
        started_at = _parse_dt(session_data.get("started_at") or self._start_ts)
        ended_at = _parse_dt(session_data.get("ended_at") or now_dt)
        duration_secs = int(session_data.get("duration_secs") or max(0, time.time() - self._start_ts))
        transcripts = session_data.get("transcripts", [])
        
        # Reconstruct full conversation from adk_brain memory if needed
        # (bot responses are stored in state.adk_brain.memory.recent_turns)
        recent_turns = (
            session_data.get("state", {})
            .get("adk_brain", {})
            .get("memory", {})
            .get("recent_turns", [])
        )
        if recent_turns:
            # Build expected transcript from recent_turns: customer, bot, customer, bot, ...
            expected_from_brain = []
            for turn in recent_turns:
                if turn.get("customer") and turn["customer"] != "<call_start>":
                    expected_from_brain.append({"role": "user", "text": turn["customer"]})
                if turn.get("bot"):
                    expected_from_brain.append({"role": "assistant", "text": turn["bot"]})
            
            # Preserve Sailly's initial greeting if it exists in transcripts
            greeting = None
            if transcripts and transcripts[0].get("role") == "assistant":
                greeting_text = transcripts[0].get("text") or ""
                # Greeting typically contains "Willkommen" or "Sailly"
                if "Willkommen" in greeting_text or "Sailly" in greeting_text:
                    greeting = transcripts[0]
            
            # Reconstruct: greeting (if exists) + alternating turns from recent_turns
            if expected_from_brain or greeting:
                merged = []
                if greeting:
                    merged.append(greeting)
                merged.extend(expected_from_brain)
                
                if len(merged) > len(transcripts):
                    logger.info(f"[BRAIN] Reconstructing transcripts: {len(transcripts)} → {len(merged)} (kept greeting={greeting is not None})")
                    transcripts = merged
        
        # Sync ADK brain tool history into session_data["tool_calls"] if pipeline
        # did not already populate it.  ADK brain tracks executed tools internally
        # in state.adk_brain.all_tools (List[str]); the standard Pipecat tool
        # registration path is bypassed when USE_ADK_BRAIN is active, so
        # session_data["tool_calls"] stays empty without this sync.
        if not session_data.get("tool_calls"):
            _all_tools_adk = (
                session_data.get("state", {})
                .get("adk_brain", {})
                .get("all_tools", [])
            )
            if _all_tools_adk:
                session_data["tool_calls"] = [{"tool": t, "name": t} for t in _all_tools_adk]
                logger.info(
                    f"[BRAIN] synced {len(_all_tools_adk)} ADK tool(s) into session_data['tool_calls']"
                )

        tool_calls = session_data.get("tool_calls", [])
        tool_names = [tc.get("tool", "") for tc in tool_calls]
        was_escalated = any(t in ("transfer_to_human", "transfer_to_tier2") for t in tool_names)

        # Compute real quality score from the live auditor (Fix 6).
        # score_live_call returns composite_score on a 0-100 scale; the DB
        # stores it on a 0-10 scale (matching the Node.js quality.get("score",0)/10 convention).
        # Fix 3 (role filter in call_auditor_live) must already be applied so
        # the auditor correctly reads bot turns written as role="bot" by ADK brain.
        try:
            from server.call_auditor_live import score_live_call as _score_live_call
            _audit_result = _score_live_call(session_data, industry=self.tenant_id or "restaurant")
            _quality_score = round(_audit_result.get("composite_score", 50.0) / 10.0, 1)
            logger.info(f"[BRAIN] quality_score={_quality_score} (composite={_audit_result.get('composite_score')})")
        except Exception as _qs_err:
            logger.warning(f"[BRAIN] quality score computation failed, using 5.0: {_qs_err}")
            _quality_score = 5.0

        conn = await asyncpg.connect(db_url)
        try:
            # Insert into google_calls
            row = await conn.fetchrow(
                """
                INSERT INTO google_calls
                    (call_sid, caller_number, tenant_id, started_at, ended_at, duration_seconds,
                     quality_score, outcome, language, was_escalated, total_turns,
                     total_cost_tokens, total_cost_telephony, session_data)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                ON CONFLICT (call_sid) DO NOTHING
                RETURNING id
                """,
                self.call_sid,
                "browser_demo",
                self.tenant_id or "doboo",
                started_at,
                ended_at,
                duration_secs,
                _quality_score,
                reason,
                "de",
                was_escalated,
                len(transcripts),
                0.0,
                0.0,
                json.dumps(session_data),
            )
            if row:
                logger.info(f"[BRAIN] PostgreSQL: call written id={row['id']}")
            call_uuid = row["id"] if row else None

            # Insert transcripts
            if transcripts:
                await conn.executemany(
                    """
                    INSERT INTO google_transcripts (call_sid, role, content, turn_number, timestamp)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    [
                        (
                            self.call_sid,
                            t.get("role") or ("assistant" if t.get("speaker") == "bot" else "user"),
                            t.get("text") or t.get("content") or "",
                            i,
                            _parse_dt(t.get("timestamp") or t.get("ts")) if (t.get("timestamp") or t.get("ts")) else now_dt,
                        )
                        for i, t in enumerate(transcripts)
                        if isinstance(t, dict)
                    ],
                )
                logger.info(f"[BRAIN] PostgreSQL: {len(transcripts)} transcript rows written")

            # Insert tool calls
            if tool_calls:
                await conn.executemany(
                    """
                    INSERT INTO google_tool_calls
                        (call_sid, tool_name, arguments, result_summary, turn_number, called_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    [
                        (
                            self.call_sid,
                            tc.get("tool", ""),
                            json.dumps(tc.get("args", {})),
                            str(tc.get("result_summary") or tc.get("result") or "")[:500],
                            i,
                            _parse_dt(tc.get("timestamp") or tc.get("ts")) if (tc.get("timestamp") or tc.get("ts")) else now_dt,
                        )
                        for i, tc in enumerate(tool_calls)
                        if isinstance(tc, dict)
                    ],
                )
                logger.info(f"[BRAIN] PostgreSQL: {len(tool_calls)} tool call rows written")

            # Per-turn metrics (drives the Call Analysis dashboard turn view).
            # Sprint 0 expansion: every observability column is written through
            # the shared persist_turn_metrics path via the fuller INSERT below
            # so the Postgres rows carry slot/validation/mood/loop/subsystem
            # fields (not just latency + text like the legacy path did).
            if self._turn_metrics:
                try:
                    from server.brain.layer1.persist import build_turn_metrics_extra as _build_turn_metrics_extra
                except Exception:
                    _build_turn_metrics_extra = lambda _s: {}  # noqa: E731

                try:
                    from server.core.obs import get_build_sha
                    _build_sha = get_build_sha()
                except Exception:
                    _build_sha = None

                def _jd(val):
                    return json.dumps(val, ensure_ascii=False) if val is not None else None

                await conn.executemany(
                    """
                    INSERT INTO google_turn_metrics
                        (call_id, call_sid, tenant_id, turn_number,
                         user_text, bot_text,
                         stt_latency_ms, llm_latency_ms, tts_latency_ms, total_latency_ms,
                         tools_called, node_name, stage3_text,
                         stt_confidence, build_sha,
                         validation_breakdown, tts_situation, tts_mood,
                         prompt_tokens_in, prompt_tokens_out, max_output_tokens_config,
                         temperature_config, top_p_config,
                         slot_state_json, slot_state_diff,
                         slots_filled_count, slots_confirmed_count, slots_missing_required,
                         validations_fired_this_turn, validations_completed_this_turn,
                         validations_pending_end_of_turn, validation_cancellations,
                         raw_utterance_in_prompt, prompt_snapshot_head,
                         intent_flags_active, node_active, prompt_had_multiple_intents,
                         mood_confidence, mood_signals_matched,
                         barge_in_attempted, barge_in_succeeded, barge_in_latency_ms,
                         loop_detected_in_stream, loop_reason,
                         stream_aborted_at_sentence, cross_turn_similarity_max,
                         subsystems_fired, tts_rate_pct,
                         stt_ms, extract_ms, l2_ms, tool_ms, tts_first_byte_ms, total_ms,
                         extract_tokens_in, extract_tokens_out, cost_eur,
                         tool_durations, error_codes,
                         intent_classify_ms, worker_p50_ms, worker_p95_ms,
                         context_build_ms, generator_ttft_ms, tts_ttfb_ms,
                         eot_event_type, eot_confidence, eot_latency_ms,
                         backchannel_fired, eot_followed_immediately,
                         slot_extraction_latency_ms, slot_retention_status, validation_passes,
                         intent, turn_type, worker_profile)
                    VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12,$13,$14,$15,
                        $16::jsonb,$17,$18,
                        $19,$20,$21,$22,$23,
                        $24::jsonb,$25::jsonb,$26,$27,$28::jsonb,
                        $29::jsonb,$30::jsonb,$31::jsonb,$32,
                        $33,$34,
                        $35::jsonb,$36,$37,
                        $38,$39::jsonb,
                        $40,$41,$42,
                        $43,$44,$45,$46,
                        $47::jsonb,$48,
                        $49,$50,$51,$52,$53,$54,
                        $55,$56,$57,
                        $58::jsonb,$59::text[],
                        $60,$61,$62,$63,$64,$65,
                        $66,$67,$68,$69,$70,
                        $71,$72::jsonb,$73::jsonb,
                        $74,$75,$76
                    )
                    """,
                    [
                        (
                            call_uuid,
                            self.call_sid,
                            self.tenant_id,
                            int(tm.get("turn_number") or 0),
                            tm.get("user_text") or "",
                            tm.get("bot_text") or "",
                            int(tm.get("stt_latency_ms") or 0),
                            int(tm.get("llm_latency_ms") or 0),
                            int(tm.get("tts_latency_ms") or 0),
                            int(tm.get("total_latency_ms") or 0),
                            json.dumps(tm.get("tools_called") or []),
                            tm.get("node_name"),
                            tm.get("stage3_text") or tm.get("bot_text") or "",
                            tm.get("stt_confidence"),
                            _build_sha,
                            json.dumps(tm.get("validation_breakdown") or {}),
                            tm.get("tts_situation"),
                            tm.get("tts_mood"),
                            tm.get("prompt_tokens_in"),
                            tm.get("prompt_tokens_out"),
                            tm.get("max_output_tokens_config"),
                            tm.get("temperature_config"),
                            tm.get("top_p_config"),
                            _jd(tm.get("slot_state_json")),
                            _jd(tm.get("slot_state_diff")),
                            tm.get("slots_filled_count"),
                            tm.get("slots_confirmed_count"),
                            _jd(tm.get("slots_missing_required")),
                            _jd(tm.get("validations_fired_this_turn")),
                            _jd(tm.get("validations_completed_this_turn")),
                            _jd(tm.get("validations_pending_end_of_turn")),
                            tm.get("validation_cancellations"),
                            tm.get("raw_utterance_in_prompt"),
                            tm.get("prompt_snapshot_head"),
                            _jd(tm.get("intent_flags_active")),
                            tm.get("node_active"),
                            tm.get("prompt_had_multiple_intents"),
                            tm.get("mood_confidence"),
                            _jd(tm.get("mood_signals_matched")),
                            tm.get("barge_in_attempted"),
                            tm.get("barge_in_succeeded"),
                            tm.get("barge_in_latency_ms"),
                            tm.get("loop_detected_in_stream"),
                            tm.get("loop_reason"),
                            tm.get("stream_aborted_at_sentence"),
                            tm.get("cross_turn_similarity_max"),
                            _jd(tm.get("subsystems_fired")),
                            tm.get("tts_rate_pct"),
                            # Phase 9 A1 per-stage latency
                            tm.get("stt_ms"),
                            tm.get("extract_ms"),
                            tm.get("l2_ms"),
                            tm.get("tool_ms"),
                            tm.get("tts_first_byte_ms"),
                            tm.get("total_ms"),
                            tm.get("extract_tokens_in"),
                            tm.get("extract_tokens_out"),
                            tm.get("cost_eur"),
                            _jd(tm.get("tool_durations")),
                            tm.get("error_codes") or [],
                            # Phase 8.6 v4 latency layers
                            tm.get("intent_classify_ms"),
                            tm.get("worker_p50_ms"),
                            tm.get("worker_p95_ms"),
                            tm.get("context_build_ms"),
                            tm.get("generator_ttft_ms"),
                            tm.get("tts_ttfb_ms"),
                            tm.get("eot_event_type"),
                            tm.get("eot_confidence"),
                            tm.get("eot_latency_ms"),
                            tm.get("backchannel_fired"),
                            tm.get("eot_followed_immediately"),
                            tm.get("slot_extraction_latency_ms"),
                            _jd(tm.get("slot_retention_status")),
                            _jd(tm.get("validation_passes")),
                            # Phase A-D patch 1: intent classification columns
                            tm.get("intent"),
                            tm.get("turn_type"),
                            tm.get("worker_profile"),
                        )
                        for tm in self._turn_metrics
                    ],
                )
                logger.info(
                    f"[BRAIN] PostgreSQL: {len(self._turn_metrics)} turn_metric rows written"
                )

        finally:
            await conn.close()

        # Sprint 0.4: compute and write call-level aggregates
        # (avg/p50/p95/max latency, dead air, extractor success rate,
        #  validation invocations, loop incidents)
        try:
            from server.database import persist_call_aggregates
            await persist_call_aggregates(self.call_sid)
            logger.info(f"[BRAIN] PostgreSQL: call aggregates written for {self.call_sid}")
        except Exception as agg_e:
            logger.warning(f"[BRAIN] call aggregate write failed: {agg_e}")

    def _extract_latest_user_text(self, context) -> str:
        if hasattr(context, "messages"):
            for msg in reversed(context.messages):
                role = msg.get("role", "") if isinstance(msg, dict) else getattr(msg, "role", "")
                if role == "user":
                    content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                return part.get("text", "")
                            elif isinstance(part, str):
                                return part
                    return str(content)
        return ""

    # ── Production failure capture ────────────────────────────────────────────

    _FAILURE_CATALOG = Path(
        "/home/charles2/sailly-google-fork/server/scenarios/production_failures.py"
    )
    _QUALITY_FAILURE_THRESHOLD = 5.5  # Capture calls with auditor score below this

    async def _capture_failed_call(self, session_data: dict, reason: str):
        """
        If a production demo call is poor quality, auto-generate a validation scenario
        from its transcript and append it to production_failures.py.

        The scenario is automatically picked up by ab_test_loop when that file exists.
        """
        transcripts = session_data.get("transcripts", [])
        if not transcripts or len(transcripts) < 3:
            return  # Too short to be a meaningful scenario

        # Check auditor score (only capture low-quality or error calls)
        quality_score = session_data.get("quality_score", 10.0)
        has_error = reason in ("error", "timeout", "crash")
        if not has_error and float(quality_score or 10) >= self._QUALITY_FAILURE_THRESHOLD:
            return

        # Build scenario turns from transcript
        user_turns = [
            t.get("content", "").strip()
            for t in transcripts
            if isinstance(t, dict) and t.get("role") in ("user", "caller")
            and t.get("content", "").strip()
        ]
        if not user_turns:
            return

        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d-%H%M%S")
        scenario_id = f"prod-fail-{ts}"
        escaped_turns = [u.replace('"', '\\"').replace("\\", "\\\\") for u in user_turns]
        turns_code = "\n".join(
            f'        ScenarioTurn(user_utterance="{u}"),'
            for u in escaped_turns
        )
        tool_names = [tc.get("tool", "") for tc in session_data.get("tool_calls", []) if tc.get("tool")]
        tools_code = ", ".join(f'"{t}"' for t in tool_names)
        scenario_code = f'''\
    AudioScenario(
        id="{scenario_id}",
        phase="production",
        category="regression",
        description="Auto-captured from failed demo call (score={quality_score}, reason={reason})",
        persona="neutral",
        noise_variant="clean",
        turns=[
{turns_code}
        ],
        expected_tools=[{tools_code}],
    ),
'''
        # Ensure the file exists with proper header
        if not self._FAILURE_CATALOG.exists():
            self._FAILURE_CATALOG.parent.mkdir(parents=True, exist_ok=True)
            self._FAILURE_CATALOG.write_text(
                '"""Auto-captured production failure scenarios."""\n'
                "from server.training.ab_models import AudioScenario, ScenarioTurn\n\n"
                "PRODUCTION_FAILURE_SCENARIOS = [\n]\n"
            )

        # Append before the closing bracket
        content = self._FAILURE_CATALOG.read_text(encoding="utf-8")
        if "PRODUCTION_FAILURE_SCENARIOS = [" in content:
            content = content.rstrip().rstrip("]").rstrip() + "\n" + scenario_code + "]\n"
            self._FAILURE_CATALOG.write_text(content, encoding="utf-8")
            logger.info(
                f"[BRAIN] Captured failed call as scenario {scenario_id} "
                f"(score={quality_score}, reason={reason}, turns={len(user_turns)})"
            )
