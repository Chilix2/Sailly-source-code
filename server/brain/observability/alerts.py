"""
Slack alerting for never-events and SLO breaches per decision critical-alerts (9.O8).

Design rules:
- Alerting MUST NEVER raise — a failed webhook can never break the bot.
- Same alert code is throttled to one fire per THROTTLE_SECONDS to prevent spam.
- Severity levels: "critical" (page-worthy) vs. "warning" (Slack + email).

Wired triggers:
    alert_tech_problem_blocked  — called from Layer 3 policy when B1 hard-block fires
    alert_p95_latency_breach    — called from sla_monitor on p95 > 2500ms
    alert_high_error_rate       — called from sla_monitor on error rate > 5%
    alert_transfer_spike        — called from sla_monitor on transfer rate spike

Environment:
    SLACK_ALERTS_WEBHOOK — incoming webhook URL (absent → alerting silently skipped)
"""
from __future__ import annotations

import time
import logging

import httpx

from server.configs.secrets import get_secret

logger = logging.getLogger(__name__)


def _slack_webhook() -> str:
    """Lazy-load the Slack webhook URL from Secret Manager (cached after first call)."""
    return get_secret("slack-alerts-webhook", default="")

# Suppress repeated fires of the same code within this window
THROTTLE_SECONDS: int = 15 * 60  # 15 minutes

_LAST_ALERT_AT: dict[str, float] = {}


async def send_alert(
    code: str,
    severity: str,
    message: str,
    details: dict | None = None,
) -> None:
    """
    Post a Slack message via incoming webhook.  Silently suppressed if:
    - `SLACK_ALERTS_WEBHOOK` is not configured, or
    - the same `code` was sent within THROTTLE_SECONDS.
    """
    now = time.time()
    if now - _LAST_ALERT_AT.get(code, 0) < THROTTLE_SECONDS:
        return  # within throttle window — suppress

    _LAST_ALERT_AT[code] = now

    colour = {"critical": "danger", "warning": "warning"}.get(severity, "good")
    payload = {
        "text": f"[{severity.upper()}] `{code}`: {message}",
        "attachments": [
            {
                "color": colour,
                "fields": [
                    {"title": str(k), "value": str(v)[:500], "short": True}
                    for k, v in (details or {}).items()
                ],
            }
        ],
    }

    webhook_url = _slack_webhook()
    if not webhook_url:
        logger.debug("alerts: slack-alerts-webhook not set — alert suppressed: %s", code)
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code not in (200, 201):
                logger.warning("alerts: Slack webhook returned %d for %s", resp.status_code, code)
    except Exception as exc:
        # Alerting must never propagate errors to the caller
        logger.debug("alerts: webhook delivery failed (%s): %s", code, exc)


# ── Wired trigger helpers ─────────────────────────────────────────────────────

async def alert_tech_problem_blocked(call_sid: str, tenant_id: str = "") -> None:
    """
    Fire when Layer 3 (Phase 8 B1) intercepts a tech-problem admission.
    This is a never-event: the bot should never spontaneously say it has a
    technical problem — always escalate to human instead.
    """
    await send_alert(
        code="TECH_PROBLEM_BLOCKED",
        severity="critical",
        message="Layer 3 blocked a tech-problem admission and forced transfer",
        details={"call_sid": call_sid, "tenant_id": tenant_id or "(unknown)"},
    )


async def alert_p95_latency_breach(p95_ms: int, window: str) -> None:
    """SLO breach: p95 total latency exceeded 2500ms over `window`."""
    await send_alert(
        code="LATENCY_P95_BREACH",
        severity="warning",
        message=f"p95 total latency {p95_ms}ms exceeds 2500ms SLO over {window}",
        details={"p95_ms": p95_ms, "slo_ms": 2500, "window": window},
    )


async def alert_high_error_rate(rate: float, top_codes: list[str], window: str) -> None:
    """SLO breach: error rate exceeded 5% over `window`."""
    await send_alert(
        code="ERROR_RATE_HIGH",
        severity="warning",
        message=f"Error rate {rate:.1%} exceeds 5% SLO over {window}",
        details={
            "error_rate_pct": f"{rate * 100:.2f}",
            "top_codes": ", ".join(top_codes[:5]),
            "window": window,
        },
    )


async def alert_transfer_spike(
    transfer_rate: float,
    baseline_rate: float,
    window: str,
) -> None:
    """Transfer rate has spiked significantly above the rolling baseline."""
    await send_alert(
        code="TRANSFER_RATE_SPIKE",
        severity="warning",
        message=(
            f"Transfer rate {transfer_rate:.1%} is "
            f"{transfer_rate / max(baseline_rate, 0.001):.1f}× above baseline ({baseline_rate:.1%})"
        ),
        details={
            "transfer_rate_pct": f"{transfer_rate * 100:.2f}",
            "baseline_rate_pct": f"{baseline_rate * 100:.2f}",
            "window": window,
        },
    )


async def alert_circuit_breaker_opened(breaker_name: str, failure_count: int) -> None:
    """A circuit breaker tripped — external dependency degraded."""
    await send_alert(
        code=f"BREAKER_OPEN_{breaker_name.upper()}",
        severity="critical",
        message=f"Circuit breaker '{breaker_name}' opened after {failure_count} failures",
        details={"breaker": breaker_name, "failures": failure_count},
    )
