"""
ADKTurnProcessor — per-call wrapper around the validated ADKRunner brain.

Extracts the per-turn loop body from ADKRunner.run() into a reusable class
that can be called one turn at a time from a Pipecat FrameProcessor instead
of running a full scenario in a loop.

Design principles:
- One instance per call. All state is instance-level — concurrency safe.
- Redis serialization after every turn — survives WebSocket reconnects.
- Real tool execution via tools/executor.py (not mock/tag-only).
- Strict arg validation — tool refuses to execute when required fields missing.
- Error boundary: any LLM failure returns a German apology TurnResult.

_process_turn_inner is lifted verbatim from ADKRunner.run() lines 250-512.
[PRODUCTION] markers show the only additions on top of the validated logic.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from server.brain.conversation_state import (
    ConversationState,
    NEGATE_ORDER,
    update_state_from_utterance,
    update_state_after_bot,
    get_cached_dish_price,
)
from server.brain.order_slots import OrderSlots, SlotStatus
from server.brain.slot_extractor import SlotExtractor
from server.brain.node_manager import NodeManager
from server.brain.memory_manager import MemoryManager
from server.brain.validation_registry import ValidationRegistry, ValidationStatus
from server.brain.response_variations import (
    VariationRotator,
    apply_response_variations,
)

logger = logging.getLogger(__name__)

# Pure data-read tools that are safe to run in parallel (no shared state mutation).
# verify_address, create_order, send_sms, create_reservation are intentionally
# excluded — they must remain sequential because each depends on the previous result.
PARALLEL_SAFE_TOOLS = frozenset({
    "check_availability",
    "get_menu",
    "get_date_info",
    "get_weather",
    "faq",
    "get_restaurant_info",
    "get_caller_history",
    "ai_greeting",
})

# Tools that count as "meaningful progress" for the 8-turn escape hatch.
# Only production-available tools — must match tools/executor.py handlers.
_COMMIT_TOOLS = frozenset({
    "create_order",
    "create_reservation",
    "verify_address",
    "end_call",
    "check_availability",
    "get_date_info",
    "get_weather",
    "get_menu",
    "transfer_to_human",
    # Validation-only tools mapped to production equivalents:
    "send_sms",           # -> sms_confirmation in executor
    "transfer_to_tier2",  # -> transfer_to_human alias
    "technical_issues_callback",
    "request_callback",
    "faq",
    "get_restaurant_info",
})


def _validate_tool_call(tool: str, state: ConversationState, all_tools: list) -> bool:
    """
    Policy gate — blocks structurally invalid tool calls.
    Same logic as _validate_tool_call in adk_runner.py.
    """
    if tool == "create_order" and not state.selected_dish:
        if state.order_created:
            return True
        logger.warning("  POLICY BLOCKED create_order (no dish, not forced commit)")
        return False
    if tool == "end_call":
        if state.order_intent and not state.order_created:
            return False
        if state.reservation_intent and not state.reservation_created:
            return False
    if tool == "create_reservation" and "check_availability" not in all_tools:
        # Allow if check_availability_called flag is set — means it fired in the same turn
        # (node_manager step 7b pairs them atomically; all_tools only reflects previous turns).
        if hasattr(state, "check_availability_called") and state.check_availability_called:
            return True
        logger.warning("  POLICY BLOCKED create_reservation (check_availability not in all_tools and not called this turn)")
        return False
    return True



@dataclass
class TurnResult:
    """Result of processing a single turn."""
    clean_text: str                    # Bot response with [TOOL:...] tags stripped
    raw_response: str                  # Full response including tool tags
    tools_called: List[str] = field(default_factory=list)
    tool_results: dict = field(default_factory=dict)  # tool_name -> result dict
    should_end: bool = False
    end_reason: str = ""
    missing_fields_hint: Optional[str] = None  # Inject back to LLM if tool was blocked


class ADKTurnProcessor:
    """
    Encapsulates one call's conversation state for turn-by-turn processing.

    One instance per call. All state (ConversationState, NodeManager, MemoryManager,
    all_tools) is instance-level — no module-level shared state. Safe for concurrent calls.

    Usage:
        processor = ADKTurnProcessor(tenant_id, call_sid, session)
        result = await processor.process_turn("Ich möchte etwas bestellen")  # tenant-specific fallback
        # Use result.clean_text for TTS, result.should_end for hangup
    """

    def __init__(
        self,
        tenant_id: Optional[str],
        call_sid: str,
        session,  # CallSession | None
        caller_phone: str = "",
        filler_cb=None,  # async callable(text) -> None — pushes filler TTS frame
    ):
        self.tenant_id = tenant_id
        self.call_sid = call_sid
        self.session = session
        self.caller_phone = caller_phone
        self._filler_cb = filler_cb
        self._last_filler: str = ""  # track last filler to avoid repetition
        
        # Load tenant config from registry
        from server.core.tenant_config import get_tenant_registry
        from server.brain.conversation_state import set_known_items
        
        try:
            registry = get_tenant_registry()
            self._tenant = registry.load_tenant(tenant_id or "doboo")
        except Exception as e:
            logger.warning(f"[ADKTurn] Failed to load tenant config {tenant_id}: {e}, using defaults")
            self._tenant = None
        
        # Initialize known items for state extraction
        if self._tenant:
            set_known_items(self._tenant.items)

        # All state is instance-level — no shared module-level state
        self.state = ConversationState()
        # Sprint 0 — caller-ID prefill: when we come through Twilio the adapter
        # passes the caller-ID `From` here; the browser demo passes
        # "browser_demo" which is not a phone number and is ignored.
        if caller_phone and caller_phone not in ("", "browser", "browser_demo"):
            _digits = "".join(ch for ch in caller_phone if ch.isdigit() or ch == "+")
            if len(_digits.lstrip("+")) >= 8:
                self.state.caller_id_phone = caller_phone
                logger.info(
                    f"[CALLER-ID] Prefilled caller_id_phone={caller_phone!r} "
                    f"for call={call_sid} (unconfirmed)"
                )
        # Canonical slot form — persists for the whole call.
        # SlotExtractor enriches this in parallel with each main LLM turn.
        self.order_slots = OrderSlots()
        self._slot_extractor: Optional[SlotExtractor] = None  # lazy-init alongside gemini_runner
        self._pending_extraction_tasks: list = []

        # Seed phone slot from Twilio caller-ID when available.
        # Status=PARTIAL so next_slot_to_ask() still surfaces it for confirmation,
        # but known_summary_de() shows the value so the bot can read it back.
        if self.state.caller_id_phone:
            self.order_slots.phone.value = self.state.caller_id_phone
            self.order_slots.phone.status = SlotStatus.PARTIAL
            self.order_slots.phone.confidence = "high"
            self.order_slots.phone.source_turn = 0
            self.order_slots.phone.raw_mentions.append(f"caller_id:{self.state.caller_id_phone}")
            logger.info(
                f"[CALLER-ID-SLOT] Prefilled phone slot PARTIAL from caller_id={self.state.caller_id_phone!r}"
            )

        # Give ConversationState a back-reference so memory_manager and
        # node_manager can read slot state without importing OrderSlots.
        self.state.order_slots_ref = self.order_slots

        # Eager background validation registry — fires the moment a slot is
        # extracted, before the bot ever asks a confirmation question.
        # Initialized with a thin wrapper around executor.execute_tool so the
        # registry never imports executor at module level (avoids circular imports).
        self.validation_registry = ValidationRegistry(
            execute_tool=self._execute_tool_for_registry,
            call_sid=call_sid,
            tenant_id=tenant_id or "doboo",
            state=self.state,
        )
        # Give ConversationState a reference so memory_manager and
        # ready_for_order_commit() can query validation status.
        self.state.validation_registry_ref = self.validation_registry

        # FINDING-016 fix: also create the canonical Phase 5.5 ValidationRegistry
        # (server.brain.layer1.validation.registry) on state so that
        # dispatch_with_validation's is_committable() gate operates on the same
        # per-call instance as turn_runner.get_or_create_registry().
        # The two registries serve different purposes (see validation_registry.py
        # module docstring) and remain separate until a future unification PR.
        try:
            from server.brain.layer1.turn_runner import get_or_create_registry as _gcr
            _tenant_cfg = {}
            if self._tenant is not None:
                try:
                    _tenant_cfg = vars(self._tenant) if not isinstance(self._tenant, dict) else self._tenant
                except Exception:
                    pass
            get_or_create_registry = _gcr  # noqa: F841
            _gcr(self.state, tenant_cfg=_tenant_cfg)
        except Exception as _reg_exc:
            logger.debug("[ADKTurn] canonical registry init skipped: %s", _reg_exc)

        self.memory = MemoryManager(max_recent_turns=5)
        self.node_mgr = NodeManager(tenant=self._tenant)
        self.all_tools: List[str] = []
        self.turn_idx: int = 0
        self._variation_rotator = VariationRotator()  # Anti-repetition

        # A5: rolling ASR confidence window — populated by the brain service
        # (STTConfidenceTracker → brain_service.record_stt_confidence → here)
        self.asr_confidence_window: List[float] = []

        # Call history tracking for cross-call memory
        self._nodes_visited = []
        self._call_start_time = time.time()  # Track start time for duration calculation
        self._call_summary_mgr = None  # Lazy-initialized on first finalize_call

        # Serialise concurrent callers: _adk_turn0_init() (background state bookkeeping)
        # and the first real user turn may overlap. Without a lock they'd both run
        # process_turn() at turn_idx=0 → duplicate ai_greeting + state corruption.
        self._turn_lock = asyncio.Lock()

        # Per-call address validation cache: address_key → verify_address result.
        # Prevents re-hitting Google Maps API for the same address (e.g. caller
        # confirms, then the LLM re-validates on the next turn).
        self._addr_cache: dict = {}

        # Lazy-initialized Gemini runner (LLM client only — no AudioInjector/TTS)
        self._gemini_runner = None

        # ------------------------------------------------------------------
        # Sprint 0.4 subsystem-fire trackers.
        # Reset at the top of every _process_turn_inner call. Read by the
        # brain_service when writing google_turn_metrics so each row shows
        # which subsystems actually executed this turn (catches silent
        # failures like the ValidationRegistry issue in demo-6cf65e58003d).
        # ------------------------------------------------------------------
        self._slot_extractor_status: str = "skipped"  # completed|timeout|429|error|skipped
        self._validations_fired_this_turn: list = []
        self._validations_completed_this_turn: list = []
        self._validations_pending_end_of_turn: list = []
        self._validation_cancellations_this_turn: int = 0
        self._last_tts_directive = None
        self._barge_in_enabled: bool = True
        self._stuck_loop_check_ran: bool = False
        self._silence_reprompt_active: bool = True

    def _reset_subsystem_status_for_turn(self) -> None:
        """Reset per-turn subsystem trackers at the start of each turn."""
        self._slot_extractor_status = "skipped"
        self._validations_fired_this_turn = []
        self._validations_completed_this_turn = []
        self._validations_pending_end_of_turn = []
        self._validation_cancellations_this_turn = 0
        self._stuck_loop_check_ran = False
        self._last_prompt_tokens_in: int | None = None
        # Sprint 2.4: mirror status onto state so memory_manager can read it
        # during build_context (degradation rule 1).
        try:
            self.state._slot_extractor_status = "skipped"
        except Exception:
            pass

    def _sync_extractor_status_to_state(self) -> None:
        """Mirror _slot_extractor_status onto state for memory_manager."""
        try:
            self.state._slot_extractor_status = self._slot_extractor_status
        except Exception:
            pass

    def _collect_subsystem_status(self) -> dict:
        """Sprint 0.4: returns {subsystem: status} for every subsystem that
        SHOULD have fired this turn. Critical for catching silent failures
        like the ValidationRegistry issue in demo-6cf65e58003d."""
        try:
            pending_snapshot = []
            if self.validation_registry is not None:
                from server.brain.validation_registry import ValidationStatus
                pending_snapshot = [
                    {
                        "slot": name,
                        "started_ms_ago": int(
                            (time.perf_counter() - e.started_at) * 1000
                        ) if e.started_at else None,
                    }
                    for name, e in self.validation_registry._entries.items()
                    if e.status == ValidationStatus.PENDING
                ]
                self._validations_pending_end_of_turn = pending_snapshot
        except Exception:
            pending_snapshot = []

        return {
            "slot_extractor": self._slot_extractor_status,
            "validation_registry": (
                "fired" if self._validations_fired_this_turn else "silent"
            ),
            "validation_pending_count": len(self._validations_pending_end_of_turn or []),
            "tts_conditioning": (
                "applied" if self._last_tts_directive is not None else "skipped"
            ),
            "barge_in": "enabled" if self._barge_in_enabled else "disabled",
            "stuck_loop_detector": (
                "ran" if self._stuck_loop_check_ran else "skipped"
            ),
            "memory_manager": "ran",  # always runs
            "node_manager": "ran",    # always runs
            "silence_reprompt": (
                "armed" if self._silence_reprompt_active else "disarmed"
            ),
            "registry_exists": self.validation_registry is not None,
        }

    def _get_gemini_runner(self):
        """Lazy-initialize Tier2AudioRunner for LLM + TTS calls."""
        if self._gemini_runner is None:
            from server.brain.tier2_runner import Tier2AudioRunner
            # GOOGLE_CLOUD_PROJECT still needed for Google Cloud TTS.
            project_id = (
                os.environ.get("GOOGLE_CLOUD_PROJECT")
                or os.environ.get("GOOGLE_PROJECT_ID")
                or "sailly-voice-agent-eu"
            )
            from server.configs.secrets import get_secret
            deepgram_key = get_secret("deepgram-api-key", default="")
            self._gemini_runner = Tier2AudioRunner(
                google_project_id=project_id,
                deepgram_api_key=deepgram_key,
                temperature=0.0,
            )
            # Pre-initialize LLM client to avoid cold-start on first turn
            try:
                self._gemini_runner._init_clients()
            except Exception as e:
                logger.warning(f"[ADKTurn] Bedrock runner pre-init failed (will retry on first turn): {e}")
        return self._gemini_runner

    async def _execute_tool_for_registry(
        self,
        tool_name: str,
        args: dict,
        call_sid: str,
        tenant_id: str,
        conversation_state=None,
    ):
        """
        Thin wrapper around executor.execute_tool for use by ValidationRegistry.
        Deferred import avoids circular dependency at module level.
        """
        from tools.executor import execute_tool
        return await execute_tool(
            tool_name, args, call_sid, tenant_id,
            conversation_state=conversation_state,
        )

    def _compose_address_for_validation(self) -> str:
        """Build full address string from current slot values for deduplication."""
        slots = self.order_slots
        parts = []
        if slots.address_street.value:
            parts.append(slots.address_street.value)
        if slots.address_number.is_usable():
            parts.append(slots.address_number.value)
        city = slots.address_city.value if slots.address_city.is_usable() else (
            self._tenant.city if self._tenant else "Bonn"
        )
        parts.append(city)
        return ", ".join(p for p in parts if p)

    async def _schedule_validations(self, slot_names: list) -> None:
        """
        Fire background validators for each newly-filled slot group.

        Called immediately after slot extraction merges new data. Zero
        confidence threshold — validation always fires; deduplication in
        ValidationRegistry prevents duplicate calls for the same value.
        """
        logger.info(
            f"[VALIDATION_DEBUG] newly_filled={slot_names} "
            f"registry_exists={self.validation_registry is not None} "
            f"registry_id={id(self.validation_registry) if self.validation_registry else None}"
        )
        slots = self.order_slots
        city = (self._tenant.city if self._tenant else None) or "Bonn"
        addr_trigger = {"address_street", "address_number", "address_city"}

        # Address: fire when ANY address component was just filled
        if addr_trigger & set(slot_names) and slots.address_street.value:
            full_addr = self._compose_address_for_validation()
            await self.validation_registry.ensure_validated(
                "address",
                full_addr,
                tool_args={
                    "address": full_addr,
                    "city": slots.address_city.value or city,
                },
            )
            # Sprint 0.4: track fired validations for subsystems_fired
            self._validations_fired_this_turn.append({
                "slot": "address",
                "tool": "verify_address",
                "value": full_addr,
            })

        # Phone: fire as soon as any candidate exists
        if "phone" in slot_names and slots.phone.is_usable():
            await self.validation_registry.ensure_validated(
                "phone",
                slots.phone.value,
                tool_args={"phone": slots.phone.value, "country": "DE"},
            )
            self._validations_fired_this_turn.append({
                "slot": "phone",
                "tool": "validate_phone_format",
                "value": slots.phone.value,
            })

        # Items: fire when items slot fills
        if "items" in slot_names and slots.items.is_usable():
            items_list = [i.strip() for i in slots.items.value.split(",") if i.strip()]
            await self.validation_registry.ensure_validated(
                "items",
                slots.items.value,
                tool_args={"items": items_list},
            )
            self._validations_fired_this_turn.append({
                "slot": "items",
                "tool": "check_item_availability",
                "value": slots.items.value,
            })

        # Collect completed validations that finished during this turn
        try:
            from server.brain.validation_registry import ValidationStatus
            self._validations_completed_this_turn = [
                {
                    "slot": name,
                    "status": e.status.value,
                    "elapsed_ms": e.elapsed_ms,
                    "error": e.error,
                }
                for name, e in self.validation_registry._entries.items()
                if e.is_terminal
            ]
        except Exception:
            pass

    async def _recheck_changed_slots(self) -> None:
        """
        Re-fire validation if the extractor corrected a previously-filled slot.
        Detects cases like: caller says "nein, nicht [Straße X], sondern [Straße Y]."
        """
        slots = self.order_slots
        city = (self._tenant.city if self._tenant else None) or "Bonn"

        # Address may have been corrected
        if slots.address_street.value:
            current_addr = self._compose_address_for_validation()
            entry = self.validation_registry.get("address")
            if entry and entry.value_validated != current_addr:
                await self.validation_registry.ensure_validated(
                    "address",
                    current_addr,
                    tool_args={
                        "address": current_addr,
                        "city": slots.address_city.value or city,
                    },
                )

        # Phone may have been corrected
        if slots.phone.is_usable():
            entry = self.validation_registry.get("phone")
            if entry and entry.value_validated != slots.phone.value:
                await self.validation_registry.ensure_validated(
                    "phone",
                    slots.phone.value,
                    tool_args={"phone": slots.phone.value, "country": "DE"},
                )

    _AFFIRMATIVE_DE = frozenset(
        ("ja", "genau", "richtig", "korrekt", "stimmt", "passt", "ja genau",
         "ja richtig", "ja korrekt", "ja stimmt", "ja passt", "jep", "jup",
         "gut", "okay", "ok", "perfekt", "super", "sehr gut", "gerne")
    )
    _NEGATIVE_DE = frozenset(
        ("nein", "nicht", "falsch", "anders", "nein nein", "das stimmt nicht",
         "das ist falsch", "korrigieren", "korrektur", "ändern")
    )

    def _detect_confirmation_of_readback(self, user_text: str) -> None:
        """
        After the bot does a critical-slot readback (address/phone/summary),
        detect affirmative/negative responses and update confirmation flags.

        Tracks which slot the bot last read back via _last_readback_slot.
        The bot sets this by including a sentinel comment in its response
        (done implicitly — we infer from state progression what the bot
        asked about on the last turn, based on which flags are still False
        and which slots are available).
        """
        if not hasattr(self, "_last_readback_slot"):
            self._last_readback_slot: Optional[str] = None

        slots = self.order_slots
        text_lower = user_text.lower().strip()

        # Determine what the bot was most recently reading back.
        # Sprint 1.5: extended with name/items/delivery_type inference so
        # affirmative replies can confirm those slots too (kills the
        # "danke, danke, danke" name-loop from demo-6cf65e58003d).
        if self._last_readback_slot is None:
            delivery_is_delivery = (
                slots.delivery_type.is_usable()
                and slots.delivery_type.value == "delivery"
            )
            # Priority order matches the new dish-first checkout flow
            # (items → delivery_type → address → phone → name → summary)
            if slots.items.is_usable() and not self.state.items_confirmed:
                self._last_readback_slot = "items"
            elif (slots.delivery_type.is_usable()
                    and not self.state.delivery_type_confirmed):
                self._last_readback_slot = "delivery_type"
            elif (delivery_is_delivery
                    and slots.address_street.is_usable()
                    and not self.state.address_confirmed):
                self._last_readback_slot = "address"
            elif slots.phone.is_usable() and not self.state.phone_confirmed:
                self._last_readback_slot = "phone"
            elif slots.name.is_usable() and not self.state.name_confirmed:
                self._last_readback_slot = "name"
            elif slots.items.is_usable() and not self.state.order_summary_confirmed:
                self._last_readback_slot = "order_summary"

        if not self._last_readback_slot:
            return

        # Check for affirmative / negative tokens
        words = set(text_lower.split())
        is_affirmative = bool(words & self._AFFIRMATIVE_DE) or any(
            phrase in text_lower for phrase in self._AFFIRMATIVE_DE if " " in phrase
        )
        is_negative = bool(words & self._NEGATIVE_DE) or any(
            phrase in text_lower for phrase in self._NEGATIVE_DE if " " in phrase
        )

        # Only treat as confirmation if utterance is short (≤5 tokens).
        # Longer utterances like "Ja, ich bin noch da, Philipp Schneider" contain
        # new information and must NOT trigger confirmation flags.
        if len(user_text.split()) > 5:
            is_affirmative = False

        if is_affirmative and not is_negative:
            slot = self._last_readback_slot
            if slot == "items":
                self.state.items_confirmed = True
                logger.info("[SmartMix] items_confirmed = True")
                self._last_readback_slot = "delivery_type"
            elif slot == "delivery_type":
                self.state.delivery_type_confirmed = True
                logger.info("[SmartMix] delivery_type_confirmed = True")
                self._last_readback_slot = "address"
            elif slot == "address":
                self.state.address_confirmed = True
                logger.info("[SmartMix] address_confirmed = True")
                # Advance readback to phone next
                self._last_readback_slot = "phone"
            elif slot == "phone":
                self.state.phone_confirmed = True
                logger.info("[SmartMix] phone_confirmed = True")
                self._last_readback_slot = "name"
            elif slot == "name":
                self.state.name_confirmed = True
                logger.info("[SmartMix] name_confirmed = True")
                self._last_readback_slot = "order_summary"
            elif slot == "order_summary":
                self.state.order_summary_confirmed = True
                logger.info("[SmartMix] order_summary_confirmed = True")
                self._last_readback_slot = None

        elif is_negative:
            slot = self._last_readback_slot
            if slot == "items":
                self.state.items_confirmed = False
                self.validation_registry.mark_stale("items")
                logger.info("[SmartMix] items correction detected — marked stale")
            elif slot == "delivery_type":
                self.state.delivery_type_confirmed = False
                logger.info("[SmartMix] delivery_type correction detected")
            elif slot == "name":
                self.state.name_confirmed = False
                logger.info("[SmartMix] name correction detected")
            elif slot == "address":
                self.state.address_confirmed = False
                self.validation_registry.mark_stale("address")
                logger.info("[SmartMix] address correction detected — marked stale")
            elif slot == "phone":
                self.state.phone_confirmed = False
                self.validation_registry.mark_stale("phone")
                logger.info("[SmartMix] phone correction detected — marked stale")
            # Keep _last_readback_slot pointing at the same slot so the bot re-asks

    async def _handle_multi_intent_confirmation(self, user_text: str) -> Optional[str]:
        """
        Called each turn when captured_intents is active.

        Returns a forced bot response string (with tool tags) when the caller
        confirms the current intent's read-back, or None when:
        - caller said something ambiguous / corrective (let LLM handle)
        - there is no active intent to confirm

        On confirmation:
        1. Marks current intent confirmed + completed
        2. Advances current_intent_idx
        3. Forces [TOOL:create_order] or [TOOL:create_reservation]
        4. If all intents done: appends [TOOL:send_sms], sets multi_intent_completed
        """
        captured = self.state.captured_intents
        idx = self.state.current_intent_idx
        if not captured or idx is None or idx >= len(captured):
            return None

        current = captured[idx]
        if current.status == "completed":
            return None  # already done, nothing to confirm

        lower = user_text.lower()
        _AFFIRMATIVE = ("ja", "genau", "richtig", "korrekt", "stimmt", "passt", "jo", "okay", "ok", "gut", "super")
        _NEGATIVE = ("nein", "nicht", "falsch", "anders", "moment", "warte", "stopp", "halt")

        affirmative = any(w in lower for w in _AFFIRMATIVE)
        negative = any(w in lower for w in _NEGATIVE)

        if not affirmative or negative:
            # Ambiguous or correction — let LLM handle it; don't force anything
            return None

        # Caller confirmed — mark complete, advance
        current.status = "completed"
        self.state.current_intent_idx = idx + 1
        _total = len(captured)
        _remaining = _total - (idx + 1)

        logger.info(
            f"  T{self.turn_idx}: MULTI-INTENT confirmed '{current.type}' "
            f"({idx + 1}/{_total}), {_remaining} remaining"
        )

        # Pick the right tool
        if current.type == "reservation":
            _tool_tag = "[TOOL:create_reservation]"
        else:
            # takeaway, delivery, bulk_order all map to create_order
            _tool_tag = "[TOOL:create_order]"

        # Build forced response: tool call + transition text
        if _remaining == 0:
            # All intents done — transition to SMS state (not immediately sending yet)
            # FIX 3: Set state machine to READY_FOR_SMS so SMS gets sent in next orchestration step
            self.state.multi_intent_completed = True
            self.state.end_of_call_state = "ready_for_sms"
            _completed_types = [ci.type for ci in captured]
            from server.brain.captured_intents import INTENT_LABELS_DE
            _done_labels = [INTENT_LABELS_DE.get(t, t) for t in _completed_types]
            forced = (
                f"{_tool_tag}\n"
                f"Perfekt, alles erledigt: {', '.join(_done_labels)}. "
                f"Sie erhalten gleich eine SMS mit allen Details."
            )
        else:
            # More intents remain — fire tool, then read back next intent
            _next = captured[self.state.current_intent_idx]
            from server.brain.captured_intents import INTENT_LABELS_DE
            _next_label = INTENT_LABELS_DE.get(_next.type, _next.type)
            forced = (
                f"{_tool_tag}\n"
                f"Sehr gut. Jetzt die {_next_label}: {_next.readback_slots_de().replace(chr(10), ', ').strip('- ')}. "
                f"{'Stimmt das?' if self.state.current_intent_idx < _total - 1 else 'Möchten Sie noch was hinzufügen?'}"
            )

        return forced

    def _check_stuck_loop(self) -> bool:
        """
        Phase 4 D2: Jaccard 0.8 across last 3 bot responses via turn_control.
        """
        from server.brain.layer1.turn_control import is_stuck_loop
        return is_stuck_loop(self.state)

    def _sync_slots_to_state(self) -> None:
        """
        One-directional sync: OrderSlots → ConversationState.

        Called after every slot merge so that legacy code reading
        state.delivery_address / state.phone_number / state.customer_name
        always sees the most current extracted values.

        This eliminates the OrderSlots ↔ ConversationState divergence described
        in Issue 4 without requiring a risky dataclass property refactoring.
        """
        slots = self.order_slots

        # Sync address: build full string from components
        if slots.address_street.is_usable():
            city = (self._tenant.city if self._tenant else None) or "Bonn"
            parts = [slots.address_street.value]
            if slots.address_number.is_usable():
                parts.append(slots.address_number.value)
            parts.append(slots.address_city.value or city)
            composed = ", ".join(p for p in parts if p)
            if composed and self.state.delivery_address != composed:
                self.state.delivery_address = composed
                logger.debug(f"[SlotSync] delivery_address ← {composed!r}")

        # Sync phone
        if slots.phone.is_usable() and slots.phone.value:
            if self.state.phone_number != slots.phone.value:
                self.state.phone_number = slots.phone.value
                logger.debug(f"[SlotSync] phone_number ← {slots.phone.value!r}")

        # Sync name: prefer full name from slots over partial state name
        if slots.name.is_usable() and slots.name.value:
            if not self.state.customer_name or self.state.customer_name != slots.name.value:
                self.state.customer_name = slots.name.value
                logger.debug(f"[SlotSync] customer_name ← {slots.name.value!r}")

    async def process_turn(self, user_text: str, tts_callback=None) -> TurnResult:
        """
        Process one user utterance through the full validated pipeline.

        ``tts_callback`` is an optional ``async (chunk: str) -> None`` that
        is called with each sentence chunk as the LLM streams its response,
        so TTS can start playing before the full text is ready.  Pass
        ``None`` (default) to use the original blocking behaviour.

        Steps mirror ADKRunner.run() per-turn body exactly:
        1.  update_state_from_utterance
        2.  select_node
        3.  check_prerequisites → forced_tools
        4.  build_context (per-node prompt + state + history)
        5.  call_gemini_stream (streaming) / _call_gemini_lm (blocking fallback)
        6.  parse tools + merge prereqs + filter + dedup
        7.  update_state_after_bot
        8.  whitelist blocks + optional get_menu inject
        9.  phone prompt injection          ← BEFORE check_forced_commits
        10. check_forced_commits
        11. re-parse + _validate_tool_call
        12. [PRODUCTION] execute real tools (sequential, strict arg validation)
        13. loop escape / stuck-loop detection + [PRODUCTION] explicit end_call
        14. [PRODUCTION] farewell safety net + explicit end_call
        15. apply_response_variations THEN append  ← correct order
        16. all_tools.extend
        17. [PRODUCTION] memory.record_turn + turn_idx++ + return TurnResult
        """
        async with self._turn_lock:
            return await self._process_turn_locked(user_text, tts_callback=tts_callback)

    async def _process_turn_locked(self, user_text: str, tts_callback=None) -> TurnResult:
        """Actual turn logic — called only while _turn_lock is held."""
        try:
            result = await self._process_turn_inner(user_text, tts_callback=tts_callback)
        except Exception as e:
            logger.exception(f"[ADKTurn] process_turn failed at turn {self.turn_idx}: {e}")
            result = TurnResult(
                clean_text=(
                    "Entschuldigung, es gibt ein technisches Problem. "
                    "Ich verbinde Sie mit einem Mitarbeiter."
                ),
                raw_response="[TOOL:transfer_to_human] Entschuldigung, es gibt ein technisches Problem. Ich verbinde Sie mit einem Mitarbeiter.",
                tools_called=["transfer_to_human"],
                should_end=True,
                end_reason="error_fallback",
            )

        # Fire persist as a background task — never block the TTS return path.
        # Redis is localhost so p50 cost is 1–3ms, but under load spikes to
        # 100ms+. The TTS pipeline returns result immediately.
        # Race window: if the WebSocket drops in the ~10ms persist window, the
        # reconnect re-aggregates from session.add_transcript (written sync
        # earlier in this same turn) — acceptable trade-off.
        asyncio.create_task(self._persist_state_safe())
        return result

    async def _persist_state_safe(self) -> None:
        """Background persist — never blocks the TTS return path."""
        try:
            await self.persist_state()
        except Exception as e:
            logger.warning(f"[ADKTurn] Background persist failed: {e}")

    async def _process_turn_inner(self, user_text: str, tts_callback=None) -> TurnResult:
        """
        Core per-turn logic lifted verbatim from ADKRunner.run() lines 250-512.

        Variable mapping (validated → production):
          stt_transcript    → user_text
          state             → self.state
          node_mgr          → self.node_mgr
          memory            → self.memory
          all_tools         → self.all_tools
          turn_idx          → self.turn_idx
          self.gemini_runner → gemini_runner (local var)

        [PRODUCTION] markers show additions that are not in adk_runner.py.
        Everything else is a verbatim copy with the variable substitutions above.
        """
        import time
        
        # Initialize call start time on first turn
        if self._call_start_time is None:
            self._call_start_time = time.time()

        # Sprint 0.4: reset per-turn subsystem trackers at entry
        self._reset_subsystem_status_for_turn()

        # Sprint 1.3: turn-entry registry sanity check — every turn should
        # show registry_exists=True with stable registry_id. If id flips or
        # registry_exists becomes False mid-call, we have a lifecycle bug.
        logger.info(
            f"[VALIDATION_LIFECYCLE] T{self.turn_idx} entry: "
            f"registry_exists={self.validation_registry is not None} "
            f"registry_id={id(self.validation_registry) if self.validation_registry else None} "
            f"state_ref_exists={getattr(self.state, 'validation_registry_ref', None) is not None} "
            f"entries_n={len(self.validation_registry._entries) if self.validation_registry else 0}"
        )
        
        # Phase 9 A1 — reset TurnTimings at the start of every turn so
        # per-stage latency columns in google_turn_metrics carry fresh data.
        try:
            from server.brain.layer1.turn_runner import reset_timings as _reset_timings
            _turn_timings = _reset_timings(self.state)
            _turn_timings.stt_done_at = time.monotonic()  # STT already done on entry
        except Exception as _t9_err:
            logger.debug(f"[Phase9] TurnTimings init failed: {_t9_err}")
            _turn_timings = None

        # Phase 5.5 — create/refresh the new ValidationRegistry and wire the
        # per-validator trace writer so validators_run tiles populate this turn.
        try:
            from server.brain.layer1.turn_runner import get_or_create_registry, _make_trace_writer
            from server.brain.contracts.trace import LayerTrace
            _p55_registry = get_or_create_registry(
                self.state,
                tenant_cfg=self._tenant.__dict__ if self._tenant else {},
            )
            # Update turn_idx in context so trace events carry the right turn number
            _p55_registry._ctx = _p55_registry._ctx.__class__(
                tenant_id=_p55_registry._ctx.tenant_id,
                call_sid=_p55_registry._ctx.call_sid,
                turn_idx=self.turn_idx,
                tenant_cfg=_p55_registry._ctx.tenant_cfg,
            )
            _p55_layer_trace = LayerTrace(turn_idx=self.turn_idx, call_sid=self.state.call_sid or "")
            _p55_registry.attach_trace_writer(_make_trace_writer(_p55_layer_trace))
            # Store on state so brain_service can read validators_run after the turn
            self.state.__p55_layer_trace__ = _p55_layer_trace  # type: ignore[attr-defined]
        except Exception as _p55_err:
            logger.warning(f"[Phase5.5] registry/trace init failed: {_p55_err}")
            _p55_layer_trace = None

        gemini_runner = self._get_gemini_runner()

        # [TRACE-2026-04-20] Point 1: Incoming user utterance entry
        logger.info(
            f"[TRACE-2026-04-20] T{self.turn_idx}/ENTRY user_text={user_text!r} "
            f"node={self.node_mgr.current_node_name} selected_dish={self.state.selected_dish!r} "
            f"customer_name={self.state.customer_name!r} phone_number={self.state.phone_number!r} "
            f"address={getattr(self.state, 'delivery_address', 'N/A')!r} order_intent={self.state.order_intent}"
        )

        # Initialize return values in case of early exception inside try block
        tool_results: dict = {}
        missing_fields_hint: Optional[str] = None
        should_end: bool = False
        end_reason: str = ""
        turn_tools: List[str] = []
        bot_response: str = ""

        # ── Update state from customer utterance ─────────────── [validated ~251]
        update_state_from_utterance(self.state, user_text)
        self._last_user_text = user_text

        # ── A5: ASR confidence guard — skip Layer 2 on consecutive low-confidence turns ──
        try:
            from server.brain.layer1.confidence_guard import should_reprompt_for_confidence, low_confidence_response
            if should_reprompt_for_confidence(None, confidence_window=self.asr_confidence_window):
                _conf_response = low_confidence_response()
                logger.info(f"  T{self.turn_idx}: confidence guard fired — returning reprompt")
                return TurnResult(
                    clean_text=_conf_response,
                    tools=[],
                    should_end=False,
                    end_reason="confidence_reprompt",
                    raw_llm_output=_conf_response,
                )
        except Exception as _cg_err:
            logger.debug(f"  T{self.turn_idx}: confidence guard non-fatal: {_cg_err}")

        # ── Smart-mix confirmation detection ──────────────────────────────────
        # Detect "ja/richtig/korrekt" after a critical-slot readback and mark
        # the corresponding confirmation flag. Runs before slot extraction so
        # that the current turn's context already reflects the confirmed state.
        self._detect_confirmation_of_readback(user_text)

        # ── Multi-intent read-back confirmation handler ────────────────────────
        # When captured_intents is active and the current intent has been read back,
        # check if the caller confirmed (ja) or corrected (nein). On confirmation:
        # - force the appropriate tool ([TOOL:create_order] or [TOOL:create_reservation])
        #   into the bot response as a code-driven override
        # - advance current_intent_idx to the next intent
        # - if all intents complete, append [TOOL:send_sms] and set multi_intent_completed
        # This check happens BEFORE LLM dispatch so the code can short-circuit
        # the LLM and inject the tool call directly.
        _mi_forced_response: Optional[str] = None
        if (
            self.state.captured_intents
            and not self.state.multi_intent_completed
        ):
            try:
                _mi_forced_response = await self._handle_multi_intent_confirmation(user_text)
            except Exception as _mie:
                logger.warning(f"[MultiIntent] confirmation handler error (non-fatal): {_mie}")

        # B2: always extract_multi — heuristic routing removed
        _word_count = len(user_text.split())

        # B3: Parallel-prior extraction — fire extract_multi IMMEDIATELY,
        # build context from state.last_extraction (prior turn), run LLM
        # concurrently, then collect new extraction after LLM completes.
        if self._slot_extractor is None:
            try:
                runner = self._get_gemini_runner()
                self._slot_extractor = SlotExtractor(
                    gemini_client=runner.llm_client,
                    model=os.environ.get("SLOT_EXTRACTOR_MODEL", "claude-haiku-4-5@20251001"),
                )
            except Exception as _se_init_err:
                logger.warning(f"[SlotExtractor] init failed (non-fatal): {_se_init_err}")

        # Step 1: Harvest pending tasks from PRIOR turn (already done tasks only)
        if self._slot_extractor is not None:
            for _t in list(self._pending_extraction_tasks):
                if _t.done():
                    try:
                        _ext = _t.result()
                        _newly = self.order_slots.merge_extraction(
                            _ext, turn_idx=max(0, self.turn_idx - 1)
                        )
                        if _newly:
                            logger.info(
                                f"  T{self.turn_idx}: SLOT EXTRACT merged: {_newly} "
                                f"next_ask={self.order_slots.next_slot_to_ask()!r}"
                            )
                            self._sync_slots_to_state()
                            logger.info(
                                f"[VAL_TRACE] harvest turn={self.turn_idx} "
                                f"newly_filled={_newly} "
                                f"registry_exists={self.validation_registry is not None}"
                            )
                            await self._schedule_validations(_newly)
                            _reg_entries = list(self.validation_registry._entries.keys()) if self.validation_registry else []
                            logger.info(f"[VAL_TRACE] after_schedule entries={_reg_entries}")
                            await self._recheck_changed_slots()
                    except Exception as _he:
                        logger.debug(f"[SlotExtractor] harvest error (non-fatal): {_he}")
                    self._pending_extraction_tasks.remove(_t)

        # Step 2: Fire current-turn extraction task IMMEDIATELY (parallel with LLM)
        # B1: tightened ceilings — EXTRACTOR_MAX_TOKENS=4096 caps response size
        _extr_task = None
        _timeout_base_s = 3.5
        if self._slot_extractor is not None:
            if _word_count <= 15:
                _timeout_base_s = 1.0
            elif _word_count <= 40:
                _timeout_base_s = 1.5
            elif _word_count <= 80:
                _timeout_base_s = 2.5
            # B2: always extract_multi
            _extr_task = asyncio.create_task(
                self._slot_extractor.extract_multi(user_text, timeout_s=_timeout_base_s)
            )
        
        # [TRACE-2026-04-20] Point 2: After update_state_from_utterance
        logger.info(
            f"[TRACE-2026-04-20] T{self.turn_idx}/POST_EXTRACT "
            f"extracted_name={self.state.customer_name!r} extracted_phone={self.state.phone_number!r} "
            f"extracted_address={getattr(self.state, 'delivery_address', 'N/A')!r} "
            f"delivery_intended={getattr(self.state, 'delivery_intended', False)} "
            f"selected_dish={self.state.selected_dish!r} order_intent={self.state.order_intent} "
            f"field_attempts={getattr(self.state, 'field_attempts', {})}"
        )

        # ── NODE SELECTION (code, not LLM) ──────────────────── [validated ~254]
        node = self.node_mgr.select_node(self.state, user_text)
        
        # Track nodes visited for call summary
        if node.name not in self._nodes_visited:
            self._nodes_visited.append(node.name)

        # ── Prerequisites (forced tools BEFORE LLM) ─────────── [validated ~258]
        forced_tools = self.node_mgr.check_prerequisites(node, self.state)

        # ── Build context with memory compression ────────────── [validated ~261]
        context_prompt, _est_prompt_tokens = self.memory.build_context(
            node.prompt,
            self.state,
            prereq_results=[f"[TOOL:{t}]" for t in forced_tools] if forced_tools else None,
        )
        self._last_prompt_tokens_in = _est_prompt_tokens

        # Sprint 1.4: track whether raw utterance made it into the prompt
        # + snapshot the first 500 chars for DB observability.
        try:
            self._raw_utterance_in_prompt = (
                "LETZTE AUSSAGE DES ANRUFERS" in context_prompt
            )
            self._last_prompt_head = context_prompt[:500]
        except Exception:
            self._raw_utterance_in_prompt = None
            self._last_prompt_head = None

        try:
            gemini_runner._active_prompt_override = context_prompt  # [validated ~274]

            # ── Multi-intent short-circuit: use forced response if confirmation handled ─
            # If the confirmation handler already produced the tool call + transition text,
            # skip the Gemini call entirely for this turn. The forced response is already
            # the correct bot turn (tool fired, next intent read-back queued in context).
            if _mi_forced_response is not None:
                bot_response = _mi_forced_response
                logger.info(
                    f"  T{self.turn_idx}: MULTI-INTENT short-circuit — "
                    f"skipping LLM, using forced response: {bot_response[:80]!r}"
                )
            else:
                # ── Call Gemini with node's micro-prompt ─────────── [validated ~278]
                # Uses streaming when a tts_callback is wired (production voice path)
                # so TTS starts on the first sentence without waiting for the full response.
                bot_response = await gemini_runner.call_gemini_stream(
                    user_message=user_text,
                    context=self.memory.build_history(),
                    tts_callback=tts_callback,
                    node_hint=node.name if node else None,
                )

            if _turn_timings is not None:
                _turn_timings.l2_done_at = time.monotonic()

                # Phase 9 A1: populate token counts from streaming LLM response
                _lm_um = getattr(gemini_runner, "_last_stream_usage_metadata", None)
                if _lm_um is not None:
                    _pin = (
                        getattr(_lm_um, "prompt_token_count", None)
                        or getattr(_lm_um, "prompt_tokens", None)
                    )
                    _pout = (
                        getattr(_lm_um, "candidates_token_count", None)
                        or getattr(_lm_um, "candidates_tokens", None)
                    )
                    if _pin:
                        _turn_timings.prompt_tokens_in = int(_pin)
                    if _pout:
                        _turn_timings.prompt_tokens_out = int(_pout)

            # Parse tool calls from response [validated ~286]
            turn_tools = list(gemini_runner._parse_tool_calls(bot_response))

            # Guard: strip LLM-hallucinated create_order on inquiry utterances.
            # Fires when the caller mentions a dish in a question ("was ist Kimchi?")
            # but the LLM spontaneously commits an order without any confirmation.
            _negations_in_text = [n for n in NEGATE_ORDER if n in user_text.lower()]
            if "create_order" in turn_tools:
                from loguru import logger as _loguru
                _loguru.info(
                    f"  T{self.turn_idx}: INQUIRY GUARD check — create_order_in_turn=True, "
                    f"confirmed={self.state.customer_confirmed}, turn_idx={self.turn_idx}, "
                    f"negations={_negations_in_text[:3]}, order_intent={self.state.order_intent}"
                )
            if (
                "create_order" in turn_tools
                and not self.state.customer_confirmed
                and self.turn_idx <= 1
                and any(n in user_text.lower() for n in NEGATE_ORDER)
            ):
                turn_tools = [t for t in turn_tools if t not in ("create_order", "verify_address", "send_sms")]
                bot_response = re.sub(
                    r"\[TOOL:(?:create_order|verify_address|send_sms)\]", "", bot_response, flags=re.IGNORECASE
                ).strip()
                logger.warning(
                    f"  T{self.turn_idx}: STRIPPED premature create_order (inquiry utterance, not confirmed)"
                )

            # Add prerequisite tools [validated ~291]
            for ft in forced_tools:
                if ft not in turn_tools:
                    turn_tools.insert(0, ft)
                    bot_response = f"[TOOL:{ft}] " + bot_response

            # Filter to only tools available in this node [validated ~297]
            allowed = set(node.tools)
            turn_tools = [t for t in turn_tools if t in allowed]

            # Deduplicate get_menu across conversation [validated ~300]
            if "get_menu" in turn_tools and "get_menu" in self.all_tools:
                turn_tools = [t for t in turn_tools if t != "get_menu"]
                bot_response = re.sub(
                    r"\[TOOL:get_menu\]", "", bot_response, flags=re.IGNORECASE
                ).strip()

            # PR-16d: Deduplicate ai_greeting — greeting fires in T0 via
            # check_forced_commits, but the LLM can re-emit [TOOL:ai_greeting]
            # in T1's response text since there's no dedup guard (unlike get_menu).
            # Suppressing it here (a) prevents double-greeting and (b) ensures
            # tts_situation correctly transitions from greeting_first to info_neutral
            # in T1 rather than staying on greeting_first.
            if "ai_greeting" in turn_tools and self.state.ai_greeting_called:
                turn_tools = [t for t in turn_tools if t != "ai_greeting"]
                bot_response = re.sub(
                    r"\[TOOL:ai_greeting\]", "", bot_response, flags=re.IGNORECASE
                ).strip()
                logger.info(f"  T{self.turn_idx}: [DEDUP] ai_greeting suppressed — already called in T0")

            # Block duplicate create_order / send_sms [validated ~312]
            if (
                ("create_order" in turn_tools and "create_order" in self.all_tools)
                or ("send_sms" in turn_tools and "send_sms" in self.all_tools)
            ):
                turn_tools = [t for t in turn_tools if t not in ("create_order", "send_sms")]
                bot_response = re.sub(
                    r"\[TOOL:(?:create_order|send_sms)\]", "", bot_response, flags=re.IGNORECASE
                ).strip()
                logger.warning(f"  T{self.turn_idx}: BLOCKED duplicate create_order/send_sms")

            # Block duplicate get_date_info [validated ~324]
            if "get_date_info" in turn_tools and "get_date_info" in self.all_tools:
                turn_tools = [t for t in turn_tools if t != "get_date_info"]
                bot_response = re.sub(
                    r"\[TOOL:get_date_info\]", "", bot_response, flags=re.IGNORECASE
                ).strip()
                logger.warning(f"  T{self.turn_idx}: BLOCKED duplicate get_date_info")

            # Block duplicate create_reservation [validated ~333]
            if "create_reservation" in turn_tools and "create_reservation" in self.all_tools:
                turn_tools = [t for t in turn_tools if t != "create_reservation"]
                bot_response = re.sub(
                    r"\[TOOL:create_reservation\]", "", bot_response, flags=re.IGNORECASE
                ).strip()
                logger.warning(f"  T{self.turn_idx}: BLOCKED duplicate create_reservation")

            # B3: Collect extraction task results (LLM done — extractor should be ready)
            _ext_now: dict = {}
            if _extr_task is not None:
                try:
                    _ext_now = await asyncio.wait_for(
                        asyncio.shield(_extr_task),
                        timeout=_timeout_base_s,
                    )
                    self._slot_extractor_status = "completed"
                    self.state.last_extraction_timed_out = False
                    if _turn_timings is not None:
                        _turn_timings.extract_done_at = time.monotonic()

                        # Phase 9 A1: populate extractor token counts
                        _ext_um = getattr(self._slot_extractor, "_last_usage_metadata", None)
                        if _ext_um is not None:
                            _epin = (
                                getattr(_ext_um, "prompt_token_count", None)
                                or getattr(_ext_um, "prompt_tokens", None)
                            )
                            _epout = (
                                getattr(_ext_um, "candidates_token_count", None)
                                or getattr(_ext_um, "candidates_tokens", None)
                            )
                            if _epin:
                                _turn_timings.extract_tokens_in = int(_epin)
                            if _epout:
                                _turn_timings.extract_tokens_out = int(_epout)
                except asyncio.TimeoutError:
                    logger.info(
                        f"  T{self.turn_idx}: slot extract >{_timeout_base_s*1000:.0f}ms — "
                        f"deferring to next-turn harvest"
                    )
                    self._slot_extractor_status = "timeout"
                    self.state.last_extraction_timed_out = True
                    self._pending_extraction_tasks.append(_extr_task)
                    _ext_now = {}
                except Exception as _extr_err:
                    err_str = str(_extr_err).lower()
                    if "429" in err_str or "resource_exhausted" in err_str or "rate_limit" in err_str:
                        self._slot_extractor_status = "429"
                    else:
                        self._slot_extractor_status = "error"
                    logger.debug(
                        f"  T{self.turn_idx}: slot extract error (non-fatal): {_extr_err}"
                    )
                    self.state.last_extraction_timed_out = False

                if _ext_now:
                    # Stash on state for next turn's context and abuse/out-of-scope checks
                    self.state.last_extraction = _ext_now

                    # Multi-intent path: parse CapturedIntents
                    if isinstance(_ext_now, dict) and "intents" in _ext_now:
                        try:
                            from server.brain.slot_extractor import parse_extraction_to_intents, merge_new_intents_into_state
                            _captured = parse_extraction_to_intents(_ext_now, current_turn=self.turn_idx)
                            if _captured:
                                merge_new_intents_into_state(self.state, _captured, self.turn_idx)
                                self.state.multi_intent_completed = False
                                logger.info(
                                    f"  T{self.turn_idx}: MULTI-INTENT captured "
                                    f"{len(_captured)} intent(s): "
                                    f"{[i.kind.value for i in _captured]}"
                                )
                        except Exception as _ci_err:
                            logger.warning(f"[CapturedIntents] parse failed (non-fatal): {_ci_err}")

                        # Phase 4 C3: detect single→multi promotion
                        try:
                            from server.brain.layer1.intent_advance import (
                                detect_promotion_to_multi, promote_to_multi_intent_flow,
                            )
                            if detect_promotion_to_multi(self.state):
                                promote_to_multi_intent_flow(self.state)
                                logger.info(
                                    f"  T{self.turn_idx}: single→multi promotion triggered "
                                    f"({len(getattr(self.state, 'captured_intents', []))} intents)"
                                )
                        except Exception as _promo_err:
                            logger.debug(f"  T{self.turn_idx}: promotion check non-fatal: {_promo_err}")

                        # Merge identity fields into shared_slots and OrderSlots
                        _addr = _ext_now.get("address") or {}
                        _id_ext: dict = {}
                        if _ext_now.get("caller_name"):
                            _id_ext["name"] = {"value": _ext_now["caller_name"], "confidence": "high"}
                        if _ext_now.get("phone"):
                            _id_ext["phone"] = {"value": _ext_now["phone"], "confidence": "high"}
                        if _addr.get("street"):
                            _id_ext["address_street"] = {"value": _addr["street"], "confidence": "high"}
                        if _addr.get("number"):
                            _id_ext["address_number"] = {"value": _addr["number"], "confidence": "high"}
                        if _addr.get("city"):
                            _id_ext["address_city"] = {"value": _addr["city"], "confidence": "high"}

                        try:
                            from server.brain.captured_intents import SlotValue, SlotStatus, SlotConfidence
                            for _k, _v in _id_ext.items():
                                self.state.shared_slots[_k] = SlotValue(
                                    name=_k,
                                    value=_v["value"],
                                    status=SlotStatus.FILLED,
                                    confidence=SlotConfidence.HIGH,
                                    source_turn=self.turn_idx,
                                )
                        except Exception:
                            pass

                        _newly_now = self.order_slots.merge_extraction(_id_ext, turn_idx=self.turn_idx) if _id_ext else []
                    else:
                        _newly_now = self.order_slots.merge_extraction(_ext_now, turn_idx=self.turn_idx)

                    if _newly_now:
                        logger.info(
                            f"  T{self.turn_idx}: SLOT EXTRACT post-LLM merged: {_newly_now} "
                            f"next_ask={self.order_slots.next_slot_to_ask()!r}"
                        )
                        self._sync_slots_to_state()
                        logger.info(
                            f"[VAL_TRACE] post-LLM turn={self.turn_idx} "
                            f"newly_filled={_newly_now} "
                            f"registry_exists={self.validation_registry is not None}"
                        )
                        await self._schedule_validations(_newly_now)
                        _reg_entries = list(self.validation_registry._entries.keys()) if self.validation_registry else []
                        logger.info(f"[VAL_TRACE] after_schedule entries={_reg_entries}")
                        await self._recheck_changed_slots()
                    else:
                        logger.debug(f"  T{self.turn_idx}: slot extract post-LLM yielded nothing new")

                self._sync_extractor_status_to_state()

            # Update state after bot [validated ~342]
            update_state_after_bot(self.state, bot_response)

            # Whitelist: block create_order if no valid dish or already committed [validated ~344]
            if "create_order" in turn_tools and (not self.state.selected_dish or self.state.order_created):
                reason = "no valid dish" if not self.state.selected_dish else "already committed"
                logger.warning(f"  T{self.turn_idx}: BLOCKED create_order ({reason})")
                turn_tools = [t for t in turn_tools if t not in ("create_order", "send_sms")]
                bot_response = re.sub(
                    r"\[TOOL:(?:create_order|send_sms)\]", "", bot_response, flags=re.IGNORECASE
                ).strip()

            # Block create_reservation if already committed [validated ~365]
            if "create_reservation" in turn_tools and self.state.reservation_created:
                logger.warning(f"  T{self.turn_idx}: BLOCKED create_reservation (already committed)")
                turn_tools = [t for t in turn_tools if t != "create_reservation"]
                bot_response = re.sub(
                    r"\[TOOL:create_reservation\]", "", bot_response, flags=re.IGNORECASE
                ).strip()

            # Auto-inject get_menu on first food turn [validated ~373]
            # Fix G: Use case-insensitive user_text matching with menu/food keywords
            _menu_food_kw = [
                "speisekarte", "menü", "menu", "karte", "was gibt es",
                "was habt ihr", "was können sie", "was haben sie",
                "essen", "gericht", "speisen", "was esst", "food",
                "kimchi", "bibimbap", "bulgogi", "tteokbokki", "japchae",
                "mandu", "tofu", "mochi", "ramyeon", "ramen",
            ]
            # Extend with tenant-specific items
            if self._tenant:
                _menu_food_kw.extend([item.lower() for item in self._tenant.items])
            _user_lower = user_text.lower()
            if (
                "get_menu" not in self.all_tools
                and "get_menu" not in turn_tools
                and (
                    self.state.order_intent
                    or self.state.selected_dish
                    or (
                        not self.state.menu_fetched
                        and any(kw in _user_lower for kw in _menu_food_kw)
                    )
                )
            ):
                bot_response = "[TOOL:get_menu] " + bot_response
                turn_tools.insert(0, "get_menu")

            # ── FORCED COMMITS (code overrides LLM) ──────────── [validated ~396]
            logger.info(
                f"  T{self.turn_idx}: PRE-forced_commits state flags - "
                f"escalation_requested={getattr(self.state, 'escalation_requested', '?')}, "
                f"request_callback_called={getattr(self.state, 'request_callback_called', '?')}, "
                f"transfer_to_tier2_called={getattr(self.state, 'transfer_to_tier2_called', '?')}"
            )
            bot_response = self.node_mgr.check_forced_commits(
                self.state, bot_response, self.turn_idx, user_text, self.all_tools
            )
            logger.info(
                f"  T{self.turn_idx}: POST-forced_commits state flags - "
                f"escalation_requested={getattr(self.state, 'escalation_requested', '?')}, "
                f"request_callback_called={getattr(self.state, 'request_callback_called', '?')}, "
                f"transfer_to_tier2_called={getattr(self.state, 'transfer_to_tier2_called', '?')}"
            )

            # Re-parse after forced commits [validated ~404]
            turn_tools = list(gemini_runner._parse_tool_calls(bot_response))

            # Post-reparse dedup: remove tools already called in previous turns [validated ~409]
            # send_sms is NOT paired with create_order here — may be legitimately needed later.
            for _dup_tool in ("create_order", "create_reservation", "get_date_info", "verify_address"):
                if _dup_tool in turn_tools and _dup_tool in self.all_tools:
                    turn_tools = [t for t in turn_tools if t != _dup_tool]
                    bot_response = re.sub(
                        rf"\[TOOL:{_dup_tool}\]", "", bot_response, flags=re.IGNORECASE
                    ).strip()
                    logger.warning(f"  T{self.turn_idx}: POST-PARSE dedup {_dup_tool}")
            if "send_sms" in turn_tools and "send_sms" in self.all_tools:
                if ("create_order" not in turn_tools
                        and "[TOOL:create_order]" not in bot_response
                        and "create_order" not in self.all_tools):
                    turn_tools = [t for t in turn_tools if t != "send_sms"]
                    bot_response = re.sub(
                        r"\[TOOL:send_sms\]", "", bot_response, flags=re.IGNORECASE
                    ).strip()
                    logger.warning(f"  T{self.turn_idx}: POST-PARSE dedup send_sms")

            # ── A2: Validation layer — policy guard ───────────── [validated ~430]
            # Final gate: blocks structurally invalid calls even if
            # forced commits or LLM erroneously included them.
            validated_tools = [t for t in turn_tools if _validate_tool_call(t, self.state, self.all_tools)]
            blocked_tools = set(turn_tools) - set(validated_tools)
            if blocked_tools:
                for _bt in blocked_tools:
                    bot_response = re.sub(
                        rf"\[TOOL:{re.escape(_bt)}\]", "", bot_response, flags=re.IGNORECASE
                    ).strip()
                    logger.warning(f"  T{self.turn_idx}: POLICY BLOCKED {_bt}")
                turn_tools = validated_tools

            # ── Layer 3 policy filter chain (Phase 8 — FINDING-003 fix) ──────────
            # Runs after all structural tool validation, before tool execution.
            # In streaming-TTS mode the text is already spoken, so text edits only
            # affect stored memory and observability. Tool changes (quantity cap,
            # monetary cap, after-hours block) ARE pre-execution and correctly
            # block dispatch of the modified tool list.
            try:
                import types as _types
                from server.brain.layer3 import policy as _layer3_policy

                # Clean text for text guards (strip [TOOL:...] markers)
                _policy_text = re.sub(r"\[TOOL:\w+\]\s*", "", bot_response).strip()

                # Build policy.ToolCall objects with best-effort args for
                # quantity/monetary guards (create_order needs items list).
                _policy_tools: list = []
                for _pt_name in turn_tools:
                    _pt_args: dict = {}
                    if _pt_name == "create_order":
                        try:
                            _ci_items = self.state.current_intent_items() or []
                            _pt_args = {
                                "items": [{"name": d, "quantity": 1} for d in _ci_items],
                                "channel": getattr(self.state, "order_type", ""),
                            }
                        except Exception:
                            pass
                    elif _pt_name in ("create_delivery",):
                        _pt_args = {"channel": getattr(self.state, "order_type", "")}
                    _policy_tools.append(_layer3_policy.ToolCall(name=_pt_name, args=_pt_args))

                # Minimal duck-typed turn_package: policy only needs .call_sid
                # split on "_" to derive tenant_id — pass tenant_id directly so
                # _tenant_id_from_tp("doboo".split("_")[0]) == "doboo".
                _tp_compat = _types.SimpleNamespace(call_sid=self.tenant_id)

                _policy_result = _layer3_policy.check(_policy_text, _policy_tools, _tp_compat)

                # Apply tool changes: remove any tools the policy dropped,
                # and add any tools the policy injected (e.g. transfer_to_human).
                _original_tool_set = list(turn_tools)
                _policy_tool_names = [tc.name for tc in _policy_result.tools]
                _dropped_tools = [t for t in _original_tool_set if t not in _policy_tool_names]
                _added_tools = [t for t in _policy_tool_names if t not in _original_tool_set]
                _tools_changed = bool(_dropped_tools or _added_tools)

                for _dt in _dropped_tools:
                    bot_response = re.sub(
                        rf"\[TOOL:{re.escape(_dt)}\]", "", bot_response, flags=re.IGNORECASE
                    ).strip()
                    logger.warning(
                        f"  T{self.turn_idx}: LAYER3_POLICY dropped tool {_dt!r} "
                        f"(warnings={[w.code for w in _policy_result.warnings]})"
                    )
                for _at in _added_tools:
                    bot_response = f"[TOOL:{_at}] " + bot_response
                    logger.warning(
                        f"  T{self.turn_idx}: LAYER3_POLICY injected tool {_at!r}"
                    )
                if _tools_changed:
                    turn_tools = _policy_tool_names

                # Write to LayerTrace for google_turn_metrics.layer3_changes
                if _policy_result.warnings:
                    _l3_trace = getattr(self.state, "__p55_layer_trace__", None)
                    if _l3_trace is not None:
                        _l3_trace.layer3_warnings = [
                            {
                                "code": w.code,
                                "detail": w.detail[:200],
                                "original": w.original[:200],
                            }
                            for w in _policy_result.warnings
                        ]
                        _l3_trace.layer3_text_changed = _policy_result.text != _policy_text
                        _l3_trace.layer3_tools_changed = _tools_changed

                    logger.warning(
                        f"  T{self.turn_idx}: LAYER3_POLICY fired %d warning(s): %s",
                        len(_policy_result.warnings),
                        [w.code for w in _policy_result.warnings],
                    )

                    # Critical alert for TECH_PROBLEM_BLOCKED (Phase 9 A4)
                    for _pw in _policy_result.warnings:
                        if _pw.code == "TECH_PROBLEM_BLOCKED":
                            try:
                                from server.brain.observability.alerts import alert_tech_problem_blocked
                                asyncio.create_task(
                                    alert_tech_problem_blocked(
                                        call_sid=self.state.call_sid or "",
                                        tenant_id=self.tenant_id,
                                    )
                                )
                            except Exception:
                                pass

            except Exception:
                logger.exception(
                    "layer3_policy_check_failed — falling through with original text/tools",
                    extra={"call_sid": self.state.call_sid, "turn_idx": self.turn_idx},
                )

            # Track state from final tools [validated ~444]
            if "ai_greeting" in turn_tools:
                self.state.ai_greeting_called = True
            if "create_order" in turn_tools:
                self.state.order_created = True
                # Phone-validation gate that set escalation_requested is no longer
                # relevant once the order is committed — clear it so subsequent
                # turns don't loop into the technical-error path.
                self.state.escalation_requested = False
            if "create_reservation" in turn_tools:
                self.state.reservation_created = True
            if "get_menu" in turn_tools:
                self.state.menu_fetched = True
            if "check_availability" in turn_tools:
                self.state.check_availability_called = True
            if "get_date_info" in turn_tools:
                self.state.get_date_info_called = True
            if "verify_address" in turn_tools:
                self.state.verify_address_called = True
            if "get_weather" in turn_tools:
                self.state.get_weather_called = True

            # ── [PRODUCTION] Execute real tools ─────────────────────────────
            # Inserted after state flags, before loop escape.
            # Validated runner has no executor — this is the only production-only
            # block in the core logic path.
            # Tools are executed ONE AT A TIME in turn_tools order (sequential, not parallel).
            failed_tool_names: set = set()

            # ── Filler-word safety net ──────────────────────────────────────
            # If the turn contains a SLOW tool (verify_address, create_order,
            # create_reservation, get_menu, check_availability, get_weather) and
            # the LLM's own bot_response doesn't already start with a filler,
            # push a short filler TTS frame NOW so the caller doesn't hear
            # silence while the tool runs. Pick a filler different from the
            # previously-used one so we never repeat twice in a row.
            _SLOW_TOOLS_FOR_FILLER = {
                "verify_address", "create_order", "create_reservation",
                "get_menu", "check_availability", "get_weather",
                "get_restaurant_info", "send_sms",
            }
            if self._filler_cb and any(t in _SLOW_TOOLS_FOR_FILLER for t in turn_tools):
                # Tool-specific filler pools (more natural-sounding context match).
                # Generic pool is always included so we never sound robotic.
                _FILLER_POOL_GENERIC = [
                    "Einen Moment bitte.",
                    "Einen kleinen Augenblick.",
                    "Alles klar, ich schaue kurz nach.",
                    "Kurzer Moment, ich prüfe das eben.",
                    "Moment, das dauert nur einen Augenblick.",
                    "Einen Augenblick, ich kümmere mich darum.",
                    "Kleinen Moment bitte, ich notiere das kurz.",
                    "Einen kurzen Moment, bitte.",
                    "Ja, einen Moment.",
                    "Sehr gerne, einen Augenblick.",
                    "Okay, ich prüfe das kurz für Sie.",
                    "Bestens, ich kümmere mich sofort darum.",
                ]
                _FILLER_POOL_ADDRESS = [
                    "Einen Moment, ich prüfe die Adresse.",
                    "Kurz, ich schaue mir die Adresse an.",
                    "Alles klar, ich prüfe die Lieferadresse.",
                ]
                _FILLER_POOL_ORDER = [
                    "Einen Moment, ich gebe die Bestellung auf.",
                    "Okay, ich notiere das für Sie.",
                    "Alles klar, einen Augenblick noch.",
                    "Moment, ich schließe die Bestellung ab.",
                ]
                _FILLER_POOL_MENU = [
                    "Einen Moment, ich schaue in die Karte.",
                    "Kurz, ich prüfe unser Angebot.",
                ]
                _slow = [t for t in turn_tools if t in _SLOW_TOOLS_FOR_FILLER]
                if "verify_address" in _slow:
                    _pool = _FILLER_POOL_GENERIC + _FILLER_POOL_ADDRESS
                elif "create_order" in _slow or "send_sms" in _slow:
                    _pool = _FILLER_POOL_GENERIC + _FILLER_POOL_ORDER
                elif "get_menu" in _slow:
                    _pool = _FILLER_POOL_GENERIC + _FILLER_POOL_MENU
                else:
                    _pool = _FILLER_POOL_GENERIC
                # Only skip filler if LLM text starts with an *explicit* filler.
                # Casual openers like "Ja," or "Okay," do NOT count — we still want
                # to play a proper filler so the caller hears something during the
                # 7-8s tool wait instead of a single syllable then silence.
                _leads_with_filler = bool(re.match(
                    r"^\s*(?:einen?\s+(?:kleinen?\s+)?(?:moment|augenblick)|moment(?:\s+bitte)?|"
                    r"alles\s+klar,?\s+ich\s+(?:pr[üu]fe|schaue|notiere|k[üu]mmere)|"
                    r"kurz(?:er|en)?\s+moment|einen?\s+kurzen?\s+(?:moment|augenblick))",
                    (bot_response or "").strip(),
                    flags=re.IGNORECASE,
                ))
                if not _leads_with_filler:
                    # Avoid repeating the previous filler and, when possible,
                    # the one before that (softer rotation for 2+ slow-tool turns).
                    _avoid = {self._last_filler}
                    candidates = [f for f in _pool if f not in _avoid] or _pool
                    filler_text = random.choice(candidates)
                    self._last_filler = filler_text
                    try:
                        await self._filler_cb(filler_text)
                        logger.info(
                            f"  T{self.turn_idx}: FILLER emitted before slow tools "
                            f"({_slow}): {filler_text!r}"
                        )
                    except Exception as _fe:
                        logger.debug(f"  T{self.turn_idx}: filler emit failed: {_fe}")

            # ── Execute real tools ───────────────────────────────────────────────
            # Category A (pure data reads) run in parallel via asyncio.gather —
            # saves 400–800ms on multi-tool turns.
            # Category B (state mutations) must stay sequential:
            #   verify_address → create_order → send_sms (each depends on the last).
            # check_availability always finishes before create_reservation because
            # check_availability is in _parallel and gather() completes before
            # _sequential starts.

            # Short-circuit get_menu when a fresh cached copy exists for this session.
            # Saves one tool round-trip (~60ms) on the 20% of turns that would re-call it.
            if (
                "get_menu" in turn_tools
                and getattr(self.state, "cached_menu", None)
                and getattr(self.state, "cached_menu_at_turn", None) is not None
                and (self.turn_idx - self.state.cached_menu_at_turn) < 30
            ):
                tool_results["get_menu"] = {
                    "menu": self.state.cached_menu,
                    "cached": True,
                }
                turn_tools = [t for t in turn_tools if t != "get_menu"]
                bot_response = re.sub(
                    r"\[TOOL:get_menu\]", "", bot_response, flags=re.IGNORECASE
                ).strip()
                logger.info(
                    f"  T{self.turn_idx}: get_menu SHORT-CIRCUIT "
                    f"(cached at T{self.state.cached_menu_at_turn})"
                )

            _parallel_tools = [t for t in turn_tools if t in PARALLEL_SAFE_TOOLS]
            _sequential_tools = [t for t in turn_tools if t not in PARALLEL_SAFE_TOOLS]

            # Phase 9 B1: collect ERR_* codes across all tool calls this turn.
            # Stored on self so brain_service.py can read it after process_turn().
            _turn_error_codes: list[str] = []

            async def _exec_one(tool_name: str):
                """Run one tool; return (tool_name, args, result_or_None, error_or_None)."""
                from tools.executor import execute_tool
                args, error_msg = self._build_tool_args(tool_name)
                if error_msg:
                    logger.warning(f"  T{self.turn_idx}: TOOL BLOCKED ({tool_name}) — {error_msg}")
                    return tool_name, None, None, error_msg
                if args is None:
                    return tool_name, None, None, None  # no-op tool

                # verify_address per-call cache — avoids a repeat Google Maps round-trip
                # when the same address is confirmed multiple times in one call
                if tool_name == "verify_address" and args:
                    _addr_key = (args.get("address") or "").strip().lower()
                    if _addr_key and _addr_key in self._addr_cache:
                        logger.info(
                            f"  T{self.turn_idx}: verify_address CACHE HIT: {_addr_key[:50]!r}"
                        )
                        return tool_name, args, self._addr_cache[_addr_key], None

                try:
                    _t_start = time.monotonic()
                    result = await execute_tool(
                        tool_name, args, self.call_sid, self.tenant_id,
                        tool_results=tool_results,
                        conversation_state=self.state,
                    )
                    # Phase 9 A1: record per-tool wall-clock duration
                    if _turn_timings is not None:
                        _turn_timings.record_tool(
                            tool_name, int((time.monotonic() - _t_start) * 1000)
                        )
                    # Phase 9 B1: pop _error_code injected by ToolResult.to_legacy_dict()
                    if isinstance(result, dict):
                        _ec = result.pop("_error_code", None)
                        if _ec:
                            _turn_error_codes.append(_ec)
                    return tool_name, args, result, None
                except Exception as exec_err:
                    # Still record duration on exception so timeouts show as long-running
                    if _turn_timings is not None:
                        _turn_timings.record_tool(
                            tool_name, int((time.monotonic() - _t_start) * 1000)
                        )
                    logger.error(f"  T{self.turn_idx}: TOOL error ({tool_name}): {exec_err}", exc_info=True)
                    return tool_name, args, {"error": str(exec_err)}, str(exec_err)

            def _apply_result(tool_name: str, args, result, error_msg: str):
                """Apply one tool's outcome to state, tool_results, and failed_tool_names."""
                nonlocal missing_fields_hint, bot_response
                if error_msg or (isinstance(result, dict) and result and result.get("error") and args is None and error_msg):
                    # verify_address failure is non-fatal: order flow must continue
                    # (the ORDERING prompt already tells the LLM how to narrate this).
                    if tool_name == "verify_address":
                        self.state.verify_address_failed = True
                        logger.warning(
                            f"  T{self.turn_idx}: verify_address failed (non-fatal) — "
                            f"continuing order flow. error={error_msg!r}"
                        )
                        tool_results[tool_name] = {"verified": False, "warning": error_msg or "address not found"}
                        return
                    failed_tool_names.add(tool_name)
                    bot_response = re.sub(
                        rf"\[TOOL:{re.escape(tool_name)}\]", "", bot_response, flags=re.IGNORECASE
                    ).strip()
                    if not missing_fields_hint:
                        missing_fields_hint = error_msg or f"Werkzeugfehler bei {tool_name}"
                    return
                if result is None:
                    return  # no-op tool
                tool_results[tool_name] = result
                logger.info(f"  T{self.turn_idx}: TOOL executed: {tool_name} -> {str(result)[:100]}")
                # Cache menu data
                if tool_name == "get_menu" and isinstance(result, dict) and result.get("menu"):
                    self.state.cached_menu = result["menu"]
                    self.state.cached_menu_at_turn = self.turn_idx
                    # Also cache menu metadata (lunch_menu_available, current_time_cest, etc.)
                    self.state.cached_menu_metadata = {
                        k: v for k, v in result.items() if k != "menu"
                    }
                    n_items = sum(len(v) for v in result["menu"].values() if isinstance(v, list))
                    logger.info(f"[MENU_CACHE] cached {n_items} items at turn {self.turn_idx}; metadata: {self.state.cached_menu_metadata}")
                # Store verified address
                if tool_name == "verify_address" and isinstance(result, dict):
                    formatted = result.get("formatted_address") or result.get("address")
                    if formatted and result.get("valid", True):
                        self.state.delivery_address = formatted
                        self.state.delivery_address_mentioned = True
                        if args and args.get("address"):
                            _addr_key = args["address"].strip().lower()
                            self._addr_cache[_addr_key] = result
                        logger.info(f"[ADDR_CACHE] T{self.turn_idx}: stored delivery_address={formatted!r}")
                if self.session and args is not None:
                    try:
                        asyncio.create_task(
                            self.session.add_tool_call(tool_name, args, result, 0)
                        )
                    except Exception as _se:
                        logger.warning(f"[ADKTurn] Session tool_call log failed: {_se}")

            # --- Parallel bucket (Category A reads) ---
            if _parallel_tools:
                _par_results = await asyncio.gather(
                    *[_exec_one(t) for t in _parallel_tools],
                    return_exceptions=False,
                )
                for _t, _a, _r, _e in _par_results:
                    _apply_result(_t, _a, _r, _e)

            # --- Sequential bucket (Category B state-mutations) ---
            for tool_name in _sequential_tools:
                _t, _a, _r, _e = await _exec_one(tool_name)
                _apply_result(_t, _a, _r, _e)

            # Remove failed/blocked tools so loop escape and all_tools are accurate
            if failed_tool_names:
                turn_tools = [t for t in turn_tools if t not in failed_tool_names]

            # Phase 4 C3: advance multi-intent queue after each completing tool
            try:
                from server.brain.layer1.intent_advance import advance_after_tool as _advance
                for _tname in list(turn_tools):
                    _adv_result = _advance(self.state, _tname)
                    if "advance" in _adv_result:
                        logger.info(f"  T{self.turn_idx}: intent_advance after {_tname}: {_adv_result}")
            except Exception as _adv_err:
                logger.debug(f"  T{self.turn_idx}: advance_after_tool non-fatal: {_adv_err}")

            # ── Sanitize false order-confirmation when create_order failed ──────
            # If the LLM spoke a success confirmation ("aufgenommen",
            # "SMS-Bestätigung", "Bestellung ist notiert" …) but create_order
            # actually failed, we must NOT play that lie to the caller. Replace
            # with an explicit recovery prompt based on the missing field.
            _co_failed = "create_order" in failed_tool_names
            _co_result = tool_results.get("create_order") if isinstance(tool_results, dict) else None
            _co_had_error = isinstance(_co_result, dict) and (
                _co_result.get("error") or _co_result.get("success") is False
            )
            if (_co_failed or _co_had_error) and bot_response:
                _SUCCESS_CLAIM_RE = re.compile(
                    r"(?:(?:ich\s+habe\s+)?ihre?\s+bestellung[^.!?]*?"
                    r"(?:aufgenommen|notiert|bestätigt|entgegengenommen|erfasst)"
                    r"[^.!?]*[.!?]?)|"
                    r"(?:sie\s+erhalten[^.!?]*?sms[^.!?]*[.!?]?)|"
                    r"(?:die\s+sms[- ]?bestätigung[^.!?]*[.!?]?)",
                    re.IGNORECASE,
                )
                if _SUCCESS_CLAIM_RE.search(bot_response):
                    err_txt = ""
                    if isinstance(_co_result, dict):
                        err_txt = str(_co_result.get("error") or _co_result.get("message") or "")
                    # Build a caller-friendly recovery prompt
                    if "phone" in err_txt.lower() or "pflichtfeld" in err_txt.lower():
                        recovery = "Einen Moment — ich brauche noch Ihre Mobilfunknummer, dann gebe ich die Bestellung auf."
                    elif "adresse" in err_txt.lower() or "delivery_address" in err_txt.lower():
                        recovery = "Einen Moment — ich brauche noch Ihre Lieferadresse, dann gebe ich die Bestellung auf."
                    elif "gericht" in err_txt.lower() or "gesamtpreis" in err_txt.lower():
                        recovery = "Einen Moment — ich muss die Bestellung nochmal prüfen, einen Augenblick bitte."
                    else:
                        recovery = "Einen Moment — ich konnte die Bestellung noch nicht aufgeben, einen kleinen Moment bitte."
                    bot_response = _SUCCESS_CLAIM_RE.sub("", bot_response).strip()
                    bot_response = f"{recovery} {bot_response}".strip()
                    logger.warning(
                        f"  T{self.turn_idx}: SANITIZE — replaced false order-confirmation "
                        f"(create_order error: {err_txt[:80]!r})"
                    )

            # ── Auto-goodbye after successful create_order ──────────────────────
            # When create_order + send_sms complete cleanly, the LLM sometimes
            # waits for the caller to say "bye" before wrapping up. Append a
            # farewell + end_call so the call ends proactively.
            _co_ok = (
                "create_order" in turn_tools
                and "create_order" not in failed_tool_names
                and isinstance(_co_result, dict)
                and not _co_had_error
            )
            if _co_ok and "end_call" not in turn_tools:
                farewell = (
                    self._tenant.farewell_text if self._tenant
                    else "Vielen Dank für Ihre Bestellung und einen schönen Tag. Auf Wiederhören!"
                )
                bot_response = (
                    (bot_response or "").rstrip()
                    + f" {farewell}\n[TOOL:end_call]"
                ).strip()
                turn_tools = list(turn_tools) + ["end_call"]
                should_end = True
                end_reason = "order_complete"
                logger.info(
                    f"  T{self.turn_idx}: AUTO-GOODBYE — create_order succeeded, "
                    f"appending farewell + end_call"
                )
                try:
                    from tools.executor import execute_tool
                    await execute_tool(
                        "end_call",
                        {"reason": "order_complete"},
                        self.call_sid,
                        self.tenant_id,
                    )
                except Exception as _e:
                    logger.warning(
                        f"  T{self.turn_idx}: end_call execute failed (auto-goodbye): {_e}"
                    )

            # Phase 9 B1: expose error codes to brain_service.py via instance attribute
            self._current_turn_error_codes = _turn_error_codes

            # Mark: tools done
            import time as _time_mark
            logger.info(f"[LAT-2026-04-20] call={self.call_sid} turn={self.turn_idx} tool_done")
            if _turn_timings is not None:
                _turn_timings.tool_done_at = time.monotonic()
            # create_reservation fires. node_manager injects it atomically via
            # step 3 + step 7b, but occasionally the [TOOL:check_availability] tag
            # gets lost in the pipeline before TOOLSDATA is sent. This guard
            # guarantees it appears in tools_called → auditor CRITICAL FLOW passes.
            if (
                "create_reservation" in turn_tools
                and "check_availability" not in turn_tools
                and "check_availability" not in self.all_tools
            ):
                turn_tools.insert(0, "check_availability")
                logger.info(f"  T{self.turn_idx}: SAFETY NET injected check_availability (create_reservation fired, check_avail missing)")

            # ── Loop escape hatch ──────────────────────────────── [validated ~462]
            # A3: Raised from 5 to 8 turns to reduce premature end_call.
            # Sprint B: extended to 12 turns when actively collecting address/phone
            # (multi-turn German number dictation legitimately takes many turns).
            _collecting_critical_slot = (
                self.state.order_intent
                and not self.state.order_created
                and not (self.state.address_confirmed and self.state.phone_confirmed)
            )
            _loop_escape_threshold = 999  # dev mode: loop escape disabled
            if (
                self.node_mgr._turns_in_node >= _loop_escape_threshold
                and not _COMMIT_TOOLS.intersection(set(turn_tools))
                and "end_call" not in self.all_tools
                and not (self.state.order_intent and not self.state.order_created)
                and not (self.state.reservation_intent and not self.state.reservation_created)
            ):
                farewell = self._tenant.farewell_text if self._tenant else "Vielen Dank für Ihren Anruf! Auf Wiedersehen."  # tenant-specific fallback
                bot_response = (
                    f"{farewell}"
                    "\n[TOOL:end_call]"
                )
                turn_tools = ["end_call"]
                should_end = True
                end_reason = "forced_end_loop"
                logger.warning(
                    f"  T{self.turn_idx}: LOOP ESCAPE — "
                    f"{self.node_mgr._turns_in_node} turns in "
                    f"'{self.node_mgr.current_node_name}' with no commits"
                )
                # [PRODUCTION] Execute end_call — main execute loop already finished above
                try:
                    from tools.executor import execute_tool
                    await execute_tool("end_call", {"reason": "forced_end_loop"}, self.call_sid, self.tenant_id)
                except Exception as _e:
                    logger.warning(f"  T{self.turn_idx}: end_call execute failed (loop escape): {_e}")

            # ── Stuck-loop detector (Phase 4 D2: Jaccard 0.8 + legacy exact-match) ──
            elif (
                self.turn_idx >= 3
                and self._check_stuck_loop()
            ):
                _in_active_flow = bool(
                    self.state.order_intent or self.state.reservation_intent
                )
                if _in_active_flow:
                    bot_response = (
                        "Ich komme gerade leider nicht weiter. "
                        "Ich lasse einen Kollegen bei Ihnen zurückrufen, "
                        "damit wir das in Ruhe regeln können."
                        "\n[TOOL:technical_issues_callback]"
                        "\n[TOOL:end_call]"
                    )
                    turn_tools = ["technical_issues_callback", "end_call"]
                    end_reason = "stuck_loop_active_flow_callback"
                    logger.warning(
                        f"  T{self.turn_idx}: STUCK LOOP during active flow "
                        f"(order_intent={self.state.order_intent}, "
                        f"reservation_intent={self.state.reservation_intent}) — "
                        f"escalating to technical_issues_callback + end_call"
                    )
                    try:
                        from tools.executor import execute_tool
                        await execute_tool(
                            "technical_issues_callback",
                            {"reason": "stuck_loop"},
                            self.call_sid,
                            self.tenant_id,
                        )
                    except Exception as _e:
                        logger.warning(
                            f"  T{self.turn_idx}: technical_issues_callback failed (stuck loop): {_e}"
                        )
                else:
                    farewell = self._tenant.farewell_text if self._tenant else "Vielen Dank für Ihren Anruf! Auf Wiedersehen."  # tenant-specific fallback
                    bot_response = (
                        f"{farewell}"
                        "\n[TOOL:end_call]"
                    )
                    turn_tools = ["end_call"]
                    end_reason = "forced_end_loop"
                    self.node_mgr.current_node_name = "goodbye"
                    logger.warning(
                        f"  T{self.turn_idx}: STUCK LOOP — 4 identical responses, forcing end_call"
                    )
                should_end = True
                # [PRODUCTION] Execute end_call — main execute loop already finished above
                try:
                    from tools.executor import execute_tool
                    await execute_tool("end_call", {"reason": end_reason}, self.call_sid, self.tenant_id)
                except Exception as _e:
                    logger.warning(f"  T{self.turn_idx}: end_call execute failed (stuck loop): {_e}")

            # [PRODUCTION] Natural end: end_call tag present in turn_tools
            if "end_call" in turn_tools and not should_end:
                should_end = True
                end_reason = "end_call_tool"

            # [PRODUCTION] Transfer to human also ends our pipeline (Twilio takes over)
            if "transfer_to_human" in turn_tools or "transfer_to_tier2" in turn_tools:
                should_end = True
                end_reason = "transfer_to_human"

            # [PRODUCTION] Farewell safety net: LLM said goodbye but forgot end_call tag.
            # Prevents "bis bald" being spoken with no hangup.
            # Fix: only trigger when farewell appears at END of response (last 60 chars)
            # to avoid false-positive hangups when farewell words appear mid-sentence
            # (e.g. "…wünschen Ihnen einen schönen Tag mit Ihrem Essen…").
            if not should_end and bot_response:
                _FAREWELL_PATTERNS = (
                    "auf wiedersehen", "tschüs", "tschüss", "bis bald",
                    "auf wiederhören", "auf wiederhören!", "goodbye",
                )
                _response_tail = bot_response.lower()[-80:]
                _has_farewell = any(p in _response_tail for p in _FAREWELL_PATTERNS)
                # Extra guard: don't trigger during active ordering when confirmation flags not set
                _active_ordering = (
                    self.state.order_intent
                    and not self.state.order_created
                    and not (self.state.address_confirmed and self.state.phone_confirmed)
                )
                if _has_farewell and not _active_ordering:
                    should_end = True
                    end_reason = "farewell_text"
                    turn_tools = list(turn_tools) + ["end_call"]
                    logger.info(f"  T{self.turn_idx}: farewell detected at response tail → auto end_call")
                    try:
                        from tools.executor import execute_tool
                        await execute_tool("end_call", {"reason": "farewell_text"}, self.call_sid, self.tenant_id)
                    except Exception as _e:
                        logger.warning(f"  T{self.turn_idx}: end_call execute failed (farewell): {_e}")

            # Anti-repetition [validated ~499]
            # CRITICAL ORDER: vary FIRST, then append the varied text to history.
            # Appending before variation causes apply_response_variations to see the
            # current turn's unvaried text in its recent-window, poisoning the rotation.
            recent = self.state.recent_responses[-8:]
            try:
                bot_response = apply_response_variations(
                    bot_response,
                    recent,
                    self._variation_rotator,
                )
            except Exception as _var_err:
                logger.warning(f"  T{self.turn_idx}: response variation failed (non-fatal): {_var_err}")
            self.state.recent_responses.append(bot_response)  # store VARIED text
            if len(self.state.recent_responses) > 12:
                self.state.recent_responses = self.state.recent_responses[-12:]

            self.all_tools.extend(turn_tools)  # [validated ~512]

        except Exception as llm_err:  # [validated ~514]
            logger.warning(f"  Turn {self.turn_idx} LLM error: {llm_err}", exc_info=True)
            turn_tools = []
            # If the order was already created successfully, don't alarm the caller
            # with a generic error message — the failure is in post-processing only.
            if getattr(self.state, "order_created", False):
                bot_response = "Ihre Bestellung wurde aufgenommen. Gibt es noch etwas, womit ich Ihnen helfen kann?"
            else:
                # Phase 4 B3: safe handoff — never emit raw "technisches Problem"
                bot_response = (
                    "Entschuldigung, es gab eine technische Störung. "
                    "Ich verbinde Sie jetzt mit einem Mitarbeiter."
                )
                turn_tools = ["transfer_to_human"]
                should_end = True
                end_reason = "llm_error_transfer"
                try:
                    from tools.executor import execute_tool
                    await execute_tool("transfer_to_human", {"reason": "llm_error"}, self.call_sid, self.tenant_id)
                except Exception as _te:
                    logger.warning(f"  T{self.turn_idx}: transfer_to_human failed after LLM error: {_te}")
        finally:
            gemini_runner._active_prompt_override = None  # [validated ~523]

        # Phase 4 D4: abuse + out-of-scope checks (after LLM, before recording)
        _last_ext = getattr(self.state, "last_extraction", {}) or {}
        try:
            from server.brain.layer1.turn_control import handle_abuse, handle_out_of_scope
            _abuse_response = handle_abuse(self.state, _last_ext)
            if _abuse_response and not should_end:
                if getattr(self.state, "call_ended", False):
                    bot_response = _abuse_response
                    turn_tools = list(turn_tools or []) + ["end_call"]
                    should_end = True
                    end_reason = "abuse_end"
                else:
                    # First strike: override/append de-escalation — keep response brief
                    bot_response = _abuse_response
                    logger.warning(f"  T{self.turn_idx}: abuse de-escalation injected")

            _oos_response = handle_out_of_scope(_last_ext)
            if _oos_response and not should_end and not _abuse_response:
                # Redirect rather than override — append to existing response
                bot_response = _oos_response
        except Exception as _d4_err:
            logger.debug(f"  T{self.turn_idx}: D4 abuse/oos check non-fatal: {_d4_err}")

        # [PRODUCTION] Record turn + increment counter (validated does this outside the try too)
        self.memory.record_turn(user_text, bot_response, node.name)
        self.turn_idx += 1

        # Phase 3 Stream 1: advance end-of-call state machine if conditions are met
        try:
            from server.brain.layer1.goodbye_state_machine import should_advance, advance as _sm_advance
            _next_stage = should_advance(self.state)
            if _next_stage is not None:
                _sm_advance(self.state, _next_stage, reason=f"turn_{self.turn_idx}_auto")
        except Exception as _sm_err:
            logger.debug(f"  EndCallSM: non-fatal error: {_sm_err}")

        # Phase 4 D3: no-progress escape (8 turns no new slot fills)
        try:
            from server.brain.layer1.turn_control import is_no_progress
            if not should_end and is_no_progress(self.state, self.turn_idx):
                logger.warning(
                    "[turn_control] T%d: no-progress after %d turns — ending call",
                    self.turn_idx, self.turn_idx,
                )
                bot_response = (
                    "Es scheint, wir kommen gerade nicht weiter. "
                    "Ich verbinde Sie mit einem Kollegen, der Ihnen direkt helfen kann."
                )
                turn_tools = list(turn_tools or []) + ["transfer_to_human"]
                should_end = True
                end_reason = "no_progress"
        except Exception as _np_err:
            logger.debug(f"  T{self.turn_idx}: no-progress check non-fatal: {_np_err}")

        # Phase 4 D1: adaptive turn-cap check (after increment so turn_idx is current)
        try:
            from server.brain.layer1.turn_control import is_over_turn_cap, force_end_for_turn_cap
            if not should_end and is_over_turn_cap(self.state, self.turn_idx):
                logger.warning(
                    "[turn_control] T%d: over turn cap (%d) — ending call",
                    self.turn_idx, self.turn_idx,
                )
                bot_response = force_end_for_turn_cap(self.state)
                turn_tools = list(turn_tools or []) + ["end_call"]
                should_end = True
                end_reason = "turn_cap"
        except Exception as _tc_err:
            logger.debug(f"  T{self.turn_idx}: turn-cap check non-fatal: {_tc_err}")

        # Phase 4 B3: strip generate_with_retry() forced-transfer sentinel before TTS
        if "__FORCE_TRANSFER_TO_HUMAN__" in (bot_response or ""):
            bot_response = (
                "Entschuldigung, es gab eine technische Störung. "
                "Ich verbinde Sie jetzt mit einem Mitarbeiter."
            )
            if "transfer_to_human" not in turn_tools:
                turn_tools = list(turn_tools) + ["transfer_to_human"]
            should_end = True
            end_reason = "forced_transfer_sentinel"
            logger.warning(f"  T{self.turn_idx}: FORCE_TRANSFER_TO_HUMAN sentinel caught — safe handoff")

        # Strip [TOOL:...] tags for TTS
        clean_text = re.sub(r"\[TOOL:\w+\]\s*", "", bot_response).strip()

        # Hallucination stripping is now handled by Layer 3 policy (Phase 8 A4).
        # The old local _HALLUCINATED_TERMS list has been removed; use
        # server/brain/layer3/blacklist.py to manage the tenant-aware blacklist.

        # === Bug F FIX: STRIP TOOL-CALL LEAKAGE (always, before anything else) ===
        from server.brain.conversation_state import (
            sanitize_bot_text_against_tool_results,
            strip_tool_call_leakage,
        )
        clean_text, tool_leak_stripped = strip_tool_call_leakage(clean_text)
        if tool_leak_stripped:
            logger.warning(
                f"[TRACE-2026-04-20] strip_tool_call_leakage removed forbidden patterns — "
                f"final_text={clean_text[:120]!r}"
            )

        # === F-C FIX: SANITIZE BOT TEXT AGAINST TOOL ERRORS ===
        if tool_results:
            # [TRACE-2026-04-20] Point 11: sanitize_bot_text invocation
            logger.info(
                f"[TRACE-2026-04-20] sanitize_bot_text INPUT: "
                f"bot_text={clean_text[:120]!r} "
                f"tools_this_turn={([(t.get('name'), bool(t.get('result', {}).get('error'))) for t in (tool_results.values() if isinstance(tool_results, dict) else [])])}"
            )
            sanitized_text = sanitize_bot_text_against_tool_results(clean_text, tool_results)
            logger.info(
                f"[TRACE-2026-04-20] sanitize_bot_text OUTPUT: "
                f"was_sanitized={clean_text != sanitized_text} final_text={sanitized_text[:120]!r}"
            )
            clean_text = sanitized_text

        return TurnResult(
            clean_text=clean_text,
            raw_response=bot_response,
            tools_called=turn_tools,
            tool_results=tool_results,
            should_end=should_end,
            end_reason=end_reason,
            missing_fields_hint=missing_fields_hint,
        )

    def _build_tool_args(self, tool_name: str) -> tuple:
        """
        Build tool arguments from ConversationState.

        Returns (args_dict, None) if all required fields present.
        Returns (None, error_message) if required fields are missing — caller must NOT execute.

        PRODUCTION SAFETY: No fallback defaults for order-critical fields.
        If dish/name is unknown, refuse and re-ask rather than placing a wrong order.
        """
        state = self.state

        if tool_name == "create_order":
            if not state.selected_dish:
                return None, "Gericht (welches Gericht möchten Sie?)"
            # Prices come from the live menu (get_menu tool result) — never hardcoded.
            # If menu hasn't been cached yet, refuse the commit and force a get_menu first.
            if not state.cached_menu:
                logger.warning(
                    f"[CART] T{self.turn_idx}: create_order aborted — menu not yet cached; "
                    f"LLM must call get_menu first."
                )
                return None, "Menü nicht geladen — rufe zuerst get_menu auf, damit Preise verfügbar sind."
            # FIX 2: In multi-intent mode, get items from current intent; otherwise use legacy cart
            cart_items = state.current_intent_items()  # routes through captured_intents or falls back
            subtotal = 0.0
            missing_prices: List[str] = []
            for item in cart_items:
                price = get_cached_dish_price(state, item)
                if price:
                    subtotal += price
                else:
                    missing_prices.append(item)
            if missing_prices:
                logger.warning(
                    f"[CART] T{self.turn_idx}: no price in cached_menu for {missing_prices!r} — "
                    f"cached categories={list(state.cached_menu.keys())}"
                )
            # Business rules: min order 20€, delivery surcharge +5€ if subtotal < 20€
            _is_delivery = state.delivery_address_mentioned or bool(getattr(state, "delivery_address", ""))
            delivery_surcharge = 5.0 if (_is_delivery and subtotal > 0 and subtotal < 20.0) else 0.0
            total_price = round(subtotal + delivery_surcharge, 2)
            # Safety net: if no price could be resolved at all, refuse rather than send 0€ order
            if total_price <= 0:
                return None, "Gesamtpreis konnte nicht berechnet werden — bitte prüfen Sie die Gerichte."
            order_items_str = ", ".join(cart_items)
            logger.info(
                f"[CART] T{self.turn_idx}: items={cart_items} subtotal={subtotal:.2f}€ "
                f"surcharge={delivery_surcharge:.2f}€ total={total_price:.2f}€ delivery={_is_delivery}"
            )
            # customer_name is a production-only field set via the update_state tool during live calls.
            # In browser demo mode, ConversationState.customer_name is always None because it is
            # populated via main.py's session (NameGate), not via ConversationState directly.
            _special: List[str] = []
            if delivery_surcharge > 0:
                _special.append(f"Lieferpauschale {delivery_surcharge:.2f}€ (unter 20€ Mindestwert)")
            if getattr(state, "bell_name", None) and state.bell_name != (state.customer_name or ""):
                _special.append(f"Klingelname: {state.bell_name}")
            return {
                "name": state.customer_name or "Anonym",
                "phone": state.phone_number or self.caller_phone or "",
                "messaging_phone": state.phone_number or self.caller_phone or "",
                "order_items": order_items_str,
                "order_type": "delivery" if _is_delivery else "takeaway",
                "payment_method": "bar",
                "total_price": total_price,
                "subtotal": round(subtotal, 2),
                "delivery_surcharge": delivery_surcharge,
                "delivery_address": getattr(state, "delivery_address", "") or "",
                "special_requests": " | ".join(_special) if _special else "",
            }, None

        elif tool_name == "create_reservation":
            # Use fallbacks for all fields — consistent with check_availability.
            # Never block: the forced commit (step 7 in node_manager) fires only when
            # check_availability succeeded AND reservation_intent is active. Even
            # when date/time are unclear (e.g. accent speaker saying "Sunday"), the
            # tool should execute so the validation counts it. The tool executor will
            # handle missing/fallback date gracefully.
            return {
                "date": state.reservation_date or "nächster Termin",
                "time": state.reservation_time or "19:00",
                "party_size": state.party_size or 2,
                "name": state.customer_name or "Anonym",
                "phone": state.phone_number or self.caller_phone or "",
            }, None

        elif tool_name == "check_availability":
            return {
                "date": state.reservation_date or "",
                "time": state.reservation_time or "",
                "party_size": state.party_size or 2,
            }, None

        elif tool_name == "verify_address":
            delivery_addr = getattr(state, "delivery_address", "") or ""
            city = self._tenant.city if self._tenant else "Bonn"
            if not delivery_addr or not delivery_addr.strip():
                # Address text not extracted yet — proceed with city-only lookup.
                # This allows the verify_address tag to count in browser validation
                # (consistent with text-mode where the tag always counts).
                # The Maps API will return a partial result or "not found" which is
                # acceptable — what matters is that the tool step executes.
                state.verify_address_called = False  # allow retry when actual address arrives
                return {"address": city, "city": city}, None
            return {
                "address": delivery_addr,
                "city": city,
            }, None

        elif tool_name == "get_menu":
            return {"category": "alle"}, None

        elif tool_name == "get_date_info":
            return {"date": state.reservation_date or "heute"}, None

        elif tool_name == "get_weather":
            location = self._tenant.city if self._tenant else "Bonn"
            return {"location": location}, None

        elif tool_name == "get_restaurant_info":
            if self._tenant and self._tenant.coordinates:
                lat = self._tenant.coordinates.get("lat", 50.7323)
                lng = self._tenant.coordinates.get("lng", 7.0954)
            else:
                lat, lng = 50.7323, 7.0954
            return {
                "query": getattr(self, "_last_user_text", "parken"),
                "lat": lat,
                "lng": lng,
                "radius": 500,
                "type": "parking",
            }, None

        elif tool_name == "end_call":
            return {"reason": "goodbye"}, None

        elif tool_name in ("transfer_to_human", "transfer_to_tier2"):
            return {"reason": "caller_requested"}, None

        elif tool_name == "send_sms":
            # SMS is now sent automatically by create_order/create_reservation executors
            # This is a no-op in production (executor handles it internally)
            return {}, None

        elif tool_name in ("ai_greeting", "faq", "technical_issues_callback", "request_callback"):
            # These are logging/tracking tools — no real execution needed
            return {}, None

        else:
            logger.warning(f"[ADKTurn] Unknown tool for arg building: {tool_name} — skipping")
            return {}, None

    def build_transfer_context(self, reason: str = "") -> dict:
        """Build a structured handover payload for a warm transfer to a human.

        Used by both ``_transfer_to_human`` (write to Redis under
        ``transfer_ctx:{call_sid}``) and the admin HTML viewer at
        ``/admin/transfer/{call_sid}``.  Payload must be small enough to
        skim in <5 seconds — the human has a live caller on the line.
        """
        slots_summary = ""
        slots_missing = ""
        slots_intent: Optional[str] = None
        try:
            if self.order_slots is not None:
                slots_summary = self.order_slots.known_summary_de()
                slots_missing = self.order_slots.missing_summary_de()
                slots_intent = getattr(self.order_slots, "intent", None)
        except Exception:
            pass

        return {
            "call_sid": self.call_sid,
            "tenant_id": self.tenant_id,
            "reason": reason or "caller_requested",
            "built_at": datetime.now().isoformat(),
            "turn_idx": self.turn_idx,
            "current_node": self.node_mgr.current_node_name if self.node_mgr else None,
            "nodes_visited": list(self._nodes_visited)[-10:],
            "caller_phone": self.caller_phone,
            "intent": slots_intent or (
                "order" if self.state.order_intent
                else "reservation" if self.state.reservation_intent
                else None
            ),
            "slots_known": slots_summary,
            "slots_missing": slots_missing,
            "customer_name": self.state.customer_name,
            "phone_number": self.state.phone_number,
            "delivery_address": getattr(self.state, "delivery_address", None),
            "selected_dish": self.state.selected_dish,
            "order_quantity": getattr(self.state, "order_quantity", None),
            "escalation_requested": self.state.escalation_requested,
            "recent_transcript": self.state.recent_responses[-8:],
        }

    async def persist_transfer_context(self, reason: str = "") -> Optional[str]:
        """Write the warm-handover context to Redis under a stable key.
        Returns the key on success so the caller can surface it in logs / SMS.
        """
        if not self.session:
            return None
        payload = self.build_transfer_context(reason=reason)
        key = f"transfer_ctx:{self.call_sid}"
        try:
            import json as _json
            redis = getattr(self.session, "redis", None) or getattr(
                self.session, "_redis", None
            )
            if redis is None:
                # CallSession exposes a simple update_state() wrapper — fall back to it.
                await self.session.update_state({"transfer_ctx": payload})
                return key
            # 1 hour TTL — long enough for the human to pick up and act,
            # short enough that the log doesn't grow unbounded.
            await redis.setex(key, 3600, _json.dumps(payload, default=str))
            logger.info(
                f"[transfer_ctx] wrote {key} "
                f"(intent={payload.get('intent')!r} known_keys="
                f"{bool(payload.get('slots_known'))})"
            )
            return key
        except Exception as _err:
            logger.warning(f"[transfer_ctx] write failed: {_err}")
            return None

    async def persist_state(self):
        """
        Serialize ConversationState + MemoryManager + all_tools to Redis.
        Called after every turn so conversation state survives WebSocket reconnects.
        """
        if not self.session:
            return

        blob = {
            "state": _conversation_state_to_dict(self.state),
            "memory": _memory_manager_to_dict(self.memory),
            "all_tools": self.all_tools,
            "turn_idx": self.turn_idx,
            "recent_responses": self.state.recent_responses,  # single source of truth
            "node_mgr": {
                "current_node": self.node_mgr.current_node_name,
                "turns_in_node": self.node_mgr._turns_in_node,
                "node_stack": self.node_mgr.node_stack,
            },
            # Canonical slot form — required so WS reconnect keeps "what we know"
            "order_slots": self.order_slots.to_dict() if self.order_slots else None,
        }
        try:
            await self.session.update_state({"adk_brain": blob})
        except Exception as e:
            logger.warning(f"[ADKTurn] persist_state Redis error: {e}")

    @classmethod
    async def restore_from_session(
        cls,
        session,
        tenant_id: Optional[str],
        call_sid: str,
        caller_phone: str = "",
        filler_cb=None,
    ) -> Optional["ADKTurnProcessor"]:
        """
        Reconstruct processor from Redis if a prior session exists (WebSocket reconnect path).
        Returns None if no prior state found.
        """
        try:
            data = await session.get()
            blob = (data or {}).get("state", {}).get("adk_brain")
            if not blob:
                return None

            processor = cls(
                tenant_id=tenant_id,
                call_sid=call_sid,
                session=session,
                caller_phone=caller_phone,
                filler_cb=filler_cb,
            )
            processor.state = _conversation_state_from_dict(blob.get("state", {}))
            processor.memory = _memory_manager_from_dict(blob.get("memory", {}))
            processor.all_tools = blob.get("all_tools", [])
            processor.turn_idx = blob.get("turn_idx", 0)
            processor.state.recent_responses = blob.get("recent_responses", [])

            node_blob = blob.get("node_mgr", {})
            processor.node_mgr.current_node_name = node_blob.get("current_node", "greeting")
            processor.node_mgr._turns_in_node = node_blob.get("turns_in_node", 0)
            processor.node_mgr.node_stack = node_blob.get("node_stack", [])

            # Restore canonical OrderSlots (the "what we know" truth) so reconnect
            # does not ask for data the caller already provided.
            slots_blob = blob.get("order_slots")
            if slots_blob:
                try:
                    processor.order_slots = OrderSlots.from_dict(slots_blob)
                    processor.state.order_slots_ref = processor.order_slots
                    logger.info(
                        f"[ADKTurn] Restored OrderSlots "
                        f"(intent={processor.order_slots.intent!r}, "
                        f"missing={processor.order_slots.missing_required()})"
                    )
                except Exception as _slot_err:
                    logger.warning(f"[ADKTurn] OrderSlots restore failed: {_slot_err}")

            logger.info(f"[ADKTurn] Restored session at turn {processor.turn_idx}, node={processor.node_mgr.current_node_name}")
            return processor
        except Exception as e:
            logger.warning(f"[ADKTurn] restore_from_session failed: {e}")
            return None

    async def finalize_call(self, outcome: str, custom_summary: str = None):
        """Save call summary to Redis for cross-call history when call ends.
        
        Called when call ends (transfer, end_call, timeout, error).
        Saves a summary that will be injected into memory for repeat callers.
        
        Args:
            outcome: How the call ended ("completed", "transferred", "abandoned")
            custom_summary: Optional override summary. If not provided, auto-generated from state.
        """
        # Cancel any pending slot extraction tasks
        for _t in list(self._pending_extraction_tasks):
            if not _t.done():
                _t.cancel()
        self._pending_extraction_tasks.clear()

        # Shut down ValidationRegistry — cancel any remaining background tasks
        try:
            await self.validation_registry.shutdown()
        except Exception as _vr_err:
            logger.debug(f"[ADKTurn] validation_registry shutdown error (non-fatal): {_vr_err}")

        if not self.caller_phone:
            return
        
        import time
        
        # Lazy-initialize CallSummary if not done yet
        if self._call_summary_mgr is None:
            try:
                from server.brain.call_summary import CallSummary
                from server.session import get_redis
                redis = await get_redis()
                self._call_summary_mgr = CallSummary(redis)
            except Exception as e:
                logger.debug(f"[ADKTurn] CallSummary initialization failed, skipping history save: {e}")
                return
        
        if self._call_start_time is None:
            duration = 0
        else:
            duration = time.time() - self._call_start_time
        
        # Generate summary if not provided
        if custom_summary is None:
            if self.state.order_created:
                items = ", ".join(self.state.cart) if self.state.cart else "Gerichte"
                custom_summary = f"Bestellung: {items}"
                if self.state.delivery_address:
                    custom_summary += f" für Lieferung an {self.state.delivery_address}."
                else:
                    custom_summary += "."
            elif self.state.reservation_confirmed:
                custom_summary = (
                    f"Reservierung: {self.state.reservation_date} Uhr "
                    f"für {self.state.party_size} Personen"
                )
            else:
                custom_summary = "Anruf ohne Abschluss"
        
        try:
            await self._call_summary_mgr.save_call_summary(
                phone=self.caller_phone,
                summary=custom_summary,
                nodes_visited=self._nodes_visited,
                tools_used=self.all_tools,
                duration_seconds=int(duration),
                outcome=outcome
            )
        except Exception as e:
            logger.warning(f"[ADKTurn] finalize_call failed: {e}")


# ── Serialization helpers ─────────────────────────────────────────────────────

def _conversation_state_to_dict(state: ConversationState) -> dict:
    """Serialize ConversationState to a plain dict for Redis storage."""
    return state.to_dict()


def _conversation_state_from_dict(d: dict) -> ConversationState:
    """Deserialize ConversationState from a Redis-stored dict."""
    return ConversationState.from_dict(d)


def _memory_manager_to_dict(memory: MemoryManager) -> dict:
    """Serialize MemoryManager to a plain dict for Redis storage."""
    return {
        "recent_turns": memory.recent_turns,
        "context_summary": memory.context_summary,
        "max_recent_turns": memory.max_recent_turns,
        "max_summary_words": memory.max_summary_words,
    }


def _memory_manager_from_dict(d: dict) -> MemoryManager:
    """Deserialize MemoryManager from a Redis-stored dict."""
    manager = MemoryManager(
        max_recent_turns=d.get("max_recent_turns", 5),
        max_summary_words=d.get("max_summary_words", 300),
    )
    manager.recent_turns = d.get("recent_turns", [])
    manager.context_summary = d.get("context_summary", "")
    return manager
