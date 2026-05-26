"""
Live call auditor — runs after every demo call in real-time.

Merges validation loop's 10-dimension scoring engine with production's industry weights
and training scenario generation. Adapted for `session_data` format (skips audio/STT dims
that require per-turn bytes/WER unavailable in live calls).

Scoring dimensions (8 kept from validation loop):
1. Task (20%) — expected tools called, intent resolved
2. Language (15%) — German-only, Sie-form, forbidden phrases
3. Instruction (10%) — max 2 sentences, no loops
4. Latency (10%) — P50/P90 per turn vs budget
5. Flow (10%) — no dead-ends, proper transitions
6. Response (7%) — substantive, not deflecting
7. Hallucination (10%) — no fabricated info
8. Completeness (5%) — greeting, end_call, summary, SMS

Audio (8%) and STT (5%) skipped for live: those 13% redistributed proportionally.
Industry-specific weights applied (restaurant=35% task).
"""

import re
import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_DIR = Path("/home/charles2/sailly/.state")
DAILY_DIR = STATE_DIR / "daily-scores"
SCENARIOS_FILE = STATE_DIR / "live-call-scenarios.jsonl"
QUALITY_THRESHOLD = 72.0

# ─── Validation loop patterns ───────────────────────────────────────────────

# Known tools from validation loop
ALL_TOOLS = {
    "ai_greeting", "end_call", "transfer_to_tier2", "transfer_to_human",
    "transfer_to_ordering", "create_reservation", "create_order", "send_sms",
    "get_menu", "check_availability", "verify_address", "update_state",
    "technical_issues_callback", "request_callback",
    "get_date_info", "get_weather", "faq",
}

# German language rules
INFORMAL_PATTERNS = [
    r"\bdu\b", r"\bdich\b", r"\bdir\b", r"\bdein\b", r"\bdeine[rns]?\b",
    r"\bhast\b(?!.*Sie)", r"\bbist\b(?!.*Sie)", r"\bkannst\b(?!.*Sie)",
]

ENGLISH_STRONG = {
    "hello", "hi", "certainly", "absolutely", "awesome", "welcome", "sure",
    "thank", "thanks", "please", "sorry", "unfortunately", "great", "perfect",
    "wonderful", "amazing", "excellent", "fantastic",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "open", "closed", "call", "calling", "help",
}

ENGLISH_COMMON = {
    "the", "is", "are", "you", "have", "this", "that", "with", "for",
    "your", "can", "will", "from", "they", "been", "more", "also",
    "but", "not", "what", "when", "how", "our", "just", "very",
    "would", "could", "should", "might", "shall", "going", "looking",
    "anything", "everything", "something", "nothing", "someone",
    "calling", "today", "booking", "reservation", "available", "moment",
    "understand", "order", "table", "time",
}

FORBIDDEN_PHRASES = [
    "ich bin eine ki", "ich bin ein bot", "als sprachmodell",
    "als ki-assistent", "als künstliche intelligenz",
    "ich bin ein sprachassistent", "ich bin ein virtuell",
    "ich bin kein mensch", "als chatbot", "als ai",
]

DEFLECTION_PHRASES = [
    "das kann ich leider nicht", "das weiß ich leider nicht",
    "ich habe keine informationen", "da kann ich ihnen nicht helfen",
    "dazu kann ich nichts sagen", "ich bin nicht sicher",
    "das übersteigt meine fähigkeiten",
]

MENU_DISHES = {
    "bibimbap", "bulgogi", "kimchi jjigae", "tteokbokki", "japchae",
    "mandu", "tofu jjigae", "tofu bibimbap", "mochi-eis", "mochi eis",
    "bibimbap (klassisch)",
}

JACCARD_THRESHOLD = 0.75

# ─── Industry-specific weights (from production auditor) ───────────────────

SCORING_WEIGHTS = {
    "restaurant": {
        "task_completion": 0.35,
        "language": 0.15,
        "instruction": 0.10,
        "latency": 0.10,
        "flow": 0.10,
        "response": 0.07,
        "hallucination": 0.10,
        "completeness": 0.03,
    },
    "medical": {
        "task_completion": 0.30,
        "language": 0.15,
        "instruction": 0.10,
        "latency": 0.10,
        "flow": 0.05,
        "response": 0.07,
        "hallucination": 0.23,
        "completeness": 0.00,
    },
}

DEFAULT_WEIGHTS = SCORING_WEIGHTS["restaurant"]

LATENCY_BUDGET_MS = {1: 5_000, 2: 15_000, 3: 15_000, 4: 20_000}


def _get_weights(industry: str) -> dict:
    return SCORING_WEIGHTS.get(industry, DEFAULT_WEIGHTS)


def _jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two strings."""
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _has_english(text: str) -> bool:
    """Check for >=3 consecutive English words or strong English opener."""
    words = re.sub(r"[^\w\s]", "", text.lower()).split()
    if words and words[0] in ENGLISH_STRONG:
        return True
    run = 0
    for w in words:
        if w in (ENGLISH_COMMON | ENGLISH_STRONG):
            run += 1
            if run >= 3:
                return True
        else:
            run = 0
    return False


def _has_informal(text: str) -> bool:
    """Check for informal 'du' forms."""
    tl = text.lower()
    return any(re.search(p, tl) for p in INFORMAL_PATTERNS)


def _count_sentences(text: str) -> int:
    """Count sentences in text."""
    return max(1, len(re.split(r"[.!?]+", text.strip())))


def score_live_call(session_data: dict, industry: str = "restaurant") -> dict:
    """
    Score a live call using merged validation loop + production logic.

    Args:
        session_data: Redis session dict with transcripts, tool_calls, duration_secs
        industry: "restaurant", "medical", etc. for weight selection

    Returns:
        dict with composite_score (0-100), dimension scores, and flags
    """
    transcripts = session_data.get("transcripts", [])
    tool_calls = session_data.get("tool_calls", [])
    duration_secs = session_data.get("duration_secs", 0) or 0

    n_turns = len(transcripts)
    weights = _get_weights(industry)
    budget_ms = 15_000  # Phase 2-3 budget for live Gemini+TTS

    # ══════════════════════════════════════════════════════════════════════
    # Build per-turn analysis from session_data transcripts
    # ══════════════════════════════════════════════════════════════════════

    bot_responses: List[str] = []
    latencies: List[float] = []
    all_tools: set = set()

    for i, t in enumerate(transcripts):
        role = t.get("role", "unknown")
        content = t.get("content") or t.get("text", "")
        if role == "assistant":
            bot_responses.append(content.strip())

        # Compute latency from timestamp if available
        if i > 0 and role == "assistant":
            prev_ts = transcripts[i-1].get("timestamp") or transcripts[i-1].get("ts")
            curr_ts = t.get("timestamp") or t.get("ts")
            if prev_ts and curr_ts:
                try:
                    delta_ms = (float(curr_ts) - float(prev_ts)) * 1000
                    if 0 < delta_ms < 30000:
                        latencies.append(delta_ms)
                except (ValueError, TypeError):
                    pass

    # Extract tool calls
    for tc in tool_calls:
        tool_name = tc.get("tool") or tc.get("name", "")
        if tool_name:
            all_tools.add(tool_name)

    failures: List[str] = []

    # ══════════════════════════════════════════════════════════════════════
    # DIM 1: Task Completion (35% for restaurant)
    # ══════════════════════════════════════════════════════════════════════

    score_task = 50  # baseline
    expected_tools = {"create_order", "create_reservation", "end_call"}
    action_tools = all_tools & expected_tools

    if action_tools:
        score_task = 80
        if "end_call" in all_tools:
            score_task = min(score_task + 10, 100)
    elif len(tool_calls) > 0:
        score_task = 65

    if n_turns < 4:
        score_task = max(score_task - 20, 0)

    if "end_call" not in all_tools and duration_secs > 30:
        failures.append("end_call not used")

    # ══════════════════════════════════════════════════════════════════════
    # DIM 2: Language Compliance (15%)
    # ══════════════════════════════════════════════════════════════════════

    score_lang = 100.0
    n_english = sum(1 for r in bot_responses if _has_english(r))
    n_informal = sum(1 for r in bot_responses if _has_informal(r))
    n_forbidden = sum(
        1 for r in bot_responses
        for fp in FORBIDDEN_PHRASES if fp in r.lower()
    )
    n_empty = sum(1 for r in bot_responses if len(r) < 5)

    score_lang -= n_english * 30.0
    score_lang -= n_informal * 20.0
    score_lang -= n_forbidden * 25.0
    score_lang -= n_empty * 10.0

    if bot_responses and all(_has_english(r) for r in bot_responses if r.strip()):
        score_lang = 0.0

    score_lang = max(0.0, score_lang)

    if n_english >= 2:
        failures.append(f"English in {n_english} turns")
    if n_informal >= 3:
        failures.append(f"Informal 'du' in {n_informal} turns")

    # ══════════════════════════════════════════════════════════════════════
    # DIM 3: Instruction Following (10%)
    # ══════════════════════════════════════════════════════════════════════

    score_instr = 100.0
    n_verbose = sum(1 for r in bot_responses if _count_sentences(r) > 3)
    n_too_short = sum(1 for r in bot_responses if len(r) < 25 and not re.search(r"\[TOOL", r))
    n_too_long = sum(1 for r in bot_responses if len(r) > 600)

    score_instr -= n_verbose * 8.0
    score_instr -= n_too_short * 10.0
    score_instr -= n_too_long * 12.0

    # Repetition: Jaccard similarity
    n_repetitions = 0
    for i in range(1, len(bot_responses)):
        if _jaccard(bot_responses[i], bot_responses[i-1]) >= JACCARD_THRESHOLD:
            n_repetitions += 1

    score_instr -= n_repetitions * 15.0
    loop_detected = n_repetitions >= 4
    if loop_detected:
        score_instr -= 30.0
        failures.append("Conversation loop detected")

    score_instr = max(0.0, score_instr)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 4: Latency (10%)
    # ══════════════════════════════════════════════════════════════════════

    score_latency = 0.0
    if latencies:
        lats_sorted = sorted(latencies)
        p50 = lats_sorted[len(lats_sorted) // 2]
        p90 = lats_sorted[int(len(lats_sorted) * 0.90)]

        if p50 <= budget_ms:
            p50_score = 100.0
        elif p50 <= budget_ms * 2:
            p50_score = 100.0 - (p50 - budget_ms) / budget_ms * 50.0
        else:
            p50_score = max(0.0, 50.0 - (p50 - budget_ms * 2) / budget_ms * 30.0)

        p90_budget = budget_ms * 1.5
        if p90 <= p90_budget:
            p90_score = 100.0
        elif p90 <= p90_budget * 2:
            p90_score = 100.0 - (p90 - p90_budget) / p90_budget * 60.0
        else:
            p90_score = max(0.0, 40.0 - (p90 - p90_budget * 2) / p90_budget * 20.0)

        score_latency = p50_score * 0.6 + p90_score * 0.4

    score_latency = max(0.0, min(100.0, score_latency))

    # ══════════════════════════════════════════════════════════════════════
    # DIM 7: Conversation Flow (10%)
    # ══════════════════════════════════════════════════════════════════════

    score_flow = 100.0
    score_flow -= n_repetitions * 10.0

    # Dead-ends: short response without "?" and no tools
    n_dead_ends = 0
    for i, resp in enumerate(bot_responses):
        if (len(resp) < 25 and not resp.strip().endswith("?")
                and not re.search(r"\[TOOL", resp) and i < len(bot_responses) - 1):
            n_dead_ends += 1
    score_flow -= n_dead_ends * 8.0

    # Monotone: no questions asked
    n_questions = sum(1 for r in bot_responses if "?" in r)
    if n_turns >= 4 and n_questions == 0:
        score_flow -= 15.0

    # Goodbye recognition
    all_text = " ".join(bot_responses).lower()
    caller_said_bye = False
    bot_ended = False
    for r in bot_responses:
        if any(p in r.lower() for p in ["wiedersehen", "tschüss", "tschüs", "bye"]):
            caller_said_bye = True
        if "end_call" in r.lower():
            bot_ended = True

    if caller_said_bye and not bot_ended:
        score_flow -= 10.0

    score_flow = max(0.0, score_flow)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 8: Response Quality (7%)
    # ══════════════════════════════════════════════════════════════════════

    score_response = 100.0
    n_deflections = sum(
        1 for r in bot_responses
        for dp in DEFLECTION_PHRASES if dp in r.lower()
    )
    score_response -= n_deflections * 15.0
    score_response -= n_empty * 20.0
    score_response -= n_too_short * 8.0

    # Vocabulary check
    all_bot_text = " ".join(bot_responses).lower()
    unique_words = set(re.findall(r"\b\w+\b", all_bot_text))
    if n_turns >= 5 and len(unique_words) < 20:
        score_response -= 20.0

    # Starter phrase frequency
    starters = [r[:30].lower() for r in bot_responses if len(r) > 30]
    if starters:
        starter_counts = Counter(starters)
        max_starter_freq = max(starter_counts.values())
        if max_starter_freq >= 4:
            score_response -= 15.0

    score_response = max(0.0, score_response)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 9: Hallucination / Safety (10%)
    # ══════════════════════════════════════════════════════════════════════

    score_halluc = 100.0
    score_halluc -= n_forbidden * 25.0

    # Price hallucination
    price_claims = re.findall(r"\b\d+[,.]?\d*\s*(?:euro|€|EUR)\b", all_text, re.IGNORECASE)
    unique_prices = set(price_claims)
    if len(unique_prices) > 5:
        score_halluc -= 15.0

    # Menu dish validation for create_order
    hallucination_risk = False
    if "create_order" in all_tools:
        order_context = " ".join(bot_responses).lower()
        mentioned_dishes = [d for d in MENU_DISHES if d in order_context]
        if not mentioned_dishes:
            score_halluc = 0.0
            hallucination_risk = True
            failures.append("create_order for non-menu dish")

    score_halluc = max(0.0, score_halluc)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 10: Completeness / Protocol (3% for restaurant, 0% for medical)
    # ══════════════════════════════════════════════════════════════════════

    score_complete = 100.0

    # AI disclosure in greeting
    if bot_responses:
        first_resp = bot_responses[0].lower()
        greeting_words = ["willkommen", "hallo", "guten", "herzlich", "doboo",
                         "begrüss", "anruf", "helfen", "hilfe"]
        has_greeting = any(g in first_resp for g in greeting_words)
        if not has_greeting:
            score_complete -= 15.0

        ai_disclosure = ["sailly", "ki", "künstliche", "digital", "assistentin",
                        "sprachassistentin"]
        has_ai_disclosure = any(d in first_resp for d in ai_disclosure)
        if not has_ai_disclosure:
            score_complete -= 10.0

    if "end_call" not in all_tools:
        score_complete -= 20.0

    if 0 < n_turns < 3:
        score_complete -= 20.0

    score_complete = max(0.0, score_complete)

    # ══════════════════════════════════════════════════════════════════════
    # COMPOSITE SCORE (redistributed 8 dimensions)
    # ══════════════════════════════════════════════════════════════════════

    composite = (
        score_task * weights["task_completion"]
        + score_lang * weights["language"]
        + score_instr * weights["instruction"]
        + score_latency * weights["latency"]
        + score_flow * weights["flow"]
        + score_response * weights["response"]
        + score_halluc * weights["hallucination"]
        + score_complete * weights["completeness"]
    )

    # Auto-fail conditions
    if n_turns == 0:
        failures.append("0 turns (crash/timeout)")

    dim_scores = {
        "task": score_task,
        "language": score_lang,
        "instruction": score_instr,
        "latency": score_latency,
        "flow": score_flow,
        "response": score_response,
        "hallucination": score_halluc,
        "completeness": score_complete,
    }

    for dim_name, dim_val in dim_scores.items():
        if dim_val < 30.0:
            failures.append(f"{dim_name} score {dim_val:.0f} < 30")

    passed = len(failures) == 0 and composite >= QUALITY_THRESHOLD

    # For dashboard compatibility: map dimensions to the expected format
    # greeting_score = first response quality component
    # tool_usage_score = task completion
    # resolution_score = flow + completeness combined
    greeting_score = (score_lang + score_complete) / 2.0
    tool_usage_score = score_task
    resolution_score = (score_flow + score_instr) / 2.0

    result = {
        "composite_score": round(composite, 1),
        "score_task": round(score_task, 1),
        "score_language": round(score_lang, 1),
        "score_instruction": round(score_instr, 1),
        "score_latency": round(score_latency, 1),
        "score_flow": round(score_flow, 1),
        "score_response": round(score_response, 1),
        "score_hallucination": round(score_halluc, 1),
        "score_completeness": round(score_complete, 1),
        "greeting_score": round(greeting_score / 10.0, 1),
        "tool_usage_score": round(tool_usage_score / 10.0, 1),
        "resolution_score": round(resolution_score / 10.0, 1),
        "passed": passed,
        "failure_reasons": failures,
        "hallucination_risk": hallucination_risk,
        "loop_detected": loop_detected,
        "n_turns": n_turns,
        "duration_secs": duration_secs,
        "tools_called": list(all_tools),
    }

    return result
