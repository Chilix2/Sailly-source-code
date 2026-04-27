"""
SlotExtractor — per-utterance entity extraction via Claude Haiku (Vertex AI, EU).

Runs on EVERY user utterance (turn 1 onwards), regardless of conversation node.
Results are typed CapturedIntent objects merged into ConversationState.captured_intents.

Design:
- Runs fire-and-forget in parallel with the main LLM turn
- Extracts aggressively — fragments, partial values, VAD-cut utterances all
  produce useful slots
- Returns JSON that is then converted to typed CapturedIntent list
- Failure mode: returns [] — main LLM still gets whatever's in state
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Optional, TYPE_CHECKING

EXTRACTOR_MAX_TOKENS: int = 4096  # B1: reduced from 20000 — extractor output is always compact JSON

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState

logger = logging.getLogger(__name__)

_SLOT_EXTRACTION_PROMPT = """\
Du bist ein Slot-Extraktor für einen Restaurant-Sprachagenten.

Analysiere die folgende Anruferäußerung und extrahiere ALLE erkennbaren \
Informationen als JSON.

Mögliche Slots:
- name          (Vorname oder Nachname)
- phone         (Telefonnummer; Deepgram smart_format liefert "0179 345 67 89" — Leerzeichen beibehalten)
- delivery_type ("delivery" oder "pickup")
- items         (Gerichte, Getränke, Mengen — komma-getrennter Text)
- address_street (Straßenname, auch ohne Hausnummer)
- address_number (Hausnummer als Zahl)
- address_city  (Stadt)
- party_size    (Anzahl Personen als Zahl-String)
- reservation_date (Datum, ISO-Format wenn möglich)
- reservation_time (Uhrzeit, HH:MM)
- intent        ("order" | "reservation" | "faq" | null)

Für JEDEN erkannten Slot gib an:
- "value":      der extrahierte Wert (String)
- "confidence": "high" | "medium" | "low"
- "partial":    true wenn unvollständig (z.B. Straße ohne Hausnummer)
- "correction": true wenn der Anrufer eine frühere Angabe korrigiert

Regeln:
- Extrahiere AUCH aus unvollständigen Sätzen (VAD-Schnitte)
- "liefern", "Lieferung", "nach Hause", "bringen", "geliefert" \
→ delivery_type: "delivery"
- "abholen", "mitnehmen", "zum Mitnehmen", "Abholung" \
→ delivery_type: "pickup"
- Straße ohne Hausnummer → address_street.partial: true
- "nein, nicht X, sondern Y" → correction: true
- Wenn nichts erkennbar: gib {} zurück
- KEINE Halluzinationen — nur was wirklich in der Äußerung steht

Antwort NUR als JSON, keine Erklärung, keine Markdown-Fences.

Anruferäußerung:
"""

_MULTI_INTENT_PROMPT = """\
Du bist ein Slot-Extraktor für einen deutschsprachigen Restaurant-Voice-Agenten.
Analysiere die folgende Anrufer-Aussage und extrahiere ALLE Anliegen (intents) und Slots.

WICHTIG:
- Mehrere Anliegen in einer Aussage sind möglich (Abholung + Bestellung + Reservierung)
- Für jeden Slot: nur "high" Confidence wenn du 100% sicher bist
- Unklare Slots: confidence "low" oder weglassen
- Rate NICHT — lieber weglassen als halluzinieren

Intent-Typen:
- takeaway (sofortige Abholung vor Ort)
- delivery (sofortige Lieferung nach Hause)
- bulk_order (Sammelbestellung für ein späteres Datum / Veranstaltung)
- reservation (Tischreservierung)
- pre_order (Vorbestellung: Anrufer weiß, dass Restaurant jetzt zu ist, möchte für Öffnungszeit bestellen)
- modify_order (bestehende Bestellung ändern: "ich wollte noch einen Bibimbap dazu")
- cancel_order (bestehende Bestellung stornieren: "vergessen Sie die Bestellung")
- order_status (Frage nach Bestellstatus: "wo bleibt mein Essen?")
- modify_reservation (bestehende Reservierung ändern: "können wir statt 7 Uhr um 8 kommen?")
- cancel_reservation (Reservierung absagen: "ich muss leider stornieren")
- complaint (Beschwerde über Qualität, Service, Lieferung, fehlendes Item)
- payment_issue (Zahlungsproblem: doppelt abgebucht, Karte abgelehnt, Rückerstattung)
- lost_and_found (Gegenstand im Restaurant vergessen: "ich habe meine Jacke vergessen")
- dietary_inquiry (Ernährungsfrage: glutenfrei, vegan, vegetarisch, Nussallergie)
- group_catering (Großbestellung >20 Personen oder Menge >30 Stück — erfordert Rückruf)
- faq (allgemeine Info: Öffnungszeiten, Adresse, Speisekarte, Preise)

Antworte AUSSCHLIESSLICH mit diesem JSON-Schema (kein Text, keine Erklärung):
{
  "caller_name": "Vorname Nachname | null",
  "phone": "Telefonnummer wie von Deepgram smart_format geliefert (z.B. '0179 345 67 89') — führende Leerzeichen entfernen, aber Leerzeichen im Format beibehalten | null",
  "address": {
    "street": "Straßenname | null",
    "number": "Hausnummer | null",
    "city": "Stadt | null"
  },
  "intents": [
    {
      "kind": "takeaway | delivery | bulk_order | reservation | pre_order | modify_order | cancel_order | order_status | modify_reservation | cancel_reservation | complaint | payment_issue | lost_and_found | dietary_inquiry | group_catering | faq",
      "confidence": "high | low",
      "party_size": 2,
      "pickup_offset_minutes": 30,
      "date": "Samstag | 2026-04-26 | null",
      "time": "19:00 | null",
      "occasion": "Super Bowl Party | Geburtstag | null",
      "special_requests": ["Tisch am Fenster", "Blumendeko"],
      "items": [
        {"name": "Bulgogi", "quantity": 2, "confidence": "high", "category": "food | drink"}
      ],
      "order_identifier": "Telefon+Name oder Bestellnummer | null",
      "modification": "Freitext was geändert werden soll | null",
      "complaint_type": "food_quality | service | delivery_delay | missing_item | wrong_order | other | null",
      "description": "Freitext zur Beschwerde | null",
      "issue_type": "payment_failed | double_charged | refund_needed | null",
      "item_description": "vergessener Gegenstand | null",
      "visit_date": "Datum des Besuchs | null",
      "dietary_restriction": "gluten_free | vegan | vegetarian | nut_free | dairy_free | halal | kosher | other | null",
      "channel": "takeaway | delivery | null"
    }
  ]
}

Phase-4-Flags (immer auf Top-Level zurückgeben):
{
  "negation_detected": true | false,
  "negation_scope": "cancel_all | correct_quantity | correct_dish | correct_date | correct_other | null",
  "corrected_quantity": "<Zahl> | null",
  "corrected_dish": "<Gerichtsname> | null",
  "corrected_date": "<ISO-Datum> | null",
  "corrected_time": "<HH:MM> | null",
  "abuse_detected": true | false,
  "out_of_scope": true | false,
  "confirmation_response": "confirm_all | restart_all | correct_specific | null"
}

Regeln für Phase-4-Flags:
- negation_detected: true wenn Anrufer etwas ablehnt, korrigiert oder storniert ("nein", "nicht", "doch eher", "vergessen Sie", "stimmt nicht")
- negation_scope: Untertyp der Negation (bei cancel_all: Bestellung/Reservierung komplett stornieren; bei correct_*: Korrektur)
- abuse_detected: true bei Beleidigungen, Drohungen oder wiederholt aggressivem Verhalten
- out_of_scope: true bei Themen, die kein Restaurant-Anliegen sind und auch kein Small-Talk (politische Diskussionen, technischer Support, etc.)
- confirmation_response: nur setzen wenn der Anrufer auf einen Bestätigungsschritt reagiert (ja/stimmt → confirm_all; nein/neu → restart_all; Korrektur eines Punktes → correct_specific)
- Alle Phase-4-Flags immer im JSON zurückgeben, auch wenn false/null

Regeln:
- Identitätsdaten (Name, Telefon, Adresse) gelten für ALLE Anliegen — einmal oben angeben
- Jedes Anliegen bekommt GENAU EINEN Eintrag in "intents"
- pickup_offset_minutes nur bei takeaway/delivery — "in einer halben Stunde" → 30
- Wenn ein Anliegen keine Artikel hat: "items": []
- Wenn kein phone: "phone": null (nicht weglassen)
- Wenn keine address-Teile: "address": {"street": null, "number": null, "city": null}

Anruferäußerung:
"""


class _UsageShim:
    """Maps Anthropic token counts to the field names read by adk_turn_processor."""
    __slots__ = ("prompt_token_count", "candidates_token_count")

    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.prompt_token_count = input_tokens
        self.candidates_token_count = output_tokens


_EXTRACTOR_SYSTEM = (
    "Du bist ein präziser JSON-Extraktor. "
    "Antworte ausschließlich mit validem JSON, ohne Erklärungen oder Markdown-Fences."
)


class SlotExtractor:
    """Mini LLM call that extracts slots from one utterance via Claude Haiku (Vertex AI, EU)."""

    def __init__(self, gemini_client, model: str = "claude-haiku-4-5@20251001"):
        self._client = gemini_client
        self._model = model
        # Phase 9 A1: last usage_metadata from generate_content call.
        # Read by adk_turn_processor after the extraction task completes
        # to populate _turn_timings.extract_tokens_in / extract_tokens_out.
        self._last_usage_metadata = None

    async def extract(self, utterance: str, timeout_s: float = 1.5) -> dict:
        """
        Return {slot_name: {value, confidence, partial, correction}, ...}
        or {} on any failure. Never raises.
        """
        if not utterance or not utterance.strip():
            return {}
        try:
            response = await asyncio.wait_for(
                self._client.messages.create(
                    model=self._model,
                    max_tokens=EXTRACTOR_MAX_TOKENS,
                    system=_EXTRACTOR_SYSTEM,
                    messages=[{"role": "user", "content": _SLOT_EXTRACTION_PROMPT + utterance.strip()}],
                    temperature=0.0,
                ),
                timeout=timeout_s,
            )
            # Phase 9 A1: stash usage_metadata before touching response text
            self._last_usage_metadata = _UsageShim(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            text = (response.content[0].text if response.content else "{}").strip()
            # Strip any accidental markdown fences the model may emit
            if text.startswith("```"):
                text = text.split("```")[1].lstrip("json").strip()
            parsed = json.loads(text)
            if isinstance(parsed, dict) and parsed:
                logger.info(
                    f"[SlotExtractor] '{utterance[:50]}' -> {list(parsed.keys())}"
                )
            return parsed if isinstance(parsed, dict) else {}
        except asyncio.TimeoutError:
            logger.warning(f"[SlotExtractor] timeout after {timeout_s}s")
            return {}
        except json.JSONDecodeError as exc:
            logger.warning(f"[SlotExtractor] JSON parse failed: {exc}")
            return {}
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SlotExtractor] failed: {exc}")
            return {}

    async def extract_multi(self, utterance: str, timeout_s: float = 3.5) -> dict:
        """
        Multi-intent extraction — returns structured JSON with caller_name, phone,
        address dict, and an intents[] array. Used for utterances > 40 words with
        >= 2 intent signals. Returns {} on any failure. Never raises.
        """
        if not utterance or not utterance.strip():
            return {}
        try:
            response = await asyncio.wait_for(
                self._client.messages.create(
                    model=self._model,
                    max_tokens=EXTRACTOR_MAX_TOKENS,
                    system=_EXTRACTOR_SYSTEM,
                    messages=[{"role": "user", "content": _MULTI_INTENT_PROMPT + utterance.strip()}],
                    temperature=0.0,
                ),
                timeout=timeout_s,
            )
            # Phase 9 A1: stash usage_metadata before touching response text
            self._last_usage_metadata = _UsageShim(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            text = (response.content[0].text if response.content else "{}").strip()
            if text.startswith("```"):
                text = text.split("```")[1].lstrip("json").strip()
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                n_intents = len(parsed.get("intents", []))
                logger.info(
                    f"[SlotExtractor.multi] '{utterance[:60]}' -> {n_intents} intent(s)"
                )
            return parsed if isinstance(parsed, dict) else {}
        except asyncio.TimeoutError:
            logger.warning(f"[SlotExtractor.multi] timeout after {timeout_s}s")
            return {}
        except json.JSONDecodeError as exc:
            logger.warning(f"[SlotExtractor.multi] JSON parse failed: {exc}")
            return {}
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SlotExtractor.multi] failed: {exc}")
            return {}


# ---------------------------------------------------------------------------
# Phase 2: typed output helpers
# ---------------------------------------------------------------------------

def parse_extraction_to_intents(
    extraction: dict,
    current_turn: int,
) -> List["CapturedIntent"]:
    """Convert extract_multi() raw JSON output into typed CapturedIntent list.

    This is the bridge between extraction and state storage. The old path
    returned raw dicts; this converts them to typed objects that can be
    merged into ConversationState.captured_intents.

    Returns [] on any parse error (non-fatal).
    """
    from server.brain.captured_intents import (
        CapturedIntent, IntentKind, IntentStatus,
        SlotValue, SlotStatus, SlotConfidence,
    )

    intents_raw = extraction.get("intents", [])
    if not intents_raw and extraction.get("kind"):
        # Single-intent extraction — wrap it
        intents_raw = [extraction]
    if not isinstance(intents_raw, list):
        return []

    result: List[CapturedIntent] = []
    for raw in intents_raw:
        if not isinstance(raw, dict):
            continue

        # Support both "kind" (new) and "type" (legacy) field name
        kind_str = raw.get("kind") or raw.get("type", "")
        try:
            kind = IntentKind(kind_str)
        except ValueError:
            logger.debug(f"parse_extraction_to_intents: unknown kind {kind_str!r}, skipping")
            continue

        slots: dict = {}
        # Process all recognized slot fields from the extraction JSON
        _SLOT_FIELDS = {
            "items", "party_size", "pickup_offset_minutes", "date", "time",
            "occasion", "special_requests", "pickup_time", "channel",
            "order_identifier", "modification", "complaint_type", "description",
            "issue_type", "item_description", "visit_date", "dietary_restriction",
            "event_date",
        }
        for name in _SLOT_FIELDS:
            val = raw.get(name)
            if val is None:
                continue
            # Determine status and confidence from raw value
            conf_raw = raw.get("confidence", "medium")
            try:
                conf = SlotConfidence(conf_raw)
            except ValueError:
                conf = SlotConfidence.MEDIUM

            slots[name] = SlotValue(
                name=name,
                value=json.dumps(val) if isinstance(val, (list, dict)) else str(val),
                status=SlotStatus.FILLED,
                confidence=conf,
                source_turn=current_turn,
            )

        result.append(CapturedIntent(
            kind=kind,
            status=IntentStatus.CAPTURED,
            slots=slots,
            created_turn=current_turn,
        ))

    return result


def merge_new_intents_into_state(
    state: "ConversationState",
    new_intents: List["CapturedIntent"],
    current_turn: int,
) -> None:
    """Merge extracted intents into ConversationState.captured_intents.

    Merge rules:
    - New intents with a kind not already present → append
    - New intents matching an existing kind → merge slots (newer wins for FILLED)
    - COMPLETED / CANCELLED intents are never overwritten
    - Sets current_intent_idx to first intent if not yet set
    """
    from server.brain.captured_intents import IntentStatus, SlotStatus

    for new in new_intents:
        existing = next(
            (i for i in state.captured_intents if i.kind == new.kind),
            None,
        )
        if existing is None:
            state.captured_intents.append(new)
            if state.current_intent_idx is None:
                state.current_intent_idx = len(state.captured_intents) - 1
            continue

        if existing.status in (IntentStatus.COMPLETED, IntentStatus.CANCELLED):
            continue  # frozen — do not overwrite

        # Merge slots: newer value wins for FILLED; do not overwrite CONFIRMED
        for name, new_slot in new.slots.items():
            cur = existing.slots.get(name)
            if cur is None:
                existing.slots[name] = new_slot
            elif cur.status == SlotStatus.FILLED:
                # Always take the newer value
                existing.slots[name] = new_slot
            elif cur.status == SlotStatus.CONFIRMED and new_slot.value != cur.value:
                # Caller corrected a confirmed slot — overwrite
                existing.slots[name] = new_slot
                logger.info(
                    f"merge_intents: correction of confirmed slot {name!r} "
                    f"from {cur.value!r} to {new_slot.value!r}"
                )


async def merge_new_intents_into_state_with_validation(
    state: "ConversationState",
    new_intents: List["CapturedIntent"],
    current_turn: int,
    registry: "ValidationRegistry",  # noqa: F821
) -> None:
    """
    Phase 5.5 extension of Phase 2's merge with eager validation (eager-keep decision).

    Calls `merge_new_intents_into_state` first, then fires background validation
    tasks for every newly FILLED slot that has a registered validator and hasn't
    already been VERIFIED with the same value.

    Validation tasks are NOT awaited here — they run in the background. The
    dispatcher gate (Task A3) waits up to 200 ms before blocking a tool call.
    """
    from server.brain.captured_intents import SlotStatus
    from server.brain.layer1.validation.registry import ValidationRegistry, ValidationStatus  # noqa: F811

    # Apply the standard Phase 2 merge
    merge_new_intents_into_state(state, new_intents, current_turn)

    pending_tasks: list[asyncio.Task] = []
    for intent_idx, intent in enumerate(state.captured_intents):
        for slot_name, slot_value in intent.slots.items():
            if slot_value.status != SlotStatus.FILLED or slot_value.value is None:
                continue
            slot_path = f"intent[{intent_idx}].{slot_name}"

            # Don't re-validate VERIFIED slots with the same value
            existing_status = registry.get_status(slot_path)
            if existing_status == ValidationStatus.VERIFIED:
                continue

            task = asyncio.create_task(
                registry.validate_slot(slot_path, slot_name, slot_value.value)
            )
            pending_tasks.append(task)

    # Store tasks on state so the dispatcher can wait briefly for them (A3)
    state._pending_validation_tasks = pending_tasks  # type: ignore[attr-defined]
