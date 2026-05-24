"""
validation_dashboard_server.py — Custom HTTP server for the validation dashboard.

Replaces 'python -m http.server 8090 -d /tmp/validation_runs'.
Serves static files AND handles POST API endpoints for the CFV manual control features.

Endpoints:
  GET  /*                  — Serve static files from RUNS_ROOT
  POST /api/instruction    — Save human instruction + trigger async bucket re-run
  POST /api/select-attempt — Mark an attempt as selected for cherry-pick deployment
  POST /api/deploy-selected— Apply selected attempt's patches + mark bucket resolved_manual

Run as: python -m server.training.validation_dashboard_server
Or as systemd service (see sailly-validation-static.service).
"""

import asyncio
import json
import logging
import mimetypes
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

RUNS_ROOT = Path("/tmp/validation_runs")
PORT = 8090
VENV_PYTHON = Path("/home/charles2/sailly-google-fork/.venv/bin/python3")
MODULE_ROOT = Path("/home/charles2/sailly-google-fork")
LOCK_FILE = Path("/tmp/validation_heal_loop.lock")
CONTROL_FILE = RUNS_ROOT / "control_signal.json"
STATUS_FILE = RUNS_ROOT / "heal_loop_status.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DashSrv] %(message)s")
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ok(handler, data: dict) -> None:
    body = json.dumps({"ok": True, **data}).encode()
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _err(handler, msg: str, status: int = 400) -> None:
    body = json.dumps({"ok": False, "error": msg}).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str))


def _find_cfv_run_dir(run_dir_hint: str) -> Path | None:
    """Resolve the cfv_iter_N directory from a run_dir hint like 'cfv_iter_8'."""
    if run_dir_hint:
        candidate = RUNS_ROOT / Path(run_dir_hint).name
        if candidate.exists() and (candidate / "cfv_state.json").exists():
            return candidate
    # Fallback: find the most recent cfv_iter_* directory
    dirs = sorted(RUNS_ROOT.glob("cfv_iter_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0] if dirs else None


# ── API handlers ───────────────────────────────────────────────────────────────

def handle_instruction(handler, body: dict) -> None:
    """
    POST /api/instruction
    Body: { "bucket": "verify_address", "instruction": "...", "run_dir": "cfv_iter_8" }

    Saves the instruction to disk and spawns an async subprocess to run one CFV attempt.
    """
    bucket = body.get("bucket", "").strip()
    instruction = body.get("instruction", "").strip()
    run_dir_hint = body.get("run_dir", "")

    if not bucket:
        return _err(handler, "bucket is required")

    run_dir = _find_cfv_run_dir(run_dir_hint)
    if not run_dir:
        return _err(handler, "CFV run directory not found")

    # Save instruction to disk
    instr_file = run_dir / f"human_instruction_{bucket}.json"
    _write_json(instr_file, {
        "bucket": bucket,
        "instruction": instruction,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(f"[DashSrv] Saved instruction for '{bucket}' to {instr_file}")

    # Update cfv_state.json to mark bucket as awaiting re-run
    state_file = run_dir / "cfv_state.json"
    if state_file.exists():
        state = _read_json(state_file)
        for b in state.get("buckets", []):
            if b.get("name") == bucket:
                b["pending_instruction"] = instruction[:200]
                b["instruction_submitted_at"] = datetime.now(timezone.utc).isoformat()
                break
        state["status"] = "running"
        _write_json(state_file, state)

    # Spawn a subprocess to run one more attempt for this bucket
    env = os.environ.copy()
    cmd = [
        str(VENV_PYTHON), "-m", "server.training.cfv_manual_runner",
        "--bucket", bucket,
        "--run-dir", str(run_dir),
    ]
    if instruction:
        cmd += ["--instruction", instruction]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(MODULE_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info(f"[DashSrv] Spawned cfv_manual_runner PID={proc.pid} for bucket '{bucket}'")
        _ok(handler, {"message": f"Re-run triggered for bucket '{bucket}' (PID {proc.pid})", "pid": proc.pid})
    except Exception as e:
        logger.error(f"[DashSrv] Failed to spawn cfv_manual_runner: {e}")
        _err(handler, f"Failed to start re-run: {e}")


def handle_select_attempt(handler, body: dict) -> None:
    """
    POST /api/select-attempt
    Body: { "bucket": "verify_address", "attempt": 3, "run_dir": "cfv_iter_8" }

    Marks an attempt as selected in cfv_state.json for later cherry-pick deployment.
    """
    bucket = body.get("bucket", "").strip()
    attempt = body.get("attempt")
    run_dir_hint = body.get("run_dir", "")

    if not bucket or attempt is None:
        return _err(handler, "bucket and attempt are required")

    run_dir = _find_cfv_run_dir(run_dir_hint)
    if not run_dir:
        return _err(handler, "CFV run directory not found")

    state_file = run_dir / "cfv_state.json"
    if not state_file.exists():
        return _err(handler, "cfv_state.json not found")

    state = _read_json(state_file)
    found = False
    for b in state.get("buckets", []):
        if b.get("name") == bucket:
            # Toggle: if same attempt clicked again, deselect
            if b.get("selected_attempt") == attempt:
                b.pop("selected_attempt", None)
                msg = f"Deselected attempt #{attempt} for bucket '{bucket}'"
            else:
                b["selected_attempt"] = attempt
                msg = f"Selected attempt #{attempt} for bucket '{bucket}'"
            found = True
            break

    if not found:
        return _err(handler, f"Bucket '{bucket}' not found in cfv_state.json")

    _write_json(state_file, state)
    logger.info(f"[DashSrv] {msg}")
    _ok(handler, {"message": msg})


def handle_deploy_selected(handler, body: dict) -> None:
    """
    POST /api/deploy-selected
    Body: { "bucket": "verify_address", "run_dir": "cfv_iter_8" }

    Applies the patches from the selected attempt and marks the bucket as resolved_manual.
    Also adds the scenario IDs to a deploy_manifest.json so the heal loop picks them up.
    """
    bucket = body.get("bucket", "").strip()
    run_dir_hint = body.get("run_dir", "")

    if not bucket:
        return _err(handler, "bucket is required")

    run_dir = _find_cfv_run_dir(run_dir_hint)
    if not run_dir:
        return _err(handler, "CFV run directory not found")

    state_file = run_dir / "cfv_state.json"
    if not state_file.exists():
        return _err(handler, "cfv_state.json not found")

    state = _read_json(state_file)
    bucket_state = None
    for b in state.get("buckets", []):
        if b.get("name") == bucket:
            bucket_state = b
            break

    if not bucket_state:
        return _err(handler, f"Bucket '{bucket}' not found")

    selected_attempt = bucket_state.get("selected_attempt")
    if not selected_attempt:
        return _err(handler, f"No attempt selected for bucket '{bucket}'")

    # Find the attempt record
    attempt_record = None
    for ar in bucket_state.get("attempt_records", []):
        if ar.get("attempt") == selected_attempt:
            attempt_record = ar
            break

    if not attempt_record:
        return _err(handler, f"Attempt #{selected_attempt} record not found for bucket '{bucket}'")

    patches = attempt_record.get("patches", [])
    if not patches:
        return _err(handler, f"Attempt #{selected_attempt} has no patch data stored (only description available)")

    # Spawn subprocess to apply patches and mark resolved_manual
    env = os.environ.copy()
    cmd = [
        str(VENV_PYTHON), "-m", "server.training.cfv_manual_runner",
        "--bucket", bucket,
        "--run-dir", str(run_dir),
        "--deploy-attempt", str(selected_attempt),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(MODULE_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info(f"[DashSrv] Spawned deploy PID={proc.pid} for bucket '{bucket}' attempt #{selected_attempt}")
        _ok(handler, {"message": f"Deploying attempt #{selected_attempt} for '{bucket}' (PID {proc.pid})"})
    except Exception as e:
        logger.error(f"[DashSrv] Failed to spawn deploy: {e}")
        _err(handler, f"Failed to start deploy: {e}")


# ── Loop control helpers ───────────────────────────────────────────────────────

def _find_heal_loop_pid() -> int | None:
    """Find the PID of the running validation_heal_loop process."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "validation_heal_loop"],
            capture_output=True, text=True
        )
        pids = [int(p) for p in result.stdout.strip().split() if p.isdigit()]
        return pids[0] if pids else None
    except Exception:
        return None


def _update_status(running: bool, paused: bool, phase: str = "") -> None:
    """Update heal_loop_status.json to reflect current state."""
    try:
        data = json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}
        data["running"] = running
        data["paused"] = paused
        if phase:
            data["phase"] = phase
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        STATUS_FILE.write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:
        logger.warning(f"[DashSrv] Could not update status file: {e}")


def _mark_manifest_stopped() -> None:
    """Mark the latest running entry in runs_manifest.json as stopped."""
    manifest = RUNS_ROOT / "runs_manifest.json"
    if not manifest.exists():
        return
    try:
        data = json.loads(manifest.read_text())
        runs = data.get("runs", data) if isinstance(data, dict) else data
        changed = False
        for r in runs:
            if r.get("status") == "running":
                r["status"] = "stopped"
                r["finished_at"] = datetime.now(timezone.utc).isoformat()
                changed = True
        if changed:
            if isinstance(data, dict):
                data["runs"] = runs
                manifest.write_text(json.dumps(data, indent=2, default=str))
            else:
                manifest.write_text(json.dumps(runs, indent=2, default=str))
    except Exception as e:
        logger.warning(f"[DashSrv] Could not update manifest: {e}")


def _regenerate_dashboard() -> None:
    """Regenerate index.html from runs_manifest.json."""
    try:
        subprocess.run(
            [str(VENV_PYTHON), "-c",
             "from server.training.unified_dashboard import write_dashboard;"
             "from pathlib import Path;"
             f"write_dashboard(Path('{RUNS_ROOT}'))"],
            cwd=str(MODULE_ROOT), capture_output=True, timeout=15
        )
    except Exception as e:
        logger.warning(f"[DashSrv] Dashboard regen failed: {e}")


def handle_stop_loop(handler, body: dict) -> None:
    """
    POST /api/stop-loop
    Gracefully stops the running validation_heal_loop via SIGTERM + control file.
    """
    pid = _find_heal_loop_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"[DashSrv] Sent SIGTERM to heal_loop PID={pid}")
        except ProcessLookupError:
            pass
        except PermissionError as e:
            return _err(handler, f"Permission denied killing PID {pid}: {e}")

    # Write control file as belt-and-suspenders
    CONTROL_FILE.write_text(json.dumps({"action": "stop", "requested_at": datetime.now(timezone.utc).isoformat()}))

    _update_status(running=False, paused=False, phase="stopped")
    _mark_manifest_stopped()
    _regenerate_dashboard()

    msg = f"Stop signal sent (PID={pid})" if pid else "No running loop found; manifest marked stopped"
    logger.info(f"[DashSrv] stop-loop: {msg}")
    _ok(handler, {"message": msg, "pid": pid})


def handle_start_loop(handler, body: dict) -> None:
    """
    POST /api/start-loop
    Starts a new validation_heal_loop run (--skip-full-validation --workers 20).
    Refuses if a loop is already running (lock file held).
    """
    if LOCK_FILE.exists():
        pid = _find_heal_loop_pid()
        if pid:
            return _err(handler, f"Validation loop already running (PID={pid}). Stop it first.")
        # Stale lock — remove it
        LOCK_FILE.unlink(missing_ok=True)
        logger.warning("[DashSrv] Removed stale lock file before starting new loop.")

    env = os.environ.copy()
    env["TTS_ENGINE"] = "gemini-flash"
    cmd = [
        str(VENV_PYTHON), "-m", "server.training.validation_heal_loop",
        "--skip-full-validation",
        "--workers", "20",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(MODULE_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info(f"[DashSrv] Started validation_heal_loop PID={proc.pid}")
        _ok(handler, {"message": f"Validation loop started (PID={proc.pid})", "pid": proc.pid})
    except Exception as e:
        logger.error(f"[DashSrv] Failed to start loop: {e}")
        _err(handler, f"Failed to start loop: {e}")


def handle_pause_loop(handler, body: dict) -> None:
    """
    POST /api/pause-loop
    Body: { "action": "pause" | "resume" }
    Pauses (SIGSTOP) or resumes (SIGCONT) the running loop.
    """
    action = body.get("action", "pause")
    pid = _find_heal_loop_pid()
    if not pid:
        return _err(handler, "No running validation loop found")

    try:
        if action == "resume":
            os.kill(pid, signal.SIGCONT)
            _update_status(running=True, paused=False, phase="resumed")
            msg = f"Loop resumed (PID={pid})"
        else:
            os.kill(pid, signal.SIGSTOP)
            _update_status(running=True, paused=True, phase="paused")
            msg = f"Loop paused (PID={pid})"
        logger.info(f"[DashSrv] pause-loop: {msg}")
        _ok(handler, {"message": msg, "pid": pid})
    except ProcessLookupError:
        _err(handler, f"Process {pid} no longer exists")
    except PermissionError as e:
        _err(handler, f"Permission denied: {e}")


# ── HTTP server ────────────────────────────────────────────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Suppress default access log for static files; only log API calls
        if self.path.startswith("/api/"):
            logger.info(f"{self.address_string()} {format % args}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        # Strip query string
        path = self.path.split("?")[0].split("#")[0]
        if path == "/" or not path:
            path = "/index.html"

        # Serve noautofix_deep results from /tmp/noautofix_deep/
        if path.startswith("/noautofix_deep/"):
            file_path = Path("/tmp/noautofix_deep") / path[len("/noautofix_deep/"):]
        else:
            file_path = RUNS_ROOT / path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            mime, _ = mimetypes.guess_type(str(file_path))
            mime = mime or "application/octet-stream"
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return _err(self, "Invalid JSON body")

        path = self.path.split("?")[0]
        if path == "/api/instruction":
            handle_instruction(self, body)
        elif path == "/api/select-attempt":
            handle_select_attempt(self, body)
        elif path == "/api/deploy-selected":
            handle_deploy_selected(self, body)
        elif path == "/api/stop-loop":
            handle_stop_loop(self, body)
        elif path == "/api/start-loop":
            handle_start_loop(self, body)
        elif path == "/api/pause-loop":
            handle_pause_loop(self, body)
        else:
            _err(self, f"Unknown endpoint: {path}", status=404)


def main():
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("", PORT), DashboardHandler)
    logger.info(f"[DashSrv] Serving {RUNS_ROOT} on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("[DashSrv] Stopping.")


if __name__ == "__main__":
    main()
