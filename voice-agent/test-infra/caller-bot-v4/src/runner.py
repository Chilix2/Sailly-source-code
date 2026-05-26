"""
src/runner.py — Per-scenario orchestrator

Runs one scenario: caller persona ↔ headless WS, end conditions, timeout.
"""
import asyncio
import logging
from typing import Optional

from .transport import HeadlessClient
from .persona import CallerPersona, PersonaResponse
from .scenario_loader import Scenario
from .metrics import fetch_call_metrics, derive_signals
from .verifier import Verifier

logger = logging.getLogger(__name__)


class ScenarioRunner:
    """Orchestrates one scenario run."""

    def __init__(
        self,
        scenario: Scenario,
        ws_url: str,
        pg_dsn: str,
        persona: CallerPersona,
        system_prompt_path: str,
    ):
        self.scenario = scenario
        self.ws_url = ws_url
        self.pg_dsn = pg_dsn
        self.persona = persona
        self.system_prompt_path = system_prompt_path

        self.client: Optional[HeadlessClient] = None
        self.call_sid: str = ""
        self.bot_responses: list[str] = []
        self.user_utterances: list[str] = []
        self.tools_fired_per_turn: list[list[str]] = []
        self.conversation_history: list[dict] = []
        self.turn_idx = 0
        self.per_turn_latency_ms: list[int] = []

    async def run(self) -> dict:
        """Run the scenario. Returns a result dict."""
        result = {
            "scenario_id": self.scenario.id,
            "call_sid": "",
            "passed": False,
            "turn_count": 0,
            "bot_responses": [],
            "user_utterances": [],
            "tools_fired": [],
            "latencies_ms": [],
            "verification_result": None,
            "error": None,
        }

        self.client = HeadlessClient(self.ws_url)

        try:
            # Connect
            self.call_sid = await self.client.connect()
            result["call_sid"] = self.call_sid
            logger.info(
                f"[Runner] {self.scenario.id} started: call_sid={self.call_sid}"
            )

            # Receive greeting
            greeting, greeting_tools = await asyncio.wait_for(
                self.client.receive_bot_turn(timeout_s=15.0), timeout=20.0
            )
            self.bot_responses.append(greeting)
            self.tools_fired_per_turn.append(greeting_tools)
            self.conversation_history.append({"role": "assistant", "content": greeting})
            logger.debug(f"[Runner] Greeting: {greeting[:80]!r}")

            # Main caller loop
            max_patience_turns = self.scenario.caller_patience_turns
            turn_timeout = 15.0
            # Scripted mode: use fixed utterance_sequence instead of LLM persona
            scripted_utterances = list(self.scenario.utterance_sequence or [])
            use_scripted = bool(scripted_utterances)
            scripted_idx = 0

            for turn_idx in range(1, max_patience_turns + 5):
                self.turn_idx = turn_idx

                # Generate or select caller utterance
                if use_scripted:
                    # Scripted mode: use pre-defined utterances in order
                    if scripted_idx >= len(scripted_utterances):
                        logger.info(f"[Runner] Scripted mode: all {len(scripted_utterances)} utterances sent")
                        break
                    caller_text = scripted_utterances[scripted_idx]
                    scripted_idx += 1
                    persona_response = PersonaResponse(
                        speech=caller_text, end_politely=(scripted_idx >= len(scripted_utterances))
                    )
                else:
                    # LLM persona mode
                    try:
                        persona_response: PersonaResponse = await asyncio.wait_for(
                            self.persona.generate_utterance(
                                scenario_goal=self.scenario.caller_goal,
                                caller_identity=self.scenario.caller_identity,
                                confirmation_phrases=self.scenario.confirmation_phrases,
                                patience_turns=max_patience_turns,
                                conversation_history=self.conversation_history,
                            ),
                            timeout=10.0,
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"[Runner] Persona LLM timeout on turn {turn_idx}")
                        result["error"] = "Persona LLM timeout"
                        break

                    if not persona_response.speech:
                        logger.warning(
                            f"[Runner] Persona returned empty speech on turn {turn_idx}"
                        )
                        break

                caller_text = persona_response.speech
                self.user_utterances.append(caller_text)
                self.conversation_history.append({"role": "user", "content": caller_text})
                logger.info(
                    f"[Runner] T{turn_idx} caller: {caller_text[:60]!r}"
                )

                # Send to agent
                await self.client.send_utterance(caller_text)

                # Receive bot response
                try:
                    start_ms = self._now_ms()
                    bot_text, tools = await asyncio.wait_for(
                        self.client.receive_bot_turn(timeout_s=turn_timeout),
                        timeout=turn_timeout + 2.0,
                    )
                    latency_ms = self._now_ms() - start_ms
                except asyncio.TimeoutError:
                    logger.error(f"[Runner] Agent timeout on turn {turn_idx}")
                    result["error"] = "Agent response timeout"
                    break
                except Exception as e:
                    logger.error(f"[Runner] Agent error on turn {turn_idx}: {e}")
                    result["error"] = f"Agent error: {e}"
                    break

                self.bot_responses.append(bot_text)
                self.tools_fired_per_turn.append(tools)
                self.per_turn_latency_ms.append(latency_ms)
                self.conversation_history.append({"role": "assistant", "content": bot_text})
                logger.info(
                    f"[Runner] T{turn_idx} agent ({latency_ms}ms): {bot_text[:60]!r} | tools={tools}"
                )

                # Check end conditions
                if persona_response.end_politely:
                    logger.info(f"[Runner] Caller ended politely on turn {turn_idx}")
                    break

                if persona_response.abandon:
                    logger.warning(
                        f"[Runner] Caller abandoned on turn {turn_idx}: {persona_response.internal_note!r}"
                    )
                    result["error"] = f"Caller abandoned: {persona_response.internal_note}"
                    break

            # Wrap up
            await self.client.end_session()

            # Populate result
            result["bot_responses"] = self.bot_responses
            result["user_utterances"] = self.user_utterances
            result["tools_fired"] = [t for turn_tools in self.tools_fired_per_turn for t in turn_tools]
            result["latencies_ms"] = self.per_turn_latency_ms
            result["turn_count"] = len(self.user_utterances)

            # Fetch DB metrics and verify
            db_metrics = await fetch_call_metrics(self.pg_dsn, self.call_sid)
            signals = derive_signals(db_metrics, self.bot_responses, self.user_utterances)

            verifier = Verifier()
            verification = verifier.verify_call(
                scenario_id=self.scenario.id,
                call_sid=self.call_sid,
                bot_responses=self.bot_responses,
                tools_fired_per_turn=self.tools_fired_per_turn,
                user_utterances=self.user_utterances,
                db_metrics=db_metrics,
                expectations=self.scenario.expectations,
            )

            result["verification_result"] = verification
            result["passed"] = verification.passed and not result["error"]
            result["signals"] = signals

            logger.info(
                f"[Runner] {self.scenario.id} complete: "
                f"passed={result['passed']} turns={result['turn_count']}"
            )

        except Exception as e:
            logger.exception(f"[Runner] Unhandled error in {self.scenario.id}")
            result["error"] = str(e)
        finally:
            if self.client:
                await self.client.close()

        return result

    @staticmethod
    def _now_ms() -> int:
        """Get current time in milliseconds."""
        import time
        return int(time.time() * 1000)
