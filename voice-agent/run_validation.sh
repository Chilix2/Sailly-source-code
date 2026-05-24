#!/usr/bin/env bash
# ============================================================
# Sound Validation — Standalone CLI Entry Point
# Runs independently of Cursor / Jupyter / any IDE.
# Safe to use in:  tmux, screen, systemd, nohup, Cloud Run jobs
#
# Usage:
#   bash run_validation.sh                       # interactive, phase a
#   bash run_validation.sh --daemon              # background mode (logs to file)
#   bash run_validation.sh --phase all           # all phases
#   bash run_validation.sh --resume              # resume from last checkpoint
#   bash run_validation.sh --daemon --phase all --resume  # full autonomous run
#   nohup bash run_validation.sh --daemon &      # fully detached
#
# Watchdog behaviour:
#   When --daemon is set this script also monitors the heartbeat file.
#   If no heartbeat update is seen for 120s, the validation process is
#   considered hung, killed, and restarted with --resume.
#
# Environment (auto-loaded from .env if present, then GCP secrets):
#   XAI_API_KEY       — XAI Grok Realtime key (voice caller)
#   ANTHROPIC_API_KEY — Claude Haiku 4.5 key (fix auditor)
#   DEEPGRAM_API_KEY  — Deepgram STT key (loaded by Sailly)
#   GCP_PROJECT_ID    — Google Cloud project (sailly-voice-agent-eu)
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
PYTHON="${PROJECT_DIR}/venv/bin/python3"
LOG_DIR="$PROJECT_DIR/logs"
DAEMON_MODE=false
PHASE="all"
RESUME_MODE=false
HEARTBEAT_FILE="/tmp/sound_validation_heartbeat.json"
HEARTBEAT_STALE_S=120   # seconds before considering process hung

# ── Colours ────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
header()  { echo -e "\n${BOLD}${BLUE}$*${NC}\n"; }

# ── Parse args ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --daemon)  DAEMON_MODE=true; shift ;;
        --resume)  RESUME_MODE=true; shift ;;
        --phase)   PHASE="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--daemon] [--resume] [--phase a|all]"
            exit 0 ;;
        *) error "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Banner ──────────────────────────────────────────────────
header "╔══════════════════════════════════════════════════════╗"
header "║   SAILLY SOUND VALIDATION — STS Caller Test Suite   ║"
header "╚══════════════════════════════════════════════════════╝"
info "Project: $PROJECT_DIR"
info "Phase:   $PHASE"
info "Daemon:  $DAEMON_MODE"
info "Resume:  $RESUME_MODE"
info "Python:  $($PYTHON --version 2>&1)"
echo ""

# ── Step 1: Load secrets ────────────────────────────────────
header "Step 1: Load Secrets"

load_from_gcp_secret() {
    local secret_name="$1"
    local env_var="$2"
    if command -v gcloud &>/dev/null; then
        local val
        val=$(gcloud secrets versions access latest --secret="$secret_name" 2>/dev/null || echo "")
        if [[ -n "$val" ]]; then
            export "$env_var"="$val"
            info "Loaded $env_var from GCP secret: $secret_name"
            return 0
        fi
    fi
    return 1
}

# Load .env file if present (local development)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    info "Loading .env file..."
    set -a
    # shellcheck disable=SC1090
    source "$PROJECT_DIR/.env" 2>/dev/null || true
    set +a
fi

# Try to load secrets from GCP Secret Manager if env vars are missing
if [[ -z "${XAI_API_KEY:-}" ]]; then
    load_from_gcp_secret "xai-api-key" "XAI_API_KEY" || warn "XAI_API_KEY not found (check GCP or .env)"
fi
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    load_from_gcp_secret "anthropic-api-key" "ANTHROPIC_API_KEY" || warn "ANTHROPIC_API_KEY not found"
fi
if [[ -z "${DEEPGRAM_API_KEY:-}" ]]; then
    load_from_gcp_secret "deepgram-api-key" "DEEPGRAM_API_KEY" || warn "DEEPGRAM_API_KEY not found"
fi

# ── Step 2: Validate required keys ─────────────────────────
header "Step 2: Validate API Keys"

KEYS_OK=true

if [[ -n "${XAI_API_KEY:-}" ]]; then
    success "XAI_API_KEY    ✓ (${XAI_API_KEY:0:20}...)"
elif [[ -n "${OPENAI_API_KEY:-}" ]]; then
    success "OPENAI_API_KEY ✓ (fallback caller)"
else
    error "No voice caller key set. Need XAI_API_KEY or OPENAI_API_KEY."
    KEYS_OK=false
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    success "ANTHROPIC_API_KEY ✓ — Claude Haiku 4.5 fix auditor ENABLED"
else
    warn "ANTHROPIC_API_KEY not set — fix auditor DISABLED (will just restart on failure)"
fi

if [[ -n "${DEEPGRAM_API_KEY:-}" ]]; then
    success "DEEPGRAM_API_KEY  ✓"
else
    warn "DEEPGRAM_API_KEY not set — Sailly may fail if not loaded from GCP"
fi

if [[ "$KEYS_OK" == false ]]; then
    error "Required API keys missing. Aborting."
    exit 1
fi

# ── Step 3: Verify Sailly service health ────────────────────
header "Step 3: Verify Sailly Service"

check_sailly() {
    local status
    status=$(curl -sf http://localhost:8080/healthz 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null \
        || echo "")
    [[ "$status" == "ok" ]]
}

if check_sailly; then
    success "Sailly service healthy on port 8080"
else
    warn "Sailly not responding — trying to start..."
    cd "$PROJECT_DIR"

    if systemctl is-active --quiet sailly-browser-demo 2>/dev/null; then
        sudo systemctl restart sailly-browser-demo || true
    else
        warn "Starting Sailly directly in background..."
        nohup $PYTHON -m uvicorn server.main:app --host 0.0.0.0 --port 8080 \
            >> "$LOG_DIR/sailly_server.log" 2>&1 &
        SAILLY_PID=$!
        info "Sailly PID: $SAILLY_PID"
    fi

    info "Waiting for Sailly to come up..."
    for i in $(seq 1 15); do
        sleep 2
        if check_sailly; then
            success "Sailly is up!"
            break
        fi
        if [[ $i -eq 15 ]]; then
            error "Sailly did not come up after 30s. Check: tail -f $LOG_DIR/sailly_server.log"
            exit 1
        fi
    done
fi

# ── Step 4: Create log/report directories ──────────────────
mkdir -p "$LOG_DIR" reports

# ── Step 5: Build python command ────────────────────────────
header "Step 5: Run Phase $PHASE Sound Validation"
echo ""
info "Caller Bot    : OpenAI GPT-4o-mini (text-mode customer)"
info "LLM Auditor   : Grok grok-3-mini (tool accuracy 40%, flow 30%, linguistic 15%, deterministic 15%)"
info "Fix Generator : Claude Haiku 4.5"
info "Target        : Sailly ws://127.0.0.1:8080/ws/headless (Postgres recording ON)"
info "Pass Threshold: 80/100 composite + 10pt improvement from baseline"
info "Max Attempts  : 3 per scenario batch → forced advance if not met"
info "Workers       : 5 concurrent, 5s stagger"
echo ""

# Build the python args
if [[ "$PHASE" == "all" || "$PHASE" == "a-d" ]]; then
    PYTHON_PHASES="a-d"
else
    PYTHON_PHASES="$PHASE"
fi

PYTHON_ARGS="--phases $PYTHON_PHASES --workers 5 --stagger-s 5 --output-dir $PROJECT_DIR/reports"
if $RESUME_MODE; then
    PYTHON_ARGS="$PYTHON_ARGS --resume"
    info "Resume mode: will skip already-completed scenario batches"
fi

# ── Step 6: Run with or without daemon watchdog ─────────────
if $DAEMON_MODE; then
    LOG_FILE="$LOG_DIR/sound_validation.log"
    info "Daemon mode: logs → $LOG_FILE"
    info "Monitor with: tail -f $LOG_FILE"
    echo ""

    # Launch validation in background, monitor heartbeat
    $PYTHON -m server.validation.scenario_based_loop \
        $PYTHON_ARGS >> "$LOG_FILE" 2>&1 &
    VALIDATION_PID=$!
    info "Validation PID: $VALIDATION_PID"

    # ── Watchdog loop: monitor heartbeat, restart if stale ──────────────────
    info "Watchdog active — will restart if heartbeat stale for ${HEARTBEAT_STALE_S}s"
    while true; do
        sleep 30

        # Check if process is still alive
        if ! kill -0 "$VALIDATION_PID" 2>/dev/null; then
            EXIT_CODE=$?
            warn "Validation process $VALIDATION_PID exited (code $EXIT_CODE)"
            # If exit was clean (0), we're done
            wait "$VALIDATION_PID" 2>/dev/null && break || true

            # Non-zero exit — restart with --resume
            warn "Restarting validation with --resume..."
            $PYTHON -m server.validation.scenario_based_loop \
                $PYTHON_ARGS --resume >> "$LOG_FILE" 2>&1 &
            VALIDATION_PID=$!
            info "Restarted — new PID: $VALIDATION_PID"
            continue
        fi

        # Check heartbeat freshness
        if [[ -f "$HEARTBEAT_FILE" ]]; then
            HEARTBEAT_TS=$(python3 -c "
import json, time
try:
    d = json.load(open('$HEARTBEAT_FILE'))
    print(int(time.time() - d.get('ts', 0)))
except:
    print(999)
" 2>/dev/null || echo "999")

            if [[ "$HEARTBEAT_TS" -gt "$HEARTBEAT_STALE_S" ]]; then
                warn "Heartbeat stale (${HEARTBEAT_TS}s old) — killing hung process and restarting"
                kill "$VALIDATION_PID" 2>/dev/null || true
                sleep 5
                $PYTHON -m server.validation.scenario_based_loop \
                    $PYTHON_ARGS --resume >> "$LOG_FILE" 2>&1 &
                VALIDATION_PID=$!
                info "Restarted after stale heartbeat — PID: $VALIDATION_PID"
            else
                info "Heartbeat OK (${HEARTBEAT_TS}s ago, PID=$VALIDATION_PID)"
            fi
        fi
    done

    wait "$VALIDATION_PID" 2>/dev/null
    exit $?

else
    # Interactive mode — run directly (no watchdog needed)
    info "Interactive mode: logs to stdout"
    info "Reports: tail -f reports/phase_a_smoke_attempt1.md"
    echo ""
    exec $PYTHON -m server.validation.scenario_based_loop $PYTHON_ARGS
fi
