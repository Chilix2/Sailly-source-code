"""server/brain/v4_turn_processor.py — Adapter: process_turn_v4 behind ADKTurnProcessor interface.

Drop-in replacement for ADKTurnProcessor in BrowserBrainService and TextModeRunner.
Drives process_turn_v4 (workers + context_doc + commit gate + TinyGenerator).
All v4_pipeline fixes are live through this class.

Usage (both callers change ONE import line):
    from server.brain.v4_turn_processor import V4TurnProcessor as ADKTurnProcessor
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

logger = logging.getLogger(__name__)


# ── TurnResult (same shape as adk_turn_processor.TurnResult) ────────────────

@dataclass
class TurnResult:
    """Result of processing a single turn — compatible with adk_turn_processor.TurnResult."""
    clean_text: str
    raw_response: str
    tools_called: List[str] = field(default_factory=list)
    tool_results: dict = field(default_factory=dict)
    should_end: bool = False
    end_reason: str = ""
    missing_fields_hint: Optional[str] = None
    node_name: Optional[str] = None  # v4 exposes this directly; adk_turn_processor used getattr fallback


# ── NodeMgr stub (brain_service reads .current_node_name as fallback) ────────

class _NodeMgrStub:
    """Minimal stub satisfying brain_service.py reads of turn_processor.node_mgr."""
    def __init__(self):
        self.current_node_name: str = "greeting"
        self._turns_in_node: int = 0
        self.node_stack: list = []


# ── V4TurnProcessor ──────────────────────────────────────────────────────────

class V4TurnProcessor:
    """Drop-in replacement for ADKTurnProcessor that drives process_turn_v4.

    Implements the same external interface (constructor signature, process_turn,
    restore_from_session, and all fields brain_service.py reads directly) so
    BrowserBrainService and TextModeRunner need only a one-line import change.
    """

    def __init__(
        self,
        tenant_id: Optional[str],
        call_sid: str,
        session=None,
        caller_phone: str = "",
        filler_cb=None,
    ):
        from server.brain.conversation_state import ConversationState, set_known_items
        from anthropic import AsyncAnthropic

        self.tenant_id = tenant_id
        self.call_sid = call_sid
        self.caller_phone = caller_phone
        self._filler_cb = filler_cb
        self.session = session

        # Populate known items from tenant config so dish extraction works
        _tid = tenant_id or "doboo"
        try:
            import pathlib, yaml as _yaml
            _cfg_path = pathlib.Path(__file__).parent.parent.parent / "configs" / "tenants" / f"{_tid}.yaml"
            with open(_cfg_path) as _f:
                _cfg = _yaml.safe_load(_f)
            _items = _cfg.get("items", [])
            if _items:
                set_known_items(_items)
                logger.debug(f"[V4Turn] loaded {len(_items)} known items for tenant={_tid}")
        except Exception as _e:
            logger.warning(f"[V4Turn] could not load known items for tenant={_tid}: {_e}")

        # Core state — real ConversationState so all slot extraction works
        self.state = ConversationState()
        self.turn_idx: int = 0
        self.last_turns: list[tuple[str, str]] = []
        self.all_tools: list[str] = []

        # NodeMgr stub — brain_service reads node_mgr.current_node_name as fallback
        self.node_mgr = _NodeMgrStub()

        # Observability stubs — brain_service reads these in metrics block (lines ~853-1006)
        # Returning empty/zero values is safe; they are logging-only
        self._last_prompt_tokens_in: int = 0
        self._last_prompt_tokens_out: int = 0
        self._current_turn_error_codes: list = []
        try:
            from server.brain.validation_registry import ValidationRegistry
            from tools.executor import execute_tool

            self.validation_registry = ValidationRegistry(
                execute_tool=execute_tool,
                call_sid=call_sid,
                tenant_id=tenant_id or "doboo",
                state=self.state,
            )
            self.state.validation_registry_ref = self.validation_registry
        except Exception as exc:
            logger.warning("[V4Turn] validation registry disabled: %s", exc)
            self.validation_registry = None
        self._validations_passed: int = 0
        self._validations_failed: int = 0
        self._validations_skipped: int = 0
        self._last_stt_confidence: Optional[float] = None
        self._last_tts_directive = None
        self._last_bot_response: str = ""
        self._pending_bot_response: str = ""
        self._response_repeat_count: int = 0
        self._last_slot_extraction_latency_ms: Optional[int] = None
        self._last_slot_retention_status: Optional[dict] = None
        self._last_validation_passes: Optional[list] = None
        self._semantic_tools_called_this_turn: list[str] = []

        # Anthropic client for TinyGenerator
        self._llm_client = AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        try:
            from server.brain.slot_extractor import SlotExtractor
            from server.brain.slot_extraction_layer import SlotExtractionLayer

            self.slot_extractor = SlotExtractor(anthropic_client=self._llm_client)
            self.slot_extraction_layer = SlotExtractionLayer(self.slot_extractor)
        except Exception as exc:
            logger.warning("[V4Turn] semantic slot extraction disabled: %s", exc)
            self.slot_extractor = None
            self.slot_extraction_layer = None

    # ── brain_service reads turn_processor._state for CRM ────────────────────
    @property
    def _state(self):
        return self.state

    # ── brain_service calls this for metrics ─────────────────────────────────
    def _collect_subsystem_status(self) -> dict:
        status: dict[str, str | bool] = {
            "registry_exists": self.validation_registry is not None,
        }
        metrics = getattr(self.state, "_last_semantic_slot_metrics", {}) or {}
        if metrics:
            status["slot_extractor"] = "timed_out" if metrics.get("timed_out") else "completed"
        elif self.slot_extraction_layer is not None:
            status["slot_extractor"] = "idle"
        if self.validation_registry is not None:
            try:
                status["validation_registry"] = (
                    "fired" if getattr(self.validation_registry, "_entries", {}) else "silent"
                )
            except Exception:
                status["validation_registry"] = "unknown"
        return status

    # ── Main entry point ──────────────────────────────────────────────────────
    async def process_turn(
        self,
        user_text: str,
        tts_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> TurnResult:
        from server.brain.conversation_state import update_state_from_utterance
        from server.brain.context_doc_builder import _persist_resolved_entities_to_state
        from server.brain.v4_pipeline import process_turn_v4

        self._semantic_tools_called_this_turn = []

        semantic_pre_response = await self._run_semantic_slot_extraction(user_text)
        if semantic_pre_response:
            clean = semantic_pre_response
            if user_text:
                self.last_turns.append(("user", user_text))
            self.last_turns.append(("assistant", clean))
            self.last_turns = self.last_turns[-10:]
            self._last_bot_response = clean
            self.turn_idx += 1
            return TurnResult(
                clean_text=clean,
                raw_response=clean,
                tools_called=list(self._semantic_tools_called_this_turn),
                node_name="semantic_slot_readback",
            )

        # Step 1: semantic candidates plus legacy phone/name/date/party extraction.
        # Workers in v4_pipeline handle date/time/party_size/name but NOT phone numbers
        # (phone uses the cross-turn digit-buffer logic in update_state_from_utterance).
        update_state_from_utterance(self.state, user_text)

        # Step 2: run v4 pipeline — workers + context_doc + commit gate + TinyGenerator
        # Include current user turn in last_turns so TinyGenerator always sees it in context.
        turns_with_current = list(self.last_turns) + ([("user", user_text)] if user_text else [])
        result_dict = await process_turn_v4(
            user_text=user_text,
            turn_idx=self.turn_idx,
            state=self.state,
            call_sid=self.call_sid,
            tenant_id=self.tenant_id or "doboo",
            llm_client=self._llm_client,
            last_turns=turns_with_current,
            tts_callback=tts_callback,
            caller_phone=self.caller_phone,
            speculative_worker_results=getattr(self, "_speculative_worker_results", None),
        )
        self._speculative_worker_results = None

        # Step 3: maintain turn history for TinyGenerator context window
        # (No explicit persist call needed — process_turn_v4 mutates state in-place.)
        if user_text:
            self.last_turns.append(("user", user_text))
        clean = result_dict.get("clean_text", "")
        if clean:
            self.last_turns.append(("assistant", clean))
        self.last_turns = self.last_turns[-10:]  # keep last 10 turns

        # Step 4: update bookkeeping
        profile = result_dict.get("profile", result_dict.get("node_name", "greeting"))
        self.node_mgr.current_node_name = profile
        tools = result_dict.get("tools_called", [])
        if self._semantic_tools_called_this_turn:
            tools = list(dict.fromkeys(list(tools or []) + self._semantic_tools_called_this_turn))
        for t in tools:
            if t not in self.all_tools:
                self.all_tools.append(t)
        self._last_bot_response = clean
        self.turn_idx += 1

        return TurnResult(
            clean_text=clean,
            raw_response=result_dict.get("raw_response", clean),
            tools_called=tools,
            tool_results={},
            should_end=result_dict.get("should_end", False),
            end_reason=result_dict.get("end_reason", ""),
            node_name=profile,
        )

    async def _run_semantic_slot_extraction(self, user_text: str) -> Optional[str]:
        """Extract, validate, and apply semantic slot candidates before v4 logic."""
        if not user_text or self.slot_extraction_layer is None:
            return None

        import time
        from server.brain.slot_extraction_layer import slots_for_current_turn
        from server.brain.slot_validators import (
            AddressValidator,
            DateValidator,
            OrderItemValidator,
            PartySizeValidator,
            PhoneValidator,
        )

        started = time.monotonic()
        slots = slots_for_current_turn(self.state, user_text)
        candidates = await self.slot_extraction_layer.extract(
            user_utterance=user_text,
            conversation_history=self.last_turns + ([("user", user_text)] if user_text else []),
            current_state=self.state,
            slots_to_extract=slots,
        )
        self._last_slot_extraction_latency_ms = int((time.monotonic() - started) * 1000)

        validators = {
            "delivery_address": AddressValidator(
                call_sid=self.call_sid,
                tenant_id=self.tenant_id or "doboo",
                city="Bonn",
            ),
            "phone": PhoneValidator(),
            "order_items": OrderItemValidator(self.state),
            "delivery_date": DateValidator(),
            "party_size": PartySizeValidator(),
        }
        validation_passes: list[dict] = []
        address_reprompt: Optional[str] = None
        for candidate in candidates.all():
            validator = validators.get(candidate.slot_name)
            if validator is None:
                continue
            result = await validator.validate(candidate)
            candidate.validator_feedback = result.feedback
            candidate.validator_valid = result.is_valid
            candidate.confidence = max(0.0, min(1.0, candidate.confidence + result.confidence_adjustment))
            candidate.needs_readback = (
                candidate.confidence < 0.85
                or (candidate.slot_name == "delivery_address" and not result.is_valid)
            )
            if result.corrected_value is not None:
                candidate.value = result.corrected_value
                candidate.source = "validator_corrected"
            if candidate.slot_name == "delivery_address" and not result.is_valid and result.corrected_value is None:
                candidate.confidence = 0.0
                self._clear_delivery_address_state()
                address_reprompt = (
                    "Die Adresse konnte ich nicht sicher finden. "
                    "Können Sie Straße, Hausnummer und Stadt bitte noch einmal nennen?"
                )
            if result.tool_called:
                self._semantic_tools_called_this_turn.append(result.tool_called)
            validation_passes.append({
                "slot": candidate.slot_name,
                "valid": result.is_valid,
                "feedback": result.feedback,
                "tool_called": result.tool_called,
            })

        confirmation = candidates.by_name("confirmation_intent")
        pending = getattr(self.state, "pending_readback_slots", {}) or {}
        if pending and confirmation and str(confirmation.value).lower() == "yes":
            self._apply_pending_semantic_slots()
            self.state.pending_readback_slots = {}
        elif pending and confirmation and str(confirmation.value).lower() == "no":
            if "delivery_address" in pending:
                self._clear_delivery_address_state()
                self.state.pending_readback_slots = {}
                return (
                    "Alles klar, bitte nennen Sie die vollständige Lieferadresse "
                    "mit Straße, Hausnummer und Stadt noch einmal."
                )
            self.state.pending_readback_slots = {}
            return "Alles klar, was soll ich ändern?"

        applied = self.state.update_state_from_extracted_slots(candidates)
        self._last_slot_retention_status = {
            "requested_slots": slots,
            "applied_slots": applied,
            **getattr(self.state, "_last_semantic_slot_metrics", {}),
        }
        self._last_validation_passes = validation_passes

        if address_reprompt:
            return address_reprompt

        pending = getattr(self.state, "pending_readback_slots", {}) or {}
        if pending and not applied:
            return self._build_semantic_readback(pending)
        return None

    def _clear_delivery_address_state(self) -> None:
        self.state.delivery_address = None
        self.state.address_verified = False
        self.state.address_confirmed = False
        self.state.verify_address_called = False
        self.state.verify_address_failed = False
        self.state.pending_readback_slots.pop("delivery_address", None)
        self.state.semantic_slot_values.pop("delivery_address", None)
        self.state._readback_already_shown = False
        self.state._order_readback_confirmed = False
        self.state.end_call_stage = "idle"

    def _apply_pending_semantic_slots(self) -> None:
        from server.brain.slot_extraction_layer import SlotCandidate, SlotCandidates

        pending = getattr(self.state, "pending_readback_slots", {}) or {}
        candidates = SlotCandidates()
        for slot_name, raw in pending.items():
            if not isinstance(raw, dict):
                continue
            candidate = SlotCandidate(
                slot_name=slot_name,
                value=raw.get("value"),
                confidence=max(float(raw.get("confidence") or 0.6), 0.85),
                evidence_span=str(raw.get("evidence_span") or ""),
                source=str(raw.get("source") or "readback_confirmed"),
                needs_readback=False,
                validator_valid=raw.get("validator_valid"),
            )
            if slot_name == "order_items":
                candidates.order_items.append(candidate)
            elif hasattr(candidates, slot_name):
                setattr(candidates, slot_name, candidate)
        self.state.update_state_from_extracted_slots(candidates, apply_medium_confidence=True)

    def _build_semantic_readback(self, pending: dict) -> str:
        labels = {
            "customer_name": "den Namen",
            "delivery_address": "die Adresse",
            "phone": "die Telefonnummer",
            "order_items": "die Bestellung",
            "delivery_date": "das Datum",
            "party_size": "die Personenzahl",
        }
        parts = []
        for slot_name, raw in pending.items():
            if not isinstance(raw, dict):
                continue
            label = labels.get(slot_name, slot_name)
            value = raw.get("value")
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            if value:
                parts.append(f"{label}: {value}")
        if not parts:
            return ""
        return "Ich habe verstanden: " + "; ".join(parts) + ". Stimmt das so?"

    async def _persist_state_safe(self):
        """State persistence stub — v4 does not use Redis adk_brain blob."""
        pass

    # ── Session restore (WebSocket reconnect path for /ws/demo) ──────────────
    @classmethod
    async def restore_from_session(
        cls,
        session,
        tenant_id: Optional[str],
        call_sid: str,
        caller_phone: str = "",
        filler_cb=None,
    ) -> Optional["V4TurnProcessor"]:
        """Reconstruct processor from Redis session blob (WebSocket reconnect).

        Reads the same `state.adk_brain` blob written by ADKTurnProcessor so
        existing sessions survive the migration.
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
            # Restore ConversationState without importing the retired ADK stack.
            from server.brain.session_restore import conversation_state_from_dict
            processor.state = conversation_state_from_dict(blob.get("state", {}))
            processor.all_tools = blob.get("all_tools", [])
            processor.turn_idx = blob.get("turn_idx", 0)
            processor.state.recent_responses = blob.get("recent_responses", [])

            node_blob = blob.get("node_mgr", {})
            processor.node_mgr.current_node_name = node_blob.get("current_node", "greeting")
            processor.node_mgr._turns_in_node = node_blob.get("turns_in_node", 0)
            processor.node_mgr.node_stack = node_blob.get("node_stack", [])

            logger.info(
                f"[V4Turn] Restored session at turn {processor.turn_idx}, "
                f"node={processor.node_mgr.current_node_name}"
            )
            return processor
        except Exception as e:
            logger.warning(f"[V4Turn] restore_from_session failed (non-fatal): {e}")
            return None
