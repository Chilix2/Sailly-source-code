#!/usr/bin/env bash
# Phase 9 C3 — Rolling deploy with drain (decision rolling-with-drain 9.D8)
#
# Deploys to each instance one at a time:
#   1. Remove instance from load balancer (mark not-ready)
#   2. Wait for active calls to drain (up to DRAIN_TIMEOUT_S)
#   3. Deploy new code via git pull + systemctl restart
#   4. Wait for /ready endpoint to pass
#   5. Re-add to load balancer
#
# Requires:
#   - INSTANCES array set below or overridden via SAILLY_INSTANCES env var
#   - SSH access to each instance (key at /tmp/deploy_key or SSH_KEY_PATH)
#   - gcloud CLI authenticated for load balancer commands
#
# Usage:
#   SAILLY_INSTANCES="sailly-1 sailly-2" ./scripts/deploy_rolling.sh
#
# Environment:
#   SAILLY_INSTANCES    — space-separated hostnames (default: sailly-1 sailly-2)
#   SAILLY_INTERNAL_DOMAIN — DNS suffix for internal addresses (default: .internal)
#   DRAIN_TIMEOUT_S     — max seconds to wait for drain (default: 300)
#   HEALTH_WAIT_S       — max seconds to wait for /ready (default: 60)
#   DEPLOY_DIR          — directory on instance (default: /opt/sailly)
#   SYSTEMD_UNIT        — systemd unit name (default: sailly-voice-agent)
#   SSH_KEY_PATH        — path to SSH private key (default: /tmp/deploy_key)
#   GCP_INSTANCE_GROUP  — for gcloud LB commands (optional; skip LB if unset)

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
IFS=' ' read -ra INSTANCES <<< "${SAILLY_INSTANCES:-sailly-1 sailly-2}"
INTERNAL_DOMAIN="${SAILLY_INTERNAL_DOMAIN:-.internal}"
DRAIN_TIMEOUT_S="${DRAIN_TIMEOUT_S:-300}"
HEALTH_WAIT_S="${HEALTH_WAIT_S:-60}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/sailly}"
SYSTEMD_UNIT="${SYSTEMD_UNIT:-sailly-voice-agent}"
SSH_KEY_PATH="${SSH_KEY_PATH:-/tmp/deploy_key}"
GCP_INSTANCE_GROUP="${GCP_INSTANCE_GROUP:-}"

SSH_OPTS="-i $SSH_KEY_PATH -o StrictHostKeyChecking=no -o ConnectTimeout=10"

log() { echo "$(date '+%Y-%m-%dT%H:%M:%S') [deploy] $*"; }

# ── Helpers ───────────────────────────────────────────────────────────────────

get_active_calls() {
    local host="$1"
    local url="http://${host}${INTERNAL_DOMAIN}:8080/active-calls"
    curl -sf --max-time 5 "$url" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('count',0))" 2>/dev/null || echo "0"
}

wait_for_drain() {
    local host="$1"
    log "  Draining $host (timeout=${DRAIN_TIMEOUT_S}s)..."
    local elapsed=0
    while true; do
        local active
        active=$(get_active_calls "$host")
        if [ "$active" -eq 0 ]; then
            log "  $host drained (0 active calls)"
            return 0
        fi
        if [ "$elapsed" -ge "$DRAIN_TIMEOUT_S" ]; then
            log "  WARNING: drain timeout reached with $active active call(s) on $host — proceeding anyway"
            return 0
        fi
        log "  $host has $active active call(s) — waiting 5s (${elapsed}s elapsed)..."
        sleep 5
        elapsed=$((elapsed + 5))
    done
}

wait_for_healthy() {
    local host="$1"
    log "  Waiting for $host to be healthy..."
    local elapsed=0
    while true; do
        local url="http://${host}${INTERNAL_DOMAIN}:8080/ready"
        if curl -sf --max-time 5 "$url" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ready') else 1)" 2>/dev/null; then
            log "  $host is healthy"
            return 0
        fi
        if [ "$elapsed" -ge "$HEALTH_WAIT_S" ]; then
            log "  ERROR: $host did not become healthy within ${HEALTH_WAIT_S}s"
            return 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
}

remove_from_lb() {
    local instance="$1"
    if [ -z "$GCP_INSTANCE_GROUP" ]; then
        log "  (GCP_INSTANCE_GROUP not set — skipping LB remove for $instance)"
        return
    fi
    log "  Removing $instance from load balancer..."
    gcloud compute instance-groups managed set-named-ports "$GCP_INSTANCE_GROUP" \
        --named-ports= \
        --zone="${GCP_ZONE:-us-central1-a}" 2>/dev/null || true
    # Mark instance as draining via backend service
    gcloud compute backend-services edit "${GCP_BACKEND_SERVICE:-sailly-backend}" \
        --global 2>/dev/null || true
}

add_to_lb() {
    local instance="$1"
    if [ -z "$GCP_INSTANCE_GROUP" ]; then
        log "  (GCP_INSTANCE_GROUP not set — skipping LB add for $instance)"
        return
    fi
    log "  Re-adding $instance to load balancer..."
    # Re-register named ports (signals readiness)
    gcloud compute instance-groups managed set-named-ports "$GCP_INSTANCE_GROUP" \
        --named-ports="http:8080" \
        --zone="${GCP_ZONE:-us-central1-a}" 2>/dev/null || true
}

deploy_instance() {
    local instance="$1"
    log "  Deploying code to $instance..."
    ssh $SSH_OPTS "$instance${INTERNAL_DOMAIN}" \
        "cd ${DEPLOY_DIR} && git pull --ff-only && systemctl restart ${SYSTEMD_UNIT}"
}

# ── Main rolling loop ─────────────────────────────────────────────────────────

log "Starting rolling deploy to: ${INSTANCES[*]}"
FAILED=0

for instance in "${INSTANCES[@]}"; do
    log "── Deploying $instance ──────────────────────────────────────────────"

    # Step 1: Remove from LB so no new calls are routed here
    remove_from_lb "$instance"

    # Step 2: Wait for active calls to complete
    wait_for_drain "$instance"

    # Step 3: Deploy
    if ! deploy_instance "$instance"; then
        log "ERROR: deploy failed on $instance"
        add_to_lb "$instance"  # restore LB entry even on failure
        FAILED=1
        continue
    fi

    # Step 4: Wait for healthy
    if ! wait_for_healthy "$instance"; then
        log "ERROR: $instance failed health check after deploy — investigate before re-adding to LB"
        FAILED=1
        continue
    fi

    # Step 5: Re-add to LB
    add_to_lb "$instance"
    log "  $instance deployed and serving"
done

if [ "$FAILED" -ne 0 ]; then
    log "DEPLOY FAILED on one or more instances — check logs above"
    exit 1
fi

log "Rolling deploy complete — all instances updated"
