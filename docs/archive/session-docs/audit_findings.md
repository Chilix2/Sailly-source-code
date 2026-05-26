# Phase 1–9 Legacy Code Audit — 2026-04-25

## Summary
- **Total findings: 33**
- **Critical (broken at runtime): 10**
- **High (drift from plan, will break): 10**
- **Medium (dead code, not breaking): 9**
- **Low (cosmetic, naming, comments): 4**

---

## Findings

### [FINDING-001] `call_external` imported from non-existent symbol in tools/executor.py and tools/sms_service.py

- **Severity:** critical
- **Phase reference:** Phase 9 B3 — Circuit breaker migration
- **File(s):**
  - `/home/charles2/sailly-browser-demo/tools/executor.py` lines 226, 236, 1821, 1828
  - `/home/charles2/sailly-browser-demo/tools/sms_service.py` lines 151, 158
- **Line(s):**
  - `executor.py:226`: `from server.core.resilience import call_external, POS_BREAKER, CircuitBreakerOpenError`
  - `executor.py:1821`: `from server.core.resilience import call_external, MAPS_BREAKER, CircuitBreakerOpenError`
  - `sms_service.py:151`: `from server.core.resilience import call_external, SMS_BREAKER, CircuitBreakerOpenError`
- **Current state:** Both files import `call_external`, `POS_BREAKER`, and `CircuitBreakerOpenError` from `server.core.resilience`. None of these three names exist in that package — the `__init__.py` exports only `CircuitBreaker`, `BreakerOpenError`, `BreakerState`, `with_breaker`, `MAPS_BREAKER`, `TWILIO_BREAKER`, `WHATSAPP_BREAKER`, `SMS_BREAKER`, `GEMINI_BREAKER`.
- **Expected state:** External HTTP calls should use `await with_breaker(SMS_BREAKER, coro)` (the standalone function form) or be replaced by the Phase 3 handler equivalents.
- **Risk if left:** Any code path that hits these import lines raises `ImportError` at runtime. This already caused the `verify_address` failure in `demo-f07b90afc1bf`. SMS confirmations (create_order, create_reservation success flows) are similarly broken every call.
- **Suggested fix:** Remove the three dead imports; replace the `call_external(BREAKER, ...)` call pattern with `await with_breaker(BREAKER, _actual_coro(...))` using the correct standalone function signature from `server.core.resilience`.

---

### [FINDING-002] verify_address.py uses `@MAPS_BREAKER.with_breaker` decorator — attribute does not exist

- **Severity:** critical
- **Phase reference:** Phase 9 B3 — circuit breaker wiring; fix applied Apr 25 2026
- **File(s):** `/home/charles2/sailly-browser-demo/server/tools/handlers/verify_address.py`
- **Line(s):** ~93, ~102 (post-Apr-25 fix)
- **Current state:** The Apr 25 rewrite of `maps_lookup()` uses `@MAPS_BREAKER.with_breaker` as a decorator on the inner `call_geocoding` function. `CircuitBreaker` in `server/core/resilience/breakers.py` has no `with_breaker` attribute or method — the public API is the **standalone function** `with_breaker(breaker, coro)` defined at line 133 of `breakers.py`.
- **Expected state:** `result = await with_breaker(MAPS_BREAKER, call_geocoding())` — calling the function, not using a decorator from the breaker instance.
- **Risk if left:** Every `verify_address` call raises `AttributeError` at the point `call_geocoding()` is invoked. Address validation always fails silently, delivery orders are unblocked without a valid address.
- **Suggested fix:** Replace the `@MAPS_BREAKER.with_breaker` decorator with a direct call: `result = await with_breaker(MAPS_BREAKER, call_geocoding())` inside the `maps_lookup` function body.

---

### [FINDING-003] Layer 3 policy.check() never called from any production turn path

- **Severity:** critical
- **Phase reference:** Phase 8 B1–B8 — L3 policy guards
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/layer3/policy.py` (~433–480)
  - `/home/charles2/sailly-browser-demo/server/brain/adk_turn_processor.py`
- **Line(s):** policy.py lines 433–480 (`check()` function); zero call sites in `server/` production code
- **Current state:** `policy.check()` fully implements all 8 guards in order: `check_tech_problem`, `check_quantity_in_tools`, `check_monetary_cap`, `check_after_hours_orders`, `filter_bot_profanity`, `strip_blacklisted`, `check_prices_in_text`, `check_length_cap`. Zero production files under `server/` import or invoke `policy.check()`. It is exercised only in `test_phase8_guards.py`.
- **Expected state:** `policy.check(text, tools, tenant_policy)` called in `adk_turn_processor.py` after the LLM generates a bot response, before the response is handed to TTS.
- **Risk if left:** All Phase 8 safety guards are completely bypassed in every live call: hallucinated prices are spoken, profanity is not filtered, monetary cap is unenforced, after-hours orders are accepted.
- **Suggested fix:** Import `from server.brain.layer3 import policy` in `adk_turn_processor.py`; call `policy.check(bot_text, tool_calls, tenant_policy)` in the post-LLM bot text preparation block; act on the returned `PolicyResult`.

---

### [FINDING-004] write_audit_entry never called in production

- **Severity:** critical
- **Phase reference:** Phase 8 B6 — Audit log
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/observability/audit.py` line 39
  - `/home/charles2/sailly-browser-demo/tools/executor.py`
  - `/home/charles2/sailly-browser-demo/server/tools/handlers/*.py`
- **Line(s):** audit.py:39 (`async def write_audit_entry`); audit.py:30–36 (`AUDITED_TOOLS`)
- **Current state:** `write_audit_entry` is defined. `AUDITED_TOOLS` lists `create_order`, `create_reservation`, `modify_order`, `cancel_order`, `transfer_to_human`. No production code under `server/` calls it. Only `test_phase8_guards.py` references it. The audit.py docstring says "called from dispatcher.py" but no such call exists.
- **Expected state:** Called from `tools/executor.py`'s `execute_tool` after every state-mutating tool succeeds or fails for tools in `AUDITED_TOOLS`.
- **Risk if left:** Zero audit trail for orders, reservations, cancellations, and transfers. Compliance requirement entirely unmet; `audit_log` table stays empty indefinitely.
- **Suggested fix:** Add `await write_audit_entry(...)` in `execute_tool` success and failure branches for each tool in `AUDITED_TOOLS`.

---

### [FINDING-005] build_turn_metrics_extra / calc_turn_cost_eur not wired to the main INSERT path

- **Severity:** critical
- **Phase reference:** Phase 9 A1 — Turn timings and cost
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/layer1/persist.py`
  - `/home/charles2/sailly-browser-demo/server/brain_service.py` (~971–992)
- **Line(s):** persist.py defines `build_turn_metrics_extra()`; brain_service.py INSERT block never imports or calls it
- **Current state:** `build_turn_metrics_extra()` in `persist.py` computes `cost_eur` via `calc_turn_cost_eur()` from `TurnTimings`. However, it is never imported or called from `brain_service.py` — the actual INSERT path. `brain_service.py` builds its metrics dict directly from `_turn_timings.to_metrics_dict()` which does NOT include `cost_eur`.
- **Expected state:** `build_turn_metrics_extra(state, timings)` should be called by `brain_service.py` before every `google_turn_metrics` INSERT, with its result merged into the INSERT dict.
- **Risk if left:** `cost_eur` is always NULL. Phase 9 A1 operator cost dashboard and cost-spike alerts never fire.
- **Suggested fix:** Import `build_turn_metrics_extra` from `server.brain.layer1.persist` in `brain_service.py`; call it in the metrics accumulation block; merge the result into the INSERT dict.

---

### [FINDING-006] error_codes never written to google_turn_metrics

- **Severity:** critical
- **Phase reference:** Phase 9 B1 — Error codes
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain_service.py` (~971–992 INSERT block)
  - `/home/charles2/sailly-browser-demo/server/tools/common/errors.py`
- **Line(s):** brain_service.py INSERT block; errors.py line ~22–30 (`error_code: Optional[str]` on `ToolResult`)
- **Current state:** `ToolResult` correctly has `error_code: Optional[str]`. However, the `brain_service.py` INSERT statement has no `error_codes` column. No code aggregates per-tool `error_code` values into a turn-level `error_codes: list[str]` array before or during the INSERT.
- **Expected state:** After each turn's tool calls complete, collect all non-None `error_code` values into an array and write to `google_turn_metrics.error_codes`.
- **Risk if left:** The SLA monitor's `_check_error_rate()` query on `error_codes IS NOT NULL` always returns 0. Circuit breaker and error-rate alerts are blind. Confirmed NULL in `demo-f07b90afc1bf`.
- **Suggested fix:** In `brain_service.py` metrics accumulation, collect `[r.error_code for r in tool_results if r.error_code]` and include as `"error_codes": [...]` in the INSERT dict.

---

### [FINDING-007] tts_first_byte_at never assigned; tts_first_byte_ms always NULL

- **Severity:** critical
- **Phase reference:** Phase 9 A1 — TurnTimings
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/contracts/turn_timings.py`
  - `/home/charles2/sailly-browser-demo/server/brain/adk_turn_processor.py`
- **Line(s):** turn_timings.py defines `tts_first_byte_at`; no assignment found anywhere in `server/`
- **Current state:** `TurnTimings` defines `tts_first_byte_at` and computes `tts_first_byte_ms` from it. Searching all `server/` files finds zero assignments to `tts_first_byte_at`. `stt_done_at` (line ~866), `l2_done_at` (~1081), `extract_done_at` (~1166), and `tool_done_at` (~1708) are all stamped in `adk_turn_processor.py`. `tts_first_byte_at` is absent.
- **Expected state:** `state._turn_timings.tts_first_byte_at = time.monotonic()` called in the Pipecat TTS first-audio-chunk callback.
- **Risk if left:** `tts_first_byte_ms` always NULL. Latency SLO tracking covers only total latency, missing the critical TTS contribution that often dominates p95.
- **Suggested fix:** Locate the Pipecat TTS first-chunk callback in `main.py` or `brain_service.py`; assign `tts_first_byte_at = time.monotonic()` there on the active `_turn_timings` object.

---

### [FINDING-008] prompt_tokens_out and extract_tokens_* never assigned; Gemini usage_metadata not captured

- **Severity:** critical
- **Phase reference:** Phase 9 A1 — Token counting
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/adk_turn_processor.py`
  - `/home/charles2/sailly-browser-demo/server/brain/brain_service.py`
  - `/home/charles2/sailly-browser-demo/server/brain/contracts/turn_timings.py`
- **Line(s):** brain_service.py writes `prompt_tokens_out` from `self._last_prompt_tokens_out` which is never assigned; `TurnTimings` token fields never set
- **Current state:** `brain_service.py` writes `prompt_tokens_out` from `self._last_prompt_tokens_out` — that attribute is never assigned anywhere in `server/`. `TurnTimings` defines `prompt_tokens_in/out` and `extract_tokens_in/out` but no code assigns them. Gemini `usage_metadata` is only read in `tier2_runner.py` for a cost tracker, never captured in the main ADK turn path.
- **Expected state:** After each Gemini `generate()` call in `adk_turn_processor.py`, capture `response.usage_metadata.prompt_token_count` and `candidates_token_count`; store on `TurnTimings` and/or `_last_prompt_tokens_out`.
- **Risk if left:** Token count columns always NULL. Cost computation (FINDING-005) cannot work even if wired, since `calc_turn_cost_eur` depends on token counts.
- **Suggested fix:** In `adk_turn_processor.py` after each `generate()` call, read `response.usage_metadata` (if present) and assign to `self._last_prompt_tokens_out` and `state._turn_timings.prompt_tokens_out`.

---

### [FINDING-009] tools/sms_service.py broken — same dead imports as FINDING-001

- **Severity:** critical
- **Phase reference:** Phase 9 B3 — Circuit breaker migration
- **File(s):** `/home/charles2/sailly-browser-demo/tools/sms_service.py`
- **Line(s):** 151: `from server.core.resilience import call_external, SMS_BREAKER, CircuitBreakerOpenError`; 158: `response = await call_external(`
- **Current state:** Imports `call_external` and `CircuitBreakerOpenError` which do not exist in `server.core.resilience`. `SMS_BREAKER` does exist. This file is called by the legacy `_send_sms` path in `tools/executor.py`.
- **Expected state:** SMS sending uses `await with_breaker(SMS_BREAKER, _send_sms_coro(...))` directly.
- **Risk if left:** Every SMS confirmation for create_order and create_reservation raises `ImportError`. Users never receive any SMS confirmations regardless of order success.
- **Suggested fix:** Remove dead imports; adopt `with_breaker(SMS_BREAKER, coro)` pattern from `server.core.resilience`.

---

### [FINDING-010] TurnTimings.record_tool() never called; tool_durations always empty

- **Severity:** critical
- **Phase reference:** Phase 9 A1 — Per-tool latency observability
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/contracts/turn_timings.py`
  - `/home/charles2/sailly-browser-demo/tools/executor.py`
- **Line(s):** turn_timings.py defines `record_tool(name, start, end)`; zero call sites in `server/` or `tools/`
- **Current state:** `TurnTimings.record_tool(name, start, end)` is defined to populate the `tool_durations` dict (used for per-tool latency tracking). No code calls `record_tool`. `tool_durations` is always `{}` in every turn row.
- **Expected state:** `record_tool` called wrapping each tool execution in `tools/executor.py`'s `execute_tool`.
- **Risk if left:** `tool_durations` column always NULL/empty. Per-tool latency analysis in the Phase 9 engineer dashboard never works. Slow tool regressions are undetectable.
- **Suggested fix:** In `execute_tool`, record `start = time.monotonic()` before `handle()` and call `state._turn_timings.record_tool(tool_name, start, time.monotonic())` after.

---

### [FINDING-011] GATED_TOOLS is empty; tool slot-validation gate disabled

- **Severity:** high
- **Phase reference:** Phase 6 — Tool gating / Phase 5.5 left it empty
- **File(s):** `/home/charles2/sailly-browser-demo/tools/dispatcher.py`
- **Line(s):** 8, 11, 67–68 (`GATED_TOOLS = {}`)
- **Current state:** `GATED_TOOLS = {}` with only commented-out example entries. The docstring acknowledges Phase 5.5 ships it empty "so nothing is blocked yet" — but Phase 6 was supposed to populate it with required fields per tool.
- **Expected state:**
  ```python
  GATED_TOOLS = {
      "create_order":       {"phone", "items"},
      "create_reservation": {"phone", "party_size", "name", "date", "time"},
      "verify_address":     {"address"},
      "send_sms":           {"phone"},
  }
  ```
- **Risk if left:** `create_order` and `create_reservation` fire without required slots validated. Real orders placed without caller name or phone; reservations without party_size. Data quality failure on every incomplete-info call.
- **Suggested fix:** Populate `GATED_TOOLS` in `tools/dispatcher.py` with the required fields per Phase 6 plan; test that an order without a phone number is blocked.

---

### [FINDING-012] Six tool handler files missing entirely

- **Severity:** high
- **Phase reference:** Phase 6 — Per-tool handlers
- **File(s):** `server/tools/handlers/` directory
- **Line(s):** N/A — files absent
- **Current state:** `modify_order.py`, `cancel_order.py`, `order_status.py`, `modify_reservation.py`, `cancel_reservation.py`, `capture_catering_lead.py` do not exist. The `__init__.py` registers only 10 handlers. If any of these tools are dispatched, `execute_tool` falls through to legacy inline code in `executor.py` — which has the broken `call_external` imports (FINDING-001).
- **Expected state:** All 15 planned tool handler files present with `async def handle(args: dict, ctx: ToolContext) -> ToolResult` signatures.
- **Risk if left:** Modify/cancel/status flows silently fail or raise `ImportError` at runtime via the broken legacy fallback.
- **Suggested fix:** Create the six missing handler stubs with proper signatures that delegate to working executor functions; register each in `server/tools/handlers/__init__.py`.

---

### [FINDING-013] Existing handlers delegate critical I/O to legacy executor which has broken imports

- **Severity:** high
- **Phase reference:** Phase 3 / Phase 6 — Handler migration
- **File(s):**
  - `server/tools/handlers/create_order.py` line ~150
  - `server/tools/handlers/create_reservation.py` lines ~117, 153
  - `server/tools/handlers/transfer_to_human.py` line ~44
  - `server/tools/handlers/get_menu.py` line ~49
  - `server/tools/handlers/get_date_info.py` lines ~35, 55
  - `server/tools/handlers/end_call.py` line ~45
- **Line(s):** Each handler imports `_create_order`, `_create_reservation`, `_transfer_to_human`, `_get_menu`, `_get_date_info`, `_end_call` from `tools.executor`
- **Current state:** These handlers delegate their DB writes and external calls to functions in `tools/executor.py` that internally use `call_external` (FINDING-001). The `call_external` import is function-level (not top-level), so it doesn't fail on module load — it only fails when the function containing the import is actually invoked.
- **Expected state:** Handlers should own their I/O directly, with proper circuit-breaker wrapping, not delegate through the broken legacy executor.
- **Risk if left:** DB writes and SMS sends in order/reservation success paths raise `ImportError` at runtime on the first call to those executor functions.
- **Suggested fix:** After FINDING-001 is resolved (executor's `call_external` removed), these handlers will function. Long-term: inline the I/O directly in each handler with proper `with_breaker` usage.

---

### [FINDING-014] TurnContext lives in wrong module; expected path is a missing file

- **Severity:** high
- **Phase reference:** Phase 4 — TurnContext contract
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/tts_conditioning.py` line 361 (actual location)
  - `/home/charles2/sailly-browser-demo/server/brain/contracts/turn_context.py` (does not exist)
- **Line(s):** tts_conditioning.py:361 `class TurnContext`
- **Current state:** `TurnContext` is defined in `server/brain/tts_conditioning.py`. The Phase 4 plan and audit check expected it at `server/brain/contracts/turn_context.py`. Any import of `from server.brain.contracts.turn_context import TurnContext` raises `ModuleNotFoundError`.
- **Expected state:** Either a `turn_context.py` re-export shim at `server/brain/contracts/`, or all import sites use the `tts_conditioning` path consistently.
- **Risk if left:** Any new code written per the phase plan's documented import path breaks on first execution.
- **Suggested fix:** Create `server/brain/contracts/turn_context.py` containing `from server.brain.tts_conditioning import TurnContext; __all__ = ["TurnContext"]`.

---

### [FINDING-015] Callback queue is in-memory only; DB table unused by Python code

- **Severity:** high
- **Phase reference:** Phase 8 B7 — Callback fallback on failed transfer
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/tools/handlers/transfer_to_human.py` lines ~124–165
  - `/home/charles2/sailly-browser-demo/migrations/0002_full_observability_schema.sql`
- **Line(s):** transfer_to_human.py:~130 `_CALLBACK_QUEUE: list = []`; no SQL INSERT anywhere in Python
- **Current state:** Failed transfers append to `_CALLBACK_QUEUE` — an in-process Python list. The `callback_queue` Postgres table created by the Phase 9 migration is never written to from Python. Comments in the handler say "Phase 9 may move to Postgres/Cloud Tasks."
- **Expected state:** Failed transfers INSERT a row into `callback_queue` so pending callbacks survive server restarts and operators can see them in the dashboard.
- **Risk if left:** Any callbacks scheduled during a server restart are silently lost. Operators have no DB-backed visibility into missed transfers. The operator dashboard query for `callback_queue` always returns 0 rows.
- **Suggested fix:** Replace `_CALLBACK_QUEUE.append(...)` in `_schedule_callback` with an async `INSERT INTO callback_queue(call_sid, phone, name, context_summary, scheduled_for, status) VALUES (...)`.

---

### [FINDING-016] Two conflicting ValidationRegistry classes coexist

- **Severity:** high
- **Phase reference:** Phase 5.5 — ValidationRegistry
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/adk_turn_processor.py` lines ~42, ~223
  - `/home/charles2/sailly-browser-demo/server/brain/layer1/validation/registry.py`
  - `/home/charles2/sailly-browser-demo/server/brain/validation_registry.py` (implied by import path)
- **Line(s):** adk_turn_processor.py:42 `from server.brain.validation_registry import ValidationRegistry`; turn_runner.py uses `server.brain.layer1.validation.registry.ValidationRegistry`
- **Current state:** `adk_turn_processor.py` imports from `server.brain.validation_registry` (old path) and constructs `self.validation_registry` at ~line 223. `turn_runner.py` separately uses `server.brain.layer1.validation.registry.ValidationRegistry` with `register_default_validators`. These may be two different classes or diverged copies; rules registered in one are invisible to the other.
- **Expected state:** Single canonical `ValidationRegistry` at `server/brain/layer1/validation/registry.py`; all code imports from this path.
- **Risk if left:** Validation rules registered via `register_default_validators` may not be enforced in the main ADK turn path. Slot validation silently skipped for some or all turns.
- **Suggested fix:** Audit both modules for divergence; consolidate to the Phase 5.5 canonical location; delete `server/brain/validation_registry.py` if it's stale; update the import in `adk_turn_processor.py`.

---

### [FINDING-017] get_secret() defined but never called outside its own module

- **Severity:** high
- **Phase reference:** Phase 9 C1 — Google Secret Manager migration
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/configs/secrets.py` line 54
  - `/home/charles2/sailly-browser-demo/server/main.py` (~16 `os.environ.get` / `os.getenv` calls)
  - `/home/charles2/sailly-browser-demo/server/brain/health.py` lines 88, 105
  - `/home/charles2/sailly-browser-demo/server/brain/observability/alerts.py` line 28
- **Line(s):** secrets.py:54 (`def get_secret`); zero call sites in application code
- **Current state:** `get_secret()` is defined in `server/configs/secrets.py` with Google Secret Manager support and dev env-var fallback. It is called by zero production files. `main.py` reads `DEEPGRAM_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `GEMINI_REGION`, `REDIS_URL`, and others directly via `os.environ.get()`. `health.py` reads `GEMINI_API_KEY` and `DEEPGRAM_API_KEY` the same way. `alerts.py` reads `SLACK_ALERTS_WEBHOOK` directly.
- **Expected state:** Per Phase 9 C1, all API key reads go through `get_secret()` which uses Secret Manager in prod and env-var fallback in dev.
- **Risk if left:** Phase 9 C1 entirely un-deployed. Secret rotation via Google Secret Manager impossible. Direct env-var reads are the entire production secret surface.
- **Suggested fix:** Migrate at minimum `DEEPGRAM_API_KEY`, `GOOGLE_MAPS_API_KEY`, and `SLACK_ALERTS_WEBHOOK` reads in `main.py`, `health.py`, and `alerts.py` to `get_secret()`.

---

### [FINDING-018] scripts/verify_no_hardcoded_tenants.py missing — CI guard never created

- **Severity:** high
- **Phase reference:** Phase 5 D — CI tenant content guard
- **File(s):** `/home/charles2/sailly-browser-demo/scripts/` (directory)
- **Line(s):** N/A — file absent
- **Current state:** The file does not exist. The CI guard that prevents DOBOO content from leaking into brain/tool code was never created per the Phase 5 D plan.
- **Expected state:** Script exists, is executable, and is called in the GitHub Actions workflow on every push.
- **Risk if left:** No automated check prevents future tenant content leakage. FINDING-019 documents 20+ existing violations that this guard should have caught.
- **Suggested fix:** Create `scripts/verify_no_hardcoded_tenants.py`; wire into `.github/workflows/deploy.yml` as a lint step before build.

---

### [FINDING-019] DOBOO/dish names hardcoded in 20+ production brain/tool files

- **Severity:** high
- **Phase reference:** Phase 5 D — Tenant content isolation
- **File(s):**
  - `server/brain/layer1/nodes/menu_browse.py` lines 15–17
  - `server/brain/layer1/nodes/ordering.py` lines 11, 30
  - `server/brain/layer1/nodes/greeting.py` line 11
  - `server/brain/layer1/nodes/_prompts.py` lines 10–75
  - `server/brain/layer1/nodes/goodbye.py` lines 11–12
  - `server/brain/layer1/nodes/faq.py` line 11
  - `server/brain/layer1/nodes/escalation.py` line 11
  - `server/brain/layer1/nodes/reservation.py` line 12
  - `server/brain/layer1/nodes/pre_order_confirm.py` line 11
  - `server/brain/conversation_nodes.py` lines 76, 116
  - `server/brain/layer2/system_prompt.py` lines 53, 55, 69
  - `server/brain/layer3/blacklist.py` line 21
  - `server/brain/tts/caller_mirrors.py` line 14
  - `server/brain/tts/situation_styles.py` line 16
  - `server/brain/tts/pronunciation.py` lines 5–6, 29, 32–33
  - `server/brain/tts_conditioning.py` line 30
  - `server/brain/slot_extractor.py` lines 85, 117
  - `server/brain/captured_intents.py` line 42
  - `server/brain/conversation_state.py` lines 482, 519, 664, 761, and 5 others
  - `server/tools/handlers/create_order.py` line 45
- **Line(s):** See above — 20+ files, 50+ instances
- **Current state:** Dish names (Bibimbap, Bulgogi, Mochi-Eis, Japchae), restaurant name (DOBOO), and address details appear inline in node prompts, slot extractor examples, TTS conditioning, and system prompt. These affect live LLM behavior.
- **Expected state:** All tenant-specific content read from `TenantConfig` / YAML at runtime; brain code is tenant-agnostic.
- **Risk if left:** Bot says "DOBOO" and lists DOBOO dishes for any tenant whose config doesn't override these strings. Second-tenant onboarding is impossible without a broad patch.
- **Suggested fix:** Replace hardcoded strings in node prompt templates with `ctx.tenant.restaurant_name`, `ctx.tenant.menu_items`, etc.; node prompts become templates rendered with TenantConfig at call time.

---

### [FINDING-020] Duplicate `language` key in doboo.yaml — one value silently dropped

- **Severity:** high
- **Phase reference:** Phase 5 D — Tenant config
- **File(s):** `/home/charles2/sailly-browser-demo/configs/tenants/doboo.yaml`
- **Line(s):** two `language:` keys — one `language: German` (top level) and one `language: de` (near/inside `tts:` block)
- **Current state:** `language: German` appears at top level early in the file; `language: de` appears again near the TTS section. YAML parsers silently use the last occurrence; the earlier value is discarded. `TenantConfig.language` may receive `"de"` or `"German"` depending on parser and section position.
- **Expected state:** Single `language: de` (ISO-639-1 code) at top level; a separate `tts.language_code: de-DE` if a locale-specific TTS value is needed.
- **Risk if left:** `TenantConfig.language` is non-deterministic. STT language hint and LLM language instruction may be inconsistent.
- **Suggested fix:** Remove the duplicate; keep `language: de` at top level; add `tts.language_code: de-DE` as a distinct TTS-specific field.

---

### [FINDING-021] _is_stuck_loop (legacy exact-match) still present in adk_turn_processor.py

- **Severity:** medium
- **Phase reference:** Phase 4 D — Jaccard stuck-loop replacement
- **File(s):** `/home/charles2/sailly-browser-demo/server/brain/adk_turn_processor.py`
- **Line(s):** ~86–99 (`_is_stuck_loop` definition); ~711–722 (`_check_stuck_loop` fallback to it)
- **Current state:** Legacy `_is_stuck_loop` (exact string match) is still defined and used as a fallback inside `_check_stuck_loop` — which tries the Phase 4 Jaccard `turn_control.is_stuck_loop` first, then falls back to exact-match if Jaccard fails or is unavailable.
- **Expected state:** Only the Jaccard version from `server/brain/layer1/turn_control.py`; legacy removed entirely.
- **Risk if left:** Dead weight; dual detection can trigger inconsistently. The fallback path means the stricter exact-match detector runs when Jaccard is unavailable (e.g. import failure), producing false negatives.
- **Suggested fix:** Remove `_is_stuck_loop` from `adk_turn_processor.py`; remove the fallback branch in `_check_stuck_loop`; let the function raise if `turn_control` import fails so the error is visible.

---

### [FINDING-022] Forced-commit rules: only negation.py exists (14 of 15 planned rules missing)

- **Severity:** medium
- **Phase reference:** Phase 3 Stream 2 / Phase 4 C — Forced commits
- **File(s):** `/home/charles2/sailly-browser-demo/server/brain/layer1/forced_commits/rules/`
- **Line(s):** `rules/__init__.py` exports only `negation.py`'s rules
- **Current state:** `rules/__init__.py` exports `ALL_RULES` from `negation.py` only. No `quantity_ceiling.py`, `address_required_for_delivery.py`, `phone_required.py`, `menu_question.py`, `goodbye_after_completion.py`, `multi_intent_skip.py`, `stall_path.py`, or the other 9 planned rule files exist.
- **Expected state:** 15 rule files covering all Phase 3/4 forced-commit scenarios, each with a unit test.
- **Risk if left:** Most forced-commit scenarios are handled by the inline ~800-line T2 block in `adk_turn_processor.py`. That code works but is untestable as rule units and tightly coupled to the main turn processor.
- **Suggested fix:** Migrate each T2 forced-commit pattern from `adk_turn_processor.py` into its own rule file in `rules/`; register each in `__init__.py`; add unit tests.

---

### [FINDING-023] 203+ f-string log lines in hot paths; logger.bind used once (in logging_config.py itself)

- **Severity:** medium
- **Phase reference:** Phase 9 B2 — Structured logging
- **File(s):**
  - `server/brain/adk_turn_processor.py` (~59 f-string log lines)
  - `server/brain/node_manager.py` (~59 f-string log lines)
  - `server/brain/conversation_state.py` (~14 f-string log lines)
  - `server/brain/tier2_runner.py` (~14 f-string log lines)
  - Plus 8+ other brain files
- **Line(s):** Approximately 203 total f-string log lines across `server/brain/`
- **Current state:** Virtually all logging in hot paths uses `logger.info(f"...")`. `logger.bind(...)` appears exactly once — inside `logging_config.py` itself. Phase 9 B2 introduced `configure_logging()` for structured JSON output but did not migrate any existing log lines.
- **Expected state:** Hot-path logs use `logger.bind(call_sid=..., turn_idx=...).info("event_name")` with structured key-value extras for machine-parseable JSON in production.
- **Risk if left:** Log aggregation and alerting in production relies on string regex; `call_sid` and `turn_idx` cannot be indexed or queried as fields.
- **Suggested fix:** Incrementally migrate the ~40 highest-value log lines in `adk_turn_processor.py` to `logger.bind` form; establish the pattern before addressing remaining files.

---

### [FINDING-024] conversation_nodes_pre_phase3.py — stale backup file with 20+ DOBOO references in production tree

- **Severity:** medium
- **Phase reference:** Phase 3 — Node migration
- **File(s):** `/home/charles2/sailly-browser-demo/server/brain/conversation_nodes_pre_phase3.py`
- **Line(s):** Lines 32, 38, 42, 44, 99, 129, 157–159, 180, 199, 275, 317, 348, 377, 400–401, 588, 607, 719, 722, 729, 750 (and more)
- **Current state:** File contains 20+ DOBOO/dish-name references, full hardcoded dish lists, and legacy pre-Phase-3 node definitions. Exists alongside the live `conversation_nodes.py`.
- **Expected state:** Deleted or archived outside the production source tree.
- **Risk if left:** A stray import of this file would regress to pre-Phase-3 behavior. IDEs/linters may surface symbols from it. Inflates the test for FINDING-019 (hardcoded content).
- **Suggested fix:** Delete the file; if it must be preserved for reference, move to `docs/legacy/conversation_nodes_pre_phase3.py`.

---

### [FINDING-025] Backup files (*.bak, *_backup_*, *.deploy_bak) accumulating in server/brain/

- **Severity:** medium
- **Phase reference:** All phases — general hygiene / rolling deploy
- **File(s):** `server/brain/_backup_*`, `server/brain/*.deploy_bak`, `server/brain/*.bak`
- **Line(s):** N/A — directories/files
- **Current state:** Multiple backup copies of `adk_turn_processor`, `tier2_runner`, `conversation_nodes`, etc. created by rolling deploys remain in the tree.
- **Expected state:** Backup copies in `.gitignore`d staging directories or managed exclusively by the deploy script; never committed to the repo.
- **Risk if left:** IDEs and linters may index backup files; duplicate symbol definitions produce false positives in grep/audit searches (every future audit run will need to exclude them explicitly).
- **Suggested fix:** Add `*.bak`, `*.deploy_bak`, `_backup_*/` to `.gitignore`; delete existing backup copies from the repo.

---

### [FINDING-026] update_state tool still wired as active handler despite Phase 6 deprecation

- **Severity:** medium
- **Phase reference:** Phase 6 — update_state deprecation
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/tools/handlers/__init__.py`
  - `/home/charles2/sailly-browser-demo/tools/definitions.py`
  - `/home/charles2/sailly-browser-demo/tools/executor.py`
- **Line(s):** `__init__.py` registers `update_state` in `ALL_HANDLERS`; `definitions.py` lists it as an active tool definition
- **Current state:** `update_state` registered in `ALL_HANDLERS`, listed in tool definitions, and has a full executor implementation (`_update_state`). Phase 6 marked it deprecated; `server/tools/handlers/update_state.py` is a no-op/warning handler but the tool is still presented to the LLM.
- **Expected state:** Removed from `tools/definitions.py` so the LLM cannot see or call it; deprecated handler kept in place for graceful degradation.
- **Risk if left:** LLM may continue calling `update_state` wasting tokens and potentially conflicting with the Phase 5.5 `ValidationRegistry` slot-management path.
- **Suggested fix:** Remove `update_state` from `tools/definitions.py`; keep the no-op handler for a deprecation grace period.

---

### [FINDING-027] TenantConfig Pydantic model missing typed fields for key YAML sections

- **Severity:** medium
- **Phase reference:** Phase 5 D — Tenant schema
- **File(s):** `/home/charles2/sailly-browser-demo/server/core/tenant_config.py`
- **Line(s):** Class declaration — missing fields for `pre_order`, `menu_version`, `hallucination_blacklist`, top-level `tts`, `delivery`, `faqs`
- **Current state:** `TenantConfig` Pydantic model declares tenant_id, voice, model, tools, locale, language, audio, restaurant_name, location, opening_hours, etc. — but does not declare `pre_order`, `menu_version`, `hallucination_blacklist`, top-level `tts` block, `delivery`, or `faqs` as typed fields. Pydantic's default extra policy silently discards or ignores these keys.
- **Expected state:** All YAML keys consumed by brain/tool code declared as typed fields on `TenantConfig` with appropriate types and defaults.
- **Risk if left:** Any code reading `tenant.hallucination_blacklist` or `tenant.delivery.zone_polygon` raises `AttributeError`. Tenant-level blacklist from Phase 8 A4 is unreachable.
- **Suggested fix:** Add the missing fields to `TenantConfig`; add `model_config = ConfigDict(extra="ignore")` explicitly so future unknown keys are dropped cleanly rather than causing parse errors.

---

### [FINDING-028] server/tools/dispatcher.py missing; GATED_TOOLS lives in legacy tools/ path

- **Severity:** medium
- **Phase reference:** Phase 5.5 — Validation dispatcher
- **File(s):**
  - `/home/charles2/sailly-browser-demo/tools/dispatcher.py` (exists — old location)
  - `/home/charles2/sailly-browser-demo/server/tools/dispatcher.py` (does not exist — expected location)
- **Line(s):** N/A — file absent at expected path
- **Current state:** `GATED_TOOLS` and `dispatch_with_validation` live in `tools/dispatcher.py` alongside the monolithic `executor.py`. `server/tools/dispatcher.py` (the Phase 5.5 canonical path under `server/`) does not exist. Docs and phase plans reference the `server/` path.
- **Expected state:** `server/tools/dispatcher.py` as the post-refactor canonical location; `tools/dispatcher.py` deprecated.
- **Risk if left:** New code following phase plan conventions looks in the wrong place; the validation dispatcher stays entangled with the legacy executor path.
- **Suggested fix:** Move `tools/dispatcher.py` to `server/tools/dispatcher.py`; update all imports; deprecate the old path.

---

### [FINDING-029] sla_monitor.py used `ts` column instead of `created_at` — fixed Apr 25 2026

- **Severity:** medium (already fixed)
- **Phase reference:** Phase 9 A4 — SLA monitoring
- **File(s):** `/home/charles2/sailly-browser-demo/server/brain/observability/sla_monitor.py`
- **Line(s):** Previously lines 72, 91, 99, 120, 123, 127, 131 (now `created_at` after fix)
- **Current state:** Fixed in the Apr 25 session — all queries now use `created_at` to match the actual `google_turn_metrics` column name.
- **Expected state:** `WHERE created_at > now() - interval '5 minutes'`
- **Risk if left:** Was causing periodic `asyncpg.exceptions.UndefinedColumnError` in the background SLA monitor task; all SLA alerts would silently fail.
- **Suggested fix:** Already applied. Documented here for completeness.

---

### [FINDING-030] DOBOO hardcoded in TenantConfig Python class default values

- **Severity:** low
- **Phase reference:** Phase 5 D — Tenant content isolation
- **File(s):** `/home/charles2/sailly-browser-demo/server/core/tenant_config.py`
- **Line(s):** Default string values for `greeting_line` and/or `farewell_text` field defaults
- **Current state:** Default values for fields like `greeting_line` and `farewell_text` in the `TenantConfig` Python class reference "DOBOO" as fallback text when the YAML doesn't provide an override.
- **Expected state:** Defaults should be empty strings `""` or generic placeholders like `"Hallo!"` so they work for any tenant.
- **Risk if left:** Any tenant that omits `greeting_line` from their YAML gets "DOBOO" spoken in their greeting. Low probability now (only one tenant), high impact when second tenant onboards.
- **Suggested fix:** Replace DOBOO-specific default strings with generic placeholders or `""`.

---

### [FINDING-031] health.py router not mounted via include_router; liveness() function dead

- **Severity:** low
- **Phase reference:** Phase 9 B5 — Health endpoints
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/main.py` lines ~1127–1138
  - `/home/charles2/sailly-browser-demo/server/brain/health.py`
- **Line(s):** main.py:1127 (own `@app.get("/health")`); health.py:21 (`router = APIRouter()`); health.py `liveness()` function never called
- **Current state:** `main.py` defines its own `@app.get("/health")` returning `{"status":"ok","service":"sailly-browser-demo"}`. The `router` object from `health.py` is never `include_router`'d. Only `readiness` is imported and re-exposed as `/ready`. The `liveness()` function in `health.py` is dead code.
- **Expected state:** `app.include_router(health_router)` mounting both `/health` and `/ready` from the canonical `health.py` module.
- **Risk if left:** Low — both endpoints work functionally. But changes to `health.py`'s liveness logic have no effect on the live `/health` response.
- **Suggested fix:** Remove the inline `/health` handler from `main.py`; add `app.include_router(health_router)` so `health.py` is the single source of truth.

---

### [FINDING-032] configs/rate_limit_overrides.txt file missing

- **Severity:** low
- **Phase reference:** Phase 9 B4 — Rate limiter override list
- **File(s):** `/home/charles2/sailly-browser-demo/configs/rate_limit_overrides.txt`
- **Line(s):** N/A — file absent; `rate_limit.py` line 27 references `Path("configs/rate_limit_overrides.txt")`
- **Current state:** `rate_limit.py` reads override phone numbers from `configs/rate_limit_overrides.txt`. File does not exist. `load_overrides()` handles missing file gracefully (logs and returns). Rate limiting IS correctly wired for the `/voice` Twilio webhook in `main.py`.
- **Expected state:** File exists (even if empty) so the override mechanism is clearly operational; override phones can be added without a code deploy.
- **Risk if left:** No runtime impact (graceful fallback). Operator confusion when attempting to add bypass numbers — the file path is in code but there's no file to edit.
- **Suggested fix:** Create `configs/rate_limit_overrides.txt` with a comment header explaining the format; add it to the repo.

---

### [FINDING-033] DOBOO dish examples in docstrings of slot_extractor.py and system_prompt.py

- **Severity:** low
- **Phase reference:** Phase 5 D — Tenant content isolation
- **File(s):**
  - `/home/charles2/sailly-browser-demo/server/brain/slot_extractor.py` lines 85, 117
  - `/home/charles2/sailly-browser-demo/server/brain/layer2/system_prompt.py` lines 53, 55, 69
- **Line(s):** Docstring/comment positions only
- **Current state:** "Bibimbap" and "Bulgogi" appear in docstring examples in `slot_extractor.py` and `system_prompt.py`. These are documentation strings, not in LLM prompts or runtime logic (unlike FINDING-019).
- **Expected state:** Docstring examples use generic food names (e.g. "Pizza margherita") to avoid DOBOO-specificity in multi-tenant code.
- **Risk if left:** Low — docstrings only. Could mislead future developers into treating DOBOO-specific concepts as framework-level constraints.
- **Suggested fix:** Replace with generic menu item examples in docstrings; no runtime change needed.

---

## Recommended Fix Order

### Tier 1 — Immediate / Critical (one PR each, with regression test)

1. **FINDING-001 + FINDING-009** — Remove `call_external`/`POS_BREAKER`/`CircuitBreakerOpenError` from `tools/executor.py` and `tools/sms_service.py`; adopt `with_breaker(BREAKER, coro)` function form. Unblocks SMS and address validation.
2. **FINDING-002** — Fix `@MAPS_BREAKER.with_breaker` in `verify_address.py` to use `await with_breaker(MAPS_BREAKER, coro)`.
3. **FINDING-003** — Wire `policy.check()` into `adk_turn_processor.py` post-LLM response path.
4. **FINDING-004** — Call `write_audit_entry()` from `execute_tool` for tools in `AUDITED_TOOLS`.
5. **FINDING-005 + FINDING-006 + FINDING-008** — Wire `build_turn_metrics_extra`, collect `error_codes` array, capture `usage_metadata` token counts into the `brain_service.py` INSERT. (Three related write-path gaps, one PR.)
6. **FINDING-007 + FINDING-010** — Stamp `tts_first_byte_at` in TTS callback; call `record_tool` around each tool execution.

### Tier 2 — Near-term / High (one PR each)

7. **FINDING-011** — Populate `GATED_TOOLS` in `tools/dispatcher.py`.
8. **FINDING-012** — Create the six missing handler stubs.
9. **FINDING-014** — Create `server/brain/contracts/turn_context.py` re-export shim.
10. **FINDING-015** — Replace `_CALLBACK_QUEUE` with DB INSERT in `transfer_to_human.py`.
11. **FINDING-016** — Consolidate to single `ValidationRegistry`; delete stale copy.
12. **FINDING-017** — Migrate key secret reads in `main.py`, `health.py`, `alerts.py` to `get_secret()`.
13. **FINDING-018** — Create `scripts/verify_no_hardcoded_tenants.py`; wire into CI.
14. **FINDING-019** — Replace hardcoded DOBOO strings in node prompts with TenantConfig-driven templates.
15. **FINDING-020** — Fix duplicate `language` key in `doboo.yaml`.

### Tier 3 — Cleanup / Medium (batch into 2–3 PRs)

16. FINDING-021 — Remove legacy `_is_stuck_loop`.
17. FINDING-022 — Create forced-commit rule stubs; migrate patterns from T2 block.
18. FINDING-023 — Migrate top-40 f-string log lines to `logger.bind` form.
19. FINDING-024 + FINDING-025 — Delete stale backup files; add to `.gitignore`.
20. FINDING-026 — Remove `update_state` from tool definitions.
21. FINDING-027 — Add missing typed fields to `TenantConfig`.
22. FINDING-028 — Move `tools/dispatcher.py` to `server/tools/dispatcher.py`.

### Tier 4 — Low (batch into one housekeeping PR)

23. FINDING-030 — Replace DOBOO defaults in `TenantConfig`.
24. FINDING-031 — Mount `health_router` in `main.py`.
25. FINDING-032 — Create `configs/rate_limit_overrides.txt`.
26. FINDING-033 — Replace docstring DOBOO examples.
