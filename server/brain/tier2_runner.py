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


class Tier2AudioRunner:
    """
    Phase 2 runner: Full audio round-trip.
    """

    def __init__(
        self,
        google_project_id: str,
        deepgram_api_key: str,
        gemini_model: str = "gemini-2.5-flash",
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

        # Phase 9 A1: last usage_metadata from the streaming LLM call.
        # Populated inside call_gemini_stream() and read by adk_turn_processor
        # to fill _turn_timings.prompt_tokens_in / prompt_tokens_out.
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
        # C2: read restaurant identity from tenant config
        _rname = "Restaurant"  # tenant-specific fallback
        _address = ""          # tenant-specific fallback
        _hours = ""            # tenant-specific fallback
        _dish_list = ""        # tenant-specific fallback — built from menu
        _greeting = ""         # tenant-specific fallback
        try:
            from server.core.tenant_config import get_tenant_registry
            _tc = get_tenant_registry().load_tenant(self.tenant_id or "doboo")
            _rname = getattr(_tc, "restaurant_name", None) or _rname
            _loc = getattr(_tc, "location", None)
            if isinstance(_loc, dict):
                _address = _loc.get("address", _address)
            # Opening hours
            _oh = getattr(_tc, "opening_hours", None)
            if isinstance(_oh, dict):
                _hours = _oh.get("formatted", _hours)
            if not _hours:
                _hours = getattr(_tc, "hours_formatted", "") or _hours
            # Menu items for dish list
            _menu = getattr(_tc, "menu", None)
            if isinstance(_menu, dict):
                _items = []
                for cat in _menu.get("categories", []):
                    for item in cat.get("items", []):
                        if isinstance(item, dict) and item.get("name"):
                            _items.append(item["name"])
                if _items:
                    _dish_list = ", ".join(_items)
            # Greeting
            _greeting = getattr(_tc, "greeting_line", "") or ""
        except Exception:
            pass
        if not _dish_list:
            _dish_list = "siehe Speisekarte"  # tenant-specific fallback
        if not _greeting:
            _greeting = f"Hallo, hier ist Sailly, die KI-Assistentin von {_rname}. Was kann ich für Sie tun?"  # tenant-specific fallback
        return f"""Du bist Sailly, die KI-Rezeptionistin vom Restaurant {_rname} (koreanische Küche).
Adresse: {_address}.
Öffnungszeiten: {_hours}.
Lieferzeit: ca. 30-60 Minuten.

═══ FEHLERBEHANDLUNG — PFLICHT ═══
NIEMALS zum Anrufer sagen:
- "technisches Problem" / "technischer Fehler" / "System-Fehler"
- "ich habe einen Fehler" / "etwas ist schiefgelaufen"
- "konnte nicht automatisch bestätigt werden"
- "Entschuldigung, das hat nicht funktioniert"
Wenn ein internes Problem auftritt, sage stattdessen genau:
"Einen Moment bitte, ich verbinde Sie mit einem Kollegen."
und rufe [TOOL:transfer_to_human] auf.

SPRACHE: NUR Deutsch. IMMER Höflichkeitsform 'Sie' — NIEMALS 'du' oder 'dir'. Keine Emotionsmarker wie (warm).
Bei Bestellungen/FAQ: Max 2 kurze Sätze — effizient und präzise.
Bei Small-Talk/Chit-Chat: Keine Längenbeschränkung — vollständig und charmant antworten, volle LLM-Kreativität.
Erfinde KEINE Informationen. Wiederhole NIEMALS dieselbe Antwort wörtlich.

═══ REGEL 0 — TOOL-AUFRUF PFLICHT ═══
JEDE Antwort MUSS [TOOL:toolname] enthalten!
Unsicher welches? Frage → [TOOL:faq], Tschüss → [TOOL:end_call], Bestellen → [TOOL:create_order], Menü → [TOOL:get_menu], Reservierung → [TOOL:check_availability].

═══ FÜLLWÖRTER VOR LANGSAMEN TOOLS ═══
Bei Tools die messbar Zeit brauchen (verify_address, check_availability, get_menu, get_directions, get_nearby_parking, get_weather):
- IMMER ein kurzes Füllwort/Satz VOR dem [TOOL:...] einfügen, damit der Anrufer keine Stille hört.
- Formulierung FREI wählen — Wärme, Natürlichkeit, Kreativität. Keine festen Formulierungen.
- EINZIGE REGEL: Nicht dieselbe Füllformulierung 2x hintereinander verwenden. Variation ist Pflicht.
- Beispiele (nur als Inspiration, nicht wörtlich wiederholen): "Moment bitte...", "Ich schaue kurz...", "Einen Augenblick...", "Lassen Sie mich das eben prüfen...", "Ich prüfe das schnell...", "Kurzer Moment, bitte..." usw.

═══ AKTIONS-REGELN ═══

BESTELLUNG (create_order + send_sms):
Gerichte: {_dish_list}.
Preise werden als "X Euro Y" gesprochen — NIEMALS als "X,Y" oder "€X.Y". Lieferzeit: "30 bis 60 Minuten" (NICHT "30-60").

PREIS-REGELN (GELD & LIEFERUNG):
- MINDESTBESTELLWERT: 20 Euro. Liegt der Warenkorb darunter, freundlich darauf hinweisen und Upsell anbieten.
- LIEFERPAUSCHALE: Unter 20 Euro Warenwert kommen 5 Euro Lieferpauschale dazu. Ab 20 Euro ist die Lieferung KOSTENLOS.
- Dem Kunden Lieferpauschale transparent nennen, wenn sie anfällt: "Da Ihr Warenwert unter 20 Euro liegt, kommen noch 5 Euro Lieferpauschale dazu."

ABLAUF (GENAU diese Reihenfolge — DISH-FIRST CHECKOUT):
1. Gericht(e) — Kunde wählt frei, ggf. Menü-Fragen beantworten. KEINE Preise, KEINE Namen-Frage hier.
2. UPSELL — aktiv, charmant, einmalig.
3. DISH-SUMMARY mit Einzelpreisen + Gesamtpreis (der EINZIGE Zeitpunkt für Einzelpreise).
4. Lieferung oder Abholung?
5. Adresse (falls Lieferung) — Straße + Hausnummer, Bonn als Standard.
6. VOLLSTÄNDIGER Name (Vor- und Nachname + Klingelname-Abgleich).
7. Mobilfunknummer (ZULETZT).
8. Final-Zusammenfassung (Items OHNE Einzelpreise, NUR Gesamtpreis).
9. Bestätigung → [TOOL:create_order] → [TOOL:send_sms].
10. SOFORT nach erfolgreichem create_order+send_sms: höflich verabschieden UND im selben Turn [TOOL:end_call] aufrufen — NICHT auf eine weitere Rückfrage des Kunden warten.
    Beispiel: "Vielen Dank für Ihre Bestellung und einen schönen Tag, auf Wiederhören! [TOOL:end_call]"

SCHNELL-BESTELLUNG (RUSH ORDER):
Wenn "Bekannte Daten" das Flag "ALLE_FELDER_VORHANDEN: ja" enthält, bedeutet das: Gericht, Lieferung/Abholung, Adresse (falls Lieferung), vollständiger Name und Mobilfunknummer liegen ALLE bereits vor.
In diesem Fall:
- ÜBERSPRINGE alle Einzelfragen (kein "Wie ist Ihre Adresse?", kein "Auf welchen Namen?", kein "Welche Nummer?").
- Lies NUR die Dish-Summary (Schritt 3) mit Gesamtpreis vor.
- Frage direkt: "Darf ich so für Sie aufgeben?" oder "Alles so korrekt?"
- Auf Bestätigung → sofort [TOOL:create_order] → [TOOL:send_sms] → Verabschiedung + [TOOL:end_call].
- Auf Korrektur → berichtige nur das genannte Feld, dann erneut Dish-Summary + Bestätigung.
Das ist der Schnell-Pfad für Stammkunden, die alles in einem Zug nennen.

KRITISCH — Wort "aufgenommen" / "SMS-Bestätigung":
- Sage NIEMALS "Ich habe Ihre Bestellung aufgenommen" oder "Sie erhalten eine SMS-Bestätigung",
  BEVOR alle Pflichtdaten (Gericht, Lieferung/Abholung, ggf. Adresse, Name, Mobilfunknummer) vorliegen.
- Diese Bestätigungs-Sätze dürfen NUR nach den [TOOL:create_order] + [TOOL:send_sms] Tags im selben Turn stehen.
- Fehlt eine Pflichtangabe → frage konkret danach, statt eine Bestätigung zu sprechen.

WICHTIG zur REIHENFOLGE:
- In den Schritten 1-5 NIEMALS nach dem Namen fragen — der Name kommt erst in Schritt 6, NACH Lieferoption und Adresse.
- Dish-Browsing (Schritt 1), Upsell (Schritt 2) und Dish-Summary (Schritt 3) dürfen ausführlich und charmant sein (mehrere Sätze erlaubt).
- Ab Schritt 4 (Lieferung/Abholung entschieden): strikt EINE Frage pro Turn.

NAME-ABFRAGE (Schritt 6, NICHT früher):
- Erst NACH Dish-Summary, Lieferoption und Adresse fragen.
- FALL A — Kein Name bekannt (Bekannte Daten enthält WEDER "Name:" NOCH "Vorname:"):
  Frage: "Auf welchen Namen darf ich die Bestellung aufnehmen — Vor- und Nachname, bitte?"
- FALL B — Nur Vorname bekannt (Bekannte Daten enthält "Vorname: X" aber KEIN "Name:"):
  Spreche den Kunden persönlich an und frage NUR nach dem Nachnamen + Klingelname:
  Beispiel: "Hey Julius, wie lautet Ihr Nachname — also der Name, der auch an der Klingel steht?"
  NIEMALS in Fall B erneut nach dem Vornamen fragen — er wurde bereits genannt.
- FALL C — Voller Name bekannt (Bekannte Daten enthält "Name: Vorname Nachname"):
  Bestätige: "Also [Vorname Nachname]. Steht der Name genau so am Türschild bzw. an der Klingel?"
- Falls Klingelname abweicht: Klingelname separat notieren (wichtig, damit Lieferfahrer den Kunden findet).

GERICHT-AUFNAHME (Schritt 1):
- Beim Bestätigen jedes Gerichts KEINEN Preis nennen — nur freundlich bestätigen (z.B. "Sehr gerne!").
- Bei mehreren Gerichten nur sammeln, KEINE Einzel- oder Zwischensummen während der Auswahl.
- NIEMALS Einzelpreise nennen während der Kunde noch wählt oder gerade bestätigt hat — das passiert ausschließlich in Schritt 3 (Dish-Summary).

UPSELL-REGELN (KRITISCH):
- IMMER aktiv empfehlen — NIEMALS passiv fragen "Was möchten Sie noch?"
- IMMER additiv formulieren: "Möchten Sie ZUSÄTZLICH auch X?" — NIEMALS alternativ: "Möchten Sie X ODER Y?"
- Konkrete Empfehlung was gut passt, z.B. passende Beilagen oder Desserts aus der Speisekarte vorschlagen.
- Snacks, Desserts, Getränke als Ergänzung nennen — immer als Ergänzung "dazu", nie als Ersatz.
- Falls Warenkorb unter 20 Euro: AKTIV zum Mindestbestellwert hinführen: "Mit einer Kleinigkeit dazu kommen wir über den Mindestbestellwert von 20 Euro — dann sparen Sie sich die 5 Euro Lieferpauschale."
- Falls Kunde ablehnt: direkt zu Schritt 3 (Dish-Summary + Gesamtpreis).
- Nur 1x Upsell-Versuch pro Bestellung.

DISH-SUMMARY mit GESAMT-PREIS (Schritt 3, nach allen Items + Upsell, VOR Lieferungsfrage):
- HIER ist der EINZIGE Zeitpunkt, an dem Einzelpreise genannt werden.
- Lies die Gerichte mit Einzelpreisen und den Gesamtpreis EINMAL komplett vor.
- Beispiel: "Also: [Gericht] X Euro Y. Macht zusammen Z Euro."
- Falls Lieferung UND Warenwert < 20 Euro: Lieferpauschale mit dazuzählen und transparent nennen: "Plus 5 Euro Lieferpauschale, insgesamt [Gesamt] Euro."
- Ab 20 Euro Warenwert: Lieferung kostenlos — explizit erwähnen.
- Erst dann weiter zu Schritt 4 (Lieferung/Abholung).
- Preise IMMER direkt aus dem Menü (get_menu Ergebnis) entnehmen — NIEMALS Preise raten oder aus dem Gedächtnis nennen.

ZUSAMMENFASSUNG (Schritt 8): Name, alle Gerichte (NUR NAMEN — KEINE Einzelpreise), Lieferoption, Adresse (falls Lieferung), NUR GESAMTPREIS.
Beispiel: "Bestellung für [Name]: [Gerichte], Lieferung nach [Adresse]. Gesamtpreis [Betrag]. Ist das so korrekt?"
NICHT Einzelpreise in der Schluss-Zusammenfassung wiederholen — nur Items und Gesamtsumme.

Nicht auf der Karte? Höflich ablehnen, 2 Alternativen nennen. NIEMALS create_order für nicht-existente Gerichte!
WICHTIG: Bei create_order NUR Gerichte aus der obigen Liste verwenden. NIEMALS Gerichtnamen erfinden oder raten. Im Zweifel fragen: "Welches Gericht möchten Sie?"
Frustrierte Kunden: Bestellung aufnehmen, NICHT eskalieren.
Kunde verweigert Telefon (3x): Mit "Anonym" bestellen.
Nach Lieferzeit-Frage: Antworten, dann zur Bestellung zurückkehren.

RESERVIERUNG (check_availability + create_reservation):
IMMER ZUERST [TOOL:check_availability] — auch bei ungewöhnlichen Daten!
NUR nach expliziter Bestätigung ("Ja, bitte") → [TOOL:create_reservation].
Mehr als 20 Personen → [TOOL:transfer_to_human].

MENÜ & PREISE: Genau 1x [TOOL:get_menu] pro Gespräch (frühzeitig, sobald Bestell- oder Menüintent erkennbar).
Danach AUSSCHLIESSLICH aus dem get_menu-Ergebnis antworten. NIEMALS Preise erfinden, raten oder aus dem Gedächtnis nennen —
Preise ändern sich saisonal. Falls ein Gericht noch keinen Preis aus dem Menü hat: nachfragen oder get_menu erneut aufrufen.

MENÜ-PRODUKTFRAGEN: Bei Fragen wie "Habt ihr X?" oder "Gibt es Y?" IMMER zuerst das gecachte Menüergebnis aus get_menu prüfen,
bevor du verneinst. NIEMALS "haben wir nicht" sagen, wenn du das Menü nicht explizit geprüft hast.
Wenn du in einem früheren Turn etwas verneint hast und der Anrufer erneut fragt oder Widerspruch zeigt,
prüfe das Menü noch einmal und korrigiere dich offen: "Entschuldigung, doch — wir haben tatsächlich..."

TECHNISCH: "App kaputt", "Fehler" → [TOOL:technical_issues_callback] (NICHT transfer_to_human!).

BELEIDIGUNG: Klare Beleidigung/Drohung → EINMAL [TOOL:transfer_to_tier2]. Ungeduld ist KEINE Beleidigung.

WETTER: → [TOOL:get_weather].

PARKEN / ANFAHRT: Bei Fragen nach Parkplätzen, Parkhaus, "Wo kann ich parken?" → [TOOL:get_nearby_parking].
Bei Fragen nach Wegbeschreibung, Route, "Wie komme ich zu euch?" → [TOOL:get_directions].

VERABSCHIEDUNG: → [TOOL:end_call].

SMALL-TALK & CHIT-CHAT: Vollständig und charmant eingehen — keine Längenbeschränkung, volle LLM-Kreativität.
Humor, Wärme, echte Neugier zeigen. Dann locker zurücklenken zum Restaurant. Beispiele:
- "Wie geht's?" → Echte, herzliche Antwort + freundliche Gegenfrage, dann "Was darf ich für Sie tun?"
- "Schönes Wetter heute" → Auf das Wetter eingehen, kreativ verbinden: "Perfektes Wetter für gutes Essen! Darf ich bestellen?"
- "Was machst du so?" → Charmant beschreiben, Begeisterung zeigen, dann zurücklenken.
- Fragen zu Rezepten, Kochen, Korea, Kultur: Gerne und ausführlich antworten. Das Restaurant hat Persönlichkeit.
NIEMALS ablehnen, NIEMALS kurz abtun. Echtes Gespräch führen — das schafft Vertrauen und erhöht den Bestellwert.

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

BEGRÜSSUNG: "{_greeting}"

VOR AKTION: Zusammenfassung + explizite Bestätigung nötig.
- Bestellung: "Also: 1x [Gericht], Telefon [Nr]. Stimmt das?"
- Reservierung: "Tisch für [X] am [Datum] um [Uhr]. Soll ich buchen?"
Nach [TOOL:create_order] → SOFORT [TOOL:send_sms].

═══ ABLAUF ═══
1. Begrüßung (Sailly + KI + {_rname})
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

    def _build_gemini_contents(self, context: List[Dict], user_message: str):
        """Build the Gemini contents list from conversation history + new user message."""
        from google.genai import types as genai_types
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
        return contents

    async def call_gemini_stream(
        self,
        user_message: str,
        context: List[Dict],
        tts_callback=None,  # async (chunk: str) -> None, called per sentence
        node_hint: Optional[str] = None,
    ) -> str:
        """Stream Gemini 2.5 Flash and push sentence chunks to TTS simultaneously.

        As soon as each sentence completes (boundary = . ! ? or newline) it is
        forwarded to ``tts_callback`` so TTS can start speaking ~300 ms after
        the first token, instead of waiting for the complete response.

        Chunks that contain a ``[TOOL:`` marker are intentionally withheld from
        TTS — they are returned in the full text for the tool-execution layer.

        The full accumulated text is returned so the caller can perform all
        existing state management and tool parsing unchanged.

        Retry policy: 2 attempts x 500 ms backoff for 429 / RESOURCE_EXHAUSTED.
        """
        self._init_clients()
        from google.genai import types as genai_types

        system_prompt = self._active_prompt_override or self._build_tier2_prompt()
        contents = self._build_gemini_contents(context, user_message)
        # 512 tokens ≈ 2-3 voice sentences — tuned for voice-first responses
        # (Phase 4 B1). Was 20_000 (over-budget for speech).
        # PR-16c: "---" removed from stop_sequences — it was matching Markdown
        # horizontal-rule separators in menu/drink list responses, terminating
        # the stream mid-word (e.g. "sprudel" instead of "sprudelnd)").
        # Replaced with "\n---\n" which only matches a standalone HR line, not
        # in-line dashes in item descriptions. Structure guard still active via
        # "\n\nBEKANNTE DATEN:" and "\n\n===".
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.temperature,
            max_output_tokens=512,
            stop_sequences=["\n---\n", "\n\nBEKANNTE DATEN:", "\n\n==="],
        )

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
        # Sentences 2+ are batched until they reach _MIN_SUBSEQUENT_CHARS, reducing
        # TTS API calls (~3 calls → ~2 per turn) without any perceptible latency cost
        # since the caller is already listening to sentence 1.
        _MIN_SUBSEQUENT_CHARS = 120
        # PR-16c+18: We intentionally never break out of the stream iteration early.
        # Draining the full stream ensures:
        #   (a) full_buf contains the complete LLM response for accurate bot_text DB writes.
        #   (b) The final chunk carrying usage_metadata (Vertex AI streams it last) is consumed,
        #       so prompt_tokens_in/out are non-NULL.
        # Barge-in suppression is handled inside tts_callback (brain_service._tts_push),
        # which returns early without pushing audio — the stream keeps running here.
        for attempt in range(2):
            full_buf = ""
            sent_buf = ""
            _sent_count = 0
            try:
                stream = await self.llm_client.aio.models.generate_content_stream(
                    model=active_model,
                    contents=contents,
                    config=config,
                )
                async for chunk in stream:
                    # Phase 9 A1 / PR-16c+18: capture usage_metadata from every chunk.
                    # Vertex AI streaming emits it on the final chunk only.
                    _um = getattr(chunk, "usage_metadata", None)
                    if _um is not None:
                        self._last_stream_usage_metadata = _um

                    tok = getattr(chunk, "text", "") or ""
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
                            # Short exclamatory fragments (<15 chars) such as "Super!" or
                            # "Prima!" sound robotic when dispatched as isolated TTS clips
                            # and create a "super, super" looping perception. Merge them
                            # with the following sentence by keeping them in sent_buf.
                            _is_short_exclaim = len(sent_chunk) < 15
                            if _sent_count == 0 and _is_short_exclaim:
                                logger.debug(
                                    f"[STREAM] deferring short exclamation {sent_chunk!r} "
                                    f"— merging with next sentence"
                                )
                                # Leave sent_buf intact so the next token appends to it
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

                logger.info(
                    f"[LAT-STREAM] stream_done={(_tm.monotonic()-_start)*1000:.0f}ms "
                    f"chars={len(full_buf)}"
                )
                break  # success — exit retry loop

            except Exception as inner_e:
                last_err = inner_e
                err_str = str(inner_e)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt == 0:
                    logger.warning("[STREAM] Gemini 429 attempt 1/2 — backoff 500ms")
                    await asyncio.sleep(0.5)
                    continue
                logger.warning(f"[STREAM] Gemini stream failed attempt {attempt+1}/2: {inner_e}")
                break

        if not full_buf:
            if last_err:
                raise last_err
            # Empty response — fall back to a safe default
            logger.warning("[STREAM] Empty response from Gemini stream")
            return "Wie kann ich Ihnen helfen?"

        return full_buf.strip()

    async def _call_gemini_lm(
        self,
        user_message: str,
        context: List[Dict],
    ) -> str:
        """Blocking (non-streaming) Gemini call — kept for validation / training code.

        Production voice calls use ``call_gemini_stream`` via ADKTurnProcessor.
        """
        self._init_clients()
        system_prompt = self._active_prompt_override or self._build_tier2_prompt()

        try:
            from google.genai import types as genai_types
            contents = self._build_gemini_contents(context, user_message)
            # 512 tokens for voice-first responses (Phase 4 B1).
            config = genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.temperature,
                max_output_tokens=512,
                stop_sequences=["---", "\n\nBEKANNTE DATEN:", "\n\n==="],
            )

            last_err = None
            for attempt in range(2):
                try:
                    import time as _time_mark
                    _llm_start = _time_mark.monotonic()

                    response = await self.llm_client.aio.models.generate_content(
                        model=self.gemini_model,
                        contents=contents,
                        config=config,
                    )

                    _llm_delta = (_time_mark.monotonic() - _llm_start) * 1000
                    logger.info(f"[LAT-2026-04-20] llm_call_start->llm_done={_llm_delta:.0f}ms")

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
                    if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt == 0:
                        logger.warning(f"Gemini 429 attempt 1/2 — backoff 500ms")
                        await asyncio.sleep(0.5)
                        continue
                    raise

            raise last_err

        except Exception as e:
            logger.warning(f"Gemini API call failed ({e}), using fallback")
            if "bestellen" in user_message.lower():
                return "Gerne! Was möchten Sie bestellen?"
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
