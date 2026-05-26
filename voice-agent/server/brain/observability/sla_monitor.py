"""
SLA monitor — periodic check of p95 latency and error rate (9.O8).

Runs every 5 minutes, either via systemd timer, pg_cron, or as a
background asyncio task started in server/main.py.

Usage (as background task from main.py):

    import asyncio
    from server.brain.observability.sla_monitor import start_monitor

    # In app startup:
    asyncio.create_task(start_monitor())

Environment:
    DATABASE_URL — asyncpg-compatible DSN for the read replica
    SLACK_ALERTS_WEBHOOK — set to receive alerts
"""
from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS: int = 5 * 60       # run every 5 minutes
P95_LATENCY_SLO_MS: int = 2500            # alert if p95 total_ms exceeds this
ERROR_RATE_SLO: float = 0.05              # alert if error rate exceeds 5%
TRANSFER_SPIKE_MULTIPLIER: float = 2.5    # alert if rate is N× the prior period


# ── Core SLA check ────────────────────────────────────────────────────────────

async def check_sla() -> None:
    """
    Run all SLA checks against the last 5-minute window.
    Silently skips if DATABASE_URL is not configured.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.debug("sla_monitor: DATABASE_URL not set — checks skipped")
        return

    try:
        import asyncpg  # type: ignore
    except ImportError:
        logger.warning("sla_monitor: asyncpg not installed — checks skipped")
        return

    try:
        conn = await asyncpg.connect(db_url)
    except Exception as exc:
        logger.warning("sla_monitor: DB connect failed: %s", exc)
        return

    try:
        await _check_latency(conn)
        await _check_error_rate(conn)
        await _check_transfer_rate(conn)
    finally:
        await conn.close()


async def _check_latency(conn) -> None:
    from server.brain.observability.alerts import alert_p95_latency_breach

    p95 = await conn.fetchval(
        """
        SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_ms)
        FROM google_turn_metrics
        WHERE created_at > now() - interval '5 minutes'
          AND total_ms IS NOT NULL
        """
    )
    if p95 is not None and p95 > P95_LATENCY_SLO_MS:
        logger.warning("sla_monitor: p95 latency breach — %.0fms", p95)
        await alert_p95_latency_breach(int(p95), "5min")


async def _check_error_rate(conn) -> None:
    from server.brain.observability.alerts import alert_high_error_rate

    error_rate = await conn.fetchval(
        """
        SELECT
            COUNT(*) FILTER (WHERE error_codes IS NOT NULL
                                AND array_length(error_codes, 1) > 0
            )::FLOAT / NULLIF(COUNT(*), 0)
        FROM google_turn_metrics
        WHERE created_at > now() - interval '5 minutes'
        """
    )
    if error_rate is not None and error_rate > ERROR_RATE_SLO:
        top_rows = await conn.fetch(
            """
            SELECT unnest(error_codes) AS code, COUNT(*) AS n
            FROM google_turn_metrics
            WHERE created_at > now() - interval '5 minutes'
              AND error_codes IS NOT NULL
            GROUP BY code
            ORDER BY n DESC
            LIMIT 5
            """
        )
        top_codes = [r["code"] for r in top_rows]
        logger.warning("sla_monitor: error rate breach — %.2f%%", error_rate * 100)
        await alert_high_error_rate(error_rate, top_codes, "5min")


async def _check_transfer_rate(conn) -> None:
    """Alert if transfer rate this window is 2.5× the prior window."""
    from server.brain.observability.alerts import alert_transfer_spike

    row = await conn.fetchrow(
        """
        SELECT
            -- Current 5-min window
            COUNT(*) FILTER (
                WHERE created_at > now() - interval '5 minutes'
                  AND tools_called::text ILIKE '%transfer_to_human%'
            )::FLOAT / NULLIF(
                COUNT(*) FILTER (WHERE created_at > now() - interval '5 minutes'), 0
            ) AS current_rate,
            -- Prior 5-min window (5–10 min ago) as baseline
            COUNT(*) FILTER (
                WHERE created_at BETWEEN now() - interval '10 minutes' AND now() - interval '5 minutes'
                  AND tools_called::text ILIKE '%transfer_to_human%'
            )::FLOAT / NULLIF(
                COUNT(*) FILTER (
                    WHERE created_at BETWEEN now() - interval '10 minutes' AND now() - interval '5 minutes'
                ), 0
            ) AS baseline_rate
        FROM google_turn_metrics
        """
    )
    if row is None:
        return

    current = row["current_rate"] or 0.0
    baseline = row["baseline_rate"] or 0.0

    if baseline > 0.0 and current >= baseline * TRANSFER_SPIKE_MULTIPLIER and current >= 0.10:
        logger.warning(
            "sla_monitor: transfer spike — %.1f%% vs baseline %.1f%%",
            current * 100, baseline * 100,
        )
        await alert_transfer_spike(current, baseline, "5min")


# ── Background task entry point ───────────────────────────────────────────────

async def start_monitor() -> None:
    """
    Run `check_sla` in an infinite loop with CHECK_INTERVAL_SECONDS delay.
    Exceptions are caught and logged so the task never dies silently.
    """
    logger.info("sla_monitor: starting (interval=%ds)", CHECK_INTERVAL_SECONDS)
    while True:
        try:
            await check_sla()
        except Exception as exc:
            logger.exception("sla_monitor: unexpected error in check_sla: %s", exc)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
