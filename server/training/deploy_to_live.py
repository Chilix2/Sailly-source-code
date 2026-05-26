"""
Deploy-to-Live — Git commit, file sync, restart agent, smoke verify, auto-rollback.

Called after a bucket passes. Deploys the latest fixes to the live demo environment.
"""

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class DeployResult:
    """Result of a deployment attempt."""
    deployed: bool
    bucket: str
    pass_rate: float
    commit_hash: Optional[str] = None
    smoke_result: Optional[bool] = None
    error: Optional[str] = None
    files_synced: int = 0


class DeployToLive:
    """
    Deploys validated fixes to the live demo environment.

    Architecture note:
        sailly.tech/ws/demo  →  nginx upstream sailly_demo  →  127.0.0.1:3003
        Port 3003 IS the demo.  It is managed by sailly-voice-agent.service.
        No rsync needed — the repo IS the running code.
    """

    # git binary (not on $PATH for non-charles2 users)
    GIT = "/home/charles2/bin/git"
    SERVICE = "sailly-voice-agent"

    def __init__(
        self,
        repo_dir: str = "/home/charles2/sailly-google-fork",
        demo_host: str = "localhost",
        demo_port: int = 3003,
        demo_user: str = "charles2",
    ):
        self.repo_dir = Path(repo_dir)
        self.demo_host = demo_host
        self.demo_port = demo_port
        self.demo_user = demo_user

    async def _run_cmd(
        self,
        cmd: str,
        cwd: Optional[Path] = None,
        timeout_s: float = 30.0,
    ) -> tuple[int, str, str]:
        """
        Run a shell command and return (returncode, stdout, stderr).
        """
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=cwd or self.repo_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_s,
                )
                return (
                    proc.returncode or 0,
                    stdout.decode("utf-8", errors="ignore"),
                    stderr.decode("utf-8", errors="ignore"),
                )
            except asyncio.TimeoutError:
                proc.kill()
                return (1, "", f"Command timed out after {timeout_s}s")
        except Exception as e:
            return (1, "", str(e))

    async def git_commit(self, bucket_name: str, pass_rate: float) -> Optional[str]:
        """Git commit all changes. pass_rate is 0-100 percentage."""
        message = f"[auto-deploy] {bucket_name} passed at {pass_rate:.1f}%"

        rc, out, err = await self._run_cmd(f"{self.GIT} add -A")
        if rc != 0:
            logger.warning(f"git add failed (no git or no changes): {err}")
        
        rc, out, err = await self._run_cmd(f'{self.GIT} commit -m "{message}"')
        if rc != 0:
            logger.info(f"git commit skipped (no changes or no git): {err[:80]}")

        # Return current HEAD regardless
        rc, out, _ = await self._run_cmd(f"{self.GIT} rev-parse HEAD")
        if rc == 0:
            commit_hash = out.strip()
            logger.info(f"HEAD: {commit_hash[:8]} — {message}")
            return commit_hash

        logger.warning("Could not get HEAD hash, using timestamp")
        from datetime import datetime
        return datetime.utcnow().strftime("nongit-%Y%m%d-%H%M%S")

    async def git_push(self) -> bool:
        """Push to remote for backup."""
        rc, out, err = await self._run_cmd(f"{self.GIT} push origin HEAD", timeout_s=60.0)
        if rc != 0:
            logger.warning(f"git push failed: {err[:80]}")
            return False
        logger.info("Pushed to remote")
        return True

    async def sync_files_to_demo(self) -> int:
        """
        Sync modified files to live demo environment via rsync/scp.
        
        Modified files include:
            - server/training/node_manager.py
            - server/training/check_forced_commits.py
            - Any other files changed by the fix
        
        Returns:
            Number of files synced (or -1 on error).
        """
        # If demo_host is localhost, no sync needed (same machine)
        if self.demo_host in ("localhost", "127.0.0.1", "0.0.0.0"):
            logger.info("Demo is on localhost, skipping file sync")
            return 0

        # Build list of critical files to sync
        files_to_sync = [
            "server/training/node_manager.py",
            "server/training/check_forced_commits.py",
            "server/adk_brain_service.py",
        ]

        demo_path = f"{self.demo_user}@{self.demo_host}:/home/{self.demo_user}/sailly-google-fork/"
        synced_count = 0

        for file_path in files_to_sync:
            src = self.repo_dir / file_path
            if not src.exists():
                logger.debug(f"File not found locally, skipping: {file_path}")
                continue

            # rsync file to demo
            cmd = f"rsync -avz {src} {demo_path}{file_path}"
            rc, out, err = await self._run_cmd(cmd, timeout_s=30.0)
            if rc != 0:
                logger.warning(f"rsync {file_path} failed: {err}")
            else:
                synced_count += 1
                logger.info(f"Synced {file_path}")

        return synced_count

    async def restart_agent(self, timeout_s: float = 60.0) -> bool:
        """
        Restart the voice agent (sailly-voice-agent.service on port 3003).

        Tries systemctl first; falls back to SIGTERM + relaunch if that fails.
        """
        # Option 1: systemctl (works if sudoers grants this)
        rc, out, err = await self._run_cmd(
            f"sudo systemctl restart {self.SERVICE}",
            timeout_s=timeout_s,
        )
        if rc == 0:
            logger.info(f"Restarted {self.SERVICE} via systemctl")
            await asyncio.sleep(3)
            return True

        logger.warning(f"systemctl restart failed ({err[:60]}), trying direct kill+restart")

        # Option 2: kill the PID listening on port 3003, systemd auto-restarts it
        rc, out, err = await self._run_cmd(
            f"sudo fuser -k {self.demo_port}/tcp", timeout_s=10.0
        )
        if rc == 0:
            logger.info(f"Killed port {self.demo_port}, systemd will auto-restart")
            await asyncio.sleep(8)  # wait for Restart=on-failure
            return True

        logger.warning(f"Could not restart agent: {err[:80]}")
        return False

    async def wait_for_health(self, timeout_s: float = 30.0) -> bool:
        """
        Wait for the voice agent to be healthy (health check passes).
        
        Returns:
            True if healthy, False if timeout.
        """
        health_url = f"http://{self.demo_host}:{self.demo_port}/health"
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout_s:
            try:
                cmd = f"curl -s -o /dev/null -w '%{{http_code}}' {health_url}"
                rc, out, err = await self._run_cmd(cmd, timeout_s=5.0)
                if rc == 0 and "200" in out:
                    logger.info("Health check passed")
                    return True
            except Exception as e:
                logger.debug(f"Health check error: {e}")

            await asyncio.sleep(1)

        logger.error(f"Health check timed out after {timeout_s}s")
        return False

    async def smoke_verify(self) -> Optional[bool]:
        """
        Quick health check: WebSocket connects and /health returns 200.
        Full scenario smoke runs in the RBV loop itself; this is just a
        liveness check after the restart.
        """
        logger.info("Running post-deploy health check...")

        # 1. HTTP health
        health_ok = await self.wait_for_health(timeout_s=30.0)
        if not health_ok:
            return False

        # 2. WebSocket connects
        try:
            import websockets
            ws_url = f"ws://{self.demo_host}:{self.demo_port}/ws/demo"
            ws = await asyncio.wait_for(
                websockets.connect(ws_url), timeout=8
            )
            await ws.close()
            logger.info("WS /ws/demo: OK")
            return True
        except Exception as e:
            logger.error(f"WS health check failed: {e}")
            return False

    async def rollback(self, commit_hash: Optional[str]) -> bool:
        """
        Revert the last commit (undo the deployment).
        
        Args:
            commit_hash: Commit to revert from (if known)
        
        Returns:
            True if rollback succeeded, False otherwise.
        """
        logger.warning("Rolling back deployment...")

        # Revert HEAD
        rc, out, err = await self._run_cmd("git revert --no-commit HEAD", timeout_s=30.0)
        if rc != 0:
            logger.error(f"git revert failed: {err}")
            return False

        # Commit revert
        rc, out, err = await self._run_cmd(
            'git commit -m "[rollback] Deploy failed smoke test"',
            timeout_s=30.0,
        )
        if rc != 0:
            logger.error(f"git commit (revert) failed: {err}")
            return False

        # Restart agent to pick up reverted code
        await self.restart_agent()
        logger.info("Rollback completed")
        return True

    async def deploy(self, bucket_name: str, pass_rate: float) -> DeployResult:
        """
        Full deployment cycle:
        1. Git commit
        2. Sync files to demo (if remote)
        3. Restart voice agent
        4. Wait for health
        5. Smoke verify
        6. Auto-rollback if smoke fails
        
        Args:
            bucket_name: Bucket name (for commit message)
            pass_rate: Pass rate of the bucket
        
        Returns:
            DeployResult object
        """
        logger.info(f"Starting deployment for {bucket_name} ({pass_rate:.1f}%)")

        # 1. Git commit
        commit_hash = await self.git_commit(bucket_name, pass_rate)
        if not commit_hash:
            return DeployResult(
                deployed=False,
                bucket=bucket_name,
                pass_rate=pass_rate,
                error="git commit failed",
            )

        # 2. Git push (for backup)
        await self.git_push()

        # 3. Sync files (if remote)
        files_synced = await self.sync_files_to_demo()

        # 4. Restart agent
        if not await self.restart_agent():
            await self.rollback(commit_hash)
            return DeployResult(
                deployed=False,
                bucket=bucket_name,
                pass_rate=pass_rate,
                commit_hash=commit_hash,
                error="Agent restart failed",
            )

        # 5. Wait for health
        if not await self.wait_for_health():
            await self.rollback(commit_hash)
            return DeployResult(
                deployed=False,
                bucket=bucket_name,
                pass_rate=pass_rate,
                commit_hash=commit_hash,
                error="Health check timeout",
            )

        # 6. Smoke verify
        smoke_result = await self.smoke_verify()
        if smoke_result is False:
            # Smoke failed, rollback
            await self.rollback(commit_hash)
            return DeployResult(
                deployed=False,
                bucket=bucket_name,
                pass_rate=pass_rate,
                commit_hash=commit_hash,
                smoke_result=False,
                error="Smoke test failed after deploy",
            )

        # Success!
        logger.info(f"Deployment successful: {bucket_name} live")
        return DeployResult(
            deployed=True,
            bucket=bucket_name,
            pass_rate=pass_rate,
            commit_hash=commit_hash,
            smoke_result=smoke_result,
            files_synced=files_synced,
        )


async def demo():
    deployer = DeployToLive()
    result = await deployer.deploy("1_order", 0.87)
    print(f"Deployment result: {result}")


if __name__ == "__main__":
    asyncio.run(demo())
