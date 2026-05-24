#!/usr/bin/env bash
# Add two Google Secret Manager secrets expected by the Sailly app:
#   aws-access-key-id
#   aws-secret-access-key
#
# Prerequisite: create two local files (do not commit real keys). Copy from
#   scripts/gsm-aws-bedrock-templates/*.TEMPLATE  →  *.value  and edit in one line per file.
#
# Usage (from repo root, with gcloud auth):
#   export GCP_PROJECT_ID=your-project-id
#   ./scripts/gsm-aws-bedrock-upload-two-secrets.sh
#
# Or set custom file paths:
#   GSM_AWS_ACCESS_KEY_ID_FILE=/path/ak  GSM_AWS_SECRET_KEY_FILE=/path/sk  ./scripts/...
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPL_DIR="${SCRIPT_DIR}/gsm-aws-bedrock-templates"

PROJECT_ID="${GCP_PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-}}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Set GCP_PROJECT_ID to your Google Cloud project id (or number)." >&2
  exit 1
fi

F1="${GSM_AWS_ACCESS_KEY_ID_FILE:-${TEMPL_DIR}/aws-access-key-id.value}"
F2="${GSM_AWS_SECRET_KEY_FILE:-${TEMPL_DIR}/aws-secret-access-key.value}"

for f in "$F1" "$F2"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing file: $f" >&2
    echo "  cp ${TEMPL_DIR}/aws-access-key-id.TEMPLATE ${TEMPL_DIR}/aws-access-key-id.value" >&2
    echo "  cp ${TEMPL_DIR}/aws-secret-access-key.TEMPLATE ${TEMPL_DIR}/aws-secret-access-key.value" >&2
    echo "  (edit: one line of key material in each, remove placeholder lines starting with #)" >&2
    exit 1
  fi
done

# First non-empty line that is not a shell-style comment
strip_to_one_line() {
  local file=$1
  local line
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}" # ltrim
    line="${line%"${line##*[![:space:]]}"}" # rtrim
    [[ -z "$line" || "$line" == \#* ]] && continue
    printf '%s' "$line"
    return 0
  done < "$file"
  return 1
}

create_if_missing() {
  local name=$1
  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "[exists] $name"
  else
    gcloud secrets create "$name" --replication-policy="automatic" --project="$PROJECT_ID"
    echo "[created] $name"
  fi
}

create_if_missing "aws-access-key-id"
create_if_missing "aws-secret-access-key"

K1=$(strip_to_one_line "$F1")
K2=$(strip_to_one_line "$F2")
if [[ -z "$K1" || -z "$K2" ]]; then
  echo "One of the key files is empty. Fix: $F1  and  $F2" >&2
  exit 1
fi

printf '%s' "$K1" | gcloud secrets versions add aws-access-key-id --data-file=- --project="$PROJECT_ID"
printf '%s' "$K2" | gcloud secrets versions add aws-secret-access-key --data-file=- --project="$PROJECT_ID"
echo "Done. New versions for aws-access-key-id and aws-secret-access-key in project $PROJECT_ID"
