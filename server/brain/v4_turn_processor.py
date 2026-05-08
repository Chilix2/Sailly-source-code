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
        self.validation_registry = None
        self._validations_passed: int = 0
        self._validations_failed: int = 0
        self._validations_skipped: int = 0
        self._last_stt_confidence: Optional[float] = None
        self._last_tts_directive = None
        self._last_bot_response: str = ""
        self._pending_bot_response: str = ""
        self._response_repeat_count: int = 0

        # Anthropic client for TinyGenerator
        self._llm_client = AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )

    # ── brain_service reads turn_processor._state for CRM ────────────────────
    @property
    def _state(self):
        return self.state

    # ── brain_service calls this for metrics ─────────────────────────────────
    def _collect_subsystem_status(self) -> dict:
        return {}

    # ── Main entry point ──────────────────────────────────────────────────────
    async def process_turn(
        self,
        user_text: str,
        tts_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> TurnResult:
        from server.brain.conversation_state import update_state_from_utterance
        from server.brain.context_doc_builder import _persist_resolved_entities_to_state
        from server.brain.v4_pipeline import process_turn_v4

        # Step 1: phone / name / date / party_size extraction via conversation_state.
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
        )

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
            # Restore ConversationState from the ADK blob using the existing helper
            from server.brain.adk_turn_processor import _conversation_state_from_dict
            processor.state = _conversation_state_from_dict(blob.get("state", {}))
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
