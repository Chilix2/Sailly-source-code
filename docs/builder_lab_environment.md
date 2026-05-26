# Builder Lab Environment

This runbook records the read-only topology observed on this host and the lab-safe
commands/artifacts needed to create an isolated Builder Lab. It does not require
editing `/etc/nginx`, editing `/etc/systemd`, or restarting any live service.

## Observed Live Topology

Repos:

- Backend/runtime/builder API: `/home/charles2/sailly-browser-demo`
- Dashboard/monorepo tree: `/home/charles2/sailly`
- Dashboard app: `/home/charles2/sailly/apps/dashboard`

Systemd:

- `sailly-browser-demo.service`: working directory `/home/charles2/sailly-browser-demo`, `uvicorn server.main:app`, port `8080`
- `sailly-dashboard.service`: working directory `/home/charles2/sailly/apps/dashboard`, Next standalone server, port `3001`
- `sailly-backend-api.service`: working directory `/home/charles2/sailly`, Fastify API, port `3002`
- `sailly-voice-agent.service`: not found/inactive on this host
- `redis-server.service`: active on `6379`
- `postgresql@17-main.service`: active on `5432`

Nginx:

- `sailly_demo` upstream points at `127.0.0.1:8080`.
- `sailly.tech` routes `/api/builder/`, selected dashboard monitor APIs, and `/ws/demo` to `sailly_demo`.
- Other live routes still reference `3001`, `3002`, and stale `3003`. Builder Lab must not reuse or change those routes.

Environment:

- The live backend unit currently defines secrets inline plus `REDIS_URL` and `DATABASE_URL` for the production-like runtime.
- Existing repo env files include `configs/env/.env.dev`, `.env.staging`, and `.env.prod`; all use `DEMO_PORT=8080`.
- Dashboard `next.config.mjs` defaults `VOICE_AGENT_ORIGIN` to `http://127.0.0.1:3003`, so Builder Lab dashboard builds must set `VOICE_AGENT_ORIGIN=http://127.0.0.1:18080`.

## Lab Isolation Contract

Use these lab-only names and ports:

- Lab root: `/home/charles2/builder-lab`
- Backend repo path: `/home/charles2/builder-lab/sailly-browser-demo`
- Dashboard repo path: `/home/charles2/builder-lab/sailly`
- Backend port: `18080`
- Dashboard port: `13001`
- Postgres database: `sailly_builder_lab`
- Postgres user: `sailly_lab`
- Redis logical DB: `14`
- Redis monitor keys: `builder_lab:monitor:completed_calls`, `builder_lab:monitor:config`
- Default lab tenant: `builder_lab_doboo`

Safety defaults:

- `ENABLE_TWILIO=false`
- `SMS_DRY_RUN=true`
- `SERVER_URL=http://127.0.0.1:18080`
- Bind backend systemd template to `127.0.0.1`, not `0.0.0.0`.

## Repo-Local Artifacts

- `configs/env/.env.builder_lab.example`: non-secret backend env template.
- `scripts/builder_lab_preflight.sh`: read-only validation of port/env/database/Redis separation.
- `deploy/builder_lab/sailly-builder-lab.service.template`: inactive backend systemd template.
- `deploy/builder_lab/sailly-builder-lab-dashboard.service.template`: inactive dashboard systemd template.
- `deploy/builder_lab/nginx-builder-lab.locations.template`: inactive nginx location template for a future dedicated lab host.

## Create The Lab Tree

These commands create lab working copies without touching production service paths:

```bash
mkdir -p /home/charles2/builder-lab
rsync -a --exclude venv --exclude logs --exclude .git /home/charles2/sailly-browser-demo/ /home/charles2/builder-lab/sailly-browser-demo/
rsync -a --exclude node_modules --exclude .next /home/charles2/sailly/ /home/charles2/builder-lab/sailly/
cd /home/charles2/builder-lab/sailly-browser-demo
cp configs/env/.env.builder_lab.example .env.builder_lab
```

Fill only the secret values in `.env.builder_lab`. Keep it untracked.

## Create Lab Database

Run only after approving a new lab database on the existing local Postgres cluster:

```bash
sudo -u postgres createuser sailly_lab --pwprompt
sudo -u postgres createdb --owner=sailly_lab sailly_builder_lab
```

If schema migrations are available for the backend, apply them to `sailly_builder_lab`.
If not, clone only the required schema from the current `sailly` database after an
explicit data-safety review; do not copy production call/transcript rows into the lab.

## Run Backend Manually

Manual foreground run, no systemd:

```bash
cd /home/charles2/builder-lab/sailly-browser-demo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
set -a
source .env.builder_lab
set +a
bash scripts/builder_lab_preflight.sh .env.builder_lab
python3 -m uvicorn server.main:app --host 127.0.0.1 --port 18080
```

Health checks:

```bash
curl -fsS http://127.0.0.1:18080/healthz
curl -fsS http://127.0.0.1:18080/api/builder/runtime
```

## Run Dashboard Manually

The dashboard rewrite must point at the lab backend during build and runtime:

```bash
cd /home/charles2/builder-lab/sailly/apps/dashboard
npm install
VOICE_AGENT_ORIGIN=http://127.0.0.1:18080 \
VOICE_AGENT_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_VOICE_AGENT_WSS=ws://127.0.0.1:18080 \
npm run build
PORT=13001 \
VOICE_AGENT_ORIGIN=http://127.0.0.1:18080 \
VOICE_AGENT_URL=http://127.0.0.1:18080 \
NEXT_PUBLIC_VOICE_AGENT_WSS=ws://127.0.0.1:18080 \
node .next/standalone/server.js
```

Open the lab dashboard locally at `http://127.0.0.1:13001`.

## Optional Service Templates

The files in `deploy/builder_lab/` are templates only. Installing them would be a
live `/etc/systemd` or `/etc/nginx` change and is intentionally outside this work
package.

If approved later, copy them into `/etc/systemd/system/` and a dedicated nginx lab
server block, then run `systemctl daemon-reload`, `systemctl start ...`, and
`nginx -t`. Do not add Builder Lab locations to the existing production
`sailly.tech` server block.

## Blockers Before Publishing A Public Lab

- The dashboard build currently needs explicit `VOICE_AGENT_ORIGIN`; its default still points to stale port `3003`.
- The live nginx production routes still contain stale `3003` references; do not depend on those for lab validation.
- The backend `/health` route is routed in nginx to `3003`, while this backend exposes `/healthz`; use `/healthz` for lab checks unless a code-level health alias is added.
- Database schema bootstrap for a clean `sailly_builder_lab` is not defined in this repo-local package.
- Public lab exposure needs a dedicated hostname, TLS, and auth decision before any nginx changes.
