"""
Fix Applier — Applies code changes to disk, restarts service, and reverts on failure.

Features:
  - Exact-match with verbose failure logging (dumps excerpt vs old_code on mismatch)
  - Per-file backup (.bak) before modification
  - Automatic revert if health check fails after restart
  - Health wait increased to 60s
"""

import asyncio
import hashlib
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class FixApplier:
    """Applies code fixes and restarts the service."""

    def __init__(self, repo_root: str = None):
        """Initialize fix applier."""
        self.repo_root = Path(repo_root or os.environ.get("SAILLY_REPO_ROOT", "/home/charles2/sailly-browser-demo"))
        # Track diffs (hashes of old_code+new_code) already applied this session
        # to avoid re-proposing duplicate fixes across attempts
        self._applied_diffs: set[str] = set()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def apply_fixes(self, fix_plan: Dict[str, Any]) -> bool:
        """
        Apply fixes from the fix plan.

        Returns True if at least one fix was applied and the service is healthy.
        On health-check failure, all modified files are reverted from .bak copies.
        """
        fixes = fix_plan.get("fixes", [])
        if not fixes:
            logger.warning("[fix_applier] No fixes in plan — skipping restart")
            return False

        logger.info("[fix_applier] Applying %d fix(es) | priority=%s", len(fixes), fix_plan.get("priority", "?"))

        applied_files: List[Path] = []
        any_applied = False

        for i, fix in enumerate(fixes):
            success, modified_path = await self._apply_single_fix(fix, fix_number=i + 1)
            if success and modified_path:
                any_applied = True
                applied_files.append(modified_path)
            else:
                logger.error(
                    "[fix_applier] Fix %d/%d failed (%s) — continuing with remaining fixes",
                    i + 1, len(fixes), fix.get("file", "?"),
                )

        if not any_applied:
            logger.warning("[fix_applier] Zero fixes applied — skipping restart")
            return False

        logger.info("[fix_applier] %d/%d fixes applied — restarting service", len(applied_files), len(fixes))
        success = await self._restart_service()

        if not success:
            logger.error("[fix_applier] Service unhealthy after restart — reverting %d file(s)", len(applied_files))
            self._revert_backups(applied_files)
            # Restart once more after revert
            await self._restart_service()
            return False

        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _apply_single_fix(self, fix: Dict[str, Any], fix_number: int = 0) -> Tuple[bool, Path | None]:
        """
        Apply one fix to disk.

        Returns (success, modified_path).
        modified_path is None when fix is skipped or fails.
        """
        file_rel = fix.get("file", "")
        old_code = fix.get("old_code", "")
        new_code = fix.get("new_code", "")

        if not file_rel or not old_code or not new_code:
            logger.warning("[fix_applier] Fix #%d incomplete (missing file/old_code/new_code): %s", fix_number, fix)
            return False, None

        if old_code == new_code:
            logger.warning("[fix_applier] Fix #%d is a no-op (old==new) in %s", fix_number, file_rel)
            return False, None

        # Check for duplicate fix (same old_code + new_code already applied this session)
        diff_hash = hashlib.sha256((old_code + new_code).encode()).hexdigest()[:12]
        if diff_hash in self._applied_diffs:
            logger.warning("[fix_applier] Fix #%d is a duplicate (already tried this session) in %s [hash=%s]",
                          fix_number, file_rel, diff_hash)
            return False, None

        full_path = self.repo_root / file_rel

        if not full_path.exists():
            logger.error("[fix_applier] Fix #%d: file not found: %s", fix_number, full_path)
            return False, None

        try:
            content = full_path.read_text(encoding="utf-8")

            if old_code not in content:
                # Verbose failure: show first 200 chars of both sides
                excerpt_start = content.find(old_code[:30]) if len(old_code) >= 30 else -1
                file_excerpt = (
                    content[max(0, excerpt_start - 50):excerpt_start + 200]
                    if excerpt_start >= 0
                    else content[:200]
                )
                logger.error(
                    "[fix_applier] Fix #%d EXACT MATCH FAILED in %s\n"
                    "  old_code[:200]  = %r\n"
                    "  file_excerpt    = %r",
                    fix_number, file_rel,
                    old_code[:200],
                    file_excerpt,
                )
                return False, None

            # Backup before modification
            bak_path = full_path.with_suffix(full_path.suffix + ".bak")
            shutil.copy2(full_path, bak_path)
            logger.debug("[fix_applier] Backup created: %s", bak_path.name)

            # Apply (replace first occurrence only)
            new_content = content.replace(old_code, new_code, 1)

            # ── Syntax validation for Python files ──────────────────────────
            if full_path.suffix == ".py":
                import ast as _ast
                try:
                    _ast.parse(new_content)
                except SyntaxError as _syn_err:
                    logger.error(
                        "[fix_applier] Fix #%d REJECTED — syntax error in %s after patch: %s",
                        fix_number, file_rel, _syn_err
                    )
                    # Restore backup to clean state
                    shutil.copy2(bak_path, full_path)
                    return False, None

            full_path.write_text(new_content, encoding="utf-8")
            logger.info("[fix_applier] Fix #%d applied to %s (%+d bytes)",
                        fix_number, file_rel, len(new_content) - len(content))
            
            # Track this diff so we don't re-propose it
            diff_hash = hashlib.sha256((old_code + new_code).encode()).hexdigest()[:12]
            self._applied_diffs.add(diff_hash)
            
            return True, full_path

        except Exception as exc:
            logger.error("[fix_applier] Fix #%d error writing %s: %s", fix_number, file_rel, exc)
            return False, None

    def _revert_backups(self, modified_files: List[Path]) -> None:
        """Restore .bak files for all modified paths."""
        for path in modified_files:
            bak = path.with_suffix(path.suffix + ".bak")
            if bak.exists():
                try:
                    shutil.copy2(bak, path)
                    logger.info("[fix_applier] Reverted %s from backup", path.name)
                except Exception as exc:
                    logger.error("[fix_applier] Revert failed for %s: %s", path, exc)
            else:
                logger.warning("[fix_applier] No backup found for %s — cannot revert", path)

    def revert_last(self) -> None:
        """Revert all .bak files in the project (used when score regresses after fixes)."""
        repo_root = Path(self.repo_root)
        backed_up = list(repo_root.rglob("*.bak"))
        for bak in backed_up:
            original = bak.with_suffix("")
            if original.exists():
                try:
                    shutil.copy2(bak, original)
                    logger.info("[fix_applier.revert_last] Reverted %s from backup", original.name)
                    bak.unlink()
                except Exception as exc:
                    logger.error("[fix_applier.revert_last] Failed to revert %s: %s", original, exc)

    async def _restart_service(self) -> bool:
        """
        Stop the running Sailly service, start it fresh, and wait up to 60s for health.
        Uses sudo pkill to handle cross-user process ownership.
        """
        try:
            logger.info("[fix_applier] Stopping existing service process...")
            # Try sudo pkill first (handles cross-user ownership), fall back to plain pkill.
            kill_result = subprocess.run(
                ["sudo", "-n", "pkill", "-9", "-f", "uvicorn.*server.main"],
                capture_output=True, timeout=5,
            )
            if kill_result.returncode != 0:
                subprocess.run(
                    ["pkill", "-9", "-f", "uvicorn.*server.main"],
                    capture_output=True, timeout=5,
                )
            await asyncio.sleep(3)

            logger.info("[fix_applier] Starting service on port 8080...")
            venv_python = str(Path(self.repo_root) / "venv" / "bin" / "python3")
            subprocess.Popen(
                [venv_python, "-m", "uvicorn", "server.main:app",
                 "--host", "0.0.0.0", "--port", "8080"],
                cwd=str(self.repo_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "PYTHONUNBUFFERED": "1", "SKIP_VERTEX_PREFLIGHT": "1"},
            )

            logger.info("[fix_applier] Waiting for service (up to 60s)...")
            ready = await self._wait_for_service(max_wait_sec=60)

            if ready:
                logger.info("[fix_applier] Service is healthy")
                return True
            else:
                logger.error("[fix_applier] Service did NOT become healthy within 60s")
                return False

        except Exception as exc:
            logger.error("[fix_applier] _restart_service error: %s", exc)
            return False

    async def _wait_for_service(self, max_wait_sec: int = 60) -> bool:
        """Poll /health every 2s until 200 or timeout."""
        try:
            import aiohttp
        except ImportError:
            logger.warning("[fix_applier] aiohttp not available — assuming service ready after sleep")
            await asyncio.sleep(30)
            return True

        health_url = os.environ.get("SAILLY_HEALTH_URL", "http://localhost:8080/health")
        deadline = time.monotonic() + max_wait_sec

        while time.monotonic() < deadline:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        health_url, timeout=aiohttp.ClientTimeout(total=3)
                    ) as resp:
                        if resp.status == 200:
                            return True
            except Exception:
                pass
            await asyncio.sleep(2)

        return False
