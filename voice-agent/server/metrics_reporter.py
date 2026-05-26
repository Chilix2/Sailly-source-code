"""
Metrics Reporter — Phase 0 root-cause analysis reporting layer.

Queries google_turn_metrics and related tables to generate deep-dive
diagnostics for:
- Slot extraction and retention
- Validation pipeline
- TTS timing
- Barge-in behavior
- LLM latency anomalies
- Call lifecycle (farewell, end_call wiring)
"""

import json
from typing import Optional, Any
from datetime import datetime
import asyncpg

from server.database import get_pool
from loguru import logger


async def get_call_metrics_deep_dive(call_sid: str) -> dict:
    """
    Root-cause analysis deep dive for a single call.
    
    Returns:
    {
        "call_header": {...},  # from google_calls
        "universal_failures": [...],  # Phase 0 critical findings
        "per_turn_diagnostics": [...],  # slot, validation, TTS, barge-in per turn
        "metrics_summary": {...},  # aggregates (latencies, success rates, etc.)
        "recommendations": [...]  # actionable fixes based on patterns
    }
    """
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            # Fetch call header
            call_header = await conn.fetchrow("""
                SELECT 
                    id, call_sid, caller_number, started_at, ended_at,
                    duration_seconds, quality_score, outcome, sentiment,
                    was_escalated, avg_latency_ms
                FROM google_calls
                WHERE call_sid = $1
            """, call_sid)
            
            if not call_header:
                return {"error": f"Call {call_sid} not found"}
            
            # Fetch all turn metrics
            turn_metrics = await conn.fetch("""
                SELECT
                    turn_number, user_text, bot_text,
                    stt_latency_ms, llm_latency_ms, tts_latency_ms, total_latency_ms,
                    tools_called, node_name, validation_breakdown,
                    slot_state_json, slots_filled_count, slots_missing_required,
                    validations_fired_this_turn, validations_completed_this_turn,
                    barge_in_attempted, barge_in_succeeded, barge_in_latency_ms,
                    intent_classify_ms, worker_p50_ms, worker_p95_ms,
                    context_build_ms, generator_ttft_ms, tts_ttfb_ms,
                    eot_event_type, eot_confidence, eot_latency_ms,
                    backchannel_fired, eot_followed_immediately,
                    slot_extraction_latency_ms, slot_retention_status, validation_passes
                FROM google_turn_metrics
                WHERE call_sid = $1
                ORDER BY turn_number
            """, call_sid)
            
            if not turn_metrics:
                return {
                    "call_header": dict(call_header),
                    "error": "No turn metrics found for this call"
                }
            
            # Analyze Phase 0 universal failures
            universal_failures = _analyze_universal_failures(turn_metrics)
            
            # Per-turn diagnostics
            per_turn_diag = [
                _build_turn_diagnostic(tm, idx)
                for idx, tm in enumerate(turn_metrics)
            ]
            
            # Metrics summary
            metrics_summary = _compute_metrics_summary(turn_metrics)
            
            # Recommendations
            recommendations = _generate_recommendations(
                universal_failures, metrics_summary, turn_metrics
            )
            
            return {
                "call_header": dict(call_header),
                "universal_failures": universal_failures,
                "per_turn_diagnostics": per_turn_diag,
                "metrics_summary": metrics_summary,
                "recommendations": recommendations,
            }
    
    except Exception as e:
        logger.error(f"[METRICS] deep_dive failed for {call_sid}: {e}")
        return {"error": str(e)}


def _analyze_universal_failures(turn_metrics: list) -> list:
    """
    Identify Phase 0 critical patterns across all turns.
    Returns list of failure signatures with severity and turn indices.
    """
    failures = []
    
    # Check 1: TTS metrics always 0
    tts_always_zero = all(
        (tm.get("tts_latency_ms") or 0) == 0
        for tm in turn_metrics
    )
    if tts_always_zero:
        failures.append({
            "id": "F1_TTS_NEVER_MEASURED",
            "severity": "CRITICAL",
            "description": "TTS latency never populated in any turn",
            "affected_turns": "ALL",
            "root_cause": "TTS timing instrumentation not wired; tts_ttfb_ms captures first byte but not full TTS latency",
            "impact": "Cannot measure TTS performance; impossible to debug TTS timeouts"
        })
    
    # Check 2: Slots not retained between turns
    slot_reuse_failures = []
    for i, tm in enumerate(turn_metrics):
        slot_retention = tm.get("slot_retention_status")
        if slot_retention:
            slot_retention_dict = (
                slot_retention if isinstance(slot_retention, dict)
                else json.loads(slot_retention) if isinstance(slot_retention, str) else {}
            )
            extracted = slot_retention_dict.get("extracted", {})
            if extracted:
                # Check if in next turn, that extracted slot is carried forward
                if i + 1 < len(turn_metrics):
                    next_retention = turn_metrics[i + 1].get("slot_retention_status")
                    if next_retention:
                        next_dict = (
                            next_retention if isinstance(next_retention, dict)
                            else json.loads(next_retention) if isinstance(next_retention, str) else {}
                        )
                        for slot_name in extracted:
                            if next_dict.get("after", {}).get(slot_name) != extracted[slot_name]:
                                slot_reuse_failures.append(i)
                                break
    
    if slot_reuse_failures:
        failures.append({
            "id": "F2_SLOTS_NOT_RETAINED",
            "severity": "CRITICAL",
            "description": "Extracted slots not carried to next turn",
            "affected_turns": slot_reuse_failures,
            "root_cause": "Slot state not persisted in ConversationState between turns OR state not reloaded",
            "impact": "Name, phone, date asked repeatedly; frustrating caller experience"
        })
    
    # Check 3: Validations never fired
    validations_ever_fired = any(
        (tm.get("validations_fired_this_turn") or [])
        for tm in turn_metrics
    )
    if not validations_ever_fired:
        failures.append({
            "id": "F3_VALIDATIONS_SILENT",
            "severity": "CRITICAL",
            "description": "Validation system never fires in any turn",
            "affected_turns": "ALL",
            "root_cause": "Validation trigger logic not wired; ValidationRegistry not invoked or gates muted",
            "impact": "No slot validation; bad data collected; commit_gate not enforced"
        })
    
    # Check 4: Barge-in never attempted or tracked
    barge_attempts = [
        tm.get("barge_in_attempted")
        for tm in turn_metrics
        if tm.get("barge_in_attempted") is not None
    ]
    if not barge_attempts or all(not ba for ba in barge_attempts):
        failures.append({
            "id": "F4_BARGE_IN_OFFLINE",
            "severity": "HIGH",
            "description": "Barge-in detection not wired to metrics",
            "affected_turns": "ALL",
            "root_cause": "BargeInHandler._on_interrupt callback not connected to ADKTurnProcessor.mark_next_turn_as_interrupt()",
            "impact": "No barge-in observability; soft barge-in tuning impossible"
        })
    
    # Check 5: LLM latencies suspiciously low
    llm_latencies = [
        tm.get("llm_latency_ms") or 0
        for tm in turn_metrics
        if tm.get("llm_latency_ms")
    ]
    if llm_latencies and (sum(llm_latencies) / len(llm_latencies)) < 20:
        failures.append({
            "id": "F5_LLM_CACHE_BYPASS",
            "severity": "MEDIUM",
            "description": "LLM latencies impossibly low (avg < 20ms)",
            "affected_turns": "ALL",
            "root_cause": "LLM latency measured after template cache hit; actual LLM inference not timed",
            "impact": "Cannot measure real LLM perf; latency estimates useless for optimization"
        })
    
    return failures


def _build_turn_diagnostic(tm: dict, turn_idx: int) -> dict:
    """Build per-turn diagnostic for Phase 0 root-cause analysis."""
    
    slot_retention = tm.get("slot_retention_status") or {}
    if isinstance(slot_retention, str):
        try:
            slot_retention = json.loads(slot_retention)
        except:
            slot_retention = {}
    
    validation_passes = tm.get("validation_passes") or []
    if isinstance(validation_passes, str):
        try:
            validation_passes = json.loads(validation_passes)
        except:
            validation_passes = []
    
    validations_fired = tm.get("validations_fired_this_turn") or []
    if isinstance(validations_fired, str):
        try:
            validations_fired = json.loads(validations_fired)
        except:
            validations_fired = []
    
    return {
        "turn_number": tm.get("turn_number"),
        "user_text": tm.get("user_text"),
        "bot_text": tm.get("bot_text"),
        "latencies": {
            "stt_ms": tm.get("stt_latency_ms"),
            "llm_ms": tm.get("llm_latency_ms"),
            "tts_ms": tm.get("tts_latency_ms"),
            "total_ms": tm.get("total_latency_ms"),
            # v4 layers
            "intent_classify_ms": tm.get("intent_classify_ms"),
            "worker_p50_ms": tm.get("worker_p50_ms"),
            "context_build_ms": tm.get("context_build_ms"),
            "generator_ttft_ms": tm.get("generator_ttft_ms"),
            "tts_ttfb_ms": tm.get("tts_ttfb_ms"),
        },
        "slots": {
            "extraction_latency_ms": tm.get("slot_extraction_latency_ms"),
            "retention_status": slot_retention,
        },
        "validation": {
            "fired": validations_fired,
            "passes": validation_passes,
            "total_complete": len([p for p in validation_passes if p]),
        },
        "barge_in": {
            "attempted": tm.get("barge_in_attempted"),
            "succeeded": tm.get("barge_in_succeeded"),
            "latency_ms": tm.get("barge_in_latency_ms"),
        },
        "eot": {
            "event_type": tm.get("eot_event_type"),
            "confidence": tm.get("eot_confidence"),
            "latency_ms": tm.get("eot_latency_ms"),
            "followed_immediately": tm.get("eot_followed_immediately"),
        },
        "node_name": tm.get("node_name"),
    }


def _compute_metrics_summary(turn_metrics: list) -> dict:
    """Compute call-level aggregate metrics."""
    
    latencies = {
        "stt": [],
        "llm": [],
        "tts": [],
        "total": [],
        "intent_classify": [],
        "worker_p50": [],
        "context_build": [],
        "generator_ttft": [],
    }
    
    for tm in turn_metrics:
        stt_ms = tm.get("stt_latency_ms")
        if stt_ms is not None and stt_ms > 0:
            latencies["stt"].append(stt_ms)
        
        llm_ms = tm.get("llm_latency_ms")
        if llm_ms is not None and llm_ms > 0:
            latencies["llm"].append(llm_ms)
        
        tts_ms = tm.get("tts_latency_ms")
        if tts_ms is not None and tts_ms > 0:
            latencies["tts"].append(tts_ms)
        
        total_ms = tm.get("total_latency_ms")
        if total_ms is not None and total_ms > 0:
            latencies["total"].append(total_ms)
        
        ic_ms = tm.get("intent_classify_ms")
        if ic_ms is not None and ic_ms > 0:
            latencies["intent_classify"].append(ic_ms)
        
        wp_ms = tm.get("worker_p50_ms")
        if wp_ms is not None and wp_ms > 0:
            latencies["worker_p50"].append(wp_ms)
        
        cb_ms = tm.get("context_build_ms")
        if cb_ms is not None and cb_ms > 0:
            latencies["context_build"].append(cb_ms)
        
        gt_ms = tm.get("generator_ttft_ms")
        if gt_ms is not None and gt_ms > 0:
            latencies["generator_ttft"].append(gt_ms)
    
    def percentiles(values):
        if not values:
            return {"count": 0, "min": None, "p50": None, "p95": None, "max": None}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "min": sorted_vals[0],
            "p50": sorted_vals[n // 2],
            "p95": sorted_vals[int(n * 0.95)] if n > 1 else sorted_vals[-1],
            "max": sorted_vals[-1],
            "mean": sum(sorted_vals) // len(sorted_vals),
        }
    
    return {
        "latencies": {
            "stt": percentiles(latencies["stt"]),
            "llm": percentiles(latencies["llm"]),
            "tts": percentiles(latencies["tts"]),
            "total": percentiles(latencies["total"]),
            "intent_classify": percentiles(latencies["intent_classify"]),
            "worker_p50": percentiles(latencies["worker_p50"]),
            "context_build": percentiles(latencies["context_build"]),
            "generator_ttft": percentiles(latencies["generator_ttft"]),
        },
        "validation_coverage": {
            "turns_with_validation": len([tm for tm in turn_metrics if tm.get("validations_fired_this_turn")]),
            "total_turns": len(turn_metrics),
        }
    }


def _generate_recommendations(
    universal_failures: list,
    metrics_summary: dict,
    turn_metrics: list
) -> list:
    """Generate actionable recommendations based on failures."""
    
    recommendations = []
    failure_ids = {f["id"] for f in universal_failures}
    
    if "F1_TTS_NEVER_MEASURED" in failure_ids:
        recommendations.append({
            "priority": "P0",
            "title": "Wire TTS latency instrumentation",
            "steps": [
                "Modify PipecatTTSSession to record start/end timestamps for each TTS call",
                "Store total_tts_latency_ms = end_t - start_t in brain_service._turn_metrics",
                "Verify tts_ttfb_ms (first byte) is also captured separately",
                "Test with sample call to confirm non-zero tts_latency_ms"
            ]
        })
    
    if "F2_SLOTS_NOT_RETAINED" in failure_ids:
        recommendations.append({
            "priority": "P0",
            "title": "Fix slot persistence across turns",
            "steps": [
                "Verify ConversationState is serialized to Redis after each turn",
                "Verify ConversationState is deserialized from Redis at turn start",
                "Add test: extract name in turn 1 → verify name in turn 2 without re-asking",
                "Check if state.customer_name = '' is being reset instead of preserved"
            ]
        })
    
    if "F3_VALIDATIONS_SILENT" in failure_ids:
        recommendations.append({
            "priority": "P0",
            "title": "Activate validation trigger logic",
            "steps": [
                "Verify validation_registry.trigger_on_extract() is called after update_state_from_utterance()",
                "Check if ValidationRegistry._entries is populated (not empty)",
                "Enable debug logging in ValidationRegistry.trigger_on_extract()",
                "Test with manual validation call: extract phone → check ValidationRegistry._entries"
            ]
        })
    
    if "F4_BARGE_IN_OFFLINE" in failure_ids:
        recommendations.append({
            "priority": "P1",
            "title": "Connect barge-in detection to metrics",
            "steps": [
                "Verify BargeInHandler._on_interrupt is called when speaker detects voice",
                "Add logging to mark_next_turn_as_interrupt()",
                "Test with demo: simulate user interruption → check barge_in_attempted=true"
            ]
        })
    
    if "F5_LLM_CACHE_BYPASS" in failure_ids:
        recommendations.append({
            "priority": "P1",
            "title": "Fix LLM latency measurement",
            "steps": [
                "Audit TinyGenerator: measure from request start to first token, not cache hit",
                "Remove any cached response short-circuits from latency measurement",
                "Verify LLM call is always to actual LLM, never cached template",
                "Re-run call: expect llm_latency_ms > 100ms"
            ]
        })
    
    return recommendations


async def query_call_batch_analysis(call_sids: list[str]) -> dict:
    """Analyze multiple calls for common pattern failures."""
    
    analyses = {}
    for call_sid in call_sids:
        analyses[call_sid] = await get_call_metrics_deep_dive(call_sid)
    
    # Aggregate failure patterns
    failure_counts = {}
    for call_sid, analysis in analyses.items():
        if "universal_failures" in analysis:
            for failure in analysis["universal_failures"]:
                fail_id = failure["id"]
                failure_counts[fail_id] = failure_counts.get(fail_id, 0) + 1
    
    return {
        "calls_analyzed": len(call_sids),
        "individual_analyses": analyses,
        "common_failures": sorted(
            [
                {"failure_id": fid, "appears_in": count, "percentage": (count / len(call_sids)) * 100}
                for fid, count in failure_counts.items()
            ],
            key=lambda x: x["appears_in"],
            reverse=True
        ),
    }
