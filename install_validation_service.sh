#!/usr/bin/env bash
# ============================================================
# install_validation_service.sh
#
# Installs the Sailly Sound Validation as a systemd service.
# Runs independently of Cursor / Jupyter on GCP.
#
# Usage:
#   sudo bash install_validation_service.sh          # install + enable
#   sudo bash install_validation_service.sh --remove # uninstall
#
# After install, manage with:
#   sudo systemctl start   sailly-sound-validation
#   sudo systemctl stop    sailly-sound-validation
#   sudo systemctl status  sailly-sound-validation
#   journalctl -u sailly-sound-validation -f
# ============================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="sailly-sound-validation"
SERVICE_FILE="$PROJECT_DIR/${SERVICE_NAME}.service"
SYSTEMD_DIR="/etc/systemd/system"
LOG_DIR="$PROJECT_DIR/logs"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Root check ────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    error "Run as root: sudo bash $0"
    exit 1
fi

# ── Remove mode ────────────────────────────────────────────
if [[ "${1:-}" == "--remove" ]]; then
    info "Removing $SERVICE_NAME..."
    systemctl stop  "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SYSTEMD_DIR/$SERVICE_NAME.service"
    systemctl daemon-reload
    success "Service removed."
    exit 0
fi

# ── Install ────────────────────────────────────────────────
info "Installing $SERVICE_NAME systemd service..."
info "Project: $PROJECT_DIR"

# Verify service file exists
if [[ ! -f "$SERVICE_FILE" ]]; then
    error "Service file not found: $SERVICE_FILE"
    exit 1
fi

# Make run script executable
chmod +x "$PROJECT_DIR/run_validation.sh"
chmod +x "$PROJECT_DIR/manage_secrets.py" 2>/dev/null || true

# Create log directory
mkdir -p "$LOG_DIR"
chown "$(stat -c '%U:%G' "$PROJECT_DIR")" "$LOG_DIR"

# Copy service file
cp "$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME.service"
chmod 644 "$SYSTEMD_DIR/$SERVICE_NAME.service"
success "Service file installed: $SYSTEMD_DIR/$SERVICE_NAME.service"

# Reload and enable
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
success "Service enabled (will start on next boot)"

# Start now
info "Starting service..."
systemctl start "$SERVICE_NAME" || {
    warn "Service start failed — check: journalctl -u $SERVICE_NAME -n 50"
}

# Status
echo ""
systemctl status "$SERVICE_NAME" --no-pager 2>/dev/null || true

echo ""
success "Installation complete!"
echo ""
echo "  Management commands:"
echo "    sudo systemctl start   $SERVICE_NAME"
echo "    sudo systemctl stop    $SERVICE_NAME"
echo "    sudo systemctl restart $SERVICE_NAME"
echo "    sudo systemctl status  $SERVICE_NAME"
echo "    journalctl -u $SERVICE_NAME -f"
echo ""
echo "  Log file: $LOG_DIR/sound_validation.log"
echo "  Reports:  $PROJECT_DIR/reports/"
echo ""
echo "  To remove: sudo bash $0 --remove"
