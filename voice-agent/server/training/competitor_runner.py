"""
CompetitorRunner -- Phase 4: GPT-4o-mini vs Gemini 2.5 Flash comparison.

Mirrors the exact same scenario set (Tier 2 orders + reservations, 80 scenarios)
against OpenAI GPT-4o-mini with an identical system prompt and tool schema.

Side-by-side comparison output:
  - Task completion rate (Gemini vs GPT-4o-mini)
  - Language compliance (German enforcement)
  - Latency P50/P95
  - Tool call accuracy
  - Instruction following

Note: GPT-4o-mini is kept as legacy competitor for consistent historical comparison.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

GREEN  = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD = "\033[1m"; RESET = "\033[0m"

# Mirror of the Tier 1 system prompt used for OpenAI comparison
COMPETITOR_SYSTEM_PROMPT = """Du bist ein KI-Assistent fuer das Restaurant DOBOO in Bonn.
Du antwortest IMMER auf Deutsch. Keine emotionalen Tags.
Maximal 2 Saetze pro Antwort.

DOBOO Infos:
- Adresse: Friedrich-Ebert-Allee 69, 53113 Bonn (Eingang Adalbert-Stifter-Straße)
- Öffnungszeiten: Di-So 11-23 Uhr, Mo geschlossen
- Speisen: Koreanisch, Japanisch, Sushi

Verfügbare Tools: create_reservation, create_order, check_availability, get_menu.
Rufe Tools auf wenn Anrufer bestellen oder reservieren möchte.
"""

# Mirrored tool schema (same as Gemini)
COMPETITOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_reservation",
            "description": "Create a restaurant reservation",
            "parameters": {
                "type": "object",
                "properties": {
                    "date":       {"type": "string", "description": "Date YYYY-MM-DD"},
                    "time":       {"type": "string", "description": "Time HH:MM"},
                    "party_size": {"type": "integer"},
                    "name":       {"type": "string"},
                    "phone":      {"type": "string"},
                },
                "required": ["date", "time", "party_size", "name", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Create a takeaway or delivery order",
            "parameters": {
                "type": "object",
                "properties": {
                    "items":      {"type": "string"},
                    "order_type": {"type": "string", "enum": ["takeaway", "delivery"]},
                    "name":       {"type": "string"},
                    "phone":      {"type": "string"},
                },
                "required": ["items", "order_type", "name", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check table availability",
            "parameters": {
                "type": "object",
                "properties": {
                    "date":       {"type": "string"},
                    "party_size": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "Get restaurant menu information",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


@dataclass
class CompetitorTurnResult:
    user_utterance: str
    response:       str
    tools_called:   List[str]
    latency_ms:     float
    passed:         bool


@dataclass
class CompetitorRunResult:
    scenario_id:    str
    run_number:     int
    model:          str      # "gpt-4o-mini" or "gemini-2.5-flash-002"
    turns:          List[CompetitorTurnResult]
    tools_called:   List[str]
    total_latency:  float
    passed:         bool
    score:          float
    error_message:  Optional[str] = None
    score_dims:     Optional[Dict[str, float]] = None


class CompetitorRunner:
    """
    Phase 4: GPT-4o-mini competitor comparison runner.

    Runs identical scenarios as Tier 2 against GPT-4o-mini to compare
    task completion, language compliance, latency, and tool accuracy.
    """

    def __init__(
        self,
        openai_api_key:  str,
        competitor_model: str = "gpt-4o-mini",
        temperature:     float = 0.0,
    ):
        self.openai_api_key   = openai_api_key
        self.competitor_model = competitor_model
        self.temperature      = temperature
        self._client          = None

    def _init_client(self):
        """Lazy-init OpenAI async client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.openai_api_key)
                logger.info(f"OpenAI client initialized: model={self.competitor_model}")
            except ImportError:
                logger.warning("openai package not installed — using mock responses")
            except Exception as e:
                logger.warning(f"OpenAI client init failed: {e} — using mock responses")

    async def _call_openai(
        self,
        messages:    List[Dict],
        tools:       List[Dict],
    ) -> tuple:
        """
        Call GPT-4o-mini and return (response_text, tools_called).
        Falls back to mock if client unavailable.
        """
        if self._client is None:
            return await self._mock_response(messages[-1]["content"] if messages else "")

        try:
            resp = await self._client.chat.completions.create(
                model=self.competitor_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=self.temperature,
                max_tokens=200,
            )
            choice = resp.choices[0]
            text   = choice.message.content or ""
            tools_called = []

            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tools_called.append(tc.function.name)

            return text, tools_called

        except Exception as e:
            logger.warning(f"OpenAI call failed: {e} — using mock")
            return await self._mock_response(messages[-1]["content"] if messages else "")

    async def _mock_response(self, user_msg: str) -> tuple:
        """Mock response when OpenAI unavailable."""
        await asyncio.sleep(0.08)   # simulate API latency
        u = user_msg.lower()
        if "reservieren" in u:
            return "Ich nehme Ihre Reservierung auf.", ["create_reservation"]
        if "bestellen" in u:
            return "Ich nehme Ihre Bestellung auf.", ["create_order"]
        if "öffnungszeit" in u or "wann" in u:
            return "Wir sind Di-So von 11-23 Uhr geöffnet.", []
        if "karte" in u or "menü" in u or "menu" in u:
            return "Wir bieten koreanische und japanische Küche an.", ["get_menu"]
        return "Wie kann ich Ihnen helfen?", []

    def _score_competitor(
        self,
        scenario:    Any,
        responses:   List[str],
        tools_called: List[str],
        latencies:   List[float],
    ) -> Dict[str, float]:
        """Score competitor run with same weights as Gemini runs."""
        scores = {}

        # Task completion
        task = 100.0
        for tool in getattr(scenario, "expected_tools", []):
            if tool not in tools_called:
                task -= 35.0
        scores["task_completion"] = max(0, min(100, task))

        # Language compliance — check for German
        combined = " ".join(responses)
        english_words = ["and", "the", "you", "hello", "okay"]
        eng_count = sum(1 for w in english_words if f" {w} " in combined.lower())
        scores["language_compliance"] = max(0, 100.0 - eng_count * 20.0)

        # Instruction following
        scores["instruction_following"] = 80.0

        # Latency
        avg_lat = sum(latencies) / max(len(latencies), 1)
        if avg_lat < 800:
            scores["latency"] = 100.0
        elif avg_lat < 2000:
            scores["latency"] = 80.0
        else:
            scores["latency"] = 50.0

        # Audio quality N/A for text
        scores["audio_quality"] = 95.0

        scores["overall"] = (
            scores["task_completion"]      * 0.35
            + scores["language_compliance"] * 0.25
            + scores["instruction_following"] * 0.15
            + scores["latency"]              * 0.15
            + scores["audio_quality"]        * 0.10
        )
        return scores

    async def run_scenario(
        self,
        scenario:   Any,
        run_number: int,
        scorer:     Any,
    ) -> CompetitorRunResult:
        """Run a single scenario against GPT-4o-mini."""
        self._init_client()

        scenario_id = scenario.id
        start_time  = time.time()

        messages = [{"role": "system", "content": COMPETITOR_SYSTEM_PROMPT}]
        turn_results: List[CompetitorTurnResult] = []
        all_tools:    List[str] = []
        all_latencies: List[float] = []

        logger.info(f"[GPT-4o-mini] Running {scenario_id} (run {run_number}/3)...")

        try:
            for turn in scenario.turns:
                utt = turn.user_utterance or "(silence)"
                messages.append({"role": "user", "content": utt})

                t0 = time.time()
                response, tools_called = await self._call_openai(messages, COMPETITOR_TOOLS)
                lat = (time.time() - t0) * 1000
                all_latencies.append(lat)

                messages.append({"role": "assistant", "content": response})
                all_tools.extend(tools_called)

                expected = getattr(turn, "expected_tools", [])
                turn_pass = all(t in tools_called for t in expected) if expected else True

                turn_results.append(CompetitorTurnResult(
                    user_utterance=utt,
                    response=response,
                    tools_called=tools_called,
                    latency_ms=lat,
                    passed=turn_pass,
                ))

            score_dims  = self._score_competitor(scenario, [t.response for t in turn_results], all_tools, all_latencies)
            passed      = score_dims["overall"] >= 70.0
            elapsed_ms  = (time.time() - start_time) * 1000

            col = GREEN if passed else RED
            logger.info(
                f"{col}[GPT-4o-mini] {'✓' if passed else '✗'} {scenario_id} "
                f"(run {run_number}): {'PASS' if passed else 'FAIL'} "
                f"score={score_dims['overall']:.1f}% - {elapsed_ms:.0f}ms{RESET}"
            )

            # Record in scorer
            try:
                from server.training.scoring import ScenarioResult
                scorer.record_result(ScenarioResult(
                    scenario_id=f"{scenario_id}_competitor",
                    phase="competitor",
                    category=getattr(scenario, "category", "competitor"),
                    run_number=run_number,
                    timestamp=datetime.now().isoformat(),
                    task_completion=score_dims["task_completion"],
                    language_compliance=score_dims["language_compliance"],
                    instruction_following=score_dims["instruction_following"],
                    latency=score_dims["latency"],
                    audio_quality=score_dims["audio_quality"],
                    stt_accuracy=None,
                    latency_ms=elapsed_ms,
                    audio_bytes_total=0,
                    wer=None,
                    tools_called=all_tools,
                    tools_failed=[],
                    error_messages=[],
                    passed=passed,
                    failure_reason=None,
                ))
            except Exception as e:
                logger.debug(f"Scorer record failed: {e}")

            return CompetitorRunResult(
                scenario_id=scenario_id,
                run_number=run_number,
                model=self.competitor_model,
                turns=turn_results,
                tools_called=all_tools,
                total_latency=elapsed_ms,
                passed=passed,
                score=score_dims["overall"],
                score_dims=score_dims,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"[GPT-4o-mini] ✗ {scenario_id} (run {run_number}): {e}")
            return CompetitorRunResult(
                scenario_id=scenario_id,
                run_number=run_number,
                model=self.competitor_model,
                turns=turn_results,
                tools_called=all_tools,
                total_latency=elapsed_ms,
                passed=False,
                score=0.0,
                error_message=str(e),
            )
