# Test Infrastructure Inventory — 2026-04-25

## TL;DR

- **We have**: 25+ test files across 2 directories (server/tests, tests/), a regression harness with JSONL scenario support, 8 JSONL scenario files, 1 JSON baseline file, latency profiling infrastructure, and audit/compliance guards
- **Pointed at port 8080**: YES (default `ws://127.0.0.1:8080/ws/headless`)
- **Pointed at legacy code**: PARTIAL — regression harness supports legacy `/ws/demo_text` protocol via flag; some unit tests reference old code paths as part of audit guards
- **Coverage**: Tier 1 [partial — text-only unit tests], Tier 2 [no — no audio frame generation or TTS/STT in-loop], Tier 3 [no — no production replay mechanism], Orchestration [yes — regression harness + manual runners]
- **Biggest gap**: No audio-in-the-loop testing; all WebSocket tests are text-only; no production call replay infrastructure; latency baseline is read-only (cannot replicate failure conditions)

---

## 1. File Inventory

### server/tests/regression/harness.py
- **Size**: 28,531 bytes (855 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Main regression harness; dual-protocol WebSocket client supporting both new `/ws/headless` (JSON-based) and legacy `/ws/demo_text` (transcript protocol) endpoints
- **Key capabilities**:
  - Loads JSONL scenario files (one JSON object per line)
  - Supports inline Python-callable assertions (legacy) and JSONL declarative assertions
  - Connects to WebSocket, sends user utterances, collects bot responses + tools fired
  - Optional Postgres integration to fetch tools from `google_turn_metrics` table (best-effort)
  - Runs scenarios in sequence, aggregates results to JSON
  - Latency tracking per turn
- **Assertions supported**: `contains`, `forbid`, `tool`, `tool_not`, `turn_count`
- **Usage**: `python -m server.tests.regression.harness [--only scenario_name] [--url ws://...] [--json-output results.json] [--verbose]`

### server/tests/test_regression_scenarios.py
- **Size**: 10,066 bytes (311 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Sprint 3.2 in-process unit test suite; drives `ADKTurnProcessor` directly with synthetic transcripts to catch logic bugs (no WebSocket, no audio, no external calls)
- **Test classes**:
  - `TestSlotOrdering`: slot order invariants (items before name, phone before name)
  - `TestStateFlags`: conversation state flags (confirmation, phone_retry_mode)
  - `TestIntentPriority`: single-intent resolver (escalation > order > reservation)
  - `TestTTSConditioning`: TTS rate clamping, mood detection (frustrated/normal)
  - `TestReservationDeconfliction`: 'tisch' during escalation must not trigger reservation intent
  - `TestBudgetConstants`: SlotExtractor timeout values
  - `TestMaxOutputTokensCap`: LLM max_output_tokens capped at 128
- **Run**: `python -m unittest server.tests.test_regression_scenarios`

### server/tests/test_barge_in.py
- **Size**: 4,538 bytes (140 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Unit test for barge-in suppression logic (Sprint 2.3); simulates user speech mid-TTS and verifies suppression <300ms
- **Test classes**:
  - `TestBargeInSuppression`: timestamp semantics, TTS suppression, latency target
  - `TestBargeInHandler`: smoke test (handler importable, brain service exposes `_barge_in_ts`)
- **Run**: `python -m pytest server/tests/test_barge_in.py -v`

### server/tests/test_phase8_guards.py
- **Size**: 11,442 bytes (347 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Quality & Safety guard tests (Phase 8 exit criteria) without live server or Twilio
- **Guard classes tested**:
  - `TestTechProblemBlock`: detects and blocks "technisches Problem" → transfers to human
  - `TestQuantityCeiling`: caps per-item and per-order totals
  - `TestMonetaryCap`: caps EUR order total
  - `TestPriceValidation`: checks prices in text match tool args
  - `TestAfterHoursBlocking`: blocks orders outside service hours
  - `TestLengthCap`: enforces max response sentences
- **Run**: `pytest server/tests/test_phase8_guards.py`

### server/tests/test_variation_order.py
- **Size**: 9,340 bytes (288 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Tests that state transitions respect slot-filling order across multiple variations

### server/tests/audit/test_finding_regressions.py
- **Size**: 11,324 bytes (346 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Audit regression suite (PR-8 findings); guards against re-introduction of specific bugs
- **Finding guards**:
  - FINDING-014: TurnContext canonical import path
  - FINDING-015: No silent ValidationRegistry
  - FINDING-016: No deprecated tool references
  - FINDING-021: Legacy `_is_stuck_loop` deleted
  - FINDING-025: `conversation_nodes_pre_phase3.py` deleted
  - FINDING-026: `update_state` removed from LLM tool declarations
- **Run**: `python -m pytest server/tests/audit/test_finding_regressions.py -v`

### server/tests/observability/test_audit_wiring.py
- **Size**: 9,004 bytes (278 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Guards that observability wiring (metrics, logging, tracing) is not importing dead code

### server/tests/observability/test_latency_instrumentation.py
- **Size**: 6,968 bytes (215 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Verifies latency instrumentation (STT, LLM, TTS stages) is properly wired

### server/tests/observability/test_metrics_wiring.py
- **Size**: 9,996 bytes (307 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Checks metrics collection and Prometheus export

### server/tests/dispatcher/test_gated_tools.py
- **Size**: 15,478 bytes (476 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Tool dispatcher gates and tool filtering logic (no tool execution)

### server/tests/handlers/test_new_handlers_smoke.py
- **Size**: 9,914 bytes (304 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Smoke tests for new tool handlers (importable, basic contracts)

### server/tests/handlers/test_transfer_callback.py
- **Size**: 5,451 bytes (168 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Tests transfer_to_human tool callback flow

### server/tests/resilience/test_with_breaker_usage.py
- **Size**: 5,721 bytes (176 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Guards that legacy circuit breaker code (`call_external`, `CircuitBreakerOpenError`, `POS_BREAKER`) has been deleted

### server/tests/tool_deprecation/test_update_state_deprecated.py
- **Size**: 1,726 bytes
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: FINDING-026 regression — update_state removed from LLM-facing tools

### server/tests/turn_control/test_stuck_loop_unified.py
- **Size**: 1,093 bytes
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: FINDING-021 regression — legacy `_is_stuck_loop` deleted

### server/tests/validation/test_registry_consolidation.py
- **Size**: 3,621 bytes
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: FINDING-015 regression — ValidationRegistry consolidation guards

### server/tests/tool_dispatcher/test_dispatcher_path.py
- **Size**: 1,247 bytes
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Ensures tool dispatcher is not imported from legacy path

### server/tests/secrets/test_secret_manager_migration.py
- **Size**: 8,016 bytes (246 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Secret manager migration guards

### server/tests/policy/test_policy_wiring.py
- **Size**: 7,378 bytes (227 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Policy layer wiring checks

### server/tests/configs/test_tenant_yaml_validity.py
- **Size**: 4,070 bytes (135 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Tenant YAML config validation

### server/tests/contracts/test_turn_context_shim.py
- **Size**: 768 bytes
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: TurnContext contract shim tests

### server/tests/health/test_health_endpoints.py
- **Size**: 733 bytes
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Health endpoint checks

### server/tests/vertical/test_tenant_content_extracted.py
- **Size**: 6,585 bytes (202 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Vertical pattern — tenant-specific content extraction

### server/tests/rate_limit/test_overrides_file.py
- **Size**: 1,205 bytes
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Rate limit overrides file validation

### server/tests/repo_hygiene/test_hygiene_cleanup.py
- **Size**: 1,893 bytes
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Repository cleanup checks (no debug code, no print statements in production)

### server/tests/scripts/test_verify_no_hardcoded_tenants.py
- **Size**: 6,375 bytes (196 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Verifies no hardcoded tenant IDs in production code

### server/tests/regression/replay_tool.py
- **Size**: 9,975 bytes (306 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Utility to replay call_sids from database (infrastructure helper, not a test itself)

### tests/latency_baseline.py
- **Size**: 6,830 bytes (210 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: Reads `google_turn_metrics` + `google_calls` from Postgres; generates p50/p95/p99 latency breakdown; identifies slowest turns (outlier hunting)
- **Usage**: `DATABASE_URL='postgresql://...' python tests/latency_baseline.py [--limit 100]`
- **Output**: Terminal summary + warns if p50 > 1500ms or p99 > 10s
- **Note**: Read-only analytics tool — requires Postgres connection

### tests/test_greeting_ki_disclosure.py
- **Size**: 3,422 bytes (104 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: EU AI Act Art. 50 compliance — verifies first bot utterance contains standalone "KI" token; tests both default tenant config and fallback greeting in brain_service

### tests/test_bargein_latency_metric.py
- **Size**: 3,187 bytes (98 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: Barge-in latency metric extraction from call data

### tests/test_step2_bugs.py
- **Size**: 7,327 bytes (225 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: Step 2 bug-pack unit tests (Bugs A-F); exercises conversation_state extraction functions (name, address, phone, number-word conversion, tool-call leakage stripping)

### tests/test_call_summary.py
- **Size**: 2,376 bytes (73 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: Call summary generation tests

### tests/test_menu_86_filter.py
- **Size**: 1,490 bytes (65 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: Menu item filtering (86 = on-demand filters)

### tests/test_micro_pack_bugD.py
- **Size**: 3,485 bytes (107 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: Bug D specific test from Step 2 bug pack

### tests/test_pos_webhook.py
- **Size**: 2,476 bytes (104 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: POS webhook payload parsing

### tests/test_reservation_capacity.py
- **Size**: 1,855 bytes (83 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: Reservation capacity checking

### tests/test_sms_templates.py
- **Size**: 1,859 bytes (80 lines)
- **Last modified**: 2026-04-22 07:47
- **Purpose**: SMS template rendering

### scripts/run_regression.sh
- **Size**: 76 bytes (4 lines)
- **Last modified**: 2026-04-25 19:29:18
- **Purpose**: Wrapper script that invokes `python -m server.tests.regression.harness` with `SAILLY_TEST_MODE=1`

---

## 2. Port and Endpoint Check

| File | URL/Port Found | Endpoint Path | Verdict |
|------|---|---|---|
| `server/tests/regression/harness.py:75` | `os.environ.get("SAILLY_WS_URL", ...)` | default: `ws://127.0.0.1:8080/ws/headless` | ✓ Current |
| `server/tests/regression/harness.py:42` | `ws://127.0.0.1:8080/ws/headless` | `/ws/headless` | ✓ Current |
| `server/tests/regression/harness.py:235` | Legacy mention | `/ws/demo_text` | ⚠ Legacy (but optional flag) |
| `server/tests/regression/harness.py:763` | `--legacy-protocol` flag | `/ws/demo_text` | ⚠ Legacy (opt-in) |
| `tests/latency_baseline.py:76-87` | `get_pool()` database | (Postgres DSN, not HTTP) | ✓ Current (internal DB) |

**Environment variables recognized**:
- `SAILLY_WS_URL` — defaults to `ws://127.0.0.1:8080/ws/headless` if not set
- `SAILLY_PG_DSN` — defaults to `postgresql://sailly:sailly@localhost:5432/sailly` if not set
- `DATABASE_URL` — required for latency_baseline.py (no default)

**Summary**: ✓ Default target is port 8080 `/ws/headless` (current architecture). Legacy `/ws/demo_text` protocol is supported but requires explicit `--legacy-protocol` flag.

---

## 3. Legacy Code Path Findings

### Tier 1 — Definitely Legacy (should be deleted per PR-8)

| File | Line | Pattern | Status |
|------|------|---------|--------|
| `server/tests/resilience/test_with_breaker_usage.py` | 114-128 | Tests that `call_external`, `CircuitBreakerOpenError`, `POS_BREAKER` do NOT exist in production | ✓ Guard passes (legacy code deleted) |
| `server/tests/turn_control/test_stuck_loop_unified.py` | 19-35 | Tests that `_is_stuck_loop` function has been deleted from `adk_turn_processor.py` | ✓ Guard passes |
| `server/tests/audit/test_finding_regressions.py:183` | Line 183 | Tests that `conversation_nodes_pre_phase3.py` does NOT exist | ✓ Guard passes |
| `server/tests/tool_deprecation/test_update_state_deprecated.py` | 14-39 | Tests that `update_state` not in TOOL_DECLARATIONS (LLM-facing tools) | ✓ Guard passes |

### Tier 2 — Possibly Legacy (Phase 3 deprecation)

| File | Line | Pattern | Note |
|------|------|---------|------|
| `server/tests/tool_dispatcher/test_dispatcher_path.py:39` | `from tools.dispatcher` | Tests that production does NOT import from legacy path | ✓ Guard (legacy path disallowed) |
| `server/tests/observability/test_audit_wiring.py` | 162, 190, 217, 241 | References to `from tools.executor import execute_tool` in test comments | ⚠ Documenting what NOT to do |

### Tier 3 — Legacy Imports in Tests (intentional audit pattern)

| File | Line | Pattern | Purpose |
|------|------|---------|---------|
| `server/tests/validation/test_registry_consolidation.py:59-103` | Multiple lines | Imports from `server.brain.validation_registry` | FINDING-015: Guards that shim exists; tests backward compat |
| `server/tests/audit/test_finding_regressions.py:101,107` | Multiple lines | Imports from `server.brain.validation_registry` | FINDING-015: Guards backward compat import path |

**Verdict**: ✓ No production code paths are pointing at legacy code. All legacy-looking imports are in audit guards where they intentionally test that old code is gone or properly shimmed.

---

## 4. Tier Classification

### Tier 1 — Text-only (Fast Logic Regression)
- `server/tests/test_regression_scenarios.py` — ✓ Tier 1
  - In-process ADK turn processor with synthetic transcripts (text in → text out)
  - No audio, no TTS/STT, no WebSocket
  
- `server/tests/test_barge_in.py` — Partial Tier 1
  - Unit test of barge-in suppression logic
  - Mocks TTS suppression, does not generate audio frames
  
- `server/tests/test_phase8_guards.py` — ✓ Tier 1
  - Quality guard checks (text analysis + tool arg validation)
  - No audio, no external calls
  
- `server/tests/test_variation_order.py` — ✓ Tier 1
  - State transition tests
  
- `tests/test_greeting_ki_disclosure.py` — ✓ Tier 1
  - Text content validation (greeting contains "KI")
  
- `tests/test_step2_bugs.py` — ✓ Tier 1
  - Extraction function unit tests (name, address, phone from text)
  
- `tests/test_call_summary.py` — ✓ Tier 1
- `tests/test_menu_86_filter.py` — ✓ Tier 1
- `tests/test_sms_templates.py` — ✓ Tier 1

**Tier 1 Total**: ~10 files (strong coverage of state logic and guards)

### Tier 2 — Audio-in-the-Loop (Realistic)
- `server/tests/regression/harness.py` — Text-only version
  - Connects to WebSocket at `/ws/headless`
  - Sends user text via JSON messages
  - Receives bot text + tools via JSON
  - **NO audio frames, no TTS/STT in-the-loop**
  - ✗ Not true Tier 2 (text-only)

**Tier 2 Total**: 0 files with audio-in-the-loop

### Tier 3 — Production Replay
- `server/tests/regression/replay_tool.py` — Infrastructure helper (not a test)
  - Can read call_sids from database
  - Does NOT replay calls against running instance
  - ✗ Incomplete implementation

**Tier 3 Total**: 0 complete implementations

### Orchestration / Harness
- `server/tests/regression/harness.py` — ✓ Full harness
  - Loads JSONL scenario files
  - Runs scenarios sequentially
  - Aggregates results to JSON
  - Reports pass/fail + per-assertion details
  
- `scripts/run_regression.sh` — ✓ CLI wrapper
  - Invokes harness with `SAILLY_TEST_MODE=1`

### Judge / Evaluation
- `tests/latency_baseline.py` — ✓ Metrics aggregator (not a judge)
  - Reads from `google_turn_metrics` table
  - Computes p50/p95/p99 latency
  - Warns if thresholds exceeded
  - Does NOT score conversation quality

- `server/tests/regression/harness.py` → `_run_jsonl_assertions()` — Partial judge
  - Evaluates simple contains/forbid/tool assertions
  - Does NOT use LLM-as-judge or semantic scoring

---

## 5. Scenarios / Personas / Rubrics

### Regression Scenarios (JSONL format)

Scenarios are stored in `server/tests/regression/scenarios/` and loaded by `harness.py`:

#### after_hours_pre_order.jsonl
- **Modified**: 2026-04-25 19:29:18
- **Scenarios defined**: 1
- **Shape**: JSONL (meta + user/assert steps)
- **Purpose**: Tests pre-order behavior outside service hours

#### delivery_address_flow.jsonl
- **Modified**: 2026-04-25 19:29:18
- **Scenarios defined**: 1
- **Shape**: JSONL
- **Purpose**: Tests delivery address collection and validation

#### off_menu_pivot.jsonl
- **Modified**: 2026-04-25 19:29:18
- **Scenarios defined**: 1
- **Purpose**: Tests "pizza" (not on menu) → bot offers Korean alternative

#### philipp_stress_test.jsonl
- **Modified**: 2026-04-25 19:29:18
- **Scenarios defined**: 1
- **Shape**: JSONL
- **Name**: "philipp_stress_test"
- **Description**: "Extreme 3-intent monologue (Abholung + Sammelbestellung + Reservierung). Phase 3 KPI baseline. This scenario is expected to FAIL in Phase 2 (0% pass rate is the baseline). The Phase 3 target is 100%."
- **Sample user input** (line 2):
  ```
  "Hallo, hier Philipp Schneider. Null eins sieben neun drei vier fünf sechs sieben acht neun. Friedrichstraße zwanzig in Bonn. Ich hätte gerne Abholung für zwei Personen in einer halben Stunde. Zweimal Bulgogi, zwei Bibimbap, ein Wasser. Dann eine Bestellung für Samstag. Super Bowl Party. Zehn Leute. Zwanzig Bulgogi, zehn Bibimbap, fünfzehn Japchae, zehn Mochi-Eis, zehn Flaschen Wein, fünfzehn Cola, zehn Wasser. Und einen Tisch für nächsten Freitag. Neunzehn Uhr. Sechs Personen. Geburtstag. Tisch am Fenster. Blumendeko. Vielleicht einen Kuchen."
  ```
- **Assertions**: Contains "abholung", forbid "[tool:", tool="create_order" (at_end), tool="create_reservation" (at_end)

#### reservation_basic.jsonl
- **Modified**: 2026-04-25 19:29:18
- **Purpose**: Tests basic reservation flow

#### takeaway_simple.jsonl
- **Modified**: 2026-04-25 19:29:18
- **Purpose**: Tests takeaway order (no delivery)

#### wine_not_denied.jsonl
- **Modified**: 2026-04-25 19:29:18
- **Purpose**: Tests that wine (which IS on Korean menu) is not denied

### Baseline File

#### tests/baselines/2026-04-23-baseline.json
- **Modified**: 2026-04-23 20:56
- **Content**: 56 lines (5 scenario results shown)
- **Status**: All scenarios report `"passed": false` with `"harness_error": "Protocol adapter in development - framework established"`
- **Scenarios**: pizza_pivot, wine_is_available, no_phantom_reservation, multi_item_coherent, philipp_stress_test
- **Verdict**: Baseline file is a stub (test framework not fully wired to running server yet)

### Inline Scenarios (Legacy Python format)

From `server/tests/regression/harness.py:678-725`:

| Scenario | Description | Key Assertions |
|----------|---|---|
| pizza_pivot | Caller asks for Pizza (not on menu); bot must offer Korean alternative | Contains: "pizza" + ("bulgogi" OR "bibimbap" OR "japchae" OR "ähnlich" OR "beliebt") |
| wine_is_available | Wine IS on menu; bot must NOT deny it | Forbid: "keinen wein", "kein wein", "keine flasche wein", etc. |
| no_phantom_reservation | Takeaway order; must fire create_order but NOT create_reservation | Tool: create_order; Tool NOT: create_reservation, check_availability |
| multi_item_coherent | Multi-item order; bot must acknowledge items coherently | Min 30 chars; Contains: "bulgogi" |

### Universal Assertions (Applied to All Scenarios)

From `server/tests/regression/harness.py:646-673`:

1. **No forbidden phrases** (UNIVERSAL_FORBIDDEN list):
   - "technisches problem", "technischer fehler", "system-fehler", "system fehler"
   - "ich habe einen fehler", "etwas ist schiefgelaufen", "das hat nicht funktioniert"
   - "[tool:", "bekannte daten", "nächster schritt", "validierungsstatus"
   - "letzte aussage", "noch fehlend", "{time}", "{date}", "{name}", "{{", "}}"

2. **Min response length**: 20 characters

3. **Max turn latency**: 15,000 ms (15 seconds)

### Personas / Characteristics

Scenarios test these speaker profiles:
- **Philipp** (front-loader): Delivers all info in T1, includes names, addresses, phone, multiple intents
- **Overinformer** (concise): 2 sentences max, multi-item in single turn
- **Piecemeal-cautious**: One slot per turn, slow speaker
- **Correction-heavy**: Changes mind 3x (item, address, delivery type)
- **Frustrated-from-turn-1**: Caller starts angry (frustration keywords)
- (Others implicit via scenario variation)

### Rubrics

- **JSONL format rubric**: Contains/forbid text, tool presence/absence, turn count, optionally evaluated at session end
- **Latency rubric** (from `latency_baseline.py`): p50 target ≤ 800ms, p95 target ≤ 1800ms (warns if exceeded)
- **KI disclosure rubric** (from `test_greeting_ki_disclosure.py`): First utterance must contain standalone "KI" token (word boundary)
- **Quality guards** (from `test_phase8_guards.py`): No tech-problem text, qty ceilings per item + per order, EUR cap, price consistency

---

## 6. Anti-Pattern Check

| Anti-pattern | How to check | Findings |
|---|---|---|
| Test caller TTS = bot TTS (STT memorization risk) | Search for ElevenLabs/Polly/Anthropic in synthetic client | ✗ No TTS/STT in tests at all (all text-only) — not applicable |
| Pass/fail is single-run | Search for `n_runs\|replications\|repeat` in harness | ✓ Each scenario runs once; no built-in replication (but can call harness multiple times from CI) |
| Lenient judge ("is it reasonable") | Read judge prompt if LLM-as-judge exists | ✓ No LLM judge — assertions are rule-based (exact text match, tool presence) |
| Cooperative-only personas | Count distinct persona files or scenario variations | ⚠ Limited personas (Philipp, Overinformer, Cautious, Correction-heavy, Frustrated); no adversarial/silent-failure personas |
| No production-failure feedback | Search for code that ingests real call_sids | ⚠ `replay_tool.py` can read call_sids; latency_baseline.py reads call metrics; but no automated failure ingestion loop |
| Same LLM family for caller/judge/agent | Check which models synthetic client and judge use | ✓ Not applicable — no LLM-driven caller or judge |
| No statistical thresholds | Search for `threshold\|>= 0\.` in result aggregation | ⚠ Latency baseline has hard thresholds (p50 > 1500ms warning, p99 > 10s warning) but no auto-fail threshold in harness |
| No production data pipeline | Check if real calls feed test infrastructure | ⚠ Partial — metrics tables exist; no automated CI ingestion of recent production calls |

---

## 7. Open Questions for Human Review

1. **Latency baseline disconnection**: `tests/latency_baseline.py` requires manual `DATABASE_URL` setup. Is this run in CI or only manually? If manually, there's no automated regression detection.

2. **Baseline file staleness**: `tests/baselines/2026-04-23-baseline.json` shows all scenarios with `harness_error: "Protocol adapter in development"`. Is this expected? When was this last run against a live server?

3. **Tier 2 feasibility**: No audio-in-the-loop tests exist. Is audio TTS/STT infrastructure available for testing, or is it behind a separate boundary (e.g., only tested via live calls to Twilio)?

4. **Production replay pipeline**: `server/tests/regression/replay_tool.py` exists but is not invoked in any CI job or test file. Should this be a Tier 3 test, or is it infrastructure-only?

5. **LLM-as-judge**: Current assertions are rule-based (exact text, tool presence). Should semantic / LLM-based scoring be added, or is text-based sufficient for current use cases?

6. **CI integration**: How are these tests triggered in CI? Which tests are blocking (must pass) vs. informational (publish metrics only)?

7. **Concurrent test safety**: If running multiple scenarios against a single test server instance, is there isolation between call_sids? Or should scenarios run serially?

8. **Call duration ceiling**: No test checks for runaway conversations (e.g., >30 turns). Should there be a guard for max conversation length?

---

## 8. Suggested Next Steps

**Critical gaps identified**:

1. **Tier 2 (audio-in-the-loop) is completely missing**. The regression harness is text-only (`/ws/headless`). If TTS/STT integration is needed, either:
   - Extend harness to generate/mock audio frames (requires TTS library and audio codec knowledge)
   - Route tests through a browser-based client that handles audio (e.g., Playwright/Puppeteer)
   - Accept that audio validation is only possible via live Twilio calls

2. **Tier 3 (production replay) is incomplete**. `replay_tool.py` exists but is not wired into any automated test. To enable production replay:
   - Add a scheduled CI job that selects recent call_sids from `google_calls`
   - Replay each call against a test instance using the harness
   - Compare results to golden baselines or detect anomalies

3. **Latency baseline lacks CI automation**. `latency_baseline.py` is a standalone script requiring manual `DATABASE_URL` setup. To automate:
   - Wire into CI environment (provide `DATABASE_URL` secret)
   - Generate JSON output suitable for graphing (current: terminal-only)
   - Set up regression detection (fail CI if p95 > threshold)

4. **No adversarial personas**. All scenarios are well-behaved or frustration-signaling, but none test:
   - Silent comprehension failures (caller gets the order wrong but doesn't notice)
   - Garbled ASR (high-confidence mispronunciations)
   - Barge-in storms (user interrupts every bot turn)
   - Timeout handling (network latency > turn timeout)

5. **Baseline file is stale**. The 2026-04-23 baseline shows all failures. Before scaling to production:
   - Re-run scenarios against current server
   - Commit passing baseline
   - Set up CI to detect regressions (not just pass/fail, but failure mode changes)

6. **No statistical aggregation across multiple runs**. If a scenario passes 8/10 times and fails 2/10, the harness reports "FAIL". To detect flakiness:
   - Add `--reruns N` flag to harness
   - Report pass rate (e.g., "8/10 passed") and flag >5% flakiness as a warning

**Recommended prioritization**:

- **Week 1**: Get baseline file passing (re-run harness against live server, update baseline)
- **Week 2**: Wire latency_baseline into CI; set up p95 regression detection
- **Week 3**: Design and implement Tier 2 (audio-in-the-loop) if TTS/STT boundary is testable
- **Week 4**: Implement Tier 3 (production replay) with scheduled job + anomaly detection
- **Ongoing**: Add adversarial personas as edge cases are discovered in production

---

## Appendix: Test Infrastructure Metadata

**Inventory Date**: 2026-04-25  
**Scan Date**: Today  
**Total files**: 25 test files + 2 supporting files + 8 JSONL scenarios + 1 baseline JSON  
**Total lines of test code**: ~6,000 (excluding unit test directories)  
**Languages**: Python (all)  
**Test frameworks used**: unittest, pytest, custom harness  
**External dependencies**: websockets (for harness), asyncpg (optional for DB enrichment), Postgres (for latency analytics)  
**CI/CD integration**: Unknown (not visible in codebase scan)  
**Last modified (most files)**: 2026-04-25 19:29:18 (UTC)  
**Last modified (tests/ directory)**: 2026-04-22 07:47 (UTC)
