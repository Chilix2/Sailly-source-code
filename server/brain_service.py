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

from server.brain.adk_turn_processor import ADKTurnProcessor
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

                async def _tts_push(chunk: str) -> None:
                    nonlocal _streamed_chunks, _full_response_buf, _tts_turn_start
                    # Capture when TTS actually starts streaming (not when turn processing started).
                    # This is the correct anchor for the barge-in comparison: we only want to
                    # suppress chunks if the user spoke AFTER audio started playing, not during
                    # the LLM generation window.
                    if not _streamed_chunks:
                        _tts_turn_start = time.time()
                    # Barge-in suppression: if user started speaking AFTER this
                    # turn's TTS began streaming, the caller has interrupted —
                    # suppress audio but STILL accumulate _full_response_buf so
                    # bot_text in the DB reflects the complete LLM response, not
                    # the truncated pre-barge-in portion. (PR-16c)
                    if self._barge_in_ts > _tts_turn_start:
                        logger.debug(
                            f"[BRAIN] TTS chunk suppressed (barge-in): "
                            f"barge_in={self._barge_in_ts:.3f} tts_start={_tts_turn_start:.3f}"
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
                else:
                    tts_text = _sanitize_for_tts(result.clean_text)
                    if tts_text:
                        timer.mark("tts_text_pushed")
                        await self.push_frame(LLMFullResponseStartFrame())
                        await self.push_frame(LLMTextFrame(text=f"{_directive.inline_tag} {tts_text}"))
                        await self.push_frame(LLMFullResponseEndFrame())
                    else:
                        logger.warning(
                            f"[BRAIN] Skipping TTS for empty/trivial fragment: {result.clean_text!r}"
                        )

                # Accumulate per-turn metrics for google_turn_metrics persistence
                try:
                    self._turn_counter += 1
                    node_name = None
                    try:
                        state = getattr(self.turn_processor, "state", None)
                        node_name = getattr(state, "current_node", None) if state else None
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
                        "tts_latency_ms": None,  # set if measurable
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
                    })
                except Exception as me:
                    logger.debug(f"[BRAIN] turn_metrics accumulate failed: {me}")

                if self.session:
                    try:
                        await self.session.add_transcript("assistant", result.clean_text)
                    except Exception:
                        pass

                # Send bot transcript to browser
                await self._send_to_browser("transcript", speaker="bot", text=result.clean_text)

                if result.should_end:
                    # Estimate farewell audio length for the sleep guard.
                    # Use streamed chars if available, else result.clean_text.
                    _spoken = "".join(_streamed_chunks) if _streamed_chunks else _sanitize_for_tts(result.clean_text) or ""
                    if _spoken:
                        _farewell_secs = max(2.0, min(10.0, len(_spoken) / _CHARS_PER_SEC_DE + 1.5))
                        logger.info(
                            f"[BRAIN] Waiting {_farewell_secs:.1f}s for farewell TTS before EndFrame "
                            f"({len(_spoken)} chars)"
                        )
                        await asyncio.sleep(_farewell_secs)
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

            logger.info("[BRAIN-GREET] Triggering turn-0 greeting")
            # EU AI Act Art. 50: the first bot line MUST contain the token "KI".
            # Text is loaded from tenant config (greeting_line) with a hard fallback
            # that keeps the KI disclosure even if the tenant config failed to load.
            _fallback_greeting = (
                "Hallo, hier ist Sailly, die KI-Assistentin vom DOBOO Korean Soulfood. — schön, dass Sie anrufen! Was kann ich für Sie tun?"
            )
            tenant = getattr(self.turn_processor, "_tenant", None) if self.turn_processor else None
            greeting_text = (getattr(tenant, "greeting_line", None) or _fallback_greeting).strip()
            if " KI" not in f" {greeting_text}":
                logger.error(
                    "[BRAIN-GREET] tenant.greeting_line missing 'KI' token — "
                    "falling back to compliant default (EU AI Act Art. 50)"
                )
                greeting_text = _fallback_greeting

            class GreetingResult:
                clean_text = greeting_text
            result = GreetingResult()
            if result.clean_text:
                logger.info(f"[BRAIN-GREET] '{result.clean_text[:120]}'")

                if self.session:
                    try:
                        await self.session.add_transcript("assistant", result.clean_text)
                    except Exception:
                        pass

                # Send bot transcript to browser
                await self._send_to_browser("transcript", speaker="bot", text=result.clean_text)

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

                tts_greet = _sanitize_for_tts(result.clean_text)
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
        tool_calls = session_data.get("tool_calls", [])
        tool_names = [tc.get("tool", "") for tc in tool_calls]
        was_escalated = any(t in ("transfer_to_human", "transfer_to_tier2") for t in tool_names)

        conn = await asyncpg.connect(db_url)
        try:
            # Insert into google_calls
            row = await conn.fetchrow(
                """
                INSERT INTO google_calls
                    (call_sid, caller_number, started_at, ended_at, duration_seconds,
                     quality_score, outcome, language, was_escalated,
                     total_cost_tokens, total_cost_telephony, session_data)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (call_sid) DO NOTHING
                RETURNING id
                """,
                self.call_sid,
                "browser_demo",
                started_at,
                ended_at,
                duration_secs,
                5.0,
                reason,
                "de",
                was_escalated,
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
                            t.get("role", "user"),
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
                         tool_durations, error_codes)
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
                        $58::jsonb,$59::text[]
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
