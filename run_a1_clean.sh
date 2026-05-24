#!/bin/bash
set -e

REPORT_DIR="reports/phase_a1_surgical_fix"
WORKERS=5
STAGGER=10

echo "[$(date)] Starting Phase A1 validation with surgical fixes (v4_pipeline corrections)"
echo "  - Output: $REPORT_DIR"
echo "  - Workers: $WORKERS (staggered by ${STAGGER}s)"
echo "  - Phases: A1.1_D1 through A1.5_D5"

. ./venv/bin/activate

python3 -m server.validation.scenario_based_loop \
  --phases "A1.1_D1 A1.2_D2 A1.3_D3 A1.4_D4 A1.5_D5" \
  --workers $WORKERS \
  --stagger-s $STAGGER \
  --output-dir "$REPORT_DIR" \
  2>&1 | tee "$REPORT_DIR/validation.log"

echo "[$(date)] Phase A1 validation complete"
