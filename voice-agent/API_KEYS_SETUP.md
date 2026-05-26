# API Keys & Google Secrets Setup Guide

## Quick Start: Set XAI API Key

```bash
# Option 1: Local development (.env file)
export XAI_API_KEY="REDACTED_XAI_KEY"

# Option 2: Load from Google Secret Manager (recommended for prod)
export XAI_API_KEY=$(gcloud secrets versions access latest --secret="REDACTED_XAI_KEY")

# Verify it's set
echo $XAI_API_KEY
```

---

## API Keys Reference

| Service | Key | Cost | Status |
|---------|-----|------|--------|
| **XAI (Grok)** | `REDACTED_XAI_KEY` | $0.05/min | ✅ Set |
| **Anthropic Claude** | `sk-ant-api03-xxxxxxxx` | $0.003-0.015/M tokens | ✅ Set |
| **DeepGram (STT)** | `7fb1bd0211e2bd3e003a...` | $0.0043/min | ✅ Set |
| **OpenAI (Fallback)** | `sk-xxxxxxxx` | $0.10/min (audio) | Optional |
| **Google Cloud (TTS)** | Service Account JSON | Included | ✅ Configured |

---

## Store XAI Key in Google Secret Manager

### Prerequisites
```bash
# Install Google Cloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Login
gcloud auth login

# Set project
gcloud config set project sailly-voice-agent-eu
```

### Create Secret
```bash
# Create secret from environment variable
gcloud secrets create REDACTED_XAI_KEY \
  --replication-policy="automatic" \
  --data-file=- << 'EOF'
REDACTED_XAI_KEY
EOF

# Or create from echo
echo -n "REDACTED_XAI_KEY" | \
  gcloud secrets create REDACTED_XAI_KEY --replication-policy="automatic" --data-file=-
```

### Verify Secret
```bash
# List all secrets
gcloud secrets list

# Access the secret (output to terminal)
gcloud secrets versions access latest --secret="REDACTED_XAI_KEY"

# Or pipe to environment
export XAI_API_KEY=$(gcloud secrets versions access latest --secret="REDACTED_XAI_KEY")
```

---

## Python Integration

### Using `manage_secrets.py`

```bash
# Install dependency
pip install google-cloud-secret-manager

# Create/update a secret
python3 manage_secrets.py --create REDACTED_XAI_KEY "REDACTED_XAI_KEY"

# Load a secret
python3 manage_secrets.py --load REDACTED_XAI_KEY

# Sync all secrets from .env to GCP
source .env
python3 manage_secrets.py --sync-from-env

# List all secrets
python3 manage_secrets.py --list
```

### Code Usage

```python
from google.cloud import secretmanager
import os

def get_xai_key():
    """Load XAI API key from Google Secret Manager."""
    if os.getenv("XAI_API_KEY"):
        return os.getenv("XAI_API_KEY")
    
    # Fallback to Google Secret Manager
    client = secretmanager.SecretManagerServiceClient()
    project_id = "sailly-voice-agent-eu"
    secret_id = "REDACTED_XAI_KEY"
    
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Usage in code
XAI_API_KEY = get_xai_key()
```

---

## Environment File Strategy

### `.env` (Local Development)
- Contains **non-sensitive** config (ports, regions, model names)
- Checked into git (with sensitive data removed)
- Override with env vars in production

### `.env.secrets.example` (Template)
- Documents which secrets are needed
- **NEVER commit actual secrets**
- Template for team members

### Production Secrets (GCP Secret Manager)
- Store sensitive keys in Google Secret Manager
- Load via `gcloud secrets versions access latest --secret="..."`
- Rotate keys without code changes

---

## File Structure

```
/home/charles2/sailly-browser-demo/
├── .env                      # ✅ Non-sensitive config (committed)
├── .env.secrets.example      # ✅ Secrets template (committed)
├── manage_secrets.py         # ✅ Secret management helper
└── .gitignore               # ✅ Ignores actual .env.secrets files
```

### .gitignore entries
```gitignore
# Secrets (never commit)
.env.secrets
.env.local
*.key.json
credentials.json

# Python
__pycache__/
*.pyc
.pytest_cache/
venv/

# IDE
.vscode/
.idea/
```

---

## Testing the Setup

### 1. Verify environment variable
```bash
cd /home/charles2/sailly-browser-demo
export XAI_API_KEY="REDACTED_XAI_KEY"

python3 -c "import os; print('XAI_API_KEY set:', 'xai-' in os.getenv('XAI_API_KEY', ''))"
```

### 2. Run Phase A with XAI key
```bash
python3 server/validation/phase_a_smoke_test.py
# Expected: ✓ PHASE A PASSED (5/5 checks)

# Then with real STS
python3 -m server.validation.loop_runner
# Expected: ✓ PHASE A PASSED (20/20 calls)
```

### 3. Verify Google Secret Manager
```bash
# After syncing secrets to GCP
gcloud secrets list | grep REDACTED_XAI_KEY

# Access and verify
gcloud secrets versions access latest --secret="REDACTED_XAI_KEY" | head -c 20
# Should show: REDACTED_XAI_KEY...
```

---

## Security Best Practices

✅ **DO:**
- Store secrets in Google Secret Manager for production
- Rotate API keys every 90 days
- Use service accounts with minimal permissions
- Enable audit logging for secret access
- Load secrets from environment variables

❌ **DON'T:**
- Commit `.env.secrets` files
- Hardcode keys in Python code
- Share keys in chat/emails/docs
- Use personal API keys in production
- Log secret values

---

## Next Steps

1. **Local Development**
   ```bash
   source .env
   export XAI_API_KEY="REDACTED_XAI_KEY"
   python3 -m server.validation.loop_runner
   ```

2. **Google Secret Manager Setup**
   ```bash
   gcloud auth login
   gcloud config set project sailly-voice-agent-eu
   echo -n "REDACTED_XAI_KEY" | \
     gcloud secrets create REDACTED_XAI_KEY --replication-policy="automatic" --data-file=-
   ```

3. **Production Deployment**
   - Deploy with Cloud Run / Cloud Build
   - Let GCP authenticate automatically (workload identity)
   - Use `google-cloud-secret-manager` to load keys at runtime

---

## Support

- **GCP Secret Manager Docs:** https://cloud.google.com/secret-manager/docs
- **Google Cloud CLI:** https://cloud.google.com/cli
- **Python Client:** https://googleapis.dev/python/google-cloud-secret-manager/latest/

---

**✅ API Keys configured and ready for Sound Validation testing!**
