"""
Production-Grade German Voice Agent Auditor — 10 Dimensions
Based on: Hamming Voice Agent Metrics Guide, Deepgram VAQI, ArkSim repetition detection,
kulu-audio-eval cut-off detection, and ITU-T P.800/P.808 MOS standards.

═══════════════════════════════════════════════════════════════
DIM  WEIGHT  METRIC
═══════════════════════════════════════════════════════════════
 1   20%  Task Completion       — expected tools called, intent resolved
 2   15%  Language Compliance   — German-only, formality (Sie), no forbidden
 3   10%  Instruction Following — max 2 sentences, no fabrication
 4   10%  Latency (per-turn)    — P50/P90 within budget per component
 5    8%  Audio Quality (TTS)   — length, cut-off, silence gaps
 6    5%  STT Accuracy          — WER below threshold
 7   10%  Conversation Flow     — no loops, no dead-ends, natural transitions
 8    7%  Response Quality      — substantive answers, not deflecting
 9   10%  Hallucination / Safety— no fabricated info, no forbidden disclosure
10    5%  Completeness          — greeting, end_call, all steps done
═══════════════════════════════════════════════════════════════
    100%

Pass threshold: weighted composite >= 72.
Auto-fail: any single dimension < 30.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# ─── Weights ───────────────────────────────────────────────────────────────
WEIGHTS = {
    "task":          0.20,
    "language":      0.15,
    "instruction":   0.10,
    "latency":       0.10,
    "audio":         0.08,
    "stt":           0.05,
    "flow":          0.10,
    "response":      0.07,
    "hallucination": 0.10,
    "completeness":  0.05,
}

PASS_THRESHOLD    = 72.0
AUTOFAIL_DIM      = 30.0   # any single dim below this → auto-fail

# Latency budgets ms/turn by phase (adjusted for real Gemini+TTS latency)
# Phase 1: Fast (pre-training) = 5s, Phase 2-3: Real APIs (Gemini+TTS) = 15s, Phase 4: Production buffer = 20s
LATENCY_BUDGET_MS = {1: 5_000, 2: 15_000, 3: 15_000, 4: 20_000}

# ─── Known Tools ───────────────────────────────────────────────────────────
ALL_TOOLS = {
    "ai_greeting", "end_call", "transfer_to_tier2", "transfer_to_human",
    "transfer_to_ordering",
    "create_reservation", "create_order", "send_sms", "get_menu",
    "check_availability", "verify_address", "update_state",
    "technical_issues_callback", "request_callback",
    "get_date_info", "get_weather",
    "faq",
}

# ─── German Language Rules ─────────────────────────────────────────────────
# Bot MUST use Sie (formal). Any du/dich/dir = penalty.
INFORMAL_PATTERNS = [
    r"\bdu\b", r"\bdich\b", r"\bdir\b", r"\bdein\b", r"\bdeine[rns]?\b",
    r"\bhast\b(?!.*Sie)", r"\bbist\b(?!.*Sie)", r"\bkannst\b(?!.*Sie)",
]

# English words that NEVER appear in proper German bot responses
ENGLISH_STRONG = {
    "hello", "hi", "certainly", "absolutely", "awesome", "welcome", "sure",
    "thank", "thanks", "please", "sorry", "unfortunately", "great", "perfect",
    "wonderful", "amazing", "excellent", "fantastic",
    # Days/time in English (bot should say Montag, not Monday)
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

# Forbidden bot self-disclosure (bot must not reveal it's AI)
FORBIDDEN_PHRASES = [
    "ich bin eine ki", "ich bin ein bot", "als sprachmodell",
    "als ki-assistent", "als künstliche intelligenz",
    "ich bin ein sprachassistent", "ich bin ein virtuell",
    "ich bin kein mensch", "als chatbot", "als ai",
]

# Deflection / low-effort responses
DEFLECTION_PHRASES = [
    "das kann ich leider nicht",
    "das weiß ich leider nicht",
    "ich habe keine informationen",
    "da kann ich ihnen nicht helfen",
    "dazu kann ich nichts sagen",
    "ich bin nicht sicher",
    "das übersteigt meine fähigkeiten",
]

# DOBOO restaurant known facts for hallucination checking
DOBOO_FACTS = {
    "name": "DOBOO",
    "cuisine": "koreanisch",
    "city": "Bonn",
}

# ─── Repetition Detection ─────────────────────────────────────────────────
JACCARD_THRESHOLD = 0.75   # Jaccard similarity for "same response" detection


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _has_english(text: str) -> bool:
    """True if ≥ 3 consecutive English words or starts with strong English word."""
    words = re.sub(r"[^\w\s]", "", text.lower()).split()
    # Strong English opener
    if words and words[0] in ENGLISH_STRONG:
        return True
    # 3+ consecutive English tokens
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
    tl = text.lower()
    return any(re.search(p, tl) for p in INFORMAL_PATTERNS)


def _count_sentences(text: str) -> int:
    return max(1, len(re.split(r"[.!?]+", text.strip())))


def _parse_tools_full(text: str) -> List[str]:
    """Extract tool names from bracket tags and JSON only — no bare substring match."""
    found = set()
    for m in re.finditer(r"\[TOOL:(\w+)\]", text):
        found.add(m.group(1))
    for m in re.finditer(r"`\[TOOL:(\w+)\]`", text):
        found.add(m.group(1))
    for m in re.finditer(r'"name":\s*"(\w+)"', text):
        if m.group(1) in ALL_TOOLS:
            found.add(m.group(1))
    return list(found)


# ─── Dataclasses ───────────────────────────────────────────────────────────

@dataclass
class TurnAudit:
    turn_idx:         int
    caller_text:      str
    bot_response:     str
    stt_transcript:   str
    wer:              float
    tools_called:     List[str]
    latency_ms:       float
    tts_bytes:        int
    # Per-turn flags
    is_empty:         bool = False   # response is blank/trivial
    is_english:       bool = False
    is_informal:      bool = False
    is_repetition:    bool = False   # repeats a prior response
    is_deflection:    bool = False   # "I can't help with that"
    is_too_short:     bool = False   # < 25 chars
    is_too_long:      bool = False   # > 600 chars (wall of text)
    is_cutoff:        bool = False   # TTS suspiciously short vs text length
    n_sentences:      int  = 1


@dataclass
class AuditResult:
    scenario_id:  str
    phase:        int
    run_number:   int

    # 10 dimension scores 0-100
    score_task:           float
    score_language:       float
    score_instruction:    float
    score_latency:        float
    score_audio:          float
    score_stt:            float
    score_flow:           float
    score_response:       float
    score_hallucination:  float
    score_completeness:   float

    composite:    float
    passed:       bool

    tools_expected:   List[str]
    tools_called:     List[str]
    tools_missing:    List[str]
    n_turns:          int
    total_latency_ms: float
    avg_wer:          float

    # Flag counts
    n_empty:          int = 0
    n_english:        int = 0
    n_informal:       int = 0
    n_repetitions:    int = 0
    n_deflections:    int = 0
    n_too_short:      int = 0
    n_too_long:       int = 0
    n_cutoffs:        int = 0
    loop_detected:    bool = False
    no_end_call:      bool = False
    hallucination_risk: bool = False

    failure_reasons: List[str] = field(default_factory=list)

    def dim_breakdown(self) -> str:
        return (f"T:{self.score_task:.0f} L:{self.score_language:.0f} "
                f"I:{self.score_instruction:.0f} Lat:{self.score_latency:.0f} "
                f"A:{self.score_audio:.0f} S:{self.score_stt:.0f} "
                f"F:{self.score_flow:.0f} R:{self.score_response:.0f} "
                f"H:{self.score_hallucination:.0f} C:{self.score_completeness:.0f}")


# ─── Main Auditor ──────────────────────────────────────────────────────────

def audit_call(
    scenario_id: str,
    phase: int,
    run_number: int,
    turns: List[Dict],
    expected_tools: List[str],
    total_latency_ms: float,
) -> AuditResult:
    """
    Full 10-dimension audit of one call.

    turns: each dict has keys:
      turn_idx, user_utterance, stt_transcript, wer,
      llm_response, tts_bytes, tools_called, latency_ms, passed
    """
    n = len(turns)
    budget_ms = LATENCY_BUDGET_MS.get(phase, 7_000)

    # ══════════════════════════════════════════════════════════════════════
    # Per-turn analysis
    # ══════════════════════════════════════════════════════════════════════
    audits: List[TurnAudit] = []
    all_tools: List[str] = []
    bot_responses: List[str] = []

    for t in turns:
        resp   = t.get("llm_response", "")
        caller = t.get("user_utterance", "")
        stt    = t.get("stt_transcript", "")
        wer    = float(t.get("wer", 0.0))
        lat    = float(t.get("latency_ms", 0.0))
        tts    = int(t.get("tts_bytes", 0))

        raw_tools = list(t.get("tools_called", []))
        extra = _parse_tools_full(resp)
        merged = list(dict.fromkeys(raw_tools + extra))
        all_tools.extend(merged)

        resp_stripped = resp.strip()
        resp_lower    = resp_stripped.lower()
        n_sent        = _count_sentences(resp_stripped)

        # Cut-off detection: TTS bytes suspiciously low for text length
        # Real 8kHz Linear16 mono: ~80-160 bytes/char (speech rate varies)
        expected_tts_min = max(2000, len(resp_stripped) * 80)
        is_cutoff = (tts > 0 and tts < expected_tts_min * 0.15 and len(resp_stripped) > 40)

        ta = TurnAudit(
            turn_idx=t.get("turn_idx", 0),
            caller_text=caller,
            bot_response=resp_stripped,
            stt_transcript=stt,
            wer=wer,
            tools_called=merged,
            latency_ms=lat,
            tts_bytes=tts,
            is_empty=len(resp_stripped) < 5,
            is_english=_has_english(resp_stripped),
            is_informal=_has_informal(resp_stripped),
            is_deflection=any(d in resp_lower for d in DEFLECTION_PHRASES),
            is_too_short=len(resp_stripped) < 25 and not merged,
            is_too_long=len(resp_stripped) > 600,
            is_cutoff=is_cutoff,
            n_sentences=n_sent,
        )
        audits.append(ta)
        bot_responses.append(resp_stripped)

    # Repetition detection: compare each response to all prior
    for i in range(1, len(audits)):
        for j in range(i):
            if _jaccard(bot_responses[i], bot_responses[j]) >= JACCARD_THRESHOLD:
                audits[i].is_repetition = True
                break

    # Aggregate flag counts
    n_empty      = sum(1 for a in audits if a.is_empty)
    n_english    = sum(1 for a in audits if a.is_english)
    n_informal   = sum(1 for a in audits if a.is_informal)
    n_repetitions= sum(1 for a in audits if a.is_repetition)
    n_deflections= sum(1 for a in audits if a.is_deflection)
    n_too_short  = sum(1 for a in audits if a.is_too_short)
    n_too_long   = sum(1 for a in audits if a.is_too_long)
    n_cutoffs    = sum(1 for a in audits if a.is_cutoff)
    loop_detected = n_repetitions >= 4

    called_set   = set(all_tools)
    expected_set = set(expected_tools)
    missing      = list(expected_set - called_set)
    no_end_call  = "end_call" not in called_set and n >= 5
    
    # Initialize failures list for all checks
    failures: List[str] = []

    # ══════════════════════════════════════════════════════════════════════
    # CRITICAL: DETERMINISTIC CONVERSATION FLOW VALIDATOR
    # Only hard-fail on CRITICAL issues (incomplete order/reservation)
    # ══════════════════════════════════════════════════════════════════════
    flow_failures = []
    
    # CRITICAL: If create_order was called, send_sms MUST follow
    if "create_order" in called_set and "send_sms" not in called_set:
        flow_failures.append("CRITICAL FLOW: create_order without send_sms confirmation")
    
    # CRITICAL: If create_reservation was called, check_availability MUST come first
    if "create_reservation" in called_set and "check_availability" not in called_set:
        flow_failures.append("CRITICAL FLOW: create_reservation without check_availability")
    
    # If there are flow violations, hard-fail the entire call
    if flow_failures:
        return AuditResult(
            scenario_id=scenario_id,
            phase=phase,
            run_number=run_number,
            score_task=0.0,
            score_language=0.0,
            score_instruction=0.0,
            score_latency=0.0,
            score_audio=0.0,
            score_stt=0.0,
            score_flow=0.0,
            score_response=0.0,
            score_hallucination=0.0,
            score_completeness=0.0,
            composite=0.0,
            passed=False,
            tools_expected=expected_tools,
            tools_called=list(called_set),
            tools_missing=missing,
            n_turns=n,
            total_latency_ms=0.0,
            avg_wer=0.0,
            failure_reasons=flow_failures,
        )

    # ══════════════════════════════════════════════════════════════════════
    # DIM 1: Task Completion (20%)
    # ══════════════════════════════════════════════════════════════════════
    if n == 0:
        s_task = 0.0
    elif not expected_set:
        s_task = 80.0
    elif expected_set <= called_set:
        s_task = 100.0
    elif expected_set & called_set:
        s_task = 100.0 * len(expected_set & called_set) / len(expected_set)
    else:
        s_task = 0.0

    if no_end_call and n >= 5:
        s_task = max(0, s_task - 15)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 2: Language Compliance (15%)
    # German-only, Sie-form, no forbidden self-disclosure
    # ══════════════════════════════════════════════════════════════════════
    s_lang = 100.0
    s_lang -= n_english  * 30.0     # each English turn = -30
    s_lang -= n_informal * 20.0     # each du-address = -20
    n_forbidden = sum(
        1 for a in audits
        for fp in FORBIDDEN_PHRASES
        if fp in a.bot_response.lower()
    )
    s_lang -= n_forbidden * 25.0
    s_lang -= n_empty     * 10.0
    # Full English: if ALL responses are English → 0
    non_empty_audits = [a for a in audits if not a.is_empty]
    if non_empty_audits and all(a.is_english for a in non_empty_audits):
        s_lang = 0.0
    s_lang = max(0.0, s_lang)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 3: Instruction Following (10%)
    # Max 2 sentences per response, no too-long/too-short
    # ══════════════════════════════════════════════════════════════════════
    s_instr = 100.0
    # Penalty for responses > 3 sentences (bot should be concise)
    n_verbose = sum(1 for a in audits if a.n_sentences > 3)
    s_instr -= n_verbose    * 8.0
    s_instr -= n_too_short  * 10.0
    s_instr -= n_too_long   * 12.0
    s_instr -= n_repetitions * 15.0
    if loop_detected:
        s_instr -= 30.0
    s_instr = max(0.0, s_instr)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 4: Latency (10%)
    # Per-turn latency: P50 and P90 vs budget
    # ══════════════════════════════════════════════════════════════════════
    if audits:
        lats = sorted([a.latency_ms for a in audits if a.latency_ms > 0])
        if lats:
            p50 = lats[len(lats) // 2]
            p90 = lats[int(len(lats) * 0.90)]

            # P50 scoring (60% of latency score)
            if p50 <= budget_ms:
                p50_score = 100.0
            elif p50 <= budget_ms * 2:
                p50_score = 100.0 - (p50 - budget_ms) / budget_ms * 50.0
            else:
                p50_score = max(0.0, 50.0 - (p50 - budget_ms * 2) / budget_ms * 30.0)

            # P90 scoring (40% of latency score)
            p90_budget = budget_ms * 1.5
            if p90 <= p90_budget:
                p90_score = 100.0
            elif p90 <= p90_budget * 2:
                p90_score = 100.0 - (p90 - p90_budget) / p90_budget * 60.0
            else:
                p90_score = max(0.0, 40.0 - (p90 - p90_budget * 2) / p90_budget * 20.0)

            s_latency = p50_score * 0.6 + p90_score * 0.4
        else:
            s_latency = 0.0
    else:
        s_latency = 0.0
    s_latency = max(0.0, min(100.0, s_latency))

    # ══════════════════════════════════════════════════════════════════════
    # DIM 5: Audio Quality (8%)
    # TTS byte length (not too short/long), cut-off detection
    # ══════════════════════════════════════════════════════════════════════
    if audits:
        tts_sizes = [a.tts_bytes for a in audits if a.tts_bytes > 0]
        if tts_sizes:
            avg_tts = sum(tts_sizes) / len(tts_sizes)
            # Real 8kHz Linear16 TTS: ~16 bytes/char → typical range 5k-200k
            if 2_000 <= avg_tts <= 200_000:
                s_audio = 100.0
            elif avg_tts < 2_000:
                s_audio = max(0.0, avg_tts / 2_000 * 70.0)
            else:
                s_audio = max(50.0, 100.0 - (avg_tts - 200_000) / 100_000 * 30.0)
        else:
            s_audio = 0.0

        # Cut-off penalty
        s_audio -= n_cutoffs * 15.0
        # Zero-TTS penalty
        zero_tts = sum(1 for a in audits if a.tts_bytes == 0)
        s_audio -= zero_tts * 12.0

        # Voice consistency: big variation in TTS sizes = inconsistent
        if len(tts_sizes) >= 3:
            mean_t = sum(tts_sizes) / len(tts_sizes)
            if mean_t > 0:
                cv = (sum((x - mean_t)**2 for x in tts_sizes) / len(tts_sizes)) ** 0.5 / mean_t
                if cv > 1.5:
                    s_audio -= 10.0  # highly inconsistent voice output
    else:
        s_audio = 0.0
    s_audio = max(0.0, s_audio)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 6: STT Accuracy (5%)
    # WER: 0% → 100, 10% → 80, 25% → 50, 50% → 0
    # ══════════════════════════════════════════════════════════════════════
    wers = [a.wer for a in audits]
    avg_wer = sum(wers) / len(wers) if wers else 0.0
    s_stt = max(0.0, 100.0 - avg_wer * 200.0)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 7: Conversation Flow (10%)
    # Natural structure: greeting → inquiry → summary → approval → action → goodbye
    # No loops, no dead-ends, proper turn transitions
    # ══════════════════════════════════════════════════════════════════════
    s_flow = 100.0

    # Repetition degrades flow; loop is already penalized on instruction dimension
    s_flow -= n_repetitions * 10.0

    # Dead-end detection: bot gives short non-question response (no "?" at end)
    n_dead_ends = 0
    for i, a in enumerate(audits):
        if (a.is_too_short and not a.bot_response.strip().endswith("?")
                and not a.tools_called and i < len(audits) - 1):
            n_dead_ends += 1
    s_flow -= n_dead_ends * 8.0

    # Monotone detection: bot never asks a question (no "?" in any response)
    n_questions = sum(1 for a in audits if "?" in a.bot_response)
    if n >= 4 and n_questions == 0:
        s_flow -= 15.0  # bot never asked anything = poor conversational skill

    # Awkward silence: caller had to repeat (consecutive identical caller texts)
    n_caller_repeats = 0
    for i in range(1, len(audits)):
        if (audits[i].caller_text.strip().lower() ==
                audits[i-1].caller_text.strip().lower()):
            n_caller_repeats += 1
    s_flow -= n_caller_repeats * 10.0

    # Goodbye recognition: bot should respond to goodbye with end_call
    # Check if caller said goodbye-like phrases and bot failed to end
    caller_said_bye = False
    bot_ended = False
    for a in audits:
        cl = a.caller_text.lower()
        if any(p in cl for p in ["wiedersehen", "tschüss", "tschüs", "bye",
                                  "das war's", "das wars", "danke das wäre alles",
                                  "das wäre alles"]):
            caller_said_bye = True
        if "end_call" in a.tools_called:
            bot_ended = True
    if caller_said_bye and not bot_ended:
        s_flow -= 10.0

    # Order before info gathering: create_order in first 2 turns = too hasty
    if n >= 4:
        early_order = any(
            "create_order" in a.tools_called
            for a in audits[:2]
        )
        if early_order:
            s_flow -= 8.0

    s_flow = max(0.0, s_flow)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 8: Response Quality (7%)
    # Substantive answers, not deflecting or empty
    # ══════════════════════════════════════════════════════════════════════
    s_response = 100.0
    s_response -= n_deflections * 15.0   # each deflection -15
    s_response -= n_empty       * 20.0   # empty response -20
    s_response -= n_too_short   * 8.0    # too-short -8

    # Unique vocabulary check: if bot uses < 20 unique words total = poor quality
    all_bot_text = " ".join(bot_responses).lower()
    unique_words = set(re.findall(r"\b\w+\b", all_bot_text))
    if n >= 5 and len(unique_words) < 20:
        s_response -= 20.0  # very limited vocabulary

    # Check response variety: if bot gives the exact same starter phrase > 3 times
    starters = [resp[:30].lower() for resp in bot_responses if len(resp) > 30]
    if starters:
        from collections import Counter
        starter_counts = Counter(starters)
        max_starter_freq = max(starter_counts.values())
        if max_starter_freq >= 4:
            s_response -= 15.0  # always starts with the same phrase

    s_response = max(0.0, s_response)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 9: Hallucination / Safety (10%)
    # No fabricated facts, no forbidden self-disclosure
    # ══════════════════════════════════════════════════════════════════════
    s_halluc = 100.0

    # Forbidden self-disclosure (bot admits being AI)
    s_halluc -= n_forbidden * 25.0

    # Price hallucination: > 4 different price claims = suspicious
    price_claims = re.findall(r"\b\d+[,.]?\d*\s*(?:euro|€|EUR)\b", all_bot_text, re.IGNORECASE)
    unique_prices = set(price_claims)
    hallucination_risk = len(unique_prices) > 5
    if hallucination_risk:
        s_halluc -= 15.0

    # Fabricated restaurant name
    if all_bot_text and "doboo" not in all_bot_text:
        other_restaurants = re.findall(r"restaurant\s+(\w+)", all_bot_text)
        if other_restaurants:
            for rname in other_restaurants:
                if rname.lower() not in ("doboo", "das", "unser", "unserem", "im"):
                    s_halluc -= 20.0
                    hallucination_risk = True
                    break

    # Bot claims specific hours/days without being asked
    # (over-specificity: making up hours that might be wrong)
    time_claims = re.findall(r"\b\d{1,2}:\d{2}\b", all_bot_text)
    if len(time_claims) > 6:
        s_halluc -= 10.0  # suspiciously many specific time claims

    # ── MENU DISH VALIDATION: Check if create_order was called for a non-menu dish ──
    # Fix 3 (Iter 7): Aligned with training mock menu (tool_executor.py) and tier2 prompt.
    # Also includes lowercase variants of names returned by get_menu so any LLM output
    # from a real menu response passes the substring check.
    MENU_DISHES = {
        # Canonical DOBOO menu items (tier2 prompt + conversation_nodes)
        "bibimbap", "bulgogi", "kimchi jjigae", "tteokbokki", "japchae",
        "mandu", "tofu jjigae", "tofu bibimbap", "mochi-eis", "mochi eis",
        # Variants returned by training mock menu (tool_executor.py)
        "bibimbap (klassisch)",
    }
    if "create_order" in called_set:
        # Find the bot response context around when create_order was called
        order_context = ""
        for audit in audits:
            if "create_order" in audit.tools_called:
                # Get this turn and previous turn for context
                idx = audits.index(audit)
                if idx > 0:
                    order_context += audits[idx - 1].bot_response + " "
                order_context += audit.bot_response
                break
        
        order_context_lower = order_context.lower()
        mentioned_dishes = [d for d in MENU_DISHES if d in order_context_lower]
        if not mentioned_dishes:
            s_halluc = 0.0
            failures.append("CRITICAL: create_order for non-menu dish")

    s_halluc = max(0.0, s_halluc)

    # ══════════════════════════════════════════════════════════════════════
    # DIM 10: Completeness / Conversation Protocol (5%)
    # Proper greeting with AI disclosure, summary before action,
    # approval before commit, confirmation SMS, proper closing
    # ══════════════════════════════════════════════════════════════════════
    s_complete = 100.0

    # --- (A) GREETING with AI disclosure ---
    # Agent must identify as Sailly / digital AI assistant on first response
    if audits:
        first_resp = audits[0].bot_response.lower()
        greeting_words = ["willkommen", "hallo", "guten", "herzlich", "doboo",
                          "begrüß", "anruf", "helfen", "hilfe"]
        has_greeting = any(g in first_resp for g in greeting_words)
        if not has_greeting:
            s_complete -= 15.0

        ai_disclosure = ["sailly", "ki", "künstliche", "digital", "assistentin",
                         "sprachassistentin"]
        has_ai_disclosure = any(d in first_resp for d in ai_disclosure)
        if not has_ai_disclosure:
            s_complete -= 10.0

    # --- (B) END-CALL recognition ---
    if no_end_call:
        s_complete -= 20.0

    # If conversation < 3 turns, probably incomplete
    if 0 < n < 3:
        s_complete -= 20.0

    # --- (C) SUMMARY before action ---
    # Before create_order or create_reservation, bot should summarize
    # (restate dish/date/time etc.) in the same or preceding turn
    action_tools = called_set & {"create_reservation", "create_order"}
    if action_tools:
        summary_words = ["zusammenfass", "bestätigt", "reserviert", "notiert",
                         "aufgenommen", "gebucht", "bestellung",
                         "also", "ihr", "ihre bestellung"]
        has_summary = any(sw in all_bot_text for sw in summary_words)
        if not has_summary:
            s_complete -= 10.0

    # --- (D) APPROVAL before commit ---
    # Bot should have asked for confirmation before executing order/reservation
    # Look for a question turn before the tool-call turn
    if action_tools and n >= 3:
        approval_words = ["stimmt das", "richtig so", "einverstanden",
                          "bestätigen", "soll ich", "darf ich",
                          "passt das", "korrekt", "in ordnung"]
        has_approval_ask = any(aw in all_bot_text for aw in approval_words)
        if not has_approval_ask:
            s_complete -= 10.0

    # --- (E) CONFIRMATION SMS ---
    # After create_order → send_sms must follow
    if "create_order" in called_set and "send_sms" not in called_set:
        s_complete -= 15.0

    s_complete = max(0.0, s_complete)

    # ══════════════════════════════════════════════════════════════════════
    # COMPOSITE
    # ══════════════════════════════════════════════════════════════════════
    composite = (
        s_task      * WEIGHTS["task"]          +
        s_lang      * WEIGHTS["language"]      +
        s_instr     * WEIGHTS["instruction"]   +
        s_latency   * WEIGHTS["latency"]       +
        s_audio     * WEIGHTS["audio"]         +
        s_stt       * WEIGHTS["stt"]           +
        s_flow      * WEIGHTS["flow"]          +
        s_response  * WEIGHTS["response"]      +
        s_halluc    * WEIGHTS["hallucination"] +
        s_complete  * WEIGHTS["completeness"]
    )

    # ══════════════════════════════════════════════════════════════════════
    # PASS / FAIL
    # ══════════════════════════════════════════════════════════════════════

    # Auto-fail conditions
    if n == 0:
        failures.append("0 turns (crash/timeout)")

    dim_scores = {
        "task": s_task, "language": s_lang, "instruction": s_instr,
        "latency": s_latency, "audio": s_audio, "stt": s_stt,
        "flow": s_flow, "response": s_response,
        "hallucination": s_halluc, "completeness": s_complete,
    }
    for dim_name, dim_val in dim_scores.items():
        if dim_val < AUTOFAIL_DIM:
            failures.append(f"{dim_name} score {dim_val:.0f} < {AUTOFAIL_DIM:.0f}")

    # Specific auto-fail triggers
    if n_english >= 2:
        failures.append(f"Bot spoke English in {n_english} turns")
    if loop_detected:
        failures.append("Conversation loop (4+ repeated responses)")
    if missing and expected_tools:
        failures.append(f"Missing tools: {missing}")
    if n_empty >= 3:
        failures.append(f"{n_empty} empty responses")
    if avg_wer > 0.30 and n >= 3:
        failures.append(f"STT avg WER {avg_wer:.0%}")
    if n_informal >= 3:
        failures.append(f"Used 'du' in {n_informal} turns")

    passed = len(failures) == 0 and composite >= PASS_THRESHOLD
    if not passed and not failures:
        failures.append(f"Composite {composite:.1f} < {PASS_THRESHOLD}")

    return AuditResult(
        scenario_id=scenario_id,
        phase=phase,
        run_number=run_number,
        score_task=round(s_task, 1),
        score_language=round(s_lang, 1),
        score_instruction=round(s_instr, 1),
        score_latency=round(s_latency, 1),
        score_audio=round(s_audio, 1),
        score_stt=round(s_stt, 1),
        score_flow=round(s_flow, 1),
        score_response=round(s_response, 1),
        score_hallucination=round(s_halluc, 1),
        score_completeness=round(s_complete, 1),
        composite=round(composite, 1),
        passed=passed,
        tools_expected=list(expected_tools),
        tools_called=list(called_set),
        tools_missing=missing,
        n_turns=n,
        total_latency_ms=total_latency_ms,
        avg_wer=round(avg_wer, 4),
        n_empty=n_empty,
        n_english=n_english,
        n_informal=n_informal,
        n_repetitions=n_repetitions,
        n_deflections=n_deflections,
        n_too_short=n_too_short,
        n_too_long=n_too_long,
        n_cutoffs=n_cutoffs,
        loop_detected=loop_detected,
        no_end_call=no_end_call,
        hallucination_risk=hallucination_risk,
        failure_reasons=failures,
    )
