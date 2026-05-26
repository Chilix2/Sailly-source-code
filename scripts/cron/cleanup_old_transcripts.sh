#!/usr/bin/env bash
# Phase 9 A5 — 90-day transcript retention cleanup
#
# Deletes google_turn_metrics rows older than 90 days.
# Runs nightly at 03:00 CET via sailly-cleanup.timer (see systemd/).
#
# Usage: ./scripts/cron/cleanup_old_transcripts.sh
#
# Environment (read from /etc/sailly/env or export before calling):
#   DATABASE_URL — asyncpg/libpq DSN to the primary Postgres instance
#   LOG_DIR      — directory for daily cleanup logs (default: /var/log/sailly)

set -euo pipefail

LOG_DIR="${LOG_DIR:-/var/log/sailly}"
LOGFILE="${LOG_DIR}/cleanup_$(date +%Y%m%d).log"
DATABASE_URL="${DATABASE_URL:-}"

log() {
    echo "$(date '+%Y-%m-%dT%H:%M:%S') $*" | tee -a "$LOGFILE"
}

if [[ -z "$DATABASE_URL" ]]; then
    # Try loading from env file if present
    ENV_FILE="/etc/sailly/.env"
    if [[ -f "$ENV_FILE" ]]; then
        # shellcheck disable=SC1090
        source "$ENV_FILE"
    fi
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
    log "ERROR: DATABASE_URL not set — cannot connect to Postgres"
    exit 1
fi

mkdir -p "$LOG_DIR"
log "INFO: starting transcript cleanup (retain-90 policy)"

RESULT=$(psql "$DATABASE_URL" --tuples-only --no-align \
    -c "SELECT cleanup_old_transcripts();" 2>&1)

EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    log "ERROR: cleanup query failed: $RESULT"
    exit $EXIT_CODE
fi

DELETED=$(echo "$RESULT" | tr -d '[:space:]')
log "INFO: cleanup complete — deleted_turn_rows=${DELETED}"
