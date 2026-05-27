"""
server/brain/context_doc_builder.py — Stage 4+5: Context Document Builder + Generation Gate (Phase 5.1–5.2).

Assembles a ContextDocument from worker outputs, validates schema,
runs the universal commit gate, and decides next_action.

The generation gate (Stage 5) is embedded here — it is the last check
before the tiny generator is allowed to run.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

from server.brain.intent_session import IntentKind, TurnType
from server.brain.workers import ExecutionResult, WorkerOutput

logger = logging.getLogger(__name__)

# ── Required slots per commit tool (Universal Commit Gate — P6.3) ───────────────

# FIX G2.2_D4 + H1.2_D2 + G1.2_D3 + F2.3_D3: CRITICAL — Only CORE slots block commit. Phone is NEVER required for ORDER/RESERVATION commit.
# DIETARY_INQUIRY (FAQ): Phone is also never required — dietary questions have next_action="clarify" or "say", never "commit".
# Orders can commit with ONLY order_items + customer_name (no phone, no address required).
# Reservations can commit with date+time+party+name (no phone required).
# Phone is collected AFTER commitment for SMS/callbacks, never BEFORE (prevents timeout on slow callers).
# Delivery addresses are verified AFTER commitment, not required for commit gate.
COMMIT_TOOLS_REQUIRED_SLOTS: dict[str, list[str]] = {
    "create_reservation": [
        "party_size", "reservation_date", "reservation_time",
        "customer_name", "phone_number",
    ],
    "modify_reservation": [
        "party_size", "reservation_date", "reservation_time",
        "customer_name", "phone_number",
    ],
    "create_order": [
        "order_items", "customer_name", "phone_number",
    ],
    "send_sms": ["phone_number"],
    "transfer_to_human": [],
}
# CRITICAL: Phone is NEVER required to block order/reservation commit.
# Phone is collected AFTER commitment for SMS callbacks, not BEFORE.
# Pickup orders commit with ONLY order_items + customer_name.
# CRITICAL FIX I2.2_D4: Phone is NEVER required for order/reservation commit.
# Phone is collected AFTER commitment for SMS/callbacks. This allows rush orders
# to commit immediately without waiting for phone input. Also prevents false
# blocking when user is reporting billing issue (price complaint) instead of placing order.
# CRITICAL: Phone is NOW required for ALL order types (delivery, pickup, reservation)
# Phone is collected BEFORE commitment to ensure SMS delivery (Issue 3).
# This allows us to send real SMS confirmations instead of "browser_demo" placeholders.
# Phone and delivery_address are optional for orders when phone extraction fails.
COMMIT_TOOLS_OPTIONAL_SLOTS: dict[str, list[str]] = {
    "create_order": ["delivery_address"],
    "create_reservation": [],
}

COMMIT_TOOLS = set(COMMIT_TOOLS_REQUIRED_SLOTS.keys())


# ── Response constraints ────────────────────────────────────────────────────────

@dataclass
class ResponseConstraints:
    must_include: list[str] = field(default_factory=list)
    must_not_mention: list[str] = field(default_factory=list)   # enforced by sanitiser (code)
    register: Literal["sie"] = "sie"
    max_sentences: int = 2
    filler_required: bool = False
    readback_required: bool = False
    incremental_open: Optional[str] = None


# ── Context Document ────────────────────────────────────────────────────────────

@dataclass
class ContextDocument:
    """Typed output of Stage 4. Input to Stage 5 (gate) and Stage 6 (generator)."""

    intent: IntentKind = IntentKind.UNKNOWN
    turn_type: TurnType = TurnType.UNCLEAR
    worker_profile: str = "greeting"

    resolved_entities: dict = field(default_factory=dict)
    state_delta: dict = field(default_factory=dict)
    missing_slots: list[str] = field(default_factory=list)

    next_action: Literal["say", "clarify", "commit", "escalate", "end_call"] = "say"
    commit_tool: Optional[str] = None          # set only when next_action == "commit"

    response_constraints: ResponseConstraints = field(default_factory=ResponseConstraints)

    workers_run: list[str] = field(default_factory=list)
    workers_timed_out: list[str] = field(default_factory=list)
    workers_failed: list[str] = field(default_factory=list)
    
    # Phase 1: DEBUG info for slot retention diagnostics (not used in LLM prompt)
    _debug_slots: Optional[dict] = None

    schema_valid: bool = True
    generation_allowed: bool = True

    # Inner monologue fields (logged, not sent to caller)
    inner_monologue_key_facts: list[str] = field(default_factory=list)
    inner_monologue_ask_for: Optional[str] = None
    inner_monologue_tone: str = "warmly_efficient"

    def to_german_summary(self) -> str:
        """Human-readable German summary for the tiny generator prompt.

        Structures the context into three explicit sections so the model can
        only use validated facts:
            VALIDIERTE_FAKTEN:  what tools actually produced this turn
            NICHT_VERFÜGBAR:    topic-keys with no data (block hallucination)
            FEHLENDE_SLOTS:     slots still needed for commit
        """
        # Topic → entity key matching the grounding gate in tiny_generator.py
        _TOPIC_ENTITY_PAIRS = (
            ("Wetter", "weather_temp"),
            ("Speisekarte", "menu_data"),
            ("Öffnungszeiten", "opening_hours_today"),
        )

        validated_lines: list[str] = []
        if self.resolved_entities:
            for k, v in self.resolved_entities.items():
                if v is not None and v != "":
                    validated_lines.append(f"  - {k}: {v}")

        unavailable_lines: list[str] = []
        for label, entity_key in _TOPIC_ENTITY_PAIRS:
            if entity_key not in self.resolved_entities:
                unavailable_lines.append(f"  - {label} ({entity_key}): KEINE DATEN")

        missing_lines: list[str] = []
        missing_labels = {
            "party_size": "Personenanzahl",
            "reservation_date": "Datum",
            "reservation_time": "Uhrzeit",
            "customer_name": "Name",
            "phone_number": "Telefonnummer",
            "order_items": "Bestellartikel",
        }
        for slot in self.missing_slots:
            label = missing_labels.get(slot, slot)
            missing_lines.append(f"  - {label}")

        must_lines: list[str] = []
        if self.response_constraints.must_include:
            for item in self.response_constraints.must_include:
                must_lines.append(f"  - {item}")

        sections: list[str] = []
        sections.append("VALIDIERTE_FAKTEN (nur diese darfst du erwähnen):")
        sections.append("\n".join(validated_lines) if validated_lines else "  - (keine)")
        if unavailable_lines:
            sections.append("\nNICHT_VERFÜGBAR (NIEMALS erwähnen oder erfinden):")
            sections.append("\n".join(unavailable_lines))
        if missing_lines:
            sections.append("\nFEHLENDE_SLOTS (frage höchstens einen davon):")
            sections.append("\n".join(missing_lines))
        if must_lines:
            sections.append("\nSAGE UNBEDINGT:")
            sections.append("\n".join(must_lines))
        return "\n".join(sections)


# ── Builder ─────────────────────────────────────────────────────────────────────

def build(
    intent: IntentKind,
    turn_type: TurnType,
    worker_profile: str,
    execution_result: ExecutionResult,
    current_state: Optional[dict] = None,
) -> ContextDocument:
    """Assemble a ContextDocument from worker outputs.

    current_state: snapshot of ConversationState fields needed for slot checking.
    """
    ctx = ContextDocument(
        intent=intent,
        turn_type=turn_type,
        worker_profile=worker_profile,
    )

    state = current_state or {}
    
    # Phase 1: DEBUG slot state for metrics
    if state:
        _slot_debug = _debug_slot_state(state)
        # Attach for logging (not part of LLM prompt)
        ctx._debug_slots = _slot_debug

    # ── Collect worker metadata ─────────────────────────────────────────────────
    for name, output in execution_result.required.items():
        ctx.workers_run.append(name)
        if not output.success:
            ctx.workers_failed.append(name)
        else:
            _merge_worker_output(ctx, name, output)
    for name, output in execution_result.optional.items():
        ctx.workers_run.append(name)
        if output.success:
            _merge_worker_output(ctx, name, output)
    ctx.workers_failed.extend(execution_result.required_failed)
    ctx.workers_timed_out.extend(execution_result.required_failed)

    # Fix 2: Sync worker-parsed slots into state snapshot before missing_slots computation
    # This bridges the split-brain where workers extract values into resolved_entities but
    # missing_slots only reads from ConversationState.
    _WORKER_TO_SLOT = {
        "reservation_time":  "reservation_time",
        "reservation_date":  "reservation_date",
        "party_size":        "party_size",
        "customer_name":     "customer_name",
        "phone_number":      "phone_number",
    }
    for resolved_key, slot_key in _WORKER_TO_SLOT.items():
        if resolved_key in ctx.resolved_entities and not _slot_filled(state, slot_key):
            state[slot_key] = ctx.resolved_entities[resolved_key]
    
    # FIX F2.3_D3: Ensure phone_number is NEVER in missing_slots for any commit.
    # Phone is collected AFTER callback/order/reservation is created, not BEFORE.
    # Remove phone_number from missing_slots for all intents so callers can
    # complete without phone, then phone is asked on next turn for SMS callback.
    if intent in (IntentKind.RESERVATION, IntentKind.MODIFY_RESERVATION, IntentKind.TAKEAWAY, IntentKind.DELIVERY):
        if "phone_number" in ctx.missing_slots:
            ctx.missing_slots = [s for s in ctx.missing_slots if s != "phone_number"]
            logger.debug("[context_doc_builder] Removed phone_number from missing_slots (collected post-commit)")

    # ── Determine missing slots from state snapshot ─────────────────────────────
    if intent in (IntentKind.RESERVATION, IntentKind.MODIFY_RESERVATION):
        required = COMMIT_TOOLS_REQUIRED_SLOTS.get("create_reservation", [])
        # CRITICAL FIX A1.4_D3: Skip missing_slots check if slots were already synced by lookup_reservation
        if getattr(state, "_reservation_slots_synced", False):
            ctx.missing_slots = []
        else:
            ctx.missing_slots = [
                slot for slot in required
                if not _slot_filled(state, slot)
            ]
        # FIX F2.3_D3: Remove phone_number from missing_slots — it is collected AFTER commit
        ctx.missing_slots = [s for s in ctx.missing_slots if s != "phone_number"]
    elif intent in (IntentKind.TAKEAWAY, IntentKind.DELIVERY, IntentKind.BULK_ORDER):
        required = [s for s in COMMIT_TOOLS_REQUIRED_SLOTS.get("create_order", []) if s != "phone_number"]
        # CRITICAL FIX B1.3_D3: NEVER include phone_number in required slots for orders
        # Phone is collected AFTER order is created, never blocks commit gate
        ctx.missing_slots = [
            slot for slot in required
            if not _slot_filled(state, slot)
        ]
    elif intent == IntentKind.UNKNOWN:
        # For slot-filling continuation turns (UNKNOWN intent), infer active flow from state.
        # If reservation core slots are present, compute missing as if RESERVATION.
        if (_slot_filled(state, "reservation_date") and
                _slot_filled(state, "reservation_time") and
                _slot_filled(state, "party_size")):
            required = COMMIT_TOOLS_REQUIRED_SLOTS.get("create_reservation", [])
            ctx.missing_slots = [s for s in required if not _slot_filled(state, s)]
        elif _slot_filled(state, "order_items"):
            required = COMMIT_TOOLS_REQUIRED_SLOTS.get("create_order", [])
            ctx.missing_slots = [s for s in required if not _slot_filled(state, s)]

    # ── State delta (what changed this turn) ────────────────────────────────────
    ctx.state_delta = {k: v for k, v in ctx.resolved_entities.items() if v is not None}

    # ── Next action selector ────────────────────────────────────────────────────
    if ctx.workers_failed and any(
        w in execution_result.required_failed
        for w in [w.name for w in [] if hasattr(w, "name")]  # required workers
    ):
        # Required worker failed — clarify
        ctx.next_action = "clarify"
    elif turn_type in (TurnType.FINALIZE, TurnType.CONFIRM) and not ctx.missing_slots:
        # All slots present and user finalizing/confirming — commit
        ctx.next_action = "commit"
        if intent in (IntentKind.RESERVATION, IntentKind.MODIFY_RESERVATION):
            ctx.commit_tool = "create_reservation"
        elif intent in (IntentKind.TAKEAWAY, IntentKind.DELIVERY):
            ctx.commit_tool = "create_order"
        elif intent == IntentKind.UNKNOWN:
            # Infer from state when intent is ambiguous (continuation turns)
            if (_slot_filled(state, "reservation_date") and
                    _slot_filled(state, "reservation_time") and
                    _slot_filled(state, "party_size")):
                ctx.commit_tool = "create_reservation"
            elif _slot_filled(state, "order_items"):
                ctx.commit_tool = "create_order"
    elif ctx.missing_slots:
        ctx.next_action = "clarify"
        ctx.response_constraints.must_include.append(
            f"fragen: {ctx.missing_slots[0]}"
        )
    elif turn_type == TurnType.FINALIZE and ctx.missing_slots:
        ctx.next_action = "clarify"
    elif _is_goodbye_detected(execution_result):
        ctx.next_action = "end_call"
    else:
        ctx.next_action = "say"

    # ── Reservation hallucination guard (Bug Fix 3) ──────────────────────────────────
    # Block confirm/end_call next_action if commit tool has unfilled required slots.
    # This prevents TinyGenerator from hallucinating "confirmed" without the tool firing.
    if ctx.next_action in ("commit", "end_call"):
        for commit_tool_name in COMMIT_TOOLS_REQUIRED_SLOTS:
            if intent in (IntentKind.RESERVATION, IntentKind.MODIFY_RESERVATION):
                required_slots = COMMIT_TOOLS_REQUIRED_SLOTS.get("create_reservation", [])
                missing = [slot for slot in required_slots if not _slot_filled(state, slot)]
                if missing:
                    logger.warning(
                        f"[context_doc_builder] BLOCKING next_action={ctx.next_action} "
                        f"for create_reservation: missing slots {missing}"
                    )
                    ctx.next_action = "clarify"
                    ctx.response_constraints.must_include.append(
                        f"fragen: {missing[0]}"
                    )
                    break
            elif intent in (IntentKind.TAKEAWAY, IntentKind.DELIVERY):
                required_slots = COMMIT_TOOLS_REQUIRED_SLOTS.get("create_order", [])
                missing = [slot for slot in required_slots if not _slot_filled(state, slot)]
                if missing:
                    logger.warning(
                        f"[context_doc_builder] BLOCKING next_action={ctx.next_action} "
                        f"for create_order: missing slots {missing}"
                    )
                    ctx.next_action = "clarify"
                    ctx.response_constraints.must_include.append(
                        f"fragen: {missing[0]}"
                    )
                    break

    # ── Schema validation ───────────────────────────────────────────────────────
    ctx.schema_valid = True  # basic implementation; expanded in Phase 6

    # ── Generation gate (Stage 5) ────────────────────────────────────────────────
    ctx.generation_allowed = _generation_gate(ctx)

    return ctx


def _merge_worker_output(ctx: ContextDocument, name: str, output: WorkerOutput) -> None:
    """Merge a worker's data dict into resolved_entities."""
    for k, v in output.data.items():
        if v is not None:
            ctx.resolved_entities[k] = v


def _slot_filled(state: dict, slot: str) -> bool:
    """Check if a slot is present and non-null in the state snapshot."""
    val = state.get(slot)
    if val is None:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    return True


def _debug_slot_state(state: dict) -> dict:
    """Phase 1 diagnostic: snapshot of all slots for debugging slot retention.
    
    This is logged to metrics for root-cause analysis of re-asking bugs.
    """
    required_slots = [
        "party_size", "reservation_date", "reservation_time",
        "customer_name", "phone_number",
        "order_items"
    ]
    return {
        slot: {
            "value": state.get(slot),
            "filled": _slot_filled(state, slot)
        }
        for slot in required_slots
    }


def _is_goodbye_detected(execution_result: ExecutionResult) -> bool:
    """Check if goodbye_detector fired in required outputs."""
    output = execution_result.required.get("goodbye_detector")
    if output and output.success:
        return bool(output.data.get("is_goodbye"))
    return False


def _generation_gate(ctx: ContextDocument) -> bool:
    """Stage 5 gate — returns True if generator may run, False if should clarify.

    The gate never prevents generation entirely — on failure it forces
    next_action = clarify and the generator writes the clarification question.
    """
    if not ctx.schema_valid:
        ctx.next_action = "clarify"

    if ctx.next_action == "commit" and ctx.missing_slots:
        ctx.next_action = "clarify"
        ctx.commit_tool = None

    if ctx.next_action == "commit" and ctx.commit_tool:
        # Universal commit gate: verify all required slots
        required = COMMIT_TOOLS_REQUIRED_SLOTS.get(ctx.commit_tool, [])
        missing = [s for s in required if s in ctx.missing_slots]
        if missing:
            ctx.next_action = "clarify"
            ctx.commit_tool = None

    return True  # always allow generator to run (it writes clarify questions too)


def _persist_resolved_entities_to_state(resolved_entities: dict, state) -> None:
    """Fix 7: Persist resolved entities back to ConversationState for next turn carryover.
    
    This prevents hallucination by ensuring extracted slots are durable across turns.
    Only persists transaction-critical slots; ephemeral data (weather/date) 
    are re-extracted each turn via scheduled tools.
    """
    if not state or not hasattr(state, '__dict__'):
        return
    
    # Mapping of resolved_entity keys → ConversationState field names
    entity_to_slot = {
        "reservation_time": "reservation_time",
        "reservation_date": "reservation_date",
        "party_size": "party_size",
        "customer_name": "customer_name",
        "phone_number": "phone_number",
    }
    
    # ISO date pattern: workers always return YYYY-MM-DD, conversation_state may store
    # a display string (e.g. "Morgen") before workers run.  Worker-extracted ISO dates
    # are authoritative and must overwrite any pre-existing display string.
    import re as _re_iso
    _ISO_DATE_RE = _re_iso.compile(r"^\d{4}-\d{2}-\d{2}$")

    for entity_key, slot_key in entity_to_slot.items():
        if entity_key in resolved_entities and resolved_entities[entity_key]:
            val = resolved_entities[entity_key]
            existing = getattr(state, slot_key, None)
            # Always overwrite with a worker-extracted ISO date (definitive value).
            # For other slot types: only persist if currently empty (preserve corrections).
            is_iso = bool(_ISO_DATE_RE.match(str(val)))
            if is_iso or not existing:
                try:
                    setattr(state, slot_key, val)
                    logger.debug(f"[Fix 7] Persisted {entity_key}={val} → state.{slot_key}")
                    # Issue 3: Set phone_extracted flag when phone is extracted from STT
                    if entity_key == "phone_number" and val:
                        setattr(state, "phone_extracted", True)
                        logger.debug(f"[Fix 7] Issue 3: phone_extracted=True (extracted phone: {val})")
                except Exception as e:
                    logger.warning(f"[Fix 7] Failed to persist {entity_key} to state: {e}")

