# Sailly Flow Builder — Phase 0 Findings

## Executive Summary

This document records the complete analysis of the Sailly voice agent brain required to build the Flow Builder — a visual UI inside the sailly.tech dashboard that maps the conversation graph, shows which tools fire at each node, displays the forced-commit guards, lets you replay finished calls step-by-step, and (in Phase 4) edit the graph declaratively.

**Critical constraint:** The graph is *derived from the running brain*, never hardcoded. If someone edits `node_manager.py`, the Builder updates on next reload.

---

## 1. Repo Topology

### Discovery

- **Brain/voice agent server:** `/home/charles2/sailly-browser-demo/` (Python FastAPI)
  - Port 8080 for demo (`/ws/demo`, `/ws/demo_text`, `/ws/headless`)
  - Port 3003 for production (`sailly-voice-agent` service behind nginx at `wss://sailly.tech/ws/demo`)
  - Git repo with `.git/` at root
  - All brain logic: `server/training/conversation_nodes.py`, `node_manager.py`, `conversation_state.py`
  - Tool executor: `tools/executor.py`
  - Monitoring: `server/main.py` hosts `/api/dashboard/*`, `/api/admin/*`, `/admin/call/{call_sid}`, `/admin/transfer/{call_sid}`

- **Dashboard:** `/home/charles2/sailly/apps/dashboard/` (Next.js 14 App Router, TypeScript/React)
  - Deployed to `sailly.tech/` (frontend routing)
  - Git repo separate from `sailly-browser-demo`
  - No pnpm workspace tying them together; they are independent services
  - `package.json` at `apps/dashboard/` (standalone)
  - `next.config.mjs` with rewrites for `/validation-static/*` → validation dashboard

### Consequence for Builder

**New routes are added to the brain server** (`sailly-browser-demo/server/main.py` + new `server/builder/` module).

**Dashboard calls them over HTTP** via:
1. Nginx route: `/api/builder/*` → `:3003/api/builder/*` (same as `/api/dashboard/*` today)
2. Or via `next.config.mjs` rewrite at dev/build time: `/api/builder/:path*` → `${VOICE_AGENT_ORIGIN}/api/builder/:path*` (env var pointing to the brain server)

**Authentication:** Existing JWT + middleware in dashboard handles it; brain server routes don't need special auth for `/api/builder/*` if they're behind nginx/CORS checks.

---

## 2. Complete Node Set

From `server/training/conversation_nodes.py` (`ALL_NODES` dict, lines 145–168):

| Node Name | Category | Node Prompt | Tools | Prerequisites |
|-----------|----------|-------------|-------|---------------|
| `greeting` | Entry | "Du bist Sailly... erstes Kontakt... hilf..." | `ai_greeting`, `faq`, `end_call`, `get_weather`, `get_date_info`, `check_availability`, `verify_address` | — |
| `menu_browse` | Data-fetch interrupt | "Der Kunde fragt nach dem Menü..." | `ai_greeting`, `get_menu`, `faq`, `get_date_info`, `end_call` | `menu_fetched` → `get_menu` |
| `ordering` | State-transition | "Kunde möchte bestellen... erfrage Gericht..." | `ai_greeting`, `create_order`, `send_sms`, `get_menu`, `verify_address`, `get_date_info`, `check_availability`, `end_call` | `menu_fetched` → `get_menu` |
| `reservation` | State-transition | "Kunde möchte reservieren... erfrage Datum, Uhrzeit..." | `check_availability`, `create_reservation`, `get_date_info`, `get_weather`, `verify_address`, `send_sms`, `end_call` | — |
| `escalation` | Error handling | "Technisch/Beleidigung/Catering..." | `technical_issues_callback`, `transfer_to_tier2`, `transfer_to_human`, `request_callback`, `end_call` | — |
| `faq` | Data-fetch (sticky) | "Adresse/Öffnungszeiten/Lieferzeit..." | `ai_greeting`, `faq`, `end_call`, `get_weather`, `get_date_info`, `verify_address`, `check_availability`, `create_order`, `send_sms`, `request_callback` | — |
| `goodbye` | Terminal | "'Vielen Dank...' [TOOL:end_call]" | `end_call`, `send_sms` | — |

**Node.js A4 Invariant:** Every node declares *every* tool that `check_forced_commits()` can inject, so the first-pass node filter never silently drops a forced tool. This is validated in Phase 1 tests.

---

## 3. Edge List (from `select_node()` in `node_manager.py`, lines 244–400)

The routing is deterministic, keyword-driven. Keywords live in lists like `_ABUSE_KW`, `_TRANSFER_KW`, `_ORDER_KW`, etc.

### Edges by source node

**From `greeting` (and any node):**
- → `escalation`: abuse keyword match (`_ABUSE_KW`: "arschloch", "scheiße", "idiot", etc.)
- → `escalation`: payment frustration + transfer keywords
- → `escalation`: hard transfer keyword match (`_HARD_TRANSFER_KW`: "ich will einen agenten", "sprechen sie mich durch", etc.)
- → `escalation`: escalation keyword match (`_ESCALATION_KW`: "kaputt", "fehler", "beschwerde", etc.)

**From any node, if order/reservation completed:**
- → `goodbye`: if both tasks done or only one intent and goodbye keyword
- → `ordering`: if second pending intent is order + `!order_created`
- → `reservation`: if second pending intent is reservation + `!reservation_created`
- → `faq`/`menu_browse`: if FAQ/menu keywords
- → `goodbye` (default)

**From any node (order flow):**
- → `ordering`: order intent detected OR `_ORDER_KW` keywords
- → `menu_browse`: order intent + `!menu_fetched` (push_return "ordering" for interrupt)

**From any node (reservation flow):**
- → `reservation`: reservation intent detected OR `_RESERVATION_KW` keywords
- → `reservation`: implicit (party_size ≥ 2, no dish, no order intent)

**From any node (FAQ/weather interrupt):**
- → `faq`: `_MENU_KW` keywords (menu questions)
- → `faq`: `_WEATHER_KW` keywords (weather questions)
- → `faq`: `_FAQ_KW` keywords (address, hours, etc.)
- When in `ordering` or `reservation`: push_return stack to return later

**From FAQ/menu_browse (interrupt exit):**
- → [return to saved node]: via `_pop_return()` if `node_stack` non-empty

**From escalation (stay until explicit switch):**
- → `escalation`: if `current_node == "escalation"` AND no `_ORDER_KW` / `_RESERVATION_KW` match

**Negation / cancel:**
- `any` → `greeting`: `_NEGATE_KW` (customer says "nicht bestellen", "kein interesse", etc.)

**Goodbye:**
- `any` → `goodbye`: `_GOODBYE_KW` ("tschüss", "auf wiedersehen", "bye", etc.)

### Edge metadata for Builder

Each edge should capture:
```json
{
  "from": "greeting",
  "to": "escalation",
  "label": "abuse",
  "keywords": ["arschloch", "scheiße", "fick", "idiot"],
  "kind": "keyword",
  "source": { "file": "server/training/node_manager.py", "start_line": 69, "end_line": 72 },
  "condition": "any(kw in lower for kw in _ABUSE_KW)"
}
```

---

## 4. Forced-Commit Guard Layer

From `server/training/node_manager.py` `check_forced_commits()` (lines 504–1341), **17 ordered steps** fire state-transition tools atomically (replacing bot text) or data-retrieval tools additively (prepending):

### Step-by-step breakdown

| Order | Tool(s) | Trigger | Atomic? | Notes |
|-------|---------|---------|---------|-------|
| 1 | `ai_greeting` | T0, `!ai_greeting_called` | No (prepend) | Greeting marker on first turn |
| 2 | `request_callback` | `_CALLBACK_KW` detected (one-shot) | Yes (atomic replace) | "Rückruf", "call me back", etc. → template response |
| 2b | `transfer_to_tier2` + `end_call` | `_TRANSFER_KW` + no order/reservation intent (one-shot) | Yes (atomic) | Transfer to human agent, end call |
| 2c-tech | `technical_issues_callback` | `_TECH_KW` early, pre-commit | Yes (atomic) | Audio/tech problems → callback template |
| 2c | `get_date_info` | `_DATE_REL_KW` / reservation_intent without date | No (prepend) | Category A, runs before order/reservation |
| 3 | `check_availability` | reservation_intent OR `_AVAILABILITY_KW`; strips `create_reservation`/`send_sms` same turn | No (prepend) | CRITICAL FLOW: check_availability must run before create_reservation |
| 4 | `create_order` + `send_sms` | `ready_for_order_commit()` at T≥1, `!inquiry_turn` | Yes (atomic) | Full template with dish name |
| 5b | `create_order` + `send_sms` | Stall fallback: get_menu+verify_address called, no create_order | Yes (atomic) | Fallback when LLM doesn't commit after collecting info |
| 5c | `create_order` + `send_sms` | Takeaway stall: order_intent, get_menu called, T≥3, no delivery address | Yes (atomic) | Pickup order fallback |
| 5 | `create_order` + `send_sms` | Timeout: ordering node, turns_in_node ≥ 3 | Yes (atomic) | Safety net if collection stalls |
| 6 | `send_sms` | Auto-pair with LLM-emitted `create_order` | No (append) | CRITICAL FLOW: create_order always pairs with send_sms |
| 7 | `create_reservation` + `send_sms` | After check_availability, reservation_intent, get_date_info, T≥4 | Yes (atomic) | Auto-commit once all info present |
| 7b | `create_reservation` + `send_sms` | `ready_for_reservation_commit()` | Yes (atomic) | Direct commit path |
| 8 | `create_reservation` + `send_sms` | Timeout: reservation_intent + party_size, turns_in_node ≥ 1 (any node) | Yes (atomic) | Fallback after stall |
| 9 | `send_sms` | Auto-pair with LLM-emitted `create_reservation` | No (append) | CRITICAL FLOW pair |
| 10 | `verify_address` | Sticky: `delivery_address_mentioned + order_intent` | No (append) | Once caller mentions address, verify it |
| 11 | `verify_address` | Fallback: order+dish+delivery | No (append) | Ensure address captured for orders |
| 12 | `get_weather` | `_WEATHER_KW` match; auto `end_call` after weather-only 3+ turns | No (prepend) | Weather-only auto-wrap after 3 turns |
| 12b | `get_restaurant_info` | `_LOCATION_KW` (parking, location queries) | No (prepend) | Parking/directions |
| 14 | `technical_issues_callback` | Tech/audio keywords post-reservation | Yes (atomic) | Escalation if complaint after booking |
| 15 | `transfer_to_tier2` | Escalation node timeout (≥ 2 turns) | Yes (atomic) | Force transfer if escalation stalls |
| 16 | `get_menu` | Menu keywords OR ordering stall (order_intent, no dish) | No (prepend) | Re-trigger menu if requested again |
| 17 | `end_call` | Goodbye node forced | No (append) | Always end in goodbye node |

### Preservation across atomic replacements

When atomic replacements fire (Category B state-transition tools), `_extract_already_injected()` preserves Category A tool tags (`ai_greeting`, `check_availability`, `get_weather`, `get_menu`, `get_date_info`) so they don't get lost.

---

## 5. GUARDIAN Preconditions

From `tools/executor.py` `_GUARDIAN_PRECONDITIONS` (lines 337–345):

```python
_GUARDIAN_PRECONDITIONS: dict = {
    "create_order": {
        "required_from_args": ["order_items"],   # dish must be present
        "min_prior_assistant_turns": 2,           # can't fire on T0 or T1
    },
    "create_reservation": {
        "required_from_args": ["date", "time", "party_size"],
        "min_prior_assistant_turns": 3,
    },
}
```

**Gate in `_guardian_pre_commit_check()`** (lines 358–376):
- If any required arg is missing → `(allowed=False, reason, must_ask_for=[...])`
- If turn_number < min_prior_assistant_turns → `(allowed=False, reason)`
- Otherwise → `(allowed=True, reason="ok", [])`

Block result: tool does NOT execute; brain handler logs GUARDIAN_BLOCK, persists to DB, returns structured error so LLM can be told which fields to ask for.

---

## 6. Existing Observability Surface

### Monitoring endpoints (in `server/main.py`)

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `GET /api/dashboard/monitor` | Redis-backed pipeline health (browser demo calls) | JSON { activeWsConnections, recentCalls, ... } |
| `GET /api/dashboard/monitor/calls` | Recent finished/in-progress calls | JSON array of call records (tenant, call_sid, started_at, duration, quality_score) |
| `GET /api/dashboard/live/{call_sid}/trace` | Live Redis trace events (real-time updates during call) | JSON stream of events (tools_called, transcription, etc.) |
| `GET /api/admin/call/{call_sid}/turns` | Per-turn metrics JSON (THE REPLAY SOURCE) | JSON array of turn records |
| `GET /admin/call/{call_sid}` | Per-turn HTML viewer | HTML table with per-turn user/bot text, latencies, tools, node, confidence |

### `google_turn_metrics` table schema

Columns that the Builder will use for replay:
```sql
turn_number INTEGER,           -- 0, 1, 2, ...
node_name TEXT,                -- "greeting", "ordering", ...
user_text TEXT,                -- caller's utterance
bot_text TEXT,                 -- bot response (may have [TOOL:...] tags)
stt_latency_ms INTEGER,        -- STT processing time
llm_latency_ms INTEGER,        -- Gemini LLM time
tts_latency_ms INTEGER,        -- TTS generation time
tools_called JSONB,            -- [{"name": "create_order", ...}, ...]
stt_confidence REAL,           -- 0–1 STT confidence
validation_breakdown JSONB,    -- Sprint C: per-turn validation scores
layer1_decision JSONB,         -- Phase observability: layer1 routing decision
layer2_raw_output TEXT,        -- Phase observability: raw LLM output
layer3_changes JSONB           -- Phase observability: diffs applied
```

**Note:** `/api/admin/call/{call_sid}/turns` returns the full turn records including all columns above.

---

## 7. Dashboard Architecture

### File structure (`sailly/apps/dashboard/`)

```
app/
├── layout.tsx                # Root layout (LayoutShell wraps children)
├── globals.css
├── middleware.ts             # JWT auth + refresh token logic
├── page.tsx                  # Landing page
├── login/page.tsx            # Login form
├── api/
│   ├── auth/
│   │   ├── login/route.ts
│   │   ├── logout/route.ts
│   │   └── me/route.ts       # Get current user
│   ├── dashboard/            # Validation dashboard routes (exist but unused for Builder)
│   ├── demo/                 # Demo tenants, WS tokens
│   ├── health/
│   └── validation/
├── overview/page.tsx         # Dashboard home (calls today, quality, costs)
├── live-calls/page.tsx
├── demo-call/page.tsx
├── calls/page.tsx            # Call history
├── call-analysis/page.tsx
├── checkpoints/page.tsx
├── crucial-fix/page.tsx
├── analytics/page.tsx
├── quality/page.tsx
└── compliance/page.tsx
components/
├── LayoutShell.tsx           # Wraps all non-login pages with Sidebar
├── Sidebar.tsx               # Navigation groups + logout
├── SessionWarning.tsx        # Session expiry warning
└── ui/                       # Radix UI components (Button, Dialog, etc.)
lib/
└── db.ts                     # Postgres client
next.config.mjs               # Standalone build + /validation-static/* rewrite
middleware.ts                 # JWT auth
tsconfig.json                 # paths: "@/*" → "./*"
```

### Authentication

- **Middleware** (`middleware.ts`): JWT (`access_token`/`refresh_token` cookies)
  - Public paths: `/login`, `/demo-call`, `/crucial-fix`, `/api/auth`, `/api/health`, `/_next/*`
  - Protected paths: everything else → check JWT, refresh if stale, redirect to login if expired
  - Role field in JWT: `admin`, `user`, etc. (used for edit mode gating in Phase 4)

- **Session:** access_token TTL = 4 hours (or 400 days for admins), refresh_token = 24 hours

### Navigation convention (`Sidebar.tsx`)

```typescript
const navigationGroups = [
  { label: "Operations", items: [ { label: "Overview", href: "/overview", icon: BarChart3 }, ... ] },
  { label: "Configure", items: [ { label: "Agent Config", href: "/agent", icon: Settings }, ... ] },
  { label: "Insights", items: [ { label: "Analytics", href: "/analytics", icon: LineChart }, ... ] },
  { label: "Data", items: [ { label: "Compliance", href: "/compliance", icon: Lock }, ... ] },
  { label: "Legacy", items: [ ... ] },
];
```

**Builder will be added** to "Configure" group:
```typescript
{ label: "Builder", href: "/builder", icon: GitBranch }
```

### Styling conventions

- **Tailwind + brand tokens:**
  - Colors: `brand-pink` (#ec4899), `brand-navy` (#001f3f), `brand-cream` (#f5e9e4), `brand-muted`, `brand-peach`, `brand-salmon`
  - Cards: `bg-white shadow-sm border border-brand-cream rounded-lg p-4`
  - Text: `text-brand-navy`, `font-bold`, `text-xs uppercase tracking-widest`
- **Component pattern:** Client-side state with `useState`, fetches on `useEffect`
- **Error handling:** Try/catch with fallback mock data (e.g., `overview/page.tsx` uses fallback metrics if API fails)

### Backend API integration

**Pattern:** Client pages fetch relative `/api/*` routes.
- If route is a Next.js route handler → handled in `app/api/` (e.g., `/api/auth/me`)
- If route should proxy to voice agent → use `next.config.mjs` rewrites (e.g., `/api/dashboard/*` → `:3003/api/dashboard/*`)

**Builder will use:** `/api/builder/*` routes (proxied to voice agent via rewrite)

---

## 8. Builder Integration Points

### Existing infrastructure the Builder will reuse

1. **`google_turn_metrics` table:** Existing replay source (per-turn user/bot text, node names, tools, latencies)
2. **`/api/dashboard/monitor/calls`:** Recent calls (for call picker)
3. **Monitoring endpoints:** `/api/dashboard/live/{call_sid}/trace` (for live mode, stretch)
4. **Auth:** Existing JWT middleware (no extra auth setup needed)
5. **Styling:** Existing Tailwind + brand tokens (matching dashboard UX)
6. **Nav:** Sidebar group system (just add Builder entry)
7. **Fetch pattern:** `useEffect` + `fetch()` + `useState` (matches dashboard pages)

### What Builder adds (new)

- **`GET /api/builder/graph?tenant=<id>`** — full conversation graph JSON (nodes, edges, tools, forced commits)
- **`GET /api/builder/tenants`** — list available tenants (IDs, names, industries)
- **`GET /api/builder/calls?tenant=<id>`** — thin wrapper, same data as `/api/dashboard/monitor/calls`
- **`GET /api/builder/call/{call_sid}/turns`** — wrapper, same data as `/api/admin/call/{call_sid}/turns` (replay source)
- **`GET /api/builder/call/{call_sid}/trace`** — wrapper around live trace
- **`POST /api/builder/proposals`** → `POST /api/builder/proposals/{id}/apply` (Phase 4 editor)

---

## 9. Implementation approach

### Phase 1: Backend introspection

**Module:** `server/builder/graph_introspect.py`

Functions:
- `build_graph(tenant_id: str) -> dict` — Main introspection function
  - Load `ALL_NODES` from `conversation_nodes.py`
  - Parse `select_node()` keyword lists and branch logic to extract edges
  - Load tenant YAML and merge tool schemas
  - Load `_GUARDIAN_PRECONDITIONS` and `check_forced_commits()` steps
  - Compute source line ranges using `inspect.getsourcelines()`
  - Return JSON graph: `{ tenant, nodes: [...], edges: [...], tools: [...], forced_commits: [...] }`
- `list_tenants() -> List[dict]` — List available tenants
- Thin wrappers for `/api/dashboard/*` endpoints

**Tests:** Validate every edge target exists in ALL_NODES; every forced-commit tool has an executor handler.

### Phase 2: Frontend canvas + replay

**Components:**
- `FlowCanvas.tsx` — ReactFlow + dagre layout
- `InspectorPanel.tsx` — Tabbed drawer (Prompt, Tools, Guards, Code)
- `ReplayBar.tsx` — Call picker, transport controls, timeline
- `TenantSwitcher.tsx` — Dropdown + channels strip

**Main page:** `app/builder/page.tsx` — Layout combining canvas + inspector + replay

### Phase 3: Tenant awareness

- TenantSwitcher → refetch graph on change
- Show per-tenant tools + prompts

### Phase 4: Editor (three tiers)

- Tier 1: YAML edits → proposals flow
- Tier 2: Node prompts → regression gate
- Tier 3: Structural → full validation + PR workflow

---

## 10. No changes to brain runtime

All builder-related code is:
- **Additive in `server/main.py`:** new routes registered; no changes to existing logic
- **New module:** `server/builder/` (read-only introspection; no imports of pipeline objects)
- **Comment-only markers optional:** `# BUILDER-EDGE:` tags in `node_manager.py` if edge parsing needs hints (comments only, no behaviour change)

**Guarantee:** If builder code is removed, voice agent continues unchanged.

---

## 11. Decisions log

| Decision | Rationale | Confirmed |
|----------|-----------|-----------|
| Separate repos → HTTP API | Simplest integration; no code duplication; reuses existing nginx routes | Yes |
| Edge parsing via keyword lists | More robust than AST; keyword constants already declared; markers optional fallback | Yes |
| `inspect.getsourcelines()` for source ranges | Exact line ranges; supports clickable code viewer | Yes |
| Phases 0→1→2→3→4 gates | Early stopping prevents building UI on broken graph; tests validate consistency | Yes |
| Tenant YAML → lowest risk editor tier | Data-driven, no code changes; existing TenantRegistry reloads safely | Yes |
| Git branch/PR for Tiers 2–3 | Never hot-patch production; all changes reviewable + deployable | Yes |

---

## End of Phase 0 findings

**Status:** Ready for Phase 1 implementation.

To proceed, confirm:
1. ✅ Repo topology decision (separate repos, HTTP API via nginx)
2. ✅ Node set complete (7 nodes, all tools catalogued)
3. ✅ Edge list and forced-commit guards documented
4. ✅ GUARDIAN preconditions noted
5. ✅ Observability surface (monitoring + turn_metrics) identified
6. ✅ Dashboard conventions (Nav, Auth, Styling, Fetch) captured
7. ✅ Phase 1 scope clear (graph_introspect.py + routes + tests)
