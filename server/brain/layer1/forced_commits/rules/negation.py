"""
layer1/forced_commits/rules/negation.py — 4-scope negation handler.

Scopes:
  cancel_all      — caller cancels their entire order/reservation
  correct_quantity — caller corrects the quantity of a dish
  correct_dish     — caller replaces a dish with another
  correct_date     — caller changes reservation date/time
  correct_other    — any other correction (catch-all)

Each rule reads state.last_extraction["negation_scope"] written by the
slot extractor and forces the appropriate state mutation via update_state.

The extractor is expected to populate:
  last_extraction["negation_detected"] = True/False
  last_extraction["negation_scope"]    = one of the 5 scope strings above
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from server.brain.layer1.forced_commits.framework import ForcedTool, Rule

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState


def _negation_detected(state: "ConversationState", extraction: dict) -> bool:
    return bool(extraction.get("negation_detected"))


def _negation_scope(extraction: dict) -> str:
    return extraction.get("negation_scope", "")


# ── Rule: cancel_all ──────────────────────────────────────────────────────────
def _matches_cancel_all(state: "ConversationState", extraction: dict) -> bool:
    return _negation_detected(state, extraction) and _negation_scope(extraction) == "cancel_all"


def _apply_cancel_all(state: "ConversationState", extraction: dict) -> List[ForcedTool]:
    return [
        ForcedTool(
            name="cancel_order",
            args={"reason": "caller_cancelled"},
            reason="negation:cancel_all",
            replace_response=(
                "Alles klar — ich habe Ihre Bestellung storniert. "
                "Gibt es noch etwas, womit ich Ihnen helfen kann?"
            ),
        )
    ]


CANCEL_ALL_RULE = Rule(
    rule_id="negation:cancel_all",
    description="Caller cancels their entire order.",
    matches=_matches_cancel_all,
    apply=_apply_cancel_all,
    priority=10,
)


# ── Rule: correct_quantity ────────────────────────────────────────────────────
def _matches_correct_quantity(state: "ConversationState", extraction: dict) -> bool:
    return _negation_detected(state, extraction) and _negation_scope(extraction) == "correct_quantity"


def _apply_correct_quantity(state: "ConversationState", extraction: dict) -> List[ForcedTool]:
    new_qty = extraction.get("corrected_quantity", "")
    dish = extraction.get("corrected_dish") or extraction.get("current_dish", "")
    return [
        ForcedTool(
            name="update_state",
            args={"field": "quantity_correction", "value": f"{new_qty}x {dish}".strip()},
            reason="negation:correct_quantity",
        )
    ]


CORRECT_QUANTITY_RULE = Rule(
    rule_id="negation:correct_quantity",
    description="Caller corrects the quantity of a dish.",
    matches=_matches_correct_quantity,
    apply=_apply_correct_quantity,
    priority=20,
)


# ── Rule: correct_dish ────────────────────────────────────────────────────────
def _matches_correct_dish(state: "ConversationState", extraction: dict) -> bool:
    return _negation_detected(state, extraction) and _negation_scope(extraction) == "correct_dish"


def _apply_correct_dish(state: "ConversationState", extraction: dict) -> List[ForcedTool]:
    new_dish = extraction.get("corrected_dish", "")
    return [
        ForcedTool(
            name="update_state",
            args={"field": "dish_correction", "value": new_dish},
            reason="negation:correct_dish",
        )
    ]


CORRECT_DISH_RULE = Rule(
    rule_id="negation:correct_dish",
    description="Caller replaces a dish with another.",
    matches=_matches_correct_dish,
    apply=_apply_correct_dish,
    priority=20,
)


# ── Rule: correct_date ────────────────────────────────────────────────────────
def _matches_correct_date(state: "ConversationState", extraction: dict) -> bool:
    return _negation_detected(state, extraction) and _negation_scope(extraction) == "correct_date"


def _apply_correct_date(state: "ConversationState", extraction: dict) -> List[ForcedTool]:
    new_date = extraction.get("corrected_date") or extraction.get("reservation_date", "")
    new_time = extraction.get("corrected_time") or extraction.get("reservation_time", "")
    tools = []
    if new_date:
        tools.append(ForcedTool(
            name="update_state",
            args={"field": "reservation_date", "value": new_date},
            reason="negation:correct_date",
        ))
    if new_time:
        tools.append(ForcedTool(
            name="update_state",
            args={"field": "reservation_time", "value": new_time},
            reason="negation:correct_date",
        ))
    return tools or [ForcedTool(
        name="update_state",
        args={"field": "date_correction_requested", "value": "true"},
        reason="negation:correct_date (no specific value)",
    )]


CORRECT_DATE_RULE = Rule(
    rule_id="negation:correct_date",
    description="Caller changes the reservation date or time.",
    matches=_matches_correct_date,
    apply=_apply_correct_date,
    priority=20,
)


# ── Rule: correct_other (catch-all) ──────────────────────────────────────────
def _matches_correct_other(state: "ConversationState", extraction: dict) -> bool:
    return _negation_detected(state, extraction) and _negation_scope(extraction) == "correct_other"


def _apply_correct_other(state: "ConversationState", extraction: dict) -> List[ForcedTool]:
    # Signal that a correction was requested — LLM must ask what specifically
    return [
        ForcedTool(
            name="update_state",
            args={"field": "correction_requested", "value": "true"},
            reason="negation:correct_other",
        )
    ]


CORRECT_OTHER_RULE = Rule(
    rule_id="negation:correct_other",
    description="Catch-all: caller says 'no' / negates without specific scope.",
    matches=_matches_correct_other,
    apply=_apply_correct_other,
    priority=30,
)


# ── Exported list ─────────────────────────────────────────────────────────────
NEGATION_RULES = [
    CANCEL_ALL_RULE,
    CORRECT_QUANTITY_RULE,
    CORRECT_DISH_RULE,
    CORRECT_DATE_RULE,
    CORRECT_OTHER_RULE,
]
