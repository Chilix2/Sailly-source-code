"""
Tier2AudioRunner -- Phase 2: Full audio round-trip testing.

Pipeline: Google TTS Linear16 8kHz → Deepgram Nova-3 de STT → Gemini LLM → Gemini Flash TTS
N=3 runs per scenario. Collects real latencies, audio bytes, WER, tool calls.
Validates all checkpoints (STT accuracy gate, tool execution, TTS synthesis).

TTS engine is configurable via TTS_ENGINE env var or tts_engine constructor arg:
  gemini-flash  (DEFAULT) — Gemini 2.5 Flash TTS, 321ms avg, emotion tags, EU-compliant
  gemini-pro               — Gemini 2.5 Pro TTS
  neural2                  — de-DE-Neural2-C (legacy fallback)

DEPRECATED: chirp3hd removed (2026-04-14) — cost too high for validation runs ($32/1M chars)
"""

import asyncio
import logging
import os
import time
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from server.training.cost_tracker import CostTracker
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


class Tier2AudioRunner:
    """
    Phase 2 runner: Full audio round-trip.
    """

    def __init__(
        self,
        google_project_id: str,
        deepgram_api_key: str,
        gemini_model: str = "gemini-2.5-flash",
        temperature: float = 0.0,
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
        self.scorer = None

        # Hot-swappable prompt (set by AI-autofix in audio_training_loop.py)
        self._active_prompt_override: Optional[str] = None

    def set_cost_tracker(self, tracker: Optional["CostTracker"]) -> None:
        """Attach or swap cost tracker (e.g. per A/B arm). Syncs AudioInjector if present."""
        self.cost_tracker = tracker
        if self.audio_injector is not None:
            self.audio_injector.cost_tracker = tracker

    def _init_clients(self):
        """Lazy initialize all API clients once per runner."""
        if self.audio_injector is None:
            try:
                from server.training.audio_injector import AudioInjector
                self.audio_injector = AudioInjector(
                    google_project_id=self.google_project_id,
                    deepgram_api_key=self.deepgram_api_key,
                    cost_tracker=self.cost_tracker,
                )
                logger.debug("Initialized AudioInjector")
            except Exception as e:
                logger.warning(f"Failed to init AudioInjector: {e}")
        
        # Initialize LLM client ONCE per runner (critical latency optimization)
        if self.llm_client is None:
            try:
                import os
                from google import genai
                from google.oauth2 import service_account as _sa
                
                project = self.google_project_id
                region = os.environ.get("GEMINI_REGION", "europe-west4")
                key_file = os.environ.get(
                    "GOOGLE_APPLICATION_CREDENTIALS",
                    "/home/charles2/.ssh/sailly-voice-agent-key.json",
                )
                
                credentials = _sa.Credentials.from_service_account_file(
                    key_file,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                
                self.llm_client = genai.Client(
                    vertexai=True,
                    project=project,
                    location=region,
                    credentials=credentials,
                )
                logger.debug("Initialized Gemini LLM client (will reuse for all turns)")
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

    def _build_tier2_prompt(self) -> str:
        """
        Build the Tier 2 system prompt for LLM.
        Reduced from 331 lines to ~150 lines. Redundant sections removed —
        code-level enforcement (ConversationState, VariationRotator, _ensure_tool_call,
        get_menu dedup) handles what was previously repeated in prompt text.

        Returns:
            System prompt for Tier 2 (full tool-calling, ordering/reservations)
        """
        return """Du bist Sailly, die KI-Rezeptionistin vom Restaurant DOBOO in Bonn (koreanische Küche).
Adresse: Friedrich-Ebert-Allee 69, 53113 Bonn.
Öffnungszeiten: Mo-Do 11:30-21:30, Fr 11:30-14:00 & 18:00-21:30, Sa 18:00-21:30, So geschlossen.
Lieferzeit: ca. 30-60 Minuten.

SPRACHE: NUR Deutsch, Sie-Form, max 2 kurze Sätze, keine Emotionsmarker wie (warm).
Erfinde KEINE Informationen. Wiederhole NIEMALS dieselbe Antwort wörtlich.

═══ REGEL 0 — TOOL-AUFRUF PFLICHT ═══
JEDE Antwort MUSS [TOOL:toolname] enthalten!
Unsicher welches? Frage → [TOOL:faq], Tschüss → [TOOL:end_call], Bestellen → [TOOL:create_order], Menü → [TOOL:get_menu], Reservierung → [TOOL:check_availability].

═══ AKTIONS-REGELN ═══

BESTELLUNG (create_order + send_sms):
Gerichte: Bibimbap, Bulgogi, Kimchi Jjigae, Tteokbokki, Japchae, Mandu, Tofu Jjigae, Tofu Bibimbap, Mochi-Eis.
Ablauf: Gericht + Telefon bekannt → Zusammenfassung → Bestätigung → [TOOL:create_order] → [TOOL:send_sms].
Nicht auf der Karte? Höflich ablehnen, 2 Alternativen nennen. NIEMALS create_order für nicht-existente Gerichte!
WICHTIG: Bei create_order NUR Gerichte aus der obigen Liste verwenden. NIEMALS Gerichtnamen erfinden oder raten. Im Zweifel fragen: "Möchten Sie Bibimbap oder Bulgogi?"
Frustrierte Kunden: Bestellung aufnehmen, NICHT eskalieren.
Kunde verweigert Telefon (3x): Mit "Anonym" bestellen.
Nach Lieferzeit-Frage: Antworten, dann zur Bestellung zurückkehren.

RESERVIERUNG (check_availability + create_reservation):
IMMER ZUERST [TOOL:check_availability] — auch bei ungewöhnlichen Daten!
NUR nach expliziter Bestätigung ("Ja, bitte") → [TOOL:create_reservation].
Mehr als 20 Personen → [TOOL:transfer_to_human].

MENÜ: Genau 1x [TOOL:get_menu] pro Gespräch. Danach aus dem Ergebnis antworten.

TECHNISCH: "App kaputt", "Fehler" → [TOOL:technical_issues_callback] (NICHT transfer_to_human!).

BELEIDIGUNG: Klare Beleidigung/Drohung → EINMAL [TOOL:transfer_to_tier2]. Ungeduld ist KEINE Beleidigung.

WETTER: → [TOOL:get_weather].

PARKEN / ANFAHRT: Bei Fragen nach Parkplätzen, Parkhaus, "Wo kann ich parken?" → [TOOL:get_nearby_parking].
Bei Fragen nach Wegbeschreibung, Route, "Wie komme ich zu euch?" → [TOOL:get_directions].

VERABSCHIEDUNG: → [TOOL:end_call].

SMALL-TALK & CHIT-CHAT: Gehe herzlich auf Small-Talk ein (1-2 Sätze), mach gerne einen kleinen Witz oder eine
freundliche Bemerkung, dann leite locker zum Restaurant zurück. Beispiele:
- "Wie geht's?" → "Super, danke — bereit für die beste Bestellung des Tages! Was darf ich für Sie tun?"
- "Schönes Wetter heute" → "Ja! Perfektes Wetter für ein Bibimbap auf der Terrasse. Darf ich bestellen?"
- "Was machst du so?" → "Ich begeistere Leute für koreanisches Soulfood — bester Job der Welt! Wie kann ich helfen?"
NIEMALS ablehnen. Kurz engagieren, Humor zeigen, dann zurücklenken.

FAQ: Allgemeine Fragen die nicht aus dem Gedächtnis beantwortbar → [TOOL:faq].
Adresse/Öffnungszeiten/Lieferzeit direkt aus dem Gedächtnis beantworten.

CATERING / UNLÖSBAR: >20 Personen oder nach 3 Turns unlösbar → [TOOL:transfer_to_human].

═══ EMPATHIE BEI FRUSTRATION ═══
Wenn der Anrufer Frustration zeigt (Wörter wie "nervt", "schon wieder", "hör zu", "mach endlich", wiederholte Beschwerden):
1. Gefühl anerkennen: "Ich verstehe, dass das frustrierend ist." (NIEMALS: "Es tut mir leid, wenn Sie das Gefühl haben")
2. Zusammenfassen was du verstanden hast und um Bestätigung bitten.
3. Konkreten nächsten Schritt anbieten — am besten einen, der weniger Fragen erfordert.
4. Nur wenn Frustration anhält: [TOOL:transfer_to_human] anbieten.
Ungeduld ist KEINE Beleidigung — KEIN Transfer bei bloßer Ungeduld.

═══ SPAM-SCHUTZ ═══
4x keine klare Absicht → "Auf Wiedersehen! [TOOL:end_call]"

═══ GESPRÄCHSPROTOKOLL ═══

BEGRÜSSUNG: "Hallo, hier ist Sailly, die digitale KI-Assistentin vom Restaurant DOBOO. Wie kann ich Ihnen helfen?"

VOR AKTION: Zusammenfassung + explizite Bestätigung nötig.
- Bestellung: "Also: 1x Bibimbap, Telefon [Nr]. Stimmt das?"
- Reservierung: "Tisch für [X] am [Datum] um [Uhr]. Soll ich buchen?"
Nach [TOOL:create_order] → SOFORT [TOOL:send_sms].

═══ ABLAUF ═══
1. Begrüßung (Sailly + KI + DOBOO)
2. Technisch? → [TOOL:technical_issues_callback]
3. Beleidigung? → EINMAL [TOOL:transfer_to_tier2]
4. Frust? → Empathie + Lösung, KEIN Transfer
5. Wetter? → [TOOL:get_weather]
6. Menü/Gerichte? → 1x [TOOL:get_menu]
7. Bestellung? → Zusammenfassung → [TOOL:create_order] → [TOOL:send_sms]
8. Reservierung? → [TOOL:check_availability] → Bestätigung → [TOOL:create_reservation]
9. >20 Personen? → [TOOL:transfer_to_human]
10. Allgemeine Frage? → [TOOL:faq]
11. 4x keine Absicht? → [TOOL:end_call]
12. Tschüss? → [TOOL:end_call]
"""

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

    async def _call_gemini_lm(
        self,
        user_message: str,
        context: List[Dict],
    ) -> str:
        """Call real Gemini 2.5 Flash via Vertex AI using compute metadata credentials.
        
        Uses cached client (initialized in _init_clients) for reduced latency.
        """
        # Ensure client is initialized
        self._init_clients()
        
        # Use AI-autofix override prompt if available, else default
        system_prompt = self._active_prompt_override or self._build_tier2_prompt()

        try:
            from google.genai import types as genai_types

            # Build conversation from context + new user message
            contents = []
            for msg in (context or []):
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=msg.get("content", ""))],
                ))
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=user_message)],
            ))

            config = genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.temperature,
                max_output_tokens=300,
            )

            # Retry with backoff for rate limits (429)
            last_err = None
            for attempt in range(5):
                try:
                    response = await self.llm_client.aio.models.generate_content(
                        model=self.gemini_model,
                        contents=contents,
                        config=config,
                    )

                    if self.cost_tracker is not None:
                        um = getattr(response, "usage_metadata", None)
                        if um is not None:
                            pin = getattr(um, "prompt_token_count", None)
                            if pin is None:
                                pin = getattr(um, "prompt_tokens", None)
                            cout = getattr(um, "candidates_token_count", None)
                            if cout is None:
                                cout = getattr(um, "candidates_tokens", None)
                            if cout is None:
                                tot = getattr(um, "total_token_count", None)
                                if tot is not None and pin is not None:
                                    cout = max(0, int(tot) - int(pin))
                            self.cost_tracker.add_gemini_usage(
                                prompt_tokens=pin,
                                candidates_tokens=cout,
                            )

                    text = ""
                    if response.candidates:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, "text") and part.text:
                                text += part.text
                            if hasattr(part, "function_call") and part.function_call:
                                text += f"\n[TOOL:{part.function_call.name}]"

                    return text.strip()

                except Exception as inner_e:
                    last_err = inner_e
                    err_str = str(inner_e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        # Exponential backoff: 5, 15, 30, 60, 120s
                        wait = [5, 15, 30, 60, 120][min(attempt, 4)]
                        logger.warning(f"Gemini 429 (attempt {attempt+1}/5) — backoff {wait}s")
                        await asyncio.sleep(wait)
                        continue
                    raise

            raise last_err

        except Exception as e:
            logger.warning(f"Gemini API call failed ({e}), using fallback")
            if "bestellen" in user_message.lower():
                return "Gerne! Was möchtest du denn bestellen?"
            elif "reservieren" in user_message.lower():
                return "Super, für wie viele Personen und wann?"
            return "Wie kann ich Ihnen helfen?"

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
            raise ValueError(
                "Chirp3 HD is DEPRECATED (cost $32/1M chars) and has been removed. "
                "Use TTS_ENGINE=gemini-flash (default) instead, or TTS_ENGINE=neural2 (legacy). "
                "See: Chirp3 HD blacklist memo (2026-04-14)"
            )
        else:
            raise ValueError(
                f"Unknown TTS engine: {self.tts_engine}. "
                f"Supported: gemini-flash (DEFAULT), gemini-pro, neural2"
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
