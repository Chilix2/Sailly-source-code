# POST-REVERT STATE AUDIT — April 23, 2026

**Audit Timestamp**: 2026-04-23 ~13:00 UTC  
**Scope**: Live deployed code + running service + database schema  
**Git Status**: Neither /home/charles2/sailly-browser-demo nor /home/charles2/sailly-google-fork is a git repository  
**Service Discrepancy**: sailly-voice-agent systemd service points to non-existent /home/charles2/sailly-google-fork. Port 8080 (localhost) is served by /home/charles2/sailly-browser-demo.

---

## 1. MODEL CONFIGURATION

### Grep Results (gemini-* strings in codebase)

**sailly-browser-demo active files:**

| File | Line | Model String |
|------|------|--------------|
| `server/brain/slot_extractor.py` | 69 | `"gemini-2.0-flash"` (default param) |
| `server/brain/adk_turn_processor.py` | 841 | `"gemini-2.0-flash"` (env override) |
| `server/brain/tier2_runner.py` | 68 | `"gemini-2.5-flash"` (main LLM model init) |
| `server/brain/tier2_runner.py` | 70 | `"gemini-flash"` (TTS engine env, defaults to) |
| `server/brain/tier2_runner.py` | 747 | `"gemini-2.5-flash-tts"` (TTS model_name param) |
| `server/brain/tier2_runner.py` | 752 | `"gemini-2.5-pro-tts"` (alternate TTS model) |
| `server/main.py` | 521 | `"gemini-2.5-flash-tts"` (fallback TTS) |

**Directory search results**: Searched `/home/charles2/sailly-google-fork` — directory does not exist.

### Exact Model Configuration

- **Main LLM**: `gemini-2.5-flash` (set in `tier2_runner.py` line 68)
- **SlotExtractor**: `gemini-2.0-flash` (default, `slot_extractor.py` line 69; overridable via `SLOT_EXTRACTOR_MODEL` env var)
- **TTS Model**: `gemini-2.5-flash-tts` (selected based on `TTS_ENGINE` env var; default is `gemini-flash` which maps to `gemini-2.5-flash-tts`)

---

## 2. GENERATION CONFIG

### GenerateContentConfig Streaming (Line 546–551)

```python
config = genai_types.GenerateContentConfig(
    system_instruction=system_prompt,
    temperature=self.temperature,
    max_output_tokens=128,
    stop_sequences=["---", "\n\nBEKANNTE DATEN:", "\n\n==="],
)
```

### GenerateContentConfig Non-Streaming (Line 666–671)

```python
config = genai_types.GenerateContentConfig(
    system_instruction=system_prompt,
    temperature=self.temperature,
    max_output_tokens=128,
    stop_sequences=["---", "\n\nBEKANNTE DATEN:", "\n\n==="],
)
```

### Parameters

| Parameter | Value |
|-----------|-------|
| `max_output_tokens` | **128** |
| `temperature` | **self.temperature** (initialized to 0.0 by default, line 69) |
| `top_p` | **NOT SET** (omitted, uses default) |
| `stop_sequences` | `["---", "\n\nBEKANNTE DATEN:", "\n\n==="]` |
| `thinking_config` | **NOT PRESENT** |

---

## 3. DATABASE SCHEMA

### google_turn_metrics Columns

Checked columns exist: 56 total columns in table.

| Column Name | Exists | Data Type | Nullable |
|-------------|--------|-----------|----------|
| `prompt_tokens_in` | YES | integer | YES |
| `prompt_tokens_out` | YES | integer | YES |
| `slot_state_json` | YES | jsonb | YES |
| `validations_fired_this_turn` | YES | jsonb | YES |
| `leaks_detected` | NO | — | — |
| `raw_utterance_in_prompt` | YES | boolean | YES |
| `tts_situation` | YES | text | YES |
| `tts_mood` | YES | text | YES |
| `tts_rate_pct` | YES | integer | YES |
| `subsystems_fired` | YES | jsonb | YES |
| `response_was_fallback` | NO | — | — |
| `loop_detected_in_stream` | YES | boolean | YES |

### google_calls Columns

| Column Name | Exists | Data Type | Nullable |
|-------------|--------|-----------|----------|
| `call_disposition` | YES | character varying | YES |
| `avg_latency_ms` | YES | integer | YES |
| `total_dead_air_ms` | YES | integer | YES |

### NULL Rates (Last 48 Hours)

**google_turn_metrics (206 rows in last 48h):**

| Column | NULL Rate | Interpretation |
|--------|-----------|-----------------|
| `prompt_tokens_in` | 85.9% | Mostly NULL — token auditing write-path broken |
| `prompt_tokens_out` | 100.0% | Entirely NULL — no output token capture |
| `slot_state_json` | 74.8% | Mostly NULL — slot state not written |
| `validations_fired_this_turn` | 74.8% | Mostly NULL — validation registry silent |
| `raw_utterance_in_prompt` | 74.8% | Mostly NULL — not being populated |
| `tts_situation` | 74.8% | Mostly NULL — TTS situation not captured |
| `tts_mood` | 74.8% | Mostly NULL — mood not captured |
| `tts_rate_pct` | 74.8% | Mostly NULL — rate not captured |
| `subsystems_fired` | 74.8% | Mostly NULL — subsystem logging not working |
| `loop_detected_in_stream` | 100.0% | Entirely NULL — loop detection silent |

**google_calls (72 rows in last 48h):**

| Column | NULL Rate |
|--------|-----------|
| `call_disposition` | 88.9% |
| `avg_latency_ms` | 80.6% |
| `total_dead_air_ms` | 80.6% |

**Pattern**: ~75% of rows have sparse/NULL observability data. Suggests observability instrumentation is not wired to write-path on most code paths.

---

## 4. MEMORY MANAGER PROMPT BUILDER

### build_context() Function (Lines 127–216)

Full signature:
```python
def build_context(
    self,
    node_prompt: str,
    state: ConversationState,
    prereq_results: Optional[List[str]] = None,
) -> str:
```

**Return type**: Single `str` value (not a tuple).

### Blocks Present in Assembled Prompt

| Block Name | Present | Lines | Notes |
|------------|---------|-------|-------|
| `LETZTE AUSSAGE DES ANRUFERS (WÖRTLICH)` | YES | 141–154 | Raw utterance injection |
| `BEKANNTE DATEN` | YES (conditional) | 155–157 | Legacy state format |
| Validation Registry status | YES | 138–152 | Pending/failed validation hints |
| `MITTAGSANGEBOT` | YES | 160–173 | Menu metadata |
| Menu pivot / off-menu detection | NO | — | Not present |
| Compact menu summary | NO | — | Not present |
| NOCH FEHLEND | NO | — | Not present in code |
| NÄCHSTER SCHRITT | NO | — | Not present in code |

### Key Code Sections

**Lines 127–140**: If ValidationRegistry exists, injects pending/failed slot hints.

**Lines 141–154**: Injects raw caller utterance unconditionally if present.

**Lines 155–157**: Legacy fallback; formats state via `_format_state()`.

**Lines 160–173**: Injects menu metadata (lunch availability, current time).

**Lines 175–216**: Context summary, injected items, and token audit warning (~1500+ token threshold).

**Note**: `build_context()` returns a single string (`return built` at line 216). It does NOT return a tuple. Token auditing is logged but not returned for DB persistence.

---

## 5. SANITIZER AND OUTPUT GUARDS

### Search Results

Searched `tier2_runner.py` for:
- `sanitize_bot_output()` — **NOT FOUND**
- `enforce_minimum_response()` — **NOT FOUND**
- `LoopGuardState` — **NOT FOUND**
- `check_sentence_for_loop()` — **NOT FOUND**

### Present Guards

**Tool tag stripping (Line 777):**
```python
clean = _re.sub(r"`?\[TOOL:\w+\]`?", "", text).strip()
```
Located in `_prepare_text_for_tts()` function (line 770–802).

**Partial [TOOL: guard in streaming (Line 597):**
```python
if sent_chunk and "[TOOL:" not in sent_chunk and "[" not in sent_chunk[-5:] and tts_callback:
```
Prevents tool tags from being sent to TTS. Also checks for lone `[` character at end of chunk.

**Short exclamation deferral (Lines 602–608):**
```python
_is_short_exclaim = len(sent_chunk) < 15
if _sent_count == 0 and _is_short_exclaim:
    # ... defer merging with next sentence
```
Prevents short fragments like "Super!" or "Prima!" from being sent as isolated TTS (avoids "super, super" loop).

**Minimum sentence length batching (Line 609):**
```python
elif _sent_count == 0 or len(sent_chunk) >= _MIN_SUBSEQUENT_CHARS:
```
Batches subsequent sentences until they reach 120 chars.

### Summary

| Guard Type | Wired | Location | Notes |
|-----------|-------|----------|-------|
| Sanitizer (generic) | NO | — | No `sanitize_bot_output()` function |
| Minimum response length | PARTIAL | Line 602–608 | Defers short exclamations; no hard minimum |
| Loop detection | NO | — | No `LoopGuardState` or equivalent |
| Tool tag stripping | YES | Line 777 | In `_prepare_text_for_tts()` |
| Partial tool tag guard | YES | Line 597 | Streaming callback guard |

---

## 6. TTS CONDITIONING

### Rate Clamp Line

**File**: `server/brain/tts_conditioning.py` line 478

```python
rate_pct = max(75, min(200, round(raw_rate * 100)))
```

**Clamp range**: `[75, 200]` (75% to 200% of base rate).

### GLOBAL_SPEED_MULTIPLIER

**Line 180:**
```python
GLOBAL_SPEED_MULTIPLIER = float(os.environ.get("GLOBAL_SPEED_MULTIPLIER", "1.5"))
```

**Default value**: **1.5** (overridable via env var).

### Applied (Line 477)

```python
raw_rate = sit_style.rate * mirror.rate_mul * GLOBAL_SPEED_MULTIPLIER
```

Multiplier is applied to the computed rate after situation × mood adjustments.

---

## 7. GIT STATE

### /home/charles2/sailly-browser-demo

**Status**: NOT A GIT REPOSITORY  
- `ls -la .git` → No such file or directory
- `git log` → Command not found (git not installed on system)

### /home/charles2/sailly-google-fork

**Status**: DIRECTORY DOES NOT EXIST  
- `ls -la /home/charles2/sailly-google-fork/` → No such file or directory
- Service systemd file points to this non-existent directory

### Existing Directories

- `/home/charles2/sailly` — exists (12 KiB, Mar 27)
- `/home/charles2/sailly-browser-demo` — exists (10 MiB, Apr 23 12:52)
- `/home/charles2/sailly-google-fork_ARCHIVED_2026-04-20` — archive exists (191 dirs)

**Implication**: The revert was performed as manual file edits, not git operations. Both repos use manual change management.

---

## 8. SERVICE RESTART TIMESTAMP

### sailly-voice-agent (systemd service, port 3003)

```
● sailly-voice-agent.service - Sailly Voice Agent (Python/FastAPI)
     Loaded: loaded (/etc/systemd/system/sailly-voice-agent.service)
     Active: active (running) since Sun 2026-04-19 22:49:12 UTC; 3 days ago
   Main PID: 1101122 (python3)
```

**Service last restarted**: April 19, 2026 at 22:49:12 UTC  
**PID 1101122 elapsed time**: 3 days, 14:15:24 (as of audit time ~Apr 23 13:00)

### sailly-browser-demo (manual uvicorn, port 8080)

```
1769133  /home/charles2/sailly-browser-demo/venv/bin/python3 -m uvicorn server.main:app --port 8080
```

**Process started**: April 23, 2026 at 12:24 UTC  
**Elapsed time**: 39:58 (approx 40 minutes, as of audit time ~13:05 UTC)

### Restart Sequence

**Timeline:**
- Apr 19 22:49:12 — sailly-voice-agent systemd service started (port 3003)
- Apr 23 12:18–12:20 — Files reverted (`slot_extractor.py`, `tier2_runner.py`, `memory_manager.py`, `tts_conditioning.py`)
- Apr 23 12:24 — sailly-browser-demo uvicorn process started (port 8080)
- Apr 23 ~13:00 — This audit executed

**Finding**: **sailly-voice-agent service (port 3003) has NOT been restarted since April 19**. The revert files were edited on Apr 23 12:18–12:20, but the systemd service was not restarted. Only the manual uvicorn process on port 8080 reflects the revert.

---

## SUMMARY

### Model Configuration
- **Model currently serving SlotExtractor**: `gemini-2.0-flash` ✅ (reverted from 2.5-flash-lite)
- **Main LLM model**: `gemini-2.5-flash`
- **TTS model**: `gemini-2.5-flash-tts` (via `gemini-flash` engine)

### Generation Settings
- **Main LLM max_output_tokens**: **128** (capped per Sprint 1.2)
- **Temperature**: **0.0** (default)
- **Top_p**: Not set (uses Gemini default)
- **Stop sequences**: `["---", "\n\nBEKANNTE DATEN:", "\n\n==="]`

### Database Schema
- **Columns confirmed existing with non-NULL data**: 12 of 23 checked (52%)
- **leaks_detected column**: **DROPPED** ✅
- **response_was_fallback column**: Does not exist
- **NULL rate pattern**: ~75% sparse for observability fields (prompt_tokens_in 85.9%, prompt_tokens_out 100%, validations_fired 74.8%)

### Code Guards
- **Sanitizer (generic)**: NO
- **Minimum response guard wired**: PARTIAL (short exclamation deferral only)
- **Loop guard wired**: NO

### TTS Rate Conditioning
- **Rate clamp formula**: `max(75, min(200, round(raw_rate * 100)))`
- **X value in clamp**: **200** (max 200%)
- **GLOBAL_SPEED_MULTIPLIER**: **1.5** (default)

### Git & Deployment
- **Git HEAD sailly-browser-demo**: NOT A GIT REPOSITORY
- **Git HEAD sailly-google-fork**: NOT A GIT REPOSITORY (directory does not exist)
- **sailly-voice-agent service (port 3003) last restarted**: April 19, 2026 22:49:12 UTC
- **Service restart AFTER last code change**: **NO** ✅ CRITICAL ISSUE

### Critical Finding

**The sailly-voice-agent systemd service (port 3003) was NOT RESTARTED after the revert.** Files were edited Apr 23 12:18–12:20, but the service continues running the pre-revert code from Apr 19. Only the manually-started uvicorn process on port 8080 (sailly-browser-demo) reflects the revert.

**Service must be restarted for revert to take effect:**
```bash
sudo systemctl restart sailly-voice-agent
```

---

---

## ADDENDUM: sailly.tech NGINX ROUTING

### Discovered Architecture: Split-Brain Deployment

**Browser Demo (WebSocket + Dashboard UI):**
- URL: `https://sailly.tech/demo-call`, `https://sailly.tech/ws/demo`
- Nginx upstream: `sailly_demo` → `127.0.0.1:8080`
- Process: `/home/charles2/sailly-browser-demo/venv/bin/python3 -m uvicorn`
- Status: **RUNNING** (started Apr 23 12:24 UTC)
- Code: **POST-REVERT** ✅

**Voice Pipeline API:**
- URL: `https://sailly.tech/api/demo/` and `/api/dashboard/call-analysis`
- Nginx proxy: `http://127.0.0.1:3003`
- Process: sailly-voice-agent systemd service (PID 1101122)
- Status: **RUNNING** (started Apr 19 22:49:12 UTC)
- Code: **PRE-REVERT** ⚠️ (NOT RESTARTED after revert)

### Implication

**sailly.tech demo browser uses port 8080 for UI/WebSocket, but voice calls route to port 3003.**

When a user calls `sailly.tech/demo-call`:
1. ✅ UI and WebSocket run reverted code (port 8080)
2. ⚠️ Voice agent backend runs pre-revert code (port 3003)

**Result**: Demo browser sees hybrid behavior — revert not fully deployed to production.

---

**Report Generated**: 2026-04-23 ~13:05 UTC  
**No changes made. Facts only. All times in UTC.**
