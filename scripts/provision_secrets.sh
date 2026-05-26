#!/usr/bin/env bash
# provision_secrets.sh — create all required GSM secrets (idempotent).
#
# Usage:
#   ./scripts/provision_secrets.sh [staging|prod]
#
# The script only *creates* secret resources.  It never adds or modifies
# secret versions — operators must add the actual values manually:
#
#   echo -n '<value>' | gcloud secrets versions add <name> \
#       --data-file=- --project=$PROJECT_ID
#
# IAM prerequisite (run once per environment):
#   gcloud projects add-iam-policy-binding "$PROJECT_ID" \
#       --member="serviceAccount:<vm-sa>@<project>.iam.gserviceaccount.com" \
#       --role="roles/secretmanager.secretAccessor"
set -euo pipefail

ENV="${1:-prod}"
PROJECT_ID="${SAILLY_GCP_PROJECT:-sailly-prod}"

echo "==> Provisioning GSM secrets for env=${ENV} project=${PROJECT_ID}"

declare -a SECRETS=(
  "deepgram-api-key"
  "gemini-api-key"
  "maps-api-key"
  "twilio-account-sid"
  "twilio-auth-token"
  "whatsapp-token"
  "slack-alerts-webhook"
  "postgres-password"
  "redis-password"
  "aws-access-key-id"
  "aws-secret-access-key"
)

for name in "${SECRETS[@]}"; do
  if gcloud secrets describe "$name" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "  [exists]  $name"
  else
    echo "  [create]  $name"
    gcloud secrets create "$name" \
      --replication-policy=automatic \
      --project="$PROJECT_ID"
  fi
done

echo ""
echo "Done. Add secret versions with:"
echo "  echo -n '<value>' | gcloud secrets versions add <name> --data-file=- --project=${PROJECT_ID}"
echo ""
echo "Grant runtime SA access (if not already done):"
echo "  gcloud projects add-iam-policy-binding ${PROJECT_ID} \\"
echo "    --member='serviceAccount:<vm-sa>@${PROJECT_ID}.iam.gserviceaccount.com' \\"
echo "    --role='roles/secretmanager.secretAccessor'"
