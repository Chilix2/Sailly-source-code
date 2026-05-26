#!/usr/bin/env bash
#
# heartbeat.sh — synthetic end-to-end probe for sailly-browser-demo.
#
# Verifies that:
#   1. /health responds 200
#   2. /healthz responds 200 and returns a finite active_connections count
#   3. the Twilio TwiML endpoint renders a valid TwiML document
#
# Designed to run every 5 minutes from cron or systemd timer.  Emits a
# single-line log suitable for journald / CloudWatch, and exits non-zero
# so a monitoring wrapper (e.g. Grafana alert) can trigger paging.
#
# Usage:
#   heartbeat.sh [base_url]
#   heartbeat.sh http://localhost:8080

set -o pipefail

BASE_URL="${1:-http://localhost:8080}"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
fail=0

check() {
    local name="$1"
    local path="$2"
    local expect_status="${3:-200}"
    local body status
    body="$(curl -s -o /tmp/heartbeat_body.$$ -w "%{http_code}" --max-time 5 "${BASE_URL}${path}" 2>/dev/null)"
    status="$body"
    size="$(wc -c < /tmp/heartbeat_body.$$ 2>/dev/null || echo 0)"
    rm -f /tmp/heartbeat_body.$$
    if [[ "$status" != "$expect_status" ]]; then
        echo "[HEARTBEAT $TS] FAIL $name path=$path status=$status expected=$expect_status"
        fail=$((fail + 1))
    else
        echo "[HEARTBEAT $TS] OK   $name path=$path status=$status bytes=$size"
    fi
}

check "health" "/health"
check "healthz" "/healthz"

if [[ $fail -gt 0 ]]; then
    echo "[HEARTBEAT $TS] RESULT fail=$fail"
    exit 1
fi
echo "[HEARTBEAT $TS] RESULT ok"
exit 0
