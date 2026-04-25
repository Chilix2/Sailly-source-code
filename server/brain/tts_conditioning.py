"""
TTS conditioning for Sailly — adaptive style selection combining
permanent persona, situation context, and caller mood mirroring.

Layer 1: SAILLY_PERSONA — permanent identity, set once per call.
Layer 2: Situation style — derived from ConversationState + pipeline
         outputs BEFORE each turn. 15 discrete styles.
Layer 3: Caller mirror — derived from ASR confidence, lexical signals,
         utterance cadence, and conversation history. 6 mood states.
         (Phase 1: hardcoded NEUTRAL. Phase 2: fully wired.)

All three layers compose into a single TTSDirective passed to the
TTS service before streaming begins.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── Layer 1: Permanent persona ─────────────────────────────────────────────────

SAILLY_PERSONA = (
    "Du bist Sailly, die KI-Sprachassistentin vom Restaurant DOBOO in Bonn. "
    "Deine Stimme ist freundlich-professionell, mittlere Tonhöhe, leicht warm, "
    "nicht süßlich oder überschwänglich. Du klingst wie die Rezeptionistin eines "
    "guten Restaurants, die gerne hilft — nicht wie eine Callcenter-Stimme."
)


# ── Layer 2: Situation styles ──────────────────────────────────────────────────

class Situation(str, Enum):
    GREETING_FIRST           = "greeting_first"
    GREETING_RETURNING       = "greeting_returning"
    INFO_NEUTRAL             = "info_neutral"
    INFO_READBACK            = "info_readback"
    CLARIFY_PATIENT          = "clarify_patient"
    CONFIRM_SUCCESS          = "confirm_success"
    UPSELL_CURIOUS           = "upsell_curious"
    APOLOGY_SOFT             = "apology_soft"
    APOLOGY_SERIOUS          = "apology_serious"
    HANDOFF_CALM             = "handoff_calm"
    ESCALATION_REASSURING    = "escalation_reassuring"
    URGENT_CLEAR             = "urgent_clear"
    WAITING_FILLER           = "waiting_filler"
    REPROMPT_UNDERSTOOD_NONE = "reprompt_understood_none"
    FAREWELL_WARM            = "farewell_warm"


@dataclass(frozen=True)
class SituationStyle:
    tag: str    # inline tag sent on first TTS chunk, e.g. "[warm]"
    prompt: str # style prompt fragment composed with persona
    rate: float # base speaking rate multiplier (1.0 = normal)


# Sprint 2.1: situation rates reverted to their original adaptive values.
# The 2.0x multiplier we applied earlier is replaced by GLOBAL_SPEED_MULTIPLIER
# below, so per-situation distinctions (fast vs. slow) are preserved.
SITUATION_STYLES: dict[Situation, SituationStyle] = {
    Situation.GREETING_FIRST: SituationStyle(
        tag="[warm]",
        prompt=(
            "Begrüße einladend, mit hörbarem Lächeln, mittleres Tempo. "
            "Der Anrufer hört dich zum ersten Mal."
        ),
        rate=2.00,
    ),
    Situation.GREETING_RETURNING: SituationStyle(
        tag="[warm]",
        prompt=(
            "Begrüße wiedererkennend und etwas vertrauter, leicht persönlicher Ton. "
            "Der Anrufer hat schon einmal angerufen."
        ),
        rate=1.00,
    ),
    Situation.INFO_NEUTRAL: SituationStyle(
        tag="[friendly]",
        prompt="Sachlich freundlich, klar, gleichmäßiges Tempo.",
        rate=1.00,
    ),
    Situation.INFO_READBACK: SituationStyle(
        tag="[attentive]",
        prompt=(
            "Bewusst langsamer und deutlich artikuliert — der Anrufer muss "
            "Ziffern, Adressen und Bestelldetails klar verstehen können."
        ),
        rate=0.88,
    ),
    Situation.CLARIFY_PATIENT: SituationStyle(
        tag="[patient]",
        prompt=(
            "Geduldig und freundlich, nicht herablassend, leicht langsamer — "
            "als würdest du freundlich nachfragen, weil du es nicht verstanden hast."
        ),
        rate=0.93,
    ),
    Situation.CONFIRM_SUCCESS: SituationStyle(
        tag="[cheerful]",
        prompt=(
            "Aufrichtig, zurückhaltend fröhlich — als hättest du gerade erfolgreich "
            "geholfen. Nicht euphorisch, nicht übertrieben."
        ),
        rate=1.00,
    ),
    Situation.UPSELL_CURIOUS: SituationStyle(
        tag="[inviting]",
        prompt="Neugierig-einladend, offen, ohne Druck, leicht spielerisch.",
        rate=1.02,
    ),
    Situation.APOLOGY_SOFT: SituationStyle(
        tag="[empathetic]",
        prompt=(
            "Echtes Bedauern, sanfter Ton, leicht gesenkte Stimme, "
            "gemächliches Tempo — eine kleine Unannehmlichkeit wird anerkannt."
        ),
        rate=0.92,
    ),
    Situation.APOLOGY_SERIOUS: SituationStyle(
        tag="[sympathetic]",
        prompt=(
            "Ernst und verantwortungsvoll, keine Fröhlichkeit, bewusst langsamer. "
            "Der Anrufer soll spüren, dass du das wirklich ernst nimmst."
        ),
        rate=0.88,
    ),
    Situation.HANDOFF_CALM: SituationStyle(
        tag="[calm]",
        prompt=(
            "Ruhig, sachlich, kompetent — wie eine erfahrene Fachkraft, "
            "die die Situation im Griff hat und jetzt weiterleitet."
        ),
        rate=0.95,
    ),
    Situation.ESCALATION_REASSURING: SituationStyle(
        tag="[reassuring]",
        prompt=(
            "Beruhigend und kompetent. Signalisiere, dass du dich jetzt kümmerst. "
            "Warm, aber nicht süßlich — der Anrufer ist aufgebracht."
        ),
        rate=0.92,
    ),
    Situation.URGENT_CLEAR: SituationStyle(
        tag="[urgent]",
        prompt="Leicht drängend aber nicht panisch, klar und direkt.",
        rate=1.05,
    ),
    Situation.WAITING_FILLER: SituationStyle(
        tag="[thoughtful]",
        prompt=(
            "Kurze, ruhige Überbrückungsphrase während ein Hintergrundprozess läuft. "
            "Nicht zu lebhaft, nicht zu lang."
        ),
        rate=1.00,
    ),
    Situation.REPROMPT_UNDERSTOOD_NONE: SituationStyle(
        tag="[understanding]",
        prompt=(
            "Geduldig-verständnisvoll, leicht langsamer, keine Frustration im Ton — "
            "der Anrufer wurde mehrfach nicht verstanden oder hat mehrfach nicht geantwortet."
        ),
        rate=0.90,
    ),
    Situation.FAREWELL_WARM: SituationStyle(
        tag="[warm]",
        prompt="Freundlich abschließend, entspannt, nicht gehetzt.",
        rate=0.98,
    ),
}

# Sprint 2.1: global speed multiplier applied AFTER situation × mood, so
# the adaptive per-situation distinctions survive.
GLOBAL_SPEED_MULTIPLIER = float(os.environ.get("GLOBAL_SPEED_MULTIPLIER", "2.0"))


# ── Layer 3: Caller mirror ─────────────────────────────────────────────────────

class CallerMood(str, Enum):
    NEUTRAL    = "neutral"
    FRUSTRATED = "frustrated"
    IMPATIENT  = "impatient"
    CONFUSED   = "confused"
    RELAXED    = "relaxed"
    ELDERLY    = "elderly"


@dataclass(frozen=True)
class CallerMirror:
    prompt_add: str  # appended to situation prompt when non-empty
    rate_mul: float  # multiplied with situation rate


CALLER_MIRRORS: dict[CallerMood, CallerMirror] = {
    CallerMood.NEUTRAL: CallerMirror(
        prompt_add="",
        rate_mul=1.00,
    ),
    CallerMood.FRUSTRATED: CallerMirror(
        prompt_add=(
            "Der Anrufer klingt frustriert — senke die Stimme leicht, "
            "sprich verständnisvoll und merklich ruhiger."
        ),
        rate_mul=0.92,
    ),
    CallerMood.IMPATIENT: CallerMirror(
        prompt_add=(
            "Der Anrufer hat es eilig — knackig und zielgerichtet, "
            "kein Small Talk, direkt zur Sache."
        ),
        rate_mul=1.05,
    ),
    CallerMood.CONFUSED: CallerMirror(
        prompt_add=(
            "Der Anrufer hat etwas nicht verstanden — sprich langsamer, "
            "deutlicher, mit mehr Betonung auf Schlüsselwörtern."
        ),
        rate_mul=0.88,
    ),
    CallerMood.RELAXED: CallerMirror(
        prompt_add=(
            "Der Anrufer ist entspannt — natürliches Tempo, "
            "leichter Gesprächston, darf ganz menschlich klingen."
        ),
        rate_mul=1.00,
    ),
    CallerMood.ELDERLY: CallerMirror(
        prompt_add=(
            "Der Anrufer spricht langsamer — passe dich an, "
            "deutliche Aussprache, ruhiges Tempo, keine Eile."
        ),
        rate_mul=0.85,
    ),
}


# ── Signal detection (Phase 2) ────────────────────────────────────────────────

_FRUSTRATION_KW = [
    "schon wieder", "schon x-mal", "dritte mal", "zum wiederholten mal",
    "unmöglich", "lächerlich", "frechheit", "unverschämt",
    "keine lust", "reicht mir", "habe genug",
    "nicht akzeptabel", "inakzeptabel",
    "wütend", "sauer", "ärgerlich",
    # Sprint 2.2: demo-6cf65e58003d T2 analysis — add phrases that
    # indicate frustration without explicit anger keywords.
    "was willst du", "was wollen sie", "jetzt von mir", "jetzt schon",
    "hab ich doch gesagt", "ich hab schon gesagt", "ich habe doch gesagt",
    "vorhin gesagt", "hab ich schon",
    "hab ich dir gesagt", "wie oft noch",
    "verstehst du nicht", "verstehen sie nicht",
    # Terse dismissal / sign-off patterns (T6 "lass mal")
    "lass mal", "schon gut", "egal",
]
_IMPATIENCE_KW = [
    "schnell", "sofort", "jetzt bitte", "bitte eilen",
    "habe keine zeit", "kann nicht warten",
    "machen sie hinne", "zack zack",
]
_CONFUSION_KW = [
    "wie bitte", "was haben sie gesagt", "nochmal sagen",
    "versteh ich nicht", "was meinen sie",
    "häh", "kapier ich nicht",
]
_RELAXED_KW = [
    "kein stress", "alles gut", "super", "prima", "wunderbar",
    "hehe", "haha", "ach so",
]


def _detect_repetition(recent: list) -> bool:
    """True if the caller is repeating the same content words across the last 3 turns."""
    if len(recent) < 3:
        return False
    _STOPWORDS = {"dass", "eine", "einen", "sein", "haben", "werde",
                  "können", "bitte", "auch", "noch", "nicht", "aber"}

    def content_words(s: str) -> set:
        return {
            w for w in re.findall(r"\w+", s.lower())
            if len(w) > 3 and w not in _STOPWORDS
        }

    sets = [content_words(u) for u in recent[-3:]]
    if not all(sets):
        return False
    common = sets[0] & sets[1] & sets[2]
    return len(common) >= 2


def detect_caller_mood(
    last_utterance: str,
    recent_utterances: list,
    asr_mean_confidence: float,
    utterance_duration_ms: int,
    escalation_requested: bool,
    consecutive_reprompts: int,
) -> CallerMood:
    """Rule-based mood detection. All signals from existing pipeline data."""
    text = (last_utterance or "").lower()
    recent_text = " ".join(recent_utterances[-3:]).lower() if recent_utterances else text

    if escalation_requested:
        return CallerMood.FRUSTRATED

    frustration_hits = sum(1 for kw in _FRUSTRATION_KW if kw in recent_text)
    if frustration_hits >= 2:
        return CallerMood.FRUSTRATED
    if frustration_hits >= 1 and "!" in (last_utterance or ""):
        return CallerMood.FRUSTRATED

    # Sprint 2.2: strong cross-turn signal — if "hab ich gesagt" (or variant)
    # appears in 2+ recent turns the caller has repeated themselves, which
    # is near-certain frustration.
    _HAB_ICH_PATTERNS = ["hab ich gesagt", "habe ich gesagt", "hab ich doch gesagt",
                          "hab ich schon", "ich hab gesagt", "ich habe gesagt"]
    hab_ich_turn_hits = sum(
        1 for u in (recent_utterances or [])
        if any(p in (u or "").lower() for p in _HAB_ICH_PATTERNS)
    )
    if hab_ich_turn_hits >= 2:
        return CallerMood.FRUSTRATED

    if _detect_repetition(recent_utterances):
        return CallerMood.FRUSTRATED

    if any(kw in text for kw in _CONFUSION_KW):
        return CallerMood.CONFUSED
    if asr_mean_confidence < 0.70:
        return CallerMood.CONFUSED
    if consecutive_reprompts >= 2:
        return CallerMood.CONFUSED

    if any(kw in text for kw in _IMPATIENCE_KW):
        return CallerMood.IMPATIENT
    words = text.split()
    word_count = len(words)
    if word_count <= 3 and 200 < utterance_duration_ms < 1500:
        return CallerMood.IMPATIENT

    if utterance_duration_ms > 0:
        wpm = (word_count / (utterance_duration_ms / 1000)) * 60
        if word_count >= 15 and wpm < 100:
            return CallerMood.ELDERLY

    if any(kw in text for kw in _RELAXED_KW):
        return CallerMood.RELAXED

    return CallerMood.NEUTRAL


# ── Turn context ───────────────────────────────────────────────────────────────

@dataclass
class TurnContext:
    """Everything the situation selector and mood detector need.

    Populated from ConversationState and BrainService fields BEFORE
    process_turn() is called. Tool results from the CURRENT turn are
    not yet available (tools execute after LLM streaming starts).
    """
    # Conversation position
    node_name: str = ""
    turn_idx: int = 0
    is_first_turn: bool = False
    is_returning_caller: bool = False

    # State flags (from prior turns — all available before streaming)
    escalation_requested: bool = False
    verify_address_failed: bool = False
    order_just_committed: bool = False
    reservation_just_committed: bool = False
    is_goodbye: bool = False
    is_waiting_filler: bool = False
    contains_readback: bool = False
    is_upsell: bool = False

    # Quality / reprompt signals
    consecutive_reprompts: int = 0
    asr_mean_confidence: float = 1.0

    # Caller utterance data (Phase 2 mood detection)
    last_caller_utterance: str = ""
    recent_caller_utterances: list = field(default_factory=list)
    utterance_duration_ms: int = 0


# ── Situation selection ────────────────────────────────────────────────────────

def select_situation(ctx: TurnContext) -> Situation:
    """Pick the situation style purely from conversation state.

    Priority order mirrors call flow: terminal states first (goodbye,
    filler, escalation), then success/failure outcomes, then content type.
    """
    if ctx.is_goodbye:
        return Situation.FAREWELL_WARM
    if ctx.is_waiting_filler:
        return Situation.WAITING_FILLER
    if ctx.consecutive_reprompts >= 2:
        return Situation.REPROMPT_UNDERSTOOD_NONE
    if ctx.escalation_requested:
        return Situation.ESCALATION_REASSURING
    if ctx.verify_address_failed:
        return Situation.APOLOGY_SOFT
    if ctx.order_just_committed or ctx.reservation_just_committed:
        return Situation.CONFIRM_SUCCESS
    if ctx.contains_readback:
        return Situation.INFO_READBACK
    if ctx.is_upsell:
        return Situation.UPSELL_CURIOUS
    if ctx.is_first_turn or (ctx.node_name == "greeting" and ctx.turn_idx == 0):
        return (
            Situation.GREETING_RETURNING
            if ctx.is_returning_caller
            else Situation.GREETING_FIRST
        )
    if ctx.asr_mean_confidence < 0.70:
        return Situation.CLARIFY_PATIENT
    return Situation.INFO_NEUTRAL


# ── Final assembly ─────────────────────────────────────────────────────────────

@dataclass
class TTSDirective:
    """Final per-turn TTS instruction for SaillyGeminiTTSService."""
    style_instruction: str  # full prompt: persona + situation + mood mirror
    inline_tag: str         # e.g. "[warm]" — prepended to first chunk only
    prosody_rate_pct: int   # e.g. 92 → cascade_speaking_rate = 0.92
    situation: Situation = Situation.INFO_NEUTRAL
    mood: CallerMood = CallerMood.NEUTRAL


def build_tts_directive(
    ctx: TurnContext,
    *,
    phase2_mood: bool = False,
) -> TTSDirective:
    """Compose the full TTS directive for this turn.

    phase2_mood=False (default, Phase 1): CallerMood.NEUTRAL always.
    phase2_mood=True  (Phase 2): detect mood from ctx signals.
    """
    situation = select_situation(ctx)

    if phase2_mood:
        mood = detect_caller_mood(
            last_utterance=ctx.last_caller_utterance,
            recent_utterances=ctx.recent_caller_utterances,
            asr_mean_confidence=ctx.asr_mean_confidence,
            utterance_duration_ms=ctx.utterance_duration_ms,
            escalation_requested=ctx.escalation_requested,
            consecutive_reprompts=ctx.consecutive_reprompts,
        )
    else:
        mood = CallerMood.NEUTRAL

    sit_style = SITUATION_STYLES[situation]
    mirror = CALLER_MIRRORS[mood]

    parts = [SAILLY_PERSONA, sit_style.prompt]
    if mirror.prompt_add:
        parts.append(mirror.prompt_add)
    full_prompt = " ".join(parts)

    # Sprint 2.1: apply GLOBAL_SPEED_MULTIPLIER after situation × mood,
    # and raise clamp from 115 to 200 so the adaptive distinctions
    # between fast/normal/slow situations actually survive into the
    # final cascade_speaking_rate. Google's Cloud TTS accepts 0.25–2.0.
    raw_rate = sit_style.rate * mirror.rate_mul * GLOBAL_SPEED_MULTIPLIER
    rate_pct = max(75, min(200, round(raw_rate * 100)))

    logger.info(
        f"[TTS-COND] situation={situation.value} mood={mood.value} "
        f"rate={rate_pct}% tag={sit_style.tag} "
        f"global_mul={GLOBAL_SPEED_MULTIPLIER}"
    )

    return TTSDirective(
        style_instruction=full_prompt,
        inline_tag=sit_style.tag,
        prosody_rate_pct=rate_pct,
        situation=situation,
        mood=mood,
    )
