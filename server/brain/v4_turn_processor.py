"""server/brain/v4_turn_processor.py — Adapter: process_turn_v4 behind ADKTurnProcessor interface.

Drop-in replacement for ADKTurnProcessor in BrowserBrainService and TextModeRunner.
Drives process_turn_v4 (workers + context_doc + commit gate + TinyGenerator).
All v4_pipeline fixes are live through this class.

Usage (both callers change ONE import line):
    from server.brain.v4_turn_processor import V4TurnProcessor as ADKTurnProcessor
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

logger = logging.getLogger(__name__)


# ── TurnResult (same shape as adk_turn_processor.TurnResult) ────────────────

@dataclass
class TurnResult:
    """Result of processing a single turn — compatible with adk_turn_processor.TurnResult."""
    clean_text: str
    raw_response: str
    tools_called: List[str] = field(default_factory=list)
    tool_results: dict = field(default_factory=dict)
    should_end: bool = False
    end_reason: str = ""
    missing_fields_hint: Optional[str] = None
    node_name: Optional[str] = None  # v4 exposes this directly; adk_turn_processor used getattr fallback


# ── NodeMgr stub (brain_service reads .current_node_name as fallback) ────────

class _NodeMgrStub:
    """Minimal stub satisfying brain_service.py reads of turn_processor.node_mgr."""
    def __init__(self):
        self.current_node_name: str = "greeting"
        self._turns_in_node: int = 0
        self.node_stack: list = []


# ── V4TurnProcessor ──────────────────────────────────────────────────────────

class V4TurnProcessor:
    """Drop-in replacement for ADKTurnProcessor that drives process_turn_v4.

    Implements the same external interface (constructor signature, process_turn,
    restore_from_session, and all fields brain_service.py reads directly) so
    BrowserBrainService and TextModeRunner need only a one-line import change.
    """

    def __init__(
        self,
        tenant_id: Optional[str],
        call_sid: str,
        session=None,
        caller_phone: str = "",
        filler_cb=None,
    ):
        from server.brain.conversation_state import ConversationState, set_known_items, set_tenant_context
        from anthropic import AsyncAnthropic

        self.tenant_id = tenant_id
        self.call_sid = call_sid
        self.caller_phone = caller_phone
        self._filler_cb = filler_cb
        self.session = session

        # Populate known items from tenant config so dish extraction works
        _tid = tenant_id or "doboo"
        try:
            from server.core.tenant_config import load_tenant_config
            _tenant_cfg = load_tenant_config(_tid)
            # Set global context for module-level functions to access tenant config
            set_tenant_context(_tenant_cfg)
            
            _items = getattr(_tenant_cfg, "items", []) or []
            if _items:
                set_known_items(_items)
                logger.debug(f"[V4Turn] loaded {len(_items)} known items for tenant={_tid}")
        except Exception as _e:
            logger.warning(f"[V4Turn] could not load tenant config for tenant={_tid}: {_e}")

        # Core state — real ConversationState so all slot extraction works
        self.state = ConversationState()
        self.turn_idx: int = 0
        self.last_turns: list[tuple[str, str]] = []
        self.all_tools: list[str] = []
        
        # ISSUE 5 Part 2: Pre-cache menu at init to eliminate cold-load on Turn 1
        self._menu_cache_task: Optional[asyncio.Task] = None
        
        # NodeMgr stub — brain_service reads node_mgr.current_node_name as fallback
        self.node_mgr = _NodeMgrStub()

        # Observability stubs — brain_service reads these in metrics block (lines ~853-1006)
        # Returning empty/zero values is safe; they are logging-only
        self._last_prompt_tokens_in: int = 0
        self._last_prompt_tokens_out: int = 0
        self._current_turn_error_codes: list = []
        
        # LayerTrace — wired in process_turn for full observability
        self._current_layer_trace: Optional[object] = None
        try:
            from server.brain.validation_registry import ValidationRegistry
            from tools.executor import execute_tool

            self.validation_registry = ValidationRegistry(
                execute_tool=execute_tool,
                call_sid=call_sid,
                tenant_id=tenant_id or "doboo",
                state=self.state,
            )
            self.state.validation_registry_ref = self.validation_registry
        except Exception as exc:
            logger.warning("[V4Turn] validation registry disabled: %s", exc)
            self.validation_registry = None
        self._validations_passed: int = 0
        self._validations_failed: int = 0
        self._validations_skipped: int = 0
        self._last_stt_confidence: Optional[float] = None
        self._last_tts_directive = None
        self._last_bot_response: str = ""
        self._pending_bot_response: str = ""
        self._response_repeat_count: int = 0
        self._last_slot_extraction_latency_ms: Optional[int] = None
        self._last_slot_retention_status: Optional[dict] = None
        self._last_validation_passes: Optional[list] = None
        self._semantic_tools_called_this_turn: list[str] = []
        self._speculative_semantic_task: Optional[asyncio.Task] = None
        self._speculative_semantic_partial: str = ""
        self._speculative_semantic_slots: list[str] = []
        self._speculative_semantic_turn_idx: Optional[int] = None
        self._speculative_generator_task: Optional[asyncio.Task] = None
        self._speculative_generator_partial: str = ""
        self._speculative_generator_profile: str = ""
        self._speculative_generator_turn_idx: Optional[int] = None

        # Anthropic client for TinyGenerator
        self._llm_client = AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        try:
            from server.brain.slot_extractor import SlotExtractor
            from server.brain.slot_extraction_layer import SlotExtractionLayer

            self.slot_extractor = SlotExtractor(anthropic_client=self._llm_client)
            self.slot_extraction_layer = SlotExtractionLayer(self.slot_extractor)
        except Exception as exc:
            logger.warning("[V4Turn] semantic slot extraction disabled: %s", exc)
            self.slot_extractor = None
            self.slot_extraction_layer = None
        
        # ISSUE 5 Part 2: Start menu pre-caching asynchronously at init
        self._start_menu_precache()

    def _start_menu_precache(self) -> None:
        """Start menu pre-caching in background to avoid cold-load latency on Turn 1."""
        if self._menu_cache_task is not None:
            return
        try:
            self._menu_cache_task = asyncio.create_task(self._precache_menu())
            logger.debug(f"[V4Turn] started background menu pre-caching for tenant={self.tenant_id or 'doboo'}")
        except Exception as e:
            logger.warning(f"[V4Turn] could not start menu pre-cache task: {e}")

    def _normalize_menu_for_cache(self, menu: dict) -> dict:
        """Convert menu from any format (nested categories or flat) to canonical flat dict.
        
        Returns: {category_name: [{name, price, ...}, ...], ...}
        Handles both menu.categories[].items[] (nested) and category: items[] (flat).
        """
        if not isinstance(menu, dict):
            return {}
        
        canonical: dict = {}
        
        # Case 1: Nested format with categories key (menu.categories[])
        if "categories" in menu:
            for category in menu.get("categories", []):
                if not isinstance(category, dict):
                    continue
                cat_name = category.get("name", "")
                if not cat_name:
                    continue
                items = category.get("items", [])
                if not isinstance(items, list):
                    continue
                
                flat_items = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    # Flatten variants into separate items
                    variants = item.get("variants", [])
                    if variants and isinstance(variants, list) and len(variants) > 0:
                        for variant in variants:
                            if not isinstance(variant, dict):
                                continue
                            # Create new item with variant info merged
                            flat_item = {k: v for k, v in item.items() if k != "variants"}
                            # Merge variant fields (size, price, etc.)
                            for vk, vv in variant.items():
                                if vk == "size" and "size" not in flat_item:
                                    # Append size to name for clarity
                                    flat_item["name"] = f"{item.get('name', '')} {vv}".strip()
                                elif vk != "size":
                                    flat_item[vk] = vv
                            flat_items.append(flat_item)
                    else:
                        # No variants, keep as-is
                        flat_items.append(item)
                
                if flat_items:
                    canonical[cat_name] = flat_items
        else:
            # Case 2: Already flat format (category_name: items[])
            for cat_name, items in menu.items():
                if cat_name in ("restaurant_info", "weather_location"):
                    continue  # Skip non-menu sections
                if not isinstance(items, list):
                    continue
                
                flat_items = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    # Flatten variants into separate items
                    variants = item.get("variants", [])
                    if variants and isinstance(variants, list) and len(variants) > 0:
                        for variant in variants:
                            if not isinstance(variant, dict):
                                continue
                            flat_item = {k: v for k, v in item.items() if k != "variants"}
                            for vk, vv in variant.items():
                                if vk == "size" and "size" not in flat_item:
                                    flat_item["name"] = f"{item.get('name', '')} {vv}".strip()
                                elif vk != "size":
                                    flat_item[vk] = vv
                            flat_items.append(flat_item)
                    else:
                        flat_items.append(item)
                
                if flat_items:
                    canonical[cat_name] = flat_items
        
        return canonical

    async def _precache_menu(self) -> None:
        """Pre-cache the menu from tenant config or tools."""
        try:
            from server.core.tenant_config import get_tenant_registry
            _tenant_cfg = get_tenant_registry().load_tenant(self.tenant_id or "doboo")
            if hasattr(_tenant_cfg, "menu") and _tenant_cfg.menu:
                normalized_menu = self._normalize_menu_for_cache(_tenant_cfg.menu)
                self.state.cached_menu = normalized_menu
                _n_items = sum(len(v) for v in normalized_menu.values() if isinstance(v, list))
                logger.info(f"[V4Turn] pre-cached menu from tenant config ({_n_items} items)")
                return
        except Exception as e:
            logger.debug(f"[V4Turn] tenant config menu pre-cache failed: {e}")
        
        # Fallback: attempt to fetch via execute_tool if available
        try:
            from tools.executor import execute_tool
            _menu_result = await execute_tool("get_menu", {}, self.call_sid, self.tenant_id or "doboo")
            if isinstance(_menu_result, dict):
                _menu = _menu_result.get("menu") or _menu_result.get("items") or _menu_result
                if isinstance(_menu, dict) and _menu:
                    normalized_menu = self._normalize_menu_for_cache(_menu)
                    self.state.cached_menu = normalized_menu
                    _n_items = sum(len(v) for v in normalized_menu.values() if isinstance(v, list))
                    logger.info(f"[V4Turn] pre-cached menu via execute_tool ({_n_items} items)")
        except Exception as e:
            logger.debug(f"[V4Turn] execute_tool menu pre-cache failed: {e}")

    async def start_speculative_semantic_extraction(self, partial_text: str) -> None:
        """Start semantic slot extraction on Flux partial text without mutating durable state."""
        # ISSUE 5 Part 4: Enable speculative extraction by default
        if os.environ.get("SEMANTIC_SPECULATIVE_ENABLED", "true").lower() not in ("1", "true", "yes"):
            return
        if not partial_text or self.slot_extraction_layer is None:
            return
        from server.brain.slot_extraction_layer import should_run_semantic_extraction, slots_for_current_turn

        if not should_run_semantic_extraction(self.state, partial_text):
            return
        existing = self._speculative_semantic_task
        if existing is not None and not existing.done():
            return
        slots = slots_for_current_turn(self.state, partial_text)
        self._speculative_semantic_partial = partial_text
        self._speculative_semantic_slots = slots
        self._speculative_semantic_turn_idx = self.turn_idx
        self._speculative_semantic_task = asyncio.create_task(
            self.slot_extraction_layer.extract(
                user_utterance=partial_text,
                conversation_history=self.last_turns + ([("user", partial_text)] if partial_text else []),
                current_state=self.state,
                slots_to_extract=slots,
            )
        )
        logger.info(
            "[V4Turn] started speculative semantic extraction turn=%s partial_chars=%s",
            self.turn_idx,
            len(partial_text),
        )

    async def start_speculative_generator(self, partial_text: str) -> None:
        """Start cache-only TinyGenerator work on Flux partial text."""
        if os.environ.get("SPECULATIVE_GENERATOR_ENABLED", "true").lower() not in ("1", "true", "yes"):
            return
        if not partial_text or self._speculative_generator_task is not None:
            return
        lower = partial_text.lower()
        speculative_keywords = (
            "hallo", "karte", "offen", "öffnungszeit", "geöffnet", "noch auf",
            "preis", "kostet", "haben sie", "habt ihr",
            "bibimbap", "kimchi", "bulgogi", "tofu", "mandu", "japchae",
            "bestellen", "bestell", "lieferung", "liefern", "abholen", "abholung",
            "reservier", "danke", "tschüss", "tschuess", "auf wiederhören",
        )
        recognizable = (
            getattr(self.state, "end_call_stage", "idle") in {"idle", "readback_pending", "order_pre_commit_readback"}
            and any(signal in lower for signal in speculative_keywords)
        )
        if not recognizable:
            return

        async def _generate() -> Optional[dict]:
            try:
                from server.brain.context_doc_builder import build as build_context_doc
                from server.brain.intent_classifier import classify
                from server.brain.tiny_generator import TinyGenerator
                from server.brain.v4_pipeline import _state_snapshot_for_gate
                from server.brain.workers import ExecutionResult

                intent_result = classify(partial_text, self.turn_idx)
                profile = intent_result.worker_profile
                ctx_doc = build_context_doc(
                    intent=intent_result.intent,
                    turn_type=intent_result.turn_type,
                    worker_profile=profile,
                    execution_result=ExecutionResult(),
                    current_state=_state_snapshot_for_gate(self.state),
                )
                generator = TinyGenerator(llm_client=self._llm_client)
                restaurant_identity = ""
                try:
                    from server.core.tenant_config import load_tenant_config

                    tenant_cfg = load_tenant_config(self.tenant_id or "doboo")
                    if getattr(tenant_cfg, "restaurant_name", ""):
                        city = (tenant_cfg.location or {}).get("city") or tenant_cfg.city
                        restaurant_identity = f"{tenant_cfg.restaurant_name} in {city}"
                except Exception:
                    restaurant_identity = ""
                spoken, json_meta = await generator.generate(
                    ctx_doc,
                    self.last_turns + [("user", partial_text)],
                    current_node_name=profile,
                    restaurant_identity=restaurant_identity,
                )
                return {"spoken": spoken, "json_meta": json_meta, "profile": profile}
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.debug("[V4Turn] speculative TinyGenerator failed: %s", exc)
                return None

        self._speculative_generator_partial = partial_text
        self._speculative_generator_turn_idx = self.turn_idx
        self._speculative_generator_profile = ""
        self._speculative_generator_task = asyncio.create_task(_generate())
        logger.info(
            "[V4Turn] started speculative TinyGenerator turn=%s partial_chars=%s",
            self.turn_idx,
            len(partial_text),
        )

    async def cancel_speculative_generator(self) -> None:
        task = self._speculative_generator_task
        if task is not None and not task.done():
            task.cancel()
        self._speculative_generator_task = None
        self._speculative_generator_partial = ""
        self._speculative_generator_profile = ""
        self._speculative_generator_turn_idx = None

    async def _consume_speculative_generator(self, user_text: str) -> Optional[dict]:
        task = self._speculative_generator_task
        partial = self._speculative_generator_partial or ""
        stable_prefix = partial[:8] if partial else ""
        stable = (
            task is not None
            and self._speculative_generator_turn_idx == self.turn_idx
            and bool(stable_prefix)
            and stable_prefix.lower() in user_text.lower()
        )
        self._speculative_generator_task = None
        self._speculative_generator_partial = ""
        self._speculative_generator_profile = ""
        self._speculative_generator_turn_idx = None
        if not stable:
            if task is not None and not task.done():
                task.cancel()
            return None
        try:
            result = await asyncio.wait_for(task, timeout=0.25)
        except asyncio.TimeoutError:
            task.cancel()
            return None
        except asyncio.CancelledError:
            return None
        except Exception as exc:
            logger.debug("[V4Turn] speculative TinyGenerator consume failed: %s", exc)
            return None
        if result:
            logger.info("[V4Turn] reused speculative TinyGenerator turn=%s", self.turn_idx)
        return result

    async def cancel_speculative_semantic_extraction(self) -> None:
        task = self._speculative_semantic_task
        if task is not None and not task.done():
            task.cancel()
        self._speculative_semantic_task = None
        self._speculative_semantic_partial = ""
        self._speculative_semantic_slots = []
        self._speculative_semantic_turn_idx = None

    # ── brain_service reads turn_processor._state for CRM ────────────────────
    @property
    def _state(self):
        return self.state

    # ── brain_service calls this for metrics ─────────────────────────────────
    def _collect_subsystem_status(self) -> dict:
        status: dict[str, str | bool] = {
            "registry_exists": self.validation_registry is not None,
        }
        metrics = getattr(self.state, "_last_semantic_slot_metrics", {}) or {}
        if metrics:
            status["slot_extractor"] = "timed_out" if metrics.get("timed_out") else "completed"
        elif self.slot_extraction_layer is not None:
            status["slot_extractor"] = "idle"
        if self.validation_registry is not None:
            try:
                status["validation_registry"] = (
                    "fired" if getattr(self.validation_registry, "_entries", {}) else "silent"
                )
            except Exception:
                status["validation_registry"] = "unknown"
        return status

    # ── Main entry point ──────────────────────────────────────────────────────
    async def process_turn(
        self,
        user_text: str,
        tts_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> TurnResult:
        from server.brain.conversation_state import update_state_from_utterance
        from server.brain.v4_pipeline import process_turn_v4
        from server.brain.contracts.turn_timings import TurnTimings
        from server.brain.contracts.trace import LayerTrace
        import time

        # Initialize _turn_timings at the start of each turn for TTS TTFB instrumentation.
        # This must happen at the top of process_turn before any async work begins.
        # _turn_timings is used by the TTS timing processor to stamp tts_first_byte_at
        # and by brain_service.py to accumulate per-stage latencies.
        self.state._turn_timings = TurnTimings()
        
        # Initialize LayerTrace for full observability — populated by FSM/LLM/policy layers
        self._current_layer_trace = LayerTrace(
            turn_idx=self.turn_idx,
            call_sid=self.call_sid,
        )

        # If turn 1 races the background pre-cache, wait briefly before any
        # menu-dependent extraction/readback path can ask for prices.
        if (
            not getattr(self.state, "cached_menu", None)
            and self._menu_cache_task is not None
            and not self._menu_cache_task.done()
        ):
            try:
                await asyncio.wait_for(self._menu_cache_task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("[V4Turn] menu pre-cache timed out before turn processing")
            except Exception as exc:
                logger.debug("[V4Turn] menu pre-cache failed before turn processing: %s", exc)

        self._semantic_tools_called_this_turn = []

        from server.brain.tier1_regex_slots import apply_tier1_slots
        tier1_applied = apply_tier1_slots(self.state, user_text)
        if tier1_applied:
            logger.info("[V4Turn] tier1_regex_slots applied: %s", sorted(tier1_applied))

        semantic_pre_response = await self._run_semantic_slot_extraction(user_text)
        if semantic_pre_response:
            clean = semantic_pre_response
            if user_text:
                self.last_turns.append(("user", user_text))
            self.last_turns.append(("assistant", clean))
            self.last_turns = self.last_turns[-10:]
            self._last_bot_response = clean
            self.turn_idx += 1
            await self._persist_state_safe()
            return TurnResult(
                clean_text=clean,
                raw_response=clean,
                tools_called=list(self._semantic_tools_called_this_turn),
                node_name="semantic_slot_readback",
            )

        # Step 1: semantic candidates plus legacy phone/name/date/party extraction.
        # Workers in v4_pipeline handle date/time/party_size/name but NOT phone numbers
        # (phone uses the cross-turn digit-buffer logic in update_state_from_utterance).
        update_state_from_utterance(self.state, user_text)

        # Step 2: run v4 pipeline — workers + context_doc + commit gate + TinyGenerator
        # Include current user turn in last_turns so TinyGenerator always sees it in context.
        turns_with_current = list(self.last_turns) + ([("user", user_text)] if user_text else [])
        speculative_generator_result = await self._consume_speculative_generator(user_text)
        result_dict = await process_turn_v4(
            user_text=user_text,
            turn_idx=self.turn_idx,
            state=self.state,
            call_sid=self.call_sid,
            tenant_id=self.tenant_id,
            llm_client=self._llm_client,
            last_turns=turns_with_current,
            tts_callback=tts_callback,
            caller_phone=self.caller_phone,
            speculative_worker_results=getattr(self, "_speculative_worker_results", None),
            speculative_generator_result=speculative_generator_result,
        )
        spec_worker_results = getattr(self, "_speculative_worker_results", None)
        self._speculative_worker_results = None
        
        # Log speculative worker execution and reuse metrics
        if spec_worker_results:
            reuse_count = len(spec_worker_results)
            tools_called = result_dict.get("tools_called", [])
            reuse_rate = (reuse_count / max(1, len(tools_called))) * 100
            logger.info(
                "[V4Turn] speculative_reused: workers=%s (rate=%.1f%%) turn=%s",
                reuse_count,
                reuse_rate,
                self.turn_idx,
            )
            if reuse_rate < 30 and self.turn_idx > 5:
                logger.warning(
                    "[V4Turn] FAILED: speculative reuse rate < 30%% (%.1f%%) - architecture needs review turn=%s",
                    reuse_rate,
                    self.turn_idx,
                )

        # Step 3: maintain turn history for TinyGenerator context window
        # (No explicit persist call needed — process_turn_v4 mutates state in-place.)
        if user_text:
            self.last_turns.append(("user", user_text))
        clean = result_dict.get("clean_text", "")
        if clean:
            self.last_turns.append(("assistant", clean))
        self.last_turns = self.last_turns[-10:]  # keep last 10 turns

        # Step 4: update bookkeeping
        profile = result_dict.get("profile", result_dict.get("node_name", "greeting"))
        self.node_mgr.current_node_name = profile
        tools = result_dict.get("tools_called", [])
        if self._semantic_tools_called_this_turn:
            tools = list(dict.fromkeys(list(tools or []) + self._semantic_tools_called_this_turn))
        for t in tools:
            if t not in self.all_tools:
                self.all_tools.append(t)
        self._last_bot_response = clean
        self.turn_idx += 1
        await self._persist_state_safe()
        
        # Step 5: populate LayerTrace for observability
        if self._current_layer_trace:
            import hashlib
            # Layer 1: FSM node, forced tools, state hash
            self._current_layer_trace.layer1_node = profile
            self._current_layer_trace.layer1_forced_tools = result_dict.get("forced_tools", [])
            # State hash: CRC of key slots
            state_snapshot = f"{profile}|{self.state.customer_name}|{self.state.order_items}|{self.state.reservation_date}"
            self._current_layer_trace.layer1_state_hash = hashlib.md5(state_snapshot.encode()).hexdigest()[:16]
            # Validators from validation_registry if available
            if self.validation_registry and hasattr(self.validation_registry, 'validators_run'):
                self._current_layer_trace.validators_run = self.validation_registry.validators_run
            
            # Layer 2: LLM output and latency
            self._current_layer_trace.layer2_raw_output = result_dict.get("raw_response", clean)[:500]  # truncate
            
            # Layer 3: Policy warnings and changes
            self._current_layer_trace.layer3_warnings = result_dict.get("policy_warnings", [])
            self._current_layer_trace.layer3_text_changed = result_dict.get("text_was_rewritten", False)
            self._current_layer_trace.layer3_tools_changed = result_dict.get("tools_were_gated", False)
            
            # Store on state for brain_service to access during metrics accumulation
            self.state._current_layer_trace = self._current_layer_trace

        return TurnResult(
            clean_text=clean,
            raw_response=result_dict.get("raw_response", clean),
            tools_called=tools,
            tool_results={},
            should_end=result_dict.get("should_end", False),
            end_reason=result_dict.get("end_reason", ""),
            node_name=profile,
        )

    async def _run_semantic_slot_extraction(self, user_text: str) -> Optional[str]:
        """Extract, validate, and apply semantic slot candidates before v4 logic."""
        if not user_text or self.slot_extraction_layer is None:
            return None

        import time
        from server.brain.slot_extraction_layer import should_run_semantic_extraction, slots_for_current_turn
        from server.brain.slot_validators import (
            AddressValidator,
            DateValidator,
            OrderItemValidator,
            PartySizeValidator,
            PhoneValidator,
        )

        # Confirmation intent is turn-local. Keeping an old "yes" in durable
        # semantic state can silently advance a later pre-commit gate.
        self.state.semantic_slot_values.pop("confirmation_intent", None)
        if hasattr(self.state, "pending_readback_slots"):
            self.state.pending_readback_slots.pop("confirmation_intent", None)

        if not should_run_semantic_extraction(self.state, user_text):
            self._last_slot_extraction_latency_ms = 0
            self._last_slot_retention_status = {
                "skipped": True,
                "reason": "no_semantic_need",
            }
            self._last_validation_passes = []
            return None

        started = time.monotonic()
        slots = slots_for_current_turn(self.state, user_text)
        candidates = None
        task = self._speculative_semantic_task
        partial = self._speculative_semantic_partial or ""
        stable_prefix = partial[:8] if partial else ""
        speculative_stable = (
            task is not None
            and self._speculative_semantic_turn_idx == self.turn_idx
            and bool(stable_prefix)
            and stable_prefix.lower() in user_text.lower()
        )
        if speculative_stable:
            try:
                candidates = await asyncio.wait_for(task, timeout=0.25)
                logger.info("[V4Turn] semantic_reused: turn=%s", self.turn_idx)
            except asyncio.TimeoutError:
                logger.debug("[v4_turn_processor] speculative reuse timeout — falling back to fresh extraction")
                candidates = None
            except asyncio.CancelledError:
                candidates = None
            except Exception as exc:
                logger.debug("[V4Turn] speculative semantic extraction failed: %s", exc)
                candidates = None
        elif task is not None and not task.done():
            task.cancel()

        self._speculative_semantic_task = None
        self._speculative_semantic_partial = ""
        self._speculative_semantic_slots = []
        self._speculative_semantic_turn_idx = None

        if candidates is None:
            candidates = await self.slot_extraction_layer.extract(
                user_utterance=user_text,
                conversation_history=self.last_turns + ([("user", user_text)] if user_text else []),
                current_state=self.state,
                slots_to_extract=slots,
            )
        self._last_slot_extraction_latency_ms = int((time.monotonic() - started) * 1000)

        validators = {
            "delivery_address": AddressValidator(
                call_sid=self.call_sid,
                tenant_id=self.tenant_id if self.tenant_id else "",
                city="Bonn",
            ),
            "phone": PhoneValidator(),
            "order_items": OrderItemValidator(self.state),
            "delivery_date": DateValidator(),
            "party_size": PartySizeValidator(),
        }
        validation_passes: list[dict] = []
        address_reprompt: Optional[str] = None

        async def _validate_one(candidate):
            validator = validators.get(candidate.slot_name)
            if validator is None:
                return candidate, None
            if candidate.slot_name == "delivery_address":
                candidate_value = str(candidate.value or "").strip().lower()
                current_value = str(getattr(self.state, "delivery_address", "") or "").strip().lower()
                if (
                    candidate_value
                    and current_value == candidate_value
                    and getattr(self.state, "address_verified", False)
                ):
                    return candidate, None
            result = await validator.validate(candidate)
            return candidate, result

        validated = await asyncio.gather(*(_validate_one(candidate) for candidate in candidates.all()))
        for candidate, result in validated:
            if result is None:
                continue
            candidate.validator_feedback = result.feedback
            candidate.validator_valid = result.is_valid
            candidate.confidence = max(0.0, min(1.0, candidate.confidence + result.confidence_adjustment))
            candidate.needs_readback = (
                candidate.confidence < 0.85
                or (candidate.slot_name == "delivery_address" and not result.is_valid)
            )
            if result.corrected_value is not None:
                candidate.value = result.corrected_value
                candidate.source = "validator_corrected"
            if candidate.slot_name == "delivery_address" and not result.is_valid and result.corrected_value is None:
                candidate.confidence = 0.0
                self._clear_delivery_address_state()
                address_reprompt = (
                    "Die Adresse konnte ich nicht sicher finden. "
                    "Können Sie Straße, Hausnummer und Stadt bitte noch einmal nennen?"
                )
            if result.tool_called:
                self._semantic_tools_called_this_turn.append(result.tool_called)
                if candidate.slot_name == "delivery_address" and result.is_valid:
                    self.state.verify_address_called = True
                    self.state.address_verified = True
                    self.state.verify_address_failed = False
            validation_passes.append({
                "slot": candidate.slot_name,
                "valid": result.is_valid,
                "feedback": result.feedback,
                "tool_called": result.tool_called,
            })

        confirmation = candidates.by_name("confirmation_intent")
        pending = getattr(self.state, "pending_readback_slots", {}) or {}
        if pending and confirmation and str(confirmation.value).lower() == "yes":
            self._apply_pending_semantic_slots()
            self.state.pending_readback_slots = {}
        elif pending and confirmation and str(confirmation.value).lower() == "no":
            if "delivery_address" in pending:
                self._clear_delivery_address_state()
                self.state.pending_readback_slots = {}
                return (
                    "Alles klar, bitte nennen Sie die vollständige Lieferadresse "
                    "mit Straße, Hausnummer und Stadt noch einmal."
                )
            self.state.pending_readback_slots = {}
            logger.info(
                f"[CORRECTIONS] T{getattr(self.state, 'turn_counter', '?')} confirmation_intent=no "
                f"end_call_stage={getattr(self.state, 'end_call_stage', '?')} — entering correction_pending"
            )
            self.state.end_call_stage = "correction_pending"
            return "Alles klar, was soll ich genau ändern?"

        applied = self.state.update_state_from_extracted_slots(candidates)
        self._last_slot_retention_status = {
            "requested_slots": slots,
            "applied_slots": applied,
            **getattr(self.state, "_last_semantic_slot_metrics", {}),
        }
        self._last_validation_passes = validation_passes

        if address_reprompt:
            return address_reprompt

        pending = getattr(self.state, "pending_readback_slots", {}) or {}
        if pending and not applied:
            has_one_shot_order = (
                set(pending.keys()) == {"delivery_address"}
                and callable(getattr(self.state, "has_all_order_data_for_one_shot", None))
                and self.state.has_all_order_data_for_one_shot()
            )
            if has_one_shot_order:
                # Let the order overview read back items + address together.
                return None
            return self._build_semantic_readback(pending)
        return None

    def _clear_delivery_address_state(self) -> None:
        self.state.delivery_address = None
        self.state.address_verified = False
        self.state.address_confirmed = False
        self.state.verify_address_called = False
        self.state.verify_address_failed = False
        self.state.pending_readback_slots.pop("delivery_address", None)
        self.state.semantic_slot_values.pop("delivery_address", None)
        self.state._readback_already_shown = False
        self.state._order_readback_confirmed = False
        self.state.reset_commit_readback("create_order", "delivery_address_cleared")
        self.state.end_call_stage = "idle"

    def _apply_pending_semantic_slots(self) -> None:
        from server.brain.slot_extraction_layer import SlotCandidate, SlotCandidates

        pending = getattr(self.state, "pending_readback_slots", {}) or {}
        candidates = SlotCandidates()
        for slot_name, raw in pending.items():
            if not isinstance(raw, dict):
                continue
            candidate = SlotCandidate(
                slot_name=slot_name,
                value=raw.get("value"),
                confidence=max(float(raw.get("confidence") or 0.6), 0.85),
                evidence_span=str(raw.get("evidence_span") or ""),
                source=str(raw.get("source") or "readback_confirmed"),
                needs_readback=False,
                validator_valid=raw.get("validator_valid"),
            )
            if slot_name == "order_items":
                candidates.order_items.append(candidate)
            elif hasattr(candidates, slot_name):
                setattr(candidates, slot_name, candidate)
        self.state.update_state_from_extracted_slots(candidates, apply_medium_confidence=True)

    def _build_semantic_readback(self, pending: dict) -> str:
        labels = {
            "customer_name": "den Namen",
            "delivery_address": "die Adresse",
            "phone": "die Telefonnummer",
            "order_items": "die Bestellung",
            "delivery_date": "das Datum",
            "party_size": "die Personenzahl",
        }
        parts = []
        for slot_name, raw in pending.items():
            # CRITICAL FIX: Never expose internal slots (confirmation_intent) to readback
            if slot_name == "confirmation_intent":
                continue
            if not isinstance(raw, dict):
                continue
            label = labels.get(slot_name, slot_name)
            value = raw.get("value")
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            if slot_name == "delivery_address" and value:
                try:
                    from server.brain.v4_pipeline import format_address_for_speech

                    value = format_address_for_speech(str(value))
                except Exception:
                    value = str(value)
            if value:
                parts.append(f"{label}: {value}")
        if not parts:
            return ""
        return "Ich habe verstanden: " + "; ".join(parts) + ". Stimmt das so?"

    async def _persist_state_safe(self):
        """Persist v4 brain state for WebSocket reconnects."""
        if self.session is None:
            return
        try:
            from server.brain.session_restore import conversation_state_to_dict

            blob = {
                "state": conversation_state_to_dict(self.state),
                "all_tools": list(self.all_tools),
                "turn_idx": self.turn_idx,
                "recent_responses": list(getattr(self.state, "recent_responses", []) or []),
                "node_mgr": {
                    "current_node": self.node_mgr.current_node_name,
                    "turns_in_node": self.node_mgr._turns_in_node,
                    "node_stack": list(self.node_mgr.node_stack),
                },
            }
            await self.session.update_state({"adk_brain": blob})
        except Exception as e:
            logger.debug("[V4Turn] persist_state failed (non-fatal): %s", e)

    # ── Session restore (WebSocket reconnect path for /ws/demo) ──────────────
    @classmethod
    async def restore_from_session(
        cls,
        session,
        tenant_id: Optional[str],
        call_sid: str,
        caller_phone: str = "",
        filler_cb=None,
    ) -> Optional["V4TurnProcessor"]:
        """Reconstruct processor from Redis session blob (WebSocket reconnect).

        Reads the same `state.adk_brain` blob written by ADKTurnProcessor so
        existing sessions survive the migration.
        """
        try:
            data = await session.get()
            blob = (data or {}).get("state", {}).get("adk_brain")
            if not blob:
                return None

            processor = cls(
                tenant_id=tenant_id,
                call_sid=call_sid,
                session=session,
                caller_phone=caller_phone,
                filler_cb=filler_cb,
            )
            # Restore ConversationState without importing the retired ADK stack.
            from server.brain.session_restore import conversation_state_from_dict
            processor.state = conversation_state_from_dict(blob.get("state", {}))
            processor.all_tools = blob.get("all_tools", [])
            processor.turn_idx = blob.get("turn_idx", 0)
            processor.state.recent_responses = blob.get("recent_responses", [])

            node_blob = blob.get("node_mgr", {})
            processor.node_mgr.current_node_name = node_blob.get("current_node", "greeting")
            processor.node_mgr._turns_in_node = node_blob.get("turns_in_node", 0)
            processor.node_mgr.node_stack = node_blob.get("node_stack", [])

            logger.info(
                f"[V4Turn] Restored session at turn {processor.turn_idx}, "
                f"node={processor.node_mgr.current_node_name}"
            )
            return processor
        except Exception as e:
            logger.warning(f"[V4Turn] restore_from_session failed (non-fatal): {e}")
            return None
