# Sailly Production Stand - Live Source Snapshot

This archive is generated automatically from the live production server.

## Services

- Voice Agent: port 8080, source from `/home/charles2/sailly-browser-demo`
- Backend API: port 3002, source from `/home/charles2/sailly`

## Restore

Voice agent:

```bash
cd voice-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080
```

Backend API:

```bash
cd backend-api
cp .env.production.template .env
NODE_ENV=production npx tsx index-minimal.ts
```

Credentials are not included. See `SECRETS.md`.
