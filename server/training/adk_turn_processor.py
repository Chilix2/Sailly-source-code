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
import re
from dataclasses import dataclass, field
from typing import Optional, List

from server.training.conversation_state import (
    ConversationState,
    update_state_from_utterance,
    update_state_after_bot,
)
from server.training.node_manager import NodeManager
from server.training.memory_manager import MemoryManager
from server.training.response_variations import (
    VariationRotator,
    apply_response_variations,
)

logger = logging.getLogger(__name__)

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
})


def _is_stuck_loop(recent_responses: list, n: int = 4) -> bool:
    """Return True if the last n bot responses are identical after stripping tool tags."""
    if len(recent_responses) < n:
        return False
    stripped = [re.sub(r"\[TOOL:\w+\]", "", r).strip() for r in recent_responses[-n:]]
    return len(set(stripped)) == 1


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
        logger.warning("  POLICY BLOCKED create_reservation (check_availability not in all_tools)")
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
        result = await processor.process_turn("Ich möchte Bibimbap bestellen")
        # Use result.clean_text for TTS, result.should_end for hangup
    """

    def __init__(
        self,
        tenant_id: Optional[str],
        call_sid: str,
        session,  # CallSession | None
        caller_phone: str = "",
    ):
        self.tenant_id = tenant_id
        self.call_sid = call_sid
        self.session = session
        self.caller_phone = caller_phone

        # All state is instance-level — no shared module-level state
        self.state = ConversationState()
        self.memory = MemoryManager(max_recent_turns=5)
        self.node_mgr = NodeManager()
        self.all_tools: List[str] = []
        self.turn_idx: int = 0
        self._variation_rotator = VariationRotator()  # Anti-repetition

        # Serialise concurrent callers: _adk_turn0_init() (background state bookkeeping)
        # and the first real user turn may overlap. Without a lock they'd both run
        # process_turn() at turn_idx=0 → duplicate ai_greeting + state corruption.
        self._turn_lock = asyncio.Lock()

        # Lazy-initialized Gemini runner (LLM client only — no AudioInjector/TTS)
        self._gemini_runner = None

        # Per-turn observability trace (LayerTrace); read by brain_service during
        # metrics accumulation to persist layer1_decision/layer2_raw_output/layer3_changes.
        self._current_layer_trace = None
        # Per-turn ExecutionSpan trace (Phase 2); read by brain_service for the
        # google_turn_spans table / execution_trace exposure.
        self._span_collector = None
        self._execution_spans = []

    def _get_gemini_runner(self):
        """Lazy-initialize Tier2AudioRunner for LLM calls only."""
        if self._gemini_runner is None:
            from server.training.tier2_runner import Tier2AudioRunner
            # Match server/main.py: GOOGLE_CLOUD_PROJECT is the canonical Vertex project id.
            project_id = (
                os.environ.get("GOOGLE_CLOUD_PROJECT")
                or os.environ.get("GOOGLE_PROJECT_ID")
                or "sailly-voice-agent-eu"
            )
            deepgram_key = os.environ.get("DEEPGRAM_API_KEY", "")
            self._gemini_runner = Tier2AudioRunner(
                google_project_id=project_id,
                deepgram_api_key=deepgram_key,
                temperature=0.0,
            )
            # Pre-initialize LLM client to avoid cold-start on first turn
            try:
                self._gemini_runner._init_clients()
            except Exception as e:
                logger.warning(f"[ADKTurn] Gemini runner pre-init failed (will retry on first turn): {e}")
        return self._gemini_runner

    async def process_turn(self, user_text: str) -> TurnResult:
        """
        Process one user utterance through the full validated pipeline.

        Steps mirror ADKRunner.run() per-turn body exactly:
        1.  update_state_from_utterance
        2.  select_node
        3.  check_prerequisites → forced_tools
        4.  build_context (per-node prompt + state + history)
        5.  _call_gemini_lm
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
            return await self._process_turn_locked(user_text)

    async def _process_turn_locked(self, user_text: str) -> TurnResult:
        """Actual turn logic — called only while _turn_lock is held."""
        try:
            result = await self._process_turn_inner(user_text)
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
            # Populate LayerTrace for error fallback path (must happen on ALL exit paths)
            try:
                from server.brain.contracts.trace import LayerTrace
                trace = LayerTrace(turn_idx=self.turn_idx, call_sid=self.call_sid)
                trace.layer1_node = "error_fallback"
                trace.layer2_raw_output = result.raw_response[:500]
                self._current_layer_trace = trace
            except Exception:
                self._current_layer_trace = None

        # Persist after every turn (even errors) so reconnect can restore
        try:
            await self.persist_state()
        except Exception as e:
            logger.warning(f"[ADKTurn] State persist failed: {e}")

        return result

    async def _process_turn_inner(self, user_text: str) -> TurnResult:
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
        gemini_runner = self._get_gemini_runner()

        # Initialize return values in case of early exception inside try block
        tool_results: dict = {}
        missing_fields_hint: Optional[str] = None
        should_end: bool = False
        end_reason: str = ""
        turn_tools: List[str] = []
        bot_response: str = ""
        # Reset per-turn observability trace so a stale trace can't leak forward.
        self._current_layer_trace = None
        # Initialize TurnTimings for per-stage latency instrumentation
        from server.brain.contracts.turn_timings import TurnTimings
        self.state._turn_timings = TurnTimings()
        # Phase 2: per-turn ExecutionSpan collector (OTel gen_ai-shaped). t0 anchors
        # all relative timings. Defensive — never breaks the live turn.
        import time as _time_mod
        from server.brain.contracts.trace import TurnSpanCollector

        self._span_collector = TurnSpanCollector(_time_mod.monotonic())
        self._execution_spans = []

        # ── Update state from customer utterance ─────────────── [validated ~251]
        update_state_from_utterance(self.state, user_text)

        # ── NODE SELECTION (code, not LLM) ──────────────────── [validated ~254]
        _span_t = self._span_collector.now_ms()
        node = self.node_mgr.select_node(self.state, user_text)
        self._span_collector.add(
            1, "classify", f"select_node → {node.name}", _span_t, io={"node": node.name}
        )

        # ── Prerequisites (forced tools BEFORE LLM) ─────────── [validated ~258]
        _span_t = self._span_collector.now_ms()
        forced_tools = self.node_mgr.check_prerequisites(node, self.state)
        self._span_collector.add(
            1, "prereq", "check_prerequisites", _span_t,
            io={"forced_tools": list(forced_tools or [])},
        )

        # ── Build context with memory compression ────────────── [validated ~261]
        context_prompt = self.memory.build_context(
            node.prompt,
            self.state,
            prereq_results=[f"[TOOL:{t}]" for t in forced_tools] if forced_tools else None,
        )

        try:
            gemini_runner._active_prompt_override = context_prompt  # [validated ~274]

            # ── Call Gemini with node's micro-prompt ─────────── [validated ~278]
            _span_t = self._span_collector.now_ms()
            bot_response = await gemini_runner._call_gemini_lm(
                user_message=user_text,
                context=self.memory.build_history(),
            )
            self._span_collector.add(
                2, "chat", "TinyGenerator LLM", _span_t,
                model=(
                    getattr(gemini_runner, "model", None)
                    or getattr(gemini_runner, "_model_name", None)
                ),
                io={"chars_out": len(bot_response or "")},
            )
            # Stamp l2_done_at (LLM call complete)
            if self.state._turn_timings:
                self.state._turn_timings.l2_done_at = _time_mod.monotonic()

            # Parse tool calls from response [validated ~286]
            turn_tools = list(gemini_runner._parse_tool_calls(bot_response))

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
            if (
                "get_menu" not in self.all_tools
                and "get_menu" not in turn_tools
                and (self.state.order_intent or self.state.selected_dish)
            ):
                bot_response = "[TOOL:get_menu] " + bot_response
                turn_tools.insert(0, "get_menu")

            # Phone prompt injection [validated ~382] — BEFORE check_forced_commits
            if self.state.should_prompt_for_phone():
                br_low = bot_response.lower()
                if "telefon" not in br_low and "nummer" not in br_low:
                    bot_response = (
                        bot_response.rstrip()
                        + f"\n\nDarf ich Ihre Telefonnummer für "
                        f"die Bestellung von "
                        f"{self.state.selected_dish} notieren?"
                    )

            # ── FORCED COMMITS (code overrides LLM) ──────────── [validated ~396]
            logger.info(
                f"  T{self.turn_idx}: PRE-forced_commits state flags - "
                f"escalation_requested={getattr(self.state, 'escalation_requested', '?')}, "
                f"request_callback_called={getattr(self.state, 'request_callback_called', '?')}, "
                f"transfer_to_tier2_called={getattr(self.state, 'transfer_to_tier2_called', '?')}"
            )
            _span_t = self._span_collector.now_ms()
            bot_response = self.node_mgr.check_forced_commits(
                self.state, bot_response, self.turn_idx, user_text, self.all_tools
            )
            self._span_collector.add(1, "commit_gate", "check_forced_commits", _span_t)
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
                turn_tools = [t for t in turn_tools if t != "send_sms"]
                bot_response = re.sub(
                    r"\[TOOL:send_sms\]", "", bot_response, flags=re.IGNORECASE
                ).strip()
                logger.warning(f"  T{self.turn_idx}: POST-PARSE dedup send_sms")

            # ── A2: Validation layer — policy guard ───────────── [validated ~430]
            # Final gate: blocks structurally invalid calls even if
            # forced commits or LLM erroneously included them.
            _span_t = self._span_collector.now_ms()
            validated_tools = [t for t in turn_tools if _validate_tool_call(t, self.state, self.all_tools)]
            blocked_tools = set(turn_tools) - set(validated_tools)
            if blocked_tools:
                for _bt in blocked_tools:
                    bot_response = re.sub(
                        rf"\[TOOL:{re.escape(_bt)}\]", "", bot_response, flags=re.IGNORECASE
                    ).strip()
                    logger.warning(f"  T{self.turn_idx}: POLICY BLOCKED {_bt}")
                turn_tools = validated_tools
            self._span_collector.add(
                3, "policy", "validate_tool_call", _span_t,
                status="blocked" if blocked_tools else "ok",
                io={"blocked": sorted(blocked_tools), "allowed": list(validated_tools)},
            )

            # Track state from final tools [validated ~444]
            if "ai_greeting" in turn_tools:
                self.state.ai_greeting_called = True
            if "create_order" in turn_tools:
                self.state.order_created = True
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

            for tool_name in list(turn_tools):
                args, error_msg = self._build_tool_args(tool_name)
                if error_msg:
                    # Required fields missing — do not execute, inject hint to LLM next turn
                    logger.warning(f"  T{self.turn_idx}: TOOL BLOCKED ({tool_name}) — {error_msg}")
                    missing_fields_hint = error_msg
                    bot_response = re.sub(
                        rf"\[TOOL:{re.escape(tool_name)}\]", "", bot_response, flags=re.IGNORECASE
                    ).strip()
                    failed_tool_names.add(tool_name)
                    continue

                if args is not None:
                    _span_t = self._span_collector.now_ms()
                    try:
                        from tools.executor import execute_tool
                        result = await execute_tool(tool_name, args, self.call_sid, self.tenant_id)
                        tool_results[tool_name] = result
                        self._span_collector.add(
                            1, "execute_tool", tool_name, _span_t,
                            io={"args_keys": sorted(args.keys())},
                        )
                        logger.info(f"  T{self.turn_idx}: TOOL executed: {tool_name} -> {str(result)[:100]}")
                        if self.session:
                            try:
                                await self.session.add_tool_call(tool_name, args, result, 0)
                            except Exception as _se:
                                logger.warning(f"[ADKTurn] Session tool_call log failed: {_se}")
                    except Exception as exec_err:
                        self._span_collector.add(
                            1, "execute_tool", tool_name, _span_t,
                            status="error", io={"error": str(exec_err)[:200]},
                        )
                        logger.error(f"  T{self.turn_idx}: TOOL error ({tool_name}): {exec_err}", exc_info=True)
                        tool_results[tool_name] = {"error": str(exec_err)}
                        bot_response = re.sub(
                            rf"\[TOOL:{re.escape(tool_name)}\]", "", bot_response, flags=re.IGNORECASE
                        ).strip()
                        if not missing_fields_hint:
                            missing_fields_hint = f"Werkzeugfehler bei {tool_name}: Bitte versuchen Sie es erneut."
                        failed_tool_names.add(tool_name)
                # args is None → no-op tool (ai_greeting, faq, etc.) — counts as executed

            # Remove failed/blocked tools so loop escape and all_tools are accurate
            if failed_tool_names:
                turn_tools = [t for t in turn_tools if t not in failed_tool_names]
            
            # Stamp tool_done_at (all tools executed)
            if self.state._turn_timings:
                self.state._turn_timings.tool_done_at = _time_mod.monotonic()

            # ── Loop escape hatch ──────────────────────────────── [validated ~462]
            # A3: Raised from 5 to 8 turns to reduce premature end_call.
            # Pending-intent guard: never force end_call while an unfulfilled
            # order or reservation intent is active.
            if (
                self.node_mgr._turns_in_node >= 8
                and not _COMMIT_TOOLS.intersection(set(turn_tools))
                and "end_call" not in self.all_tools
                and not (self.state.order_intent and not self.state.order_created)
                and not (self.state.reservation_intent and not self.state.reservation_created)
            ):
                bot_response = (
                    "Vielen Dank für Ihren Anruf bei DOBOO! Auf Wiedersehen."
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

            # ── Stuck-loop detector (4 identical responses) ──── [validated ~486]
            elif _is_stuck_loop(self.state.recent_responses):
                bot_response = (
                    "Vielen Dank für Ihren Anruf bei DOBOO! Auf Wiedersehen."
                    "\n[TOOL:end_call]"
                )
                turn_tools = ["end_call"]
                should_end = True
                end_reason = "forced_end_loop"
                self.node_mgr.current_node_name = "goodbye"
                logger.warning(
                    f"  T{self.turn_idx}: STUCK LOOP — 4 identical responses, forcing end_call"
                )
                # [PRODUCTION] Execute end_call — main execute loop already finished above
                try:
                    from tools.executor import execute_tool
                    await execute_tool("end_call", {"reason": "stuck_loop"}, self.call_sid, self.tenant_id)
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
            if not should_end and bot_response:
                _FAREWELL_PATTERNS = (
                    "auf wiedersehen", "tschüs", "tschüss", "bis bald", "einen schönen tag",
                    "schönen tag noch", "guten tag noch", "auf wiederhören", "bye", "goodbye",
                )
                if any(p in bot_response.lower() for p in _FAREWELL_PATTERNS):
                    should_end = True
                    end_reason = "farewell_text"
                    turn_tools = list(turn_tools) + ["end_call"]
                    logger.info(f"  T{self.turn_idx}: farewell detected in text → auto end_call")
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
            bot_response = apply_response_variations(
                bot_response,
                recent,
                self._variation_rotator,
            )
            self.state.recent_responses.append(bot_response)  # store VARIED text
            if len(self.state.recent_responses) > 12:
                self.state.recent_responses = self.state.recent_responses[-12:]

            self.all_tools.extend(turn_tools)  # [validated ~512]

        except Exception as llm_err:  # [validated ~514]
            bot_response = "Entschuldigung, ich habe ein technisches Problem."
            turn_tools = []
            logger.warning(f"  Turn {self.turn_idx} LLM error: {llm_err}")
        finally:
            gemini_runner._active_prompt_override = None  # [validated ~523]

        # [PRODUCTION] Record turn + increment counter (validated does this outside the try too)
        self.memory.record_turn(user_text, bot_response, node.name)
        self.turn_idx += 1

        # Strip [TOOL:...] tags for TTS
        clean_text = re.sub(r"\[TOOL:\w+\]\s*", "", bot_response).strip()

        # ── LayerTrace observability (populates google_turn_metrics.layer1_decision /
        #    layer2_raw_output / layer3_changes) ──────────────────────────────────
        # This is the LIVE processor; brain_service reads _tp._current_layer_trace
        # during metrics accumulation. Without this the per-layer columns stay NULL.
        # Additive only — no behaviour change. Layer 3 stays honest "empty" until a
        # real policy layer exists.
        try:
            import hashlib
            from server.brain.contracts.trace import LayerTrace

            trace = LayerTrace(turn_idx=self.turn_idx, call_sid=self.call_sid)
            # Layer 1 (Orchestrator): selected node, forced tools, state hash.
            trace.layer1_node = node.name
            trace.layer1_forced_tools = list(forced_tools or [])
            _snap = "|".join(
                str(getattr(self.state, _f, None))
                for _f in (
                    "customer_name",
                    "selected_dish",
                    "order_items",
                    "reservation_date",
                    "reservation_time",
                    "party_size",
                    "phone_number",
                )
            )
            trace.layer1_state_hash = hashlib.md5(_snap.encode()).hexdigest()[:16]
            # Layer 2 (LLM): raw model output (truncated; final text after tag-strip
            # is bot_text). Raw is not separated from final in this pipeline.
            trace.layer2_raw_output = (bot_response or "")[:500]
            # Layer 3 (Policy): no dedicated policy layer yet — leave honest empty.
            self._current_layer_trace = trace
        except Exception as _trace_err:
            logger.debug("[ADKTurn] LayerTrace build skipped: %s", _trace_err)
            self._current_layer_trace = None

        # Phase 2: freeze the per-turn ExecutionSpan trace for persistence.
        try:
            self._execution_spans = list(getattr(self._span_collector, "spans", []) or [])
        except Exception:
            self._execution_spans = []

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
            missing = []
            if not state.selected_dish:
                missing.append("Gericht (welches Gericht möchten Sie?)")
            if not state.customer_name:
                missing.append("Name")
            if missing:
                return None, f"Bitte fragen Sie den Kunden nach: {', '.join(missing)}"
            return {
                "name": state.customer_name,
                "phone": state.phone_number or self.caller_phone or "",
                "messaging_phone": state.phone_number or self.caller_phone or "",
                "order_items": state.selected_dish,
                "order_type": "delivery" if state.delivery_address_mentioned else "takeaway",
                "payment_method": "bar",
                "total_price": 0.0,  # Will be calculated by executor if needed
                "delivery_address": getattr(state, "delivery_address", "") or "",
            }, None

        elif tool_name == "create_reservation":
            missing = []
            if not state.party_size:
                missing.append("Personenzahl (für wie viele Personen?)")
            if not state.reservation_date:
                missing.append("Datum (für welchen Tag?)")
            if missing:
                return None, f"Bitte fragen Sie den Kunden nach: {', '.join(missing)}"
            return {
                "date": state.reservation_date,
                "time": state.reservation_time or "19:00",
                "party_size": state.party_size,
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
            if not delivery_addr or not delivery_addr.strip():
                return None, "Bitte fragen Sie den Kunden nach seiner Adresse."
            return {
                "address": delivery_addr,
                "city": "Bonn",
            }, None

        elif tool_name == "get_menu":
            return {"category": "alle"}, None

        elif tool_name == "get_date_info":
            return {"date": state.reservation_date or "heute"}, None

        elif tool_name == "get_weather":
            return {"location": "Bonn"}, None

        elif tool_name == "get_restaurant_info":
            return {"query": "allgemein"}, None

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

            processor = cls(tenant_id=tenant_id, call_sid=call_sid, session=session, caller_phone=caller_phone)
            processor.state = _conversation_state_from_dict(blob.get("state", {}))
            processor.memory = _memory_manager_from_dict(blob.get("memory", {}))
            processor.all_tools = blob.get("all_tools", [])
            processor.turn_idx = blob.get("turn_idx", 0)
            processor.state.recent_responses = blob.get("recent_responses", [])

            node_blob = blob.get("node_mgr", {})
            processor.node_mgr.current_node_name = node_blob.get("current_node", "greeting")
            processor.node_mgr._turns_in_node = node_blob.get("turns_in_node", 0)
            processor.node_mgr.node_stack = node_blob.get("node_stack", [])

            logger.info(f"[ADKTurn] Restored session at turn {processor.turn_idx}, node={processor.node_mgr.current_node_name}")
            return processor
        except Exception as e:
            logger.warning(f"[ADKTurn] restore_from_session failed: {e}")
            return None


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
        max_summary_words=d.get("max_summary_words", 80),
    )
    manager.recent_turns = d.get("recent_turns", [])
    manager.context_summary = d.get("context_summary", "")
    return manager
