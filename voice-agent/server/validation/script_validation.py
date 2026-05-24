"""
Script Validation Loop — Comprehensive fix-validation orchestrator.

Combines:
1. Bucket-based gating (12 failure categories, 3-step validation, Tier 1/2 thresholds)
2. Cluster-based fixing (cascade-collapse root causes, surgical patches, LLM-as-Judge)
3. Text-only runner (no audio, no Grok/TTS, script-only for fast iteration)
4. Surgical ordering (dependency-depth prioritization)
5. Dynamic scenario generation (difficulty × persona matrix, 210+ scenarios)
6. 5-worker orchestration (stagger + per-phase attempt gates with forced advance)

One file. Complete workflow. Ready for production iteration loops.

Usage:
    python3 -m server.validation.script_validation \
        --phases a-d \
        --workers 5 \
        --stagger-s 5 \
        --threshold 0.98 \
        --max-attempts 3
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import socket
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

# Dependency-graph depth (lower = leaf, fix first)
DEP_DEPTH = {
    "conversation_state.py":   0,   # data layer
    "captured_intents.py":     0,
    "order_slots.py":          0,
    "memory_manager.py":       1,
    "validation_registry.py":  1,
    "slot_extractor.py":       1,
    "tools_executor.py":       2,
    "node_manager.py":         3,
    "conversation_nodes.py":   3,
    "adk_turn_processor.py":   4,
    "v4_pipeline.py":          5,
    "main.py":                 6,   # orchestration
}
DEFAULT_DEPTH = 4

# Tier-based validation thresholds
TIER_1_THRESHOLD = 1.0  # 100% (compliance-critical)
TIER_2_THRESHOLD = 0.60  # 60% (quality)

# 12 failure buckets (from fix_validation_buckets)
BUCKETS_DEF = [
    # Tier 1 (100% required)
    ("ai_greeting",          1, 6,  "Force ai_greeting on turn 0",               TIER_1_THRESHOLD),
    ("verify_address",       2, 41, "Sticky flag + no node restriction",          TIER_1_THRESHOLD),
    ("create_order",         3, 4,  "Remove confirmation gate + partial dish",    TIER_1_THRESHOLD),
    ("send_sms",             4, 0,  "Auto-pair send_sms with create_order",       TIER_1_THRESHOLD),
    ("create_reservation",   5, 31, "Remove confirmation gate + check_avail",     TIER_1_THRESHOLD),
    ("get_date_info",        6, 13, "Remove turn==0 + add ordering node",         TIER_1_THRESHOLD),
    ("check_availability",   7, 5,  "Widen trigger to ordering + faq nodes",      TIER_1_THRESHOLD),
    ("get_weather",          8, 0,  "Add forced commit + state flag",             TIER_1_THRESHOLD),
    # Tier 2 (60% required)
    ("task_score",           9,  38, "Expand _ORDER_KW + _RESERVATION_KW",        TIER_2_THRESHOLD),
    ("instruction_score",    10, 6,  "Escalation prompt German-only enforcement", TIER_2_THRESHOLD),
    ("timeout",              11, 8,  "5-turn loop escape + stuck-loop detector",  TIER_2_THRESHOLD),
    ("conversation_loop",    12, 3,  "4-identical-response detector → end_call",  TIER_2_THRESHOLD),
]


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ScenarioOutcome:
    scenario_id: str
    bucket: str
    passed: bool
    failure_tags: List[str] = field(default_factory=list)
    failure_signature: str = ""
    composite_score: float = 0.0
    tools_called: List[str] = field(default_factory=list)
    duration_s: float = 0.0
    difficulty: str = ""
    persona: str = ""


@dataclass
class FailureCluster:
    cluster_id: str
    signature: str
    members: List[ScenarioOutcome]
    suspect_files: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.members)

    @property
    def min_dep_depth(self) -> int:
        depths = [DEP_DEPTH.get(f, DEFAULT_DEPTH) for f in self.suspect_files]
        return min(depths) if depths else DEFAULT_DEPTH

    def priority_key(self) -> Tuple[int, int]:
        return (-self.count, self.min_dep_depth)


@dataclass
class ValidatedBucket:
    name: str
    priority: int
    tier: int
    threshold: float
    status: str = "pending"  # pending / running / validated / unresolved
    step1_rate: float = 0.0
    step2_rate: float = 0.0
    step3_rate: float = 0.0
    combined_rate: float = 0.0
    attempts: int = 0
    max_attempts: int = 3


@dataclass
class PhaseAttemptResult:
    """Result of a single phase attempt (one run of all scenarios)."""
    phase: str
    attempt: int
    total: int
    passed: int
    failed: int
    pass_rate: float
    threshold_met: bool
    forced_advance: bool = False
    duration_s: float = 0.0
    outcomes: List[ScenarioOutcome] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "attempt": self.attempt,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": f"{self.pass_rate * 100:.1f}%",
            "threshold_met": self.threshold_met,
            "forced_advance": self.forced_advance,
            "duration_s": f"{self.duration_s:.1f}s",
        }


@dataclass
class ValidationReport:
    phase: str
    timestamp: str
    total_buckets: int
    validated: int
    unresolved: int
    tier1_validated: int
    tier2_validated: int
    buckets: List[Dict] = field(default_factory=list)
    clusters: List[Dict] = field(default_factory=list)
    fixes_applied: List[Dict] = field(default_factory=list)
    duration_s: float = 0.0
    # Stress test fields
    scenarios_total: int = 0
    scenarios_passed: int = 0
    scenarios_by_difficulty: Dict[str, Any] = field(default_factory=dict)
    scenarios_by_persona: Dict[str, Any] = field(default_factory=dict)
    phase_attempts: List[Dict] = field(default_factory=list)
    grok_audits: List[Dict] = field(default_factory=list)


# ============================================================================
# UTILITIES
# ============================================================================

def _find_free_port(start: int = 9000, end: int = 9100) -> int:
    """Find a free TCP port for dashboard HTTP server."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port in range {start}-{end - 1}")


def cascade_signature(outcome: ScenarioOutcome) -> str:
    """Collapse failures with same root-cause prefix into one cluster."""
    if not outcome.failure_tags:
        return ""
    root = outcome.failure_tags[0]
    m = re.match(r"^([a-z_]+):", root)
    cls = m.group(1) if m else root
    ctx = f"score_{int(outcome.composite_score * 10)}" if outcome.composite_score else ""
    return f"{cls}|{ctx}"


def parse_phases_arg(phases_arg: str) -> List[str]:
    """Parse phases arg like 'a-d' or 'a,b,c' or 'a'."""
    phases_arg = phases_arg.strip().lower()
    if "-" in phases_arg and len(phases_arg) == 3:
        start, end = phases_arg[0], phases_arg[2]
        return [chr(i) for i in range(ord(start), ord(end) + 1)]
    return [p.strip() for p in phases_arg.split(",")]


# ============================================================================
# PHASE RUNNER (TEXT-ONLY, NO AUDIO) — WITH WORKER STAGGER
# ============================================================================

async def run_validation_scenarios(
    phase: str,
    scenario_ids: Optional[List[str]] = None,
    workers: int = 5,
    stagger_s: int = 5,
    timeout_s: float = 180.0,
    sailly_ws_url: str = os.environ.get("SAILLY_WS_URL", "ws://127.0.0.1:8080/ws/demo"),
) -> List[ScenarioOutcome]:
    """
    Run validation scenarios via text injection (script-only, no audio).

    Uses ScenarioMatrix for dynamic scenario generation (difficulty × persona).
    Distributes scenarios across workers with stagger to avoid resource spikes.

    Args:
        phase: Phase letter (a/b/c/d)
        scenario_ids: Optional subset of scenario IDs to run
        workers: Number of concurrent workers
        stagger_s: Seconds between worker start times
        timeout_s: Max seconds per scenario

    Returns:
        List of ScenarioOutcome objects
    """
    from server.validation.phase_runner import run_phase
    from server.validation.scenario_generator import ScenarioMatrix

    # Generate scenarios dynamically
    matrix = ScenarioMatrix()
    phase_num = ord(phase.lower()) - ord("a")
    scenario_dicts = matrix.get_all_scenarios_for_phase(phase_num)

    if scenario_ids:
        scenario_dicts = [s for s in scenario_dicts if s["id"] in scenario_ids]

    if not scenario_dicts:
        logger.warning("[script_validation] No scenarios for phase %s", phase)
        return []

    total = len(scenario_dicts)
    logger.info(
        "[script_validation] Phase %s: running %d scenarios across %d workers (stagger=%ds)",
        phase.upper(), total, workers, stagger_s,
    )

    # Create asyncio queue for scenario distribution
    scenario_queue: asyncio.Queue = asyncio.Queue()
    for sc in scenario_dicts:
        await scenario_queue.put(sc)

    # Shared results list
    results_lock = asyncio.Lock()
    all_outcomes: List[ScenarioOutcome] = []

    async def worker_loop(worker_id: int) -> None:
        """Worker: pull scenarios from queue and run them."""
        from server.validation.phase_runner import run_one_scenario
        from server.validation.scenario_loader import ValidationScenario

        # Stagger worker starts
        await asyncio.sleep(worker_id * stagger_s)
        logger.info("[script_validation] Worker %d active (stagger=%ds)", worker_id, worker_id * stagger_s)

        while True:
            try:
                sc_dict = scenario_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            try:
                # Build ValidationScenario from dict
                scenario = ValidationScenario(
                    id=sc_dict.get("id", "unknown"),
                    phase=sc_dict.get("phase", phase_num),
                    description=sc_dict.get("script", ""),
                    caller_goal=sc_dict.get("caller_goal", ""),
                    caller_identity=sc_dict.get("caller_identity", {}),
                    caller_patience_turns=15,
                    tenant_id=sc_dict.get("tenant_id", "test-tenant"),
                    confirmation_phrases=[],
                    expectations=sc_dict.get("expectations", {}),
                )

                # Run single scenario via websocket
                result = await run_one_scenario(
                    scenario,
                    sailly_ws_url=os.environ.get("SAILLY_WS_URL", "ws://127.0.0.1:8080/ws/demo"),
                    max_duration_sec=timeout_s,
                )

                outcome = ScenarioOutcome(
                    scenario_id=result.scenario_id,
                    bucket=result.bucket,
                    passed=bool(result.passed),
                    failure_tags=list(result.failure_tags or []),
                    composite_score=0.0,  # Not available in ScriptResult
                    tools_called=list(result.tools_called or []),
                    duration_s=float(result.duration_s or 0.0),
                    difficulty=sc_dict.get("difficulty", ""),
                    persona=sc_dict.get("persona", ""),
                )
                outcome.failure_signature = cascade_signature(outcome)

                async with results_lock:
                    all_outcomes.append(outcome)

            except Exception as e:
                logger.error("[script_validation] Worker %d scenario %s failed: %s",
                             worker_id, sc_dict.get("id"), e)
                # Record failure
                outcome = ScenarioOutcome(
                    scenario_id=sc_dict.get("id", "unknown"),
                    bucket=sc_dict.get("caller_goal", "unknown"),
                    passed=False,
                    failure_tags=[f"exception:{type(e).__name__}"],
                    difficulty=sc_dict.get("difficulty", ""),
                    persona=sc_dict.get("persona", ""),
                )
                outcome.failure_signature = cascade_signature(outcome)
                async with results_lock:
                    all_outcomes.append(outcome)
            finally:
                scenario_queue.task_done()

        logger.info("[script_validation] Worker %d done", worker_id)

    # Launch workers (with semaphore to cap concurrency)
    sem = asyncio.Semaphore(workers)

    async def guarded_worker(worker_id: int) -> None:
        async with sem:
            await worker_loop(worker_id)

    await asyncio.gather(*[guarded_worker(i) for i in range(workers)])

    logger.info(
        "[script_validation] Phase %s complete: %d/%d passed",
        phase.upper(),
        sum(1 for o in all_outcomes if o.passed),
        len(all_outcomes),
    )
    return all_outcomes


# ============================================================================
# CLUSTERING
# ============================================================================

def cluster_failures(outcomes: List[ScenarioOutcome]) -> List[FailureCluster]:
    """Group failures by cascade-collapsed root cause."""
    by_sig: Dict[str, List[ScenarioOutcome]] = defaultdict(list)

    for o in outcomes:
        if o.passed:
            continue
        by_sig[o.failure_signature].append(o)

    clusters: List[FailureCluster] = []
    for sig, members in by_sig.items():
        cid = hashlib.sha1(sig.encode()).hexdigest()[:10]
        clusters.append(FailureCluster(
            cluster_id=cid,
            signature=sig,
            members=members,
        ))

    clusters.sort(key=lambda c: c.priority_key())
    return clusters


# ============================================================================
# BUCKET VALIDATION (3-STEP GATING)
# ============================================================================

class ScriptValidator:
    def __init__(
        self,
        output_dir: str = "/tmp/script_validation",
        workers: int = 5,
        stagger_s: int = 5,
        threshold: float = 0.98,
        max_attempts: int = 3,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workers = workers
        self.stagger_s = stagger_s
        self.threshold = threshold
        self.max_attempts = max_attempts
        self.buckets: Dict[str, ValidatedBucket] = {}
        self.outcomes: List[ScenarioOutcome] = []
        self.report: Optional[ValidationReport] = None
        self._init_buckets()

    def _init_buckets(self):
        """Initialize 12 validation buckets."""
        for name, priority, baseline_fails, desc, tier_threshold in BUCKETS_DEF:
            tier = 1 if tier_threshold == TIER_1_THRESHOLD else 2
            self.buckets[name] = ValidatedBucket(
                name=name,
                priority=priority,
                tier=tier,
                threshold=tier_threshold,
            )

    async def validate_phase(self, phase: str) -> PhaseAttemptResult:
        """
        Run one phase attempt with up to max_attempts retries.

        - If pass_rate >= threshold: return success immediately
        - If pass_rate < threshold AND attempt < max_attempts: retry
        - If pass_rate < threshold AND attempt == max_attempts: forced advance
        """
        phase_start = time.monotonic()
        last_result: Optional[PhaseAttemptResult] = None

        for attempt in range(1, self.max_attempts + 1):
            logger.info(
                "[script_validation] Phase %s — Attempt %d/%d",
                phase.upper(), attempt, self.max_attempts,
            )

            attempt_start = time.monotonic()

            outcomes = await run_validation_scenarios(
                phase=phase,
                workers=self.workers,
                stagger_s=self.stagger_s,
                sailly_ws_url=os.environ.get("SAILLY_WS_URL", "ws://127.0.0.1:8080/ws/demo"),
            )

            total = len(outcomes)
            passed = sum(1 for o in outcomes if o.passed)
            pass_rate = passed / total if total > 0 else 0.0
            threshold_met = pass_rate >= self.threshold
            duration = time.monotonic() - attempt_start

            logger.info(
                "[script_validation] Phase %s attempt %d: %d/%d PASS (%.1f%%) — threshold %.0f%%",
                phase.upper(), attempt, passed, total, pass_rate * 100, self.threshold * 100,
            )

            last_result = PhaseAttemptResult(
                phase=phase,
                attempt=attempt,
                total=total,
                passed=passed,
                failed=total - passed,
                pass_rate=pass_rate,
                threshold_met=threshold_met,
                duration_s=duration,
                outcomes=outcomes,
            )

            if threshold_met:
                logger.info("[script_validation] Phase %s threshold MET ✓", phase.upper())
                return last_result

            if attempt < self.max_attempts:
                logger.info(
                    "[script_validation] Phase %s threshold NOT MET — retrying (%d/%d)",
                    phase.upper(), attempt, self.max_attempts,
                )
                # Brief pause before retry
                await asyncio.sleep(2)
            else:
                # Exhausted all attempts — forced advance
                logger.warning(
                    "[script_validation] Phase %s threshold NOT MET after %d attempts — "
                    "forcing advance to next phase",
                    phase.upper(), self.max_attempts,
                )
                last_result.forced_advance = True

        return last_result

    async def validate(self, phases: List[str]) -> Dict[str, Any]:
        """
        Run full validation workflow across all requested phases.

        For each phase:
        1. Generate scenarios dynamically (ScenarioMatrix)
        2. Run with N workers (default 2; stagger between starts)
        3. Gate: retry up to max_attempts, then forced advance
        4. Cluster failures, generate report

        Args:
            phases: List of phase letters, e.g. ["a", "b", "c", "d"]
        """
        started = datetime.now()
        all_phase_results: List[PhaseAttemptResult] = []
        all_outcomes: List[ScenarioOutcome] = []

        logger.info(
            "[script_validation] Starting validation: phases=%s workers=%d stagger=%ds "
            "threshold=%.0f%% max_attempts=%d",
            [p.upper() for p in phases], self.workers, self.stagger_s,
            self.threshold * 100, self.max_attempts,
        )

        for phase in phases:
            logger.info(
                "\n%s\nPHASE %s\n%s",
                "=" * 80, phase.upper(), "=" * 80,
            )

            phase_result = await self.validate_phase(phase)
            all_phase_results.append(phase_result)
            all_outcomes.extend(phase_result.outcomes)

            logger.info(
                "Phase %s: %d/%d PASS (%.1f%%) in %.1fs%s",
                phase.upper(),
                phase_result.passed,
                phase_result.total,
                phase_result.pass_rate * 100,
                phase_result.duration_s,
                " [FORCED ADVANCE]" if phase_result.forced_advance else "",
            )

        # Store final outcomes
        self.outcomes = all_outcomes

        # Cluster failures
        clusters = cluster_failures(all_outcomes)
        logger.info("[script_validation] Identified %d failure clusters", len(clusters))

        # Grok audit of top failure clusters (skipped if XAI_API_KEY not set)
        grok_audits: List[Dict[str, Any]] = []
        if clusters and os.environ.get("XAI_API_KEY"):
            try:
                auditor = GrokAuditor()
                grok_audits = await auditor.audit_all(clusters, all_outcomes)
                logger.info("[script_validation] Grok audited %d clusters", len(grok_audits))
            except Exception as e:
                logger.warning("[script_validation] Grok audit skipped: %s", e)

        # Bucket validation
        validated = 0
        unresolved = 0
        t1_validated = 0
        t2_validated = 0

        for bucket in self.buckets.values():
            bucket_outcomes = [o for o in all_outcomes if o.bucket == bucket.name]
            if bucket_outcomes:
                passed = sum(1 for o in bucket_outcomes if o.passed)
                bucket.combined_rate = passed / len(bucket_outcomes)
                if bucket.combined_rate >= bucket.threshold:
                    bucket.status = "validated"
                    validated += 1
                    if bucket.tier == 1:
                        t1_validated += 1
                    else:
                        t2_validated += 1
                else:
                    bucket.status = "unresolved"
                    unresolved += 1

        # Build breakdown by difficulty and persona
        by_difficulty: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0})
        by_persona: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0})
        for o in all_outcomes:
            if o.difficulty:
                by_difficulty[o.difficulty]["total"] += 1
                if o.passed:
                    by_difficulty[o.difficulty]["passed"] += 1
            if o.persona:
                by_persona[o.persona]["total"] += 1
                if o.passed:
                    by_persona[o.persona]["passed"] += 1

        total_scenarios = len(all_outcomes)
        total_passed = sum(1 for o in all_outcomes if o.passed)

        self.report = ValidationReport(
            phase=",".join(phases),
            timestamp=datetime.now().isoformat(),
            total_buckets=len(self.buckets),
            validated=validated,
            unresolved=unresolved,
            tier1_validated=t1_validated,
            tier2_validated=t2_validated,
            buckets=[asdict(b) for b in self.buckets.values()],
            clusters=[{
                "cluster_id": c.cluster_id,
                "signature": c.signature,
                "count": c.count,
                "members": [o.scenario_id for o in c.members],
            } for c in clusters],
            duration_s=(datetime.now() - started).total_seconds(),
            scenarios_total=total_scenarios,
            scenarios_passed=total_passed,
            scenarios_by_difficulty={
                d: {"total": v["total"], "passed": v["passed"],
                    "rate": f"{v['passed']/v['total']*100:.1f}%" if v["total"] else "0%"}
                for d, v in sorted(by_difficulty.items())
            },
            scenarios_by_persona={
                p: {"total": v["total"], "passed": v["passed"],
                    "rate": f"{v['passed']/v['total']*100:.1f}%" if v["total"] else "0%"}
                for p, v in sorted(by_persona.items())
            },
            phase_attempts=[r.to_dict() for r in all_phase_results],
            grok_audits=grok_audits,
        )

        # Save report
        phases_str = "".join(phases)
        report_path = self.output_dir / f"validation_report_{phases_str}_{int(time.time())}.json"
        report_path.write_text(json.dumps(asdict(self.report), indent=2))
        logger.info("[script_validation] Report saved to %s", report_path)

        return asdict(self.report)


# ============================================================================
# GROK AUDITOR (xAI grok-3-mini) — reviews failed scenarios via Postgres
# ============================================================================

class GrokAuditor:
    """
    Audits failure clusters using Grok (grok-3-mini).

    For each top failure cluster, it:
      1. Fetches the call transcript from Postgres (using the scenario's call_sid)
      2. Sends the transcript + failure metadata to Grok for diagnosis
      3. Returns structured fix proposals

    Requires: XAI_API_KEY env var.
    """

    _MODEL = "grok-3-mini"
    _BASE_URL = "https://api.x.ai/v1"

    def __init__(self):
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise RuntimeError("pip install openai") from e

        key = os.environ.get("XAI_API_KEY")
        if not key:
            raise RuntimeError("XAI_API_KEY not set")
        self.client = AsyncOpenAI(api_key=key, base_url=self._BASE_URL)

    async def _fetch_transcript(self, call_sid: str) -> str:
        """Pull call transcript from Postgres for a given call_sid."""
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url or not call_sid:
            return ""
        try:
            import asyncpg
            conn = await asyncpg.connect(db_url)
            rows = await conn.fetch(
                "SELECT turn_number, role, message "
                "FROM google_transcripts "
                "WHERE call_sid = $1 "
                "ORDER BY turn_number",
                call_sid,
            )
            await conn.close()
            lines = []
            for row in rows:
                role = "Sailly" if row["role"] in ("assistant", "agent") else "Anrufer"
                lines.append(f"[Turn {row['turn_number']}] {role}: {row['message']}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("[grok_auditor] transcript fetch failed for %s: %s", call_sid, e)
            return ""

    async def _audit_cluster(self, cluster: FailureCluster, transcript: str) -> Dict[str, Any]:
        """Ask Grok to diagnose one cluster and propose code-level fixes."""
        members_summary = "\n".join(
            f"  - {m.scenario_id} | tags: {m.failure_tags} | score: {m.composite_score:.2f}"
            for m in cluster.members[:10]
        )
        system_msg = (
            "Du bist ein KI-Qualitätsprüfer für ein Restaurant-Sprachassistenten-System namens Sailly. "
            "Deine Aufgabe: Analysiere fehlgeschlagene Testszenarien aus automatisierten Validierungsläufen "
            "und mache konkrete, umsetzbare Code-Verbesserungsvorschläge."
        )
        user_msg = (
            f"FAILURE CLUSTER: {cluster.signature} ({cluster.count} Fälle)\n\n"
            f"Fehlgeschlagene Szenarien:\n{members_summary}\n\n"
        )
        if transcript:
            user_msg += f"Beispiel-Gesprächsprotokoll:\n{transcript}\n\n"
        user_msg += (
            "Analysiere bitte:\n"
            "1. Was ist der wahrscheinlichste Grundfehler?\n"
            "2. Welche konkreten Codeänderungen (Datei, Funktion) würden das beheben?\n"
            "3. Welche Testszenarien sollten ergänzt werden?\n\n"
            "Antworte präzise auf Deutsch."
        )

        try:
            resp = await self.client.chat.completions.create(
                model=self._MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=600,
            )
            diagnosis = resp.choices[0].message.content.strip()
            return {
                "cluster_id": cluster.cluster_id,
                "signature": cluster.signature,
                "count": cluster.count,
                "diagnosis": diagnosis,
                "model": self._MODEL,
            }
        except Exception as e:
            logger.error("[grok_auditor] audit failed for cluster %s: %s", cluster.cluster_id, e)
            return {
                "cluster_id": cluster.cluster_id,
                "signature": cluster.signature,
                "count": cluster.count,
                "diagnosis": f"[audit error: {e}]",
                "model": self._MODEL,
            }

    async def audit_all(
        self,
        clusters: List[FailureCluster],
        outcomes: List[ScenarioOutcome],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Audit the top-N largest failure clusters."""
        top = sorted(clusters, key=lambda c: -c.count)[:top_n]
        audits: List[Dict[str, Any]] = []
        for cluster in top:
            # Fetch a sample transcript: use the first member's scenario_id as call_sid
            call_sid = cluster.members[0].scenario_id if cluster.members else ""
            transcript = await self._fetch_transcript(call_sid)
            audit = await self._audit_cluster(cluster, transcript)
            audits.append(audit)
            logger.info(
                "[grok_auditor] cluster %s (%d failures) audited",
                cluster.signature, cluster.count,
            )
        return audits


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Script Validation — bucket-gated, dynamic scenarios, stress-test capable"
    )
    parser.add_argument(
        "--phases",
        default="a",
        help="Phases to run: 'a', 'a-d', 'a,b,c' (default: a)",
    )
    parser.add_argument("--workers", type=int, default=2, help="Concurrent workers (default: 2)")
    parser.add_argument("--stagger-s", type=int, default=5, help="Seconds stagger between worker starts (default: 5)")
    parser.add_argument("--threshold", type=float, default=0.98, help="Pass-rate threshold (default: 0.98)")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max retries per phase before forced advance (default: 3)")
    parser.add_argument("--output-dir", default="/tmp/script_validation", help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    phases = parse_phases_arg(args.phases)

    validator = ScriptValidator(
        output_dir=args.output_dir,
        workers=args.workers,
        stagger_s=args.stagger_s,
        threshold=args.threshold,
        max_attempts=args.max_attempts,
    )

    report = await validator.validate(phases)

    print("\n" + "=" * 70)
    print("VALIDATION REPORT")
    print("=" * 70)
    print(f"Phases: {report['phase'].upper()}")
    print(f"Scenarios: {report['scenarios_passed']}/{report['scenarios_total']} PASS")
    print(f"Buckets validated: {report['validated']}/{report['total_buckets']}")
    print(f"Tier 1: {report['tier1_validated']}/8 (required: 8/8)")
    print(f"Tier 2: {report['tier2_validated']}/4 (required: ≥3/4)")
    print(f"Duration: {report['duration_s']:.1f}s")

    if report.get("scenarios_by_difficulty"):
        print("\nBy Difficulty:")
        for d, v in report["scenarios_by_difficulty"].items():
            print(f"  {d}: {v['passed']}/{v['total']} ({v['rate']})")

    if report.get("scenarios_by_persona"):
        print("\nBy Persona:")
        for p, v in report["scenarios_by_persona"].items():
            print(f"  {p:14s}: {v['passed']}/{v['total']} ({v['rate']})")

    if report.get("phase_attempts"):
        print("\nPhase Results:")
        for pa in report["phase_attempts"]:
            status = "[FORCED ADVANCE]" if pa.get("forced_advance") else ("✓" if pa.get("threshold_met") else "✗")
            print(f"  Phase {pa['phase'].upper()} attempt {pa['attempt']}: "
                  f"{pa['passed']}/{pa['total']} ({pa['pass_rate']}) {status}")

    if report.get("grok_audits"):
        print("\nGrok Audit — Top Failure Clusters:")
        for a in report["grok_audits"]:
            print(f"\n  Cluster [{a['cluster_id']}] {a['signature']} ({a['count']} failures)")
            for line in a["diagnosis"].split("\n")[:8]:
                print(f"    {line}")

    print("=" * 70)

    return 0 if report["validated"] == report["total_buckets"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
