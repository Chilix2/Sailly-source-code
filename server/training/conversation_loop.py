"""
ConversationLoop — Drives realistic multi-turn audio conversations.

Flow per turn:
  1. Caller (GPT-4o-mini) generates next German utterance based on scenario goal + bot history
  2. Google Wavenet-F TTS synthesizes caller audio (Linear16 8kHz)
  3. Deepgram Nova-3 DE STT transcribes caller audio
  4. WER gate validates transcript quality
  5. Gemini 2.5 Flash LLM generates bot response (with tool calling)
  6. Gemini Flash TTS synthesizes bot response audio (configurable via TTS_ENGINE)
  7. Loop until: end_call tool called | max_turns reached | natural goodbye detected

First turn is always the scripted scenario opener (not GPT-generated).
GPT-4o-mini generates all subsequent turns, adapting to bot responses.
GPT persona matches scenario difficulty: rude, impatient, off-topic, dialect, etc.
"""

import asyncio
import logging
import re
import time
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from server.training.conversation_state import (
    ConversationState,
    update_state_from_utterance,
    update_state_after_bot,
)
from server.training.response_variations import (
    VariationRotator,
    apply_response_variations,
)

logger = logging.getLogger(__name__)

MAX_TURNS   = 28   # Demo Training Loop global cap (was 35)
# Soft minimum — effective_min in adk_runner drops to 2 after booking/reservation completes.
# Min 6 keeps conversations realistic without forcing turns unnecessarily.
MIN_TURNS_BY_PHASE = {1: 6, 2: 6, 3: 6, 4: 6}
# No per-phase cap — MAX_TURNS (28) applies globally.
MAX_TURNS_BY_PHASE: dict = {}
END_PHRASES = [
    "auf wiederhören", "auf wiedersehen", "wiedersehen",
    "tschüss", "tschüs", "goodbye", "bye", "danke tschüss",
    "wiederhören", "ciao", "mach's gut", "danke auf wiedersehen",
    # Post-order acknowledgements that signal the call is wrapping up
    "alles klar, danke", "alles klar danke", "alles gut, danke",
    "super, danke", "super danke", "prima, danke", "prima danke",
    "okay, danke", "ok, danke", "danke, tschüss", "danke schön",
]

# GPT-4o-mini caller personas by scenario category
# Each persona is a dict with name, situation, and optionally mood
PERSONAS = {
    "greeting": {
        "name": "Anna",
        "situation": "Du rufst zum ersten Mal beim Restaurant an. Du bist freundlich und neugierig.",
    },
    "faq": {
        "name": "Lisa",
        "situation": "Du bist zum ersten Mal bei DOBOO und moechtest dich erstmal informieren bevor du bestellst.",
    },
    "handoff": {
        "name": "Peter",
        "situation": "Du moechtest bestellen aber du bist dir nicht sicher ob das telefonisch geht.",
    },
    "reservation": {
        "name": "Sarah",
        "situation": "Du planst ein Abendessen mit Freunden. Du hast schon ein Datum im Kopf.",
    },
    "order": {
        "name": "Thomas",
        "situation": "Du kommst von der Arbeit und hast Hunger. Du kennst koreanisches Essen aber nicht die Karte auswendig.",
    },
    "tool_edge_case": {
        "name": "Michael",
        "situation": "Du bist ein normaler Kunde. Du weisst was du willst und bist direkt.",
    },
    "instruction": {
        "name": "Klaus",
        "situation": "Du hast wenig Zeit und bist etwas gestresst. Du willst schnell bestellen.",
    },
    "adversarial": {
        "name": "Markus",
        "situation": "Du bist skeptisch gegenueber KI-Systemen. Du findest es merkwuerdig mit einem Bot zu reden.",
    },
    "switch": {
        "name": "Julia",
        "situation": "Du bist unentschlossen. Du wechselst zwischen Bestellung und Fragen hin und her.",
    },
    "default": {
        "name": "Martin",
        "situation": "Du rufst beim Restaurant DOBOO an. Du bist ein normaler, hoeflicher Kunde.",
    },
}


@dataclass
class ConvTurn:
    turn_idx:        int
    caller_text:     str        # GPT-generated or scripted
    stt_transcript:  str        # What Deepgram heard
    wer:             float
    bot_response:    str        # Gemini LLM text
    tts_bytes:       int        # Chirp3 audio bytes
    tools_called:    List[str]
    caller_latency_ms: float   # TTS + STT
    bot_latency_ms:    float   # LLM + Chirp3
    total_latency_ms:  float
    passed:          bool
    error:           Optional[str] = None


@dataclass
class ConvResult:
    scenario_id:    str
    phase:          int
    run_number:     int
    turns:          List[ConvTurn]
    tools_called:   List[str]
    expected_tools: List[str]
    total_latency_ms: float
    total_audio_bytes: int
    passed:         bool
    end_reason:     str = ""    # "end_call_tool" | "max_turns" | "goodbye" | "error"
    error:          Optional[str] = None


class ConversationLoop:
    """
    Drives a full multi-turn conversation between GPT-4o-mini (caller) and
    Gemini 2.5 Flash (bot) with real audio: TTS → Deepgram STT → LLM → Chirp3.
    """

    def __init__(
        self,
        audio_injector,        # AudioInjector instance
        gemini_runner,         # Tier2AudioRunner instance (provides _call_gemini_lm + _synthesize_response)
        openai_api_key: str,
        max_turns: int = MAX_TURNS,
        stt_threshold: float = 0.80,
        cost_tracker: Optional["CostTracker"] = None,
    ):
        self.audio_injector    = audio_injector
        self.gemini_runner     = gemini_runner
        self.openai_key        = openai_api_key
        self.max_turns         = max_turns
        self.stt_threshold     = stt_threshold
        self.cost_tracker      = cost_tracker
        self._openai_client    = None
        self._variation_rotator = VariationRotator()

    def _get_openai(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=self.openai_key)
        return self._openai_client

    # Persona-type behavioral modifiers injected into the GPT caller system prompt.
    _PERSONA_BEHAVIORS = {
        "angry": (
            "Du bist frustriert und ungeduldig. "
            "Du klingst gereizt, beschwerst dich leicht und zeigst Unzufriedenheit. "
            "Deine Saetze sind kurz und direkt, manchmal unhoeflicherweise."
        ),
        "impatient": (
            "Du hast wenig Zeit und bist ungeduldiger Anrufer. "
            "Du willst schnelle Antworten, unterbrichst gelegentlich, "
            "und wirst ungeduldig bei langen Erklaerungen."
        ),
        "sleepy": (
            "Du bist muede und schlaefrig. Deine Saetze sind langsam, "
            "oft unvollstaendig, manchmal laesst du Woerter weg oder pausierst lange."
        ),
        "accent": (
            "Du sprichst Deutsch mit starkem nicht-deutschen Akzent. "
            "Manchmal verwendest du englische Woerter oder Phrasen versehentlich. "
            "Deine Grammatik ist gelegentlich fehlerhaft."
        ),
        "hard_to_hear": (
            "Du sprichst leise und undeutlich. Es gibt Hintergrundgeraeusche um dich herum. "
            "Deine Saetze sind manchmal abgeschnitten oder zu leise."
        ),
        "chaos": (
            "Du bist sehr unentschlossen und springst zwischen Themen hin und her. "
            "Du aenderst mindestens 2-3 Mal deine Meinung waehrend des Gespraechs. "
            "Du kannst mitten in einem Thema zu einem anderen wechseln."
        ),
        "elderly": (
            "Du bist aelterer Anrufer und sprichst langsam. "
            "Du wiederholst Informationen manchmal, brauchst Bestaetigung, "
            "und verwechselst gelegentlich Details."
        ),
        "neutral": "",  # No modifier needed
    }

    def _persona(self, scenario) -> dict:
        """Get persona dict (name, situation) for the caller.

        Priority: scenario.persona field > scenario.category match > default.
        """
        # Named persona from scenario.persona field (from generated scenarios)
        persona_key = getattr(scenario, "persona", None)
        if persona_key and persona_key in self._PERSONA_BEHAVIORS:
            persona_names = {
                "angry": "Markus", "impatient": "Klaus", "sleepy": "Werner",
                "accent": "Bogdan", "hard_to_hear": "Gerda", "chaos": "Julia",
                "elderly": "Hannelore", "neutral": "Martin",
            }
            name = persona_names.get(persona_key, "Martin")
            desc = getattr(scenario, "description", scenario.id)
            return {"name": name, "situation": f"Du rufst beim Restaurant DOBOO an. {desc}"}

        # Fallback: match by category keyword
        cat = getattr(scenario, "category", "default").lower()
        for key in PERSONAS:
            if key in cat:
                return PERSONAS[key]
        return PERSONAS["default"]

    def _ensure_tool_call(self, bot_response: str, customer_utterance: str, turn_idx: int) -> str:
        """
        Fallback: if Gemini forgot to include a [TOOL:...] tag, inject the most appropriate one.

        This is Layer 2 of the force-tool-calling fix. REGEL 0 in the prompt tries to force it,
        but as a safety net, we check the response and inject if missing.

        Args:
            bot_response: The text response from Gemini
            customer_utterance: The customer's input for context
            turn_idx: Turn number for logging

        Returns:
            bot_response with [TOOL:...] injected if it was missing
        """
        # Check if response already has a tool tag
        tool_pattern = re.compile(r"\[TOOL:\w+\]")
        if tool_pattern.search(bot_response):
            return bot_response  # Already has a tool — pass through

        # No tool tag found — inject based on customer utterance context
        lower_utt = customer_utterance.lower()

        # Goodbye / farewell keywords
        if any(kw in lower_utt for kw in ["tschüss", "auf wiedersehen", "auf wiederhören", "bye", "danke das war", "danke tschüss", "ciao", "wiedersehen"]):
            logger.debug(f"  T{turn_idx}: Injecting [TOOL:end_call] (farewell detected)")
            return bot_response + "\n[TOOL:end_call]"

        # Order / purchase intent
        if any(kw in lower_utt for kw in ["bestellen", "bestellung", "ich nehme", "ich hätte gerne", "zum mitnehmen", "lieferung"]):
            logger.debug(f"  T{turn_idx}: Injecting [TOOL:create_order] (order intent detected)")
            return bot_response + "\n[TOOL:create_order]"

        # Menu / dishes question
        if any(kw in lower_utt for kw in ["menü", "karte", "speisekarte", "was habt ihr", "gerichte", "allergie", "vegetarisch", "fisch", "fleisch"]):
            logger.debug(f"  T{turn_idx}: Injecting [TOOL:get_menu] (menu question detected)")
            return bot_response + "\n[TOOL:get_menu]"

        # Reservation intent
        if any(kw in lower_utt for kw in ["reservier", "tisch für", "buchen", "reservation", "tisch"]):
            logger.debug(f"  T{turn_idx}: Injecting [TOOL:check_availability] (reservation intent detected)")
            return bot_response + "\n[TOOL:check_availability]"

        # Weather question
        if any(kw in lower_utt for kw in ["wetter", "wie ist das wetter", "regnet", "schneit", "sonnig"]):
            logger.debug(f"  T{turn_idx}: Injecting [TOOL:get_weather] (weather question detected)")
            return bot_response + "\n[TOOL:get_weather]"

        # Fallback: generic FAQ for any other question
        logger.debug(f"  T{turn_idx}: Injecting [TOOL:faq] (fallback for general question)")
        return bot_response + "\n[TOOL:faq]"

    async def _plan_full_conversation(
        self,
        scenario,
        num_scripted: int,
    ) -> List[str]:
        """
        Pre-plan ALL caller turns for a complete call in a single GPT call.

        Returns a list of caller utterances covering the full call arc:
        intent → clarifications → all required info → confirmation → goodbye.
        These are used as pre-planned turns; reactive generation is the fallback.
        """
        persona_dict = self._persona(scenario)
        persona_name = persona_dict.get("name", "Martin")
        persona_situation = persona_dict.get("situation", "Du rufst beim Restaurant DOBOO an.")
        desc = getattr(scenario, "description", scenario.id)
        expected_tools = getattr(scenario, "expected_tools", []) or []

        # Build arc hints based on expected tools
        arc_parts = []
        if "create_order" in expected_tools:
            arc_parts.append(
                "BESTELLABLAUF: Gericht nennen → Lieferung oder Abholung? → "
                "Lieferadresse (falls Lieferung) → Name → Mobilnummer → Bestellung bestätigen"
            )
        if "create_reservation" in expected_tools:
            arc_parts.append(
                "RESERVIERUNGSABLAUF: Datum/Uhrzeit nennen → Personenanzahl → "
                "Name → Telefonnummer → Reservierung bestätigen"
            )
        if "get_menu" in expected_tools and "create_order" not in expected_tools:
            arc_parts.append("MENÜANFRAGE: Nach Gerichten fragen → ggf. Empfehlung erfragen")
        if "faq" in expected_tools:
            arc_parts.append("FAQ: Informationsfrage stellen → Antwort empfangen → ggf. Nachfrage")
        if "get_weather" in expected_tools:
            arc_parts.append("WETTER: Wetteranfrage stellen → Antwort empfangen")
        if "transfer_to_tier2" in expected_tools:
            arc_parts.append("ESKALATION: Unzufriedenheit äußern → Weitervermittlung anfordern")
        if not arc_parts:
            arc_parts.append("ALLGEMEIN: Anliegen nennen → Informationen austauschen → verabschieden")

        arc_text = "\n".join(arc_parts)

        # Build required data hints so the planner includes realistic details
        data_hints = []
        if "create_order" in expected_tools or "create_reservation" in expected_tools:
            data_hints += [
                "Telefonnummer: eine echte deutsche Mobilnummer (z.B. 0176 55512345)",
                "Name: ein normaler deutscher Nachname (z.B. Müller, Schmidt, Weber)",
            ]
        if "create_order" in expected_tools:
            data_hints += [
                "Gericht: ein koreanisches Gericht aus der DOBOO-Karte "
                "(Bibimbap, Bulgogi, Kimchi Jjigae, Japchae, Tteokbokki)",
                "Lieferung oder Abholung: entscheide dich für eine Option",
                "Lieferadresse (nur bei Lieferung): Straße + Hausnummer in Bonn",
            ]
        if "create_reservation" in expected_tools:
            data_hints += [
                "Datum: ein konkretes Datum (z.B. Samstag Abend, morgen um 19 Uhr)",
                "Personenzahl: eine realistische Zahl (2-6 Personen)",
            ]
        data_block = (
            "\nBENÖTIGTE DATEN FÜR DIESEN ANRUF:\n" + "\n".join(f"- {d}" for d in data_hints)
            if data_hints
            else ""
        )

        system = (
            f"Du planst einen vollständigen Telefonanruf als Kunde beim Restaurant DOBOO in Bonn.\n"
            f"Name: {persona_name}\n"
            f"Situation: {persona_situation}\n"
            f"Anliegen: {desc}\n"
            f"{data_block}\n"
            f"\n"
            f"GESPRÄCHSABLAUF DEN DU VOLLSTÄNDIG ABDECKEN MUSST:\n"
            f"{arc_text}\n"
            f"\n"
            f"REGELN:\n"
            f"- Generiere 6-12 Anrufer-Turns die den KOMPLETTEN Anruf von Anfang bis Ende abdecken\n"
            f"- Jeder Turn: 1-3 natürliche Sätze wie ein echter Mensch am Telefon\n"
            f"- Der Anrufer LIEFERT proaktiv alle benötigten Informationen (nicht warten bis gefragt)\n"
            f"- Das letzte Turn MUSS eine echte Verabschiedung sein (Tschüss, Auf Wiederhören, etc.)\n"
            f"- Antworte NUR als JSON-Objekt: {{\"turns\": [\"turn1\", \"turn2\", ...]}}\n"
            f"- Die ersten {num_scripted} Turns sind bereits vorgegeben — generiere NUR die FOLGENDEN Turns\n"
        )

        try:
            client = self._get_openai()
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": (
                            f"Erstelle den vollständigen Gesprächsplan für: {desc}\n"
                            f"Antworte NUR mit dem JSON-Objekt {{\"turns\": [...]}}."
                        ),
                    },
                ],
                max_tokens=700,
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            if self.cost_tracker is not None and getattr(resp, "usage", None):
                u = resp.usage
                self.cost_tracker.add_openai_usage(
                    int(getattr(u, "prompt_tokens", 0) or 0),
                    int(getattr(u, "completion_tokens", 0) or 0),
                )
            import json as _json
            data = _json.loads(resp.choices[0].message.content)
            planned: List[str] = data.get("turns", [])
            # Sanitise: strip surrounding quotes GPT sometimes adds
            planned = [
                t[1:-1] if (t.startswith('"') and t.endswith('"')) else t
                for t in planned
                if isinstance(t, str) and t.strip()
            ]
            logger.info(
                f"[ConvLoop] Pre-planned {len(planned)} caller turns for '{scenario.id}'"
            )
            return planned
        except Exception as e:
            logger.warning(f"[ConvLoop] Full-conversation planning failed: {e} — will use reactive generation")
            return []

    async def _generate_caller_turn(
        self,
        scenario,
        history: List[Dict],
        turn_idx: int,
        min_turns: int = 0,
    ) -> str:
        """
        Generate the next caller utterance reactively using GPT-4o-mini.
        Used as fallback when pre-planned turns are exhausted.
        """
        persona_dict = self._persona(scenario)
        persona_name = persona_dict.get("name", "Martin")
        persona_situation = persona_dict.get("situation", "Du rufst beim Restaurant DOBOO an.")
        desc = getattr(scenario, "description", scenario.id)
        expected_tools = getattr(scenario, "expected_tools", []) or []

        # Inject persona-specific behavior from scenario.persona field
        persona_key = getattr(scenario, "persona", None) or ""
        persona_behavior = self._PERSONA_BEHAVIORS.get(persona_key, "")
        persona_behavior_block = (
            f"\nPERSONA-VERHALTEN ({persona_key}):\n{persona_behavior}\n"
            if persona_behavior
            else ""
        )

        # Build remaining-goal hint so reactive turns still drive toward completion
        goal_hints = []
        if "create_order" in expected_tools:
            goal_hints.append(
                "Dein Ziel: Bestellung abschliessen (Gericht, Lieferung/Abholung, "
                "Adresse, Name, Mobilnummer)"
            )
        if "create_reservation" in expected_tools:
            goal_hints.append(
                "Dein Ziel: Reservierung abschliessen (Datum, Uhrzeit, Personen, Name, Mobilnummer)"
            )
        goal_block = ("\nZIEL DIESES ANRUFS:\n" + "\n".join(goal_hints) + "\n") if goal_hints else ""

        system = (
            f"Du BIST ein echter Mensch der beim Restaurant DOBOO in Bonn anruft.\n"
            f"Name: {persona_name}\n"
            f"Situation: {persona_situation}\n"
            f"Anliegen: {desc}\n"
            f"{goal_block}"
            f"{persona_behavior_block}"
            f"\n"
            f"VERHALTEN (echter Mensch am Telefon):\n"
            f"- Sprich NUR Deutsch. Natuerliche Saetze (1-3 Saetze pro Antwort).\n"
            f"- Reagiere auf das was der Rezeptionist ZULETZT gesagt hat.\n"
            f"- Beantworte Fragen direkt und vollstaendig (z.B. nenne Name UND Telefonnummer wenn beides gefragt).\n"
            f"- Wenn du etwas nicht verstehst, bitte um Wiederholung.\n"
            f"- WICHTIG: Aendere deine Wortwahl bei jeder Antwort.\n"
            f"- Wenn dein Anliegen erledigt ist, verabschiede dich natuerlich und vollstaendig.\n"
            f"\n"
            f"VERBOTEN:\n"
            f"- Metakommentare oder Erklaerungen\n"
            f"- Woertliche Wiederholungen aus vorherigen Turns"
        )

        messages = [{"role": "system", "content": system}] + history

        try:
            client = self._get_openai()
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=150,
                temperature=0.7,
            )
            if self.cost_tracker is not None and getattr(resp, "usage", None):
                u = resp.usage
                self.cost_tracker.add_openai_usage(
                    int(getattr(u, "prompt_tokens", 0) or 0),
                    int(getattr(u, "completion_tokens", 0) or 0),
                )
            text = resp.choices[0].message.content.strip()
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            return text
        except Exception as e:
            logger.warning(f"GPT caller generation failed: {e} — using fallback")
            return self._smart_fallback(scenario, history, turn_idx)

    def _smart_fallback(self, scenario, history: List[Dict], turn_idx: int) -> str:
        """Generate scenario-aware fallback when OpenAI is unavailable."""
        import random
        exp_tools = set(getattr(scenario, "expected_tools", None) or [])
        cat = getattr(scenario, "category", "").lower()

        bot_said = ""
        order_done = False
        if history:
            for msg in reversed(history):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if not bot_said:
                        bot_said = content.lower()
                    if "create_order" in content or "send_sms" in content:
                        order_done = True

        if order_done:
            return random.choice([
                "Vielen Dank, das war alles. Auf Wiedersehen!",
                "Perfekt, danke schön. Auf Wiedersehen!",
                "Super, vielen Dank! Tschüss!",
            ])

        asked_phone = any(w in bot_said for w in ["telefon", "nummer", "rufnummer"])
        asked_name = any(w in bot_said for w in ["name", "wer bestellt"])
        asked_dish = any(w in bot_said for w in ["gericht", "bestellen", "möchten sie", "was darf"])
        asked_date = any(w in bot_said for w in ["datum", "wann", "tag", "uhrzeit"])
        asked_persons = any(w in bot_said for w in ["personen", "wie viele", "gäste"])
        greeted = any(w in bot_said for w in ["willkommen", "helfen", "guten tag", "womit"])

        if asked_phone:
            return random.choice([
                "Meine Nummer ist 0152 34567890.",
                "Ja, 0176 98765432.",
                "Unter 0221 1234567 bin ich erreichbar.",
            ])
        if asked_name:
            return random.choice(["Müller.", "Schmidt.", "Mein Name ist Weber."])
        if asked_dish:
            return random.choice([
                "Ich nehme ein Bibimbap bitte.",
                "Bulgogi klingt gut.",
                "Einmal Kimchi Jjigae bitte.",
                "Ich hätte gerne Japchae.",
            ])
        if asked_date:
            return random.choice([
                "Diesen Samstag um 19 Uhr bitte.",
                "Am Freitag um 20 Uhr.",
                "Morgen Abend, so gegen 18:30.",
            ])
        if asked_persons:
            return random.choice(["Für 4 Personen.", "Wir sind zu dritt.", "Für 2 Personen bitte."])

        # Scenario-driven utterances based on expected tools and category
        ORDER_FLOW = [
            "Meine Telefonnummer ist 0176 55512345.",
            "Ja genau, das wäre alles.",
            "Vielen Dank, auf Wiedersehen!",
        ]
        RESERVATION_FLOW = [
            "Für Samstag Abend um 19 Uhr bitte.",
            "Für 4 Personen, auf den Namen Müller.",
            "Ja, bitte reservieren. Meine Nummer ist 0176 33344455.",
            "Vielen Dank, auf Wiedersehen!",
        ]
        MENU_FLOW = [
            "Was steht bei Ihnen auf der Speisekarte?",
            "Ich nehme ein Bibimbap bitte. Meine Nummer ist 0152 11122233.",
            "Ja genau, das wäre alles.",
            "Vielen Dank, auf Wiedersehen!",
        ]
        GENERAL_FLOW = [
            "Was haben Sie auf der Speisekarte?",
            "Ich möchte gerne ein Bibimbap bestellen.",
            "Meine Telefonnummer ist 0176 99988877.",
            "Ja genau, das wäre alles. Auf Wiedersehen!",
        ]

        if "create_reservation" in exp_tools:
            flow = RESERVATION_FLOW
        elif "create_order" in exp_tools:
            flow = ORDER_FLOW if "get_menu" not in exp_tools else MENU_FLOW
        else:
            flow = GENERAL_FLOW

        flow_idx = max(0, turn_idx - len(getattr(scenario, "turns", [])))
        if flow_idx < len(flow):
            return flow[flow_idx]
        return random.choice([
            "Ja genau, das wäre alles.",
            "Vielen Dank für die Hilfe!",
            "Auf Wiedersehen!",
        ])

    def _is_end_call(self, tools_called: List[str], bot_response: str) -> bool:
        """Return True if the conversation should end."""
        if "end_call" in tools_called:
            return True
        bot_lower = bot_response.lower()
        return any(phrase in bot_lower for phrase in END_PHRASES)

    async def run(self, scenario, phase: int, run_number: int) -> ConvResult:
        """
        Run a full multi-turn conversation.
        Turn 0: scripted opener from scenario.turns[0]
        Turns 1+: pre-planned full-conversation turns (GPT-generated upfront),
                  then reactive GPT generation as fallback.
        """
        t_conv_start = time.time()

        turns: List[ConvTurn] = []
        all_tools: List[str]  = []
        total_audio           = 0

        # Conversation history for GPT context (caller role)
        gpt_history: List[Dict] = []

        # Build list of scripted turns from scenario
        scripted = [t.user_utterance for t in scenario.turns if t.user_utterance.strip()]

        # Pre-plan the full conversation arc in a single GPT call
        planned_turns: List[str] = await self._plan_full_conversation(scenario, len(scripted))

        # Minimum turns enforcement — bot cannot end before this
        min_turns = MIN_TURNS_BY_PHASE.get(phase, 10)
        max_turns_cap = MAX_TURNS_BY_PHASE.get(phase, self.max_turns)

        end_reason = "max_turns"
        error_msg  = None
        state = ConversationState()

        try:
            for turn_idx in range(max_turns_cap):
                t_turn_start = time.time()
                effective_min = (
                    4 if (state.order_created or state.reservation_created) else min_turns
                )

                # ── Determine caller utterance ────────────────────────────
                planned_idx = turn_idx - len(scripted)
                if turn_idx < len(scripted):
                    # Use hand-written scripted turn
                    caller_text = scripted[turn_idx]
                elif 0 <= planned_idx < len(planned_turns):
                    # Use pre-planned turn from full-conversation plan
                    caller_text = planned_turns[planned_idx]
                    logger.debug(f"  T{turn_idx}: [PLANNED] {caller_text[:80]}")
                else:
                    # Fallback: reactive turn-by-turn generation
                    caller_text = await self._generate_caller_turn(
                        scenario, gpt_history, turn_idx, effective_min
                    )

                # Natural goodbye from caller side — only allow after min_turns
                caller_lower = caller_text.lower()
                if any(phrase in caller_lower for phrase in END_PHRASES):
                    if turn_idx + 1 >= effective_min:
                        end_reason = "goodbye"
                        break
                    else:
                        # Caller tried to leave too early — override with follow-up
                        remaining = effective_min - (turn_idx + 1)
                        caller_text = await self._generate_caller_turn(
                            scenario,
                            gpt_history + [{
                                "role": "system",
                                "content": (
                                    f"Du hast noch {remaining} weitere Fragen. "
                                    f"Verabschiede dich NICHT — stelle stattdessen eine neue Frage "
                                    f"zum Restaurant, Menü, Öffnungszeiten oder deiner Bestellung."
                                )
                            }],
                            turn_idx,
                        )
                        logger.debug(
                            f"    T{turn_idx}: caller goodbye blocked "
                            f"(turn {turn_idx+1} < min {effective_min}) — regenerated"
                        )

                # ── Step 1+2: Caller TTS → Deepgram STT ─────────────────
                t_caller = time.time()
                try:
                    audio_seg, stt_transcript, wer = await self.audio_injector.inject_caller_turn(
                        user_utterance=caller_text,
                        noise_variant=getattr(scenario, "noise_variant", "clean"),
                        stt_min_accuracy=self.stt_threshold,
                    )
                    caller_lat = (time.time() - t_caller) * 1000
                    turn_passed = True
                except Exception as stt_err:
                    # STT failed — use raw text as fallback, log as warning
                    stt_transcript = caller_text
                    wer = 0.0
                    caller_lat = (time.time() - t_caller) * 1000
                    turn_passed = False
                    logger.warning(f"  Turn {turn_idx} STT error (using raw text): {stt_err}")
                    audio_seg = None

                update_state_from_utterance(state, stt_transcript)

                # ── Step 3: Gemini LLM ───────────────────────────────────
                t_bot = time.time()
                try:
                    bot_response = await self.gemini_runner._call_gemini_lm(
                        user_message=stt_transcript,
                        context=gpt_history[-20:],
                    )

                    # Layer 2 fallback: ensure tool calling (if REGEL 0 in prompt didn't work)
                    bot_response = self._ensure_tool_call(bot_response, stt_transcript, turn_idx)

                    # Extract tool calls from response
                    turn_tools = list(self.gemini_runner._parse_tool_calls(bot_response))

                    # Deduplicate get_menu: max one per conversation for scoring/auditor
                    if "get_menu" in turn_tools and "get_menu" in all_tools:
                        turn_tools = [t for t in turn_tools if t != "get_menu"]
                        bot_response = re.sub(
                            r"`\[TOOL:get_menu\]`",
                            "",
                            bot_response,
                            flags=re.IGNORECASE,
                        )
                        bot_response = re.sub(
                            r"\[TOOL:get_menu\]",
                            "",
                            bot_response,
                            flags=re.IGNORECASE,
                        )
                        bot_response = bot_response.strip()

                    update_state_after_bot(state, bot_response)

                    # ══ WHITELIST VALIDATION: Block create_order if no valid menu dish ══
                    if "create_order" in turn_tools and not state.selected_dish:
                        logger.warning(f"  T{turn_idx}: BLOCKED create_order -- no valid menu dish in state (selected_dish={state.selected_dish})")
                        turn_tools = [t for t in turn_tools if t != "create_order"]
                        turn_tools = [t for t in turn_tools if t != "send_sms"]

                    # Auto-inject [TOOL:get_menu] on the first food-related turn
                    # when Gemini skips it (common when customer names a dish directly)
                    if (
                        "get_menu" not in all_tools
                        and "get_menu" not in turn_tools
                        and (state.order_intent or state.selected_dish)
                    ):
                        bot_response = f"[TOOL:get_menu] " + bot_response
                        turn_tools.insert(0, "get_menu")

                    br_low = bot_response.lower()
                    if (
                        state.should_prompt_for_phone()
                        and "telefon" not in br_low
                        and "nummer" not in br_low
                    ):
                        bot_response = (
                            bot_response.rstrip()
                            + f"\n\nDarf ich kurz Ihre Telefonnummer für die Bestellung von "
                            f"{state.selected_dish} notieren?"
                        )

                    if (
                        state.ready_for_order_commit()
                        and "create_order" not in bot_response.lower()
                        and "create_order" not in turn_tools
                    ):
                        bot_response = (
                            bot_response.rstrip()
                            + "\n[TOOL:create_order]\n[TOOL:send_sms]"
                        )
                        turn_tools.append("create_order")
                        turn_tools.append("send_sms")
                        state.order_created = True

                    if "create_order" in turn_tools:
                        state.order_created = True
                    if "create_reservation" in turn_tools:
                        state.reservation_created = True

                    recent = state.recent_responses[-8:]
                    bot_response = apply_response_variations(
                        bot_response,
                        recent,
                        self._variation_rotator,
                    )
                    state.recent_responses.append(bot_response)
                    if len(state.recent_responses) > 12:
                        state.recent_responses = state.recent_responses[-12:]

                    all_tools.extend(turn_tools)
                except Exception as llm_err:
                    bot_response = "Entschuldigung, ich habe ein technisches Problem."
                    turn_tools   = []
                    logger.warning(f"  Turn {turn_idx} LLM error: {llm_err}")

                # ── Step 4: Gemini Flash TTS ─────────────────────────────
                try:
                    tts_audio, _ = await self.gemini_runner._synthesize_response(bot_response)
                    tts_bytes = len(tts_audio)
                    total_audio += tts_bytes
                except Exception as tts_err:
                    tts_bytes = 0
                    logger.warning(f"  Turn {turn_idx} TTS error: {tts_err}")

                bot_lat   = (time.time() - t_bot) * 1000
                turn_lat  = (time.time() - t_turn_start) * 1000

                # ── Record turn ──────────────────────────────────────────
                turn_rec = ConvTurn(
                    turn_idx=turn_idx,
                    caller_text=caller_text,
                    stt_transcript=stt_transcript,
                    wer=wer,
                    bot_response=bot_response,
                    tts_bytes=tts_bytes,
                    tools_called=turn_tools,
                    caller_latency_ms=caller_lat,
                    bot_latency_ms=bot_lat,
                    total_latency_ms=turn_lat,
                    passed=turn_passed,
                )
                turns.append(turn_rec)

                # Update GPT history so it adapts to what bot said.
                # From GPT's perspective:
                #   "assistant" = GPT's own previous caller utterances
                #   "user"      = the bot's responses (what GPT reacts to next)
                gpt_history.append({"role": "assistant", "content": caller_text})
                gpt_history.append({"role": "user",      "content": bot_response})

                logger.debug(
                    f"    T{turn_idx}: caller={caller_text[:40]!r} | "
                    f"bot={bot_response[:50]!r} | "
                    f"tools={turn_tools} | {turn_lat:.0f}ms"
                )

                # ── Check end conditions (respect min_turns) ─────────────
                if self._is_end_call(turn_tools, bot_response):
                    if turn_idx + 1 >= effective_min:
                        end_reason = "end_call_tool" if "end_call" in turn_tools else "goodbye"
                        break
                    else:
                        # Too early — inject a system hint so GPT keeps pushing
                        remaining = effective_min - (turn_idx + 1)
                        gpt_history.append({
                            "role": "system",
                            "content": (
                                f"Der Bot wollte das Gespräch beenden, aber du hast noch {remaining} "
                                f"weitere Fragen oder Anliegen. Stelle jetzt eine neue Frage zum "
                                f"Restaurant, Menü, Öffnungszeiten, oder deiner Bestellung/Reservierung."
                            )
                        })
                        logger.debug(
                            f"    T{turn_idx}: early-end blocked "
                            f"(turn {turn_idx+1} < min {effective_min}) — GPT continues"
                        )

        except Exception as e:
            error_msg  = str(e)
            end_reason = "error"
            logger.error(f"Conversation error at turn {len(turns)}: {e}")

        total_lat = (time.time() - t_conv_start) * 1000
        expected  = list(getattr(scenario, "expected_tools", []) or [])

        # Pass if: all expected tools called AND no critical errors
        tools_ok = all(t in all_tools for t in expected) if expected else True
        passed   = tools_ok and len(turns) > 0 and error_msg is None

        return ConvResult(
            scenario_id=scenario.id,
            phase=phase,
            run_number=run_number,
            turns=turns,
            tools_called=all_tools,
            expected_tools=expected,
            total_latency_ms=total_lat,
            total_audio_bytes=total_audio,
            passed=passed,
            end_reason=end_reason,
            error=error_msg,
        )
