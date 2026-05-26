"""
Tier2AudioRunner -- Phase 2: Full audio round-trip testing.

Pipeline: Google TTS Linear16 8kHz → Deepgram Nova-3 de STT → Claude Haiku (Vertex AI, EU) → Gemini Flash TTS
N=3 runs per scenario. Collects real latencies, audio bytes, WER, tool calls.
Validates all checkpoints (STT accuracy gate, tool execution, TTS synthesis).

LLM: Claude Haiku 4.5 via Vertex AI, default region europe-west1; avoid region="eu" (path locations/eu often 404s for Anthropic :rawPredict).
TTS engine is configurable via TTS_ENGINE env var or tts_engine constructor arg:
  gemini-flash  (DEFAULT) — Gemini 2.5 Flash TTS, 321ms avg, emotion tags, EU-compliant
  gemini-pro               — Gemini 2.5 Pro TTS
  neural2                  — de-DE-Neural2-C (legacy fallback)

DEPRECATED: chirp3hd removed (2026-04-14) — cost too high for validation runs ($32/1M chars)
"""

import asyncio
import logging
import random
import os
import re
import time
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

# Matches a complete [TOOL:name] tag (with optional trailing whitespace) so we
# can strip it from TTS-bound text while keeping it in full_buf for downstream
# tool extraction.
_TOOL_TAG_RE = re.compile(r"\[TOOL:\w+\]\s*")

if TYPE_CHECKING:
    from server.brain.cost_tracker import CostTracker
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Tier2TurnResult:
    """Result of a single turn in Tier 2."""
    user_utterance: str
    stt_transcript: str
    wer: float
    llm_response: str
    tts_audio_bytes: int
    tools_called: List[str]
    tool_latency_ms: float
    total_latency_ms: float
    passed: bool


@dataclass
class Tier2RunResult:
    """Result of running a Tier 2 scenario."""
    scenario_id: str
    run_number: int
    turns: List[Tier2TurnResult]
    tools_called: List[str]
    tools_failed: List[str]
    total_audio_bytes: int
    total_latency_ms: float
    passed: bool
    error_message: Optional[str] = None
    score_dimensions: Optional[Dict[str, float]] = None


@dataclass
class _UsageShim:
    """Maps Anthropic token counts to the field names read by adk_turn_processor."""
    prompt_token_count: int
    candidates_token_count: int


class Tier2AudioRunner:
    """
    Phase 2 runner: Full audio round-trip.
    """

    def __init__(
        self,
        google_project_id: str,
        deepgram_api_key: str,
        gemini_model: str = os.environ.get(
            "MAIN_LLM_MODEL", "claude-haiku-4-5@20251001"
        ),
        temperature: float = 0.2,
        tts_engine: str = os.environ.get("TTS_ENGINE", "gemini-flash"),
        cost_tracker: Optional["CostTracker"] = None,
    ):
        """
        Args:
            google_project_id: GCP project ID
            deepgram_api_key: Deepgram API key
            gemini_model: Gemini model name
            temperature: LLM temperature
            tts_engine: TTS engine — "gemini-flash" (DEFAULT), "gemini-pro", "neural2"
                        Overridable via TTS_ENGINE environment variable.
                        DEPRECATED: chirp3hd removed (cost $32/1M chars, too expensive for validation)
            cost_tracker: Optional accumulator for A/B cost estimates
        """
        self.google_project_id = google_project_id
        self.deepgram_api_key = deepgram_api_key
        self.gemini_model = gemini_model
        self.temperature = temperature
        self.tts_engine = tts_engine
        self.cost_tracker = cost_tracker

        self.audio_injector = None
        self.llm_client = None
        self.tts_client = None

        self._last_stream_usage_metadata = None
        self.scorer = None

        # Hot-swappable prompt (set by AI-autofix in audio_training_loop.py)
        self._active_prompt_override: Optional[str] = None

        # Per-node model routing — smaller/faster model for conversational nodes
        # where token budget and complexity are low (greeting, faq, goodbye,
        # small-talk), default model for everything stateful (ordering,
        # reservation, escalation).  Override via env var or disable by
        # leaving SAILLY_FAST_MODEL unset.
        self._fast_model: str = os.environ.get("SAILLY_FAST_MODEL", "").strip()
        self._fast_nodes: set = set(
            (os.environ.get("SAILLY_FAST_NODES", "greeting,faq,goodbye,small_talk")
             .replace(" ", "")).split(",")
        )

    def model_for_node(self, node_name: Optional[str]) -> str:
        """Return the Gemini model to use for a turn happening on ``node_name``.
        Falls back to the default ``gemini_model`` when routing is disabled
        or the node is unknown."""
        if self._fast_model and node_name and node_name in self._fast_nodes:
            return self._fast_model
        return self.gemini_model

    def set_cost_tracker(self, tracker: Optional["CostTracker"]) -> None:
        """Attach or swap cost tracker (e.g. per A/B arm). Syncs AudioInjector if present."""
        self.cost_tracker = tracker
        if self.audio_injector is not None:
            self.audio_injector.cost_tracker = tracker

    def _init_clients(self):
        """Lazy initialize all API clients once per runner."""
        if self.audio_injector is None:
            try:
                from server.brain.audio_injector import AudioInjector
                self.audio_injector = AudioInjector(
                    google_project_id=self.google_project_id,
                    deepgram_api_key=self.deepgram_api_key,
                    cost_tracker=self.cost_tracker,
                )
                logger.debug("Initialized AudioInjector")
            except Exception as e:
                logger.warning(f"Failed to init AudioInjector: {e}")
        
        # Initialize LLM client ONCE per runner (critical latency optimization)
        # Uses Anthropic Claude Opus 4.1 via standard API (temporary until Haiku quota approved).
        # Auth via ANTHROPIC_API_KEY environment variable.
        if self.llm_client is None:
            try:
                from anthropic import AsyncAnthropic

                _api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                if not _api_key:
                    logger.warning("[LLM] ANTHROPIC_API_KEY not set — LLM calls will fail")
                self.llm_client = AsyncAnthropic(api_key=_api_key)
                logger.info(
                    f"[LLM/Anthropic] client ready via standard API (claude-opus-4-1) "
                    f"— using until Haiku quota approved"
                )
            except Exception as e:
                logger.warning(f"Failed to init LLM client: {e}")
        
        # Initialize TTS client ONCE per runner (critical latency optimization)
        if self.tts_client is None:
            try:
                from google.cloud import texttospeech
                from google.oauth2 import service_account as _sa
                _key_file = os.environ.get(
                    "GOOGLE_APPLICATION_CREDENTIALS",
                    "/home/charles2/.ssh/sailly-voice-agent-key.json",
                )
                _tts_creds = _sa.Credentials.from_service_account_file(
                    _key_file,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                self.tts_client = texttospeech.TextToSpeechClient(credentials=_tts_creds)
                logger.debug("Initialized TTS client (will reuse for all turns)")
            except Exception as e:
                logger.warning(f"Failed to init TTS client: {e}")

    async def run_scenario(
        self,
        scenario: Any,
        run_number: int,
        scorer: Any,
    ) -> Tier2RunResult:
        """
        Run a single Tier 2 scenario with full audio round-trip.

        Args:
            scenario: AudioScenario object (from tier2_scenarios)
            run_number: Which run (1, 2, or 3)
            scorer: MultiDimensionalScorer instance

        Returns:
            Tier2RunResult with latencies, audio bytes, and scores
        """
        self._init_clients()

        scenario_id = scenario.id
        start_time = time.time()

        try:
            logger.info(f"Running {scenario_id} (run {run_number}/3)...")

            turns_results = []
            tools_called = []
            tools_failed = []
            total_audio_bytes = 0

            # Run through scenario turns
            for turn_idx, turn in enumerate(scenario.turns):
                turn_start = time.time()

                # Step 1: Synthesize caller audio (via Google TTS)
                audio_segment, stt_transcript, wer = await self.audio_injector.inject_caller_turn(
                    user_utterance=turn.user_utterance,
                    noise_variant=scenario.noise_variant,
                    stt_min_accuracy=turn.stt_min_accuracy,
                )

                stt_latency = (time.time() - turn_start) * 1000

                # Step 2: Call Gemini LLM (text-mode, processes STT transcript)
                llm_start = time.time()
                llm_response = await self._call_gemini_lm(
                    user_message=stt_transcript,
                    context=[],  # Simplified: no context tracking
                )
                llm_latency = (time.time() - llm_start) * 1000

                # Step 3: Call Chirp3 HD TTS to synthesize bot response
                tts_start = time.time()
                tts_audio, tts_latency = await self._synthesize_response(llm_response)
                tts_latency_ms = (time.time() - tts_start) * 1000

                # Extract tools from LLM response
                turn_tools = self._parse_tool_calls(llm_response)
                tools_called.extend(turn_tools)

                total_audio_bytes += len(tts_audio)

                # Create turn result
                total_turn_latency = (time.time() - turn_start) * 1000
                turn_passed = wer <= (1.0 - turn.stt_min_accuracy)

                turn_result = Tier2TurnResult(
                    user_utterance=turn.user_utterance,
                    stt_transcript=stt_transcript,
                    wer=wer,
                    llm_response=llm_response,
                    tts_audio_bytes=len(tts_audio),
                    tools_called=turn_tools,
                    tool_latency_ms=llm_latency,
                    total_latency_ms=total_turn_latency,
                    passed=turn_passed,
                )
                turns_results.append(turn_result)

                logger.debug(
                    f"  Turn {turn_idx + 1}: STT WER {wer:.2%}, LLM {llm_latency:.0f}ms, TTS {tts_latency_ms:.0f}ms"
                )

            # Determine overall pass/fail
            passed = all(t.passed for t in turns_results) and len(tools_called) >= len(scenario.expected_tools)

            elapsed_ms = (time.time() - start_time) * 1000

            # Score the scenario
            score_dimensions = self._score_scenario(
                scenario=scenario,
                turns=turns_results,
                tools_called=tools_called,
            )

            result = Tier2RunResult(
                scenario_id=scenario_id,
                run_number=run_number,
                turns=turns_results,
                tools_called=tools_called,
                tools_failed=tools_failed,
                total_audio_bytes=total_audio_bytes,
                total_latency_ms=elapsed_ms,
                passed=passed,
                score_dimensions=score_dimensions,
            )

            logger.info(f"✓ {scenario_id} (run {run_number}): {'PASS' if passed else 'FAIL'} - {elapsed_ms:.0f}ms")
            return result

        except Exception as e:
            logger.error(f"✗ {scenario_id} (run {run_number}): {e}")
            elapsed_ms = (time.time() - start_time) * 1000
            return Tier2RunResult(
                scenario_id=scenario_id,
                run_number=run_number,
                turns=[],
                tools_called=tools_called,
                tools_failed=tools_failed,
                total_audio_bytes=total_audio_bytes,
                total_latency_ms=elapsed_ms,
                passed=False,
                error_message=str(e),
            )

    async def call_gemini_stream(
        self,
        user_message: str,
        context: List[Dict],
        tts_callback=None,  # async (chunk: str) -> None, called per sentence
        node_hint: Optional[str] = None,
    ) -> str:
        """Stream Claude Haiku via Anthropic API and push sentence chunks to TTS.

        As soon as each sentence completes (boundary = . ! ? or newline) it is
        forwarded to ``tts_callback`` so TTS can start speaking ~300 ms after
        the first token, instead of waiting for the complete response.

        Chunks that contain a ``[TOOL:`` marker are intentionally withheld from
        TTS — they are returned in the full text for the tool-execution layer.

        The full accumulated text is returned so the caller can perform all
        existing state management and tool parsing unchanged.

        Retry policy: 2 attempts x 500 ms backoff for 429 / throttling errors.
        """
        self._init_clients()

        system_prompt = getattr(self, "_active_prompt_override", None) or ""
        messages = self._build_claude_messages(context, user_message)
        # 512 tokens ≈ 2-3 voice sentences — tuned for voice-first responses.
        # Stop sequences: "\n---\n" matches standalone markdown HR lines only.

        # Per-node model routing — small/fast model on trivial conversational
        # nodes (greeting/faq/goodbye), default model otherwise.
        active_model = self.model_for_node(node_hint)
        if active_model != self.gemini_model:
            logger.info(f"[LLM-ROUTE] node={node_hint!r} → model={active_model!r}")

        import time as _tm
        _start = _tm.monotonic()
        _first_chunk_logged = False
        full_buf = ""
        last_err = None
        self._last_stream_usage_metadata = None  # reset each turn

        # Sentence 1 is flushed immediately to preserve first-word latency.
        # Sentences 2+ are batched until they reach _MIN_SUBSEQUENT_CHARS.
        _MIN_SUBSEQUENT_CHARS = 120

        for attempt in range(2):
            full_buf = ""
            sent_buf = ""
            _sent_count = 0
            try:
                async with self.llm_client.messages.stream(
                    model=active_model,
                    max_tokens=512,
                    system=system_prompt,
                    messages=messages,
                    temperature=self.temperature,
                    stop_sequences=["\n---\n", "\n\nBEKANNTE DATEN:", "\n\n==="],
                ) as stream:
                    async for tok in stream.text_stream:
                        if not tok:
                            continue
                        full_buf += tok
                        sent_buf += tok

                        if not _first_chunk_logged:
                            _first_chunk_logged = True
                            logger.info(
                                f"[LAT-STREAM] first_token={(_tm.monotonic()-_start)*1000:.0f}ms"
                            )

                        # Flush on sentence boundary
                        if tok[-1] in ".!?\n":
                            sent_chunk = sent_buf.strip()
                            # Guard against partial [TOOL: tags split across token boundaries
                            if sent_chunk and "[TOOL:" not in sent_chunk and "[" not in sent_chunk[-5:] and tts_callback:
                                # Short exclamatory fragments (<15 chars) sound robotic when dispatched
                                # as isolated TTS clips. Merge them with the following sentence.
                                _is_short_exclaim = len(sent_chunk) < 15
                                if _sent_count == 0 and _is_short_exclaim:
                                    logger.debug(
                                        f"[STREAM] deferring short exclamation {sent_chunk!r} "
                                        f"— merging with next sentence"
                                    )
                                elif _sent_count == 0 or len(sent_chunk) >= _MIN_SUBSEQUENT_CHARS:
                                    try:
                                        await tts_callback(sent_chunk)
                                    except Exception as _cb_err:
                                        logger.debug(f"[STREAM] tts_callback error (non-fatal): {_cb_err}")
                                    sent_buf = ""
                                    _sent_count += 1

                    # Flush any remaining text (no trailing punctuation, or batched remainder)
                    if sent_buf.strip() and tts_callback and "[TOOL:" not in sent_buf:
                        try:
                            await tts_callback(sent_buf.strip())
                        except Exception as _cb_err:
                            logger.debug(f"[STREAM] tts_callback trailing flush error: {_cb_err}")
                        _sent_count += 1

                    # Capture token usage from the final message
                    final_msg = await stream.get_final_message()
                    self._last_stream_usage_metadata = _UsageShim(
                        prompt_token_count=final_msg.usage.input_tokens,
                        candidates_token_count=final_msg.usage.output_tokens,
                    )

                logger.info(
                    f"[LAT-STREAM] stream_done={(_tm.monotonic()-_start)*1000:.0f}ms "
                    f"chars={len(full_buf)}"
                )
                break  # success — exit retry loop

            except Exception as inner_e:
                last_err = inner_e
                err_str = str(inner_e)
                if ("429" in err_str or "rate_limit" in err_str.lower() or "throttl" in err_str.lower()) and attempt == 0:
                    logger.warning("[STREAM] Anthropic 429/throttle attempt 1/2 — backoff 500ms")
                    await asyncio.sleep(0.5)
                    continue
                logger.warning(f"[STREAM] Claude stream failed attempt {attempt+1}/2: {inner_e}")
                break

        if not full_buf:
            if last_err:
                raise last_err
            # Empty response — fall back to a safe default
            logger.warning("[STREAM] Empty response from Claude stream")
            return "Wie kann ich Ihnen helfen?"

        return full_buf.strip()

    def _build_claude_messages(self, context: List[Dict], user_message: str) -> List[Dict]:
        """Build Anthropic messages list from conversation history + new user message."""
        messages = []
        for msg in (context or []):
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def _call_gemini_lm(
        self,
        user_message: str,
        context: List[Dict],
    ) -> str:
        """Blocking (non-streaming) Claude call — kept for validation / training code."""
        self._init_clients()
        system_prompt = getattr(self, "_active_prompt_override", None) or ""

        try:
            messages = self._build_claude_messages(context, user_message)

            last_err = None
            for attempt in range(2):
                try:
                    import time as _time_mark
                    _llm_start = _time_mark.monotonic()

                    response = await self.llm_client.messages.create(
                        model=self.gemini_model,
                        max_tokens=1024,
                        system=system_prompt,
                        messages=messages,
                        temperature=self.temperature,
                        stop_sequences=["---", "\n\nBEKANNTE DATEN:", "\n\n==="],
                    )

                    _llm_delta = (_time_mark.monotonic() - _llm_start) * 1000
                    logger.info(f"[LAT-2026-04-20] llm_call_start->llm_done={_llm_delta:.0f}ms")

                    if self.cost_tracker is not None:
                        self.cost_tracker.add_gemini_usage(
                            prompt_tokens=response.usage.input_tokens,
                            candidates_tokens=response.usage.output_tokens,
                        )

                    text = ""
                    for block in response.content:
                        if hasattr(block, "text") and block.text:
                            text += block.text

                    return text.strip()

                except Exception as inner_e:
                    last_err = inner_e
                    err_str = str(inner_e)
                    if ("429" in err_str or "rate_limit" in err_str.lower() or "throttl" in err_str.lower()) and attempt == 0:
                        logger.warning(f"Bedrock 429/throttle attempt 1/2 — backoff 500ms")
                        await asyncio.sleep(0.5)
                        continue
                    raise

            raise last_err

        except Exception as e:
            logger.warning(f"Claude API call failed ({e}), using fallback")
            if "bestellen" in user_message.lower():
                return "Gerne! Was möchten Sie bestellen?"
            elif "reservieren" in user_message.lower():
                return "Super, für wie viele Personen und wann?"
            return random.choice([
                "Wie kann ich dir helfen?",
                "Womit kann ich dir noch helfen?",
                "Brauchst du noch was?",
                "Was kann ich noch für dich tun?",
            ])

    def _get_voice_params(self):
        """Return VoiceSelectionParams for the configured TTS engine.

        Gemini TTS models use model_name= (not name=).
        Legacy Neural2 uses name=.
        Chirp3 HD is DEPRECATED (cost $32/1M chars) — use gemini-flash instead.
        """
        from google.cloud import texttospeech
        
        if self.tts_engine == "gemini-flash":
            return texttospeech.VoiceSelectionParams(
                language_code="de-DE",
                model_name="gemini-2.5-flash-tts",
            )
        elif self.tts_engine == "gemini-pro":
            return texttospeech.VoiceSelectionParams(
                language_code="de-DE",
                model_name="gemini-2.5-pro-tts",
            )
        elif self.tts_engine == "neural2":
            return texttospeech.VoiceSelectionParams(
                language_code="de-DE",
                name="de-DE-Neural2-C",
            )
        elif self.tts_engine == "chirp3hd":
            return texttospeech.VoiceSelectionParams(
                language_code="de-DE",
                name="de-DE-Chirp3-HD-Aoede",
            )
        else:
            raise ValueError(
                f"Unknown TTS engine: {self.tts_engine}. "
                f"Supported: gemini-flash (DEFAULT), gemini-pro, neural2, chirp3hd"
            )

    def _prepare_text_for_tts(self, text: str) -> str:
        """Strip tool tags and inject Gemini emotion prefix when using a Gemini TTS engine.

        Emotion tags are only added for gemini-* engines; legacy voices ignore them.
        Supported tags: [friendly], [empathetic], [calm], [cheerful], [warm]
        """
        import re as _re
        clean = _re.sub(r"`?\[TOOL:\w+\]`?", "", text).strip()
        if not clean or not self.tts_engine.startswith("gemini"):
            return clean

        lower = clean.lower()
        empathy_kw = ["entschuldigung", "leider", "tut mir leid", "bedauere",
                      "leider nicht", "leider koennen wir"]
        calm_kw = ["weiterleite", "kollege", "moment bitte", "technisch"]
        cheerful_kw = ["bestellt", "reserviert", "aufgenommen", "gebucht",
                       "perfekt", "wunderbar", "freue mich"]
        warm_kw = ["auf wiedersehen", "tschuess", "schoenen tag",
                   "schoenen abend", "vielen dank fuer ihren anruf"]
        greeting_kw = ["hallo, hier ist", "hallo! hier ist", "hier ist sailly", "willkommen bei"]

        if any(w in lower for w in empathy_kw):
            return "[empathetic] " + clean
        elif any(w in lower for w in calm_kw):
            return "[calm] " + clean
        elif any(w in lower for w in cheerful_kw):
            return "[cheerful] " + clean
        elif any(w in lower for w in warm_kw):
            return "[warm] " + clean
        elif any(w in lower for w in greeting_kw):
            return "[warm] " + clean
        else:
            return "[friendly] " + clean

    async def _synthesize_response(
        self,
        text: str,
    ) -> Tuple[bytes, float]:
        """Synthesize bot response via Google Cloud TTS.

        Engine is determined by self.tts_engine (default: gemini-flash).
        Falls back to a silent placeholder on error.

        Returns:
            Tuple of (audio_bytes, latency_ms)
        """
        tts_text = self._prepare_text_for_tts(text)
        if not tts_text:
            return b"\x00" * 1600, 0.0

        if self.cost_tracker is not None:
            self.cost_tracker.add_bot_tts_chars(len(tts_text))

        start = time.time()
        try:
            from google.cloud import texttospeech
            self._init_clients()

            synthesis_input = texttospeech.SynthesisInput(text=tts_text)
            voice = self._get_voice_params()
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=8000,
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.tts_client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config,
                ),
            )
            latency_ms = (time.time() - start) * 1000
            logger.debug(
                f"TTS [{self.tts_engine}] {latency_ms:.0f}ms "
                f"({len(response.audio_content)} bytes)"
            )
            return response.audio_content, latency_ms

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.warning(f"Bot TTS failed ({e}), using silent placeholder")
            duration_samples = max(1600, int(len(tts_text) * 80))
            return b"\x00" * (duration_samples * 2), latency_ms

    def _parse_tool_calls(self, response_text: str) -> List[str]:
        """Parse tool calls from LLM response.

        Recognises both [TOOL:name] tags and `[TOOL:name]` (backtick-wrapped)
        variants that Gemini sometimes produces.  Also picks up bare
        function_call names injected by the Vertex response handler.
        """
        import re
        tools = []
        # F5: Added request_callback to tool_names so it can be parsed from responses
        tool_names = [
            "ai_greeting",
            "get_menu", "check_availability", "create_reservation",
            "create_order", "send_sms", "technical_issues_callback",
            "verify_address", "update_state",
            "transfer_to_human", "transfer_to_ordering", "transfer_to_tier2",
            "get_date_info", "get_weather", "get_directions", "get_nearby_parking", "end_call", "faq",
            "request_callback",
        ]
        for m in re.finditer(r'\[TOOL:(\w+)', response_text):
            name = m.group(1)
            if name in tool_names:
                tools.append(name)
        if not tools:
            for tool in tool_names:
                if f"[TOOL:{tool}]" in response_text or f"`[TOOL:{tool}]`" in response_text:
                    tools.append(tool)
        return tools

    def _score_scenario(
        self,
        scenario: Any,
        turns: List[Tier2TurnResult],
        tools_called: List[str],
    ) -> Dict[str, float]:
        """
        Score a Tier 2 scenario across 6 dimensions.

        Args:
            scenario: AudioScenario
            turns: List of turn results
            tools_called: Tools called

        Returns:
            Dict of dimension scores
        """
        scores = {}

        # Task Completion
        task_score = 100.0
        for expected_tool in scenario.expected_tools:
            if expected_tool not in tools_called:
                task_score -= 30.0
        scores["task_completion"] = max(0, min(100, task_score))

        # Language Compliance
        lang_score = 100.0
        for turn in turns:
            if "(" in turn.llm_response and ")" in turn.llm_response:
                lang_score -= 20.0  # Emotional tag
        scores["language_compliance"] = max(0, min(100, lang_score))

        # Instruction Following
        instr_score = 50.0  # Default
        scores["instruction_following"] = instr_score

        # Latency (ms)
        avg_latency = sum(t.total_latency_ms for t in turns) / len(turns) if turns else 0
        latency_score = max(0, 100 - (avg_latency / 50))  # Penalty for slow responses
        scores["latency"] = latency_score

        # Audio Quality
        total_audio = sum(t.tts_audio_bytes for t in turns)
        audio_score = 100.0 if total_audio > 500 else 50.0
        scores["audio_quality"] = audio_score

        # STT Accuracy (WER)
        avg_wer = sum(t.wer for t in turns) / len(turns) if turns else 0
        stt_accuracy = 1.0 - avg_wer
        scores["stt_accuracy"] = stt_accuracy * 100.0

        # Overall
        scores["overall"] = (
            scores["task_completion"] * 0.25
            + scores["language_compliance"] * 0.20
            + scores["instruction_following"] * 0.20
            + scores["latency"] * 0.15
            + scores["audio_quality"] * 0.10
            + scores["stt_accuracy"] * 0.10
        )

        return scores

    async def run_all_scenarios(
        self,
        scenarios: List[Any],
        scorer: Any,
    ) -> List[Tier2RunResult]:
        """Run all Tier 2 scenarios (N=3 runs each)."""
        all_results = []

        for scenario in scenarios:
            for run_num in range(1, scenario.n_runs + 1):
                result = await self.run_scenario(scenario, run_num, scorer)
                all_results.append(result)

        return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    runner = Tier2AudioRunner(
        google_project_id="your-project-id",
        deepgram_api_key="your-deepgram-key",
    )

    print("✓ Tier2AudioRunner initialized successfully")
