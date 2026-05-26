"""
One-Live Loop Runner — State-machine micro-prompts for Sailly.

Wraps the existing ConversationLoop but overrides the Gemini call path:
instead of one 74-line monolithic prompt with 16 tools, each turn uses a
phase-specific micro-prompt (5-10 lines) with 2-3 tools.

The key difference: determine_phase() (code) decides which phase/prompt to use,
NOT the LLM. The LLM only has to understand language and respond naturally
within a narrow, focused context.
"""

import logging
import re
import time
from typing import List, Dict, Optional

from server.training.conversation_loop import (
    ConversationLoop,
    ConvTurn,
    ConvResult,
    END_PHRASES,
    MIN_TURNS_BY_PHASE,
    MAX_TURNS_BY_PHASE,
)
from server.training.conversation_state import (
    ConversationState,
    update_state_from_utterance,
    update_state_after_bot,
)
from server.training.response_variations import (
    VariationRotator,
    apply_response_variations,
)
from server.training.state_prompts import PHASES, determine_phase

logger = logging.getLogger(__name__)


class OneLiveRunner(ConversationLoop):
    """
    One-Live Loop: state-machine architecture with micro-prompts.

    Inherits from ConversationLoop to reuse the audio pipeline, GPT caller,
    STT/TTS, and scenario infrastructure. Overrides `run()` to swap the
    Gemini system prompt per turn based on deterministic phase transitions.
    """

    async def run(self, scenario, phase: int, run_number: int) -> ConvResult:
        """
        Run a full conversation using state-machine micro-prompts.

        Same interface as ConversationLoop.run() so the A/B harness can
        treat both runners identically.
        """
        t_conv_start = time.time()

        turns: List[ConvTurn] = []
        all_tools: List[str] = []
        total_audio = 0
        gpt_history: List[Dict] = []

        scripted = [t.user_utterance for t in scenario.turns if t.user_utterance.strip()]
        min_turns = MIN_TURNS_BY_PHASE.get(phase, 10)
        max_turns_cap = MAX_TURNS_BY_PHASE.get(phase, self.max_turns)

        end_reason = "max_turns"
        error_msg = None
        state = ConversationState()
        current_phase = "GREETING"
        phase_history: List[str] = []

        try:
            for turn_idx in range(max_turns_cap):
                t_turn_start = time.time()
                effective_min = (
                    4 if (state.order_created or state.reservation_created) else min_turns
                )

                # ── Caller utterance ──────────────────────────────────
                if turn_idx < len(scripted):
                    caller_text = scripted[turn_idx]
                else:
                    caller_text = await self._generate_caller_turn(
                        scenario, gpt_history, turn_idx, effective_min
                    )

                caller_lower = caller_text.lower()
                if any(phrase in caller_lower for phrase in END_PHRASES):
                    if turn_idx + 1 >= effective_min:
                        end_reason = "goodbye"
                        break
                    else:
                        remaining = effective_min - (turn_idx + 1)
                        caller_text = await self._generate_caller_turn(
                            scenario,
                            gpt_history + [{
                                "role": "system",
                                "content": (
                                    f"Du hast noch {remaining} weitere Fragen. "
                                    f"Verabschiede dich NICHT — stelle stattdessen eine neue Frage "
                                    f"zum Restaurant, Menü, Öffnungszeiten oder deiner Bestellung."
                                )
                            }],
                            turn_idx,
                        )

                # ── Audio pipeline: TTS → STT ─────────────────────────
                t_caller = time.time()
                try:
                    audio_seg, stt_transcript, wer = await self.audio_injector.inject_caller_turn(
                        user_utterance=caller_text,
                        noise_variant=getattr(scenario, "noise_variant", "clean"),
                        stt_min_accuracy=self.stt_threshold,
                    )
                    caller_lat = (time.time() - t_caller) * 1000
                    turn_passed = True
                except Exception as stt_err:
                    stt_transcript = caller_text
                    wer = 0.0
                    caller_lat = (time.time() - t_caller) * 1000
                    turn_passed = False
                    logger.warning(f"  Turn {turn_idx} STT error (using raw text): {stt_err}")

                # ── State update from customer utterance ──────────────
                update_state_from_utterance(state, stt_transcript)

                # ── DETERMINISTIC PHASE TRANSITION (code, not LLM) ────
                current_phase = determine_phase(state, stt_transcript)
                phase_config = PHASES[current_phase]
                phase_history.append(current_phase)

                # ── Swap system prompt to micro-prompt ────────────────
                self.gemini_runner._active_prompt_override = phase_config.prompt

                # ── Call Gemini with micro-prompt ─────────────────────
                t_bot = time.time()
                try:
                    bot_response = await self.gemini_runner._call_gemini_lm(
                        user_message=stt_transcript,
                        context=gpt_history[-20:],
                    )

                    turn_tools = list(self.gemini_runner._parse_tool_calls(bot_response))

                    # Filter tools not in current phase's available set
                    allowed = set(phase_config.available_tools)
                    turn_tools = [t for t in turn_tools if t in allowed]

                    # Deduplicate get_menu
                    if "get_menu" in turn_tools and "get_menu" in all_tools:
                        turn_tools = [t for t in turn_tools if t != "get_menu"]
                        bot_response = re.sub(r"\[TOOL:get_menu\]", "", bot_response, flags=re.IGNORECASE).strip()

                    update_state_after_bot(state, bot_response)

                    # Track state from tools
                    if "get_menu" in turn_tools:
                        state.menu_fetched = True
                    if "check_availability" in turn_tools:
                        state.check_availability_called = True
                    if "create_order" in turn_tools:
                        state.order_created = True
                    if "create_reservation" in turn_tools:
                        state.reservation_created = True

                    # Phase-specific forced commits
                    if current_phase == "TAKING_ORDER":
                        if (
                            state.ready_for_order_commit()
                            and "create_order" not in turn_tools
                        ):
                            bot_response = bot_response.rstrip() + "\n[TOOL:create_order]\n[TOOL:send_sms]"
                            turn_tools.extend(["create_order", "send_sms"])
                            state.order_created = True

                    if current_phase == "MAKING_RESERVATION":
                        if (
                            state.reservation_intent
                            and state.check_availability_called
                            and state.party_size is not None
                            and not state.reservation_created
                            and "create_reservation" not in turn_tools
                        ):
                            # Check for confirmation words
                            if any(w in stt_transcript.lower() for w in ["ja", "bitte", "genau", "stimmt", "richtig", "passt"]):
                                bot_response = bot_response.rstrip() + "\n[TOOL:create_reservation]"
                                turn_tools.append("create_reservation")
                                state.reservation_created = True

                        # Auto-inject check_availability if not yet called
                        if (
                            state.reservation_intent
                            and not state.check_availability_called
                            and "check_availability" not in turn_tools
                        ):
                            bot_response = "[TOOL:check_availability] " + bot_response
                            turn_tools.insert(0, "check_availability")
                            state.check_availability_called = True

                    # Anti-repetition
                    recent = state.recent_responses[-8:]
                    bot_response = apply_response_variations(
                        bot_response, recent, self._variation_rotator,
                    )
                    state.recent_responses.append(bot_response)
                    if len(state.recent_responses) > 12:
                        state.recent_responses = state.recent_responses[-12:]

                    all_tools.extend(turn_tools)
                except Exception as llm_err:
                    bot_response = "Entschuldigung, ich habe ein technisches Problem."
                    turn_tools = []
                    logger.warning(f"  Turn {turn_idx} LLM error: {llm_err}")

                # ── TTS ───────────────────────────────────────────────
                try:
                    tts_audio, _ = await self.gemini_runner._synthesize_response(bot_response)
                    tts_bytes = len(tts_audio)
                    total_audio += tts_bytes
                except Exception:
                    tts_bytes = 0

                bot_lat = (time.time() - t_bot) * 1000
                turn_lat = (time.time() - t_turn_start) * 1000

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

                gpt_history.append({"role": "assistant", "content": caller_text})
                gpt_history.append({"role": "user", "content": bot_response})

                logger.debug(
                    f"    T{turn_idx} [{current_phase}]: caller={caller_text[:40]!r} | "
                    f"bot={bot_response[:50]!r} | tools={turn_tools} | {turn_lat:.0f}ms"
                )

                if self._is_end_call(turn_tools, bot_response):
                    if turn_idx + 1 >= effective_min:
                        end_reason = "end_call_tool" if "end_call" in turn_tools else "goodbye"
                        break

        except Exception as e:
            error_msg = str(e)
            end_reason = "error"
            logger.error(f"One-Live conversation error at turn {len(turns)}: {e}")
        finally:
            # Restore prompt override so it doesn't leak to other runners
            self.gemini_runner._active_prompt_override = None

        total_lat = (time.time() - t_conv_start) * 1000
        expected = list(getattr(scenario, "expected_tools", []) or [])
        tools_ok = all(t in all_tools for t in expected) if expected else True
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

        # Attach phase history for analysis
        result._phase_history = phase_history  # type: ignore[attr-defined]

        return result
