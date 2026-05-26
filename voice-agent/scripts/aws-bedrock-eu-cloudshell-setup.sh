
#!/usr/bin/env bash
# Paste into AWS Cloud Shell and run:  bash aws-bedrock-eu-cloudshell-setup.sh
# Or:  curl -sS ... | bash   (only if you host this file — prefer copy-paste for security)
#
# What it does:
#   1) Sets region to eu-central-1 (override with AWS_BEDROCK_REGION)
#   2) Shows who you are (STS)
#   3) Lists Bedrock foundation models matching claude-haiku-4-5
#   4) Tries a minimal InvokeModel (inference profile ID = EU Geo)
#   5) Prints an IAM policy JSON and optional commands to attach to your user/role
#   6) Prints .env lines for your app (no secrets)
#
# You must still enable model access in the Bedrock console if your account requires it
# (Model access). This script cannot replace that in all organizations.

set -euo pipefail

REGION="${AWS_BEDROCK_REGION:-${AWS_REGION:-eu-central-1}}"
export AWS_DEFAULT_REGION="$REGION"

# EU Geo inference profile (Claude Haiku 4.5) — data stays in EU
INFERENCE_PROFILE_ID="eu.anthropic.claude-haiku-4-5-20251001-v1:0"
# Foundation model id (for IAM resource ARNs)
FOUNDATION_MODEL_ID="anthropic.claude-haiku-4-5-20251001-v1:0"

echo "=============================================="
echo "  Region: $REGION"
echo "  Inference profile: $INFERENCE_PROFILE_ID"
echo "=============================================="
echo

echo "== 1) Caller identity =="
aws sts get-caller-identity --output table
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo

echo "== 2) Foundation models (filter: claude-haiku-4-5) =="
if aws bedrock list-foundation-models --region "$REGION" \
  --output table \
  --query "modelSummaries[?contains(modelId, 'claude-haiku-4-5')]" 2>/dev/null; then
  :
else
  echo "WARN: list-foundation-models failed (check Bedrock in this region or IAM: bedrock:ListFoundationModels)."
fi
echo

echo "== 3) Minimal InvokeModel test (4–5s) =="
REQ=$(mktemp)
OUT=$(mktemp)
trap 'rm -f "$REQ" "$OUT"' EXIT

cat >"$REQ" <<'JSON'
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 8,
  "messages": [{"role": "user", "content": "Say OK in one word."}]
}
JSON

if aws bedrock-runtime invoke-model \
  --region "$REGION" \
  --model-id "$INFERENCE_PROFILE_ID" \
  --content-type "application/json" \
  --accept "application/json" \
  --body "file://$REQ" \
  --cli-binary-format raw-in-base64-out \
  "$OUT" 2>&1; then
  echo "RAW RESPONSE FILE:"
  cat "$OUT" | head -c 2000; echo
  echo
  echo "OK: Invoke succeeded — Bedrock + model access work for this principal."
else
  EC=$?
  echo
  echo "Invoke failed (exit $EC). Common causes:"
  echo "  - Model not enabled: Bedrock console → Model access → enable Haiku 4.5 in $REGION"
  echo "  - Missing IAM: bedrock:InvokeModel, bedrock:InvokeModelWithResponseStream"
  echo "  - Wrong model id for your region (check console / docs)"
  echo
fi
echo

POLICY_FILE="${PWD}/bedrock-claude-eu-iam-policy.json"
echo "== 4) IAM policy written to: $POLICY_FILE =="
cat >"$POLICY_FILE" <<POLICY_EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockClaudeHaikuEU",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/${FOUNDATION_MODEL_ID}",
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:inference-profile/${INFERENCE_PROFILE_ID}"
      ]
    },
    {
      "Sid": "ListModelsForTroubleshooting",
      "Effect": "Allow",
      "Action": "bedrock:ListFoundationModels",
      "Resource": "*"
    }
  ]
}
POLICY_EOF
cat "$POLICY_FILE"
echo

echo "== 5) Optional: attach inline policy to YOUR IAM user (not for assumed-role) =="
CALLER_ARN=$(aws sts get-caller-identity --query Arn --output text)
if [[ "$CALLER_ARN" == *":user/"* ]]; then
  IAM_USER="${CALLER_ARN##*/}"
  echo "Detected IAM user: $IAM_USER"
  echo "To attach (if you have iam:PutUserPolicy), run:"
  echo "  aws iam put-user-policy --user-name \"${IAM_USER}\" --policy-name SaillyBedrockClaudeHaikuEU --policy-document file://${POLICY_FILE}"
else
  echo "Principal is not a long-lived IAM user: $CALLER_ARN"
  echo "In IAM → Roles → (your role) → Add permissions → Create inline policy → JSON, paste the file above."
  echo "Or: aws iam put-role-policy --role-name YOUR_ROLE --policy-name SaillyBedrockClaudeHaikuEU --policy-document file://${POLICY_FILE}"
fi
echo

echo "== 6) Create a dedicated IAM USER + access key (optional; many orgs forbid this) =="
echo "Set CREATE_APP_USER=1 to create user ${BEDROCK_IAM_USER_NAME:-sailly-bedrock-eu} and a new access key."
if [[ "${CREATE_APP_USER:-0}" == "1" ]]; then
  USER_NAME="${BEDROCK_IAM_USER_NAME:-sailly-bedrock-eu}"
  aws iam create-user --user-name "$USER_NAME" 2>/dev/null || true
  aws iam put-user-policy --user-name "$USER_NAME" --policy-name SaillyBedrockClaudeHaikuEU --policy-document "file://${POLICY_FILE}"
  echo "Creating access key (STORE SECURELY; shown once):"
  aws iam create-access-key --user-name "$USER_NAME" --output table
fi
echo

echo "== 7) App .env (fill in keys yourself; never commit secrets) =="
cat <<ENV
AWS_BEDROCK_REGION=${REGION}
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
# AWS_SESSION_TOKEN=   # only if using temporary creds
BEDROCK_LLM_MODEL=${INFERENCE_PROFILE_ID}
SLOT_EXTRACTOR_MODEL=${INFERENCE_PROFILE_ID}
MAIN_LLM_MODEL=${INFERENCE_PROFILE_ID}
ENV
echo
echo "Done."
