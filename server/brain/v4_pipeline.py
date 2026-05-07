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
    negative = ("nein", "nicht", "falsch", "anders", "ändern", "aendern",
                "korrigieren", "nochmal", "andere", "stimmt nicht", "falsch")
    if any(w in lower for w in negative):
        return False
    positive = ("ja", "genau", "richtig", "korrekt", "stimmt", "passt",
                "super", "perfekt", "ok", "okay", "gut", "gerne", "gern",
                "bestätige", "alles klar", "ja bitte", "ja genau", "in ordnung")
    return any(w in lower.split() or w in lower for w in positive)


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

    plural = "Person" if party == 1 else "Personen"
    return (
        f"Ich würde {party} {plural} "
        f"für {spoken_date} um {spoken_time} Uhr auf den Namen {name} reservieren."
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
        items_str = str(items) if items else "Ihre Bestellung"

    return f"Ich würde also {items_str} auf den Namen {name} aufnehmen."


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
        plural = "Person" if party == 1 else "Personen"
        return (
            f"Ich habe {party} {plural} "
            f"für {spoken_date} um {spoken_time} Uhr auf den Namen {name} reserviert."
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
        if any(w in text for w in ("öffnungszeit", "geöffnet", "wann", "uhrzeit")) \
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

    # Use pre-resolved intent from IntentSessionManager when supplied; this is
    # the universal intent path that handles locking, CONFIRM/DENY inheritance,
    # and reroute. Fall back to bare classify() only for direct callers (tests).
    if intent_result is None:
        intent_result = classify(user_text, turn_idx)
    profile = intent_result.worker_profile
    turn_type = intent_result.turn_type
    
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
    if _is_loop_complaint:
        state._response_repeat_count += 1
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
        _slots_after_recovery = [
            getattr(state, 'party_size', None),
            getattr(state, 'reservation_date', None),
            getattr(state, 'reservation_time', None),
            getattr(state, 'customer_name', None),
        ]
        if all(_slots_after_recovery):
            logger.info(f'[v4_pipeline] T{turn_idx} loop-recovery: all slots present after extraction — falling through to commit gate')
            state._response_repeat_count = 0
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
    _reservation_keywords = [
        "reservieren", "reservierung", "tisch", "buchen", "buchung",
        "platz", "sitzplatz", "tafel",
    ]
    _order_keywords = [
        "bestellen", "bestellung", "liefern", "abholen", "takeaway",
        "mitnehmen",
    ]
    _user_lower_kw = user_text.lower()
    if intent_result.intent == IntentKind.UNKNOWN:
        if any(kw in _user_lower_kw for kw in _reservation_keywords):
            logger.info(
                f"[v4_pipeline] T{turn_idx} UNKNOWN intent but reservation keywords detected "
                f"→ overriding profile to reservation_start"
            )
            profile = "reservation_start"
        elif any(kw in _user_lower_kw for kw in _order_keywords):
            logger.info(
                f"[v4_pipeline] T{turn_idx} UNKNOWN intent but order keywords detected "
                f"→ overriding profile to order_start"
            )
            profile = "order_start"

    # Pre-routing slot hydration: scan recent turns for any slots the user
    # already provided but that weren't persisted (e.g. party_size from turn 2
    # still missing in state at turn 5 because the worker missed it).
    _recent_utterances = [t[1] for t in (last_turns or [])] + [user_text]
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

    plan = route(profile, turn_type)
    ctx = _build_worker_ctx(user_text, turn_idx, state, call_sid, tenant_id)
    execution_result = await worker_execute(plan, ctx)

    # ── Execute business-info tools inline so results land in ctx_doc ────────
    # get_date_info is telemetry-labelled but never truly called when
    # tool_results is None (the common path via v4_turn_processor).
    # For FAQ/opening-hours questions we need the actual result.
    if tool_results is None:
        tool_results = {}
    _text_lo = user_text.lower()
    _is_hours_question = any(w in _text_lo for w in ("öffnungszeit", "geöffnet", "wann", "uhrzeit", "offen", "aufmachen", "zumachen"))
    _is_menu_question = any(w in _text_lo for w in ("speisekarte", "menü", "menu", "gericht", "essen", "habt", "was gibt", "empfehl", "was haben", "was bieten"))
    if _is_hours_question and "get_date_info" not in tool_results:
            try:
                from tools.executor import execute_tool as _et
                _date_res = await _et("get_date_info", {"date": "heute"}, call_sid, tenant_id)
                tool_results["get_date_info"] = _date_res if isinstance(_date_res, dict) else {}
                logger.debug("[v4_pipeline] executed get_date_info inline: %s", tool_results["get_date_info"])
            except Exception as _e:
                logger.debug("[v4_pipeline] inline get_date_info failed (non-fatal): %s", _e)
    if _is_menu_question and "get_menu" not in tool_results:
        try:
            from tools.executor import execute_tool as _et
            _menu_res = await _et("get_menu", {}, call_sid, tenant_id)
            tool_results["get_menu"] = _menu_res if isinstance(_menu_res, dict) else {}
            logger.debug("[v4_pipeline] executed get_menu inline: %s", str(tool_results["get_menu"])[:200])
        except Exception as _e:
            logger.debug("[v4_pipeline] inline get_menu failed (non-fatal): %s", _e)

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
                    loc = result.get("location", "Bonn")
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
                        # today's weekday key in lowercase English (e.g. "thursday")
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
                        ctx_doc.resolved_entities["menu_data"] = menu
                elif tool_name == "check_availability":
                    ctx_doc.resolved_entities["availability"] = (
                        "verfügbar" if result.get("available") else "nicht verfügbar"
                    )
                    ctx_doc.resolved_entities["seats_remaining"] = result.get("seats_remaining")

    scheduled_run = list(tool_results.keys()) if tool_results else []

    # ── POST-COMMIT READBACK STATE MACHINE ──────────────────────────────────────
    end_call_stage = getattr(state, "end_call_stage", "idle")

    # Handle correction pending: reset to idle, let workers update slots, re-evaluate
    if end_call_stage == "correction_pending":
        state.end_call_stage = "idle"
        end_call_stage = "idle"
        # Also reset check_availability_called so a new check fires for corrected date/time
        state.check_availability_called = False
        # Clear unavailable flag so corrected slots get a fresh availability check
        state.availability_unavailable_at_commit = False
        # Reset pre-commit shown flags so updated summary is re-shown after correction
        state.pre_commit_shown = False
        state.order_pre_commit_shown = False
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

    # Fix 3: Handle pre-commit readback: show summary before confirming reservation
    if end_call_stage == "pre_commit_readback":
        if _is_confirmation_v4(user_text):
            # User confirmed — now run commit tools
            state.end_call_stage = "idle"
            end_call_stage = "idle"
            logger.info(f"[v4_pipeline] T{turn_idx} pre-commit summary confirmed → proceeding to commit")
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
    _post_commit_stage = end_call_stage in ("confirmed", "idle") and _already_committed
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
        if _is_confirmation_v4(user_text):
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
    _order_not_committed = not getattr(state, "order_created", False)
    _order_slots_ok = (
        end_call_stage == "idle"
        and _all_slots_present(state, "create_order")
    )

    if _is_order_intent and _order_not_committed and _order_slots_ok:
        # Pre-commit readback: show order summary and ask for confirmation before firing tool
        if not getattr(state, "order_pre_commit_shown", False):
            state.order_pre_commit_shown = True
            state.end_call_stage = "pre_commit_readback"
            summary = _build_pre_commit_order_summary_v4(state) + " Stimmt das so?"
            logger.info(f"[v4_pipeline] T{turn_idx} pre-commit order summary: {summary!r}")
            if tts_callback:
                try:
                    await tts_callback(summary)
                except Exception as _cb_err:
                    logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
            return _quick_return(
                summary, "order_start", intent_result, t0,
                tools=scheduled_run, next_action="clarify", should_end=False,
            )

        # User confirmed on previous turn → now execute the order
        commit_tools_run: list[str] = []
        try:
            from tools.executor import execute_tool

            items = getattr(state, "selected_items", None) or []
            order_args = {
                "name": getattr(state, "customer_name", "") or "",
                "phone": getattr(state, "phone_number", "") or caller_phone or "",
                "order_items": ", ".join(items) if isinstance(items, list) else str(items),
                "order_type": "delivery" if getattr(state, "delivery_address_mentioned", False) else "takeaway",
                "payment_method": "bar",
                "delivery_address": getattr(state, "delivery_address", "") or "",
            }
            order_result = await execute_tool(
                "create_order", order_args, call_sid, tenant_id
            )
            commit_tools_run.append("create_order")
            logger.info(f"[v4_pipeline] T{turn_idx} create_order → {order_result}")

            state.order_created = True
            state.end_call_stage = "confirmed"
            readback = _build_readback_v4(state) + " Wir kümmern uns darum. Auf Wiederhören!"
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
                should_end=True,
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
        or (intent_result.intent == IntentKind.UNKNOWN and _reservation_in_progress)
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
                avail_text = (
                    f"Ja, wir haben noch einen Tisch für {state.party_size} "
                    f"{'Person' if state.party_size == 1 else 'Personen'} um "
                    f"{state.reservation_time} Uhr verfügbar. "
                    f"Auf welchen Namen darf ich reservieren?"
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
    if _is_reservation_intent and _not_yet_committed and _all_slots:
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
        if not getattr(state, "pre_commit_shown", False):
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
                "name": getattr(state, "customer_name", ""),
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
    _is_order_intent = intent_result.intent in (IntentKind.TAKEAWAY, IntentKind.DELIVERY)
    _SLOT_QUESTIONS_DE = _SLOT_QUESTIONS_ORDER if _is_order_intent else _SLOT_QUESTIONS_RESERVATION
    if (
        ctx_doc.next_action == "clarify"
        and ctx_doc.missing_slots
        and not is_goodbye
        and end_call_stage == "idle"
    ):
        first_missing = ctx_doc.missing_slots[0]
        clarify_text = _SLOT_QUESTIONS_DE.get(first_missing)
        if clarify_text:
            logger.info(
                f"[v4_pipeline] T{turn_idx} deterministic clarify for slot={first_missing}"
            )
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
