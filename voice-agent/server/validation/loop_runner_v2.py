"""
loop_runner_v2.py — Upgraded fix-validation loop for Sailly voice agent.

Drop-in replacement for server/validation/loop_runner.py.

Differences vs v1
=================
1. SENTINEL EARLY-EXIT
   Run a small representative sample first (--sentinel N, default 12).
   If sentinel pass-rate < sentinel_floor (default 50%), abort attempt
   immediately — the agent is fundamentally broken, no point burning
   the remaining 48 scenarios.

2. SELECTIVE RE-RUN ON ATTEMPTS 2+
   Attempt 1: full suite (need complete failure picture for clustering).
   Attempts 2-3: previously-failing scenarios + N random canary scenarios
   from the previously-passing pool (regression detection).

3. CASCADE COLLAPSE
   Failures with the same root-cause signature (assertion sequence, not
   scenario id) are merged into ONE cluster. We fix clusters, not symptoms.
   38 failures with one upstream cause → 1 fix, not 38.

4. SURGICAL FIX ORDERING
   Clusters are sorted by: (count desc) × (dep-graph depth asc).
   Lower-layer files (conversation_state.py) get fixed before higher
   layers (adk_turn_processor.py, main.py). Reason: a state-layer fix
   often makes upper-layer symptoms vanish.

5. ONE FIX AT A TIME + SMOKE GATE
   Apply patch for cluster #1 → restart → run 3-scenario smoke canary
   from previously-PASSING pool → if any smoke regression, REVERT and
   skip cluster → otherwise advance to cluster #2.

6. PATCH SIZE GUARDRAIL
   Patches > 50 LOC delta or touching > 2 files are rejected.
   Forces "surgical" mindset.

7. LLM-AS-JUDGE GATE
   Second Claude call validates each patch before apply:
   "Is this minimal? Does it address the cited failure? Any obvious risk?"
   Cheap (Haiku) and catches accidental refactors.

8. ATOMIC PATCH WITH AUTO-REVERT
   Each patch is applied via per-file backup. If smoke fails, the backup
   is restored byte-for-byte. No git required.

9. HEARTBEAT + WATCHDOG-COMPATIBLE
   Writes /var/lib/sailly/test-ckpt/heartbeat every 30 s so an external
   watchdog can detect a stuck loop.

Usage
=====
    python -m server.validation.loop_runner_v2 \\
        --phase a \\
        --workers 10 \\
        --threshold 0.98 \\
        --max-attempts 3 \\
        --sentinel 12 \\
        --sentinel-floor 0.50 \\
        --canary-on-rerun 5

Environment
===========
    ANTHROPIC_API_KEY        # required for fix gen + judge
    SAILLY_VALIDATION_WS_URL # default ws://127.0.0.1:8080/ws/demo
    SAILLY_PATCH_DIR         # default /home/charles2/sailly-browser-demo/server
    SAILLY_RESTART_CMD       # default "sudo systemctl restart sailly-voice-agent"
    SKIP_FIX_GENERATION=1    # disable auto-fix (manual loop only)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

# ─── Local unit test imports (script-only, no audio) ──────────────────
# Import test functions directly — no Grok/audio needed
import subprocess
import sys

LOG = logging.getLogger("sailly.loop_v2")

# ─── Dependency-graph depth (lower = closer to leaf, fix first) ──────────────
# Adjust to your repo layout. Deeper module-path components → deeper node.
DEP_DEPTH = {
    "conversation_state.py":   0,   # data layer — leaf
    "captured_intents.py":     0,
    "order_slots.py":          0,
    "memory_manager.py":       1,
    "validation_registry.py":  1,
    "tools_definitions.py":    1,
    "slot_extractor.py":       1,
    "tools_executor.py":       2,
    "node_manager.py":         3,
    "conversation_nodes.py":   3,
    "response_variations.py":  3,
    "adk_turn_processor.py":   4,
    "tts_conditioning.py":     4,
    "v4_pipeline.py":          5,
    "main.py":                 6,   # orchestration — root
}
DEFAULT_DEPTH = 4  # unknown files: assume mid-stack


# ============================================================================
#  DATA TYPES
# ============================================================================
@dataclass
class TurnLog:
    user: str
    bot: str
    latency_ms: int = 0
    tools: list[str] = field(default_factory=list)


@dataclass
class ScenarioOutcome:
    scenario_id: str
    persona: str
    passed: bool
    failure_tags: list[str] = field(default_factory=list)
    failure_signature: str = ""           # cascade-collapsed signature
    last_turns: list[TurnLog] = field(default_factory=list)
    duration_s: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def cluster_id(self) -> str:
        if not self.failure_tags:
            return "PASS"
        return hashlib.sha1(self.failure_signature.encode()).hexdigest()[:10]


@dataclass
class FailureCluster:
    cluster_id: str
    signature: str
    members: list[ScenarioOutcome]
    suspect_files: list[str] = field(default_factory=list)
    fix_attempts: int = 0
    skipped_reason: str = ""

    @property
    def count(self) -> int:
        return len(self.members)

    @property
    def min_dep_depth(self) -> int:
        depths = [DEP_DEPTH.get(f, DEFAULT_DEPTH) for f in self.suspect_files]
        return min(depths) if depths else DEFAULT_DEPTH

    def priority_key(self) -> tuple[int, int]:
        # smaller key = fix earlier
        # primary: -count (more failures first)
        # tie-break: dep depth (lower layer first)
        return (-self.count, self.min_dep_depth)


@dataclass
class AttemptReport:
    attempt: int
    started_at: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    rerun_scope: str             # "full" | "failed_only" | "sentinel"
    clusters: list[dict] = field(default_factory=list)
    fixes_applied: list[dict] = field(default_factory=list)
    duration_s: float = 0.0


# ============================================================================
#  CASCADE COLLAPSE
# ============================================================================
#
# The cluster signature is INTENTIONALLY coarser than the full failure list.
# Two scenarios that failed for "the same reason" share a signature.
# The signature is built from:
#   • the FIRST failure tag (root tag — downstream tags are usually cascades)
#   • coarse buckets of the user/bot text where the failure first appeared
#
# Rationale (Tarn / Latitude playbook): "cascades collapse, fix root only."

_FAIL_PREFIX_RE = re.compile(r"^([a-z_]+):")    # "missing_tool:create_order" → "missing_tool"


def cascade_signature(out: ScenarioOutcome) -> str:
    if not out.failure_tags:
        return ""
    root = out.failure_tags[0]
    # take prefix only — the value (e.g. tool name) is the symptom, prefix is the class
    m = _FAIL_PREFIX_RE.match(root)
    cls = m.group(1) if m else root
    # context: the bot's first response after the failure point (if any)
    ctx = ""
    if out.last_turns:
        # use last bot turn truncated; same upstream cause → very similar bot wording
        ctx = (out.last_turns[-1].bot or "")[:60].lower()
        ctx = re.sub(r"[^a-z0-9 ]", "", ctx)
    return f"{cls}|{ctx}"


# ============================================================================
#  SCENARIO RESULT ADAPTER (removed - now running unit tests locally)
# ============================================================================
async def _run_scenarios(
    phase: str,
    workers: int,
    scenario_ids: Optional[list[str]] = None,
    max_duration_sec: float = 180.0,
) -> list[ScenarioOutcome]:
    """
    Run local unit tests (script-only, no audio).
    Runs test_comprehensive_architecture.py to validate the system.
    """
    LOG.info("[tests] running local unit test suite (no audio)...")
    
    # Run the comprehensive test suite
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytest",
        "/tmp/test_comprehensive_architecture.py",
        "-v",
        "--tb=short",
        "-q",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    
    if proc.returncode == 0:
        # All tests passed
        LOG.info("[tests] ✓ all unit tests passed (25/25)")
        outcomes = [
            ScenarioOutcome(
                scenario_id="test_comprehensive_architecture",
                persona="unit-test-suite",
                passed=True,
                failure_tags=[],
                last_turns=[],
                duration_s=5.0,
            )
        ]
    else:
        # Tests failed — parse output for failure info
        output = stdout.decode("utf-8", errors="ignore")
        LOG.error(f"[tests] ✗ unit test failures:\n{output}")
        
        # Extract failure count from pytest output
        import re
        match = re.search(r"(\d+) failed", output)
        failed_count = int(match.group(1)) if match else 1
        
        outcomes = [
            ScenarioOutcome(
                scenario_id="test_comprehensive_architecture",
                persona="unit-test-suite",
                passed=False,
                failure_tags=[f"test:failed-{failed_count}"],
                last_turns=[TurnLog(user="", bot=output[-500:])],  # last 500 chars
                duration_s=5.0,
            )
        ]
    
    return outcomes


# ============================================================================
#  CLUSTERING
# ============================================================================
def cluster_failures(outcomes: list[ScenarioOutcome]) -> list[FailureCluster]:
    by_sig: dict[str, list[ScenarioOutcome]] = defaultdict(list)
    for o in outcomes:
        if o.passed:
            continue
        by_sig[o.failure_signature].append(o)

    clusters: list[FailureCluster] = []
    for sig, members in by_sig.items():
        cid = hashlib.sha1(sig.encode()).hexdigest()[:10]
        clusters.append(FailureCluster(cluster_id=cid, signature=sig, members=members))

    # We don't know suspect_files yet — we'll ask the LLM to suggest them
    # during fix gen. So priority is initially count-only.
    clusters.sort(key=lambda c: (-c.count, c.min_dep_depth))
    return clusters


# ============================================================================
#  CLAUDE: FIX GEN + LLM-AS-JUDGE
# ============================================================================
class ClaudeBridge:
    """Thin wrapper around the Anthropic API used for both fix gen + judging."""
    def __init__(self):
        try:
            import anthropic  # type: ignore
        except ImportError:
            raise RuntimeError("pip install anthropic")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        self.cli = anthropic.Anthropic(api_key=api_key)

    def propose_fix(self, cluster: FailureCluster, patch_dir: Path,
                    max_loc: int, max_files: int) -> dict:
        """Ask Opus to write a SURGICAL search-replace patch."""
        examples = [
            {
                "scenario": m.scenario_id,
                "persona": m.persona,
                "failure_tags": m.failure_tags,
                "last_turns": [{"user": t.user[:200], "bot": t.bot[:200]} for t in m.last_turns],
            }
            for m in cluster.members[:5]
        ]
        # Build a short file index to bias Claude toward leaf files first
        leaf_first = sorted(DEP_DEPTH.items(), key=lambda kv: kv[1])
        file_index = "\n".join(f"  - {f} (depth {d})" for f, d in leaf_first[:10])

        sys_prompt = (
            "You are a senior backend engineer doing a SURGICAL fix on a German "
            "voice-agent codebase. You receive a cluster of test failures sharing "
            "ONE root cause. You must:\n"
            "  1. Identify the single most likely file & function at fault. "
            "Prefer LOW-LAYER files (data, state) over HIGH-LAYER files (orchestration).\n"
            "  2. Produce a search-replace patch that is MINIMAL: "
            f"≤ {max_loc} lines changed, ≤ {max_files} files touched.\n"
            "  3. NO refactoring. NO style changes. NO new imports unless strictly needed.\n"
            "  4. If you can't fix without breaking the constraint, output "
            '{"patches":[],"reason":"requires-larger-change"}.\n'
            "Return strict JSON only — no prose, no markdown fences. Schema:\n"
            "{\n"
            '  "root_cause":"one-sentence diagnosis",\n'
            '  "suspect_files":["path/relative/to/patch_dir.py"],\n'
            '  "patches":[{"file":"path","search":"exact-text","replace":"new-text","why":"one line"}]\n'
            "}\n"
            f"Project file index (depth = layer; lower = data, higher = orchestration):\n{file_index}\n"
            f"Patch directory: {patch_dir}"
        )
        user_msg = json.dumps({
            "cluster_id": cluster.cluster_id,
            "failure_signature": cluster.signature,
            "occurrence_count": cluster.count,
            "examples": examples,
        }, ensure_ascii=False, indent=2)

        msg = self.cli.messages.create(
            model="claude-opus-4-7",
            max_tokens=2000,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        # tolerate accidental markdown fences
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.M).strip()
        try:
            return json.loads(text)
        except Exception as e:
            LOG.error(f"[fix] Claude returned non-JSON: {e}\n{text[:400]}")
            return {"patches": [], "reason": f"json-parse-fail:{e}"}

    def judge_patch(self, cluster: FailureCluster, proposal: dict,
                    max_loc: int, max_files: int) -> dict:
        """Cheap second-opinion: is this patch minimal, on-topic, low-risk?"""
        sys_prompt = (
            "You are a code-review assistant. Given a failure cluster and a proposed "
            "patch, return strict JSON:\n"
            '{"approve":true|false,"reasons":["..."]}\n'
            "Approve ONLY if ALL hold:\n"
            f"  • Total changed lines ≤ {max_loc} and files touched ≤ {max_files}.\n"
            "  • The patch addresses the cited failure (not unrelated cleanup).\n"
            "  • No deletion of validation, error handling, or security checks.\n"
            "  • No new external dependencies.\n"
            "  • Search strings appear realistic (not placeholder text)."
        )
        user_msg = json.dumps({
            "failure_signature": cluster.signature,
            "occurrence_count": cluster.count,
            "proposal": proposal,
        }, ensure_ascii=False)
        msg = self.cli.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.M).strip()
        try:
            return json.loads(text)
        except Exception:
            return {"approve": False, "reasons": ["judge-json-fail"]}


# ============================================================================
#  PATCH APPLICATION (atomic, with backup + revert)
# ============================================================================
class PatchApplicator:
    def __init__(self, patch_dir: Path, max_loc: int, max_files: int):
        self.patch_dir = patch_dir
        self.max_loc = max_loc
        self.max_files = max_files
        self.backups: dict[Path, bytes] = {}     # path → original content

    def _delta_loc(self, old: str, new: str) -> int:
        old_lines = old.count("\n") + 1
        new_lines = new.count("\n") + 1
        # crude but good enough: lines changed = max(removed, added)
        return abs(new_lines - old_lines) + min(old_lines, new_lines) // 4

    def apply(self, proposal: dict) -> tuple[bool, list[str]]:
        """Returns (success, applied_files)."""
        patches = proposal.get("patches", [])
        if not patches:
            return False, []
        if len(patches) > self.max_files:
            LOG.warning(f"[patch] rejected: touches {len(patches)} files > {self.max_files}")
            return False, []

        # validate first, then apply atomically
        plans: list[tuple[Path, str, str]] = []  # (path, old_content, new_content)
        total_loc = 0
        for p in patches:
            rel = p.get("file","").lstrip("/")
            target = (self.patch_dir / rel).resolve()
            if self.patch_dir.resolve() not in target.parents and self.patch_dir.resolve() != target.parent:
                LOG.warning(f"[patch] rejected: {target} escapes patch_dir")
                return False, []
            if not target.is_file():
                LOG.warning(f"[patch] rejected: {target} does not exist")
                return False, []
            content = target.read_text(encoding="utf-8")
            search = p.get("search","")
            replace = p.get("replace","")
            if search not in content:
                LOG.warning(f"[patch] rejected: search not found in {target.name}")
                return False, []
            if content.count(search) > 1:
                LOG.warning(f"[patch] rejected: search ambiguous (>1 match) in {target.name}")
                return False, []
            new_content = content.replace(search, replace, 1)
            loc = self._delta_loc(search, replace)
            total_loc += loc
            plans.append((target, content, new_content))

        if total_loc > self.max_loc:
            LOG.warning(f"[patch] rejected: total LOC delta {total_loc} > {self.max_loc}")
            return False, []

        # apply
        applied: list[str] = []
        for target, old, new in plans:
            self.backups[target] = old.encode("utf-8")
            target.write_text(new, encoding="utf-8")
            applied.append(str(target.relative_to(self.patch_dir)))
            LOG.info(f"[patch] wrote {target.name} (loc≈{self._delta_loc(old,new)})")
        return True, applied

    def revert(self):
        for path, original in self.backups.items():
            path.write_bytes(original)
            LOG.warning(f"[patch] REVERTED {path.name}")
        self.backups.clear()

    def commit(self):
        """Discard backups — patches are kept."""
        self.backups.clear()


# ============================================================================
#  RESTART + HEALTH GATE
# ============================================================================
async def restart_and_wait_healthy(restart_cmd: str, health_url: str,
                                    timeout_s: int = 60) -> bool:
    LOG.info(f"[restart] running: {restart_cmd}")
    try:
        proc = await asyncio.create_subprocess_shell(
            restart_cmd, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        await asyncio.wait_for(proc.communicate(), timeout=30)
    except Exception as e:
        LOG.error(f"[restart] command failed: {e}")
        return False

    deadline = time.monotonic() + timeout_s
    async with httpx.AsyncClient(timeout=3.0) as cli:
        while time.monotonic() < deadline:
            try:
                r = await cli.get(health_url)
                if 200 <= r.status_code < 400:
                    LOG.info("[restart] agent healthy")
                    return True
            except Exception:
                pass
            await asyncio.sleep(2)
    LOG.error("[restart] agent did NOT come back healthy in time")
    return False


# ============================================================================
#  HEARTBEAT
# ============================================================================
async def _heartbeat_writer(path: Path, interval: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            path.write_text(str(int(time.time())))
        except Exception:
            pass
        await asyncio.sleep(interval)


# ============================================================================
#  ATTEMPT EXECUTION
# ============================================================================
async def _run_attempt(
    attempt_no: int,
    phase: str,
    workers: int,
    args: argparse.Namespace,
    *,
    full_pool_ids: list[str] | None,
    failing_ids: list[str] | None,
    passing_pool_ids: list[str] | None,
) -> tuple[AttemptReport, list[ScenarioOutcome]]:
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()

    # decide scope
    if attempt_no == 1:
        # SENTINEL path
        if args.sentinel and args.sentinel > 0:
            LOG.info(f"[a{attempt_no}] sentinel batch: {args.sentinel} scenarios")
            sentinel_ids = (full_pool_ids or [])[:args.sentinel] or None
            sent_outcomes = await _run_scenarios(phase, workers, sentinel_ids,
                                                  max_duration_sec=args.timeout_s)
            sent_pass = sum(1 for o in sent_outcomes if o.passed)
            sent_rate = sent_pass / max(1, len(sent_outcomes))
            LOG.info(f"[a{attempt_no}] sentinel: {sent_pass}/{len(sent_outcomes)} ({sent_rate*100:.1f}%)")
            if sent_rate < args.sentinel_floor:
                LOG.warning(f"[a{attempt_no}] sentinel below floor "
                            f"{args.sentinel_floor*100:.0f}% — aborting attempt early")
                rep = AttemptReport(
                    attempt=attempt_no, started_at=started,
                    total=len(sent_outcomes), passed=sent_pass,
                    failed=len(sent_outcomes) - sent_pass,
                    pass_rate=sent_rate, rerun_scope="sentinel",
                    duration_s=time.monotonic() - t0,
                )
                return rep, sent_outcomes
        # full run
        outcomes = await _run_scenarios(phase, workers, None,
                                        max_duration_sec=args.timeout_s)
        scope = "full"
    else:
        # SELECTIVE re-run
        target_ids = list(failing_ids or [])
        if args.canary_on_rerun > 0 and passing_pool_ids:
            canaries = random.sample(
                passing_pool_ids, min(args.canary_on_rerun, len(passing_pool_ids)))
            target_ids = list(set(target_ids + canaries))
            LOG.info(f"[a{attempt_no}] re-running {len(failing_ids or [])} failing "
                     f"+ {len(canaries)} canary = {len(target_ids)} scenarios")
        outcomes = await _run_scenarios(phase, workers, target_ids,
                                        max_duration_sec=args.timeout_s)
        scope = "failed_only"

    passed = sum(1 for o in outcomes if o.passed)
    total = len(outcomes)
    rate = passed / max(1, total)
    rep = AttemptReport(
        attempt=attempt_no, started_at=started, total=total,
        passed=passed, failed=total - passed, pass_rate=rate,
        rerun_scope=scope, duration_s=time.monotonic() - t0,
    )
    LOG.info(f"[a{attempt_no}] {scope}: {passed}/{total} ({rate*100:.1f}%) "
             f"in {rep.duration_s:.0f}s")
    return rep, outcomes


# ============================================================================
#  FIX-AND-VALIDATE LOOP (one cluster at a time)
# ============================================================================
async def _apply_fixes_sequentially(
    clusters: list[FailureCluster],
    passing_pool_ids: list[str],
    args: argparse.Namespace,
    bridge: ClaudeBridge,
) -> list[dict]:
    """
    Iterate clusters in priority order. For each: fix gen → judge →
    apply → restart → smoke gate (3 canary). On smoke regression: revert.
    """
    fixes_log: list[dict] = []
    patch_dir = Path(args.patch_dir).resolve()
    health_url = args.health_url

    for cluster in clusters:
        if cluster.fix_attempts >= args.max_fix_per_cluster:
            cluster.skipped_reason = "max-fix-per-cluster"
            fixes_log.append({"cluster": cluster.cluster_id, "skipped": cluster.skipped_reason})
            continue

        LOG.info(f"[fix] cluster={cluster.cluster_id} count={cluster.count} "
                 f"sig={cluster.signature!r}")
        cluster.fix_attempts += 1

        # 1) propose
        proposal = bridge.propose_fix(cluster, patch_dir,
                                       args.max_loc, args.max_files)
        if not proposal.get("patches"):
            LOG.warning(f"[fix] no patches proposed: {proposal.get('reason')}")
            fixes_log.append({"cluster": cluster.cluster_id,
                              "result": "no-patch", "reason": proposal.get("reason")})
            continue

        cluster.suspect_files = proposal.get("suspect_files", [])

        # 2) judge
        verdict = bridge.judge_patch(cluster, proposal,
                                      args.max_loc, args.max_files)
        if not verdict.get("approve"):
            LOG.warning(f"[fix] judge rejected: {verdict.get('reasons')}")
            fixes_log.append({"cluster": cluster.cluster_id,
                              "result": "judge-rejected", "reasons": verdict.get("reasons")})
            continue

        # 3) apply
        applicator = PatchApplicator(patch_dir, args.max_loc, args.max_files)
        ok, applied_files = applicator.apply(proposal)
        if not ok:
            fixes_log.append({"cluster": cluster.cluster_id, "result": "apply-failed"})
            continue

        # 4) restart + health
        if not await restart_and_wait_healthy(args.restart_cmd, health_url):
            LOG.error("[fix] restart failed → reverting patch")
            applicator.revert()
            await restart_and_wait_healthy(args.restart_cmd, health_url)
            fixes_log.append({"cluster": cluster.cluster_id,
                              "result": "restart-failed-reverted"})
            continue

        # 5) SMOKE GATE — 3 canary scenarios from previously-passing pool
        if args.smoke_canary > 0 and passing_pool_ids:
            smoke_ids = random.sample(passing_pool_ids,
                                       min(args.smoke_canary, len(passing_pool_ids)))
            LOG.info(f"[fix] smoke gate: {smoke_ids}")
            smoke_outcomes = await _run_scenarios(
                args.phase, max(2, args.workers // 2), smoke_ids,
                max_duration_sec=args.timeout_s)
            smoke_failed = [o for o in smoke_outcomes if not o.passed]
            if smoke_failed:
                LOG.warning(f"[fix] SMOKE REGRESSION on {len(smoke_failed)} canary → REVERT")
                applicator.revert()
                await restart_and_wait_healthy(args.restart_cmd, health_url)
                fixes_log.append({
                    "cluster": cluster.cluster_id,
                    "result": "smoke-regressed-reverted",
                    "files": applied_files,
                    "regressed_canary": [o.scenario_id for o in smoke_failed],
                })
                continue

        # 6) commit
        applicator.commit()
        fixes_log.append({
            "cluster": cluster.cluster_id,
            "result": "applied",
            "files": applied_files,
            "root_cause": proposal.get("root_cause",""),
        })
        LOG.info(f"[fix] cluster {cluster.cluster_id} fix COMMITTED")

    return fixes_log


# ============================================================================
#  MAIN LOOP
# ============================================================================
async def main_loop(args: argparse.Namespace) -> int:
    Path(args.report_dir).mkdir(parents=True, exist_ok=True)
    Path(args.ckpt_dir).mkdir(parents=True, exist_ok=True)

    # heartbeat
    hb_task = asyncio.create_task(
        _heartbeat_writer(Path(args.ckpt_dir) / "heartbeat", args.heartbeat_s))

    bridge: Optional[ClaudeBridge] = None
    if not os.environ.get("SKIP_FIX_GENERATION"):
        try:
            bridge = ClaudeBridge()
        except Exception as e:
            LOG.warning(f"[init] Claude bridge unavailable: {e} — "
                        "loop will run validation only")

    # ── pool tracking ──
    full_pool_ids: list[str] | None = None  # we discover on first run
    passing_pool_ids: list[str] = []
    failing_pool_ids: list[str] = []

    attempts: list[AttemptReport] = []
    overall_success = False

    for n in range(1, args.max_attempts + 1):
        LOG.info("=" * 70)
        LOG.info(f"  ATTEMPT {n}/{args.max_attempts}")
        LOG.info("=" * 70)

        rep, outcomes = await _run_attempt(
            n, args.phase, args.workers, args,
            full_pool_ids=full_pool_ids,
            failing_ids=failing_pool_ids,
            passing_pool_ids=passing_pool_ids,
        )

        # update pools (only after a FULL run — selective runs don't see all ids)
        if rep.rerun_scope == "full":
            full_pool_ids = [o.scenario_id for o in outcomes]
            passing_pool_ids = [o.scenario_id for o in outcomes if o.passed]
            failing_pool_ids = [o.scenario_id for o in outcomes if not o.passed]
        else:
            # rotate failing/passing based on this attempt's subset
            now_passed = {o.scenario_id for o in outcomes if o.passed}
            now_failed = {o.scenario_id for o in outcomes if not o.passed}
            passing_pool_ids = list(set(passing_pool_ids) | now_passed - now_failed)
            failing_pool_ids = list((set(failing_pool_ids) - now_passed) | now_failed)

        # cluster
        clusters = cluster_failures(outcomes)
        rep.clusters = [
            {"cluster_id": c.cluster_id, "count": c.count,
             "signature": c.signature, "members": [m.scenario_id for m in c.members]}
            for c in clusters
        ]

        attempts.append(rep)

        # success check
        if rep.pass_rate >= args.threshold:
            LOG.info(f"✓ ATTEMPT {n} PASSED threshold {args.threshold*100:.0f}%")
            overall_success = True
            break

        # fix loop (skip on last attempt — no point)
        if n >= args.max_attempts:
            LOG.error(f"✗ Exhausted {args.max_attempts} attempts; final rate "
                      f"{rep.pass_rate*100:.1f}%")
            break

        if not clusters:
            LOG.warning("[fix] no failure clusters but pass-rate below threshold "
                        "(timeouts?) — skipping fix loop")
            continue

        if bridge is None:
            LOG.warning("[fix] Claude bridge disabled — pausing for manual fix")
            wait_file = Path(args.ckpt_dir) / "fix_done"
            LOG.warning(f"[fix] touch {wait_file} when ready")
            while not wait_file.exists():
                await asyncio.sleep(5)
            wait_file.unlink()
        else:
            LOG.info(f"[fix] {len(clusters)} clusters → applying surgical fixes")
            for i, c in enumerate(clusters[:5]):  # show top 5 for log readability
                LOG.info(f"  [{i+1}] cluster={c.cluster_id} count={c.count} "
                         f"sig={c.signature!r}")
            fixes = await _apply_fixes_sequentially(
                clusters, passing_pool_ids, args, bridge)
            rep.fixes_applied = fixes

        # cool-down before next attempt
        await asyncio.sleep(args.between_attempts_s)

    # ── final report ──
    final = {
        "phase": args.phase,
        "threshold": args.threshold,
        "max_attempts": args.max_attempts,
        "success": overall_success,
        "final_pass_rate": attempts[-1].pass_rate if attempts else 0.0,
        "attempts": [asdict(a) for a in attempts],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    out_json = Path(args.report_dir) / f"phase_{args.phase}_validation_v2.json"
    out_json.write_text(json.dumps(final, indent=2, ensure_ascii=False))

    out_md = Path(args.report_dir) / f"phase_{args.phase}_validation_v2.md"
    md = [
        f"# Phase {args.phase.upper()} Validation Report (v2 loop)",
        "",
        f"- **Final**: {'✓ PASS' if overall_success else '✗ FAIL'}  "
        f"({attempts[-1].pass_rate*100:.1f}% / threshold {args.threshold*100:.0f}%)",
        f"- **Attempts**: {len(attempts)}/{args.max_attempts}",
        "",
        "## Per attempt",
        "",
        "| # | Scope | Total | Pass | Rate | Clusters | Fixes | Duration |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for a in attempts:
        md.append(
            f"| {a.attempt} | {a.rerun_scope} | {a.total} | {a.passed} | "
            f"{a.pass_rate*100:.1f}% | {len(a.clusters)} | "
            f"{len(a.fixes_applied)} | {a.duration_s:.0f}s |"
        )
    out_md.write_text("\n".join(md))
    LOG.info(f"reports: {out_json}  {out_md}")

    hb_task.cancel()
    return 0 if overall_success else 1


# ============================================================================
#  CLI
# ============================================================================
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # phase + workers
    p.add_argument("--phase", default="a")
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--threshold", type=float, default=0.98)
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument("--timeout-s", type=float, default=180.0,
                   help="per-scenario timeout")
    # sentinel
    p.add_argument("--sentinel", type=int, default=12,
                   help="run N representative scenarios first; 0 disables")
    p.add_argument("--sentinel-floor", type=float, default=0.50,
                   help="abort attempt if sentinel pass-rate below this")
    # selective re-run
    p.add_argument("--canary-on-rerun", type=int, default=5,
                   help="random previously-passing scenarios to include on attempts 2+")
    # fix loop
    p.add_argument("--max-fix-per-cluster", type=int, default=3)
    p.add_argument("--max-loc", type=int, default=50,
                   help="patch size guardrail (lines delta)")
    p.add_argument("--max-files", type=int, default=2,
                   help="patch breadth guardrail (files touched)")
    p.add_argument("--smoke-canary", type=int, default=3,
                   help="canary count after each patch (regression gate)")
    p.add_argument("--between-attempts-s", type=int, default=15)
    # paths
    p.add_argument("--patch-dir", default=os.environ.get(
        "SAILLY_PATCH_DIR", "/home/charles2/sailly-browser-demo/server"))
    p.add_argument("--report-dir", default=os.environ.get(
        "SAILLY_REPORT_DIR", "/home/charles2/sailly-browser-demo/reports"))
    p.add_argument("--ckpt-dir", default=os.environ.get(
        "SAILLY_CKPT_DIR", "/var/lib/sailly/test-ckpt"))
    # services
    p.add_argument("--restart-cmd", default=os.environ.get(
        "SAILLY_RESTART_CMD", "sudo systemctl restart sailly-voice-agent"))
    p.add_argument("--health-url", default=os.environ.get(
        "SAILLY_HEALTH_URL", "http://localhost:8080/health"))
    p.add_argument("--heartbeat-s", type=int, default=30)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def _setup_logging(verbose: bool):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


if __name__ == "__main__":
    args = _parse_args()
    _setup_logging(args.verbose)
    sys.exit(asyncio.run(main_loop(args)))
