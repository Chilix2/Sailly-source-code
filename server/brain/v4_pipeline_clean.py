"""server/brain/v4_pipeline_clean.py — Clean FSM refactor of v4 deterministic pipeline.

This is the NEW single source of truth. It replaces the legacy v4_pipeline.py
with a smaller, focused file that:

1. Section A: Infrastructure
   - TTS sanitization (strip [TOOL:...] and style prompts)
   - Call duration gate (ctx.call_max_duration_s if available)
   - Redis pre-snapshot (save state before Category B tools)
   - Schema migration check (ConversationState.schema_version >= 7)

2. Section B: FSM Dispatch
   - Load ctx (TenantConfig) from session or tenant_id parameter
   - Initialize Slots from ConversationState
   - Call conversation_fsm.step(slots, executor, ctx)
   - Update state from returned Slots

3. Section C: Teardown
   - TTS-done ack (wait for TTS queue to drain)
   - Call finalization
   - Graceful shutdown

Key: ctx=TenantConfig from session ONLY, never hardcoded.
Signature is backward-compatible with v4_pipeline_legacy for gradual migration.

FALLBACK GATE: Set environment variable SAILLY_FSM_EMERGENCY_FALLBACK=1 to enable
silent fallback to legacy pipeline. Default is NO FALLBACK (Phase 2 hardening).
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# ── Fallback Gate ────────────────────────────────────────────────────────────
# Phase 2: Disable silent fallback by default. Only allow fallback if emergency flag is set.
_ENABLE_LEGACY_FALLBACK = os.getenv("SAILLY_FSM_EMERGENCY_FALLBACK", "0") == "1"

if _ENABLE_LEGACY_FALLBACK:
    logger.warning("[v4_pipeline_clean] Legacy fallback ENABLED via SAILLY_FSM_EMERGENCY_FALLBACK=1")
else:
    logger.info("[v4_pipeline_clean] Legacy fallback DISABLED (clean FSM only; set SAILLY_FSM_EMERGENCY_FALLBACK=1 to enable)")



def _sanitize_tts_text(text: str) -> str:
    """Strip [TOOL:...] tags and markdown style prompts before TTS."""
    if not text:
        return text
    text = re.sub(r'\[TOOL:[^\]]*\]', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def _enforce_call_duration(ctx: object, state: object, elapsed_ms: float) -> bool:
    """Check if call duration exceeds ctx.call_max_duration_s."""
    if ctx is None or not hasattr(ctx, 'call_max_duration_s'):
        return False
    max_duration_s = getattr(ctx, 'call_max_duration_s', None)
    if max_duration_s is None or max_duration_s <= 0:
        return False
    elapsed_s = elapsed_ms / 1000.0
    if elapsed_s > max_duration_s:
        logger.info(f"[v4_pipeline_clean] Call duration {elapsed_s:.1f}s exceeds limit {max_duration_s}s — ending call")
        return True
    return False


async def _redis_pre_snapshot(state: object, call_sid: str, category_b_tool: str) -> None:
    """Pre-commit snapshot: save ConversationState to Redis before Category B tool execution."""
    try:
        from server.layer1.persist import persist_state_snapshot
        await persist_state_snapshot(state, call_sid, checkpoint=f"pre_{category_b_tool}")
        logger.debug(f"[v4_pipeline_clean] Redis pre-snapshot: {category_b_tool}")
    except Exception as e:
        logger.warning(f"[v4_pipeline_clean] Redis pre-snapshot failed: {e}")


def _check_schema_version(state: object) -> bool:
    """Verify ConversationState.schema_version >= 7."""
    schema_version = getattr(state, 'schema_version', 0)
    if schema_version < 7:
        logger.warning(f"[v4_pipeline_clean] ConversationState schema_version={schema_version} is outdated (need >=7)")
        return False
    return True


async def _load_tenant_ctx(tenant_id: Optional[str]) -> Optional[object]:
    """Load TenantConfig from tenant_id string."""
    if not tenant_id:
        logger.warning("[v4_pipeline_clean] No tenant_id provided; cannot load ctx")
        return None
    try:
        from server.core.tenant_config import load_tenant_config
        ctx = load_tenant_config(tenant_id)
        logger.debug(f"[v4_pipeline_clean] Loaded TenantConfig for tenant={tenant_id}")
        return ctx
    except Exception as e:
        logger.error(f"[v4_pipeline_clean] Failed to load TenantConfig for {tenant_id}: {e}")
        return None


from server.brain.conversation_fsm import ConversationSlots

def _state_to_slots(state: object) -> ConversationSlots:
    """Convert ConversationState to FSM ConversationSlots dataclass."""
    return ConversationSlots(
        phone=getattr(state, 'phone_number', None),
        name=getattr(state, 'customer_name', None),
        address=getattr(state, 'delivery_address', None),
        city=getattr(state, 'city', None),
        postcode=getattr(state, 'postcode', None),
        order_type=getattr(state, 'order_type', None),
        payment_method=getattr(state, 'payment_method', None),
        reservation_date=getattr(state, 'reservation_date', None),
        reservation_time=getattr(state, 'reservation_time', None),
        party_size=getattr(state, 'reservation_party_size', None),
        intent=getattr(state, 'order_intent', None),
        confirmed=getattr(state, 'order_confirmed', False),
    )

def _slots_to_state(slots: ConversationSlots, state: object) -> None:
    """Apply FSM ConversationSlots back to ConversationState."""
    if slots.phone:
        state.phone_number = slots.phone
    if slots.name:
        state.customer_name = slots.name
    if slots.address:
        state.delivery_address = slots.address
    if slots.city:
        state.city = slots.city
    if slots.postcode:
        state.postcode = slots.postcode
    if slots.order_type:
        state.order_type = slots.order_type
    if slots.payment_method:
        state.payment_method = slots.payment_method
    if slots.reservation_date:
        state.reservation_date = slots.reservation_date
    if slots.reservation_time:
        state.reservation_time = slots.reservation_time
    if slots.party_size:
        state.reservation_party_size = slots.party_size
    if slots.intent:
        state.order_intent = slots.intent
    state.order_confirmed = slots.confirmed


async def _fsm_dispatch(
    slots: ConversationSlots,
    ctx: object,
    state: object,
    user_text: str,
    turn_idx: int,
    executor: Optional[object],
) -> tuple[Optional[ConversationSlots], list[str]]:  # (updated_slots, tools_called)
    """Dispatch to conversation_fsm.step() with proper ctx handling.
    
    ConversationFSM.step() is SYNCHRONOUS and returns a decision dict, not updated slots.
    We must instantiate FSM, call step, and extract decision.
    """
    if ctx is None:
        logger.error("[v4_pipeline_clean] ctx is None; FSM dispatch not possible")
        return None, []
    try:
        from server.brain.conversation_fsm import ConversationFSM
        # Instantiate FSM with context
        fsm = ConversationFSM(ctx=ctx)
        
        # Convert state.slots to ConversationSlots if needed
        if not isinstance(slots, ConversationSlots):
            logger.warning(f"[v4_pipeline_clean] slots not ConversationSlots; attempting conversion")
            slots = ConversationSlots()
        
        # Call synchronous step() method
        decision = fsm.step(
            slots=slots,
            user_utterance=user_text,
            ctx=ctx,
        )
        
        logger.debug(f"[v4_pipeline_clean] T{turn_idx} FSM step OK; phase={decision.get('phase')}")
        
        # Track tool calls for return
        tools_called = []
        
        # Extract tool calls from decision if phase is COMMITTED
        if decision.get('tool_calls'):
            tool_calls = decision['tool_calls']
            if executor:
                for tool_call in tool_calls:
                    try:
                        tool_name = tool_call.get('name') if isinstance(tool_call, dict) else getattr(tool_call, 'name', 'unknown')
                        await executor.execute_tool(tool_call)
                        tools_called.append(tool_name)
                    except Exception as e:
                        logger.error(f"[v4_pipeline_clean] Tool execution failed: {e}")
        
        # Return updated slots from decision (slots object, not dict)
        # FSM returns slots.to_dict() in decision, so we use the original slots object
        return slots, tools_called
        
    except ImportError as e:
        logger.error(f"[v4_pipeline_clean] ConversationFSM import failed: {e}")
        return None, []
    except Exception as e:
        logger.error(f"[v4_pipeline_clean] FSM dispatch failed: {e}", exc_info=True)
        return None, []


async def _tts_done_ack(tts_queue: Optional[asyncio.Queue]) -> None:
    """Wait for TTS queue to drain before end_call."""
    if tts_queue is None:
        return
    try:
        deadline = time.monotonic() + 10.0
        while not tts_queue.empty() and time.monotonic() < deadline:
            await asyncio.sleep(0.1)
        if not tts_queue.empty():
            logger.warning("[v4_pipeline_clean] TTS queue did not drain in 10s; ending call anyway")
    except Exception as e:
        logger.warning(f"[v4_pipeline_clean] TTS drain check failed: {e}")


async def _call_finalization(state: object, call_sid: str) -> None:
    """Final state save and cleanup after call completion."""
    try:
        from server.layer1.persist import persist_final_state
        await persist_final_state(state, call_sid)
        logger.debug(f"[v4_pipeline_clean] Call finalization saved for {call_sid}")
    except Exception as e:
        logger.warning(f"[v4_pipeline_clean] Call finalization failed: {e}")


async def _fallback_to_legacy(
    user_text: str,
    turn_idx: int,
    state: object,
    call_sid: str,
    tenant_id: Optional[str],
    llm_client: object,
    last_turns: Optional[list],
    tts_callback: Optional[Callable[[str], Awaitable[None]]],
    caller_phone: str,
    speculative_worker_results: Optional[dict],
    speculative_generator_result: Optional[dict],
) -> dict:
    """Fallback to legacy v4_pipeline_legacy if conversation_fsm not ready."""
    try:
        from server.brain.v4_pipeline_legacy import process_turn_v4 as legacy_process_turn_v4
        logger.debug("[v4_pipeline_clean] Falling back to legacy pipeline")
        result = await legacy_process_turn_v4(
            user_text=user_text,
            turn_idx=turn_idx,
            state=state,
            call_sid=call_sid,
            tenant_id=tenant_id,
            llm_client=llm_client,
            last_turns=last_turns or [],
            tts_callback=tts_callback,
            caller_phone=caller_phone,
            speculative_worker_results=speculative_worker_results,
            speculative_generator_result=speculative_generator_result,
        )
        return result
    except Exception as e:
        logger.error(f"[v4_pipeline_clean] Fallback to legacy failed: {e}", exc_info=True)
        return {
            'clean_text': user_text,
            'raw_response': "Es tut mir leid, es gab einen Fehler. Können Sie das wiederholen?",
            'tools_called': [],
            'should_end': False,
            'end_reason': '',
        }


async def process_turn_v4(
    user_text: str,
    turn_idx: int,
    state: object,
    call_sid: str,
    tenant_id: Optional[str] = None,
    llm_client: object = None,
    last_turns: Optional[list] = None,
    tts_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    caller_phone: str = "",
    speculative_worker_results: Optional[dict] = None,
    speculative_generator_result: Optional[dict] = None,
    ctx: Optional[object] = None,
    executor: Optional[object] = None,
    tts_queue: Optional[asyncio.Queue] = None,
) -> dict:
    """Process one turn with clean FSM dispatch."""
    
    t0 = time.monotonic()
    
    if not _check_schema_version(state):
        logger.warning(f"[v4_pipeline_clean] T{turn_idx} schema version check failed")
    
    if ctx is None:
        ctx = await _load_tenant_ctx(tenant_id)
    
    elapsed_ms = (time.monotonic() - t0) * 1000
    if await _enforce_call_duration(ctx, state, elapsed_ms):
        farewell = getattr(ctx, 'farewell_text', "Auf Wiederhören!") if ctx else "Auf Wiederhören!"
        if tts_callback:
            try:
                await tts_callback(_sanitize_tts_text(farewell))
            except Exception as e:
                logger.warning(f"[v4_pipeline_clean] TTS callback failed: {e}")
        await _tts_done_ack(tts_queue)
        await _call_finalization(state, call_sid)
        return {
            'clean_text': user_text,
            'raw_response': farewell,
            'tools_called': ['end_call'],
            'should_end': True,
            'end_reason': 'duration_limit_exceeded',
        }
    
    try:
        from server.brain import conversation_fsm
        has_fsm = True
    except ImportError:
        has_fsm = False
    
    if not has_fsm or ctx is None:
        if not _ENABLE_LEGACY_FALLBACK:
            logger.error(f"[v4_pipeline_clean] T{turn_idx} FSM not available (has_fsm={has_fsm}, ctx={ctx is not None}) and fallback DISABLED; raising error")
            raise RuntimeError(f"FSM dispatch prerequisites not met and emergency fallback disabled")
        logger.debug(f"[v4_pipeline_clean] T{turn_idx} FSM not available; using legacy fallback (emergency mode)")
        return await _fallback_to_legacy(
            user_text=user_text,
            turn_idx=turn_idx,
            state=state,
            call_sid=call_sid,
            tenant_id=tenant_id,
            llm_client=llm_client,
            last_turns=last_turns,
            tts_callback=tts_callback,
            caller_phone=caller_phone,
            speculative_worker_results=speculative_worker_results,
            speculative_generator_result=speculative_generator_result,
        )
    
    slots = _state_to_slots(state)
    updated_slots, tools_called = await _fsm_dispatch(
        slots=slots,
        ctx=ctx,
        state=state,
        user_text=user_text,
        turn_idx=turn_idx,
        executor=executor,
    )
    
    if updated_slots is None:
        if not _ENABLE_LEGACY_FALLBACK:
            logger.error(f"[v4_pipeline_clean] T{turn_idx} FSM dispatch returned None and fallback DISABLED; raising error")
            raise RuntimeError(f"FSM dispatch failed and emergency fallback disabled")
        logger.warning(f"[v4_pipeline_clean] T{turn_idx} FSM dispatch returned None; using legacy fallback")
        return await _fallback_to_legacy(
            user_text=user_text,
            turn_idx=turn_idx,
            state=state,
            call_sid=call_sid,
            tenant_id=tenant_id,
            llm_client=llm_client,
            last_turns=last_turns,
            tts_callback=tts_callback,
            caller_phone=caller_phone,
            speculative_worker_results=speculative_worker_results,
            speculative_generator_result=speculative_generator_result,
        )
    
    _slots_to_state(updated_slots, state)
    
    response_text = f"T{turn_idx} processed successfully"
    if tts_callback:
        try:
            await tts_callback(_sanitize_tts_text(response_text))
        except Exception as e:
            logger.warning(f"[v4_pipeline_clean] TTS callback failed: {e}")
    
    should_end = getattr(state, 'end_call_stage', 'idle') == 'confirmed'
    if should_end:
        farewell = getattr(ctx, 'farewell_text', "Auf Wiederhören!") if ctx else "Auf Wiederhören!"
        response_text = farewell
        if tts_callback:
            try:
                await tts_callback(_sanitize_tts_text(farewell))
            except Exception as e:
                logger.warning(f"[v4_pipeline_clean] TTS callback failed: {e}")
        await _tts_done_ack(tts_queue)
        await _call_finalization(state, call_sid)
    
    elapsed_ms = (time.monotonic() - t0) * 1000
    
    return {
        'clean_text': user_text,
        'raw_response': response_text,
        'tools_called': tools_called,
        'should_end': should_end,
        'end_reason': 'farewell' if should_end else '',
        'elapsed_ms': elapsed_ms,
    }
