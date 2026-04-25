# Sailly Live Demo — Architecture Ground Truth Audit
**Date**: 2026-04-20  
**Scope**: Forensic analysis of which codebase serves live calls and how it differs from production  
**Methodology**: No changes; pure discovery via configuration inspection, process listing, and code inventory

---

## 1. The Request Path (What Actually Runs)

### 1.1 nginx Routing — sailly.tech

**Live demo entry point**: Browser opens `https://sailly.tech/demo-call` → (served by Next.js frontend at port 3001)

**WebSocket connection** (the actual voice stream):
- Browser connects to: `wss://sailly.tech/ws/demo` (WebSocket Secure)
- nginx rule: `location = /ws/demo` → proxies to `http://sailly_demo` → resolves to `127.0.0.1:8080`
- **Result: Browser demo calls handled by port 8080 (`sailly-browser-demo`)**

**Dashboard endpoints**:
- `GET /api/dashboard/monitor` → `http://sailly_demo` (port 8080)
- `GET /api/dashboard/monitor/calls` → `http://sailly_demo` (port 8080)
- `GET /api/dashboard/live/{call_sid}/trace` → (not specified in nginx; likely port 8080)

**Other WebSocket routes** (fallback):
- `location /ws/` → `http://127.0.0.1:3003` (voice agent, if not matched by specific rules)

**Conclusion**: Live demo calls on port 8080 (`sailly-browser-demo`); NOT port 3003

---

## 2. The Processes Running

| Port | Service | Process | Codebase | Working Directory |
|------|---------|---------|----------|-------------------|
| **8080** | `sailly-browser-demo` | `python3 -m uvicorn server.main:app` | `sailly-browser-demo` | `/home/charles2/sailly-browser-demo` |
| **3003** | `sailly-voice-agent` | `python3 server/main.py` | `sailly-google-fork` | `/home/charles2/sailly-google-fork` |
| **3001** | `sailly-dashboard` | `next-server` | Frontend (Next.js) | — |
| **3002** | `sailly-backend-api` | `node` | Fastify API | — |
| **8090** | `sailly-validation-static` | `python3` | Validation dashboard | — |

---

## 3. The Codebases

### sailly-browser-demo (Port 8080 — LIVE DEMO)
- Location: `/home/charles2/sailly-browser-demo`
- Entry: `server/main.py` (21,277 bytes)
- Python files: 15,743
- Size: 869 MB
- Framework: FastAPI
- Status: **SERVES LIVE DEMO CALLS**

### sailly-google-fork (Port 3003 — NOT USED FOR LIVE DEMO)
- Location: `/home/charles2/sailly-google-fork`
- Entry: `server/main.py` (220,817 bytes — 10x larger)
- Python files: 27,636
- Size: 1.8 GB
- Framework: FastAPI
- Status: Production voice agent (Twilio PSTN) — **NOT used for sailly.tech/demo-call**

### Relationship
- **NOT submodules, NOT symlinked** — two independent repos
- **Same database** — both write to `postgresql://postgres:sailly2026@localhost:5432/sailly`
- **Different brain code** — divergent in `adk_turn_processor.py` (296 line diffs)
- **Separate entry points** and purpose
- **Intent** (inferred): browser-demo for isolated WebRTC demo; google-fork for Twilio PSTN

---

## 4. The Brain — Same 97% Phase A Brain?

### Brain Files Status

| File | browser-demo | google-fork | Status |
|------|--------------|-------------|--------|
| `node_manager.py` | 1,037 lines | 1,028 lines | DIVERGENT (103 diff lines) |
| `conversation_state.py` | 418 lines | 429 lines | DIVERGENT (12 diff lines) |
| `adk_turn_processor.py` | 973 lines | 797 lines | **DIVERGENT (296 diff lines — MAJOR)** |
| `tier2_runner.py` | 722 lines | 698 lines | DIVERGENT (81 diff lines) |

### Verdict
- **YES — the 97% Phase A brain IS used**
- **BUT — the implementations have significantly diverged** (especially turn processor)
- Fixes to one don't auto-propagate to the other
- Backup dirs (`_backup_after_all_fixes/`, `_backup_original_restored/`) suggest manual rework

---

## 5. The Tools — Real or Stubs?

| Tool | Status | Notes |
|------|--------|-------|
| `ai_greeting` | **STUB** | No-op, just logs |
| `get_menu` | **REAL** | Returns mock DOBOO menu with prices |
| `verify_address` | **REAL** | Calls Google Maps API |
| `create_order` | **REAL** | Validates, stores to DB; **REJECTS on total_price=0.0** |
| `send_sms` | **STUB** | **ALWAYS RETURNS SUCCESS**, even if create_order failed |
| `end_call` | **REAL** | |
| `get_weather`, `get_date_info` | **REAL** | |

### Critical Bug: send_sms Is a No-Op That Lies

```python
async def _send_sms_noop(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    logger.info(f"[send_sms] No-op — SMS already sent by create_order/create_reservation executor")
    return {
        "status": "ok",
        "note": "SMS confirmation sent automatically by order/reservation executor.",
    }
```

**Evidence**: Call `demo-36864742e817`
- `create_order()` failed: `{"error": "Fehlende Pflichtfelder: total_price"}`
- `send_sms()` immediately after: `{"status": "ok"}`
- **Result**: Brain + user both misled into thinking order succeeded

### Critical Missing Feature: Menu Caching

- `get_menu()` executes in T0, returns prices
- **No code preserves this data between turns**
- On T3, when price needed for "Kimchi Jjigae", it's gone
- Brain defaults `total_price=0.0`
- Order rejected

---

## 6. Observability

### Database Persistence
- **Writes to shared Postgres DB**: `postgresql://postgres:sailly2026@localhost:5432/sailly`
- **Tables**: `google_calls`, `google_turn_metrics`, `google_tool_calls`, `google_transcripts`, `guardian_blocks`
- **Finding**: Browser-demo and google-fork data are intermingled in same tables

### Dashboard Endpoints on browser-demo
```
GET /api/dashboard/monitor           → overview + snapshot
GET /api/dashboard/monitor/calls     → recent calls (detail)
GET /api/dashboard/live/{call_sid}/trace → live trace
```

**Finding**: Dashboard queries browser-demo data (port 8080), not google-fork

### Logging
- Structured logs via `loguru` with tags `[BARGE_IN]`, `[BRAIN]`, etc.
- Journal: `sudo journalctl -u sailly-browser-demo`
- Logs show failures clearly (as evidenced by `demo-36864742e817` logs)

---

## 7. The Fork Point

### Why Two Codebases

**Inferred**:
1. **sailly-google-fork** — Production Twilio PSTN voice agent (full-featured, 220KB main.py)
2. **sailly-browser-demo** — Lightweight isolated browser demo extracted to:
   - Avoid Twilio complexity (no PSTN routing, no WhatsApp, etc.)
   - Enable fast iteration
   - Test brain in isolation

### Code Divergence Problem
- **296 line difference in core turn processor** — why?
- **No documentation** explaining the split or sync strategy
- **Result**: Fixes not propagated; two different implementations of same brain

---

## 8. My Surprising Findings

1. **Two completely separate codebases** serve the same logical function (the 97% Phase A brain) but with **296 lines of core differences**. This is a maintenance nightmare.

2. **The brain IS the Phase A brain** — but it has diverged. Fixes applied to google-fork (BargeInHandler, TTSWatchdog, etc.) had to be manually copied to browser-demo.

3. **send_sms is intentionally a no-op** — not a bug, but a feature. Yet it returns `{"status": "ok"}` even when the parent `create_order` fails. The comment says "SMS already sent by create_order", which is FALSE.

4. **Menu prices are fetched and immediately lost** — `get_menu()` returns prices, but no code preserves them in conversation state. When T3 needs a price, it's gone (`total_price=0.0`).

5. **Both codebases write to the same Postgres DB** — call data from live-demo and production are intermingled. No way to distinguish which service created each call without metadata.

6. **Backup directories in browser-demo** — `_backup_after_all_fixes/` and `_backup_original_restored/` suggest version control issues or manual rollbacks.

7. **Dashboard endpoints duplicated** — both codebases serve `/api/dashboard/*`. Unclear which is used when or if both are active simultaneously.

8. **The fork point is undocumented** — no README, no git history explanation, no maintenance guide. The two codebases exist, but why and how they should stay in sync is unclear.

---

## 9. Conclusion

### What Actually Runs
- User opens `sailly.tech/demo-call` → frontend connects WebSocket to `sailly.tech/ws/demo`
- nginx routes to `127.0.0.1:8080` → **`sailly-browser-demo`** (NOT google-fork on 3003)
- Pipeline: Pipecat (WebRTC) + Deepgram STT + ADKTurnProcessor (diverged brain) + Stubs for send_sms + Gemini TTS
- Data → shared Postgres DB

### Critical Problems
1. **Two divergent codebases** — same purpose, different code (296 line differences in core)
2. **Menu prices not cached** — direct cause of `total_price=0.0` failures
3. **send_sms returns false success** — user hears "SMS sent" even on order failure
4. **No clear ownership or sync strategy** — which is canonical? How to maintain?
5. **Dashboard endpoints and database mixing** — unclear data provenance

### Next Steps (NOT Recommended in This Audit)
- Option A: Deprecate google-fork, make browser-demo canonical
- Option B: Sync brain code, pick one as source of truth
- Option C: Investigate if routing is wrong (should google-fork serve live demo?)
- Option D: Document the split as intentional and establish sync protocol

**This audit is pure discovery. The decision on which path to take is separate.**
