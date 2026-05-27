"""Validators for semantic slot candidates.

Validators are deliberately small and deterministic. They do not decide the
conversation flow; they only adjust candidate confidence and normalize values.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Optional

from server.brain.slot_extraction_layer import SlotCandidate

logger = logging.getLogger(__name__)


@dataclass
class SlotValidationResult:
    is_valid: bool
    confidence_adjustment: float = 0.0
    feedback: str = ""
    corrected_value: Optional[Any] = None
    tool_called: Optional[str] = None


class SlotValidator:
    async def validate(self, candidate: SlotCandidate) -> SlotValidationResult:
        return SlotValidationResult(is_valid=True)


class AddressValidator(SlotValidator):
    def __init__(self, *, call_sid: str, tenant_id: str, city: Optional[str] = None):
        from server.brain.conversation_state import _get_default_city
        
        self.call_sid = call_sid
        self.tenant_id = tenant_id
        # Use passed city, or look up from tenant config, or default
        if city:
            self.city = city
        else:
            self.city = _get_default_city()

    async def validate(self, candidate: SlotCandidate) -> SlotValidationResult:
        address = str(candidate.value or "").strip()
        if not address:
            return SlotValidationResult(False, -0.5, "Adresse leer.")
        try:
            from tools.executor import execute_tool

            result = await execute_tool(
                "verify_address",
                {"address": address, "city": self.city, "country": "Deutschland"},
                self.call_sid,
                self.tenant_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[semantic_slots] verify_address failed: %s", exc)
            return SlotValidationResult(
                is_valid=False,
                confidence_adjustment=-0.15,
                feedback=f"verify_address failed: {exc}",
                tool_called="verify_address",
            )

        if not isinstance(result, dict):
            return SlotValidationResult(
                is_valid=False,
                confidence_adjustment=-1.0,
                feedback="Adresse konnte nicht validiert werden.",
                tool_called="verify_address",
            )

        success = bool(
            result.get("success")
            or result.get("valid")
            or result.get("ok")
            or result.get("status") in {"valid", "ok", "success"}
        )
        normalized = (
            result.get("canonical_address")
            or result.get("normalized_address")
            or result.get("formatted_address")
            or result.get("address")
        )
        confidence = float(result.get("confidence") or (1.0 if success else 0.0))
        needs_confirm = bool(result.get("needs_caller_confirm"))

        if success and normalized and (needs_confirm or confidence < 0.9):
            target_confidence = 0.84
            return SlotValidationResult(
                is_valid=True,
                confidence_adjustment=target_confidence - candidate.confidence,
                feedback=result.get("readback_text") or "Adresse bitte bestätigen lassen.",
                corrected_value=normalized,
                tool_called="verify_address",
            )

        if not success:
            return SlotValidationResult(
                is_valid=False,
                confidence_adjustment=-1.0,
                feedback=result.get("error") or "Adresse konnte nicht validiert werden.",
                corrected_value=normalized if normalized and normalized != address else None,
                tool_called="verify_address",
            )

        return SlotValidationResult(
            is_valid=True,
            confidence_adjustment=0.15,
            feedback="Adresse validiert.",
            corrected_value=normalized if normalized else None,
            tool_called="verify_address",
        )


class PhoneValidator(SlotValidator):
    async def validate(self, candidate: SlotCandidate) -> SlotValidationResult:
        normalized = self._normalize_phone(str(candidate.value or ""))
        if len(normalized) < 9:
            return SlotValidationResult(False, -0.35, "Telefonnummer zu kurz.")
        if normalized.startswith("0"):
            normalized = "+49" + normalized[1:]
        return SlotValidationResult(
            True,
            0.1,
            "Telefonnummer normalisiert.",
            corrected_value=normalized,
        )

    def _normalize_phone(self, phone: str) -> str:
        phone = phone.strip()
        has_plus = phone.startswith("+")
        digits = re.sub(r"\D", "", phone)
        return ("+" if has_plus else "") + digits


class OrderItemValidator(SlotValidator):
    def __init__(self, state: Any):
        self.state = state

    async def validate(self, candidate: SlotCandidate) -> SlotValidationResult:
        values = candidate.value if isinstance(candidate.value, list) else [candidate.value]
        requested = [str(item).strip() for item in values if str(item).strip()]
        if not requested:
            return SlotValidationResult(False, -0.3, "Keine Bestellposition erkannt.")

        menu_names = self._menu_names()
        if not menu_names:
            return SlotValidationResult(True, 0.0, "Kein Menücache vorhanden; Kandidaten bleiben vorläufig.")

        matched: list[str] = []
        missing: list[str] = []
        for item in requested:
            match = self._best_menu_match(item, menu_names)
            if match:
                matched.append(match)
            else:
                missing.append(item)
        if missing:
            return SlotValidationResult(
                True,
                -0.05,
                f"Nicht auf Menü gematcht: {', '.join(missing)}",
                corrected_value=requested,
            )
        return SlotValidationResult(
            True,
            0.15,
            "Bestellpositionen auf Menü gematcht.",
            corrected_value=matched,
        )

    def _menu_names(self) -> list[str]:
        cached_menu = getattr(self.state, "cached_menu", None)
        names: list[str] = ["Bibimbap", "Kimchi", "Bulgogi", "Mandu", "Wasser", "Cola"]
        if isinstance(cached_menu, dict):
            items = cached_menu.get("items") or cached_menu.get("menu") or []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("name"):
                        names.append(str(item["name"]))
                        aliases = item.get("aliases") or []
                        if isinstance(aliases, list):
                            names.extend(str(alias) for alias in aliases if str(alias).strip())
                    elif isinstance(item, str):
                        names.append(item)
            for category_items in cached_menu.values():
                if not isinstance(category_items, list):
                    continue
                for item in category_items:
                    if isinstance(item, dict) and item.get("name"):
                        names.append(str(item["name"]))
                        aliases = item.get("aliases") or []
                        if isinstance(aliases, list):
                            names.extend(str(alias) for alias in aliases if str(alias).strip())
                    elif isinstance(item, str):
                        names.append(item)
        names.extend(str(item) for item in getattr(self.state, "known_items", []) or [])
        return sorted(set(name for name in names if name))

    def _best_menu_match(self, requested: str, menu_names: list[str]) -> Optional[str]:
        requested_l = self._normalize_food_token(requested.lower())
        best_name = None
        best_score = 0.0
        for name in menu_names:
            name_l = name.lower()
            if requested_l == name_l or requested_l in name_l or name_l in requested_l:
                return name
            score = SequenceMatcher(None, requested_l, name_l).ratio()
            if score > best_score:
                best_score = score
                best_name = name
        return best_name if best_score >= 0.68 else None

    def _normalize_food_token(self, text: str) -> str:
        for heard, canonical in {
            "bebimbap": "bibimbap",
            "bibimbab": "bibimbap",
            "bimbap": "bibimbap",
            "bimbab": "bibimbap",
        }.items():
            text = re.sub(rf"\b{re.escape(heard)}\b", canonical, text)
        return text


class DateValidator(SlotValidator):
    async def validate(self, candidate: SlotCandidate) -> SlotValidationResult:
        value = str(candidate.value or "").strip()
        if not value:
            return SlotValidationResult(False, -0.3, "Datum leer.")
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return SlotValidationResult(True, 0.1, "Datum im ISO-Format.")
        return SlotValidationResult(True, 0.0, "Datum semantisch erkannt, nicht normalisiert.")


class PartySizeValidator(SlotValidator):
    async def validate(self, candidate: SlotCandidate) -> SlotValidationResult:
        try:
            value = int(candidate.value)
        except Exception:
            return SlotValidationResult(False, -0.4, "Personenzahl nicht numerisch.")
        if 1 <= value <= 20:
            return SlotValidationResult(True, 0.1, "Personenzahl plausibel.", corrected_value=value)
        return SlotValidationResult(False, -0.4, "Personenzahl außerhalb des erwarteten Bereichs.")
