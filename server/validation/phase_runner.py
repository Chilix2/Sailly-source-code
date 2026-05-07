"""Run validation phases via Grok text generation + Postgres recording (no audio)."""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

import websockets

from server.validation.phases.definitions import PHASE_SCENARIO_DIRS
from server.validation.scenario_loader import ValidationScenario, repo_root
from server.validation.scenario_loader import load_scenarios_for_phase_folder
from server.validation.scenario_generator import ScenarioMatrix

logger = logging.getLogger(__name__)


# ── Restaurant knowledge (loaded once from doboo.yaml) ────────────────────────
@functools.lru_cache(maxsize=1)
def _load_doboo_knowledge() -> dict:
    """Load canonical Doboo restaurant facts for caller-bot verification."""
    try:
        import yaml
    except ImportError:
        return {}
    try:
        path = Path(__file__).parents[2] / "configs" / "tenants" / "doboo.yaml"
        raw = yaml.safe_load(path.read_text())
        hours = raw.get("opening_hours", {})
        menu_items = []
        for cat in raw.get("menu", {}).get("categories", []):
            for item in cat.get("items", []):
                name = item.get("name", "")
                price = item.get("price", 0)
                if name and price:
                    menu_items.append(f"{name} {price:.2f}€")
        # Deduplicate while preserving order
        seen: set = set()
        unique_menu: list = []
        for m in menu_items:
            if m not in seen:
                seen.add(m)
                unique_menu.append(m)
        return {
            "address":      raw.get("location", {}).get("address", "Friedrich-Ebert-Allee 69, 53113 Bonn"),
            "address_note": raw.get("location", {}).get("address_secondary", "Eingang Adalbert-Stifter-Straße"),
            "parking":      raw.get("location", {}).get("parking", "Parkhaus Friedrichstraße 100m"),
            "hours":        hours.get("formatted", "Mo–Do 11:30–21:30 | Fr 11:30–14:00 und 18:00–21:30 | Sa 18:00–21:30 | So geschlossen"),
            "hours_raw":    {k: v for k, v in hours.items() if k != "formatted"},
            "menu_summary": ", ".join(unique_menu[:14]),
            "max_party":    raw.get("reservation", {}).get("max_party_size", 20),
            "phone":        raw.get("practice", {}).get("phone", ""),
        }
    except Exception as exc:
        logger.warning("[doboo_kb] could not load doboo.yaml: %s", exc)
        return {
            "address":      "Friedrich-Ebert-Allee 69, 53113 Bonn",
            "address_note": "Eingang Adalbert-Stifter-Straße",
            "parking":      "Parkhaus Friedrichstraße 100m entfernt",
            "hours":        "Mo–Do 11:30–21:30 | Fr 11:30–14:00 und 18:00–21:30 | Sa 18:00–21:30 | So geschlossen",
            "hours_raw":    {"saturday": "18:00–21:30", "sunday": "geschlossen"},
            "menu_summary": "Bibimbap 14.90€, Bulgogi 16.90€, Kimchi Jjigae 13.90€, Tteokbokki 10.90€, Japchae 13.90€, Mandu 7.90€",
            "max_party":    20,
            "phone":        "",
        }


def _build_date_context() -> str:
    """Build a German date reference block relative to today."""
    today = date.today()
    weekday_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    month_de = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                "Juli", "August", "September", "Oktober", "November", "Dezember"]

    def fmt(d: date) -> str:
        return f"{weekday_de[d.weekday()]}, {d.day:02d}. {month_de[d.month - 1]} {d.year}"

    # Days until next Saturday (weekday 5)
    days_to_sat = (5 - today.weekday()) % 7
    if days_to_sat == 0:
        days_to_sat = 7  # if today IS Saturday, next Saturday is in 7 days
    this_saturday = today + timedelta(days=days_to_sat)
    next_week_saturday = this_saturday + timedelta(days=7)
    next_sunday = today + timedelta(days=(6 - today.weekday()) % 7 or 7)
    next_week_sunday = next_sunday + timedelta(days=7)

    return (
        f"Heutiges Datum: {fmt(today)}\n"
        "Kalender-Referenz (relativ zu heute):\n"
        f"  'heute'                  → {fmt(today)}\n"
        f"  'morgen'                 → {fmt(today + timedelta(1))}\n"
        f"  'übermorgen'             → {fmt(today + timedelta(2))}\n"
        f"  'nächsten Samstag'       → {fmt(this_saturday)}\n"
        f"  'nächste Woche Samstag'  → {fmt(next_week_saturday)}\n"
        f"  'nächsten Sonntag'       → {fmt(next_sunday)}  ← DOBOO ist sonntags geschlossen!\n"
        f"  'nächste Woche Sonntag'  → {fmt(next_week_sunday)}  ← DOBOO ist sonntags geschlossen!\n"
        "Berechne ALLE Datumsangaben strikt relativ zu obigem heutigen Datum."
    )


@dataclass
class ScriptResult:
    """Result from a scenario run via OpenAI text generation."""
    scenario_id: str
    bucket: str
    passed: bool = False
    failure_tags: list[str] = None
    tools_called: list[str] = None
    tools_expected: list[str] = None
    tools_missing: list[str] = None
    turns: list[dict] = None
    duration_s: float = 0.0
    error: str = ""
    call_sid: str = ""

    def __post_init__(self):
        if self.failure_tags is None:
            self.failure_tags = []
        if self.tools_called is None:
            self.tools_called = []
        if self.tools_expected is None:
            self.tools_expected = []
        if self.tools_missing is None:
            self.tools_missing = []
        if self.turns is None:
            self.turns = []


def _caller_prompt_path() -> Path:
    return (
        repo_root()
        / "test-infra"
        / "caller-bot-v4"
        / "prompts"
        / "caller_system.de.txt"
    )


class OpenAICallerBot:
    """Grok-3-mini powered scenario driver — simulates a human customer calling the restaurant."""

    def __init__(self, scenario: ValidationScenario, openai_api_key: Optional[str] = None):
        self.scenario = scenario
        self.turns: list[dict] = []  # {"role": "user"|"assistant", "content": str}
        self.turn_count = 0
        self.max_turns = 15
        self.goal_achieved = False
        self._prev_bot_text: str = ""  # for loop detection

        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise RuntimeError("pip install openai") from e

        # Prefer Grok (xAI) — same OpenAI SDK, just different base_url + key
        xai_key = os.environ.get("XAI_API_KEY")
        if xai_key:
            self.client = AsyncOpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
            self.model = "grok-3-mini"
        else:
            fallback_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
            if not fallback_key:
                raise RuntimeError("Neither XAI_API_KEY nor OPENAI_API_KEY is set")
            self.client = AsyncOpenAI(api_key=fallback_key)
            self.model = os.environ.get("OPENAI_CALLER_MODEL", "gpt-4o-mini")
            logger.warning("[caller_bot] XAI_API_KEY not set — falling back to %s", self.model)

        logger.info("[caller_bot] using model=%s", self.model)

    def _system_prompt(self) -> str:
        identity = self.scenario.caller_identity
        caller_name = identity.get("name", "ein Kunde")
        caller_phone = identity.get("phone", "")
        caller_address = identity.get("address", "")
        goal = self.scenario.caller_goal.strip()

        # Convert +49 format to German natural format (e.g., "+49 89 4521 8834" → "089 4521 8834")
        caller_phone_natural = caller_phone
        if caller_phone and caller_phone.startswith("+49"):
            # Strip +49 and prepend 0
            caller_phone_natural = "0" + caller_phone[3:].replace(" ", "")
            # Re-format with spaces for readability: "089 4521 8834" or "089 4521 8834"
            # Keep it as-is if it's already clean; the slot extractor accepts any 8-13 digit number

        identity_lines = f"Du bist {caller_name}"
        if caller_address:
            identity_lines += f", wohnhaft in {caller_address}"
        if caller_phone_natural:
            identity_lines += f", erreichbar unter {caller_phone_natural}"
        identity_lines += "."

        kb = _load_doboo_knowledge()
        date_ctx = _build_date_context()

        restaurant_facts = (
            f"Adresse:         {kb['address']} ({kb['address_note']})\n"
            f"Öffnungszeiten:  {kb['hours']}\n"
            f"Parken:          {kb['parking']}\n"
            f"Speisekarte:     {kb['menu_summary']}\n"
            f"Max. Personen:   {kb['max_party']} pro Reservierung\n"
        )
        if kb.get("phone"):
            restaurant_facts += f"Telefon:         {kb['phone']}\n"

        # Build explicit slot-answer block from required_data so the caller bot
        # always provides the exact value Sailly's slot extractor can parse.
        required = self.scenario.required_data or {}
        slot_label_map = {
            "party_size":        "Personenzahl",
            "reservation_date":  "Datum",
            "reservation_time":  "Uhrzeit",
            "customer_name":     "Name",
            "phone_number":      "Telefonnummer",
            "order_items":       "Bestellung",
        }
        answer_lines = []
        for key, label in slot_label_map.items():
            val = required.get(key)
            if val is not None and val != "":
                # For phone_number, use the natural German format
                if key == "phone_number" and caller_phone_natural:
                    val = caller_phone_natural
                answer_lines.append(f"  {label:<18} {val}")
            if val is not None and val != "":
                answer_lines.append(f"  {label:<18} {val}")
        slot_answer_block = ""
        if answer_lines:
            slot_answer_block = (
                "\n── Antworten auf Sailly's Fragen ─────────────────────────\n"
                "Wenn Sailly nach diesen Informationen fragt, antworte GENAU so:\n"
                + "\n".join(answer_lines)
                + "\nNenne diese Daten präzise, ohne Interpretation.\n"
            )

        return (
            f"{identity_lines} Du rufst beim Restaurant DOBOO Korean Soulfood in Bonn an.\n"
            "Du bist ein MENSCH und ANRUFER — du bist NICHT der Restaurantassistent Sailly.\n"
            f"Dein Anliegen: {goal}\n"
            f"{slot_answer_block}\n"
            f"── Heutiges Datum & Kalender ──────────────────────────────\n"
            f"{date_ctx}\n\n"
            f"── Fakten über DOBOO (verifiziere Sailly's Antworten dagegen) ──\n"
            f"{restaurant_facts}\n"
            "── Regeln ─────────────────────────────────────────────────\n"
            "- Antworte kurz und natürlich auf Deutsch (1–2 Sätze).\n"
            "- Benutze die höfliche Anredeform 'Sie'.\n"
            "- Beantworte Fragen des Assistenten — stelle KEINE Gegenfragen wie ein Servicemitarbeiter.\n"
            "- Falls nach deinem Namen, Adresse oder Telefonnummer gefragt wird, nenne deine Daten oben.\n"
            "── KRITISCH: Verifikationspflicht ─────────────────────────\n"
            "Wenn Sailly ein Datum, eine Uhrzeit, einen Preis, eine Adresse, Personenzahl oder\n"
            "Öffnungszeiten bestätigt oder nennt, vergleiche es mit den obigen Fakten.\n"
            "Ist es FALSCH → korrigiere Sailly in 1 Satz und hänge an:\n"
            "[Achtung Sailly: <FEHLER_TYP> — erwartet: <was du wolltest/was korrekt ist>, bestätigt: <was Sailly sagte>]\n"
            "Fehlertypen: DATUM_FALSCH | WOCHENTAG_FALSCH | UHRZEIT_FALSCH | ADRESSE_FALSCH | PREIS_FALSCH | GESCHLOSSEN | PERSONEN_FALSCH | ÖFFNUNGSZEITEN_FALSCH\n"
            "Beispiel: 'Das Datum stimmt nicht — ich hatte nächste Woche Samstag gemeint. "
            "[Achtung Sailly: DATUM_FALSCH — erwartet: Sa 16.05.2026, bestätigt: Di 12.05.2026]'"
        )

    def _build_messages(self, final_user_prompt: Optional[str] = None) -> list[dict]:
        """Build proper multi-turn message list.

        Roles stay semantically correct:
          role=user      → the caller/customer (what the human says)
          role=assistant → Sailly (what the restaurant AI says back)

        Since we want GPT-4o-mini to GENERATE the next caller (user) turn,
        we append a final user message that prompts it to respond as the customer.
        """
        messages = [{"role": "system", "content": self._system_prompt()}]
        messages.extend(self.turns)
        if final_user_prompt:
            messages.append({"role": "user", "content": final_user_prompt})
        return messages

    async def generate_opening(self) -> str:
        """Generate the caller's opening utterance."""
        goal = self.scenario.caller_goal.strip()
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "user",
                "content": (
                    f"Du rufst jetzt beim Restaurant an. Dein Anliegen: {goal}\n"
                    "Formuliere deinen Eröffnungssatz als Anrufer (1–2 Sätze, nur Deutsch, kein Englisch)."
                ),
            },
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=120,
                temperature=0.7,
            )
            opening = response.choices[0].message.content.strip()
            self.turns.append({"role": "user", "content": opening})
            logger.debug(f"[caller_bot] opening: {opening!r}")
            return opening
        except Exception as e:
            logger.error(f"[caller_bot] opening failed: {e}")
            fallback = "Guten Tag, ich würde gerne etwas anfragen."
            self.turns.append({"role": "user", "content": fallback})
            return fallback

    async def generate_next_turn(self, agent_response: str) -> Optional[str]:
        """Generate caller's next response — with active verification of Sailly's answer."""
        if self.should_end():
            return None

        self.turn_count += 1
        self.turns.append({"role": "assistant", "content": agent_response})

        # ── Programmatic checks (deterministic, run before LLM) ─────────
        pre_flags = self._programmatic_checks(agent_response)

        # Loop detected: short-circuit — no need to call LLM
        has_loop = any("BOT_LOOP" in f for f in pre_flags)
        if has_loop:
            loop_flag = next(f for f in pre_flags if "BOT_LOOP" in f)
            caller_turn = f"Das haben Sie gerade bereits gesagt. {loop_flag}"
            self.turns.append({"role": "user", "content": caller_turn})
            logger.warning("[caller_bot] LOOP detected turn %d: %r", self.turn_count, agent_response[:80])
            return caller_turn

        # ── LLM-generated response ───────────────────────────────────────
        # Append any pre-detected flags to the trigger so the LLM is aware
        extra_hints = ""
        if pre_flags:
            extra_hints = (
                "\n\nHINWEIS (vom Prüfsystem erkannt, füge am Ende ein):\n"
                + "\n".join(f"  {f}" for f in pre_flags)
            )

        trigger = (
            f"Sailly hat gerade gesagt: \"{agent_response}\"\n\n"
            "Prüfe systematisch bevor du antwortest:\n"
            "1. Datum/Wochentag: Bestätigt Sailly ein Datum? Stimmt es mit deiner Anfrage und dem Kalender überein?\n"
            "2. Uhrzeit: Liegt die Uhrzeit innerhalb der bekannten Öffnungszeiten?\n"
            "3. Tag: Ist der genannte Wochentag korrekt für das Datum?\n"
            "4. Adresse/Preis/Fakten: Stimmt alles mit den bekannten DOBOO-Fakten überein?\n"
            "\nWICHTIG: Füge NIEMALS selbst [Achtung Sailly: BOT_LOOP] ein — das geschieht automatisch "
            "durch das Prüfsystem. Antworte nur als Anrufer.\n"
            "Eine Bestätigungsabfrage ('Stimmt das so?') oder Zusammenfassung ist KEIN Loop — "
            "bestätige sie einfach mit Ja oder Nein.\n\n"
            "Wenn etwas FALSCH ist: Weise Sailly in 1 Satz darauf hin und hänge "
            "[Achtung Sailly: <FEHLER_TYP> — erwartet: <korrekt>, bestätigt: <falsch>] ans Ende.\n"
            "Wenn alles korrekt ist: Antworte natürlich als Anrufer (1–2 Sätze, nur Deutsch)."
            + extra_hints
        )

        messages = self._build_messages(final_user_prompt=trigger)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=200,
                temperature=0.7,
            )
            next_turn = response.choices[0].message.content.strip()

            # Append any pre-flags that the LLM didn't include itself
            for flag in pre_flags:
                if flag.split(" — ")[0].lower() not in next_turn.lower():
                    next_turn = next_turn.rstrip() + " " + flag

            self.turns.append({"role": "user", "content": next_turn})
            self._prev_bot_text = agent_response

            if "[achtung sailly" in next_turn.lower():
                logger.warning("[caller_bot] DETECTED ERROR turn %d: %r", self.turn_count, next_turn[:120])
            else:
                logger.debug("[caller_bot] turn %d: %r", self.turn_count, next_turn[:80])

            await self._check_goal_achieved()
            return next_turn
        except Exception as e:
            logger.error("[caller_bot] next_turn failed: %s", e)
            return None

    def _programmatic_checks(self, agent_response: str) -> List[str]:
        """
        Run deterministic checks on the bot's response.
        Returns a list of [Achtung Sailly:] flags for confirmed errors.
        """
        flags: List[str] = []
        now = datetime.now()
        text_lo = agent_response.lower()

        # ── 1. Loop detection ─────────────────────────────────────────
        # Exception: pre-commit summary ("Stimmt das so?") and post-commit readback
        # ("Ich habe X reserviert") are intentionally mirror-like — NOT a loop.
        _is_pre_commit = "stimmt das so" in text_lo
        _is_post_commit = any(kw in text_lo for kw in ("ich habe", "habe ich", "reserviert", "aufgenommen", "auf wiederhören"))
        if self._prev_bot_text and not _is_pre_commit and not _is_post_commit:
            prev = self._prev_bot_text.strip()
            curr = agent_response.strip()
            if prev and curr and len(prev) > 15 and len(curr) > 15:
                if prev == curr:
                    flags.append("[Achtung Sailly: BOT_LOOP — gleiche Antwort wiederholt]")
                elif len(prev) >= 40 and prev[:40] == curr[:40]:
                    flags.append("[Achtung Sailly: BOT_LOOP — nahezu identische Antwort wiederholt]")

        # ── 2. Past-time confirmation check ──────────────────────────
        # Only fire when the bot is confirming something
        confirmation_kw = {"bestätigt", "reserviert", "aufgenommen", "gebucht", "eingeplant"}
        is_confirmation = any(kw in text_lo for kw in confirmation_kw)

        if is_confirmation:
            # Match e.g. "19:00 Uhr", "09:30", "um 8:00"
            for m in re.finditer(r"\b(\d{1,2}):(\d{2})(?:\s*Uhr)?\b", agent_response, re.IGNORECASE):
                h, mn = int(m.group(1)), int(m.group(2))
                if 0 <= h <= 23 and 0 <= mn <= 59:
                    # If no date context is mentioned alongside, assume today
                    near_text = agent_response[max(0, m.start() - 60):m.end() + 60].lower()
                    has_future_date = bool(
                        re.search(r"\b(morgen|übermorgen|nächst|mai|juni|juli|august|dienstag|mittwoch|"
                                  r"donnerstag|freitag|samstag|sonntag|montag)\b", near_text)
                    )
                    if not has_future_date:
                        if h < now.hour or (h == now.hour and mn <= now.minute):
                            flags.append(
                                f"[Achtung Sailly: UHRZEIT_FALSCH — bestätigte Uhrzeit {h:02d}:{mn:02d} "
                                f"liegt in der Vergangenheit (jetzt {now.hour:02d}:{now.minute:02d})]"
                            )

        # ── 3. Order readback check ───────────────────────────────────
        order_confirm_kw = {"bestellung aufgenommen", "bestellt", "bestellung ist"}
        has_order_confirm = any(kw in text_lo for kw in order_confirm_kw)
        # Readback: at least one price (€) or dish name must appear in the same sentence
        has_items_listed = bool(re.search(r"\d+[,\.]\d{2}\s*€", agent_response))
        if has_order_confirm and not has_items_listed:
            flags.append(
                "[Achtung Sailly: KEIN_READBACK — Bestellung bestätigt ohne Artikel oder Preise vorzulesen]"
            )

        return flags

    async def _check_goal_achieved(self) -> None:
        """Judge whether the caller's goal was fulfilled CORRECTLY (not just superficially)."""
        if self.goal_achieved or self.turn_count < 2:
            return

        # Don't mark achieved if caller already detected an error
        if any("[achtung sailly" in t["content"].lower() for t in self.turns if t["role"] == "user"):
            return

        kb = _load_doboo_knowledge()
        date_ctx = _build_date_context()
        conversation = "\n".join(
            f"{'Anrufer' if t['role'] == 'user' else 'Sailly'}: {t['content']}"
            for t in self.turns[-12:]
        )
        judge_prompt = (
            f"{date_ctx}\n\n"
            f"Restaurant-Fakten: Adresse: {kb['address']} | Öffnungszeiten: {kb['hours']}\n\n"
            f"Ziel des Anrufers: {self.scenario.caller_goal}\n\n"
            f"Gesprächsverlauf:\n{conversation}\n\n"
            "Wurde das Ziel KORREKT erfüllt? Kriterien:\n"
            "1. Das Anliegen wurde bearbeitet UND\n"
            "2. Alle bestätigten Details (Datum, Wochentag, Uhrzeit, Personenzahl, Name, Adresse) stimmen mit der Anfrage überein.\n"
            "3. Kein [Achtung Sailly:] Fehlermarker im Gespräch.\n"
            "Antworte nur: JA oder NEIN"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Du beurteilst ob ein Gesprächsziel korrekt und vollständig erreicht wurde."},
                    {"role": "user", "content": judge_prompt},
                ],
                max_tokens=10,
                temperature=0.0,
            )
            answer = response.choices[0].message.content.strip().upper()
            if "JA" in answer or "YES" in answer:
                self.goal_achieved = True
                logger.info(f"[caller_bot] goal achieved after {self.turn_count} turns")
        except Exception as e:
            logger.debug(f"[caller_bot] goal check failed: {e}")

    def should_end(self) -> bool:
        return self.goal_achieved or self.turn_count >= self.max_turns


async def run_one_scenario(
    scenario: ValidationScenario,
    *,
    sailly_ws_url: str,
    max_duration_sec: float,
) -> ScriptResult:
    """Run scenario via OpenAI text generation + Postgres recording."""
    result = ScriptResult(
        scenario_id=scenario.id,
        bucket=scenario.bucket_name or "unknown",
    )
    t_start = time.monotonic()
    ws = None

    try:
        # Connect to /ws/demo for recording
        ws = await asyncio.wait_for(
            websockets.connect(sailly_ws_url),
            timeout=10.0,
        )

        # Handshake
        await ws.send(json.dumps({"tenant": scenario.tenant_id}))

        deadline = time.monotonic() + 20.0
        call_sid = ""
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for session_init")
            first_msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
            if isinstance(first_msg, bytes):
                continue
            try:
                data = json.loads(first_msg)
            except (json.JSONDecodeError, ValueError):
                continue
            call_sid = data.get("call_sid") or data.get("session_id") or ""
            logger.info(f"[text_run] scenario={scenario.id} connected: call_sid={call_sid!r}")
            break

        # Initialize OpenAI caller bot
        try:
            caller_bot = OpenAICallerBot(scenario, os.environ.get("OPENAI_API_KEY"))
        except Exception as e:
            logger.warning(f"[text_run] OpenAI bot init failed: {e}")
            caller_bot = None

        # ── Step 1: Send greeting trigger to kick off server greeting ────
        # In a real call the agent greets first; mirror that by sending "Hallo"
        # so the server emits ai_greeting before the caller states their request.
        # Declare turn/tool tracking here — used in greeting wait AND main loop.
        turns: list[dict] = []
        tools_called_set: set[str] = set()

        greeting_trigger = "Hallo"
        if caller_bot:
            caller_bot.turns.append({"role": "user", "content": greeting_trigger})
        await ws.send(json.dumps({"type": "user_text", "text": greeting_trigger}))
        logger.info("[text_run] scenario=%s sent greeting trigger", scenario.id)

        # ── Step 2: Wait for server greeting (bot_text) ──────────────────
        greeting_text = ""
        try:
            greet_deadline = time.monotonic() + 10.0
            while time.monotonic() < greet_deadline:
                remaining_g = greet_deadline - time.monotonic()
                if remaining_g <= 0:
                    break
                raw_g = await asyncio.wait_for(ws.recv(), timeout=remaining_g)
                if isinstance(raw_g, bytes):
                    continue
                try:
                    gdata = json.loads(raw_g)
                except (json.JSONDecodeError, ValueError):
                    continue
                if gdata.get("type") == "bot_text" and gdata.get("text", "").strip():
                    greeting_text = gdata["text"].strip()
                    tools_fired_g = gdata.get("tools_fired", [])
                    tools_called_set.update(tools_fired_g)
                    turns.append({"user": greeting_trigger, "bot": greeting_text, "tools": tools_fired_g})
                    logger.info("[text_run] scenario=%s received greeting: %r", scenario.id, greeting_text[:80])
                    break
                # Ignore non-bot_text messages (tool_event, etc.) during greeting wait
        except asyncio.TimeoutError:
            pass

        # ── Step 3: Caller responds to greeting (or generates opening if no greeting) ──
        if caller_bot:
            if greeting_text:
                # Normal path: respond to the greeting with the actual customer request
                try:
                    first_request = await caller_bot.generate_next_turn(greeting_text)
                except Exception as e:
                    logger.error("[text_run] first_request generation failed: %s", e)
                    first_request = None
            else:
                # Fallback: no greeting arrived — generate opening directly
                logger.warning("[text_run] scenario=%s no server greeting within 10s — using generate_opening fallback", scenario.id)
                try:
                    first_request = await caller_bot.generate_opening()
                except Exception as e:
                    logger.error("[text_run] generate_opening fallback failed: %s", e)
                    first_request = "Guten Tag, ich würde gerne etwas anfragen."
            if first_request:
                await ws.send(json.dumps({"type": "user_text", "text": first_request}))
        else:
            # No caller bot — use a generic opening
            first_request = "Guten Tag, ich würde gerne etwas anfragen."
            await ws.send(json.dumps({"type": "user_text", "text": first_request}))

        # Main loop
        deadline = time.monotonic() + max_duration_sec
        last_bot = None

        while True:
            if time.monotonic() >= deadline:
                result.failure_tags.append("timeout:max_duration")
                break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                result.failure_tags.append("timeout:deadline")
                break

            if caller_bot and caller_bot.should_end():
                logger.info(f"[text_run] scenario={scenario.id} goal achieved")
                break

            try:
                raw = await asyncio.wait_for(
                    ws.recv(),
                    timeout=min(remaining, 1.0),
                )
            except asyncio.TimeoutError:
                continue

            if isinstance(raw, bytes):
                continue

            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue

            msg_type = data.get("type", "")

            if msg_type == "bot_text":
                bot_text = data.get("text", "")
                tools_fired = data.get("tools_fired", [])
                tools_called_set.update(tools_fired)
                if bot_text or tools_fired:
                    turns.append({
                        "user": "",
                        "bot": bot_text,
                        "tools": tools_fired,
                    })
                    last_bot = bot_text
                    logger.debug(f"[text_run] scenario={scenario.id} bot: {bot_text!r} tools={tools_fired}")

                    # Stop if the server flagged end_call / should_end
                    if data.get("should_end") or "end_call" in tools_fired:
                        logger.info(f"[text_run] scenario={scenario.id} bot fired end_call — stopping")
                        break

                    # Generate next turn
                    if caller_bot and not caller_bot.should_end():
                        try:
                            next_turn = await caller_bot.generate_next_turn(bot_text)
                            if next_turn:
                                await ws.send(json.dumps({"type": "user_text", "text": next_turn}))
                            else:
                                logger.info(f"[text_run] scenario={scenario.id} bot: no more turns")
                                break
                        except Exception as e:
                            logger.error(f"[text_run] next_turn failed: {e}")
                            break

            elif msg_type == "tool_event":
                name = data.get("name", "")
                if name:
                    tools_called_set.add(name)
                    logger.debug(f"[text_run] scenario={scenario.id} tool_event: {name}")

            elif msg_type == "session_end":
                logger.info(f"[text_run] scenario={scenario.id} session_end")
                break

            elif msg_type == "error":
                err_msg = data.get("message", "")
                result.failure_tags.append(f"session_error:{err_msg}")
                logger.warning(f"[text_run] scenario={scenario.id} error: {err_msg}")
                break

        result.turns = turns
        result.tools_called = sorted(tools_called_set)
        result.duration_s = time.monotonic() - t_start
        result.call_sid = call_sid

        # Determine pass/fail
        result.tools_expected = scenario.expected_tools or []
        result.tools_missing = [t for t in result.tools_expected if t not in result.tools_called]

        # Check for [Achtung Sailly:] markers in the caller bot's turn history
        # (local `turns` dict never stores user text — use caller_bot.turns instead)
        achtung_flags: List[str] = []
        if caller_bot:
            for t in caller_bot.turns:
                if t.get("role") == "user" and "[achtung sailly" in t.get("content", "").lower():
                    achtung_flags.append(t["content"])
        if achtung_flags:
            result.failure_tags.append(f"caller_detected_error:{len(achtung_flags)}_flags")
            logger.warning(
                "[text_run] scenario=%s caller detected %d error(s): %s",
                scenario.id, len(achtung_flags),
                " | ".join(f[:120] for f in achtung_flags),
            )

        non_latency_failures = [t for t in result.failure_tags if "latency" not in t.lower()]
        if not result.tools_missing and not non_latency_failures:
            result.passed = True

        logger.info(
            f"[text_run] scenario={scenario.id} "
            f"passed={result.passed} tools={len(result.tools_called)}/{len(result.tools_expected)} "
            f"duration={result.duration_s:.1f}s"
        )

    except Exception as e:
        result.error = str(e)
        result.failure_tags.append(f"harness:{e}")
        logger.exception(f"[text_run] scenario={scenario.id} exception: {e}")

    finally:
        if ws is not None:
            try:
                await ws.close()
            except Exception:
                pass

    result.duration_s = time.monotonic() - t_start
    return result


async def run_phase(
    phase: str | None = None,
    *,
    phase_letter: str | None = None,
    max_concurrent: int = 3,
    sailly_ws_url: str | None = None,
    max_duration_sec: float = 180.0,
    run_fix_auditor: bool = True,
    scenario_ids: list[str] | None = None,
    bucket: str | None = None,
) -> list[ScriptResult]:
    """
    Run validation scenarios via OpenAI text + /ws/demo recording.

    Args:
        phase / phase_letter: phase identifier (e.g., "a", "b")
        max_concurrent: number of parallel scenarios
        sailly_ws_url: WebSocket URL
        max_duration_sec: timeout per scenario
        run_fix_auditor: (unused, for compatibility)

    Returns:
        list of ScriptResult objects with calls recorded to Postgres
    """
    letter = (phase or phase_letter or "a").strip().lower()
    if letter.startswith("phase_"):
        letter = letter[6:]
    letter = letter[0] if letter else "a"
    
    # Use dynamic scenario generation instead of static YAML
    phase_num = ord(letter) - ord("a")
    if phase_num < 0 or phase_num > 3:
        raise ValueError(f"Unknown phase {letter!r}; use a–d")
    
    # Generate scenarios dynamically from matrix
    matrix = ScenarioMatrix()
    scenario_dicts = matrix.get_all_scenarios_for_phase(phase_num)
    
    if not scenario_dicts:
        logger.warning("No scenarios generated for phase %s", letter)
        return []
    
    # Convert scenario dicts to ValidationScenario objects
    scenarios: list[ValidationScenario] = []
    for sc_dict in scenario_dicts:
        # Create ValidationScenario from dict
        expectations = sc_dict.get("expectations", {})
        # Store persona and difficulty metadata in expectations
        expectations["_stress_test_meta"] = {
            "difficulty": sc_dict.get("difficulty"),
            "persona": sc_dict.get("persona"),
            "base_id": sc_dict.get("base_id"),
        }
        
        scenario = ValidationScenario(
            id=sc_dict["id"],
            phase=sc_dict["phase"],
            description=sc_dict["description"],
            caller_goal=sc_dict["caller_goal"],
            caller_identity=sc_dict["caller_identity"],
            caller_patience_turns=sc_dict["caller_patience_turns"],
            tenant_id=sc_dict["tenant_id"],
            confirmation_phrases=sc_dict["confirmation_phrases"],
            expectations=expectations,
            required_data=sc_dict.get("required_data", {}),
        )
        scenarios.append(scenario)

    ws = sailly_ws_url or os.environ.get(
        "SAILLY_WS_URL", "ws://127.0.0.1:8080/ws/headless"
    )

    sem = asyncio.Semaphore(max(1, max_concurrent))
    results: list[ScriptResult | None] = [None] * len(scenarios)

    async def _run(idx: int, sc: ValidationScenario) -> None:
        async with sem:
            logger.info("[phase_runner] Starting scenario %s", sc.id)
            results[idx] = await run_one_scenario(
                sc,
                sailly_ws_url=ws,
                max_duration_sec=max_duration_sec,
            )

    await asyncio.gather(*(_run(i, s) for i, s in enumerate(scenarios)))
    out = [r for r in results if r is not None]
    return out


def results_to_jsonable(results: list[ScriptResult]) -> list[dict]:
    out = []
    for r in results:
        out.append(
            {
                "scenario_id": r.scenario_id,
                "call_sid": r.call_sid,
                "duration_sec": round(r.duration_s, 2),
                "error": r.error,
                "passed": r.passed,
                "tools_called": r.tools_called,
                "tools_missing": r.tools_missing,
            }
        )
    return out


def print_summary(results: list[ScriptResult]) -> None:
    print(json.dumps(results_to_jsonable(results), indent=2, ensure_ascii=False))
