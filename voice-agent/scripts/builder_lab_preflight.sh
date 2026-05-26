#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env.builder_lab}"

echo "Builder Lab preflight (read-only)"
echo "repo: $ROOT"
echo "env:  $ENV_FILE"
echo

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing env file"
  echo "create one with:"
  echo "  cp $ROOT/configs/env/.env.builder_lab.example $ENV_FILE"
  exit 2
fi

python3 - "$ENV_FILE" <<'PY'
import os
import re
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

env_path = Path(sys.argv[1])
env = {}
for raw in env_path.read_text().splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    env[key.strip()] = value.strip().strip('"').strip("'")

def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)

def warn(message: str) -> None:
    print(f"WARN: {message}")

def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0

port = int(env.get("DEMO_PORT", "0") or "0")
if port in {3000, 3001, 3002, 3003, 8080, 8090}:
    fail(f"DEMO_PORT={port} collides with known live service ports")
if port <= 0:
    fail("DEMO_PORT is missing or invalid")
if port_open("127.0.0.1", port):
    fail(f"port {port} is already listening")
print(f"OK: backend lab port {port} is free")

redis_url = env.get("REDIS_URL", "")
redis = urlparse(redis_url)
if not redis_url:
    fail("REDIS_URL is missing")
if redis.hostname not in {"localhost", "127.0.0.1"}:
    warn(f"REDIS_URL host is not local: {redis.hostname}")
if redis.path in {"", "/", "/0"}:
    fail("REDIS_URL must use a nonzero lab DB, for example redis://localhost:6379/14")
print(f"OK: Redis namespace uses DB {redis.path.lstrip('/')}")

db_url = env.get("DATABASE_URL", "")
if not db_url:
    fail("DATABASE_URL is missing")
if not re.search(r"/sailly_builder_lab($|[?])", db_url):
    fail("DATABASE_URL must point at database sailly_builder_lab")
print("OK: Postgres database name is sailly_builder_lab")

for key in ("MONITOR_REDIS_LIST_KEY", "MONITOR_CONFIG_REDIS_KEY"):
    value = env.get(key, "")
    if not value.startswith("builder_lab:"):
        fail(f"{key} must start with builder_lab:")
print("OK: monitor Redis keys are lab-prefixed")

if env.get("ENABLE_TWILIO", "").lower() not in {"0", "false", "no"}:
    fail("ENABLE_TWILIO must be false for the lab")
if env.get("SMS_DRY_RUN", "").lower() not in {"1", "true", "yes"}:
    fail("SMS_DRY_RUN must be true for the lab")
print("OK: telephony/SMS side effects are disabled")

print()
print("Preflight passed. This script did not modify services, nginx, Redis, or Postgres.")
PY
