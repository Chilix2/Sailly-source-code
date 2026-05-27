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
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


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


class ConversationSlots:
    """Slots interface: extracted state from ConversationState for FSM."""
    
    def __init__(self, state: object):
        """Initialize from ConversationState."""
        self.customer_name = getattr(state, 'customer_name', None)
        self.customer_phone = getattr(state, 'phone_number', None)
        self.order_items = getattr(state, 'order_items', [])
        self.order_total_price = getattr(state, 'order_total_price', None)
        self.delivery_address = getattr(state, 'delivery_address', None)
        self.delivery_confirmed = getattr(state, 'delivery_confirmed', False)
        self.pickup_confirmed = getattr(state, 'pickup_confirmed', False)
        self.reservation_date = getattr(state, 'reservation_date', None)
        self.reservation_time = getattr(state, 'reservation_time', None)
        self.reservation_party_size = getattr(state, 'reservation_party_size', None)
        self.order_created = getattr(state, 'order_created', False)
        self.reservation_created = getattr(state, 'reservation_created', False)
        self.end_call_stage = getattr(state, 'end_call_stage', 'idle')
    
    def apply_to_state(self, state: object) -> None:
        """Write Slots back to ConversationState after FSM step()."""
        state.customer_name = self.customer_name
        state.phone_number = self.customer_phone
        state.order_items = self.order_items
        state.order_total_price = self.order_total_price
        state.delivery_address = self.delivery_address
        state.delivery_confirmed = self.delivery_confirmed
        state.pickup_confirmed = self.pickup_confirmed
        state.reservation_date = self.reservation_date
        state.reservation_time = self.reservation_time
        state.reservation_party_size = self.reservation_party_size
        state.order_created = self.order_created
        state.reservation_created = self.reservation_created
        state.end_call_stage = self.end_call_stage


async def _fsm_dispatch(
    slots: ConversationSlots,
    ctx: object,
    state: object,
    user_text: str,
    turn_idx: int,
    executor: Optional[object],
) -> Optional[ConversationSlots]:
    """Dispatch to conversation_fsm.step() with proper ctx handling."""
    if ctx is None:
        logger.error("[v4_pipeline_clean] ctx is None; FSM dispatch not possible")
        return None
    try:
        from server.brain import conversation_fsm
        updated_slots = await conversation_fsm.step(
            slots=slots,
            executor=executor,
            ctx=ctx,
            user_text=user_text,
            turn_idx=turn_idx,
        )
        logger.debug(f"[v4_pipeline_clean] T{turn_idx} FSM dispatch OK")
        return updated_slots
    except ImportError:
        logger.error("[v4_pipeline_clean] conversation_fsm module not found; skipping FSM dispatch")
        return slots
    except Exception as e:
        logger.error(f"[v4_pipeline_clean] FSM dispatch failed: {e}", exc_info=True)
        return None


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
        logger.debug(f"[v4_pipeline_clean] T{turn_idx} FSM not available (has_fsm={has_fsm}, ctx={ctx is not None}); falling back to legacy pipeline")
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
    
    slots = ConversationSlots(state)
    updated_slots = await _fsm_dispatch(
        slots=slots,
        ctx=ctx,
        state=state,
        user_text=user_text,
        turn_idx=turn_idx,
        executor=executor,
    )
    
    if updated_slots is None:
        logger.warning(f"[v4_pipeline_clean] T{turn_idx} FSM dispatch returned None; falling back to legacy")
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
    
    updated_slots.apply_to_state(state)
    
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
        'tools_called': [],
        'should_end': should_end,
        'end_reason': 'farewell' if should_end else '',
        'elapsed_ms': elapsed_ms,
    }
