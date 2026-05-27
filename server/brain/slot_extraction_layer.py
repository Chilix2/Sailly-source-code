"""Semantic slot extraction layer for the v4 voice pipeline.

The layer turns a user utterance plus short conversation context into typed slot
candidates. It intentionally keeps orchestration in Python: the LLM proposes
values, validators and readback gates decide what can enter durable state.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

SEMANTIC_SLOT_NAMES = {
    "customer_name",
    "delivery_address",
    "phone",
    "order_items",
    "delivery_date",
    "party_size",
    "confirmation_intent",
}

_SYSTEM_PROMPT = (
    "Du bist ein präziser Slot-Extraktor für einen deutschsprachigen "
    "Restaurant-Sprachagenten. Extrahiere nur Informationen, die der Anrufer "
    "wirklich gesagt hat oder aus der direkten Gesprächssituation eindeutig "
    "gemeint sind. Antworte ausschließlich mit validem JSON."
)

_CONFIRMATION_YES = {
    "ja", "genau", "stimmt", "richtig", "passt", "okay", "ok", "korrekt",
    "einverstanden", "so ist es", "so passt es",
}
_CONFIRMATION_NO = {
    "nein", "nee", "nicht", "falsch", "stimmt nicht", "ändern", "aendern",
    "korrektur", "sondern", "anders",
}

_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-/()]{6,}\d)")
_BARE_INT_RE = re.compile(r"\b([1-9]|1[0-9]|20)\b")


@dataclass
class SlotCandidate:
    slot_name: str
    value: Any
    confidence: float
    evidence_span: str = ""
    source: str = "unknown"
    needs_readback: bool = False
    validator_feedback: Optional[str] = None
    validator_valid: Optional[bool] = None
    correction: bool = False

    def to_metric(self) -> dict[str, Any]:
        data = asdict(self)
        if isinstance(data.get("value"), list):
            data["value_count"] = len(data["value"])
        return data


@dataclass
class SlotCandidates:
    customer_name: Optional[SlotCandidate] = None
    delivery_address: Optional[SlotCandidate] = None
    phone: Optional[SlotCandidate] = None
    order_items: list[SlotCandidate] = field(default_factory=list)
    delivery_date: Optional[SlotCandidate] = None
    party_size: Optional[SlotCandidate] = None
    confirmation_intent: Optional[SlotCandidate] = None

    def by_name(self, slot_name: str) -> Optional[SlotCandidate]:
        if slot_name == "order_items":
            return self.order_items[0] if self.order_items else None
        return getattr(self, slot_name, None)

    def all(self) -> list[SlotCandidate]:
        result: list[SlotCandidate] = []
        for name in SEMANTIC_SLOT_NAMES:
            value = getattr(self, name, None)
            if isinstance(value, list):
                result.extend(value)
            elif value is not None:
                result.append(value)
        return result

    def to_metric(self) -> dict[str, Any]:
        return {
            "candidates": [candidate.to_metric() for candidate in self.all()],
            "candidate_count": len(self.all()),
        }


class SlotExtractionLayer:
    """Contextual extraction with deterministic fallback and latency budget."""

    def __init__(self, slot_extractor: Any = None, *, timeout_s: float = 3.5):
        self.extractor = slot_extractor
        self.timeout_s = timeout_s

    async def extract(
        self,
        *,
        user_utterance: str,
        conversation_history: list[dict[str, str]] | list[tuple[str, str]],
        current_state: Any,
        slots_to_extract: Iterable[str],
    ) -> SlotCandidates:
        started = time.monotonic()
        slots = [slot for slot in slots_to_extract if slot in SEMANTIC_SLOT_NAMES]
        deterministic = self._extract_deterministic(user_utterance, current_state, slots)
        
        # ISSUE 5 Part 1: Skip LLM on high-confidence deterministic extraction
        # If deterministic found ≥1 dish + name + address with confidence ≥0.85, skip full LLM
        _has_dish = deterministic.get("order_items", {}).get("confidence", 0.0) >= 0.85
        _has_name = deterministic.get("customer_name", {}).get("confidence", 0.0) >= 0.85
        _has_address = deterministic.get("delivery_address", {}).get("confidence", 0.0) >= 0.85
        _high_conf_deterministic = _has_dish and _has_name and _has_address
        
        llm_slots = [
            slot for slot in slots
            if slot not in deterministic
            or float(deterministic[slot].get("confidence", 0.0) or 0.0) < 0.85
            or bool(deterministic[slot].get("correction"))
            or (slot == "order_items" and self._should_llm_validate_partial_extraction(
                deterministic.get(slot), user_utterance, current_state
            ))
        ]
        
        # If we have high-confidence deterministic for core ordering signals, skip LLM
        if _high_conf_deterministic and "order_items" not in llm_slots:
            llm_slots = []
            logger.info(f"[semantic_slots] ISSUE5.1: High-confidence deterministic detected; skipping LLM")
        
        llm_candidates: dict[str, Any] = {}
        llm_timed_out = False

        if llm_slots and self.extractor is not None:
            try:
                llm_candidates = await asyncio.wait_for(
                    self._extract_via_llm(
                        user_utterance=user_utterance,
                        conversation_history=conversation_history,
                        current_state=current_state,
                        slots_to_extract=llm_slots,
                    ),
                    timeout=self.timeout_s,
                )
            except asyncio.TimeoutError:
                llm_timed_out = True
                logger.warning("[semantic_slots] LLM extractor timed out after %.2fs", self.timeout_s)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[semantic_slots] LLM extractor failed: %s", exc)

        merged = self._merge_candidates(deterministic, llm_candidates)
        candidates = self._score_and_gate(merged)
        latency_ms = int((time.monotonic() - started) * 1000)
        self._stamp_metrics(current_state, candidates, latency_ms, llm_timed_out, llm_skipped=not llm_slots)
        return candidates

    def _extract_deterministic(self, utterance: str, state: Any, slots: list[str]) -> dict[str, dict[str, Any]]:
        text = (utterance or "").strip()
        lower = text.lower()
        candidates: dict[str, dict[str, Any]] = {}

        if "phone" in slots:
            match = _PHONE_RE.search(text)
            if match:
                candidates["phone"] = self._raw_candidate(
                    match.group(0),
                    0.75,
                    match.group(0),
                    "deterministic",
                )

        if "confirmation_intent" in slots:
            yes_hits = sum(1 for token in _CONFIRMATION_YES if token in lower)
            no_hits = sum(1 for token in _CONFIRMATION_NO if token in lower)
            if yes_hits and not no_hits:
                candidates["confirmation_intent"] = self._raw_candidate("yes", 0.9, text, "deterministic")
            elif no_hits and not yes_hits:
                candidates["confirmation_intent"] = self._raw_candidate("no", 0.9, text, "deterministic")

        if "party_size" in slots and not getattr(state, "party_size", None):
            has_reservation_context = any(word in lower for word in ("person", "personen", "tisch", "reserv"))
            if has_reservation_context:
                match = _BARE_INT_RE.search(text)
                if match:
                    candidates["party_size"] = self._raw_candidate(int(match.group(1)), 0.85, match.group(1), "deterministic")

        if "order_items" in slots:
            try:
                from server.brain.conversation_state import _extract_all_dishes

                dishes = _extract_all_dishes(text, getattr(state, "known_items", None))
            except Exception:
                dishes = []
            if dishes:
                # Detect size indicator from the utterance (e.g. "0,5L", "groß", "klein")
                _size_re = re.compile(
                    r"\b(?:0[.,]\d+\s*[lL]?|\d+[.,]\d+\s*[lL]|groß|klein|mittel|large|small|medium)\b",
                    re.IGNORECASE,
                )
                _size_match = _size_re.search(lower)
                _detected_size: Optional[str] = None
                if _size_match:
                    _detected_size = _size_match.group(0).strip().replace(",", ".")

                # Detect carbonation for water items
                _carb_map = {
                    "ohne kohlensäure": "still",
                    "ohne kohlensaeure": "still",
                    "still": "still",
                    "stille": "still",
                    "sprudelnd": "sprudelnd",
                    "sprudel": "sprudelnd",
                    "mit kohlensäure": "sprudelnd",
                    "mit kohlensaeure": "sprudelnd",
                    "medium": "medium",
                }
                _detected_carb: Optional[str] = None
                for _kw, _cv in _carb_map.items():
                    if _kw in lower:
                        _detected_carb = _cv
                        break

                item_dicts = []
                for dish in dishes:
                    _is_water = dish.lower() in ("wasser", "mineralwasser")
                    item_dicts.append({
                        "dish_name": dish,
                        "quantity": 1,
                        "variant": None,
                        "size": _detected_size if len(dishes) == 1 else None,
                        "carbonation": _detected_carb if _is_water else None,
                    })
                candidates["order_items"] = self._raw_candidate(
                    item_dicts,
                    0.9,
                    text,
                    "deterministic",
                )

        return candidates

    def _should_llm_validate_partial_extraction(
        self, order_items_candidate: dict[str, Any] | None, user_utterance: str, state: Any
    ) -> bool:
        """Force LLM fallback when deterministic found items but may have missed some.
        
        Heuristic: If utterance contains multiple conjunctions (und/und/,) and we only
        extracted one item, likely missed additional dishes. Force LLM to validate.
        """
        if not order_items_candidate:
            return False
        
        try:
            items = order_items_candidate.get("value", [])
            if not isinstance(items, list) or len(items) < 1:
                return False
            
            # Count potential conjunction patterns suggesting multiple dishes
            lower_text = user_utterance.lower()
            conjunction_count = (
                lower_text.count(" und ") +
                lower_text.count(",") +
                lower_text.count(";")
            )
            
            # If we see 2+ conjunctions but only extracted 1 item, force LLM validation
            if conjunction_count >= 2 and len(items) == 1:
                return True
            
            return False
        except Exception:
            return False

    async def _extract_via_llm(
        self,
        *,
        user_utterance: str,
        conversation_history: list[dict[str, str]] | list[tuple[str, str]],
        current_state: Any,
        slots_to_extract: list[str],
    ) -> dict[str, Any]:
        client = getattr(self.extractor, "_client", None)
        model = getattr(self.extractor, "_model", "claude-haiku-4-5-20251001")
        if client is None:
            return {}

        prompt = self._build_prompt(
            user_utterance=user_utterance,
            conversation_history=conversation_history,
            current_state=current_state,
            slots_to_extract=slots_to_extract,
        )
        response = await client.messages.create(
            model=model,
            max_tokens=900,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.extractor._last_usage_metadata = getattr(  # noqa: SLF001
                self.extractor,
                "_last_usage_metadata",
                None,
            )
        text = (response.content[0].text if response.content else "{}").strip()
        if text.startswith("```"):
            text = text.split("```")[1].lstrip("json").strip()
        parsed = json.loads(text)
        return self._normalize_llm_response(parsed)

    def _build_prompt(
        self,
        *,
        user_utterance: str,
        conversation_history: list[dict[str, str]] | list[tuple[str, str]],
        current_state: Any,
        slots_to_extract: list[str],
    ) -> str:
        context = self._format_history(conversation_history[-8:])
        state_snapshot = {
            "order_intent": bool(getattr(current_state, "order_intent", False)),
            "reservation_intent": bool(getattr(current_state, "reservation_intent", False)),
            "delivery_intended": getattr(current_state, "delivery_intended", None),
            "existing_customer_name": getattr(current_state, "customer_name", None),
            "existing_delivery_address": getattr(current_state, "delivery_address", None),
            "existing_phone": getattr(current_state, "phone_number", None),
            "existing_order_items": getattr(current_state, "selected_items", None)
            or getattr(current_state, "all_order_items", lambda: [])(),
            "existing_reservation_date": getattr(current_state, "reservation_date", None),
            "existing_party_size": getattr(current_state, "party_size", None),
            "end_call_stage": getattr(current_state, "end_call_stage", "idle"),
        }
        schema = self._build_extraction_schema(slots_to_extract)
        return (
            "Extrahiere nur die angeforderten Slots aus der aktuellen Aussage und dem Gesprächskontext.\n"
            "Nutze keine Listen von Straßentypen, Namensformen oder Beispielen. Entscheide semantisch aus Kontext, "
            "welche Angabe der Anrufer gerade liefert oder korrigiert.\n"
            "Wenn ein Wert unsicher ist, gib niedrigere confidence zurück. Wenn nichts erkennbar ist, lass den Slot weg.\n"
            "Antwortformat:\n"
            "{\n"
            '  "slots": {\n'
            '    "<slot_name>": {"value": <string|number|array>, "confidence": 0.0-1.0, '
            '"evidence_span": "<Originaltext>", "correction": true|false}\n'
            "  }\n"
            "}\n\n"
            f"Angeforderte Slots als JSON-Schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
            f"Aktueller Zustand:\n{json.dumps(state_snapshot, ensure_ascii=False)}\n\n"
            f"Letzte Gesprächszüge:\n{context}\n\n"
            f"Aktuelle Anruferaussage:\n{user_utterance.strip()!r}"
        )

    def _build_extraction_schema(self, slots: list[str]) -> dict[str, Any]:
        full_schema: dict[str, Any] = {
            "customer_name": {
                "type": "string",
                "description": "Name der anrufenden Person oder korrigierter Name.",
            },
            "delivery_address": {
                "type": "string",
                "description": "Lieferadresse mit Ortsangaben, sofern der Kontext eine Adresse verlangt.",
            },
            "phone": {
                "type": "string",
                "description": "Telefonnummer, möglichst als Ziffernfolge mit Landesvorwahl falls genannt.",
            },
            "order_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "dish_name": {"type": "string", "description": "Name des Gerichts oder Getränks"},
                        "quantity": {"type": "integer", "description": "Menge (Standard: 1)"},
                        "variant": {
                            "type": ["string", "null"],
                            "description": "Variante, z.B. 'Rind', 'Vegan', 'Scharf', 'Mild'",
                        },
                        "size": {
                            "type": ["string", "null"],
                            "description": "Größe, z.B. '0.25L', '0.5L', 'groß', 'klein', 'mittel'",
                        },
                        "carbonation": {
                            "type": ["string", "null"],
                            "description": "Nur für Wasser: 'still', 'sprudelnd', 'medium'",
                        },
                    },
                    "required": ["dish_name"],
                },
                "description": "Bestellte Speisen und Getränke mit Menge, Variante, Größe und (bei Wasser) Kohlensäure.",
            },
            "delivery_date": {
                "type": "string",
                "description": "Gewünschtes Datum im ISO-Format, wenn eindeutig auflösbar.",
            },
            "party_size": {
                "type": "integer",
                "description": "Personenzahl für eine Reservierung.",
            },
            "confirmation_intent": {
                "type": "string",
                "enum": ["yes", "no", "unclear"],
                "description": "Bestätigt, verneint oder korrigiert die Person den aktuellen Readback-Schritt.",
            },
        }
        return {slot: full_schema[slot] for slot in slots if slot in full_schema}

    def _normalize_llm_response(self, parsed: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(parsed, dict):
            return {}
        raw_slots = parsed.get("slots", parsed)
        if not isinstance(raw_slots, dict):
            return {}

        normalized: dict[str, dict[str, Any]] = {}
        for slot_name, raw in raw_slots.items():
            if slot_name not in SEMANTIC_SLOT_NAMES:
                continue
            if isinstance(raw, dict):
                value = raw.get("value")
                confidence = self._confidence_to_float(raw.get("confidence", 0.7))
                evidence = str(raw.get("evidence_span") or raw.get("evidence") or "")
                correction = bool(raw.get("correction", False))
            else:
                value = raw
                confidence = 0.7
                evidence = ""
                correction = False
            if value in (None, "", [], {}):
                continue
            normalized[slot_name] = self._raw_candidate(
                value=value,
                confidence=confidence,
                evidence_span=evidence,
                source="llm",
                correction=correction,
            )
        return normalized

    def _merge_candidates(self, deterministic: dict[str, Any], llm: dict[str, Any]) -> dict[str, Any]:
        merged = dict(llm)
        for slot_name, candidate in deterministic.items():
            if candidate.get("confidence", 0.0) >= 0.85 or slot_name not in merged:
                merged[slot_name] = candidate
        return merged

    def _score_and_gate(self, candidates: dict[str, dict[str, Any]]) -> SlotCandidates:
        result = SlotCandidates()
        for slot_name, raw in candidates.items():
            confidence = max(0.0, min(1.0, self._confidence_to_float(raw.get("confidence", 0.0))))
            if confidence < 0.6:
                continue
            candidate = SlotCandidate(
                slot_name=slot_name,
                value=raw.get("value"),
                confidence=confidence,
                evidence_span=str(raw.get("evidence_span") or ""),
                source=str(raw.get("source") or "unknown"),
                needs_readback=confidence < 0.85,
                correction=bool(raw.get("correction", False)),
            )
            if slot_name == "order_items":
                items = candidate.value if isinstance(candidate.value, list) else [candidate.value]
                cleaned_items: list = []
                for item in items:
                    if isinstance(item, dict) and str(item.get("dish_name") or "").strip():
                        cleaned_items.append(item)
                    elif not isinstance(item, dict) and str(item).strip():
                        cleaned_items.append(str(item).strip())
                if cleaned_items:
                    candidate.value = cleaned_items
                    result.order_items.append(candidate)
            elif hasattr(result, slot_name):
                setattr(result, slot_name, candidate)
        return result

    def _stamp_metrics(
        self,
        state: Any,
        candidates: SlotCandidates,
        latency_ms: int,
        timed_out: bool,
        *,
        llm_skipped: bool = False,
    ) -> None:
        metric = {
            "latency_ms": latency_ms,
            "timed_out": timed_out,
            "llm_skipped": llm_skipped,
            **candidates.to_metric(),
        }
        try:
            state._last_semantic_slot_metrics = metric
            state.last_extraction = metric
            state.last_extraction_timed_out = timed_out
        except Exception:
            pass

    def _format_history(self, turns: list[dict[str, str]] | list[tuple[str, str]]) -> str:
        formatted: list[dict[str, str]] = []
        for turn in turns:
            if isinstance(turn, tuple) and len(turn) >= 2:
                formatted.append({"role": str(turn[0]), "content": str(turn[1])})
            elif isinstance(turn, dict):
                formatted.append({
                    "role": str(turn.get("role", "")),
                    "content": str(turn.get("content", "")),
                })
        return json.dumps(formatted, ensure_ascii=False)

    def _raw_candidate(
        self,
        value: Any,
        confidence: float,
        evidence_span: str,
        source: str,
        *,
        correction: bool = False,
    ) -> dict[str, Any]:
        return {
            "value": value,
            "confidence": confidence,
            "evidence_span": evidence_span,
            "source": source,
            "correction": correction,
        }

    def _confidence_to_float(self, confidence: Any) -> float:
        if isinstance(confidence, (int, float)):
            return float(confidence)
        if isinstance(confidence, str):
            return {"high": 0.9, "medium": 0.7, "low": 0.4}.get(confidence.lower(), 0.7)
        return 0.0


def slots_for_current_turn(state: Any, user_text: str = "") -> list[str]:
    """Return the semantic slots that matter for this turn."""
    lower = (user_text or "").lower()
    slots: set[str] = {"confirmation_intent"}
    if getattr(state, "end_call_stage", "idle") == "order_pre_commit_readback":
        return ["confirmation_intent"]
    if getattr(state, "order_intent", False) or any(word in lower for word in ("bestell", "liefer", "abhol", "essen")):
        slots.update({"order_items", "customer_name", "phone"})
        if (
            getattr(state, "delivery_intended", False)
            or "liefer" in lower
            or "adresse" in lower
            or " in bonn" in lower
            or "bogen" in lower
            or "straße" in lower
            or "strasse" in lower
        ):
            slots.add("delivery_address")
    if getattr(state, "reservation_intent", False) or any(word in lower for word in ("reserv", "tisch", "person")):
        slots.update({"customer_name", "party_size", "delivery_date", "phone"})
    if getattr(state, "end_call_stage", "idle") in {
        "pre_commit_readback",
        "order_pre_commit_readback",
        "readback_pending",
        "correction_pending",
    }:
        slots.update({"customer_name", "delivery_address", "order_items", "phone", "delivery_date", "party_size"})
    return sorted(slots)


def should_run_semantic_extraction(state: Any, user_text: str = "") -> bool:
    """Return False for low-value turns where deterministic v4 routing is enough."""
    lower = (user_text or "").lower()
    if getattr(state, "pending_readback_slots", None):
        return True
    if getattr(state, "end_call_stage", "idle") == "order_pre_commit_readback":
        if any(token in lower for token in _CONFIRMATION_YES | _CONFIRMATION_NO):
            return False
        return True
    if getattr(state, "end_call_stage", "idle") in {
        "pre_commit_readback",
        "order_pre_commit_readback",
        "readback_pending",
        "correction_pending",
    }:
        return True
    slot_signals = (
        "bestell", "liefer", "abhol", "essen", "reserv", "tisch", "person",
        "adresse", "straße", "strasse", "bogen", "telefon", "nummer",
        "kimchi", "bibimbap", "bebimbap", "wasser", "cola",
    )
    status_signals = (
        "noch da", "bist du da", "hallo noch", "hörst du", "hoerst du",
        "verbindung", "verbindungsproblem", "warte", "moment",
    )
    if any(signal in lower for signal in status_signals):
        return False
    phone_only_signals = (
        "telefonnummer", "nummer ist", "meine nummer", "null", "eins", "zwei",
        "drei", "vier", "fünf", "fuenf", "sechs", "sieben", "acht", "neun",
    )
    has_phone_signal = _PHONE_RE.search(user_text or "") or any(signal in lower for signal in phone_only_signals)
    has_non_phone_slot_signal = any(
        signal in lower
        for signal in (
            "bestell", "liefer", "abhol", "essen", "reserv", "tisch", "person",
            "adresse", "straße", "strasse", "bogen", "kimchi", "bibimbap",
            "bebimbap", "wasser", "cola",
        )
    )
    if has_phone_signal and not has_non_phone_slot_signal:
        return False
    if any(token in lower for token in _CONFIRMATION_YES | _CONFIRMATION_NO):
        return False
    if getattr(state, "order_intent", False) or getattr(state, "reservation_intent", False):
        return True
    if any(signal in lower for signal in slot_signals):
        return True
    if has_phone_signal:
        return True
    return False


def detect_category_mention(user_text: str) -> Optional[str]:
    """ISSUE 4 Part C: Detect if user mentioned a menu category name (e.g., 'Wasser', 'Wein', 'Sushi').
    
    Returns the category name if detected, None otherwise.
    """
    lower = (user_text or "").strip().lower()
    
    # Known category keywords for restaurants (from doboo.yaml and common patterns)
    category_keywords = {
        "wasser": "Getränke",
        "wein": "Getränke",
        "sushi": "Sushi",
        "suchumi": "Sushi",  # common misspelling
        "rollen": "Sushi",
        "nigiri": "Sushi",
        "maki": "Sushi",
        "bibimbap": "Hauptgerichte",
        "bulgogi": "Hauptgerichte",
        "ramyun": "Hauptgerichte",
        "getränk": "Getränke",
        "getranke": "Getränke",
        "limonade": "Getränke",
        "cola": "Getränke",
        "bier": "Getränke",
        "kaffee": "Getränke",
        "kaffee": "Getränke",
        "vorspeisen": "Vorspeisen",
        "vorspeise": "Vorspeisen",
        "kimchi": "Vorspeisen",
        "mandu": "Vorspeisen",
        "dessert": "Desserts",
    }
    
    for keyword, category in category_keywords.items():
        if keyword in lower:
            return category
    
    return None
