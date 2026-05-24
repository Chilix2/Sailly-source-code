#!/usr/bin/env bash
# Sound Validation Quick Start Script
# Usage: bash run_phase_a.sh [--gcp]

set -e

PROJECT_DIR="/home/charles2/sailly-browser-demo"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Sound Validation — Phase A Quick Start${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Check if running with --gcp flag
USE_GCP=false
if [ "$1" == "--gcp" ]; then
    USE_GCP=true
    echo -e "${YELLOW}[INFO] Using Google Secret Manager${NC}"
fi

# Load environment
if [ "$USE_GCP" = true ]; then
    echo -e "${YELLOW}[SETUP] Loading XAI API key from Google Secret Manager...${NC}"
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}[ERROR] gcloud CLI not found. Install with: curl https://sdk.cloud.google.com | bash${NC}"
        exit 1
    fi
    export XAI_API_KEY=$(gcloud secrets versions access latest --secret="xai-api-key" 2>/dev/null || echo "")
    if [ -z "$XAI_API_KEY" ]; then
        echo -e "${RED}[ERROR] Could not retrieve XAI_API_KEY from Google Secret Manager${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[SETUP] Loading from .env file...${NC}"
    if [ ! -f ".env" ]; then
        echo -e "${RED}[ERROR] .env file not found${NC}"
        exit 1
    fi
    source .env
fi

# Verify API key is set
if [ -z "$XAI_API_KEY" ]; then
    echo -e "${RED}[ERROR] XAI_API_KEY not set${NC}"
    exit 1
fi

echo -e "${GREEN}✓ API key configured: ${XAI_API_KEY:0:20}...${NC}"

# Verify Sailly service is running
echo -e "${YELLOW}[CHECK] Verifying Sailly service health...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8080/healthz || echo "")
if [ -z "$HEALTH_RESPONSE" ]; then
    echo -e "${RED}[ERROR] Sailly service not responding on port 8080${NC}"
    echo -e "${YELLOW}[HINT] Start Sailly with: cd /home/charles2/sailly-browser-demo && npm run dev${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Sailly service is healthy${NC}"

# Check WebSocket endpoint
echo -e "${YELLOW}[CHECK] Verifying WebSocket /ws/demo...${NC}"
WS_CHECK=$(python3 -c "
import asyncio, websockets, sys
async def test():
    try:
        async with websockets.connect('ws://localhost:8080/ws/demo', close_timeout=2) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=2)
            sys.exit(0)
    except:
        sys.exit(1)
asyncio.run(test())
" && echo "ready" || echo "failed")

if [ "$WS_CHECK" != "ready" ]; then
    echo -e "${RED}[ERROR] WebSocket /ws/demo not responding${NC}"
    exit 1
fi
echo -e "${GREEN}✓ WebSocket /ws/demo is ready${NC}"

# Run infrastructure smoke test first
echo -e "${YELLOW}[TEST] Running infrastructure smoke test...${NC}"
SMOKE_RESULT=$(python3 server/validation/phase_a_smoke_test.py 2>&1 | tail -3)
if echo "$SMOKE_RESULT" | grep -q "PHASE A PASSED"; then
    echo -e "${GREEN}✓ Infrastructure smoke test PASSED${NC}"
else
    echo -e "${RED}✗ Infrastructure smoke test FAILED${NC}"
    echo "$SMOKE_RESULT"
    exit 1
fi

# Ask for confirmation
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Ready to run Phase A with 20 STS calls (20-30 minutes)${NC}"
echo -e "${YELLOW}Cost estimate: \$15-20 USD (Grok at \$0.05/min)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}[INFO] Cancelled${NC}"
    exit 0
fi

# Run Phase A
echo ""
echo -e "${BLUE}[RUN] Starting Phase A...${NC}"
echo -e "${BLUE}Monitoring: tail -f reports/phase_a_smoke_attempt1.md${NC}"
echo ""

python3 -m server.validation.loop_runner

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ PHASE A PASSED — All 20 calls successful!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Report: $(ls -t reports/phase_a_smoke_attempt*.md 2>/dev/null | head -1)${NC}"
else
    echo ""
    echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ PHASE A FAILED — See reports for details${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}[DEBUG] Latest report:${NC}"
    tail -20 reports/phase_a_smoke_attempt*.md 2>/dev/null | tail -20
fi

exit $?
