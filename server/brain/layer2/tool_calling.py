"""
layer2/tool_calling.py — Hybrid tool-calling for Sailly.

Two modes:
  • Native (state-transition tools): build_function_declarations() produces
    Gemini FunctionDeclarations for tools that mutate conversation state.
    These are dispatched through the normal executor.execute_tool() path.

  • Text-tag (speech-style tools): the LLM embeds lightweight tags in its
    text output for speech actions that should NOT interrupt streaming TTS.
    parse_layer2_output() strips those tags and returns them as ToolCall objects.

State-transition tools (native):
  update_state, create_order, create_reservation, transfer_to_human,
  send_sms, capture_catering_lead, confirm_order, cancel_order

Speech-style text-tag tools (text):
  [PAUSE], [SPELL:<text>], [EMPHASIZE:<text>]
  These are TTS hints — callers never hear the tag text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── ToolCall dataclass ─────────────────────────────────────────────────────────


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    is_native: bool = True  # False = speech-style text-tag


# ── State-transition tool set ─────────────────────────────────────────────────
# CRITICAL: transfer_to_human is the canonical escalation tool for manager requests.
# escalate_to_manager is an alias that maps to transfer_to_human in executor.
STATE_TRANSITION_TOOLS = frozenset({
    "update_state",
    "create_order",
    "create_reservation",
    "cancel_reservation",
    "transfer_to_human",
    "send_sms",
    "capture_catering_lead",
    "confirm_order",
    "cancel_order",
    "log_complaint",
    "process_refund",
})

# ── Gemini FunctionDeclaration schemas ────────────────────────────────────────
_TOOL_SCHEMAS: Dict[str, Dict] = {
    "update_state": {
        "description": "Update one or more conversation-state slots after extracting them from the caller's utterance.",
        "parameters": {
            "type": "object",
            "properties": {
                "field": {"type": "string", "description": "Slot name to update"},
                "value": {"type": "string", "description": "New value for the slot"},
            },
            "required": ["field", "value"],
        },
    },
    "create_order": {
        "description": "Commit a confirmed food order to the POS system.",
        "parameters": {
            "type": "object",
            "properties": {
                "items":          {"type": "string", "description": "Comma-separated list of ordered items"},
                "delivery_type":  {"type": "string", "enum": ["delivery", "pickup"]},
                "name":           {"type": "string"},
                "phone":          {"type": "string"},
                "address":        {"type": "string"},
            },
            "required": ["items", "delivery_type", "name"],
        },
    },
    "create_reservation": {
        "description": "Create a restaurant reservation.",
        "parameters": {
            "type": "object",
            "properties": {
                "name":             {"type": "string"},
                "party_size":       {"type": "integer"},
                "reservation_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "reservation_time": {"type": "string", "description": "HH:MM"},
                "phone":            {"type": "string"},
            },
            "required": ["name", "party_size", "reservation_date", "reservation_time"],
        },
    },
    "transfer_to_human": {
        "description": "Escalate the call to a human agent.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
            },
            "required": ["reason"],
        },
    },
    "send_sms": {
        "description": "Send an SMS confirmation to the caller.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone":   {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["phone", "message"],
        },
    },
    "capture_catering_lead": {
        "description": "Record a group-catering lead for follow-up callback.",
        "parameters": {
            "type": "object",
            "properties": {
                "name":                          {"type": "string"},
                "phone":                         {"type": "string"},
                "catering_callback_availability": {"type": "string"},
                "group_size":                    {"type": "string"},
                "event_date":                    {"type": "string"},
            },
            "required": ["name", "phone", "catering_callback_availability"],
        },
    },
    "confirm_order": {
        "description": "Signal that all order data has been confirmed by the caller.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "cancel_order": {
        "description": "Cancel the current order on caller request.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
            },
            "required": [],
        },
    },
    "cancel_reservation": {
        "description": "Cancel an existing restaurant reservation.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer name"},
                "date": {"type": "string", "description": "Reservation date (ISO YYYY-MM-DD or 'heute')"},
                "time": {"type": "string", "description": "Reservation time HH:MM"},
            },
            "required": ["name", "date", "time"],
        },
    },
    "escalate_to_manager": {
        "description": "Escalate an angry or manager-demanding customer to human manager immediately.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for escalation (e.g. 'manager_request', 'frustrated_customer')"},
            },
            "required": ["reason"],
        },
    },
    "log_complaint": {
        "description": "Log a food complaint (wrong dish, missing item, quality issue) for follow-up by restaurant team.",
        "parameters": {
            "type": "object",
            "properties": {
                "complaint_type": {"type": "string", "description": "e.g. 'wrong_dish', 'missing_item', 'quality_issue'"},
                "description": {"type": "string", "description": "Detailed description of the complaint"},
                "order_id": {"type": "string"},
                "dish_name": {"type": "string"},
            },
            "required": ["complaint_type", "description"],
        },
    },
    "process_refund": {
        "description": "Process a refund for a complaint or cancelled order.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason": {"type": "string"},
                "amount": {"type": "number"},
            },
            "required": ["reason"],
        },
    },
}

# ── Text-tag regex for speech-style tools ────────────────────────────────────
_TEXT_TAG_RE = re.compile(
    r'\[(PAUSE|SPELL:([^\]]+)|EMPHASIZE:([^\]]+))\]',
    re.IGNORECASE,
)


def build_function_declarations(allowed_tools: Optional[frozenset] = None) -> List[Dict]:
    """
    Return a list of Gemini FunctionDeclaration dicts for the given tool set.

    If `allowed_tools` is None, all STATE_TRANSITION_TOOLS are included.
    Only tools whose names appear in STATE_TRANSITION_TOOLS are emitted;
    speech-style tools are never declared as native functions.
    """
    subset = allowed_tools if allowed_tools is not None else STATE_TRANSITION_TOOLS
    return [
        {"name": name, **schema}
        for name, schema in _TOOL_SCHEMAS.items()
        if name in subset
    ]


def parse_layer2_output(text: str) -> Tuple[str, List[ToolCall]]:
    """
    Strip speech-style text-tag tool calls from LLM output text.

    Returns (clean_text, list_of_ToolCall).
    Native tool calls are NOT parsed here — they come through the SDK function-
    calling response path and are handled by the turn processor directly.
    """
    tool_calls: List[ToolCall] = []

    def _replace(match: re.Match) -> str:
        raw = match.group(1).upper()
        if raw == "PAUSE":
            tool_calls.append(ToolCall(name="PAUSE", args={}, is_native=False))
        elif raw.startswith("SPELL:"):
            spell_text = match.group(2)
            tool_calls.append(ToolCall(name="SPELL", args={"text": spell_text}, is_native=False))
        elif raw.startswith("EMPHASIZE:"):
            emph_text = match.group(3)
            tool_calls.append(ToolCall(name="EMPHASIZE", args={"text": emph_text}, is_native=False))
        return ""

    clean = _TEXT_TAG_RE.sub(_replace, text)
    clean = " ".join(clean.split())  # collapse whitespace gaps left by removed tags
    return clean, tool_calls


def is_forced_transfer_sentinel(chunk: str) -> bool:
    """Return True if the chunk is the retry-exhausted fallback sentinel."""
    return chunk.strip() == "__FORCE_TRANSFER_TO_HUMAN__"
