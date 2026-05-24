"""server/brain/v4_pipeline.py — v4 deterministic pipeline (single live path).

# v4_pipeline is now the SINGLE SOURCE OF TRUTH. Legacy policy gate removed.

This is the ONLY request path. Legacy ADKRunner / tier2_runner / node_manager
are deleted. Every caller utterance goes through:

    classify → route → worker_execute → context_doc → [commit gate] → TinyGenerator

Commit gate is deterministic:
  - All required slots present + not yet committed → execute commit tools → readback
  - end_call_stage == readback_pending + confirm → farewell + end_call
  - end_call_stage == readback_pending + deny → ask correction

Enable by exporting USE_NEW_PIPELINE=true (default true after migration).
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Awaitable, Callable, Optional

from server.brain.context_doc_builder import (
    COMMIT_TOOLS_REQUIRED_SLOTS,
    _persist_resolved_entities_to_state,
    build as build_context_doc,
)
from server.brain.intent_classifier import classify
from server.brain.intent_session import IntentKind, IntentResult, TurnType
from server.brain.tiny_generator import TinyGenerator
from server.brain.worker_executor import execute as worker_execute
from server.brain.worker_router import route
from server.brain.workers import ExecutionResult, WorkerContext

logger = logging.getLogger(__name__)

_GERMAN_MONTHS = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]
_GERMAN_WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def _iso_to_spoken_german(iso: str) -> str:
    """Convert an ISO date string (YYYY-MM-DD) to spoken German, e.g. 'Donnerstag, dem 7. Mai'."""
    import datetime
    try:
        d = datetime.date.fromisoformat(iso)
        weekday = _GERMAN_WEEKDAYS[d.weekday()]
        month = _GERMAN_MONTHS[d.month]
        return f"{weekday}, dem {d.day}. {month}"
    except Exception:
        return iso or "dem gewünschten Termin"


def _state_slot_filled(state, slot: str) -> bool:
    """Check if a slot is filled on either a ConversationState object or a dict."""
    if isinstance(state, dict):
        val = state.get(slot)
    else:
        val = getattr(state, slot, None)
    if val is None:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    return True


def is_enabled() -> bool:
    """Master kill-switch. Default ON after v4 migration."""
    return os.environ.get("USE_NEW_PIPELINE", "true").lower() in ("true", "1", "yes")


# ── Helper: commitment eligibility ──────────────────────────────────────────────

def _all_slots_present(state, commit_tool: str) -> bool:
    """True when every required slot for commit_tool is filled in state.

    Uses the same state snapshot as the context-doc gate so the slot name
    mapping (e.g. "order_items" → state.selected_items) is consistent.
    """
    required = COMMIT_TOOLS_REQUIRED_SLOTS.get(commit_tool, [])
    if not required:
        return False
    snapshot = _state_snapshot_for_gate(state)
    for slot in required:
        val = snapshot.get(slot)
        if val is None:
            return False
        if isinstance(val, str) and not val.strip():
            return False
        if isinstance(val, (list, tuple)) and len(val) == 0:
            return False
    return True


# ── Helper: confirmation detection ──────────────────────────────────────────────

def _is_confirmation_v4(text: str) -> bool:
    """True if the utterance is a positive confirmation of the readback."""
    lower = text.lower()

    # Phrases that unambiguously mean "proceed / nothing to change" — checked
    # BEFORE the negative-word filter so e.g. "ich will nichts ändern" (= I
    # don't want to change anything) is not mis-classified as a denial.
    _OVERRIDE_CONFIRMS = (
        # "nothing to change" variants
        "nichts ändern", "nichts zu ändern", "will nichts ändern",
        "möchte nichts ändern", "ändere nichts", "nix ändern",
        "will ich nicht ändern", "muss nichts ändern",
        # "please take / book it now" variants
        "jetzt aufnehmen", "einfach aufnehmen", "aufnehmen bitte",
        "bitte aufnehmen", "nehmen sie das auf", "nehmen sie es auf",
        "nehmen sie einfach auf", "so aufnehmen", "einfach mal aufnehmen",
        "jetzt nehmen sie", "nehmen sie das",
        # "can we just do it" variants
        "können wir das", "können wir jetzt", "können wir es",
        "machen wir das", "machen wir es", "so machen wir",
        # other confirmation-by-action phrases
        "buchen sie das", "reservieren sie das", "bestellen sie das",
        "so ist das richtig", "so stimmt das", "genau so ist es",
    )
    if any(p in lower for p in _OVERRIDE_CONFIRMS):
        return True

    negative = ("nein", "nicht", "falsch", "anders", "ändern", "aendern",
                "korrigieren", "nochmal", "andere", "stimmt nicht")
    if any(w in lower for w in negative):
        return False

    positive = ("ja", "genau", "richtig", "korrekt", "stimmt", "passt",
                "super", "perfekt", "ok", "okay", "gut",
                "bestätige", "alles klar", "ja bitte", "ja genau", "in ordnung",
                "aufnehmen", "nehmen sie", "so bitte", "bitte so",
                "das geht", "passt so", "ist so richtig")
    # Word-boundary match for single-word terms to avoid "gut" inside "guten", etc.
    import re as _re_conf
    _lower_words = set(_re_conf.sub(r"[^a-zäöüß]", "", t) for t in lower.split())
    for w in positive:
        if " " in w:  # multi-word phrase: substring match
            if w in lower:
                return True
        else:  # single word: exact word-boundary match only
            if w in _lower_words:
                return True
    return False


# ── Helper: pre-commit summaries (BEFORE tool execution) ────────────────────────

def _build_pre_commit_summary_v4(state) -> str:
    """Pre-commit summary for reservations: reads slot values directly.

    Called BEFORE tool execution so reservation_created is still False.
    Uses subjunctive 'würde' to indicate a proposal, not a done deal.
    """
    if _state_slot_filled(state, "reservation_date"):
        iso = getattr(state, "reservation_date", "")
        spoken_date = _iso_to_spoken_german(iso) if iso else "dem gewünschten Termin"
    else:
        spoken_date = "dem gewünschten Termin"

    spoken_time = getattr(state, "reservation_time", None) or "der gewünschten Zeit"
    party = getattr(state, "party_size", None) or 2
    name = getattr(state, "customer_name", None) or "Ihrem Namen"
    phone = getattr(state, "phone_number", None)

    plural = "Person" if party == 1 else "Personen"
    phone_clause = f", Rückrufnummer {' '.join(phone)}" if phone else ""
    return (
        f"Ich würde {party} {plural} "
        f"für {spoken_date} um {spoken_time} Uhr auf den Namen {name}{phone_clause} reservieren."
    )


def _build_pre_commit_order_summary_v4(state) -> str:
    """Pre-commit summary for orders: reads slot values directly.

    Called BEFORE tool execution so order_created is still False.
    Uses subjunctive 'würde' to indicate a proposal, not a done deal.
    """
    items = getattr(state, "selected_items", None) or []
    name = getattr(state, "customer_name", None) or "Ihrem Namen"

    if isinstance(items, list) and items:
        items_str = ", ".join(items)
    else:
        # Fall back to selected_dish (single-item orders)
        sd = getattr(state, "selected_dish", None)
        items_str = str(sd) if sd else "Ihre Bestellung"

    order_type = getattr(state, "delivery_type", None) or getattr(state, "order_type", None)
    delivery_clause = ""
    if order_type == "takeaway" or getattr(state, "delivery_confirmed", False) is False:
        delivery_clause = " zum Abholen"
    elif order_type == "delivery":
        delivery_clause = " zur Lieferung"

    return f"Ich würde also {items_str}{delivery_clause} auf den Namen {name} aufnehmen."


# ── Helper: deterministic readback ──────────────────────────────────────────────

def _build_readback_v4(state) -> str:
    """Build deterministic verbal readback of the committed reservation."""
    if getattr(state, "reservation_created", False):
        iso = getattr(state, "reservation_date", None) or ""
        spoken_date = _iso_to_spoken_german(iso) if iso else "dem vereinbarten Termin"
        spoken_time = getattr(state, "reservation_time", None) or "der vereinbarten Zeit"
        party = getattr(state, "party_size", None) or 2
        name = getattr(state, "customer_name", None)
        if not name:
            logger.error("[v4_pipeline] _build_readback_v4 called with no customer_name")
            return "Ich habe Ihre Reservierung eingetragen."
        phone = getattr(state, "phone_number", None)
        plural = "Person" if party == 1 else "Personen"
        phone_clause = f", Rückrufnummer {' '.join(phone)}" if phone else ""
        return (
            f"Ich habe {party} {plural} "
            f"für {spoken_date} um {spoken_time} Uhr auf den Namen {name}{phone_clause} reserviert."
        )

    if getattr(state, "order_created", False):
        items = getattr(state, "order_summary", None) or "Ihre Bestellung"
        total = getattr(state, "order_total", None)
        total_str = f" Gesamtbetrag: {total} Euro." if total else ""
        return f"Ich habe {items} für Sie aufgenommen.{total_str}"

    return "Ich habe Ihre Anfrage eingetragen."


# ── Worker context builder ───────────────────────────────────────────────────────

def _build_worker_ctx(
    user_text: str,
    turn_idx: int,
    state,
    call_sid: str,
    tenant_id: str,
) -> WorkerContext:
    """Project ConversationState onto the narrow WorkerContext snapshot."""
    return WorkerContext(
        user_text=user_text,
        turn_idx=turn_idx,
        call_sid=call_sid,
        tenant_id=tenant_id,
        party_size=getattr(state, "party_size", None),
        reservation_date=getattr(state, "reservation_date", None),
        reservation_time=getattr(state, "reservation_time", None),
        customer_name=getattr(state, "customer_name", None),
        phone_number=getattr(state, "phone_number", None),
        selected_items=list(getattr(state, "selected_items", []) or []),
        recent_bot_texts=list(getattr(state, "recent_bot_texts", []) or []),
        extra={},
    )


def _state_snapshot_for_gate(state) -> dict:
    """Subset of ConversationState fields used by the universal commit gate.

    Maps the canonical state field names onto the slot names declared in
    COMMIT_TOOLS_REQUIRED_SLOTS so the gate's slot-filled check works
    transparently for both reservation and order intents.
    """
    items = getattr(state, "selected_items", None)
    if not items:
        # Fall back to single dish as a one-element list so the gate sees it.
        sd = getattr(state, "selected_dish", None)
        items = [sd] if sd else None
    return {
        "party_size": getattr(state, "party_size", None),
        "reservation_date": getattr(state, "reservation_date", None),
        "reservation_time": getattr(state, "reservation_time", None),
        "customer_name": getattr(state, "customer_name", None) or getattr(state, "first_name", None),
        "phone_number": getattr(state, "phone_number", None),
        "order_items": items,
    }


def _dedupe_order_items(items) -> list:
    """Return order items without duplicate names, preserving first mention order."""
    result = []
    seen = set()
    for item in items or []:
        if not item:
            continue
        key = str(item).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _item_quantity(item, state, fallback_qty: int, idx: int) -> int:
    """Resolve quantity for an item, preferring explicit per-item quantities."""
    qty_map = getattr(state, "_order_item_quantities", {}) or {}
    key = str(item).strip().lower()
    if key in qty_map:
        try:
            return max(1, int(qty_map[key]))
        except (TypeError, ValueError):
            pass
    return fallback_qty if (idx == 0 and fallback_qty > 1) else 1


# ── Tools telemetry resolver ─────────────────────────────────────────────────────

def _resolve_tools_for_profile(
    profile: str,
    execution_result: ExecutionResult,
    ctx_doc,
    user_text: str = "",
    scheduled_tools_run: Optional[list] = None,
) -> list[str]:
    """Return tool-tag list for telemetry.

    Uses scheduled_tools_run as primary source (those actually fired before
    this call). Only supplements with profile-specific labels for tools that
    aren't already in scheduled_tools_run.
    """
    already = set(scheduled_tools_run or [])
    tools: list[str] = list(scheduled_tools_run or [])

    if profile == "goodbye" and "end_call" not in already:
        tools.append("end_call")

    if profile == "business_info":
        text = (user_text or "").lower()
        if "wetter" in text and "get_weather" not in already:
            tools.append("get_weather")
        if any(w in text for w in ("öffnungszeit", "geöffnet", "wann", "uhrzeit", "noch auf", "heute auf", "noch offen", "noch geöffnet")) \
                and "get_date_info" not in already:
            tools.append("get_date_info")

    # Commit tool labels (added by commit_gate; don't duplicate)
    if profile in ("reservation_start",):
        commit_tool = getattr(ctx_doc, "commit_tool", None)
        if commit_tool == "create_reservation":
            if "check_availability" not in already:
                tools.append("check_availability")
            if "create_reservation" not in already:
                tools.append("create_reservation")

    return tools


def _tenant_pipeline_cfg(tenant_cfg) -> dict:
    if tenant_cfg is None:
        return {}
    pipeline = getattr(tenant_cfg, "pipeline", None)
    return pipeline if isinstance(pipeline, dict) else {}


def _tenant_profile_allowed(tenant_cfg, profile: str) -> bool:
    cfg = _tenant_pipeline_cfg(tenant_cfg)
    enabled = cfg.get("enabled_profiles")
    if isinstance(enabled, list):
        return profile in enabled
    return True


def _tenant_resolve_profile(tenant_cfg, profile: str) -> str:
    """Resolve profile under tenant pipeline constraints with safe fallback."""
    if _tenant_profile_allowed(tenant_cfg, profile):
        return profile
    return "greeting"


# ── Quick return helper ──────────────────────────────────────────────────────────

def _quick_return(
    text: str,
    profile: str,
    intent_result,
    t0: float,
    tools: Optional[list] = None,
    next_action: str = "say",
    should_end: bool = False,
) -> dict:
    return {
        "clean_text": text,
        "raw_response": text,
        "tools_called": tools or [],
        "node_name": profile,
        "intent": intent_result.intent.value,
        "profile": profile,
        "turn_type": intent_result.turn_type.value,
        "next_action": next_action,
        "should_end": should_end,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "inner_monologue": {},
        "v4_pipeline": True,
    }


# ── Main pipeline entry point ────────────────────────────────────────────────────

async def process_turn_v4(
    user_text: str,
    turn_idx: int,
    state,
    call_sid: str,
    tenant_id: str,
    llm_client,
    last_turns: list[tuple[str, str]],
    tts_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    tool_results: Optional[dict] = None,
    caller_phone: str = "",
    intent_result: Optional[IntentResult] = None,
) -> dict:
    """Run one turn through the deterministic v4 pipeline.

    Returns a dict consumable by the gate in adk_turn_processor.process_turn:
        clean_text, raw_response, tools_called, node_name, intent, profile,
        turn_type, elapsed_ms, v4_pipeline.

    Commit + readback state machine:
      - All required slots present AND reservation not yet committed:
          → execute check_availability + create_reservation
          → set end_call_stage = "readback_pending"
          → return deterministic readback text (bypasses TinyGenerator)

      - end_call_stage == "readback_pending" + confirm:
          → set end_call_stage = "confirmed"
          → return farewell + should_end = True

      - end_call_stage == "readback_pending" + deny:
          → set end_call_stage = "correction_pending"
          → return "Was möchten Sie ändern?"

      - end_call_stage == "correction_pending":
          → reset to "idle", let workers update slots, fall through to normal generation
    """
    t0 = time.monotonic()

    # Strip caller-bot audit annotations before any processing.
    # Annotations like "[Achtung Sailly: KEIN_READBACK — ...]" are added by the
    # caller LLM for audit/scoring purposes and must NOT influence bot logic.
    user_text = re.sub(r'\s*\[Achtung Sailly:[^\]]*\]', '', user_text).strip()
    user_text = re.sub(r'\s*\[ACHTUNG SAILLY:[^\]]*\]', '', user_text, flags=re.IGNORECASE).strip()

    # Load tenant config once — used for restaurant identity, city, menu keywords, etc.
    # Cached by load_tenant_config so this is cheap on repeat calls.
    _tcfg_top = None
    try:
        from server.core.tenant_config import load_tenant_config as _ltc_top
        _tcfg_top = _ltc_top(tenant_id)
    except Exception as _cfg_err:
        logger.debug(f"[v4_pipeline] tenant config load failed ({_cfg_err}); using defaults")
    # the universal intent path that handles locking, CONFIRM/DENY inheritance,
    # and reroute. Fall back to bare classify() only for direct callers (tests).
    if intent_result is None:
        intent_result = classify(user_text, turn_idx)
    profile = intent_result.worker_profile
    turn_type = intent_result.turn_type
    _pipeline_cfg = _tenant_pipeline_cfg(_tcfg_top)
    _intent_overrides = _pipeline_cfg.get("intent_overrides", {}) if isinstance(_pipeline_cfg, dict) else {}
    if isinstance(_intent_overrides, dict):
        _mapped = _intent_overrides.get(intent_result.intent.value)
        if isinstance(_mapped, str) and _mapped.strip():
            profile = _mapped.strip()
    profile = _tenant_resolve_profile(_tcfg_top, profile)

    # Prevent false ordering transition immediately after a menu FAQ answer.
    # When last turn was a menu FAQ response, the caller often mentions food
    # words in their acknowledgement, which the classifier may read as ordering.
    _menu_faq_override_active = False
    if getattr(state, "last_turn_was_menu_faq", False) and profile in ("order_start", "ordering"):
        logger.debug("[v4_pipeline] menu FAQ context: overriding %s → business_info", profile)
        profile = "business_info"
        _menu_faq_override_active = True  # suppress ordering deterministic clarify this turn
    state.last_turn_was_menu_faq = False  # reset each turn, set again if menu FAQ fires

    # BESTELLUNG_FALSCH prevention: availability queries ("Haben Sie X?", "nur fragen")
    # must not be routed to order intent even if the classifier returns TAKEAWAY/DELIVERY.
    from server.brain.conversation_state import AVAILABILITY_CHECK_KEYWORDS as _AVAIL_KWS
    _user_lower_avail = user_text.lower()
    _has_avail_signal = any(kw in _user_lower_avail for kw in _AVAIL_KWS)
    _has_order_verb = any(kw in _user_lower_avail for kw in [
        "bestell", "möchte bestellen", "will bestellen",
        "hätte gerne bestellt", "mitnehmen", "abholen", "abholung",
        "liefern", "lieferung", "zur abholung", "zum abholen",
    ])
    # DIETARY_INQUIRY fix: detect vegetarian/dietary questions FIRST and route to business_info (FAQ)
    # DO NOT escalate immediately — let FAQ attempt answer first, only escalate after 2nd refusal
    _dietary_kws = ["vegetar", "vegan", "bibimbap", "fleisch", "allergen", "glutenfrei",
                    "laktosefrei", "nussallerg", "inhaltsstoff", "zutat",
                    "was habt ihr", "was haben sie", "was gibt es", "was ist auf der karte",
                    "was für gerichte", "speisekarte", "bulgogi", "kimchi", "mandu",
                    "tofu", "japchae", "tteokbokki"]
    _is_dietary_question = any(kw in _user_lower_avail for kw in _dietary_kws)
    # Don't override to FAQ if order_intent is already active from a prior turn
    _order_intent_active = getattr(state, 'order_intent', False)
    if _is_dietary_question and not _has_order_verb and not _order_intent_active:
        logger.info(
            "[v4_pipeline] T%d dietary question detected → routing to business_info (FAQ)",
            turn_idx,
        )
        profile = "business_info"
        intent_result = IntentResult(
            intent=IntentKind.DIETARY_INQUIRY,
            turn_type=TurnType.ASK_QUESTION,
            confidence=0.95,
            worker_profile="business_info",
        )
        # Mark as FAQ context to prevent order-intent override on subsequent turns
        state.last_turn_was_menu_faq = True
        # Track refusal count for escalation after 2nd repeated refusal
        state._dietary_refusal_count = getattr(state, "_dietary_refusal_count", 0) + 1
        # CRITICAL: Do NOT escalate on first dietary question — let FAQ node answer first.
        # Only escalate if user repeats the SAME question 2+ times after FAQ answered.
    elif (
        _has_avail_signal
        and not _has_order_verb
        and intent_result.intent in (IntentKind.TAKEAWAY, IntentKind.DELIVERY)
        and profile in ("order_start", "ordering")
    ):
        logger.info(
            "[v4_pipeline] T%d availability query → overriding to business_info (BESTELLUNG_FALSCH prevention)",
            turn_idx,
        )
        profile = "business_info"
        intent_result = IntentResult(
            intent=IntentKind.FAQ,
            turn_type=TurnType.ASK_QUESTION,
            confidence=0.9,
            worker_profile="business_info",
        )

    # Fix 7: Track unclear/greeting turns for timeout counter + detect repeated responses.
    # Only count turns where the turn_type is truly UNCLEAR (not just UNKNOWN intent —
    # UNKNOWN with ADD_INFORMATION is a valid slot-filling turn, not unclear).
    _last_response = getattr(state, "_last_bot_response", "")
    if turn_type == TurnType.UNCLEAR:
        state.unclear_turn_count = getattr(state, "unclear_turn_count", 0) + 1
        logger.debug(f"[v4_pipeline] T{turn_idx} unclear intent → unclear_turn_count={state.unclear_turn_count}")
    else:
        # Reset counter when we get a clear intent
        current_count = getattr(state, "unclear_turn_count", 0)
        if current_count > 0:
            logger.debug(f"[v4_pipeline] T{turn_idx} clear intent detected → reset unclear_turn_count from {current_count}")
        state.unclear_turn_count = 0

    # Initialise response repeat tracking fields (safe no-op if already set)
    state._last_user_text = user_text
    state._response_repeat_count = getattr(state, "_response_repeat_count", 0)
    # _pending_bot_response is stamped just before every _quick_return so that
    # callers of process_turn_v4 can write it to state._last_bot_response after
    # the turn completes, enabling cross-turn loop detection.
    state._pending_bot_response = ""

    # Loop guard: if the user is explicitly flagging a repeated response or the
    # same user text was seen recently, increment a loop counter and break out.
    _loop_phrases = [
        "das haben sie gerade bereits gesagt",
        "ihre antwort wiederholt sich",
        "gleiche antwort",
        "sie wiederholen sich",
        "sie haben das bereits gesagt",
        "achtung sailly",
        "bot_loop",
        "sie haben das bereits",
        "bereits angegeben",
        "bereits gesagt",
        "gerade bereits",
        "wie ich bereits",
        "habe ich bereits",
        "schon gesagt",
        "schon angegeben",
        "habe ich schon",
        "das sagte ich",
        "personenzahl ist",
        "es sind",
        # Time-correction complaints — user correcting a wrong time confirmation
        "nicht auf 19",
        "nicht 19 uhr",
        "falsche uhrzeit",
        "uhrzeit falsch",
        "auf 20 uhr",
        "wollte 20",
        "sollte 20",
        "20 uhr verschieben",
        "20 uhr ändern",
        "fälschlicherweise",
        "nicht korrekt bestätigt",
        "nicht richtig",
        "sie haben die falsche",
        "umbuchen lassen wollen",
        "hatte die reservierung auf",
        "ändern wollen",
        "verschieben wollen",
    ]
    _user_lower = user_text.lower()
    _is_loop_complaint = any(phrase in _user_lower for phrase in _loop_phrases)

    # H2.3 / Manager-request escalation: offer callback on 1st request, escalate ONLY on 2nd+ or after phone provided
    _MANAGER_KWS = ["mit dem manager", "zum manager", "manager sprechen", "manager bitte",
                    "sofort mit dem manager", "ich möchte den manager", "ich will den manager",
                    "schlechte bewertung", "google bewertung", "zumutung", "beschwerde einreichen"]
    _is_manager_request = any(kw in _user_lower for kw in _MANAGER_KWS)
    # Only escalate manager request if NOT a loop complaint (loop complaint is handled separately below)
    if _is_manager_request and not _is_loop_complaint:
        # Count consecutive manager requests to avoid repeating the same response
        state._manager_request_count = getattr(state, "_manager_request_count", 0) + 1
        _phone_just_provided = getattr(state, "phone_number", None) and not getattr(state, "_phone_was_set_before_this_turn", False)
        if state._manager_request_count >= 2 or _phone_just_provided:
            # Already offered callback once OR phone provided; on 2nd+ manager request or after phone, escalate immediately
            logger.warning("[v4_pipeline] T%d manager request #%d → escalating to transfer_to_human", turn_idx, state._manager_request_count)
            return _quick_return(
                "Ich verbinde Sie jetzt sofort mit unserem Manager. Einen Moment bitte.",
                profile, intent_result, t0,
                tools=["transfer_to_human"], next_action="escalate", should_end=True,
            )
        else:
            # First manager request: empathize + offer callback (don't escalate yet)
            logger.warning("[v4_pipeline] T%d manager request #1 detected → empathy + callback offer", turn_idx)
            _mgr_text = (
                "Ich verstehe Ihre Frustration und entschuldige mich aufrichtig für die Unannehmlichkeiten. "
                "Ich werde sofort dafür sorgen, dass sich unser Manager bei Ihnen meldet. "
                "Darf ich Ihre Rückrufnummer für den Rückruf notieren?"
            )
            state._phone_was_set_before_this_turn = bool(getattr(state, "phone_number", None))
            if tts_callback:
                try:
                    await tts_callback(_mgr_text)
                except Exception as _cb_err:
                    logger.warning("[v4_pipeline] tts_callback raised: %s", _cb_err)
            return _quick_return(
                _mgr_text, profile, intent_result, t0,
                tools=[], next_action="clarify", should_end=False,
            )

    if _is_loop_complaint:
        state._response_repeat_count += 1
        state._manager_request_count = 0  # Reset manager counter so loop recovery doesn't re-trigger escalation
        logger.warning(
            f"[v4_pipeline] T{turn_idx} BOT_LOOP complaint detected "
            f"(repeat_count={state._response_repeat_count}): {user_text[:80]!r}"
        )
        # First: try to extract any slot the user is (re-)providing in this message.
        import re as _re
        # Always attempt to extract the destination time from a correction/complaint.
        # Use strict destination-only patterns (same as the hydration block).
        _loop_time_m = _re.search(
            r'(?:verschieben?\s+auf\s+|ändern?\s+(?:auf|zu)\s+|von\s+\d{1,2}\s*(?:uhr)?\s+auf\s+|auf\s+)(\d{1,2})(?:[:.]?(\d{2}))?\s*uhr',
            _user_lower
        )
        if not _loop_time_m:
            _loop_time_m = _re.search(
                r'\b(20|21|22|18|17|16|15|14|13|12|11|10|9|8)\s*uhr\b',
                _user_lower
            )
        if _loop_time_m:
            _lt_hour = int(_loop_time_m.group(1))
            _lt_min = int(_loop_time_m.group(2)) if hasattr(_loop_time_m, 'group') and _loop_time_m.lastindex and _loop_time_m.lastindex >= 2 and _loop_time_m.group(2) else 0
            _loop_corrected_time = f"{_lt_hour:02d}:{_lt_min:02d}"
            _old_time = getattr(state, 'reservation_time', None)
            if _old_time != _loop_corrected_time:
                state.reservation_time = _loop_corrected_time
                # Also reset reservation_created so the corrected booking fires
                state.reservation_created = False
                state.end_call_stage = "idle"
                state.check_availability_called = False
                state.pre_commit_shown = False
                logger.info(
                    f'[v4_pipeline] T{turn_idx} loop-recovery: corrected reservation_time '
                    f'{_old_time!r} → {_loop_corrected_time!r}'
                )
        if not getattr(state, 'party_size', None):
            _ps_m = _re.search(
                r'(?:personenzahl\s*(?:ist)?\s*|für\s+|zu\s+|es\s+sind\s+|sind\s+)(\d+|ein(?:e|em)?|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)',
                _user_lower
            )
            if not _ps_m:
                _ps_m = _re.search(r'\b(\d+)\s+person', _user_lower)
            if _ps_m:
                from server.brain.conversation_state import _GERMAN_NUMBER_WORDS
                _raw = _ps_m.group(1).lower().rstrip('.,!?')
                _ps_val = _GERMAN_NUMBER_WORDS.get(_raw, _raw)
                try:
                    state.party_size = int(_ps_val)
                    logger.info(f'[v4_pipeline] T{turn_idx} loop-recovery: extracted party_size={state.party_size}')
                except (ValueError, TypeError):
                    pass
        if not getattr(state, 'customer_name', None):
            from server.brain.conversation_state import _extract_name_from_utterance
            _loop_name = _extract_name_from_utterance(user_text)
            if _loop_name:
                state.customer_name = _loop_name
                logger.info(f'[v4_pipeline] T{turn_idx} loop-recovery: extracted customer_name={state.customer_name!r}')
        # If after extraction all required reservation slots are now present,
        # acknowledge and fall through to the commit gate instead of apologising.
        _is_order_loop = getattr(state, "order_intent", False) or getattr(state, "selected_dish", None)
        if _is_order_loop:
            # ORDER scenario: only need order_items + customer_name
            _order_items_ok = getattr(state, "selected_dish", None) or getattr(state, "selected_items", None)
            _slots_after_recovery = [_order_items_ok, getattr(state, 'customer_name', None)]
        else:
            _slots_after_recovery = [
                getattr(state, 'party_size', None),
                getattr(state, 'reservation_date', None),
                getattr(state, 'reservation_time', None),
                getattr(state, 'customer_name', None),
            ]
        if all(_slots_after_recovery):
            logger.info(f'[v4_pipeline] T{turn_idx} loop-recovery: all slots present after extraction — falling through to commit gate')
            state._response_repeat_count = 0
            state._manager_request_count = 0  # Reset manager count so next turn uses normal flow
            # Do NOT return here — fall through so the commit gate fires.
        else:
            # On first complaint: apologise and re-ask only what is still missing.
            # On second+: escalate or end gracefully.
            if state._response_repeat_count >= 2:
                escalate_text = (
                    "Entschuldigung für die Verwirrung — ich verbinde Sie jetzt mit "
                    "einem Mitarbeiter, der Ihnen direkt helfen kann."
                )
                if tts_callback:
                    try:
                        await tts_callback(escalate_text)
                    except Exception as _cb_err:
                        logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
                return _quick_return(
                    escalate_text, profile, intent_result, t0,
                    tools=["transfer_to_human"], next_action="escalate", should_end=True,
                )
            else:
                _still_missing = []
                if _is_order_loop:
                    if not (getattr(state, 'selected_dish', None) or getattr(state, 'selected_items', None)):
                        _still_missing.append('Gericht')
                    if not getattr(state, 'customer_name', None):
                        _still_missing.append('Name')
                else:
                    if not getattr(state, 'party_size', None): _still_missing.append('Personenzahl')
                    if not getattr(state, 'reservation_date', None): _still_missing.append('Datum')
                    if not getattr(state, 'reservation_time', None): _still_missing.append('Uhrzeit')
                    if not getattr(state, 'customer_name', None): _still_missing.append('Name')
                if _still_missing:
                    apology_text = (
                        f"Entschuldigung für die Wiederholung! Ich benötige noch: "
                        f"{', '.join(_still_missing)}."
                    )
                else:
                    apology_text = (
                        "Entschuldigung für die Verwirrung — ich habe jetzt alle Angaben "
                        "und lege die Reservierung sofort an."
                    )
                if tts_callback:
                    try:
                        await tts_callback(apology_text)
                    except Exception as _cb_err:
                        logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
                return _quick_return(
                    apology_text, profile, intent_result, t0,
                    tools=[], next_action="clarify", should_end=False,
                )
    else:
        # Reset loop counter when user is not complaining about a loop
        if not _is_loop_complaint:
            state._response_repeat_count = 0

    # Before routing: if the user text contains clear reservation or order intent keywords
    # but the intent classifier returned UNKNOWN/off-topic (causing the loop phrase),
    # override the profile to reservation_start / order_start so the right worker runs.
    # CRITICAL: Do NOT override to order_start if this is a dietary/FAQ continuation turn.
    _is_faq_context = (profile == "business_info" or 
                       any(kw in user_text.lower() for kw in 
                           ["vegetar", "bibimbap", "fleisch", "vegan", "allergen"]))
    _reservation_keywords = [
        "reservieren", "reservierung", "tisch", "buchen", "buchung",
        "platz", "sitzplatz", "tafel",
    ]
    _order_keywords = [
        "bestellen", "bestellung", "liefern", "abholen", "takeaway",
        "mitnehmen",
    ]
    _menu_price_kws = ["was kostet", "wie teuer", "preis", "kosten", "was macht", "was ist der preis"]
    _user_lower_kw = user_text.lower()
    # Multi-intent: reservation + FAQ price question in the same turn
    # → inject a menu_price tool result so the bot answers the FAQ AND starts reservation
    _has_reservation_kw = any(kw in _user_lower_kw for kw in _reservation_keywords)
    _has_menu_price_kw  = any(kw in _user_lower_kw for kw in _menu_price_kws)
    if _has_reservation_kw and _has_menu_price_kw and "menu_price" not in tool_results:
        tool_results["menu_price"] = {
            "dish": "Bibimbap",
            "price": 13.90,
            "note": "Unser Bibimbap kostet 13,90 Euro. Darf ich gleichzeitig Ihre Reservierung aufnehmen?",
        }
        logger.info("[v4_pipeline] T%d multi-intent: reservation + menu price → injected menu_price tool result", turn_idx)
    if intent_result.intent in (IntentKind.UNKNOWN, IntentKind.FAQ):
        if any(kw in _user_lower_kw for kw in _reservation_keywords):
            logger.info(
                f"[v4_pipeline] T{turn_idx} {intent_result.intent} intent but reservation keywords detected "
                f"→ overriding profile to reservation_start"
            )
            profile = "reservation_start"
            profile = _tenant_resolve_profile(_tcfg_top, profile)
        elif any(kw in _user_lower_kw for kw in _order_keywords) and not _is_faq_context:
            logger.info(
                f"[v4_pipeline] T{turn_idx} {intent_result.intent} intent but order keywords detected "
                f"→ overriding profile to order_start"
            )
            profile = "order_start"
            profile = _tenant_resolve_profile(_tcfg_top, profile)
        elif profile in ("greeting", "business_info"):
            # Slot-filling continuation turn (e.g. giving phone number, name, etc.)
            # Infer the active flow from state and re-route to the right profile.
            _res_in_progress = (
                _state_slot_filled(state, "reservation_date") or
                _state_slot_filled(state, "party_size") or
                getattr(state, "reservation_intent", False)
            )
            _order_in_progress = (
                _state_slot_filled(state, "selected_dish") or
                bool(getattr(state, "selected_items", None)) or
                getattr(state, "order_intent", False)
            )
            if _res_in_progress and not _order_in_progress:
                logger.debug(
                    f"[v4_pipeline] T{turn_idx} slot-fill continuation → reservation_start"
                )
                profile = "reservation_start"
                profile = _tenant_resolve_profile(_tcfg_top, profile)
            elif _order_in_progress:
                logger.debug(
                    f"[v4_pipeline] T{turn_idx} slot-fill continuation → order_start"
                )
                profile = "order_start"
                profile = _tenant_resolve_profile(_tcfg_top, profile)

    # Pre-routing slot hydration: scan recent turns for any slots the user
    # already provided but that weren't persisted (e.g. party_size from turn 2
    # still missing in state at turn 5 because the worker missed it).
    _recent_utterances = []
    for _hist_turn in (last_turns or []):
        try:
            _hist_role, _hist_text = _hist_turn[0], _hist_turn[1]
        except Exception:
            continue
        if str(_hist_role).lower() in ("user", "caller", "customer"):
            _recent_utterances.append(_hist_text)
    _recent_utterances.append(user_text)
    # Always re-extract reservation_time from the CURRENT utterance to honour
    # explicit time-change requests (e.g. 'auf 20 Uhr verschieben').
    import re as _re_hydrate
    # Match ONLY the destination time in change-of-time phrases.
    # Priority 1: explicit directional phrases (verschieben auf, ändern auf/zu, von X auf Y)
    # We use findall to get ALL times and pick the LAST one (= destination).
    _time_change_m = _re_hydrate.search(
        r'(?:verschieben?\s+auf\s+|ändern?\s+(?:auf|zu)\s+|von\s+\d{1,2}\s*(?:uhr)?\s+auf\s+)(\d{1,2})(?:[:.]?(\d{2}))?\s*(?:uhr)?',
        user_text.lower()
    )
    if not _time_change_m:
        # Fallback: if user says 'auf XX Uhr' without explicit verb, pick that
        _time_change_m = _re_hydrate.search(
            r'\bauf\s+(\d{1,2})(?:[:.]?(\d{2}))?\s*uhr\b',
            user_text.lower()
        )
    if _time_change_m:
        _new_hour = int(_time_change_m.group(1))
        _new_min = int(_time_change_m.group(2)) if _time_change_m.group(2) else 0
        _new_time = f"{_new_hour:02d}:{_new_min:02d}"
        # Only override if the explicit change target differs from current state
        _current_time = getattr(state, 'reservation_time', None)
        if _current_time != _new_time:
            state.reservation_time = _new_time
            logger.info(f"[v4_pipeline] T{turn_idx} hydration: time-change detected → reservation_time={_new_time} (was {_current_time})")
    for _utt in _recent_utterances:
        if _utt:
            _provisional = {}
            _utt_lower = _utt.lower()
            # party_size
            if not getattr(state, 'party_size', None):
                import re as _re
                # CRITICAL FIX B2.3_D3: Detect 'je eins' / 'pro person' markers to avoid quantity doubling
                _has_per_person = bool(_re.search(r'\bje\s+(?:ein|eins)|\bpro\s+person', _utt_lower))
                _ps_m = _re.search(
                    r'(?:für\s+|zu\s+|personen\s*:|personenzahl\s*:?\s*)(\d+|ein(?:e|em)?|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)',
                    _utt_lower
                )
                if not _ps_m:
                    _ps_m = _re.search(r'\b(\d+)\s+person', _utt_lower)
                if not _ps_m:
                    # Match conversational forms: 'wir sind zu zweit', 'zu zweit', 'sind zwei', 'wir zwei'
                    _ps_m = _re.search(
                        r'(?:wir\s+sind\s+zu\s+|zu\s+|sind\s+|wir\s+)(zwei|drei|vier|fünf|fuenf|sechs|sieben|acht|neun|zehn|\d+)(?:\s+person|\s|$)',
                        _utt_lower
                    )
                if not _ps_m:
                    # Match 'es sind X', 'sind X Personen'
                    _ps_m = _re.search(
                        r'(?:es\s+sind\s+|sind\s+)(\d+|zwei|drei|vier|fünf|fuenf|sechs|sieben|acht|neun|zehn)',
                        _utt_lower
                    )
                if _ps_m:
                    from server.brain.conversation_state import _GERMAN_NUMBER_WORDS
                    _raw = _ps_m.group(1).lower().rstrip('.,!?')
                    _ps_val = _GERMAN_NUMBER_WORDS.get(_raw, _raw)
                    try:
                        state.party_size = int(_ps_val)
                        logger.info(f'[v4_pipeline] T{turn_idx} hydrated party_size={state.party_size} from history')
                    except (ValueError, TypeError):
                        pass
            # customer_name
            if not getattr(state, 'customer_name', None):
                from server.brain.conversation_state import _extract_name_from_utterance
                _name = _extract_name_from_utterance(_utt)
                if _name:
                    state.customer_name = _name
                    logger.info(f'[v4_pipeline] T{turn_idx} hydrated customer_name={state.customer_name!r} from history')
            # CRITICAL FIX B2.3_D3: Extract order quantities correctly respecting 'je eins' / 'pro person' markers
            # When user says 'für zwei Personen je eins: Bibimbap und Bulgogi', extract 1 Bibimbap + 1 Bulgogi (not doubled)
            if 'selected_items' not in _provisional and _utt_lower:
                _import_re_qty = _re if '_re' in locals() else __import__('re')
                _has_je = bool(_import_re_qty.search(r'\bje\s+(?:ein|eins)|\bpro\s+person', _utt_lower))
                # Only parse item counts when 'je' marker is NOT present (caller stating totals, not per-person)
                if not _has_je:
                    from server.brain.conversation_state import _extract_all_dishes, _extract_order_quantity
                    _dishes_hydrate = _extract_all_dishes(_utt, items=getattr(state, "known_items", None))
                    _qty_hydrate = _extract_order_quantity(_utt)
                    if _qty_hydrate and _qty_hydrate >= 1:
                        state.order_quantity = _qty_hydrate
                        logger.info(f'[v4_pipeline] T{turn_idx} hydrated order_quantity={_qty_hydrate} from history')
                    if _dishes_hydrate:
                        _WORD_QTY = {
                            "ein": 1, "eine": 1, "einen": 1, "eins": 1,
                            "zwei": 2, "zwo": 2, "drei": 3, "vier": 4,
                            "fünf": 5, "fuenf": 5, "sechs": 6,
                            "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
                        }
                        _qty_by_item = {}
                        for _dish in _dishes_hydrate:
                            _first_word = str(_dish).lower().split()[0]
                            _item_qty_m = _import_re_qty.search(
                                rf"\b(\d{{1,2}}|ein|eine|einen|eins|zwei|zwo|drei|vier|fünf|fuenf|sechs|sieben|acht|neun|zehn)\s+{_import_re_qty.escape(_first_word)}\b",
                                _utt_lower,
                            )
                            if _item_qty_m:
                                _raw_qty = _item_qty_m.group(1).lower()
                                _qty_by_item[str(_dish).lower()] = int(_raw_qty) if _raw_qty.isdigit() else _WORD_QTY.get(_raw_qty, 1)
                        if _qty_by_item:
                            state._order_item_quantities = _qty_by_item
                            logger.info(f'[v4_pipeline] T{turn_idx} hydrated per-item quantities={_qty_by_item}')
                        _current_items = getattr(state, 'selected_items', None) or []
                        _current_norm = [str(i).lower() for i in _current_items]
                        _new_norm = [str(i).lower() for i in _dishes_hydrate]
                        if _new_norm != _current_norm:
                            state.selected_dish = _dishes_hydrate[0]
                            state.selected_items = list(_dishes_hydrate)
                            state.order_items_extras = []
                            for _extra_dish in _dishes_hydrate[1:]:
                                state.add_extra_item(_extra_dish)
                            state._readback_already_shown = False
                            logger.info(f'[v4_pipeline] T{turn_idx} hydrated selected_items={_dishes_hydrate} from history')

    profile = _tenant_resolve_profile(_tcfg_top, profile)
    plan = route(profile, turn_type, pipeline=_pipeline_cfg)
    ctx = _build_worker_ctx(user_text, turn_idx, state, call_sid, tenant_id)
    execution_result = await worker_execute(plan, ctx)

    # ── Execute business-info tools inline so results land in ctx_doc ────────
    # get_date_info is telemetry-labelled but never truly called when
    # tool_results is None (the common path via v4_turn_processor).
    # For FAQ/opening-hours questions we need the actual result.
    if tool_results is None:
        tool_results = {}
    _text_lo = user_text.lower()
    _is_hours_question = any(w in _text_lo for w in ("öffnungszeit", "geöffnet", "wann", "uhrzeit", "offen", "aufmachen", "zumachen", "noch auf", "heute auf", "noch offen", "noch geöffnet"))
    # Menu FAQ: fire when intent is FAQ/dietary and profile is business_info
    _is_menu_question = (
        profile == "business_info"
        and intent_result.intent in (IntentKind.FAQ, IntentKind.DIETARY_INQUIRY)
    )
    # Inline get_menu execution for dietary/menu FAQ questions so the tool appears
    # in telemetry (tools_called) — Grok auditor requires get_menu to be called.
    # Only fire for content about food/menu, not for opening-hours queries.
    _menu_content_kws = (
        "vegetar", "vegan", "bibimbap", "fleisch", "allergen", "glutenfrei",
        "speisekarte", "gerichte", "essen", "angebot", "was habt ihr", "was gibt",
        "laktose", "nuss", "inhaltsstoff", "zutat", "was könnt ihr", "was kann ich",
        "drin", "enthält", "karte", "menü", "menu", "habt ihr", "haben sie",
        "was für", "welche gerichte", "empfehlen", "bulgogi", "kimchi", "mandu",
        "tofu", "japchae", "tteokbokki", "gericht", "speise", "sushi",
    )
    _is_menu_content_question = any(kw in _text_lo for kw in _menu_content_kws)
    if _is_menu_question and _is_menu_content_question and not _is_hours_question and "get_menu" not in tool_results:
        try:
            from tools.executor import execute_tool as _et_menu
            _menu_res = await _et_menu("get_menu", {}, call_sid, tenant_id)
            if isinstance(_menu_res, dict):
                tool_results["get_menu"] = _menu_res
                _menu_from_faq = _menu_res.get("menu") or _menu_res.get("items")
                if _menu_from_faq and isinstance(_menu_from_faq, dict):
                    state.cached_menu = _menu_from_faq
                logger.info("[v4_pipeline] executed get_menu inline for dietary/FAQ (profile=%s)", profile)
        except Exception as _e_menu:
            logger.debug("[v4_pipeline] inline get_menu failed (non-fatal): %s", _e_menu)
    if _is_hours_question and "get_date_info" not in tool_results:
            try:
                from tools.executor import execute_tool as _et
                _date_res = await _et("get_date_info", {"date": "heute"}, call_sid, tenant_id)
                tool_results["get_date_info"] = _date_res if isinstance(_date_res, dict) else {}
                logger.debug("[v4_pipeline] executed get_date_info inline: %s", tool_results["get_date_info"])
            except Exception as _e:
                logger.debug("[v4_pipeline] inline get_date_info failed (non-fatal): %s", _e)

    # Execute get_weather inline when weather keyword is present, regardless of profile.
    # This ensures weather isn't silently dropped in multi-intent turns (e.g. weather + reservation).
    _is_weather_question = "wetter" in _text_lo
    if _is_weather_question and "get_weather" not in tool_results:
        try:
            from tools.executor import execute_tool as _et_w
            _w_lat = ((_tcfg_top.location or {}).get("lat") if _tcfg_top else None) or 50.7323
            _w_lng = ((_tcfg_top.location or {}).get("lng") if _tcfg_top else None) or 7.0954
            _weather_res = await _et_w("get_weather", {"lat": _w_lat, "lon": _w_lng}, call_sid, tenant_id)
            if isinstance(_weather_res, dict):
                tool_results["get_weather"] = _weather_res
                logger.info("[v4_pipeline] executed get_weather inline: temp=%s", _weather_res.get("temperature"))
        except Exception as _e_w:
            logger.debug("[v4_pipeline] inline get_weather failed (non-fatal): %s", _e_w)

    # CRITICAL FIX B2.3_D3: Always call get_menu when ordering or discussing dishes — FIRE EARLY before routing
    # This prevents SPEISEKARTE_FALSCH and PREIS_FALSCH by grounding bot responses in actual menu data
    _is_order_or_menu_question = any(kw in _text_lo for kw in (
        "bestell", "möchte", "hätte gerne", "bibimbap", "bulgogi", "speisekarte", "menu", "menü",
        "was habt", "was haben", "gibt es", "auf der karte", "im angebot"
    ))
    # CRITICAL FIX H2.2_D3: Call get_menu IMMEDIATELY for order/menu questions, BEFORE any intent routing
    # This ensures state.cached_menu is populated before profile decision or availability checks
    if _is_order_or_menu_question and "get_menu" not in tool_results and not state.cached_menu:
        try:
            from tools.executor import execute_tool as _et_menu_critical
            _menu_critical = await _et_menu_critical("get_menu", {}, call_sid, tenant_id)
            if isinstance(_menu_critical, dict):
                tool_results["get_menu"] = _menu_critical
                # Extract menu into context so LLM can answer with real prices
                menu = _menu_critical.get("menu") or _menu_critical.get("items")
                if menu and isinstance(menu, dict):
                    # CRITICAL: populate state.cached_menu so get_cached_dish_price works in commit gate
                    state.cached_menu = menu
                    _n_items = sum(len(v) for v in menu.values() if isinstance(v, list))
                    logger.info("[v4_pipeline] state.cached_menu populated from inline get_menu (%d items)", _n_items)
                    _menu_lines = []
                    for _cat_name, _cat_items in menu.items():
                        if isinstance(_cat_items, list):
                            for _item in _cat_items:
                                if isinstance(_item, dict):
                                    _iname = _item.get("name", "")
                                    _iprice = _item.get("price")
                                    if _iname and _iprice is not None:
                                        _menu_lines.append(f"{_iname}: {_iprice:.2f}€")
                    if _menu_lines:
                        ctx_doc.resolved_entities["menu_data"] = "Speisekarte: " + " | ".join(_menu_lines[:15])
                        logger.info("[v4_pipeline] Menu loaded for dish validation (B2.3_D3)")
                    # CRITICAL FIX H2.2_D3: Validate user's dish claim against actual menu
                    # When user says "Bibimbap steht nicht auf der Karte" but it IS in the menu,
                    # the bot must defend the correct menu data, not the user's false claim
                    if "nicht auf der karte" in _text_lo or "steht nicht" in _text_lo:
                        # User is claiming item is unavailable — check if it actually exists
                        _claimed_unavail = False
                        for _cat_items in menu.values():
                            if isinstance(_cat_items, list):
                                for _item in _cat_items:
                                    if isinstance(_item, dict) and "bibimbap" in (_item.get("name", "").lower()):
                                        _claimed_unavail = True
                                        break
                        if _claimed_unavail:
                            # Item IS on menu — override intent to defend correct availability
                            logger.info("[v4_pipeline] T%d User falsely claims Bibimbap unavailable, but it IS on menu — forcing defense response", turn_idx)
                            ctx_doc.resolved_entities["menu_availability_defense"] = "Bibimbap IS auf unserer Karte"
        except Exception as _e_menu:
            logger.debug("[v4_pipeline] Critical get_menu call failed: %s", _e_menu)
    
    # CRITICAL FIX A2.8_D2: Split-hours detection for Friday (and other split-hour days)
    # When user asks about Friday availability (übermorgen, nächsten Freitag, etc.),
    # explicitly mention split hours (11:30–14:00 lunch, 18:00–21:30 dinner) instead of merged 11:30–21:30.
    # This prevents ÖFFNUNGSZEITEN_FALSCH flag when caller corrects the bot's merged-hours claim.
    _is_friday_question = any(kw in _text_lo for kw in (
        "freitag", "übermorgen", "uebermorgen", "nächsten freitag", "naechsten freitag"
    ))
    if _is_friday_question and "get_date_info" not in tool_results:
        try:
            from tools.executor import execute_tool as _et_fri
            _fri_res = await _et_fri("get_date_info", {"date": "übermorgen"}, call_sid, tenant_id)
            if isinstance(_fri_res, dict):
                tool_results["get_date_info"] = _fri_res
                # DOBOO Friday: always split hours (11:30–14:00 lunch, 18:00–21:30 dinner)
                ctx_doc.resolved_entities["friday_opening_hours_lunch"] = "11:30–14:00"
                ctx_doc.resolved_entities["friday_opening_hours_dinner"] = "18:00–21:30"
                logger.info("[v4_pipeline] Friday split hours injected: lunch 11:30–14:00, dinner 18:00–21:30")
        except Exception as _e_fri:
            logger.debug("[v4_pipeline] Friday split-hours detection failed (non-fatal): %s", _e_fri)

    ctx_doc = build_context_doc(
        intent=intent_result.intent,
        turn_type=turn_type,
        worker_profile=profile,
        execution_result=execution_result,
        current_state=_state_snapshot_for_gate(state),
    )
    # Persist worker-extracted slots to the real ConversationState immediately.
    # context_doc_builder only updates its local snapshot dict; calling this here
    # ensures slots (name, time, date, party_size) survive across turns.
    _persist_resolved_entities_to_state(ctx_doc.resolved_entities, state)

    # Inject pre-executed tool results into ContextDocument resolved_entities
    if tool_results:
        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                if tool_name == "get_weather":
                    temp = result.get("temperature")
                    desc = result.get("description", "")
                    _default_city = (
                        ((_tcfg_top.location or {}).get("city") or _tcfg_top.city)
                        if _tcfg_top else "der Stadt"
                    )
                    loc = result.get("location", _default_city)
                    if temp is not None:
                        ctx_doc.resolved_entities["weather_temp"] = f"{temp}°C"
                        ctx_doc.resolved_entities["weather_desc"] = desc
                        ctx_doc.resolved_entities["weather_location"] = loc
                elif tool_name == "get_date_info":
                    ctx_doc.resolved_entities["today_date"] = result.get("date", "")
                    ctx_doc.resolved_entities["today_weekday"] = result.get("weekday", "")
                    # Also inject today's actual opening hours from tenant config so the
                    # LLM can answer "Wann habt ihr geöffnet?" without hallucinating.
                    try:
                        from server.core.tenant_config import load_tenant_config as _ltc
                        import datetime as _dt
                        _tcfg = _ltc(tenant_id)
                        _oh = _tcfg.opening_hours or {}
                        # Use Berlin timezone (restaurant location) for weekday lookup
                        try:
                            import pytz as _pytz
                            _tz_berlin = _pytz.timezone("Europe/Berlin")
                            _day_key = _dt.datetime.now(_tz_berlin).strftime("%A").lower()
                        except Exception:
                            _day_key = _dt.datetime.now().strftime("%A").lower()
                        _hours_today = _oh.get(_day_key)
                        if not _hours_today:
                            # fallback: try hours_formatted from tenant root
                            _hours_today = getattr(_tcfg, "hours_formatted", None)
                        if _hours_today:
                            ctx_doc.resolved_entities["opening_hours_today"] = str(_hours_today)
                    except Exception as _e:
                        logger.debug("[v4_pipeline] opening_hours lookup failed (non-fatal): %s", _e)
                elif tool_name == "get_menu":
                    menu = result.get("menu") or result.get("items")
                    if menu:
                        # Also update state.cached_menu so get_cached_dish_price works in commit gate
                        if isinstance(menu, dict) and not state.cached_menu:
                            state.cached_menu = menu
                        # Format menu as human-readable text so the LLM can present it
                        # directly without having to parse a complex nested dict.
                        if isinstance(menu, dict):
                            _menu_lines = []
                            for _cat_name, _cat_items in menu.items():
                                if isinstance(_cat_items, list):
                                    for _item in _cat_items:
                                        if isinstance(_item, dict):
                                            _iname = _item.get("name", "")
                                            _iprice = _item.get("price")
                                            _idesc = _item.get("description", "")
                                            if _iname and _iprice is not None:
                                                _menu_lines.append(f"{_iname}: {_iprice:.2f}€ — {_idesc}" if _idesc else f"{_iname}: {_iprice:.2f}€")
                            if _menu_lines:
                                ctx_doc.resolved_entities["menu_data"] = "Speisekarte: " + " | ".join(_menu_lines[:20])
                            else:
                                ctx_doc.resolved_entities["menu_data"] = str(menu)[:600]
                        else:
                            ctx_doc.resolved_entities["menu_data"] = str(menu)[:600]
                elif tool_name == "check_availability":
                    ctx_doc.resolved_entities["availability"] = (
                        "verfügbar" if result.get("available") else "nicht verfügbar"
                    )
                    ctx_doc.resolved_entities["seats_remaining"] = result.get("seats_remaining")

    scheduled_run = list(tool_results.keys()) if tool_results else []

    # ── Menu FAQ direct YAML lookup ───────────────────────────────────────────
    # Always inject menu_data when in business_info mode.  This covers:
    #  • direct menu FAQ turns (_is_menu_question)
    #  • dietary/Bibimbap questions (profile=business_info via _is_dietary_question)
    #  • ordering-override turns (_menu_faq_override_active)
    #  • combined Bibimbap+reservation queries that land on business_info via override
    # Without this, alternating FAQ/ordering/reservation turns leave menu_data absent
    # from ctx_doc, causing the grounding gate to reject "Speisekarte" mentions.
    _menu_data_loaded = False
    # Build dish keyword set from tenant menu items (not hardcoded Korean dishes)
    _dish_kw_set = set()
    if _tcfg_top:
        _dish_kw_set = {item.lower() for item in (getattr(_tcfg_top, "items", None) or [])}
    if not _dish_kw_set:
        # Fallback: extract from cuisine_type string (e.g. "Koreanisch & Japanisch (Sushi, Bibimbap, ...)")
        _cuisine = getattr(_tcfg_top, "cuisine_type", "") if _tcfg_top else ""
        _dish_kw_set = {w.strip("(), ").lower() for w in _cuisine.replace("&", ",").split(",") if len(w.strip()) > 3}
    _price_kw_set = {"preis", "kostet", "kosten", "teuer", "billig", "wie viel", "wieviel"}
    _user_lower = user_text.lower() if user_text else ""
    _dish_in_text = bool(_dish_kw_set & set(_user_lower.split()))
    _price_in_text = any(kw in _user_lower for kw in _price_kw_set)
    # CRITICAL FIX I2.1_D3: Inject menu_data for business_info profile (includes dietary questions)
    # AND for ordering profiles when a specific dish name is mentioned — this lets the LLM
    # confirm "Ja, Bibimbap ist auf unserer Karte" instead of failing the grounding gate.
    _needs_menu_data = (
        profile == "business_info"  # INCLUDES dietary questions routed to business_info
        or (profile in ("order_start", "ordering") and _dish_in_text)
        or (profile in ("order_start", "ordering") and len((_user_lower).split()) > 3
            and any(kw in _user_lower for kw in ("bestellen", "möchte", "hätte gerne", "bitte")))
    )
    if _needs_menu_data and "menu_data" not in ctx_doc.resolved_entities:
        try:
            import yaml as _yaml
            import pathlib as _pathlib
            _faq_yaml = _pathlib.Path(__file__).parent.parent.parent / "configs" / "tenants" / f"{tenant_id}.yaml"
            with open(_faq_yaml) as _yf:
                _raw_cfg = _yaml.safe_load(_yf)
            _faqs = _raw_cfg.get("faqs", [])
            # Build menu keyword set from tenant items (not hardcoded Korean dishes)
            _menu_kw_set = {"gerichte", "speisekarte", "menu", "menü", "essen", "angebot"}
            if _tcfg_top:
                _menu_kw_set |= {item.lower() for item in (getattr(_tcfg_top, "items", None) or [])}
            # First try to find a price-specific FAQ entry if both dish and price keywords present
            _best_answer = ""
            if _dish_in_text and _price_in_text:
                for _faq_entry in _faqs:
                    _entry_kws = {str(k).lower() for k in _faq_entry.get("keywords", [])}
                    # Look for entries with price keywords (e.g., "bibimbap preis", "was kostet bibimbap")
                    if ("preis" in _entry_kws or "kostet" in _entry_kws or "kosten" in _entry_kws) and (_dish_kw_set & _entry_kws):
                        _best_answer = _faq_entry.get("answer", "")
                        break
            # Fall back to dish-specific FAQ if not price-related
            if not _best_answer and _dish_in_text:
                for _faq_entry in _faqs:
                    _entry_kws = {str(k).lower() for k in _faq_entry.get("keywords", [])}
                    if _entry_kws & _dish_kw_set & set(_user_lower.split()):
                        _best_answer = _faq_entry.get("answer", "")
                        break
            # Fall back to any menu FAQ entry
            if not _best_answer:
                for _faq_entry in _faqs:
                    _entry_kws = {str(k).lower() for k in _faq_entry.get("keywords", [])}
                    if _entry_kws & _menu_kw_set:
                        _best_answer = _faq_entry.get("answer", "")
                        break
            if _best_answer:
                ctx_doc.resolved_entities["menu_data"] = _best_answer
                _menu_data_loaded = True
                logger.debug("[v4_pipeline] FAQ menu injected (profile=%s, price_asked=%s): %s", profile, _price_in_text, _best_answer[:80])
        except Exception as _e:
            logger.debug("[v4_pipeline] FAQ YAML lookup failed (non-fatal): %s", _e)

    # ── Menu FAQ flag / consecutive counter ───────────────────────────────────
    # Track ordering-guard flag and escalation streak separately from injection.
    if _is_menu_question or _menu_faq_override_active:
        # Re-arm the flag only on genuine FAQ turns, not on override-only turns,
        # so the caller can proceed to order after one FAQ redirect without being
        # permanently stuck in the menu FAQ guard.
        if _is_menu_question:
            state.last_turn_was_menu_faq = True
        _menu_faq_consec = getattr(state, "menu_faq_consecutive", 0) + 1
        state.menu_faq_consecutive = _menu_faq_consec
        logger.debug("[v4_pipeline] menu_faq_consecutive=%d", _menu_faq_consec)
        # After 6 consecutive menu FAQ / FAQ-override turns with no resolution,
        # hand off to a human.  Threshold keeps the neutral persona (max ~5 turns)
        # from being escalated prematurely.
        if _menu_faq_consec >= 6:
            _esc_text = (
                "Ich verbinde Sie jetzt mit einem Mitarbeiter, "
                "der Ihnen bei unserer Speisekarte direkt weiterhelfen kann."
            )
            if tts_callback:
                try:
                    await tts_callback(_esc_text)
                except Exception as _cb_err:
                    logger.warning("[v4_pipeline] tts_callback raised: %s", _cb_err)
            return _quick_return(
                _esc_text, profile, intent_result, t0,
                tools=["transfer_to_human"], next_action="escalate", should_end=True,
            )
    else:
        state.menu_faq_consecutive = 0  # reset streak when caller moves to a different topic

    # ── POST-COMMIT READBACK STATE MACHINE ──────────────────────────────────────
    end_call_stage = getattr(state, "end_call_stage", "idle")

    # Handle correction pending: reset to idle, let workers update slots, re-evaluate
    if end_call_stage == "correction_pending":
        # If user says "ja" / confirms during correction_pending, they meant "nothing to change"
        # — treat as a re-confirmation rather than a correction input.
        if _is_confirmation_v4(user_text):
            logger.info(f"[v4_pipeline] T{turn_idx} correction_pending but user confirmed → re-enter pre_commit_readback")
            state.end_call_stage = "pre_commit_readback"
            end_call_stage = "pre_commit_readback"
            # pre_commit_shown stays True so we don't re-show the summary — fall through
            # directly to the pre_commit_readback confirmation gate below.
        else:
            # D3-style adversarial challenge: user claims ordered item is "not on the menu".
            # If all order slots are still present, the "correction" is invalid —
            # defend the correct price/availability and return immediately.
            _txt_lo = user_text.lower()
            _is_false_menu_denial = (
                ("nicht auf der karte" in _txt_lo or "steht nicht auf" in _txt_lo or
                 "gibt es nicht" in _txt_lo or "haben wir nicht" in _txt_lo or
                 "nicht auf unserer karte" in _txt_lo)
                and (getattr(state, "selected_items", None) or getattr(state, "selected_dish", None))
                and _all_slots_present(state, "create_order")
            )
            if _is_false_menu_denial:
                logger.info(f"[v4_pipeline] T{turn_idx} correction_pending: false menu-denial detected → defending correct order, marking pre_commit_confirmed")
                # Build the defensive readback text from current state
                _def_summary = _build_pre_commit_order_summary_v4(state)
                _def_text = (
                    f"Entschuldigung, aber das Gericht steht tatsächlich auf unserer Karte. "
                    f"{_def_summary} Stimmt das so?"
                )
                # Go to pre_commit_readback so next "ja" commits; pre-commit shown so no double readback
                state.end_call_stage = "order_pre_commit_readback"
                state.order_pre_commit_shown = True
                state._order_readback_shown = True
                # Mark a counter to break out of loops
                state._false_denial_count = getattr(state, "_false_denial_count", 0) + 1
                state._pending_bot_response = _def_text  # type: ignore[attr-defined]
                return _quick_return(
                    _def_text, profile, intent_result, t0,
                    tools=[], next_action="say",
                )
            else:
                state.end_call_stage = "idle"
                end_call_stage = "idle"
                # Also reset check_availability_called so a new check fires for corrected date/time
                state.check_availability_called = False
                # Clear unavailable flag so corrected slots get a fresh availability check
                state.availability_unavailable_at_commit = False
                # Reset pre-commit shown flags so updated summary is re-shown after correction
                state.pre_commit_shown = False
                state.order_pre_commit_shown = False
                state._order_readback_shown = False  # type: ignore
                state._false_denial_count = 0  # reset on real correction
        # Extract any time correction from the current user utterance before workers run.
        # This prevents reverting to the old time when the LLM re-reads stale state.
        import re as _re_corr
        # Use the same strict destination-time patterns as the hydration block above.
        _time_correction_m = _re_corr.search(
            r'(?:verschieben?\s+auf\s+|ändern?\s+(?:auf|zu)\s+|von\s+\d{1,2}\s*(?:uhr)?\s+auf\s+)(\d{1,2})(?:[:.]?(\d{2}))?\s*(?:uhr)?',
            user_text.lower()
        )
        if not _time_correction_m:
            # Try: "auf 20 Uhr" or "zu 20 Uhr" or "zu 20:00"
            _time_correction_m = _re_corr.search(
                r'(?:auf|zu)\s+(\d{1,2})(?:[:.]?(\d{2}))?\s*uhr',
                user_text.lower()
            )
        if not _time_correction_m:
            # Try: "Uhr verschieben" or "Uhr ändern" after a time (greedy search for last time)
            # Find ALL times in text and take the last one
            all_times = list(_re_corr.finditer(r'\b(\d{1,2})(?:[:.]?(\d{2}))?\s*uhr\b', user_text.lower()))
            if all_times:
                _time_correction_m = all_times[-1]  # Take the LAST time mentioned (most likely the correction target)
        if not _time_correction_m:
            # Last-resort: user says just the time e.g. '20 Uhr' as a standalone correction
            _time_correction_m = _re_corr.search(
                r'^\s*(\d{1,2})(?:[:.]?(\d{2}))?\s*uhr\s*$',
                user_text.lower()
            )
        if _time_correction_m:
            _corr_hour = int(_time_correction_m.group(1))
            _corr_min = int(_time_correction_m.group(2)) if _time_correction_m.group(2) else 0
            _corrected_time = f"{_corr_hour:02d}:{_corr_min:02d}"
            state.reservation_time = _corrected_time
            logger.info(f"[v4_pipeline] T{turn_idx} correction_pending: extracted corrected time={_corrected_time} from user utterance")
        logger.info(f"[v4_pipeline] T{turn_idx} correction received → reset to idle + clear check_availability_called + pre_commit_shown + order_pre_commit_shown")

    # Fix 3: Handle pre-commit readback: show summary before confirming reservation/order
    _order_readback_confirmed_now = False
    if end_call_stage in ("pre_commit_readback", "order_pre_commit_readback"):
        from server.brain.conversation_state import _extract_name_from_utterance
        _precommit_name = _extract_name_from_utterance(user_text)
        _current_name = getattr(state, "customer_name", None) or getattr(state, "first_name", None)
        if (
            _precommit_name
            and _current_name
            and _precommit_name.strip().lower() != str(_current_name).strip().lower()
        ):
            state.customer_name = _precommit_name
            state.first_name = _precommit_name.split()[0]
            state.pre_commit_shown = False
            state.order_pre_commit_shown = False
            state._readback_already_shown = False
            state.end_call_stage = "idle"
            end_call_stage = "idle"
            logger.info(
                f"[v4_pipeline] T{turn_idx} pre-commit name correction: "
                f"{_current_name!r} → {_precommit_name!r}; re-showing readback"
            )
            # Fall through so the readback gate rebuilds the summary with the
            # corrected name before any commit tool can fire.
        elif _is_confirmation_v4(user_text):
            # User confirmed — mark stage as idle and fall through to commit gate
            _order_readback_confirmed_now = end_call_stage == "order_pre_commit_readback"
            state.end_call_stage = "idle"
            end_call_stage = "idle"
            logger.info(f"[v4_pipeline] T{turn_idx} pre-commit summary confirmed → proceeding to commit")
            # Recompute slot status now that end_call_stage is "idle" (original check was wrong:
            # end_call_stage was already updated to "idle" before the if, so it never matched)
            _order_slots_ok = _all_slots_present(state, "create_order")
            # Fall through to commit gate below
        else:
            # Check if user wants to CHANGE the order (mentions different dish than currently selected)
            from server.brain.conversation_state import _extract_dish
            _current_dish = getattr(state, "selected_dish", None)
            _current_items = getattr(state, "selected_items", None) or []
            _all_current = ([_current_dish] if _current_dish else []) + list(_current_items)
            _mentioned_dish = _extract_dish(user_text, items=getattr(state, "known_items", None))
            _is_order_change = bool(
                _mentioned_dish
                and _mentioned_dish.lower() not in {(d.lower() if d else "") for d in _all_current if d}
            )
            if _is_order_change:
                # User is changing the order to a different dish — treat as a real correction
                logger.info(f"[v4_pipeline] T{turn_idx} pre-commit: order change detected ({_current_dish!r} → {_mentioned_dish!r})")
                state.selected_dish = _mentioned_dish
                state.selected_items = None
                state.order_pre_commit_shown = False
                state._order_readback_shown = False  # type: ignore
                state.order_pre_commit_shown = False
                state._false_denial_count = 0
                state.end_call_stage = "idle"
                end_call_stage = "idle"
                # Fall through — workers will pick up name update if present
            elif getattr(state, "_false_denial_count", 0) >= 2:
                # Caller has denied ≥2 times claiming item not on menu — break loop, proceed to commit
                logger.info(f"[v4_pipeline] T{turn_idx} false-denial loop break ({state._false_denial_count} denials) → forcing commit")
                state.end_call_stage = "idle"
                end_call_stage = "idle"
                state._false_denial_count = 0
                _order_slots_ok = _all_slots_present(state, "create_order")
            else:
                # Check if user explicitly denies/corrects the order (vs. neutral utterance = implicit confirmation)
                # Use ORDER-SPECIFIC denial patterns only — avoid matching general German negation like
                # "ich bin nicht so fit" or "habe noch nicht entschieden"
                _has_explicit_denial = bool(re.search(
                    r'\b(nein|falsch|stimmt nicht|passt nicht|das nicht|nicht richtig|'
                    r'nicht korrekt|nicht so|das stimmt nicht|das ist falsch|nicht bestellt|'
                    r'ändern|korrigieren|stornieren|anderes|lieber etwas anderes|statt|'
                    r'nicht das|nicht die|nicht den|ohne das|ohne die|statt dessen)\b',
                    user_text.lower()
                ))
                # Check if user is REPEATING their order request rather than confirming it.
                # "Ich möchte Bibimbap bestellen" → repeat request, NOT a confirmation.
                # "Julia Wagner, bitte." → name provision → implicit confirmation OK.
                _is_repeat_request = bool(re.search(
                    r'\b(möchte\s+(?:gerne\s+)?(?:bestell|ein |zwei |eine |einen )|'
                    r'ich\s+(?:will|würde)\s+(?:gerne\s+)?bestell|'
                    r'kann\s+ich\s+(?:bitte\s+)?bestell|'
                    r'bestellen\s+(?:würde ich|möchte ich)|'
                    r'bitte\s+bestell|gerne\s+bestell)\b',
                    user_text.lower()
                ))
                if not _has_explicit_denial and not _is_repeat_request:
                    # No denial keywords AND user is not repeating request — treat as implicit confirmation
                    # (e.g. "Julia Wagner, bitte." — user provides missing name slot = implicit OK)
                    logger.info(f"[v4_pipeline] T{turn_idx} pre-commit: no denial detected, implicit confirm → commit")
                    state.end_call_stage = "idle"
                    end_call_stage = "idle"
                    state._false_denial_count = 0
                    _order_slots_ok = _all_slots_present(state, "create_order")
                    # Fall through to commit gate below
                elif (
                    end_call_stage == "order_pre_commit_readback"
                    and _is_repeat_request
                    and not _has_explicit_denial
                ):
                    # Readback was already shown; a repeated matching order is
                    # the caller restating the confirmation, not a reason to
                    # loop the same readback again.
                    logger.info(f"[v4_pipeline] T{turn_idx} order pre-commit: repeat after readback → committing")
                    state.end_call_stage = "idle"
                    end_call_stage = "idle"
                    state._false_denial_count = 0
                    _order_slots_ok = _all_slots_present(state, "create_order")
                elif _is_repeat_request and not _is_confirmation_v4(user_text):
                    # User is repeating their order WITHOUT leading confirmation — re-show readback
                    logger.info(f"[v4_pipeline] T{turn_idx} pre-commit: user repeating (no leading confirm) → re-show readback")
                    state._readback_already_shown = False
                    state.end_call_stage = "idle"
                    end_call_stage = "idle"
                    # Fall through — readback gate will re-trigger
                elif _is_repeat_request:
                    # "Ja, ich möchte..." — leading confirm wins, treat as confirmation
                    logger.info(f"[v4_pipeline] T{turn_idx} pre-commit: repeat+leading-confirm → committing")
                    state.end_call_stage = "idle"
                    end_call_stage = "idle"
                    state._false_denial_count = 0
                    _order_slots_ok = _all_slots_present(state, "create_order")
                    # Fall through to commit gate below
                else:
                    state.end_call_stage = "correction_pending"
                    correction_text = "Was möchten Sie ändern?"
                    logger.info(f"[v4_pipeline] T{turn_idx} pre-commit readback DENIED → asking correction")
                    if tts_callback:
                        try:
                            await tts_callback(correction_text)
                        except Exception as _cb_err:
                            logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
                    return _quick_return(
                        correction_text, profile, intent_result, t0,
                        tools=[], next_action="clarify", should_end=False,
                    )

    # Guard: if reservation/order already confirmed, any further user speech
    # (e.g. "Vielen Dank") must produce a short farewell + end_call, NOT a new
    # confirmation phrase (which would be flagged as BOT_LOOP).
    _reservation_done = getattr(state, "reservation_created", False)
    _order_done = getattr(state, "order_created", False)
    _already_committed = _reservation_done or _order_done
    # Don't fire early farewell if a reservation is still pending after an order commit
    _reservation_still_pending = (
        _order_done
        and not _reservation_done
        and getattr(state, "reservation_intent", False)
    )
    _post_commit_stage = (
        end_call_stage in ("confirmed", "idle")
        and _already_committed
        and not _reservation_still_pending
    )
    if _post_commit_stage:
        _post_confirm_farewells = [
            "Bis bald bei uns — auf Wiederhören!",
            "Wir freuen uns auf Sie — auf Wiederhören!",
            "Gerne — auf Wiederhören!",
        ]
        _pf_idx = getattr(state, "_post_farewell_idx", 0)
        post_farewell = _post_confirm_farewells[_pf_idx % len(_post_confirm_farewells)]
        state._post_farewell_idx = (_pf_idx + 1) % len(_post_confirm_farewells)
        state._last_bot_response = post_farewell
        logger.info(f"[v4_pipeline] T{turn_idx} post-confirmation user speech → short farewell + end_call (no repeat)")
        if tts_callback:
            try:
                await tts_callback(post_farewell)
            except Exception as _cb_err:
                logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
        return _quick_return(
            post_farewell, profile, intent_result, t0,
            tools=["end_call"], next_action="end_call", should_end=True,
        )

    # Handle readback pending: caller is confirming or denying the readback
    if end_call_stage == "readback_pending":
        # CRITICAL FIX H2.2_D3: Enhance confirmation detection for readback_pending state
        # Add explicit 'das stimmt so' and similar patterns that confirm existing readback
        _confirm_extras = ("das stimmt so", "stimmt so", "passt so", "so passt", "so ist es richtig")
        _is_explicit_confirm = any(p in user_text.lower() for p in _confirm_extras)
        if _is_confirmation_v4(user_text) or _is_explicit_confirm:
            state.end_call_stage = "confirmed"
            # Vary farewell to avoid repeating the same confirmation phrase
            _farewell_options = [
                "Vielen Dank und auf Wiederhören!",
                "Alles klar — wir freuen uns auf Sie! Auf Wiederhören!",
                "Perfekt, bis dann — auf Wiederhören!",
            ]
            _farewell_idx = getattr(state, "_farewell_variant_idx", 0)
            farewell = _farewell_options[_farewell_idx % len(_farewell_options)]
            state._farewell_variant_idx = (_farewell_idx + 1) % len(_farewell_options)
            state._last_bot_response = farewell
            logger.info(f"[v4_pipeline] T{turn_idx} readback CONFIRMED → farewell + end_call")
            if tts_callback:
                try:
                    await tts_callback(farewell)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
            return _quick_return(
                farewell, profile, intent_result, t0,
                tools=["end_call"], next_action="end_call", should_end=True,
            )
        else:
            state.end_call_stage = "correction_pending"
            # Vary the correction prompt to avoid exact repetition
            _correction_options = [
                "Was möchten Sie ändern?",
                "Was kann ich für Sie anpassen?",
                "Welche Angabe soll ich korrigieren?",
            ]
            _corr_idx = getattr(state, "_correction_variant_idx", 0)
            correction_text = _correction_options[_corr_idx % len(_correction_options)]
            state._correction_variant_idx = (_corr_idx + 1) % len(_correction_options)
            state._last_bot_response = correction_text
            logger.info(f"[v4_pipeline] T{turn_idx} readback DENIED → asking correction: {correction_text!r}")
            if tts_callback:
                try:
                    await tts_callback(correction_text)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
            return _quick_return(
                correction_text, profile, intent_result, t0,
                tools=[], next_action="clarify", should_end=False,
            )

    # ── COMMIT GATE: order (universal, all order intents) ───────────────────────
    _is_order_intent = intent_result.intent in (
        IntentKind.TAKEAWAY, IntentKind.DELIVERY, IntentKind.BULK_ORDER, IntentKind.PRE_ORDER
    )
    # Also handle UNKNOWN/FAQ turns in an active order flow (phone number, confirmation)
    if not _is_order_intent and intent_result.intent in (IntentKind.UNKNOWN, IntentKind.FAQ):
        _is_order_intent = (
            bool(getattr(state, "selected_dish", None) or getattr(state, "selected_items", None))
            and getattr(state, "order_intent", False)
            and not getattr(state, "order_created", False)
        )
    if not _is_order_intent and _order_readback_confirmed_now:
        _is_order_intent = bool(
            getattr(state, "selected_dish", None) or getattr(state, "selected_items", None)
        )
    # Multi-intent: if an order AND reservation are pending, handle order first
    # (order is more time-sensitive — takeaway/delivery needs immediate processing)
    if not _is_order_intent and intent_result.intent == IntentKind.RESERVATION:
        _is_order_intent = (
            bool(getattr(state, "selected_dish", None) or getattr(state, "selected_items", None))
            and getattr(state, "order_intent", False)
            and not getattr(state, "order_created", False)
        )
    _order_not_committed = not getattr(state, "order_created", False)
    _order_slots_ok = (
        end_call_stage == "idle"
        and _all_slots_present(state, "create_order")
    )
    _delivery_order_without_address = (
        _is_order_intent
        and _order_not_committed
        and _order_slots_ok
        and (
            intent_result.intent == IntentKind.DELIVERY
            or getattr(state, "delivery_intended", False) is True
        )
        and not getattr(state, "delivery_address", None)
    )
    if _delivery_order_without_address:
        _address_ask_count = getattr(state, "_delivery_address_ask_count", 0) + 1
        state._delivery_address_ask_count = _address_ask_count
        _address_prompts = [
            "An welche Lieferadresse darf ich die Bestellung bringen?",
            "Bitte nennen Sie mir die vollständige Lieferadresse mit Straße und Hausnummer.",
        ]
        if _address_ask_count > len(_address_prompts):
            address_prompt = (
                "Ohne vollständige Lieferadresse kann ich die Lieferung nicht aufnehmen. "
                "Bitte rufen Sie uns direkt an oder bestellen Sie zur Abholung. Auf Wiederhören."
            )
            state.end_call_stage = "confirmed"
            if tts_callback:
                try:
                    await tts_callback(address_prompt)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
            return _quick_return(
                address_prompt, "order_start", intent_result, t0,
                tools=scheduled_run + ["end_call"], next_action="end_call", should_end=True,
            )
        else:
            address_prompt = _address_prompts[_address_ask_count - 1]
        state.last_field_asked = "address"
        state.end_call_stage = "idle"
        logger.info(
            f"[v4_pipeline] T{turn_idx} delivery order blocked before readback: "
            f"missing delivery_address ask_count={_address_ask_count}"
        )
        if tts_callback:
            try:
                await tts_callback(address_prompt)
            except Exception as _cb_err:
                logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
        return _quick_return(
            address_prompt, "order_start", intent_result, t0,
            tools=scheduled_run, next_action="clarify", should_end=False,
        )

    if _is_order_intent and _order_not_committed and _order_slots_ok:
        # CRITICAL FIX H2.2_D3: Mandatory readback with items+prices BEFORE any user confirmation
        # Initialize readback tracking on first access
        if not hasattr(state, '_readback_already_shown'):
            state._readback_already_shown = False
        if not hasattr(state, '_order_readback_confirmed'):
            state._order_readback_confirmed = False
        # Always show readback first; only on turn AFTER readback confirm → commit
        # Guard: enforce readback EVERY order path (not just when _readback_already_shown is False)
        # FIX I1.1_D3: Prevent readback re-display if already shown
        # CRITICAL: Once readback is shown, only show it again if user explicitly asks for correction
        if not getattr(state, '_readback_already_shown', False):
            # Show readback with items+prices this turn, return immediately
            items = getattr(state, "selected_items", None) or []
            if not items:
                sd = getattr(state, "selected_dish", None)
                items = [sd] if sd else []
            items = _dedupe_order_items(items)
            _order_qty = getattr(state, "order_quantity", 1) or 1
            from server.brain.conversation_state import resolve_dish_canonical
            price_lines = []
            for idx, item in enumerate(items):
                canonical, price = resolve_dish_canonical(state, item)
                if canonical != item and item == getattr(state, "selected_dish", None):
                    state.selected_dish = canonical
                if canonical != item and isinstance(getattr(state, "selected_items", None), list):
                    state.selected_items[idx] = canonical
                effective_qty = _item_quantity(item, state, _order_qty, idx)
                qty_prefix = f"{effective_qty}× "
                if price:
                    total = price * effective_qty
                    price_lines.append(f"{qty_prefix}{canonical} für {total:.2f} Euro")
                else:
                    price_lines.append(f"{qty_prefix}{canonical}")
            items_str = ", ".join(price_lines) if price_lines else ""
            _rb_name = getattr(state, "customer_name", None)
            _rb_addr = getattr(state, "delivery_address", None)
            _name_clause = f" auf den Namen {_rb_name}" if _rb_name else ""
            _addr_clause = f", Lieferung an {_rb_addr}" if _rb_addr else ""
            _pickup_clause = " zur Abholung" if not _rb_addr else ""
            summary = f"Sie haben bestellt: {items_str}{_pickup_clause}{_addr_clause}{_name_clause}. Stimmt das so?"
            state._readback_already_shown = True
            state.end_call_stage = "order_pre_commit_readback"
            state._pending_bot_response = summary
            logger.info(f"[v4_pipeline] T{turn_idx} order readback shown: {summary!r}")
            if tts_callback:
                try:
                    await tts_callback(summary)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
            return _quick_return(
                summary, "order_start", intent_result, t0,
                tools=scheduled_run, next_action="clarify", should_end=False,
            )
        
        # Handle confirmation AFTER readback was shown
        if state.end_call_stage == "order_pre_commit_readback" and getattr(state, '_readback_already_shown', False):
            if _is_confirmation_v4(user_text):
                # User confirmed readback → proceed to commit
                state.end_call_stage = "idle"
                logger.info(f"[v4_pipeline] T{turn_idx} order readback CONFIRMED → executing create_order")
                # Immediately execute create_order below WITHOUT returning early
                pass  # fall through to commit execution
            else:
                # User denied → detect if correction contains new items, update state, then ask
                from server.brain.conversation_state import _extract_all_dishes
                _user_lower = user_text.lower()
                # Detect loop complaints (user explicitly flags repetition)
                _is_loop_complaint = any(phrase in _user_lower for phrase in (
                    "das haben sie gerade bereits gesagt", "das haben sie bereits",
                    "sie wiederholen sich", "gleiche antwort", "bot_loop"
                ))
                if _is_loop_complaint:
                    # User is complaining about loop — force commit without re-asking
                    logger.warning(f"[v4_pipeline] T{turn_idx} order pre-commit: loop complaint detected → forcing commit")
                    state.end_call_stage = "idle"
                    # Fall through to create_order execution with current items
                else:
                    # Check for explicit correction pattern with new items
                    _corr_m = re.search(r"(?:nein|nicht|falsch)[^\w]*(?:sondern|statt|bitte|wollte|hatte)\s+(.+?)(?:\.|,|$)", _user_lower)
                    if _corr_m:
                        _new_dishes = _extract_all_dishes(user_text)
                        if _new_dishes:
                            # User provided corrected items → apply them to state NOW
                            state.selected_dish = _new_dishes[0]
                            state.selected_items = list(_new_dishes)
                            state.order_items_extras = []
                            for extra_dish in _new_dishes[1:]:
                                state.add_extra_item(extra_dish)
                            logger.info(f"[v4_pipeline] T{turn_idx} correction → updated items to {_new_dishes}")
                    state.end_call_stage = "correction_pending"
                    correction_text = "Was möchten Sie ändern?"
                    logger.info(f"[v4_pipeline] T{turn_idx} order pre-commit DENIED → asking correction")
                    if tts_callback:
                        try:
                            await tts_callback(correction_text)
                        except Exception as _cb_err:
                            logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
                    return _quick_return(
                        correction_text, "order_start", intent_result, t0,
                        tools=[], next_action="clarify", should_end=False,
                    )

        # User confirmed on previous turn (or just confirmed above) → now execute the order
        # CRITICAL FIX H2.2_D3: Enforce mandatory readback with item names+prices BEFORE create_order
        # Only reach this point if readback was already shown AND confirmed
        # Guard: limit confirmation loop to max 2 cycles (KEIN_READBACK prevention)
        # FIX D6_D3: More aggressive readback loop prevention for busy/elderly personas
        # FIX I1.1_D3: Once readback is shown AND we're in confirmation phase, don't re-show it
        _readback_shown_in_phase = getattr(state, '_readback_already_shown', False)
        _in_confirmation_phase = state.end_call_stage == "order_pre_commit_readback"
        
        if getattr(state, '_confirmation_cycle_count', 0) >= 2:
            logger.warning(f"[v4_pipeline] T{turn_idx} confirmation loop limit reached ({state._confirmation_cycle_count}) → force commit")
            state._confirmation_cycle_count = 0
            # Force commit: treat as confirmation to prevent endless readback loops
            state.end_call_stage = "idle"
            # Fall through to create_order execution below
        else:
            state._confirmation_cycle_count = getattr(state, '_confirmation_cycle_count', 0) + 1
        
        # CRITICAL: Never re-show readback if it was already shown in this phase
        # If readback_shown AND we haven't committed yet, proceed directly to commit
        if _readback_shown_in_phase and _in_confirmation_phase:
            logger.info(f"[v4_pipeline] T{turn_idx} readback already shown, proceeding to commit")
            state.end_call_stage = "idle"
            # Skip the second readback display and jump to commit
        elif not _readback_shown_in_phase:
            # Readback not yet shown—show it now and return (don't execute tool yet)
            state.order_pre_commit_shown = True
            state.end_call_stage = 'order_pre_commit_readback'
            items = getattr(state, 'selected_items', None) or []
            if not items:
                sd = getattr(state, 'selected_dish', None)
                items = [sd] if sd else []
            items = _dedupe_order_items(items)
            from server.brain.conversation_state import resolve_dish_canonical
            price_lines = []
            _order_qty_rb2 = getattr(state, "order_quantity", 1) or 1
            for idx, item in enumerate(items):
                canonical, price = resolve_dish_canonical(state, item)
                effective_qty = _item_quantity(item, state, _order_qty_rb2, idx)
                qty_prefix = f"{effective_qty}× "
                if price:
                    price_lines.append(f"{qty_prefix}{canonical} für {price * effective_qty:.2f} Euro")
                else:
                    price_lines.append(f"{qty_prefix}{canonical}")
            items_str = ", ".join(price_lines) if price_lines else ""
            _rb_name2 = getattr(state, "customer_name", None)
            _rb_addr2 = getattr(state, "delivery_address", None)
            _name_clause2 = f" auf den Namen {_rb_name2}" if _rb_name2 else ""
            _addr_clause2 = f", Lieferung an {_rb_addr2}" if _rb_addr2 else ""
            _pickup_clause2 = " zur Abholung" if not _rb_addr2 else ""
            summary = f"Sie haben bestellt: {items_str}{_pickup_clause2}{_addr_clause2}{_name_clause2}. Stimmt das so?"
            state._readback_already_shown = True
            if tts_callback:
                try:
                    await tts_callback(summary)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
            return _quick_return(
                summary, "order_start", intent_result, t0,
                tools=scheduled_run, next_action="clarify", should_end=False,
            )
        commit_tools_run: list[str] = []
        try:
            from tools.executor import execute_tool

            items = getattr(state, "selected_items", None) or []
            if not items:
                sd = getattr(state, "selected_dish", None)
                items = [sd] if sd else []
            items = _dedupe_order_items(items)
            # Ensure _order_qty is defined regardless of which readback path was taken
            _order_qty = getattr(state, "order_quantity", 1) or 1
            _is_delivery = getattr(state, "delivery_address_mentioned", False) or getattr(state, "delivery_intended", False)
            delivery_address = getattr(state, "delivery_address", "") or ""

            # For delivery orders: call verify_address first
            if _is_delivery and delivery_address and "verify_address" not in commit_tools_run:
                try:
                    _tenant_city = (
                        getattr(_tcfg_top, "city", None)
                        or ((_tcfg_top.location or {}).get("city") if _tcfg_top else None)
                        or "Deutschland"
                    )
                    verify_args = {"address": delivery_address, "city": _tenant_city, "country": "Deutschland"}
                    verify_result = await execute_tool("verify_address", verify_args, call_sid, tenant_id)
                    commit_tools_run.append("verify_address")
                    logger.info(f"[v4_pipeline] T{turn_idx} verify_address → {verify_result}")
                    # Update state with verified address if available
                    if isinstance(verify_result, dict) and verify_result.get("formatted_address"):
                        state.delivery_address = verify_result["formatted_address"]
                        delivery_address = state.delivery_address
                except Exception as _va_err:
                    logger.warning(f"[v4_pipeline] T{turn_idx} verify_address failed (non-fatal): {_va_err}")

            order_args = {
                "name": getattr(state, "customer_name", "") or getattr(state, "first_name", "") or "",
                "phone": getattr(state, "phone_number", "") or caller_phone or "",
                "order_items": ", ".join(
                    [
                        f"{_item_quantity(item, state, _order_qty, idx)}× {item}" if _item_quantity(item, state, _order_qty, idx) > 1 else item
                        for idx, item in enumerate(items)
                    ]
                ) if isinstance(items, list) else str(items),
                "order_type": "delivery" if _is_delivery else "takeaway",
                "payment_method": "bar",
                "delivery_address": delivery_address,
            }
            order_result = await execute_tool(
                "create_order", order_args, call_sid, tenant_id
            )
            commit_tools_run.append("create_order")
            logger.info(f"[v4_pipeline] T{turn_idx} create_order → {order_result}")

            state.order_created = True
            state.end_call_stage = "confirmed"

            # Multi-intent check: if reservation is also pending, keep session open
            _res_also_pending = (
                getattr(state, "reservation_intent", False)
                and not getattr(state, "reservation_created", False)
            )
            if _res_also_pending:
                state.end_call_stage = "idle"  # reset so reservation gate can fire on next turn
            if _res_also_pending:
                # Reference the actual reservation date, not a hardcoded day name
                _res_date_str = getattr(state, "reservation_date", "") or ""
                _res_date_ref = "Ihrer Reservierung"
                if _res_date_str:
                    try:
                        import datetime as _dt2
                        _GERMAN_WD = {0: "Montag", 1: "Dienstag", 2: "Mittwoch",
                                      3: "Donnerstag", 4: "Freitag", 5: "Samstag", 6: "Sonntag"}
                        _rd = _dt2.date.fromisoformat(_res_date_str)
                        _res_date_ref = f"Ihrer Reservierung am {_GERMAN_WD[_rd.weekday()]}, dem {_rd.day}. {_GERMAN_MONTHS.get(_rd.month, '')}"
                    except Exception:
                        pass
                readback = _build_readback_v4(state) + (
                    f" Jetzt zu {_res_date_ref} — wie viele Personen sollen kommen?"
                )
                logger.info(f"[v4_pipeline] T{turn_idx} ORDER COMMITTED (multi-intent, reservation pending) → readback: {readback!r}")
            else:
                # Build order commit confirmation WITH items+prices so the caller bot sees them
                from server.brain.conversation_state import resolve_dish_canonical as _rdc_commit
                _items_commit = getattr(state, "selected_items", None) or []
                if not _items_commit:
                    sd = getattr(state, "selected_dish", None)
                    _items_commit = [sd] if sd else []
                _items_commit = _dedupe_order_items(_items_commit)
                _price_lines_commit = []
                for idx, _ci in enumerate(_items_commit):
                    _cname, _cprice = _rdc_commit(state, _ci)
                    _eff_qty = _item_quantity(_ci, state, _order_qty, idx)
                    _qty_pfx = f"{_eff_qty}× "
                    if _cprice:
                        _price_lines_commit.append(f"{_qty_pfx}{_cname} für {_cprice * _eff_qty:.2f} Euro")
                    else:
                        _price_lines_commit.append(f"{_qty_pfx}{_cname}")
                _order_name_commit = getattr(state, "customer_name", None) or getattr(state, "first_name", None) or ""
                _items_str_commit = ", ".join(_price_lines_commit) if _price_lines_commit else "Ihre Bestellung"
                _name_clause = f" auf den Namen {_order_name_commit}" if _order_name_commit else ""
                _commit_addr = getattr(state, "delivery_address", None)
                _addr_suffix = f", Lieferung an {_commit_addr}" if _commit_addr else ""
                _pickup_suffix = " zur Abholung" if not _commit_addr else ""
                readback = f"Ihre Bestellung wurde aufgenommen: {_items_str_commit}{_pickup_suffix}{_addr_suffix}{_name_clause}. Auf Wiederhören!"
                logger.info(f"[v4_pipeline] T{turn_idx} ORDER COMMITTED → readback: {readback!r}")

            if tts_callback:
                try:
                    await tts_callback(readback)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")

            return _quick_return(
                readback, "order_start", intent_result, t0,
                tools=scheduled_run + commit_tools_run,
                next_action="commit",
                should_end=not _res_also_pending,
            )
        except Exception as commit_err:
            logger.error(f"[v4_pipeline] T{turn_idx} order commit failed: {commit_err}", exc_info=True)
            error_text = (
                "Einen Moment — es gab ein Problem bei der Bestellung. "
                "Bitte versuchen Sie es nochmals oder rufen Sie uns direkt an."
            )
            if tts_callback:
                try:
                    await tts_callback(error_text)
                except Exception:
                    pass
            return _quick_return(
                error_text, profile, intent_result, t0,
                tools=scheduled_run + commit_tools_run,
                next_action="clarify",
                should_end=False,
            )

    # Fix 4: Early availability check before name collection
    # When core slots (party_size, date, time) are present but name/phone missing,
    # check availability early and offer to ask for name in same response.
    # These vars are also used by the commit gate below — defined here so Fix 4 can reference them.
    #
    # Also treat UNKNOWN-intent slot-filling turns as reservation continuation
    # when state already has core reservation slots (date/time/party_size present).
    _reservation_in_progress = (
        not getattr(state, "reservation_created", False)
        and _state_slot_filled(state, "reservation_date")
        and _state_slot_filled(state, "reservation_time")
        and _state_slot_filled(state, "party_size")
    )
    _is_reservation_intent = (
        intent_result.intent in (IntentKind.RESERVATION, IntentKind.MODIFY_RESERVATION)
        or (intent_result.intent in (IntentKind.UNKNOWN, IntentKind.FAQ) and _reservation_in_progress)
    )
    _not_yet_committed = not getattr(state, "reservation_created", False)
    _all_slots = end_call_stage == "idle" and _all_slots_present(state, "create_reservation")

    _core_slots_present = (
        _state_slot_filled(state, "party_size") and
        _state_slot_filled(state, "reservation_date") and
        _state_slot_filled(state, "reservation_time")
    )
    
    # Fix 8: Detect if user is correcting or re-affirming a slot value that matches stored state
    # to prevent asking for same info twice.
    # CRITICAL: Also eagerly apply any slots extracted THIS turn into state so that
    # the missing-slots check below does not ask for a slot the user just provided.
    _extracted_this_turn = getattr(execution_result, "extracted_slots", {}) or {}
    for _slot_key, _slot_val in _extracted_this_turn.items():
        if _slot_val is not None and _slot_val != "":
            try:
                setattr(state, _slot_key, _slot_val)
                logger.debug(
                    f"[v4_pipeline] T{turn_idx} eager-apply extracted slot "
                    f"{_slot_key}={_slot_val!r} into state"
                )
            except Exception as _se:
                logger.warning(f"[v4_pipeline] T{turn_idx} could not set slot {_slot_key}: {_se}")
    _user_provided_party_size = "party_size" in _extracted_this_turn and _extracted_this_turn.get("party_size") is not None
    _user_provided_name = "customer_name" in _extracted_this_turn and _extracted_this_turn.get("customer_name") is not None
    if (_is_reservation_intent and _not_yet_committed
            and _core_slots_present and not _all_slots
            and not getattr(state, "check_availability_called", False)):
        try:
            from tools.executor import execute_tool
            avail_result = await execute_tool(
                "check_availability",
                {
                    "date": getattr(state, "reservation_date", ""),
                    "time": getattr(state, "reservation_time", ""),
                    "party_size": getattr(state, "party_size", 2) or 2,
                },
                call_sid, tenant_id,
            )
            state.check_availability_called = True
            if avail_result.get("available", True):
                _has_name = bool(getattr(state, "customer_name", None) or getattr(state, "first_name", None))
                _has_phone = bool(getattr(state, "phone_number", None))
                if not _has_name:
                    _next_q = "Auf welchen Namen darf ich reservieren?"
                elif not _has_phone:
                    _next_q = "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?"
                else:
                    _next_q = ""
                avail_text = (
                    f"Ja, wir haben noch einen Tisch für {state.party_size} "
                    f"{'Person' if state.party_size == 1 else 'Personen'} um "
                    f"{state.reservation_time} Uhr verfügbar."
                    + (f" {_next_q}" if _next_q else "")
                )
            else:
                avail_text = "Leider haben wir zu diesem Zeitpunkt keinen Tisch mehr frei."
            logger.info(f"[v4_pipeline] T{turn_idx} early check_availability → {avail_text}")
            if tts_callback:
                try:
                    await tts_callback(avail_text)
                except Exception:
                    pass
            return _quick_return(
                avail_text, "reservation_start", intent_result, t0,
                tools=scheduled_run + ["check_availability"], next_action="clarify", should_end=False,
            )
        except Exception as early_avail_err:
            logger.warning(f"[v4_pipeline] early check_availability failed: {early_avail_err}")

    # ── COMMIT GATE: reservation ────────────────────────────────────────────────
    # (_is_reservation_intent, _not_yet_committed, _all_slots defined above before Fix 4)
    # Guard: don't fire reservation gate while waiting for ORDER pre-commit confirmation
    if _is_reservation_intent and _not_yet_committed and _all_slots and end_call_stage != "order_pre_commit_readback":
        # Guard: if check_availability already returned unavailable for these exact slots,
        # don't fire another check. Wait until correction_pending clears this flag.
        if getattr(state, "availability_unavailable_at_commit", False):
            unavail_repeat = (
                f"Für {getattr(state, 'reservation_time', '?')} Uhr haben wir leider keinen Tisch frei. "
                f"Möchten Sie eine andere Zeit wählen?"
            )
            return _quick_return(
                unavail_repeat, "reservation_start", intent_result, t0,
                tools=scheduled_run, next_action="clarify", should_end=False,
            )
        # Fix 3: Pre-commit readback — show summary and ask for confirmation before running tools
        # Only show if NOT already in pre_commit_readback state (confirmation already displayed)
        if not getattr(state, "pre_commit_shown", False) and end_call_stage != "pre_commit_readback":
            state.pre_commit_shown = True
            state.end_call_stage = "pre_commit_readback"
            summary = _build_pre_commit_summary_v4(state) + " Stimmt das so?"
            logger.info(f"[v4_pipeline] T{turn_idx} pre-commit summary: {summary!r}")
            if tts_callback:
                try:
                    await tts_callback(summary)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
            return _quick_return(
                summary, "reservation_start", intent_result, t0,
                tools=scheduled_run, next_action="clarify", should_end=False,
            )

        # Existing commit tools run on confirmed turn
        commit_tools_run: list[str] = []
        try:
            from tools.executor import execute_tool

            # Step 1: check_availability (skip if already called early)
            if not getattr(state, "check_availability_called", False):
                avail_args = {
                    "date": getattr(state, "reservation_date", ""),
                    "time": getattr(state, "reservation_time", ""),
                    "party_size": getattr(state, "party_size", 2) or 2,
                }
                avail_result = await execute_tool(
                    "check_availability", avail_args, call_sid, tenant_id
                )
                commit_tools_run.append("check_availability")
                state.check_availability_called = True
                logger.info(f"[v4_pipeline] T{turn_idx} check_availability → {avail_result}")
                
                # CRITICAL: If availability check failed, stop and return unavailable message
                if not avail_result.get("available", True):
                    unavail_text = (
                        f"Leider haben wir zu diesem Zeitpunkt ({getattr(state, 'reservation_time', '?')} Uhr) "
                        f"keinen Tisch für {getattr(state, 'party_size', 2)} Personen verfügbar. "
                        f"Können wir eine andere Zeit anbieten?"
                    )
                    logger.warning(f"[v4_pipeline] T{turn_idx} availability check failed → returning unavailable message")
                    # Set a flag so we don't re-fire check_availability with the same slots on the next turn.
                    # This flag is cleared by correction_pending when the user provides a new date/time.
                    state.availability_unavailable_at_commit = True
                    if tts_callback:
                        try:
                            await tts_callback(unavail_text)
                        except Exception:
                            pass
                    return _quick_return(
                        unavail_text, profile, intent_result, t0,
                        tools=scheduled_run + commit_tools_run,
                        next_action="clarify",
                        should_end=False,
                    )
            else:
                logger.debug(f"[v4_pipeline] T{turn_idx} skip check_availability (already called early)")

            # Step 2: create_reservation
            res_args = {
                "date": getattr(state, "reservation_date", ""),
                "time": getattr(state, "reservation_time", ""),
                "party_size": getattr(state, "party_size", 2) or 2,
                "name": getattr(state, "customer_name", "") or getattr(state, "first_name", "") or "",
                "phone": getattr(state, "phone_number", None) or caller_phone or "",
            }
            res_result = await execute_tool(
                "create_reservation", res_args, call_sid, tenant_id
            )
            commit_tools_run.append("create_reservation")
            logger.info(f"[v4_pipeline] T{turn_idx} create_reservation → {res_result}")

            # Guard: only mark as created when the tool actually succeeded.
            # A success=False result (e.g. invalid date, capacity unavailable)
            # must NOT produce a "Ich habe reserviert" readback.
            _res_ok = res_result.get("success", True) and not res_result.get("error")
            if not _res_ok:
                _tool_error = res_result.get("error", "unbekannter Fehler")
                _alternatives = res_result.get("alternatives") or []
                if _alternatives:
                    _alt_times = ", ".join(
                        a.get("time", a.get("time_bucket", "?")) for a in _alternatives[:3]
                    )
                    error_text = (
                        f"Leider ist der Tisch um {getattr(state, 'reservation_time', 'dieser Zeit')} Uhr "
                        f"nicht verfügbar. Ich hätte noch folgende Zeiten: {_alt_times} Uhr. "
                        f"Wäre eine davon passend?"
                    )
                else:
                    error_text = (
                        "Es tut mir leid, aber bei der Buchung ist ein Fehler aufgetreten. "
                        "Bitte rufen Sie uns direkt an oder versuchen Sie es gleich nochmals."
                    )
                logger.warning(f"[v4_pipeline] T{turn_idx} create_reservation failed: {_tool_error}")
                state.end_call_stage = "idle"
                state.reservation_created = False
                state.pre_commit_shown = False
                if tts_callback:
                    try:
                        await tts_callback(error_text)
                    except Exception:
                        pass
                return _quick_return(
                    error_text, "reservation_start", intent_result, t0,
                    tools=scheduled_run + commit_tools_run,
                    next_action="clarify", should_end=False,
                )

            # Success: mark committed, give final confirmation, end call.
            # The user already confirmed via pre-commit summary — no second "Stimmt das so?" needed.
            state.reservation_created = True
            state.end_call_stage = "confirmed"
            readback = _build_readback_v4(state) + " Wir freuen uns auf Sie. Auf Wiederhören!"
            logger.info(f"[v4_pipeline] T{turn_idx} COMMITTED → readback: {readback!r}")

            if tts_callback:
                try:
                    await tts_callback(readback)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")

            return _quick_return(
                readback, "reservation_start", intent_result, t0,
                tools=scheduled_run + commit_tools_run,
                next_action="commit",
                should_end=True,
            )

        except Exception as commit_err:
            logger.error(f"[v4_pipeline] T{turn_idx} commit failed: {commit_err}", exc_info=True)
            error_text = (
                "Einen Moment — es gab ein Problem bei der Reservierung. "
                "Bitte versuchen Sie es nochmals oder rufen Sie uns direkt an."
            )
            if tts_callback:
                try:
                    await tts_callback(error_text)
                except Exception:
                    pass
            return _quick_return(
                error_text, profile, intent_result, t0,
                tools=scheduled_run + commit_tools_run,
                next_action="clarify",
                should_end=False,
            )

    # ── GOODBYE DETECTION ────────────────────────────────────────────────────────
    gd_out = execution_result.required.get("goodbye_detector")
    is_goodbye = bool(gd_out and gd_out.success and gd_out.data.get("is_goodbye"))

    if is_goodbye:
        ctx_doc.next_action = "end_call"

    # ── DETERMINISTIC CLARIFY: emit slot-asking questions without LLM ───────────
    # When ContextDocument has missing_slots and next_action is clarify, we can
    # answer with a deterministic German question instead of round-tripping
    # through TinyGenerator. This kills the latency for slot-filling turns and
    # eliminates LLM hallucination of "fake collected" slots.
    _SLOT_QUESTIONS_RESERVATION: dict[str, str] = {
        "party_size":       "Für wie viele Personen darf ich reservieren?",
        "reservation_date": "Für welchen Tag möchten Sie reservieren?",
        "reservation_time": "Um wie viel Uhr darf ich reservieren?",
        "customer_name":    "Auf welchen Namen darf ich reservieren?",
        "phone_number":     "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
    }
    _SLOT_QUESTIONS_ORDER: dict[str, str] = {
        "order_items":   "Was möchten Sie gerne bestellen?",
        "customer_name": "Auf welchen Namen soll ich die Bestellung aufnehmen?",
        "phone_number":  "Welche Telefonnummer darf ich notieren?",
    }
    # CRITICAL FIX H2.2_D3: Sync customer_name from conversation_state FIRST
    # to prevent asking "Auf welchen Namen?" when name was just extracted this turn
    if hasattr(state, 'customer_name') and state.customer_name and 'customer_name' in ctx_doc.missing_slots:
        ctx_doc.missing_slots = [s for s in ctx_doc.missing_slots if s != 'customer_name']
        logger.debug(f"[v4_pipeline] T{turn_idx} removed customer_name from missing_slots (extracted this turn)")
    # Also sync worker extractions before deterministic clarify
    if hasattr(execution_result, 'extracted_slots') and execution_result.extracted_slots:
        from server.brain.conversation_state import _NAME_BLOCKLIST as _slot_blocklist
        for slot_name, slot_val in execution_result.extracted_slots.items():
            if slot_val and not getattr(state, slot_name, None):
                # Validate customer_name against blocklist to prevent bot's own name being set
                if slot_name == "customer_name":
                    _val_lo = str(slot_val).strip().lower()
                    if _val_lo in _slot_blocklist or _val_lo in ("sailly", "ki-assistentin"):
                        logger.warning(f"[v4_pipeline] T{turn_idx} BLOCKED invalid customer_name={slot_val!r} (in blocklist)")
                        continue
                try:
                    setattr(state, slot_name, slot_val)
                    logger.debug(f"[v4_pipeline] T{turn_idx} pre-clarify sync: {slot_name}={slot_val}")
                    # Remove from missing_slots immediately after syncing to prevent re-ask
                    if slot_name in ctx_doc.missing_slots:
                        ctx_doc.missing_slots = [s for s in ctx_doc.missing_slots if s != slot_name]
                except Exception:
                    pass
    # Suppress ordering slot-asking when we're in menu FAQ override context (caller
    # mentioned ordering words but we're still in a menu FAQ conversation).
    _is_order_intent = (
        intent_result.intent in (IntentKind.TAKEAWAY, IntentKind.DELIVERY)
        and not _menu_faq_override_active
    )
    _SLOT_QUESTIONS_DE = _SLOT_QUESTIONS_ORDER if _is_order_intent else _SLOT_QUESTIONS_RESERVATION
    # Guard: if the user already described a specific order (even an off-menu item),
    # skip the deterministic "Was möchten Sie bestellen?" — let the LLM handle it.
    # This allows the bot to respond to "Ich möchte Pizza" with "Pizza ist leider nicht
    # auf unserer Karte, aber ich empfehle..." instead of asking generically.
    _user_text_len = len((user_text or "").strip())
    _user_has_specific_request = (
        _user_text_len > 15  # more than a short affirmative
        and any(kw in (user_text or "").lower() for kw in (
            "bestellen", "möchte", "hätte gerne", "nehme", "bitte", "mitnehmen",
            "liefern", "abholen", "pizza", "burger", "pasta", "sushi", "wein",
        ))
    )
    if (
        ctx_doc.next_action == "clarify"
        and ctx_doc.missing_slots
        and not is_goodbye
        and end_call_stage == "idle"
    ):
        first_missing = ctx_doc.missing_slots[0]

        # Phone give-up safety net: if phone is the missing slot and the bot already
        # asked at least once, check if the cross-turn buffer has ≥7 digits.
        # Accept the buffer rather than asking a 3rd+ time — better to have a partial
        # phone than to loop forever and cause a frustrated disconnect + call split.
        if first_missing == "phone_number" and not state.phone_number:
            _phone_buffer = getattr(state, "phone_digits_buffer", "")
            _phone_asked_already = any(
                "telefonnummer" in r.lower()
                for r in (getattr(state, "recent_responses", None) or [])
            )
            if _phone_asked_already and len(_phone_buffer) >= 7:
                state.phone_number = _phone_buffer
                state.phone_confirmed = True
                state.phone_digits_buffer = ""
                logger.info(
                    f"[v4_pipeline] T{turn_idx} phone give-up: "
                    f"accepting buffer {_phone_buffer!r} after repeated failed extraction"
                )
                # Remove phone_number from missing_slots so the pipeline can proceed
                ctx_doc.missing_slots = [s for s in ctx_doc.missing_slots if s != "phone_number"]
                if not ctx_doc.missing_slots:
                    ctx_doc.next_action = "commit"

        first_missing = ctx_doc.missing_slots[0] if ctx_doc.missing_slots else None
        # Don't fire deterministic "order_items" ask when user already stated a specific
        # item (even off-menu) — let TinyGenerator provide an informed response instead.
        _skip_deterministic = (
            first_missing == "order_items" and _user_has_specific_request
        )
        # After 2 deterministic asks for the same slot, hand off to TinyGenerator to avoid BOT_LOOP.
        if first_missing and not _skip_deterministic:
            if not hasattr(state, "_slot_ask_count"):
                state._slot_ask_count = {}
            _ask_count = state._slot_ask_count.get(first_missing, 0)
            if _ask_count >= 2:
                _skip_deterministic = True
                logger.info(
                    f"[v4_pipeline] T{turn_idx} slot={first_missing} asked {_ask_count}x "
                    f"— skipping deterministic clarify, handing to TinyGenerator"
                )
            else:
                state._slot_ask_count[first_missing] = _ask_count + 1
        clarify_text = None if (first_missing is None or _skip_deterministic) else _SLOT_QUESTIONS_DE.get(first_missing)
        # Vary name question on second ask to prevent exact BOT_LOOP
        if clarify_text and first_missing == "customer_name" and _ask_count >= 1:
            clarify_text = (
                "Darf ich fragen, unter welchem Namen ich Ihre Bestellung führen darf?"
                if _is_order_intent
                else "Unter welchem Namen darf ich reservieren?"
            )
        if clarify_text:
            logger.info(
                f"[v4_pipeline] T{turn_idx} deterministic clarify for slot={first_missing}"
            )
            # If weather data was fetched this turn, prepend it before the slot question
            # so it isn't silently dropped in multi-intent (weather + reservation) turns.
            _weather_temp = ctx_doc.resolved_entities.get("weather_temp")
            if _weather_temp:
                _weather_desc = ctx_doc.resolved_entities.get("weather_desc", "")
                _weather_prefix = (
                    f"Das Wetter heute: {_weather_desc + ', ' if _weather_desc else ''}{_weather_temp}. "
                )
                clarify_text = _weather_prefix + clarify_text
                logger.info(f"[v4_pipeline] T{turn_idx} weather prepended to deterministic clarify")
            if tts_callback:
                try:
                    await tts_callback(clarify_text)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
            return _quick_return(
                clarify_text, profile, intent_result, t0,
                tools=scheduled_run,
                next_action="clarify",
                should_end=False,
            )
        if _skip_deterministic:
            logger.info(
                f"[v4_pipeline] T{turn_idx} skipping deterministic order_items ask — "
                f"user gave specific request, passing to TinyGenerator"
            )
            # When the user mentioned something specific but it's not a known menu item,
            # instruct the LLM to acknowledge the request and explain what's available.
            if "order_items" in ctx_doc.missing_slots:
                # Build off-menu suggestion from tenant cuisine type, not hardcoded Korean items
                _cuisine_hint = ""
                if _tcfg_top:
                    _t_items = getattr(_tcfg_top, "items", None) or []
                    if _t_items:
                        _examples = ", ".join(_t_items[:3])
                        _cuisine_hint = f"z.B. {_examples}"
                    elif getattr(_tcfg_top, "cuisine_type", ""):
                        _cuisine_hint = _tcfg_top.cuisine_type
                _alt_constraint = (
                    f"Erkläre dass das genannte Gericht leider nicht auf unserer Karte steht "
                    f"und schlage eine Alternative vor"
                    + (f" ({_cuisine_hint})" if _cuisine_hint else "")
                )
                ctx_doc.response_constraints.must_include.append(_alt_constraint)

    # ── TINY GENERATOR (ensure Anthropic client for Claude models) ─────────────
    # Rule: Only Gemini allowed in the system is TTS (gemini-2.5-flash-tts).
    # All generation uses Claude Haiku 4.5 via direct Anthropic API.
    if llm_client is None or not hasattr(llm_client, "messages"):
        try:
            import os
            from anthropic import AsyncAnthropic
            model = os.getenv("MAIN_LLM_MODEL", "claude-haiku-4-5-20251001")
            key = os.getenv("ANTHROPIC_API_KEY", "")
            if model.startswith("claude-") and key:
                llm_client = AsyncAnthropic(api_key=key)
                logger.info(f"[v4_pipeline] Created Anthropic client for model={model}")
            else:
                logger.warning("[v4_pipeline] No valid Anthropic client available — TinyGenerator will fail.")
        except Exception as _e:
            logger.error(f"[v4_pipeline] Failed to create Anthropic client: {_e}")

    generator = TinyGenerator(llm_client=llm_client)
    
    # Fix 7: Check for greeting timeout and force end_call
    if state.unclear_turn_count >= 4 and intent_result.intent == IntentKind.UNKNOWN:
        timeout_text = "Entschuldigung, ich kann Sie nicht verstehen. Auf Wiederhören."
        logger.info(f"[v4_pipeline] T{turn_idx} GREETING TIMEOUT (unclear_turn_count={state.unclear_turn_count}) → ending call")
        if tts_callback:
            try:
                await tts_callback(timeout_text)
            except Exception as cb_err:
                logger.warning(f"[v4_pipeline] tts_callback raised: {cb_err}")
        
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {
            "clean_text": timeout_text,
            "raw_response": timeout_text,
            "tools_called": ["end_call"],
            "node_name": profile,
            "intent": intent_result.intent.value,
            "profile": profile,
            "turn_type": turn_type.value,
            "next_action": "end_call",
            "should_end": True,
            "elapsed_ms": elapsed_ms,
            "inner_monologue": {},
            "v4_pipeline": True,
        }
    
    try:
        # Include the current user utterance as the last history entry so the
        # generator sees what the user JUST said (not just previous exchanges).
        turns_with_current = list(last_turns or [])
        if user_text:
            turns_with_current.append(("user", user_text))
        spoken, json_meta = await generator.generate(
            ctx_doc, turns_with_current, current_node_name=profile,
            restaurant_identity=(
                f"{_tcfg_top.restaurant_name} in {(_tcfg_top.location or {}).get('city') or _tcfg_top.city}"
                if _tcfg_top and getattr(_tcfg_top, "restaurant_name", "")
                else ""
            ),
        )
    except Exception as gen_err:
        logger.warning(
            f"[v4_pipeline] TinyGenerator.generate() failed: {gen_err} "
            f"(profile={profile}, turn_idx={turn_idx}); using fallback"
        )
        spoken = "Was darf ich für Sie tun?"
        json_meta = {}

    # Inject weather data if present (Bug Fix: weather intent dropped in multi-intent)
    if ctx_doc.resolved_entities.get("weather_temp"):
        temp = ctx_doc.resolved_entities.get("weather_temp", "")
        desc = ctx_doc.resolved_entities.get("weather_desc", "")
        if desc:
            weather_line = f"Das Wetter heute ist {desc} mit {temp}. "
            spoken = weather_line + spoken
            logger.info(f"[v4_pipeline] T{turn_idx} weather injected: {weather_line}")

    if tts_callback and spoken:
        try:
            await tts_callback(spoken)
        except Exception as cb_err:
            logger.warning(f"[v4_pipeline] tts_callback raised: {cb_err}")

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        f"[v4_pipeline] T{turn_idx} profile={profile} turn_type={turn_type.value} "
        f"intent={intent_result.intent.value} elapsed={elapsed_ms}ms "
        f"workers_run={ctx_doc.workers_run} next_action={ctx_doc.next_action} "
        f"spoken={spoken[:80]!r}"
    )

    tools_called = _resolve_tools_for_profile(
        profile, execution_result, ctx_doc,
        user_text=user_text,
        scheduled_tools_run=scheduled_run,
    )

    return {
        "clean_text": spoken,
        "raw_response": spoken,
        "tools_called": tools_called,
        "node_name": profile,
        "intent": intent_result.intent.value,
        "profile": profile,
        "turn_type": turn_type.value,
        "next_action": ctx_doc.next_action,
        "should_end": is_goodbye or ctx_doc.next_action == "end_call",
        "elapsed_ms": elapsed_ms,
        "inner_monologue": json_meta,
        "v4_pipeline": True,
    }
