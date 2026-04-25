"""
ADK-based conversation runner for Sailly.

Replaces both tier2_runner.py (monolithic prompt) and live_runner.py
(rigid state machine) with a node-based architecture:
- Code selects the active node (prompt + tools) per turn
- Gemini talks freely within each node
- Forced commits inject tools when state is complete

Reuses existing infrastructure:
- Tier2AudioRunner for Gemini LLM client + TTS
- ConversationLoop for GPT-4o-mini caller + audio pipeline + STT
- ToolExecutor for mock tool execution
- call_auditor_de.py for scoring (unchanged)

Interface: subclasses ConversationLoop, overrides run() to swap in
node-based prompt selection instead of monolithic prompt.
"""

from __future__ import annotations

import logging
import re
import time
from typing import List, Dict, Optional

from server.brain.conversation_loop import (
    ConversationLoop,
    ConvTurn,
    ConvResult,
    END_PHRASES,
    MIN_TURNS_BY_PHASE,
    MAX_TURNS_BY_PHASE,
)
from server.brain.conversation_state import (
    ConversationState,
    update_state_from_utterance,
    update_state_after_bot,
)
from server.brain.response_variations import (
    VariationRotator,
    apply_response_variations,
)
from server.brain.node_manager import NodeManager
from server.brain.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

# A3/A5: Expanded to all meaningful tools — keeps escape hatch from misfiring
# when data-retrieval tools are the only activity in a turn.
_COMMIT_TOOLS = frozenset({
    "create_order", "create_reservation", "verify_address",
    "end_call", "send_sms", "check_availability",
    "get_date_info", "get_weather", "get_menu",
    "transfer_to_tier2", "technical_issues_callback",
    "transfer_to_human", "request_callback", "faq",
})


def _is_stuck_loop(recent_responses: list, n: int = 4) -> bool:
    """Return True if the last n bot responses are identical after stripping tool tags."""
    if len(recent_responses) < n:
        return False
    stripped = [re.sub(r"\[TOOL:\w+\]", "", r).strip() for r in recent_responses[-n:]]
    return len(set(stripped)) == 1


def _validate_tool_call(tool: str, state: "ConversationState", all_tools: list) -> bool:
    """
    A2: Policy guard — final gate between forced commits and tool execution.

    Blocks:
    1. create_order without a valid dish (prevents hallucinated orders from 5-char prefix)
       EXCEPTION: if check_forced_commits already set state.order_created=True this turn,
       the forced commit system explicitly approved the order — allow it through.
    2. end_call when an active, unfulfilled intent exists (prevents premature hang-up)
    3. create_reservation before check_availability has been confirmed in a PREVIOUS turn.
       Uses all_tools (previous turns only — extended after this gate runs) rather than
       state.check_availability_called, which can be set in the same turn and would
       allow create_reservation and check_availability to fire together.

    Cross-turn duplicate prevention is handled separately by the post-reparse dedup
    logic using `all_tools`. We do NOT check state.order_created or
    state.reservation_created here because check_forced_commits sets those flags
    in the SAME turn before this runs — checking them would incorrectly block the
    very tool we just committed.
    """
    import logging as _log
    _logger = _log.getLogger(__name__)

    if tool == "create_order" and not state.selected_dish:
        # Fix 1 (Iteration 6): If the forced commit system already approved this order
        # (state.order_created was set to True in check_forced_commits this same turn),
        # allow it through even without a dish. The forced commit is intentional.
        # Without this, every forced create_order injection was silently stripped here.
        if state.order_created:
            _logger.info(
                "  POLICY: Allowing create_order (forced commit approved, selected_dish=None)"
            )
            return True
        _logger.warning(
            "  POLICY BLOCKED create_order (selected_dish=None, order_created=False — LLM hallucination)"
        )
        return False
    if tool == "end_call":
        if state.order_intent and not state.order_created:
            return False
        if state.reservation_intent and not state.reservation_created:
            return False
    # Fix A (Iter 8): fix-res-05 CRITICAL FLOW — block create_reservation unless
    # check_availability has been confirmed in a PREVIOUS turn (i.e. it's in all_tools,
    # which is extended AFTER this gate runs, so it only contains prior-turn tools).
    # Using all_tools instead of state.check_availability_called prevents the same-turn
    # co-fire issue where block 3 of check_forced_commits sets the flag and immediately
    # allows create_reservation through in the same turn.
    if tool == "create_reservation" and "check_availability" not in all_tools:
        _logger.warning(
            "  POLICY BLOCKED create_reservation (check_availability not in all_tools from previous turns — CRITICAL FLOW, Iter 8)"
        )
        return False
    return True


class ADKRunner(ConversationLoop):
    """
    Node-based conversation runner.

    Inherits the full audio pipeline from ConversationLoop:
    - GPT-4o-mini caller generation
    - Deepgram STT
    - Gemini Flash TTS (configurable via TTS_ENGINE env var)
    - Turn recording

    Overrides only the prompt/tool selection logic:
    - NodeManager selects which node (prompt + tools) is active
    - MemoryManager compresses context for each turn
    - Forced commits inject tools when state is complete
    """

    async def run(
        self, scenario, phase: int, run_number: int
    ) -> ConvResult:
        t_conv_start = time.time()

        turns: List[ConvTurn] = []
        all_tools: List[str] = []
        total_audio = 0

        gpt_history: List[Dict] = []
        scripted = [
            t.user_utterance
            for t in scenario.turns
            if t.user_utterance.strip()
        ]

        min_turns = MIN_TURNS_BY_PHASE.get(phase, 10)
        max_turns_cap = MAX_TURNS_BY_PHASE.get(phase, self.max_turns)

        end_reason = "max_turns"
        error_msg = None

        state = ConversationState()
        node_mgr = NodeManager()
        memory = MemoryManager()
        node_history: List[str] = []

        try:
            for turn_idx in range(max_turns_cap):
                t_turn_start = time.time()
                effective_min = (
                    2
                    if (state.order_created or state.reservation_created)
                    else min_turns
                )

                # ── Caller utterance ──────────────────────────────────
                if turn_idx < len(scripted):
                    caller_text = scripted[turn_idx]
                else:
                    caller_text = await self._generate_caller_turn(
                        scenario, gpt_history, turn_idx, effective_min
                    )

                caller_lower = caller_text.lower()
                if any(p in caller_lower for p in END_PHRASES):
                    if turn_idx + 1 >= effective_min:
                        end_reason = "goodbye"
                        # Record end_call as a natural goodbye — code ensures it
                        if "end_call" not in all_tools:
                            all_tools.append("end_call")
                            node_history.append("goodbye")
                            # Add synthetic turn so auditor sees end_call
                            turns.append(ConvTurn(
                                turn_idx=turn_idx,
                                caller_text=caller_text,
                                stt_transcript=caller_text,
                                wer=0.0,
                                bot_response="[TOOL:end_call]",
                                tts_bytes=0,
                                tools_called=["end_call"],
                                caller_latency_ms=0.0,
                                bot_latency_ms=0.0,
                                total_latency_ms=0.0,
                                passed=True,
                            ))
                        break
                    else:
                        remaining = effective_min - (turn_idx + 1)
                        caller_text = await self._generate_caller_turn(
                            scenario,
                            gpt_history
                            + [
                                {
                                    "role": "system",
                                    "content": (
                                        f"Du hast noch {remaining} Fragen. "
                                        "Verabschiede dich NICHT."
                                    ),
                                }
                            ],
                            turn_idx,
                        )

                # ── STT ───────────────────────────────────────────────
                t_caller = time.time()
                try:
                    (
                        audio_seg,
                        stt_transcript,
                        wer,
                    ) = await self.audio_injector.inject_caller_turn(
                        user_utterance=caller_text,
                        noise_variant=getattr(
                            scenario, "noise_variant", "clean"
                        ),
                        stt_min_accuracy=self.stt_threshold,
                    )
                    caller_lat = (time.time() - t_caller) * 1000
                    turn_passed = True
                except Exception as stt_err:
                    stt_transcript = caller_text
                    wer = 0.0
                    caller_lat = (time.time() - t_caller) * 1000
                    turn_passed = False
                    logger.warning(
                        f"  Turn {turn_idx} STT error (using raw text): "
                        f"{stt_err}"
                    )

                # ── Update state from customer utterance ──────────────
                update_state_from_utterance(state, stt_transcript)

                # ── NODE SELECTION (code, not LLM) ────────────────────
                node = node_mgr.select_node(state, stt_transcript)
                node_history.append(node.name)

                # ── Prerequisites (forced tools BEFORE LLM) ──────────
                forced_tools = node_mgr.check_prerequisites(node, state)

                # ── Build context with memory compression ─────────────
                context_prompt = memory.build_context(
                    node.prompt,
                    state,
                    prereq_results=[
                        f"[TOOL:{t}]" for t in forced_tools
                    ]
                    if forced_tools
                    else None,
                )

                # ── Call Gemini with node's micro-prompt ──────────────
                t_bot = time.time()
                try:
                    self.gemini_runner._active_prompt_override = (
                        context_prompt
                    )

                    bot_response = (
                        await self.gemini_runner._call_gemini_lm(
                            user_message=stt_transcript,
                            context=memory.build_history(),
                        )
                    )

                    # Parse tool calls from response
                    turn_tools = list(
                        self.gemini_runner._parse_tool_calls(bot_response)
                    )

                    # Add prerequisite tools
                    for ft in forced_tools:
                        if ft not in turn_tools:
                            turn_tools.insert(0, ft)
                            bot_response = f"[TOOL:{ft}] " + bot_response

                    # Filter to only tools available in this node
                    allowed = set(node.tools)
                    turn_tools = [t for t in turn_tools if t in allowed]

                    # Deduplicate get_menu across conversation
                    if "get_menu" in turn_tools and "get_menu" in all_tools:
                        turn_tools = [
                            t for t in turn_tools if t != "get_menu"
                        ]
                        bot_response = re.sub(
                            r"\[TOOL:get_menu\]",
                            "",
                            bot_response,
                            flags=re.IGNORECASE,
                        ).strip()

                    # Block duplicate create_order / send_sms (already committed in earlier turn)
                    if (
                        ("create_order" in turn_tools and "create_order" in all_tools)
                        or ("send_sms" in turn_tools and "send_sms" in all_tools)
                    ):
                        turn_tools = [t for t in turn_tools if t not in ("create_order", "send_sms")]
                        bot_response = re.sub(
                            r"\[TOOL:(?:create_order|send_sms)\]", "",
                            bot_response, flags=re.IGNORECASE
                        ).strip()
                        logger.warning(f"  T{turn_idx}: BLOCKED duplicate create_order/send_sms")

                    # Block duplicate get_date_info (already called in earlier turn)
                    if "get_date_info" in turn_tools and "get_date_info" in all_tools:
                        turn_tools = [t for t in turn_tools if t != "get_date_info"]
                        bot_response = re.sub(
                            r"\[TOOL:get_date_info\]", "",
                            bot_response, flags=re.IGNORECASE
                        ).strip()
                        logger.warning(f"  T{turn_idx}: BLOCKED duplicate get_date_info")

                    # Block duplicate create_reservation
                    if "create_reservation" in turn_tools and "create_reservation" in all_tools:
                        turn_tools = [t for t in turn_tools if t != "create_reservation"]
                        bot_response = re.sub(
                            r"\[TOOL:create_reservation\]", "",
                            bot_response, flags=re.IGNORECASE
                        ).strip()
                        logger.warning(f"  T{turn_idx}: BLOCKED duplicate create_reservation")

                    update_state_after_bot(state, bot_response)

                    # Whitelist: block create_order if no valid dish or already committed
                    if (
                        "create_order" in turn_tools
                        and (not state.selected_dish or state.order_created)
                    ):
                        reason = "no valid dish" if not state.selected_dish else "already committed"
                        logger.warning(
                            f"  T{turn_idx}: BLOCKED create_order ({reason})"
                        )
                        turn_tools = [
                            t
                            for t in turn_tools
                            if t not in ("create_order", "send_sms")
                        ]
                        bot_response = re.sub(
                            r"\[TOOL:(?:create_order|send_sms)\]",
                            "",
                            bot_response,
                            flags=re.IGNORECASE,
                        ).strip()

                    # Block create_reservation if already committed
                    if "create_reservation" in turn_tools and state.reservation_created:
                        logger.warning(f"  T{turn_idx}: BLOCKED create_reservation (already committed)")
                        turn_tools = [t for t in turn_tools if t != "create_reservation"]
                        bot_response = re.sub(
                            r"\[TOOL:create_reservation\]", "", bot_response, flags=re.IGNORECASE
                        ).strip()

                    # Auto-inject get_menu on first food turn
                    if (
                        "get_menu" not in all_tools
                        and "get_menu" not in turn_tools
                        and (state.order_intent or state.selected_dish)
                    ):
                        bot_response = "[TOOL:get_menu] " + bot_response
                        turn_tools.insert(0, "get_menu")

                    # Phone prompt injection
                    if state.should_prompt_for_phone():
                        br_low = bot_response.lower()
                        if (
                            "telefon" not in br_low
                            and "nummer" not in br_low
                        ):
                            bot_response = (
                                bot_response.rstrip()
                                + f"\n\nDarf ich Ihre Telefonnummer für "
                                f"die Bestellung von "
                                f"{state.selected_dish} notieren?"
                            )

                    # ── FORCED COMMITS (code overrides LLM) ──────────
                    # Fix 5: Verify state flags persist across turns
                    logger.info(f"  T{turn_idx}: PRE-forced_commits state flags - escalation_requested={getattr(state, 'escalation_requested', '?')}, request_callback_called={getattr(state, 'request_callback_called', '?')}, transfer_to_tier2_called={getattr(state, 'transfer_to_tier2_called', '?')}")
                    bot_response = node_mgr.check_forced_commits(
                        state, bot_response, turn_idx, stt_transcript, all_tools
                    )
                    logger.info(f"  T{turn_idx}: POST-forced_commits state flags - escalation_requested={getattr(state, 'escalation_requested', '?')}, request_callback_called={getattr(state, 'request_callback_called', '?')}, transfer_to_tier2_called={getattr(state, 'transfer_to_tier2_called', '?')}")

                    # Re-parse after forced commits
                    turn_tools = list(
                        self.gemini_runner._parse_tool_calls(bot_response)
                    )

                    # Post-reparse dedup: remove tools already called in previous turns
                    # Note: send_sms is NOT paired with create_order here — it may be
                    # legitimately needed in a later turn if it was missed alongside create_order.
                    for _dup_tool in ("create_order", "create_reservation", "get_date_info", "verify_address"):
                        if _dup_tool in turn_tools and _dup_tool in all_tools:
                            turn_tools = [t for t in turn_tools if t != _dup_tool]
                            bot_response = re.sub(
                                rf"\[TOOL:{_dup_tool}\]", "",
                                bot_response, flags=re.IGNORECASE
                            ).strip()
                            logger.warning(
                                f"  T{turn_idx}: POST-PARSE dedup {_dup_tool}"
                            )
                    # send_sms: only dedup if it was already sent (independent check)
                    if "send_sms" in turn_tools and "send_sms" in all_tools:
                        turn_tools = [t for t in turn_tools if t != "send_sms"]
                        bot_response = re.sub(
                            r"\[TOOL:send_sms\]", "", bot_response, flags=re.IGNORECASE
                        ).strip()
                        logger.warning(f"  T{turn_idx}: POST-PARSE dedup send_sms")

                    # ── A2: Validation layer — policy guard ───────────────
                    # Final gate: blocks structurally invalid calls even if
                    # forced commits or LLM erroneously included them.
                    validated_tools = [t for t in turn_tools if _validate_tool_call(t, state, all_tools)]
                    blocked_tools = set(turn_tools) - set(validated_tools)
                    if blocked_tools:
                        for _bt in blocked_tools:
                            bot_response = re.sub(
                                rf"\[TOOL:{re.escape(_bt)}\]", "",
                                bot_response, flags=re.IGNORECASE
                            ).strip()
                            logger.warning(f"  T{turn_idx}: POLICY BLOCKED {_bt}")
                        turn_tools = validated_tools

                    # Track state from final tools
                    if "ai_greeting" in turn_tools:
                        state.ai_greeting_called = True
                    if "create_order" in turn_tools:
                        state.order_created = True
                    if "create_reservation" in turn_tools:
                        state.reservation_created = True
                    if "get_menu" in turn_tools:
                        state.menu_fetched = True
                    if "check_availability" in turn_tools:
                        state.check_availability_called = True
                    if "get_date_info" in turn_tools:
                        state.get_date_info_called = True
                    if "verify_address" in turn_tools:
                        state.verify_address_called = True
                    if "get_weather" in turn_tools:
                        state.get_weather_called = True

                    # ── Loop escape hatch ─────────────────────────────
                    # A3: Raised from 5 to 8 turns to reduce premature end_call.
                    # Added pending-intent guard: never force end_call while an
                    # unfulfilled order or reservation intent is active
                    # (validation layer provides a second safety net).
                    if (
                        node_mgr._turns_in_node >= 8
                        and not _COMMIT_TOOLS.intersection(set(turn_tools))
                        and "end_call" not in all_tools
                        and not (state.order_intent and not state.order_created)
                        and not (state.reservation_intent and not state.reservation_created)
                    ):
                        bot_response = (
                            "Vielen Dank für Ihren Anruf bei DOBOO! Auf Wiedersehen."
                            "\n[TOOL:end_call]"
                        )
                        turn_tools = ["end_call"]
                        end_reason = "forced_end_loop"
                        logger.warning(
                            f"  T{turn_idx}: LOOP ESCAPE — "
                            f"{node_mgr._turns_in_node} turns in "
                            f"'{node_mgr.current_node_name}' with no commits"
                        )

                    # ── Stuck-loop detector (4 identical responses) ───────
                    elif _is_stuck_loop(state.recent_responses):
                        bot_response = (
                            "Vielen Dank für Ihren Anruf bei DOBOO! Auf Wiedersehen."
                            "\n[TOOL:end_call]"
                        )
                        turn_tools = ["end_call"]
                        end_reason = "forced_end_loop"
                        node_mgr.current_node_name = "goodbye"
                        logger.warning(
                            f"  T{turn_idx}: STUCK LOOP — 4 identical responses, forcing end_call"
                        )

                    # Anti-repetition
                    recent = state.recent_responses[-8:]
                    bot_response = apply_response_variations(
                        bot_response,
                        recent,
                        self._variation_rotator,
                    )
                    state.recent_responses.append(bot_response)
                    if len(state.recent_responses) > 12:
                        state.recent_responses = state.recent_responses[
                            -12:
                        ]

                    all_tools.extend(turn_tools)

                except Exception as llm_err:
                    bot_response = (
                        "Entschuldigung, ich habe ein technisches Problem."
                    )
                    turn_tools = []
                    logger.warning(
                        f"  Turn {turn_idx} LLM error: {llm_err}"
                    )
                finally:
                    self.gemini_runner._active_prompt_override = None

                # ── TTS ───────────────────────────────────────────────
                try:
                    tts_audio, _ = (
                        await self.gemini_runner._synthesize_response(
                            bot_response
                        )
                    )
                    tts_bytes = len(tts_audio)
                    total_audio += tts_bytes
                except Exception:
                    tts_bytes = 0

                bot_lat = (time.time() - t_bot) * 1000
                turn_lat = (time.time() - t_turn_start) * 1000

                # ── Record turn ───────────────────────────────────────
                turn_rec = ConvTurn(
                    turn_idx=turn_idx,
                    caller_text=caller_text,
                    stt_transcript=stt_transcript,
                    wer=wer,
                    bot_response=bot_response,
                    tts_bytes=tts_bytes,
                    tools_called=turn_tools,
                    caller_latency_ms=caller_lat,
                    bot_latency_ms=bot_lat,
                    total_latency_ms=turn_lat,
                    passed=turn_passed,
                )
                turns.append(turn_rec)

                # Record for memory manager
                memory.record_turn(
                    stt_transcript, bot_response, node.name
                )

                # GPT history (caller perspective)
                gpt_history.append(
                    {"role": "assistant", "content": caller_text}
                )
                gpt_history.append(
                    {"role": "user", "content": bot_response}
                )

                logger.debug(
                    f"    T{turn_idx} [{node.name}]: "
                    f"caller={caller_text[:40]!r} | "
                    f"bot={bot_response[:50]!r} | "
                    f"tools={turn_tools} | {turn_lat:.0f}ms"
                )

                # ── End conditions ────────────────────────────────────
                logger.info(f"  T{turn_idx}: DEBUG end_call check - end_call in turn_tools={'end_call' in turn_tools}, transfer_to_tier2 in all_tools={'transfer_to_tier2' in all_tools}, turn_idx={turn_idx}, effective_min={effective_min}")
                # Fix 5 (Iter 7): p3-angry-12 loop fix — if transfer_to_tier2 was already called
                # in a PREVIOUS turn, always end immediately regardless of end_call presence.
                # This prevents the scenario where transfer fires but end_call is absent/stripped.
                if all_tools.count("transfer_to_tier2") >= 1 and turn_idx >= 1:
                    end_reason = "transfer_to_tier2"
                    logger.info(f"  T{turn_idx}: ENDING — transfer_to_tier2 already in all_tools, terminating (p3-angry-12 fix)")
                    break
                if self._is_end_call(turn_tools, bot_response):
                    # Fix 4: If transfer_to_tier2 was called, always end immediately (don't wait for effective_min)
                    if "transfer_to_tier2" in all_tools:
                        end_reason = "transfer_to_tier2"
                        logger.info(f"  T{turn_idx}: ENDING due to transfer_to_tier2 (overriding effective_min={effective_min})")
                        break
                    elif turn_idx + 1 >= effective_min:
                        end_reason = (
                            "end_call_tool"
                            if "end_call" in turn_tools
                            else "goodbye"
                        )
                        logger.info(f"  T{turn_idx}: ENDING - turn_idx+1={turn_idx+1} >= effective_min={effective_min}, end_reason={end_reason}")
                        break
                    else:
                        remaining = effective_min - (turn_idx + 1)
                        logger.info(f"  T{turn_idx}: CONTINUING despite end_call - need {remaining} more turns")
                        gpt_history.append(
                            {
                                "role": "system",
                                "content": (
                                    f"Der Bot wollte beenden, aber du hast "
                                    f"noch {remaining} Fragen."
                                ),
                            }
                        )

        except Exception as e:
            error_msg = str(e)
            end_reason = "error"
            logger.error(
                f"Conversation error at turn {len(turns)}: {e}"
            )

        total_lat = (time.time() - t_conv_start) * 1000
        expected = list(
            getattr(scenario, "expected_tools", []) or []
        )

        tools_ok = (
            all(t in all_tools for t in expected) if expected else True
        )
        passed = tools_ok and len(turns) > 0 and error_msg is None

        result = ConvResult(
            scenario_id=scenario.id,
            phase=phase,
            run_number=run_number,
            turns=turns,
            tools_called=all_tools,
            expected_tools=expected,
            total_latency_ms=total_lat,
            total_audio_bytes=total_audio,
            passed=passed,
            end_reason=end_reason,
            error=error_msg,
        )
        result._node_history = node_history
        return result
