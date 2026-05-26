"""Periodic GDPR transcript-retention purge.

Sailly retains only *transcripts* (never raw audio), which reduces the legal
surface area (no §201 StGB audio-recording issue). Still, GDPR Art. 5(1)(e)
requires that personal data not be kept longer than necessary. This module
deletes records older than ``TranscriptPurge.retention_days`` from the
transcript-related Postgres tables on a fixed schedule.

Design notes:
- Cascades on ``google_calls.id`` delete rows in ``google_transcripts`` and
  ``google_tool_calls``. We still delete both tables explicitly so the code
  works whether or not FK ON DELETE CASCADE is set in the schema.
- We never run the purge in dry-run silent mode; every run logs the deleted
  row counts so operators can reconcile.
- Default retention = ``TRANSCRIPT_RETENTION_DAYS`` env var or 90 days.
- Failures are swallowed and logged so a bad DB doesn't crash the app.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger


class TranscriptPurge:
    """Background task that deletes old transcript rows once per ``interval_s``."""

    def __init__(
        self,
        retention_days: Optional[int] = None,
        interval_s: int = 6 * 3600,  # every 6h by default
    ):
        env_days = os.getenv("TRANSCRIPT_RETENTION_DAYS")
        default_days = 90
        if retention_days is not None:
            self.retention_days = int(retention_days)
        elif env_days:
            try:
                self.retention_days = int(env_days)
            except ValueError:
                self.retention_days = default_days
        else:
            self.retention_days = default_days
        self.interval_s = int(interval_s)
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_forever(), name="transcript_purge")
        logger.info(
            f"[PURGE] started — retention_days={self.retention_days} "
            f"interval_s={self.interval_s}"
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):
            pass
        self._task = None

    async def _run_forever(self) -> None:
        while True:
            try:
                await self.purge_once()
            except Exception as e:  # pragma: no cover — never crash the loop
                logger.error(f"[PURGE] purge_once crashed: {e!r}")
            try:
                await asyncio.sleep(self.interval_s)
            except asyncio.CancelledError:
                raise

    async def purge_once(self) -> dict:
        """Run one purge pass and return a summary of rows deleted."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        summary = {
            "cutoff": cutoff.isoformat(),
            "deleted_calls": 0,
            "deleted_transcripts": 0,
            "deleted_tool_calls": 0,
        }
        try:
            from server.database import get_pool  # lazy to avoid import-time DB connect
        except Exception as e:
            logger.warning(f"[PURGE] database module unavailable: {e!r}")
            return summary
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                async with conn.transaction():
                    summary["deleted_transcripts"] = _rowcount(await conn.execute(
                        "DELETE FROM google_transcripts WHERE call_id IN "
                        "(SELECT id FROM google_calls WHERE started_at < $1)",
                        cutoff,
                    ))
                    summary["deleted_tool_calls"] = _rowcount(await conn.execute(
                        "DELETE FROM google_tool_calls WHERE call_id IN "
                        "(SELECT id FROM google_calls WHERE started_at < $1)",
                        cutoff,
                    ))
                    summary["deleted_calls"] = _rowcount(await conn.execute(
                        "DELETE FROM google_calls WHERE started_at < $1",
                        cutoff,
                    ))
        except Exception as e:
            logger.error(f"[PURGE] DB purge failed: {e!r}")
            return summary
        logger.info(
            f"[PURGE] deleted transcripts={summary['deleted_transcripts']} "
            f"tool_calls={summary['deleted_tool_calls']} calls={summary['deleted_calls']} "
            f"(cutoff={summary['cutoff']})"
        )
        return summary


def _rowcount(status: str) -> int:
    """Parse the trailing integer from an asyncpg command status string.
    e.g. ``"DELETE 12"`` → 12. Defensive: returns 0 on any parse failure.
    """
    try:
        return int(str(status).split()[-1])
    except (ValueError, IndexError):
        return 0


# Module-level singleton so the FastAPI startup hook can just call
# `purge_task.start()` without managing state.
purge_task = TranscriptPurge()
