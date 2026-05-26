"""
validation_heal_loop.py — Self-healing validation + auto-deploy pipeline.

CORRECT ARCHITECTURE:
─────────────────────────────────────────────────────────────────────────────
Phase A  [1× at start only]
  Full 280-scenario validation → get baseline pass rate + list of failures.
  OR: load from an existing run with --skip-full-validation --results-dir PATH.

Fix Loop  [up to 8 iterations]
  Each iteration targets only the STILL-FAILING buckets:

  Phase C: Claude Sonnet 4.6 analyzes the failing buckets and proposes a patch.
           Diff gate: max 50 lines changed.  Scope limits: no sacred functions.

  Phase D: fix_validation_loop.py runs targeted scenarios for ONLY the failing buckets.
           Gated 3-step structure per bucket (3 steps × 10 different scenarios = 30 per bucket):
             Step 1 → 10 scenarios  (must pass threshold to proceed to Step 2)
             Step 2 → 10 different scenarios  (combined 1+2 must pass to proceed to Step 3)
             Step 3 → 10 different scenarios  (combined 1+2+3 must pass → VALIDATED)
             If Step 1 fails → retry up to 3 times, then STOP (don't waste time on Step 2).
             Up to 3 attempts (retries) per bucket per iteration.
           Buckets that pass their threshold → marked RESOLVED, skipped next iteration.
           Buckets that fail all 3 retries → still failing, queued for next iteration.

  Iteration ends when:
    • All buckets resolved → exit early
    • OR max 8 iterations exhausted

Phase E  [1× at end only]
  Full 280-scenario regression check (run ONCE regardless of how many iterations).
  If pass_rate >= 95% → deploy to demo browser (with 30-min canary window).
  If pass_rate <  95% → abort, log for manual review.

Deploy  [only if Phase E passes]
  Backup → copy brain files → fix imports → clear pycache → restart services
  → 5-scenario smoke test → 30-minute canary window → auto-rollback on error.
─────────────────────────────────────────────────────────────────────────────

Usage:
  # Full run (Phase A fresh):
  python -m server.training.validation_heal_loop

  # Skip Phase A — use existing 280-scenario results:
  python -m server.training.validation_heal_loop \\
      --skip-full-validation --results-dir /tmp/ab_test_results

  # Dry run (no deploy):
  python -m server.training.validation_heal_loop --dry-run \\
      --skip-full-validation --results-dir /tmp/ab_test_results
"""

import argparse
import asyncio
import fcntl
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ── Process control (signal-based pause/resume/stop) ──────────────────────────

class _LoopController:
    """Thread-safe controller for pause/resume/graceful-stop via OS signals."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default

    # --- public API -----------------------------------------------------------

    @property
    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def pause_checkpoint(self, label: str = ""):
        """Call this at safe checkpoints to honour a pause request."""
        if not self._pause_event.is_set():
            logger.info(f"[Control] Paused{' at: ' + label if label else ''}. Send SIGCONT to resume.")
            self._pause_event.wait()   # block until SIGCONT
            logger.info("[Control] Resumed.")

    def check_stop(self, label: str = ""):
        """Raise SystemExit if a stop was requested."""
        self.pause_checkpoint(label)
        if self._stop_event.is_set():
            raise SystemExit(f"Validation loop stopped at: {label}")

    # --- signal handlers (installed once at startup) --------------------------

    def setup(self):
        signal.signal(signal.SIGTERM, self._on_stop)
        signal.signal(signal.SIGUSR1, self._on_stop)   # alias for convenience
        signal.signal(signal.SIGCONT, self._on_cont)
        # SIGSTOP cannot be caught in Python; the OS suspends the process directly.
        # The dashboard sends SIGSTOP to pause and SIGCONT to resume, which works
        # at the OS level without needing a Python handler for SIGSTOP itself.
        logger.info("[Control] Signal handlers installed (SIGTERM→stop, SIGUSR1→stop, SIGCONT→resume).")

    def _on_stop(self, signum, frame):
        logger.warning(f"[Control] Received signal {signum} — requesting graceful stop.")
        self._stop_event.set()
        self._pause_event.set()   # unblock any waiting pause so stop is noticed

    def _on_cont(self, signum, frame):
        logger.info("[Control] Received SIGCONT — resuming.")
        self._pause_event.set()


_controller = _LoopController()

# Control file path — the dashboard API writes this as an alternative to signals
CONTROL_FILE = Path("/tmp/validation_runs/control_signal.json")


def _check_control_file():
    """Check if the dashboard wrote a control file and act on it."""
    global _controller
    if not CONTROL_FILE.exists():
        return
    try:
        data = json.loads(CONTROL_FILE.read_text())
        action = data.get("action", "")
        if action == "stop":
            logger.warning("[Control] Stop requested via control file.")
            _controller._stop_event.set()
            _controller._pause_event.set()
            CONTROL_FILE.unlink(missing_ok=True)
    except Exception:
        pass

# ── Configuration ─────────────────────────────────────────────────────────────

PASS_THRESHOLD = 0.95          # 95% required on the final full-280 check
MAX_ITERATIONS = 5             # Max Claude fix iterations (each targets failing buckets)
COST_CEILING_USD = 50.0        # Abort the fix loop if API spend exceeds this
CANARY_WINDOW_SECONDS = 1800   # 30-minute post-deploy monitoring window
FLAKY_CONFIRMATION_RUNS = 2    # Extra runs per failure for flaky filter (in retry mode)

RUNS_ROOT             = Path("/tmp/validation_runs")
VALIDATION_OUTPUT_DIR = Path("/tmp/ab_heal_results")
FIX_VAL_OUTPUT_DIR    = Path("/tmp/ab_fix_validation")
HEAL_HISTORY_PATH     = Path("/home/charles2/sailly-google-fork/heal_history.json")

TRAINING_DIR   = Path("/home/charles2/sailly-google-fork/server/training")
DEMO_BRAIN_DIR = Path("/home/charles2/sailly-browser-demo/server/brain")
DEMO_BACKUP_BASE = DEMO_BRAIN_DIR / "_backups"
DEMO_BRAIN_SERVICE_DIR = Path("/home/charles2/sailly-browser-demo")
DEMO_BRAIN_PYTHON = "/home/charles2/sailly-browser-demo/venv/bin/python3"

# Blue-green deployment state
ACTIVE_PORT_FILE       = Path("/tmp/sailly_demo_active_port")
NGINX_UPSTREAM_CONF    = Path("/etc/nginx/conf.d/sailly_demo_upstream.conf")
DEMO_8081_SERVICE      = "sailly-browser-demo-8081"

# Status / availability files (served at /validation/)
STATUS_FILE       = RUNS_ROOT / "heal_loop_status.json"
AVAILABILITY_FILE = RUNS_ROOT / "demo_availability.json"

# Lock file (prevents overlapping runs from cron + manual trigger)
LOCK_FILE = Path("/tmp/validation_heal_loop.lock")

# Slack webhook URL — set via SLACK_WEBHOOK_URL env variable (optional)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# Backup retention: keep this many deploy backups
BACKUP_KEEP_COUNT = 5

# Production failure capture directory
PROD_FAILURES_DIR = RUNS_ROOT / "production_failures"

DEMO_BRAIN_FILES = [
    "adk_turn_processor.py", "conversation_nodes.py", "node_manager.py",
    "conversation_state.py", "memory_manager.py", "response_variations.py",
    "tier2_runner.py", "call_auditor_de.py", "cost_tracker.py",
    "audio_injector.py", "conversation_loop.py", "adk_runner.py", "__init__.py",
]

PYTHON = str(Path("/home/charles2/sailly-google-fork/.venv/bin/python3"))


# ── Heal history ──────────────────────────────────────────────────────────────

def _load_history() -> dict:
    if HEAL_HISTORY_PATH.exists():
        try:
            return json.loads(HEAL_HISTORY_PATH.read_text())
        except Exception:
            pass
    return {"runs": []}


def _save_history(history: dict) -> None:
    HEAL_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEAL_HISTORY_PATH.write_text(json.dumps(history, indent=2))


# ── Phase A: Full 280-scenario validation (runs ONCE) ─────────────────────────

def _clear_checkpoint(output_dir: Path) -> None:
    """Delete the ab_test_loop checkpoint so a fresh run starts from scratch.

    The checkpoint persists between runs in the same output directory and causes
    Phase A/E to skip all previously-completed scenarios, producing 0 results and
    a '--' pass rate that crashes the float parser.
    """
    checkpoint = output_dir / "checkpoint.json"
    if checkpoint.exists():
        checkpoint.unlink()
        logger.info(f"[HealLoop] Cleared checkpoint from previous run in {output_dir}")


def _parse_pass_rate(raw: str) -> float:
    """Parse a pass rate string like '88.6%' or '--' safely."""
    if not raw or raw == "--":
        return 0.0
    try:
        return float(str(raw).rstrip("%")) / 100
    except (ValueError, AttributeError):
        return 0.0


async def _run_full_validation(output_dir: Path, workers: int = 20) -> dict:
    """Run the full 280-scenario ab_test_loop and return summary."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Always clear checkpoint — a fresh Phase A/E must run all 280 scenarios,
    # not skip ones "completed" in a previous run in this directory.
    _clear_checkpoint(output_dir)

    cmd = [
        PYTHON, "-m", "server.training.ab_test_loop",
        "--phases", "1", "2", "3", "4",
        "--adk-only",
        "--workers", str(workers),
        "--timeout", "360",
        "--output", str(output_dir),
    ]
    logger.info(f"[HealLoop] Full 280-scenario validation → {output_dir}")
    env = {**os.environ, "PYTHONPATH": str(TRAINING_DIR.parent.parent), "TTS_ENGINE": "gemini-flash"}

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(TRAINING_DIR.parent.parent),
        env=env,
    )
    _last_watchdog_280 = asyncio.get_event_loop().time()
    async for line in proc.stdout:
        decoded = line.decode("utf-8", errors="replace").rstrip()
        if any(k in decoded for k in ["PASS", "FAIL", "pass_rate", "Elapsed", "ERROR", "ADK", "%", "Checkpoint"]):
            logger.info(f"  [280] {decoded}")
        _now = asyncio.get_event_loop().time()
        if _now - _last_watchdog_280 >= 60:
            _sd_watchdog()
            _last_watchdog_280 = _now
    await proc.wait()

    results_path = output_dir / "ab_results.json"
    if not results_path.exists():
        raise RuntimeError(f"Validation produced no ab_results.json in {output_dir}")

    data = json.loads(results_path.read_text())
    summary = data.get("summary", {})
    results = data.get("results", [])

    # Guard: if 0 scenarios ran (e.g. all skipped), raise so the caller knows
    total = summary.get("total", len(results))
    if total == 0:
        raise RuntimeError(
            f"Phase A/E produced 0 scenarios in {output_dir}. "
            "Checkpoint may not have been cleared. Check ab_live_status.json."
        )

    pass_rate = _parse_pass_rate(summary.get("one_live_rate", "0%"))
    return {
        "pass_rate": pass_rate,
        "passes": summary.get("one_live_passes", 0),
        "total": total,
        "cost_usd": summary.get("one_live_cost_usd_total", 0.0),
        "results": results,
    }


def _load_existing_results(results_dir: Path) -> dict:
    """Load Phase A results from an existing ab_results.json."""
    results_path = results_dir / "ab_results.json"
    if not results_path.exists():
        raise FileNotFoundError(
            f"No ab_results.json found at {results_path}.\n"
            f"Point --results-dir to a directory that contains ab_results.json, "
            "or remove --skip-full-validation to run Phase A fresh."
        )
    data = json.loads(results_path.read_text())
    summary = data.get("summary", {})
    pass_rate = _parse_pass_rate(summary.get("one_live_rate", "0%"))
    failures = [r for r in data.get("results", []) if not r.get("one_live_pass", True)]

    # Copy results to VALIDATION_OUTPUT_DIR so ab_test_loop --retry-failed can find them
    VALIDATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if results_dir.resolve() != VALIDATION_OUTPUT_DIR.resolve():
        shutil.copyfile(str(results_path), str(VALIDATION_OUTPUT_DIR / "ab_results.json"))
        live = results_dir / "ab_live_status.json"
        if live.exists():
            shutil.copyfile(str(live), str(VALIDATION_OUTPUT_DIR / "ab_live_status.json"))

    logger.info(
        f"[PhaseA] Loaded existing results: "
        f"{summary.get('one_live_passes', 0)}/{summary.get('total', 0)} passed "
        f"({pass_rate:.1%}), {len(failures)} failures"
    )
    return {
        "pass_rate": pass_rate,
        "passes": summary.get("one_live_passes", 0),
        "total": summary.get("total", 0),
        "cost_usd": 0.0,  # Already paid for
        "results": data.get("results", []),
    }


# ── Phase D: fix_validation_loop (targeted, runs per iteration) ───────────────

async def _run_fix_validation(
    failed_ids: List[str],
    workers: int = 20,
    iteration: int = 0,
) -> dict:
    """
    Phase D: Run fix_validation_loop targeting ONLY the failed scenario IDs.

    Each bucket gets:
      Step 1: 10 scenarios (always runs)
      Step 2: 10 more scenarios (always runs)
      Step 3: 10 more scenarios (runs if combined 1+2 < threshold)
      Up to 3 retries per bucket if all 3 steps fail.

    Returns dict with:
      - passed_buckets: number of buckets that passed their threshold
      - failed_buckets: list of bucket names still failing
      - total_buckets: total buckets in scope
      - bucket_details: per-bucket results
      - cost_usd: estimated API cost
    """
    iter_output = FIX_VAL_OUTPUT_DIR / f"iter_{iteration}"
    iter_output.mkdir(parents=True, exist_ok=True)

    # Write failed IDs for fix_validation_loop to load
    failed_ids_path = iter_output / "failed_ids.json"
    failed_ids_path.write_text(json.dumps(failed_ids))

    cmd = [
        PYTHON, "-m", "server.training.fix_validation_loop",
        "--output", str(iter_output),
        "--workers", str(workers),
        "--failed-ids-file", str(failed_ids_path),
        "--concurrent-buckets", "2",
    ]
    logger.info(
        f"[PhaseD] fix_validation_loop iteration {iteration}: "
        f"{len(failed_ids)} failed scenarios targeted"
    )
    env = {**os.environ, "PYTHONPATH": str(TRAINING_DIR.parent.parent), "TTS_ENGINE": "gemini-flash"}

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(TRAINING_DIR.parent.parent),
        env=env,
    )
    _last_watchdog = asyncio.get_event_loop().time()
    async for line in proc.stdout:
        decoded = line.decode("utf-8", errors="replace").rstrip()
        if any(k in decoded for k in ["Bucket", "Step", "PASS", "FAIL", "threshold",
                                       "Tier", "ERROR", "✅", "❌", "VALIDATED", "UNRESOLVED",
                                       "attempt", "Attempt", "Traceback", "SyntaxError",
                                       "ImportError", "Exception", "workers", "concurrent"]):
            logger.info(f"  [fix-val] {decoded}")
        # Ping systemd watchdog every 60s while subprocess is running
        _now = asyncio.get_event_loop().time()
        if _now - _last_watchdog >= 60:
            _sd_watchdog()
            _last_watchdog = _now
    await proc.wait()

    if proc.returncode != 0:
        logger.error(
            f"[PhaseD] fix_validation_loop exited with code {proc.returncode} "
            f"(likely a crash/syntax error) — skipping iteration, treating as all-failed"
        )
        return {
            "passed_buckets": 0, "failed_buckets": [],
            "total_buckets": 0, "bucket_details": [], "cost_usd": 0.0,
        }

    # Parse bucket results from fix_validation_state.json
    state_path = iter_output / "fix_validation_state.json"
    if not state_path.exists():
        logger.warning(f"[PhaseD] No state file at {state_path} — assuming all failed")
        return {
            "passed_buckets": 0, "failed_buckets": [], "total_buckets": 0,
            "bucket_details": [], "cost_usd": 0.0,
        }

    # Guard against stale state files from a previous run
    state = json.loads(state_path.read_text())
    if state.get("status") != "finished":
        logger.warning(f"[PhaseD] State file status={state.get('status')!r} (not 'finished') — treating as all-failed")
        return {
            "passed_buckets": 0, "failed_buckets": [], "total_buckets": 0,
            "bucket_details": [], "cost_usd": 0.0,
        }

    buckets = state.get("buckets", [])

    passed = [b for b in buckets if b.get("status") == "validated"]
    failed = [b for b in buckets if b.get("status") not in ("validated", "pending")]
    failed_names = [b.get("name", "?") for b in failed]

    cost = 0.0
    for b in buckets:
        for r in b.get("step1_results", []) + b.get("step2_results", []):
            cost += r.get("cost_usd", r.get("one_live_cost_usd", 0.0))

    logger.info(
        f"[PhaseD] Iteration {iteration} result: "
        f"{len(passed)}/{len(buckets)} buckets passed. "
        f"Still failing: {failed_names or 'none'}"
    )

    return {
        "passed_buckets": len(passed),
        "failed_buckets": failed_names,
        "total_buckets": len(buckets),
        "bucket_details": buckets,
        "cost_usd": cost,
    }


# ── Status & availability files ───────────────────────────────────────────────

def _write_status(
    running: bool,
    phase: str = "",
    last_result: str = "",
    last_pass_rate: float = 0.0,
    last_completed: str = "",
    started_at: str = "",
    paused: bool = False,
) -> None:
    """Write /tmp/validation_runs/heal_loop_status.json — polled by the dashboard sidebar badge."""
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    next_sched = _get_next_scheduled()
    payload: dict = {
        "running": running,
        "paused": paused,
        "phase": phase,
        "started_at": started_at,
        "last_completed": last_completed,
        "last_result": last_result,
        "last_pass_rate": last_pass_rate,
        "next_scheduled": next_sched,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        STATUS_FILE.write_text(json.dumps(payload, indent=2))
    except Exception as e:
        logger.warning(f"[Status] Could not write status file: {e}")


def _write_availability(
    validation_running: bool,
    phase: str = "",
    estimated_end: str = "",
    iteration: int = 0,
    max_iterations: int = MAX_ITERATIONS,
) -> None:
    """Write /tmp/validation_runs/demo_availability.json — polled by demo-call page."""
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "validation_running": validation_running,
        "phase": phase,
        "estimated_end": estimated_end,
        "iteration": iteration,
        "max_iterations": max_iterations,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        AVAILABILITY_FILE.write_text(json.dumps(payload, indent=2))
    except Exception as e:
        logger.warning(f"[Status] Could not write availability file: {e}")


def _get_next_scheduled() -> str:
    """Ask systemd for the next fire time of the validation timer (returns ISO string or '')."""
    try:
        result = subprocess.run(
            ["systemctl", "show", "sailly-validation.timer",
             "--property=NextElapseUSecRealtime", "--no-pager"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "NextElapseUSecRealtime=" in line:
                val = line.split("=", 1)[1].strip()
                # Systemd may return either a raw usec integer or a human-readable string
                if val.isdigit():
                    usec = int(val)
                    if usec > 0:
                        ts = datetime.fromtimestamp(usec / 1_000_000, tz=timezone.utc)
                        return ts.isoformat()
                else:
                    # Parse human-readable format: "Thu 2026-04-09 21:30:00 UTC"
                    from email.utils import parsedate_to_datetime
                    # Strip day-of-week prefix if present
                    parts = val.split(" ", 1)
                    date_str = parts[1] if len(parts) == 2 and len(parts[0]) <= 3 else val
                    import datetime as _dt
                    try:
                        # Format: "2026-04-09 21:30:00 UTC"
                        ts = _dt.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %Z")
                        ts = ts.replace(tzinfo=timezone.utc)
                        return ts.isoformat()
                    except ValueError:
                        pass
    except Exception:
        pass
    return ""


# ── Slack notifications ────────────────────────────────────────────────────────

def _notify_slack(message: str, level: str = "info") -> None:
    """Send a message to Slack via incoming webhook. Silently ignored if no webhook configured."""
    if not SLACK_WEBHOOK_URL:
        return
    emoji = {"info": ":information_source:", "ok": ":white_check_mark:",
             "warn": ":warning:", "error": ":x:"}.get(level, ":bell:")
    body = json.dumps({"text": f"{emoji} *Sailly Validation* — {message}"}).encode()
    try:
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL, data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logger.warning(f"[Slack] Notification failed: {e}")


# ── Backup retention ───────────────────────────────────────────────────────────

def _cleanup_old_backups() -> None:
    """Keep the most recent BACKUP_KEEP_COUNT deploy backups; delete the rest."""
    if not DEMO_BACKUP_BASE.exists():
        return
    backups = sorted(
        [d for d in DEMO_BACKUP_BASE.iterdir() if d.is_dir() and d.name.startswith("backup_")],
        key=lambda d: d.name,
    )
    to_delete = backups[:-BACKUP_KEEP_COUNT] if len(backups) > BACKUP_KEEP_COUNT else []
    for d in to_delete:
        shutil.rmtree(str(d), ignore_errors=True)
        logger.info(f"[Backup] Removed old backup: {d.name}")
    if to_delete:
        logger.info(f"[Backup] Kept {min(len(backups), BACKUP_KEEP_COUNT)} backups, removed {len(to_delete)}")


# ── Blue-green port management ─────────────────────────────────────────────────

def _get_active_port() -> int:
    try:
        return int(ACTIVE_PORT_FILE.read_text().strip())
    except Exception:
        return 8080


def _set_active_port(port: int) -> None:
    ACTIVE_PORT_FILE.write_text(str(port))


def _check_healthz(port: int) -> bool:
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2)
        return resp.status == 200
    except Exception:
        return False


def _wait_for_healthz(port: int, timeout: int = 30) -> bool:
    for _ in range(timeout):
        if _check_healthz(port):
            return True
        time.sleep(1)
    return False


def _get_active_ws_count(port: int) -> int:
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2)
        data = json.loads(resp.read())
        return int(data.get("active_ws_connections", 0))
    except Exception:
        return 0


def _wait_for_ws_drain(port: int, timeout: int = 60) -> None:
    """Wait up to `timeout` seconds for all WebSocket sessions on `port` to end gracefully."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        count = _get_active_ws_count(port)
        if count == 0:
            logger.info(f"[Deploy] Port :{port} — all WebSocket sessions drained")
            return
        remaining = int(deadline - time.time())
        logger.info(f"[Deploy] Draining :{port} — {count} active call(s) ({remaining}s remaining)")
        time.sleep(5)
    logger.warning(f"[Deploy] Drain timeout on :{port} — proceeding (active calls will be interrupted)")


def _switch_nginx_upstream(port: int) -> None:
    """Write the nginx upstream snippet and gracefully reload nginx."""
    content = f"upstream sailly_demo {{ server 127.0.0.1:{port}; }}\n"
    # Write via sudo tee since /etc/nginx/conf.d/ is root-owned
    proc = subprocess.run(
        ["sudo", "tee", str(NGINX_UPSTREAM_CONF)],
        input=content.encode(), capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Could not write nginx upstream conf: {proc.stderr.decode()}")
    result = subprocess.run(["sudo", "nginx", "-s", "reload"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"nginx reload failed: {result.stderr}")
    logger.info(f"[Deploy] nginx upstream switched to :{port} (graceful reload done)")


def _load_demo_service_env() -> dict:
    """Parse Environment= lines from the browser-demo systemd service file."""
    env: dict = {}
    try:
        svc = Path("/etc/systemd/system/sailly-browser-demo.service").read_text()
        for line in svc.splitlines():
            line = line.strip()
            if line.startswith("Environment="):
                val = line[len("Environment="):].strip().strip('"')
                if "=" in val:
                    k, v = val.split("=", 1)
                    env[k] = v
    except Exception as e:
        logger.warning(f"[Deploy] Could not read demo service env: {e}")
    return env


# ── Active WebSocket guard (run before starting validation) ───────────────────

def _check_active_demo_sessions() -> int:
    """Return number of active WebSocket sessions on the browser-demo service."""
    port = _get_active_port()
    return _get_active_ws_count(port)


def _wait_for_demo_sessions_idle(max_delay_minutes: int = 15, check_interval_minutes: int = 5) -> None:
    """
    If active demo sessions exist, delay validation start.
    Retries up to max_delay_minutes // check_interval_minutes times.
    Proceeds anyway after max_delay_minutes (warns that maintenance window message should have been shown).
    """
    checks = max_delay_minutes // check_interval_minutes
    for attempt in range(checks):
        count = _check_active_demo_sessions()
        if count == 0:
            return
        logger.warning(
            f"[HealLoop] {count} active demo call(s) detected — delaying start by {check_interval_minutes}m "
            f"(attempt {attempt + 1}/{checks})"
        )
        _notify_slack(
            f"Validation delayed: {count} active demo call(s). Retrying in {check_interval_minutes} min.",
            level="warn",
        )
        time.sleep(check_interval_minutes * 60)

    count = _check_active_demo_sessions()
    if count > 0:
        logger.warning(f"[HealLoop] {count} active call(s) still running — proceeding anyway after {max_delay_minutes}m wait")


# ── Production failure harvesting (auto-add real failures to test suite) ──────

def _harvest_production_failures() -> List[dict]:
    """
    Read any production failure records captured by the browser-demo service.
    Returns a list of scenario-like dicts that can be used as additional context for Claude.
    Moves processed files to a 'processed' subdirectory.
    """
    if not PROD_FAILURES_DIR.exists():
        return []
    processed_dir = PROD_FAILURES_DIR / "processed"
    processed_dir.mkdir(exist_ok=True)
    failures = []
    for f in sorted(PROD_FAILURES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            failures.append(data)
            shutil.move(str(f), str(processed_dir / f.name))
        except Exception as e:
            logger.warning(f"[FailureReplay] Could not read {f.name}: {e}")
    if failures:
        logger.info(f"[FailureReplay] Harvested {len(failures)} production failure(s) for context")
    return failures


# ── Deploy (Phase E → Deploy) ─────────────────────────────────────────────────

def _backup_demo_brain(timestamp: str) -> Path:
    backup_path = DEMO_BACKUP_BASE / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)
    for fname in DEMO_BRAIN_FILES:
        src = DEMO_BRAIN_DIR / fname
        if src.exists():
            shutil.copy2(str(src), str(backup_path / fname))
    logger.info(f"[Deploy] Brain backed up to {backup_path}")
    return backup_path


def _copy_brain_to_demo() -> List[str]:
    errors = []
    for fname in DEMO_BRAIN_FILES:
        src = TRAINING_DIR / fname
        dst = DEMO_BRAIN_DIR / fname
        if not src.exists():
            logger.warning(f"[Deploy] Source not found: {src}, skipping")
            continue
        try:
            content = src.read_text(encoding="utf-8")
            content = re.sub(r'from server\.training\.', 'from server.brain.', content)
            content = re.sub(r'import server\.training\.', 'import server.brain.', content)
            dst.write_text(content, encoding="utf-8")
            logger.info(f"[Deploy] Copied {fname}")
        except Exception as e:
            errors.append(f"{fname}: {e}")
    return errors


def _clear_demo_cache() -> None:
    for cache_dir in DEMO_BRAIN_DIR.parent.parent.rglob("__pycache__"):
        shutil.rmtree(str(cache_dir), ignore_errors=True)
    logger.info("[Deploy] Pycache cleared")


def _restart_demo_services() -> bool:
    """
    Blue-green restart of sailly-browser-demo — zero downtime for new connections,
    60s drain window for active WebSocket calls.

    Port alternation: 8080 → 8081 → 8080 → 8081 …
    The nginx upstream is switched before the old instance is killed, so nginx
    routes new connections to the healthy instance immediately (reload is <10ms).
    """
    current_port = _get_active_port()
    new_port = 8081 if current_port == 8080 else 8080
    new_service = DEMO_8081_SERVICE if new_port == 8081 else "sailly-browser-demo"
    old_service = DEMO_8081_SERVICE if current_port == 8081 else "sailly-browser-demo"

    logger.info(f"[Deploy] Blue-green: :{current_port} ({old_service}) → :{new_port} ({new_service})")

    # Make sure nginx upstream conf exists before first deploy
    if not NGINX_UPSTREAM_CONF.exists():
        try:
            _switch_nginx_upstream(current_port)
        except RuntimeError as e:
            logger.warning(f"[Deploy] Initial nginx upstream write: {e}")

    # 1. Start new service instance
    result = subprocess.run(["systemctl", "start", new_service], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"[Deploy] Failed to start {new_service}: {result.stderr}")
        return False

    # 2. Wait for new instance to be healthy (up to 30s)
    logger.info(f"[Deploy] Waiting for :{new_port} to become healthy...")
    if not _wait_for_healthz(new_port, timeout=30):
        logger.error(f"[Deploy] New instance on :{new_port} failed health check — aborting blue-green")
        subprocess.run(["systemctl", "stop", new_service], capture_output=True)
        return False

    # 3. Switch nginx upstream → new port (graceful reload, <10ms)
    try:
        _switch_nginx_upstream(new_port)
    except RuntimeError as e:
        logger.error(f"[Deploy] nginx switch failed: {e} — aborting, stopping new instance")
        subprocess.run(["systemctl", "stop", new_service], capture_output=True)
        return False

    # 4. Drain active WebSocket sessions on old port (up to 60s)
    _wait_for_ws_drain(current_port, timeout=60)

    # 5. Stop old instance
    subprocess.run(["systemctl", "stop", old_service], capture_output=True)
    logger.info(f"[Deploy] Old instance :{current_port} stopped")

    # 6. Record new active port
    _set_active_port(new_port)

    # 7. Restart dashboard (no audio calls, 2-3s gap acceptable)
    result = subprocess.run(["systemctl", "restart", "sailly-dashboard"], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"[Deploy] Failed to restart sailly-dashboard: {result.stderr}")
        return False
    logger.info("[Deploy] sailly-dashboard restarted")
    time.sleep(5)
    return True


async def _smoke_test() -> bool:
    script = """
import asyncio, sys
sys.path.insert(0, '/home/charles2/sailly-browser-demo')

async def test():
    try:
        from server.training.adk_turn_processor import ADKTurnProcessor
    except Exception as e:
        print(f"SMOKE FAIL: import: {e}"); return False
    tests = [
        ("greeting", ""),
        ("order", "Ich möchte ein Bibimbap bestellen"),
        ("reservation", "Ich möchte einen Tisch für morgen um 19 Uhr, 2 Personen"),
        ("escalation", "Ich will sofort mit einem Menschen sprechen!"),
        ("goodbye", "Tschüss, auf Wiederhören"),
    ]
    passed = 0
    for name, utt in tests:
        try:
            tp = ADKTurnProcessor()
            if utt: await tp.process_turn("")
            r = await tp.process_turn(utt)
            if r and r.clean_text:
                print(f"SMOKE OK: {name}"); passed += 1
            else:
                print(f"SMOKE FAIL: {name} — empty response")
        except Exception as e:
            print(f"SMOKE FAIL: {name} — {e}")
    print(f"SMOKE RESULT: {passed}/5")
    return passed >= 4

sys.exit(0 if asyncio.run(test()) else 1)
"""
    proc = await asyncio.create_subprocess_exec(
        PYTHON, "-c", script,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    logger.info(f"[Deploy] Smoke test:\n{stdout.decode('utf-8', errors='replace')}")
    return proc.returncode == 0


async def _canary_monitor(window_seconds: int, backup_path: Path) -> bool:
    logger.info(f"[Deploy] Canary window: {window_seconds // 60} minutes...")
    start = time.time()
    interval = 30

    while time.time() - start < window_seconds:
        elapsed = int(time.time() - start)

        result = subprocess.run(
            ["systemctl", "is-active", "sailly-browser-demo"],
            capture_output=True, text=True,
        )
        if result.stdout.strip() != "active":
            logger.error(f"[Deploy] Canary FAIL: service down after {elapsed}s")
            await _auto_rollback(backup_path)
            return False

        log_result = subprocess.run(
            ["journalctl", "-u", "sailly-browser-demo", f"--since={interval} seconds ago",
             "--no-pager", "--output=cat", "-q"],
            capture_output=True, text=True,
        )
        for term in ["traceback", "importerror", "modulenotfounderror", "runtimeerror: brain"]:
            if term in log_result.stdout.lower():
                logger.error(f"[Deploy] Canary FAIL: '{term}' in logs after {elapsed}s")
                await _auto_rollback(backup_path)
                return False

        logger.info(f"[Deploy] Canary OK {elapsed}s/{window_seconds}s")
        await asyncio.sleep(interval)

    logger.info("[Deploy] Canary passed — deploy confirmed!")
    return True


async def _auto_rollback(backup_path: Path) -> None:
    logger.error(f"[Deploy] AUTO-ROLLBACK from {backup_path}")
    _notify_slack(f"AUTO-ROLLBACK triggered from backup `{backup_path.name}`", level="error")
    for fname in DEMO_BRAIN_FILES:
        src = backup_path / fname
        if src.exists():
            shutil.copy2(str(src), str(DEMO_BRAIN_DIR / fname))
    _clear_demo_cache()
    _restart_demo_services()
    logger.error("[Deploy] Rollback complete")
    _notify_slack("Rollback complete — previous brain version restored", level="warn")


async def deploy_to_demo_browser(dry_run: bool = False) -> bool:
    if dry_run:
        logger.info("[Deploy] DRY RUN — skipping actual deploy")
        return True

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info("=" * 60)
    logger.info("[Deploy] Starting deploy to demo browser...")
    logger.info("=" * 60)
    _notify_slack("Deploy starting — blue-green brain swap in progress", level="info")

    # Clean up old backups before creating a new one
    _cleanup_old_backups()

    backup_path = _backup_demo_brain(timestamp)
    copy_errors = _copy_brain_to_demo()
    if copy_errors:
        logger.error(f"[Deploy] Copy errors: {copy_errors}")
        _notify_slack(f"Deploy FAILED — copy errors: {copy_errors}", level="error")
        await _auto_rollback(backup_path)
        return False

    _clear_demo_cache()
    if not _restart_demo_services():
        _notify_slack("Deploy FAILED — blue-green service restart failed", level="error")
        await _auto_rollback(backup_path)
        return False

    if not await _smoke_test():
        logger.error("[Deploy] Smoke test FAILED — rolling back")
        _notify_slack("Deploy FAILED — smoke test did not pass (≥4/5 required)", level="error")
        await _auto_rollback(backup_path)
        return False

    _notify_slack("Deploy succeeded — smoke test passed. Starting 30-min canary window.", level="ok")
    result = await _canary_monitor(CANARY_WINDOW_SECONDS, backup_path)
    if result:
        _notify_slack("Canary passed — deploy confirmed stable :tada:", level="ok")
    return result


# ── Main heal loop ─────────────────────────────────────────────────────────────

def _sd_watchdog() -> None:
    """Send systemd watchdog keepalive (only effective when Type=notify and WatchdogSec is set)."""
    try:
        import sdnotify  # type: ignore
        sdnotify.SystemdNotifier().notify("WATCHDOG=1")
    except ImportError:
        # sdnotify not installed — use raw socket approach
        notify_socket = os.environ.get("NOTIFY_SOCKET")
        if notify_socket:
            import socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            try:
                sock.connect(notify_socket)
                sock.sendall(b"WATCHDOG=1")
            except Exception:
                pass
            finally:
                sock.close()


async def run_heal_loop(
    dry_run: bool = False,
    skip_full_validation: bool = False,
    results_dir: Optional[str] = None,
    workers: int = 20,
) -> dict:
    """
    Self-healing pipeline:
      Phase A (1×): Full 280-scenario run OR load existing results
      Fix Loop (up to MAX_ITERATIONS):
        Phase C: Claude proposes fix for remaining failing buckets
        Phase D: fix_validation_loop on failing buckets only
        → Resolved buckets are skipped next iteration
      Phase E (1×): Full 280 regression check
      Deploy (if Phase E >= 95%)
    """
    from server.training import claude_fixer
    from server.training.unified_dashboard import (
        register_run, finish_run, write_dashboard, RUNS_ROOT,
    )

    # ── Signal handlers — allow dashboard to pause/stop us gracefully ─────────
    _controller.setup()

    # ── Lock file — prevent concurrent runs ──────────────────────────────────
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    lock_fd = open(str(LOCK_FILE), "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        logger.error("[HealLoop] Another validation run is already in progress (lock file held). Exiting.")
        lock_fd.close()
        return {"error": "already_running"}

    loop_started_at = datetime.now(timezone.utc).isoformat()

    from server.training import claude_fixer as _claude_fixer
    from server.training.unified_dashboard import (
        register_run as _register_run,
        finish_run as _finish_run,
        write_dashboard as _write_dashboard,
        RUNS_ROOT as _RUNS_ROOT,
    )

    try:
        return await _run_heal_loop_inner(
            dry_run=dry_run,
            skip_full_validation=skip_full_validation,
            results_dir=results_dir,
            workers=workers,
            claude_fixer=_claude_fixer,
            write_dashboard=_write_dashboard,
            register_run=_register_run,
            finish_run=_finish_run,
            loop_started_at=loop_started_at,
        )
    finally:
        # Ensure status shows "not running" even on unexpected exit
        try:
            _write_status(running=False, last_result="interrupted")
            _write_availability(validation_running=False)
        except Exception:
            pass
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        try:
            LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass


async def _run_heal_loop_inner(
    dry_run: bool,
    skip_full_validation: bool,
    results_dir: Optional[str],
    workers: int,
    claude_fixer,
    write_dashboard,
    register_run,
    finish_run,
    loop_started_at: str,
) -> dict:
    write_dashboard()
    history = _load_history()
    run_id = datetime.now(timezone.utc).isoformat()
    # Human-readable session label: e.g. "2026-04-09 #3"
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_seq = len(history.get("runs", [])) + 1
    _session_label = f"{run_date} #{run_seq}"
    run_record = {
        "run_id": run_id,
        "iterations": [],
        "phase_a_pass_rate": 0.0,
        "phase_e_pass_rate": 0.0,
        "deployed": False,
        "total_cost_usd": 0.0,
        "canary_passed": False,
    }

    total_cost = 0.0
    prior_fixes: List[dict] = []

    # ── Active WebSocket session guard ────────────────────────────────────────
    _wait_for_demo_sessions_idle(max_delay_minutes=15, check_interval_minutes=5)

    # ── Mark loop as running (status + availability files) ───────────────────
    _write_status(running=True, phase="Phase A — Baseline", started_at=loop_started_at)
    _write_availability(
        validation_running=True,
        phase="Phase A — Baseline (280 scenarios)",
        estimated_end="",  # unknown until Phase A completes
    )
    _notify_slack("Validation heal loop started — Phase A baseline (280 scenarios)", level="info")
    _sd_watchdog()

    # ── Harvest any captured production failures for Claude context ───────────
    production_failures = _harvest_production_failures()

    # ── Phase A: Full 280 (ONCE at start) ────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("[HealLoop] PHASE A — 280-scenario baseline validation")
    logger.info("=" * 60)

    phase_a_started = datetime.now(timezone.utc).isoformat()
    if skip_full_validation and results_dir:
        phase_a = _load_existing_results(Path(results_dir))
    elif skip_full_validation:
        phase_a = _load_existing_results(VALIDATION_OUTPUT_DIR)
    else:
        VALIDATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        phase_a = await _run_full_validation(VALIDATION_OUTPUT_DIR, workers=workers)
        total_cost += phase_a.get("cost_usd", 0.0)

    phase_a_idx = register_run(
        run_dir="ab_heal_results",
        name=f"[{_session_label}] Phase A — Baseline ({phase_a.get('passes', 0)}/{phase_a.get('total', 0)} = {phase_a.get('pass_rate', 0):.0%})",
        code="PHASE-A",
        run_type="validation",
        started_at=phase_a_started,
    )
    finish_run(phase_a_idx, finished_at=datetime.now(timezone.utc).isoformat(), status="finished")

    baseline_pass_rate = phase_a["pass_rate"]
    run_record["phase_a_pass_rate"] = baseline_pass_rate
    all_failures = [r for r in phase_a["results"] if not r.get("one_live_pass", True)]
    remaining_failed_ids = [r["scenario_id"] for r in all_failures if r.get("scenario_id")]

    logger.info(
        f"\n[HealLoop] Phase A complete: {baseline_pass_rate:.1%} pass rate, "
        f"{len(remaining_failed_ids)} failures to fix"
    )
    _notify_slack(
        f"Phase A complete: `{baseline_pass_rate:.1%}` pass rate, "
        f"{len(remaining_failed_ids)} failures to fix",
        level="info" if baseline_pass_rate >= PASS_THRESHOLD else "warn",
    )
    _sd_watchdog()

    # Store original failed IDs as baseline for regression recovery
    run_record["_original_failed_ids"] = list(remaining_failed_ids)
    run_record["_best_remaining_count"] = len(remaining_failed_ids)
    run_record["_best_resolved_ids"] = []
    run_record["_best_iteration"] = -1

    if baseline_pass_rate >= PASS_THRESHOLD:
        logger.info(f"[HealLoop] Already at {baseline_pass_rate:.1%} >= {PASS_THRESHOLD:.0%} — skipping fix loop")
    else:
        # ── Fix Loop (up to MAX_ITERATIONS) ──────────────────────────────────
        logger.info(
            f"\n[HealLoop] Starting fix loop: up to {MAX_ITERATIONS} iterations, "
            f"targeting {len(remaining_failed_ids)} failing scenarios\n"
        )

        for iteration in range(MAX_ITERATIONS):
            if not remaining_failed_ids:
                logger.info("[HealLoop] All failing scenarios resolved — exiting fix loop")
                break

            if total_cost >= COST_CEILING_USD:
                logger.error(
                    f"[HealLoop] COST CEILING: ${total_cost:.2f} >= ${COST_CEILING_USD:.2f} — aborting"
                )
                run_record["abort_reason"] = "cost_ceiling"
                break

            iter_record = {
                "iteration": iteration,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "remaining_failures": len(remaining_failed_ids),
                "patches": [],
                "fix_validation_buckets_passed": 0,
                "fix_validation_buckets_failed": [],
                "newly_resolved": [],
                "regression": False,
                "cost_usd": 0.0,
            }

            logger.info(
                f"\n{'='*60}\n"
                f"[HealLoop] FIX ITERATION {iteration + 1}/{MAX_ITERATIONS} — "
                f"{len(remaining_failed_ids)} scenarios still failing\n"
                f"{'='*60}"
            )
            _sd_watchdog()
            _write_status(
                running=True,
                phase=f"Fix Loop — Iteration {iteration + 1}/{MAX_ITERATIONS}",
                started_at=loop_started_at,
            )
            _write_availability(
                validation_running=True,
                phase=f"Fix Loop — Iteration {iteration + 1}/{MAX_ITERATIONS}",
                iteration=iteration + 1,
                max_iterations=MAX_ITERATIONS,
            )

            # ── Phase C: Claude fix ───────────────────────────────────────────
            logger.info(f"[HealLoop] Phase C — Claude Sonnet 4.6 analyzing failures...")

            # Get failed results for Claude context
            failed_results = [r for r in all_failures if r.get("scenario_id") in set(remaining_failed_ids)]

            # Backup training source before patching
            backup_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            training_backup = TRAINING_DIR.parent.parent / f"training_backup_{backup_ts}"
            shutil.copytree(str(TRAINING_DIR), str(training_backup))

            try:
                proposal = await claude_fixer.analyze_and_fix(
                    failed_results=failed_results + production_failures,
                    iteration=iteration,
                    prior_fixes=prior_fixes,
                    cost_spent=total_cost,
                )
            except Exception as e:
                logger.error(f"[HealLoop] Claude error: {e}")
                iter_record["error"] = str(e)
                run_record["iterations"].append(iter_record)
                _save_history({**history, "runs": history.get("runs", []) + [run_record]})
                continue

            total_cost += proposal.cost_usd
            iter_record["cost_usd"] += proposal.cost_usd

            if proposal.rejected:
                logger.warning(f"[HealLoop] Proposal REJECTED: {proposal.rejection_reason}")
                prior_fixes.append({**proposal.to_dict(), "outcome": f"rejected:{proposal.rejection_reason}"})
                iter_record["patches"] = [{"rejected": True, "reason": proposal.rejection_reason}]
                run_record["iterations"].append(iter_record)
                _save_history({**history, "runs": history.get("runs", []) + [run_record]})
                continue

            # Log diffs before applying
            logger.info("[HealLoop] Patches to apply:")
            for p in proposal.patches:
                logger.info(f"  {p.file} ({p.lines_changed} lines): {p.description}")

            apply_errors = claude_fixer.apply_patches(proposal)
            if apply_errors:
                logger.warning(f"[HealLoop] Patch apply errors: {apply_errors}")

            # Clear pycache
            for cache in TRAINING_DIR.rglob("__pycache__"):
                shutil.rmtree(str(cache), ignore_errors=True)

            # ── Phase D: fix_validation_loop (targeted) ───────────────────────
            logger.info(
                f"\n[HealLoop] Phase D — fix_validation_loop\n"
                f"  Targeting {len(remaining_failed_ids)} failed scenarios\n"
                f"  Structure per bucket: Step 1→2→3 (10 each) × up to 3 retries"
            )

            fix_started = datetime.now(timezone.utc).isoformat()
            fix_run_idx = register_run(
                run_dir=f"ab_fix_validation/iter_{iteration}",
                name=f"[{_session_label}] Fix {iteration + 1}/{MAX_ITERATIONS} — {len(remaining_failed_ids)} failing",
                code=f"FIX-{iteration + 1}",
                run_type="fix-validation",
                started_at=fix_started,
            )

            fix_val = await _run_fix_validation(
                failed_ids=remaining_failed_ids,
                workers=20,
                iteration=iteration,
            )
            finish_run(fix_run_idx, finished_at=datetime.now(timezone.utc).isoformat(),
                       status="finished" if fix_val.get("passed_buckets", 0) > 0 else "failed")
            total_cost += fix_val.get("cost_usd", 0.0)
            iter_record["cost_usd"] += fix_val.get("cost_usd", 0.0)
            iter_record["fix_validation_buckets_passed"] = fix_val.get("passed_buckets", 0)
            iter_record["fix_validation_buckets_failed"] = fix_val.get("failed_buckets", [])

            # Determine which scenario IDs belong to now-resolved buckets
            bucket_details = fix_val.get("bucket_details", [])
            newly_resolved_ids: List[str] = []
            for b in bucket_details:
                if b.get("status") == "validated":
                    # Extract scenario IDs from this bucket's results
                    for step_results in [b.get("step1_results", []), b.get("step2_results", []), b.get("step3_results", [])]:
                        for r in step_results:
                            sid = r.get("scenario_id", r.get("id", ""))
                            if sid and sid in set(remaining_failed_ids):
                                newly_resolved_ids.append(sid)

            newly_resolved_ids = list(set(newly_resolved_ids))
            iter_record["newly_resolved"] = newly_resolved_ids

            # Check for regression: did this patch make things NET WORSE?
            # Regression = remaining failures increased compared to the best state we've achieved
            best_remaining = run_record.get("_best_remaining_count", len(remaining_failed_ids) + 1)
            current_remaining_after = (
                len(remaining_failed_ids) - len(newly_resolved_ids)
                if not newly_resolved_ids else len(remaining_failed_ids)
            )
            # Also catch the classic case: 0 buckets passed while previously some had
            zero_progress = (
                fix_val.get("total_buckets", 0) > 0 and fix_val.get("passed_buckets", 0) == 0
                and sum(p.get("fix_validation_buckets_passed", 0) for p in run_record["iterations"]) > 0
            )
            net_regression = len(remaining_failed_ids) > best_remaining

            if zero_progress or net_regression:
                reason = "net regression vs best state" if net_regression else "0 buckets passed"
                logger.warning(
                    f"[HealLoop] REGRESSION ({reason}) — reverting patch from iteration {iteration + 1}. "
                    f"Best was {best_remaining} remaining, now {len(remaining_failed_ids)}"
                )
                _notify_slack(
                    f"Regression detected (iter {iteration + 1}): {reason}. Reverting patch.",
                    level="warn",
                )
                claude_fixer.revert_patches(proposal)
                # Restore remaining_failed_ids to the best known state
                if net_regression and run_record.get("_best_resolved_ids"):
                    best_resolved = set(run_record["_best_resolved_ids"])
                    remaining_failed_ids = [
                        sid for sid in run_record.get("_original_failed_ids", remaining_failed_ids)
                        if sid not in best_resolved
                    ]
                iter_record["regression"] = True
                prior_fixes.append({**proposal.to_dict(), "outcome": f"regression:{reason}"})
                run_record["iterations"].append(iter_record)
                run_record["total_cost_usd"] = total_cost
                _save_history({**history, "runs": history.get("runs", []) + [run_record]})
                continue

            # Update remaining failures: remove resolved scenario IDs
            if newly_resolved_ids:
                before = len(remaining_failed_ids)
                remaining_failed_ids = [sid for sid in remaining_failed_ids if sid not in set(newly_resolved_ids)]
                logger.info(
                    f"[HealLoop] {len(newly_resolved_ids)} scenarios resolved this iteration "
                    f"({before} → {len(remaining_failed_ids)} remaining)"
                )
                # Accumulate best resolved state across iterations
                best_resolved = run_record.get("_best_resolved_ids", [])
                if len(remaining_failed_ids) < run_record.get("_best_remaining_count", 9999):
                    run_record["_best_remaining_count"] = len(remaining_failed_ids)
                    run_record["_best_resolved_ids"] = list(set(best_resolved + newly_resolved_ids))
                    run_record["_best_iteration"] = iteration
                    logger.info(f"[HealLoop] New best: {len(remaining_failed_ids)} remaining (iter {iteration + 1})")
            else:
                logger.info(
                    f"[HealLoop] No new scenarios resolved this iteration. "
                    f"{len(remaining_failed_ids)} still failing — will try a different fix next iteration"
                )

            iter_record["patches"] = [
                {
                    "file": p.file,
                    "description": p.description,
                    "lines_changed": p.lines_changed,
                    "diff": p.diff,
                }
                for p in proposal.patches
            ]
            prior_fixes.append({**proposal.to_dict(), "outcome": fix_val.get("passed_buckets", 0)})

            run_record["iterations"].append(iter_record)
            run_record["total_cost_usd"] = total_cost
            _save_history({**history, "runs": history.get("runs", []) + [run_record]})

            logger.info(
                f"[HealLoop] Iteration {iteration + 1} complete — "
                f"{fix_val.get('passed_buckets', 0)}/{fix_val.get('total_buckets', 0)} buckets passed, "
                f"{len(remaining_failed_ids)} scenarios still failing"
            )

        # ── End of fix loop ───────────────────────────────────────────────────
        best_iter = run_record.get("_best_iteration", -1)
        best_remaining = run_record.get("_best_remaining_count", len(remaining_failed_ids))
        iters_done = min(len(run_record["iterations"]), MAX_ITERATIONS)
        logger.info(
            f"\n[HealLoop] Fix loop complete after {iters_done} iterations. "
            f"{len(remaining_failed_ids)} scenarios remain unresolved.\n"
            f"  Best state: iteration {best_iter + 1} with {best_remaining} remaining failures."
        )
        if len(remaining_failed_ids) > 0:
            _notify_slack(
                f"Fix loop exhausted {iters_done} iterations — {len(remaining_failed_ids)} scenario(s) still failing. "
                f"Best state was iteration {best_iter + 1} ({best_remaining} remaining). "
                f"Proceeding to Phase E regression check.",
                level="warn",
            )
            if len(remaining_failed_ids) > best_remaining:
                logger.warning(
                    f"[HealLoop] Current state ({len(remaining_failed_ids)} remaining) is WORSE than best "
                    f"(iteration {best_iter + 1}, {best_remaining} remaining). "
                    "Consider re-running with --skip-full-validation from the best iteration's checkpoint."
                )

    # ── Crucial Fix Validation (CFV) — if buckets remain unresolved ──────────
    cfv_result: Optional[dict] = None
    if remaining_failed_ids:
        logger.info("\n" + "=" * 60)
        logger.info(
            f"[HealLoop] CRUCIAL FIX VALIDATION — {len(remaining_failed_ids)} scenario(s) still failing "
            f"after {MAX_ITERATIONS} fix iterations. Starting deep per-bucket analysis with web search."
        )
        logger.info("=" * 60)
        _sd_watchdog()
        _write_status(
            running=True,
            phase="CFV — Crucial Fix Validation (deep per-bucket, web search)",
            started_at=loop_started_at,
        )
        _write_availability(
            validation_running=True,
            phase="CFV — Crucial Fix Validation",
        )

        # Collect names of still-unresolved buckets.
        # The most reliable source is the last fix_validation_loop state file —
        # those bucket names are the canonical names used by fix_validation_loop.
        # (phase scenario IDs like 'p1-faq-01' live in a different namespace.)
        cfv_unresolved_bucket_names: List[str] = []
        import glob as _glob
        iter_state_files = sorted(_glob.glob(str(FIX_VAL_OUTPUT_DIR / "iter_*/fix_validation_state.json")))
        if iter_state_files:
            last_state = json.loads(Path(iter_state_files[-1]).read_text())
            for b in last_state.get("buckets", []):
                if b.get("status") not in ("validated",) and b.get("name"):
                    if b["name"] not in cfv_unresolved_bucket_names:
                        cfv_unresolved_bucket_names.append(b["name"])
            logger.info(
                f"[HealLoop] CFV: unresolved buckets from last fix-val state: "
                f"{cfv_unresolved_bucket_names}"
            )
        # Fallback: try mapping via fix_validation_buckets scenario IDs
        if not cfv_unresolved_bucket_names:
            try:
                from server.training.fix_validation_buckets import ALL_BUCKETS
                for bid in remaining_failed_ids:
                    for bkt in ALL_BUCKETS:
                        if any(s.id == bid for s in bkt.scenarios):
                            if bkt.name not in cfv_unresolved_bucket_names:
                                cfv_unresolved_bucket_names.append(bkt.name)
                            break
            except Exception:
                pass
        if not cfv_unresolved_bucket_names:
            logger.warning(
                "[HealLoop] Could not map failed IDs to bucket names — "
                "CFV will skip (no buckets to fix)."
            )
            cfv_unresolved_bucket_names = []

        _notify_slack(
            f"CFV starting: {len(cfv_unresolved_bucket_names)} unresolved bucket(s) — "
            f"{cfv_unresolved_bucket_names}. Using Claude + web search.",
            level="warn",
        )

        try:
            from server.training.crucial_fix_validator import run_crucial_fix_validation
            cfv_result = await run_crucial_fix_validation(
                unresolved_bucket_names=cfv_unresolved_bucket_names,
                all_failed_ids=remaining_failed_ids,
                phase_a_total_scenarios=phase_a.get("total", 280),
                phase_a_passed_scenarios=phase_a.get("passes", 0),
                iteration_offset=len(run_record["iterations"]),
                workers=workers,
                register_run=register_run,
                finish_run=finish_run,
            )

            total_cost += cfv_result.get("cost_usd", 0.0)
            run_record["cfv_result"] = cfv_result

            # Update remaining_failed_ids: remove scenarios from resolved buckets
            if cfv_result["resolved_scenario_ids"]:
                resolved_set = set(cfv_result["resolved_scenario_ids"])
                remaining_failed_ids = [
                    sid for sid in remaining_failed_ids if sid not in resolved_set
                ]
                logger.info(
                    f"[HealLoop] CFV resolved {len(cfv_result['resolved_scenario_ids'])} scenarios. "
                    f"{len(remaining_failed_ids)} still unresolved."
                )

            # Handle buckets that need human investigation
            if cfv_result["unresolved_buckets"]:
                _notify_slack(
                    f"CFV needs human investigation for: {cfv_result['unresolved_buckets']}. "
                    f"Projected pass rate: {cfv_result['projected_pass_rate']:.1%}.",
                    level="error",
                )
                logger.error(
                    f"[HealLoop] CFV: {len(cfv_result['unresolved_buckets'])} bucket(s) need human investigation: "
                    f"{cfv_result['unresolved_buckets']}"
                )
                run_record["cfv_needs_human_investigation"] = cfv_result["unresolved_buckets"]

            # Phase E gate: check projected pass rate before running the full 280-scenario check
            projected_rate = cfv_result.get("projected_pass_rate", 0.0)
            if projected_rate < PASS_THRESHOLD:
                logger.error(
                    f"[HealLoop] CFV projected pass rate {projected_rate:.1%} < {PASS_THRESHOLD:.0%} threshold. "
                    "Skipping Phase E — deploying would likely fail. Manual review required."
                )
                _notify_slack(
                    f"Phase E SKIPPED — CFV projected {projected_rate:.1%} < {PASS_THRESHOLD:.0%}. "
                    "Manual investigation required for remaining buckets.",
                    level="error",
                )
                run_record["abort_reason"] = "insufficient_projected_pass_rate_after_cfv"
                run_record["cfv_projected_pass_rate"] = projected_rate
                run_record["deployed"] = False
                run_record["total_cost_usd"] = total_cost
                finished_at = datetime.now(timezone.utc).isoformat()
                run_record["finished_at"] = finished_at
                _write_status(running=False, last_result="cfv_below_threshold")
                _write_availability(validation_running=False)
                _save_history({**history, "runs": history.get("runs", []) + [run_record]})
                return run_record

            _notify_slack(
                f"CFV complete: {len(cfv_result['resolved_buckets'])} resolved, "
                f"{len(cfv_result['unresolved_buckets'])} need human review. "
                f"Projected pass rate: {projected_rate:.1%}. Proceeding to Phase E.",
                level="ok" if not cfv_result["unresolved_buckets"] else "warn",
            )

        except Exception as e:
            logger.exception(f"[HealLoop] CFV phase failed with exception: {e}")
            _notify_slack(f"CFV phase crashed: {e}. Proceeding to Phase E anyway.", level="error")

    # ── Phase E gate: ALL buckets must have reached Step 3 at >= 95% ─────────
    # Check the last fix_validation_state.json: every bucket must have step3_count > 0
    # and the overall combined rate must be >= PASS_THRESHOLD.
    import glob as _glob_e
    _iter_states_for_gate = sorted(
        _glob_e.glob(str(FIX_VAL_OUTPUT_DIR / "iter_*/fix_validation_state.json"))
    )
    _gate_blocked = False
    if _iter_states_for_gate:
        try:
            _last_fvs = json.loads(Path(_iter_states_for_gate[-1]).read_text())
            _gate_buckets = _last_fvs.get("buckets", [])
            _no_step3 = [b["name"] for b in _gate_buckets if not b.get("step3_count", 0) and b.get("status") != "validated"]
            _step3_fail = [b["name"] for b in _gate_buckets if b.get("step3_count", 0) and b.get("step3_rate", 0) < PASS_THRESHOLD and b.get("status") != "validated"]
            if _no_step3 or _step3_fail:
                _gate_blocked = True
                _missing_msg = (
                    f"Buckets not reaching Step 3: {_no_step3}. "
                    f"Buckets failing Step 3 threshold: {_step3_fail}. "
                    f"Overall 95% gate NOT met — Phase E blocked."
                )
                logger.error(f"[HealLoop] Phase E gate BLOCKED: {_missing_msg}")
                _notify_slack(
                    f"Phase E BLOCKED by loop gate: {_missing_msg}",
                    level="error",
                )
        except Exception as _ge:
            logger.warning(f"[HealLoop] Phase E gate check failed: {_ge} — proceeding anyway")

    if _gate_blocked:
        run_record["abort_reason"] = "phase_e_gate_blocked_buckets_not_all_step3"
        run_record["deployed"] = False
        run_record["total_cost_usd"] = total_cost
        finished_at = datetime.now(timezone.utc).isoformat()
        run_record["finished_at"] = finished_at
        _write_status(running=False, last_result="phase_e_gate_blocked")
        _write_availability(validation_running=False)
        _save_history({**history, "runs": history.get("runs", []) + [run_record]})
        return run_record

    # ── Phase E: Full 280 regression check (ONCE at end) ─────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("[HealLoop] PHASE E — Final 280-scenario regression check (1× at end)")
    logger.info("=" * 60)
    _sd_watchdog()
    _write_status(running=True, phase="Phase E — Final Regression (280 scenarios)", started_at=loop_started_at)
    _write_availability(validation_running=True, phase="Phase E — Final Regression (280 scenarios)")

    phase_e_started = datetime.now(timezone.utc).isoformat()
    phase_e_idx = register_run(
        run_dir="ab_heal_results",
        name=f"[{_session_label}] Phase E — Final Regression Check",
        code="PHASE-E",
        run_type="validation",
        started_at=phase_e_started,
    )

    phase_e = await _run_full_validation(VALIDATION_OUTPUT_DIR, workers=workers)
    total_cost += phase_e.get("cost_usd", 0.0)
    final_pass_rate = phase_e["pass_rate"]
    finish_run(phase_e_idx, finished_at=datetime.now(timezone.utc).isoformat(),
               status="finished" if final_pass_rate >= PASS_THRESHOLD else "failed")
    run_record["phase_e_pass_rate"] = final_pass_rate
    run_record["total_cost_usd"] = total_cost

    logger.info(
        f"\n[HealLoop] Phase E result: {final_pass_rate:.1%} "
        f"({phase_e['passes']}/{phase_e['total']})"
    )
    logger.info(f"  Baseline (Phase A): {baseline_pass_rate:.1%}")
    logger.info(f"  Final    (Phase E): {final_pass_rate:.1%}")
    improvement = final_pass_rate - baseline_pass_rate
    logger.info(f"  Improvement:        {improvement:+.1%}")

    _notify_slack(
        f"Phase E complete: `{final_pass_rate:.1%}` (was `{baseline_pass_rate:.1%}`). "
        f"Δ`{final_pass_rate - baseline_pass_rate:+.1%}`",
        level="ok" if final_pass_rate >= PASS_THRESHOLD else "error",
    )

    # ── Deploy ────────────────────────────────────────────────────────────────
    if final_pass_rate >= PASS_THRESHOLD:
        logger.info(
            f"\n[HealLoop] ✅ {final_pass_rate:.1%} >= {PASS_THRESHOLD:.0%} — deploying to demo browser!"
        )
        _write_status(running=True, phase="Deploy — blue-green restart", started_at=loop_started_at)
        _write_availability(validation_running=True, phase="Deploy in progress")
        deployed = await deploy_to_demo_browser(dry_run=dry_run)
        run_record["deployed"] = deployed
        run_record["canary_passed"] = deployed
        if deployed:
            logger.info("[HealLoop] Deploy + canary: SUCCESS")
        else:
            logger.error("[HealLoop] Deploy FAILED or canary triggered rollback")
    else:
        logger.error(
            f"\n[HealLoop] ❌ {final_pass_rate:.1%} < {PASS_THRESHOLD:.0%} after "
            f"{len(run_record['iterations'])} fix iterations (${total_cost:.2f} spent). "
            "Manual intervention required."
        )
        _notify_slack(
            f"Heal loop ended WITHOUT deploy — `{final_pass_rate:.1%}` < `{PASS_THRESHOLD:.0%}`. "
            "Manual review required.",
            level="error",
        )
        run_record["deployed"] = False

    # ── Mark loop as finished ─────────────────────────────────────────────────
    finished_at = datetime.now(timezone.utc).isoformat()
    last_result = "success" if run_record.get("deployed") else ("partial" if final_pass_rate >= PASS_THRESHOLD else "failed")
    _write_status(
        running=False,
        phase="",
        last_result=last_result,
        last_pass_rate=final_pass_rate,
        last_completed=finished_at,
        started_at=loop_started_at,
    )
    _write_availability(validation_running=False)

    _save_history({**history, "runs": history.get("runs", []) + [run_record]})
    return run_record


# ── CLI ───────────────────────────────────────────────────────────────────────

async def main():
    global PASS_THRESHOLD, MAX_ITERATIONS, COST_CEILING_USD, CANARY_WINDOW_SECONDS  # noqa

    parser = argparse.ArgumentParser(
        description=(
            "Self-healing validation + auto-deploy pipeline.\n\n"
            "Phase A (1×): Full 280-scenario baseline.\n"
            "Fix Loop (≤8×): Claude fix → fix_validation_loop (targeted per bucket).\n"
            "Phase E (1×): Final 280-scenario regression check → deploy if ≥ 95%%."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run the full pipeline but DO NOT deploy to demo browser",
    )
    parser.add_argument(
        "--skip-full-validation", action="store_true",
        help=(
            "Skip Phase A — use existing ab_results.json from --results-dir "
            "(or /tmp/ab_heal_results if omitted)"
        ),
    )
    parser.add_argument(
        "--results-dir", default=None, metavar="PATH",
        help=(
            "Directory containing an existing ab_results.json to use as Phase A baseline. "
            "Example: --results-dir /tmp/ab_test_results"
        ),
    )
    parser.add_argument(
        "--workers", type=int, default=20,
        help="Parallel workers for full validation runs (default 20)",
    )
    parser.add_argument(
        "--max-iterations", type=int, default=8,
        help="Max Claude fix iterations in the fix loop (default 8)",
    )
    parser.add_argument(
        "--threshold", type=float, default=PASS_THRESHOLD,
        help=f"Pass rate required on Phase E to trigger deploy (default {PASS_THRESHOLD:.0%})",
    )
    parser.add_argument(
        "--cost-ceiling", type=float, default=COST_CEILING_USD,
        help=f"Abort fix loop if API spend exceeds this USD amount (default ${COST_CEILING_USD})",
    )
    parser.add_argument(
        "--canary-minutes", type=int, default=30,
        help="Canary monitoring window in minutes after deploy (default 30)",
    )
    parser.add_argument(
        "--cfv-only",
        action="store_true",
        help=(
            "Skip Phase A and the fix loop entirely — jump straight to CFV using the "
            "failed IDs from the most recent fix_validation_loop output. "
            "Use after a full fix-loop run when you want to escalate immediately to CFV. "
            "Requires /tmp/ab_fix_validation/iter_N/failed_ids.json to exist."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    PASS_THRESHOLD = args.threshold
    MAX_ITERATIONS = args.max_iterations
    COST_CEILING_USD = args.cost_ceiling
    CANARY_WINDOW_SECONDS = args.canary_minutes * 60

    if args.cfv_only:
        # --cfv-only: find the latest fix_validation iter and jump straight to CFV
        import glob as _glob
        iter_dirs = sorted(_glob.glob("/tmp/ab_fix_validation/iter_*"))
        if not iter_dirs:
            print("ERROR: No fix_validation iterations found in /tmp/ab_fix_validation/. "
                  "Run without --cfv-only first.", flush=True)
            return
        last_iter_dir = Path(iter_dirs[-1])

        # Load the fix_validation state to get canonical unresolved bucket names
        state_path = last_iter_dir / "fix_validation_state.json"
        failed_ids_path = last_iter_dir / "failed_ids.json"
        if not state_path.exists():
            print(f"ERROR: No fix_validation_state.json in {last_iter_dir}", flush=True)
            return
        fv_state = json.loads(state_path.read_text())
        unresolved_buckets = [
            b["name"] for b in fv_state.get("buckets", [])
            if b.get("status") not in ("validated",) and b.get("name")
        ]
        # Also get failing scenario IDs from the last iter
        failed_ids = json.loads(failed_ids_path.read_text()) if failed_ids_path.exists() else []
        iteration_offset = len(iter_dirs)

        print(f"\nCFV-ONLY mode:", flush=True)
        print(f"  Last fix iter: {last_iter_dir.name}", flush=True)
        print(f"  Unresolved buckets: {unresolved_buckets}", flush=True)
        print(f"  Failed scenario IDs: {len(failed_ids)}", flush=True)

        # Set MAX_ITERATIONS = 0 to skip the fix loop
        MAX_ITERATIONS = 0

        # Synthesise a Phase A result so the heal loop has a denominator for projected rate
        # Use 248/280 baseline from the morning's completed run
        syn_results_dir = Path("/tmp/ab_heal_results")
        syn_results_dir.mkdir(parents=True, exist_ok=True)
        _clear_checkpoint(syn_results_dir)
        existing_ab = syn_results_dir / "ab_results.json"
        # Only write synthetic if file is missing or tiny (don't overwrite a real run)
        if not existing_ab.exists() or existing_ab.stat().st_size < 5000:
            existing_ab.write_text(json.dumps({
                "summary": {
                    "one_live_passes": 280 - len(failed_ids),
                    "total": 280,
                    "one_live_rate": f"{(280 - len(failed_ids)) / 280 * 100:.1f}%",
                    "one_live_cost_usd_total": 0.0,
                },
                "results": [
                    {"scenario_id": sid, "one_live_pass": False, "one_live_composite": 0}
                    for sid in failed_ids
                ],
            }))
            print(f"  Wrote synthetic Phase A baseline ({len(failed_ids)} failures) → {existing_ab}",
                  flush=True)
        args.skip_full_validation = True
        args.results_dir = str(syn_results_dir)

    result = await run_heal_loop(
        dry_run=args.dry_run,
        skip_full_validation=getattr(args, "skip_full_validation", False),
        workers=args.workers,
        results_dir=getattr(args, "results_dir", None),
    )

    print("\n" + "=" * 60)
    print("HEAL LOOP COMPLETE")
    print("=" * 60)
    print(f"  Phase A (baseline): {result.get('phase_a_pass_rate', 0):.1%}")
    print(f"  Phase E (final):    {result.get('phase_e_pass_rate', 0):.1%}")
    improvement = result.get("phase_e_pass_rate", 0) - result.get("phase_a_pass_rate", 0)
    print(f"  Improvement:        {improvement:+.1%}")
    print(f"  Fix iterations:     {len(result.get('iterations', []))}/{MAX_ITERATIONS}")
    print(f"  Total cost:         ${result.get('total_cost_usd', 0):.2f}")
    print(f"  Deployed:           {result.get('deployed', False)}")
    print(f"  Canary passed:      {result.get('canary_passed', False)}")
    print(f"  History:            {HEAL_HISTORY_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
