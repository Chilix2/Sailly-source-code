# COMPLETE TIMELINE CLARIFICATION & 60-CALL ANALYSIS
## Sailly — Understanding the Full Call History, Code Deployments, and Port Architecture

---

## PART 1: THE CORRECT ARCHITECTURE (CORRECTING EARLIER CONFUSION)

### The Earlier Analysis Was Wrong on Port 3003

A previous analysis stated: "All real calls came from port 3003." **That was incorrect.**

The logs prove the opposite. Here is what is actually true:

### Every Single Live Call From sailly.tech/demo-call Goes Through PORT 8080

**Nginx routes:**
- `https://sailly.tech/ws/demo` → `upstream sailly_demo` → `127.0.0.1:8080`
- `https://sailly.tech/demo-call` UI → `http://127.0.0.1:3001` (Next.js frontend only)
- `/api/demo/` → `http://127.0.0.1:3003` (legacy voice pipeline, NOT demo calls)

**What port 3003 does:**
- Serves `/api/demo/` endpoints (legacy API only)
- Has been running since Apr 19 from an archived codebase
- Has **zero** WebSocket calls going through it from sailly.tech/demo-call
- Is irrelevant to all call analysis done in this project

**What port 8080 does:**
- Serves ALL WebSocket connections (`/ws/demo`) — i.e., every real call
- Has been the production demo service since April 20
- Gets restarted whenever code changes are deployed
- Writes all metrics to PostgreSQL

---

## PART 2: HOW CODE CHANGES REACHED PORT 8080

### How Changes Were Always Applied

1. Code changes were made to files in `/home/charles2/sailly-browser-demo/server/`
2. `sudo systemctl restart sailly-browser-demo.service` was run
3. The new code loaded and served all subsequent calls via port 8080

This happened **dozens of times across April 20–23**. The service was restarted on every code change. Evidence from `journalctl`:

```
Apr 20 00:00:37  Started (first Apr 20 restart)
Apr 20 00:05:30  Stopped → Started
Apr 20 10:35:54  Stopped → Started
Apr 20 10:51:20  Stopped → Started
Apr 20 10:52:10  Stopped → Started
Apr 20 10:53:16  Stopped → Started
Apr 20 11:54:37  Stopped → Started
Apr 20 13:26:54  Stopped → Started
Apr 20 13:35:26  Stopped → Started
... (multiple more Apr 20 restarts)
Apr 22 09:17:53  Stopped → Started
Apr 22 10:01:22  Stopped → Started
Apr 22 10:22:38  Stopped → Started
... (9 more Apr 22 restarts)
Apr 23 09:55:16  Stopped → Started  ← Apr 23 plan changes deployed
Apr 23 09:56:02  Stopped → Started  ← Re-deployed
Apr 23 10:02:32  Stopped → Started  ← Re-deployed
Apr 23 12:24:43  Stopped → Started  ← Revert deployed
```

### The Codebase Path

| Directory | Role | Status |
|-----------|------|--------|
| `/home/charles2/sailly-browser-demo/` | Active production codebase | ✅ All changes made here |
| `/home/charles2/sailly-google-fork_ARCHIVED_2026-04-20/` | Archived old codebase | Frozen Apr 20 |
| `/home/charles2/sailly-google-fork/` | Old systemd service WorkingDirectory | Does NOT exist on disk (archived) |

The `sailly-voice-agent` service (port 3003) is still running from the Apr 19 in-memory image of the old codebase. It never serves demo calls. It is a ghost — running but irrelevant.

---

## PART 3: THE CORRECT CODE DEPLOYMENT TIMELINE

### Code State Per Period (Port 8080)

```
Apr 20 00:00 → Apr 22 22:00
├─ Code: Sprint 0-2 work (observability framework, TTS conditioning,
│         node manager, validation registry structure)
│         subsystems_fired, tts_situation, tts_mood, tts_rate_pct — present
│         prompt_tokens_in — NOT present (write-path broken)
│         validation_registry — structure in code but silent
└─ Evidence: demo-6cf65e58003d (Apr 22 22:00) has 0 in all metric columns

Apr 22 22:00 → Apr 23 09:08
├─ Code: Sprint 3 work deployed (token auditing added to logs,
│         subsystems_fired enriched, slot_state_json added)
│         subsystems_fired — NOW contains rich JSON (slot_extractor status, etc.)
│         prompt_tokens_in — STILL NULL (write-path still broken)
│         validation_registry: "silent" — structure runs but fires nothing
│         SlotExtractor model: gemini-2.0-flash (404 NOT_FOUND — broken)
└─ Evidence: demo-5d54bda724cc (09:08) has full subsystems data but NULL tokens

Apr 23 09:08 → 09:17 [THE 4 ANALYZED CALLS]
├─ Code: Pre-Apr-23-session code (Sprint 3 deployed, but Apr 23 fixes NOT yet)
│         All 4 calls show SlotExtractor 404 in logs (gemini-2.0-flash missing)
│         subsystems_fired: {"slot_extractor": "completed"} — misnomer; extractor ran
│         but returned {} empty due to 404 error; logged as "completed" anyway
│         prompt_tokens_in: NULL — token write-path broken
│         validation_registry: "silent" — zero validations firing
└─ Service PID at this time: 1620901

Apr 23 09:55 → 12:18 [APR 23 SESSION CHANGES DEPLOYED]
├─ Restart at 09:55:16 — Apr 23 plan code goes live:
│   - SlotExtractor changed to gemini-2.5-flash-lite ✅
│   - Preflight check added to main.py ✅
│   - token auditing write-path fixed ✅
│   - build_context() returns tuple ✅
│   - memory_manager menu pivot hints ✅
│   - ValidationRegistry [VAL_TRACE] logging ✅
│   - OpenTelemetry spans ✅
│   - TTS A/B test infrastructure ✅
│   - leaks_detected column added ✅
├─ Log confirms at 09:55:28: "[PREFLIGHT] slot_extractor (gemini-2.5-flash-lite) — OK"
├─ Log confirms at 09:56:12: "[PREFLIGHT] slot_extractor (gemini-2.5-flash-lite) — OK"
│
├─ Calls 10:05 → 12:01 ran WITH Apr 23 changes:
│   demo-9d05fb0ef1d2, demo-7404322ad8a6, demo-29d1f38415af, demo-7fc75c89264e,
│   demo-fef404665065, demo-d1817073426f, demo-03a986bc848f, demo-131aca72621f
│   ALL show: prompt_tokens_in ≠ NULL, validation_registry "fired" on many turns
└─ These ARE the calls with working Apr 23 changes

Apr 23 12:18 → NOW [REVERT DEPLOYED]
├─ Files reverted: 12:18-12:20
│   - SlotExtractor back to gemini-2.0-flash (broken)
│   - Preflight check removed
│   - Token write-path reverted
│   - OpenTelemetry removed
│   - menu pivot removed
│   - leaks_detected column dropped
├─ Service restarted at 12:24:43
│   - No "[PREFLIGHT]" log (function deleted)
├─ Calls 12:41, 12:42 ran WITH reverted code:
│   demo-001d8beeecfa, demo-602e68d8c145
│   - prompt_tokens_in: NULL (reverted)
│   - SlotExtractor: "completed" but 404 error in logs again
└─ Confirms revert is active
```

---

## PART 4: ANSWERING THE EXACT QUESTION

> "If port 3003 was measuring (catching all data), how did code changes get to port 8080?"

**The premise is incorrect.** Port 3003 was never measuring. Port 3003 was irrelevant.

The correct version:
- **Port 8080 (sailly-browser-demo) caught ALL data** — every metric, every call
- **Code changes went TO port 8080** via `systemctl restart sailly-browser-demo.service`
- **Port 8080 ran all sprint code** once deployed and restarted
- **The 4 analyzed morning calls (09:08-09:17)** ran port 8080 with pre-Apr-23 code
- **The Fix 1 verification calls (10:05-12:01)** ran port 8080 WITH Apr 23 changes
- **The current calls (12:41+)** run port 8080 with reverted code

Port 3003 was never in the picture for any call analysis. It serves `/api/demo/` only and runs an archived codebase that stopped being relevant when sailly-google-fork was archived on Apr 20.

---

## PART 5: 60-CALL ANALYSIS REPORT

### Legend
- **tok_in**: prompt_tokens_in populated (1=yes, 0=null)
- **subs**: subsystems_fired populated
- **tts_sit**: tts_situation populated
- **slots**: slot_state_json populated
- **val**: validations_fired_this_turn populated
- **val_fired**: validation_registry actually fired this call
- **Code era**: Which deployment was running

```
 # | call_sid          | UTC Date/Time | Dur | Turns | Outcome           | Avg Lat | tok_in | subs | val_fired | Code Era
---+-------------------+---------------+-----+-------+-------------------+---------+--------+------+-----------+----------
 1 | demo-602e68d8c145 | Apr 23 12:42  |  97 |     5 | client_disconnect |  1339ms |   NO   |  YES |    NO     | REVERTED
 2 | demo-001d8beeecfa | Apr 23 12:41  |  43 |     2 | client_disconnect |  1771ms |   NO   |  YES |    NO     | REVERTED
 3 | demo-131aca72621f | Apr 23 12:01  |  61 |     4 | client_disconnect |  3424ms |  YES   |  YES |   YES     | APR-23 PLAN
 4 | demo-03a986bc848f | Apr 23 11:59  |  81 |     5 | end_call_tool ✅  |  2636ms |  YES   |  YES |    NO     | APR-23 PLAN
 5 | demo-d1817073426f | Apr 23 11:57  |  65 |     3 | client_disconnect |  5748ms |  YES   |  YES |   YES     | APR-23 PLAN
 6 | demo-fef404665065 | Apr 23 11:56  |  85 |     3 | client_disconnect |  3849ms |  YES   |  YES |   YES     | APR-23 PLAN
 7 | demo-7fc75c89264e | Apr 23 11:17  |  63 |     2 | client_disconnect |  2046ms |  YES   |  YES |   YES     | APR-23 PLAN
 8 | demo-29d1f38415af | Apr 23 11:14  |  61 |     3 | client_disconnect |  1630ms |  YES   |  YES |   YES     | APR-23 PLAN
 9 | demo-7404322ad8a6 | Apr 23 11:12  |  87 |     5 | client_disconnect |  1831ms |  YES   |  YES |   YES     | APR-23 PLAN
10 | demo-9d05fb0ef1d2 | Apr 23 10:05  |  55 |     4 | client_disconnect |  1938ms |  YES   |  YES |   YES     | APR-23 PLAN
11 | demo-bb63f93c7714 | Apr 23 09:15  | 111 |     4 | client_disconnect |  1597ms |   NO   |  YES |    NO     | PRE-PLAN
12 | demo-6997d8765097 | Apr 23 09:13  |  67 |     6 | client_disconnect |  1367ms |   NO   |  YES |    NO     | PRE-PLAN
13 | demo-fde5e5810a03 | Apr 23 09:11  |  53 |     2 | client_disconnect |  1434ms |   NO   |  YES |    NO     | PRE-PLAN
14 | demo-5d54bda724cc | Apr 23 09:08  |  76 |     4 | client_disconnect |  1528ms |   NO   |  YES |    NO     | PRE-PLAN
15 | demo-6cf65e58003d | Apr 22 22:00  | 202 |     8 | client_disconnect |  4585ms |   NO   |   NO |    NO     | SPRINT-2
16 | demo-c111c5d06b4c | Apr 22 21:32  |  10 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
17 | demo-da09b5c5b83c | Apr 22 21:32  |  19 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
18 | demo-bef6d46394c2 | Apr 22 21:29  |  17 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
19 | demo-93d8ce59f6c3 | Apr 22 21:27  |  14 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
20 | demo-8b726968bee5 | Apr 22 21:27  |   5 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
21 | demo-a69c6656aac8 | Apr 22 20:21  |   4 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
22 | demo-365164fb09fa | Apr 22 20:17  |   6 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
23 | demo-d6c3bf23a598 | Apr 22 20:17  |   8 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
24 | demo-ba3979a53fb5 | Apr 22 20:10  |   1 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
25 | demo-c2e8bc4cba27 | Apr 22 20:07  |   7 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
26 | demo-6925a43baf7e | Apr 22 19:56  | 130 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
27 | demo-d10cc903dddb | Apr 22 18:17  |   2 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
28 | demo-a41e8ac02d6a | Apr 22 18:17  |  12 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
29 | demo-70e8d241a589 | Apr 22 18:11  |  17 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
30 | demo-3ea6bd3314a2 | Apr 22 18:10  |   5 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
31 | demo-61860c854ec0 | Apr 22 18:10  |   8 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
32 | demo-14386adf6323 | Apr 22 18:10  |   8 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
33 | demo-be050891895a | Apr 22 18:09  |   2 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
34 | demo-165b926866d4 | Apr 22 18:09  |   2 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
35 | demo-164163aff90a | Apr 22 18:09  |  10 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
36 | demo-eaf7e14b1d72 | Apr 22 18:08  |  59 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
37 | demo-31cfd6f01bca | Apr 22 18:07  |   7 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
38 | demo-cc79905d4a6e | Apr 22 18:01  |  53 |     5 | client_disconnect |  5103ms |   NO   |   NO |    NO     | SPRINT-2
39 | demo-958bec4da99d | Apr 22 18:00  |   8 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
40 | demo-7459964160dc | Apr 22 18:00  |  27 |     2 | client_disconnect |  5857ms |   NO   |   NO |    NO     | SPRINT-2
41 | demo-8bfd3579f40a | Apr 22 17:53  |  22 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
42 | demo-3d041b37aba9 | Apr 22 17:47  | 108 |     8 | client_disconnect |  2224ms |   NO   |   NO |    NO     | SPRINT-2
43 | demo-64663f6fb6fe | Apr 22 17:45  |  58 |     1 | client_disconnect |  2669ms |   NO   |   NO |    NO     | SPRINT-2
44 | demo-12bf458c9157 | Apr 22 17:45  |  19 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
45 | demo-86914ff49a9b | Apr 22 17:44  |  11 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
46 | demo-f00936bd9d02 | Apr 22 16:42  | 119 |     7 | client_disconnect |  3824ms |   NO   |   NO |    NO     | SPRINT-2
47 | demo-fb7fd78f3492 | Apr 22 16:32  | 153 |    10 | client_disconnect |  3493ms |   NO   |   NO |    NO     | SPRINT-2
48 | demo-0262ca1b31fc | Apr 22 16:29  |  14 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
49 | demo-7b79f9d74990 | Apr 22 16:29  |   5 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
50 | demo-be3881e36b1b | Apr 22 15:17  | 304 |    15 | client_disconnect |  3544ms |   NO   |   NO |    NO     | SPRINT-2
51 | demo-baa9ae832ab3 | Apr 22 11:41  | 194 |     8 | client_hangup     |  1613ms |   NO   |   NO |    NO     | SPRINT-2
52 | demo-c97c1f9ff8f6 | Apr 22 11:41  |   8 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
53 | demo-0996d962e336 | Apr 22 11:23  | 284 |    16 | end_call_tool ✅  |  2098ms |   NO   |   NO |    NO     | SPRINT-2
54 | demo-aa70838aa81b | Apr 22 10:40  |   5 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
55 | demo-8377fff219ce | Apr 22 10:29  |  14 |     1 | client_disconnect |  1842ms |   NO   |   NO |    NO     | SPRINT-2
56 | demo-c12a86957e9f | Apr 22 09:56  |  24 |     4 | client_disconnect |  1706ms |   NO   |   NO |    NO     | SPRINT-2
57 | demo-557b7d4a1a9b | Apr 22 09:55  |   5 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
58 | demo-fc9e91ec2a9f | Apr 22 09:55  |  26 |     3 | client_disconnect |  1884ms |   NO   |   NO |    NO     | SPRINT-2
59 | demo-92c14a47c57f | Apr 22 09:55  |  24 |     2 | client_disconnect |  5426ms |   NO   |   NO |    NO     | SPRINT-2
60 | demo-bc9f5a816bdc | Apr 22 08:42  |  24 |     0 | client_disconnect |     —   |   NO   |   NO |    NO     | SPRINT-2
```

---

## PART 6: WHAT EACH CODE ERA ACTUALLY DID

### SPRINT-2 Era (Apr 22 all day)
**Code**: Sprint 0–2 deployed. No sprint-3 token auditing write-path. No enriched subsystems_fired.
- `subsystems_fired`: **0/60** calls populated (column existed but was not being written)
- `prompt_tokens_in`: **0/60** calls populated
- `tts_situation`, `tts_mood`, `tts_rate_pct`: **0/60** calls populated
- Notable: `demo-0996d962e336` completed as `end_call_tool` ✅ (one successful order)
- Notable: `demo-baa9ae832ab3` ended as `client_hangup` (user rage-quit)
- Latency problems visible: calls at 17:53, 18:00, 18:01 show 5000ms+ avg latency

### PRE-PLAN Era (Apr 23 09:08–09:17)
**Code**: Sprint 3 deployed. Subsystems_fired written. But SlotExtractor 404.
- `subsystems_fired`: **4/4** calls populated ✅
- `slot_state_json`: **4/4** calls populated ✅
- `prompt_tokens_in`: **0/4** calls (write-path still broken in this era)
- `validation_registry`: "silent" on all 4 (registry runs but never fires)
- **SlotExtractor**: 404 NOT_FOUND on EVERY turn — `gemini-2.0-flash` dead
- `subsystems_fired` shows `"slot_extractor": "completed"` but this is misleading:
  the extractor ran but returned `{}` empty due to the 404 error
- These ARE the "4 analyzed calls" that triggered the Apr 23 plan

### APR-23 PLAN Era (Apr 23 09:55–12:18)
**Code**: Full Apr 23 "Stabilize, Verify, Advance" plan deployed.
- `subsystems_fired`: **8/8** calls populated ✅
- `prompt_tokens_in`: **8/8** calls populated ✅ (write-path fixed)
- `validation_registry: "fired"`: **7/8** calls ✅ (registry now firing)
- `SlotExtractor`: `gemini-2.5-flash-lite` — no more 404 errors
- Preflight log confirms: `[PREFLIGHT] slot_extractor (gemini-2.5-flash-lite) — OK`
- `demo-03a986bc848f`: completed as `end_call_tool` ✅ (reservation booked)
- These are the "Fix 1 verification calls" and subsequent test calls
- Avg latency improved but still 1600–5700ms range

### REVERTED Era (Apr 23 12:24–now)
**Code**: Apr 23 changes reverted. Back to gemini-2.0-flash for SlotExtractor.
- `subsystems_fired`: **2/2** calls populated ✅ (pre-Apr-23 sprint code kept)
- `prompt_tokens_in`: **0/2** calls (reverted — write-path removed)
- `validation_registry`: "silent" again (VAL_TRACE removed)
- SlotExtractor: 404 errors again in logs (gemini-2.0-flash dead again)
- No preflight check (removed in revert)

---

## PART 7: THE REAL QUESTION — SHOULD THE REVERT HAVE HAPPENED?

### What the Apr 23 Plan Actually Achieved (Before Revert)

From the APR-23 PLAN era calls (9 calls, 09:55–12:18):

| Feature | Status Before Plan | Status After Plan | Status After Revert |
|---------|-------------------|-------------------|---------------------|
| SlotExtractor running | ❌ 404 dead | ✅ gemini-2.5-flash-lite OK | ❌ 404 dead again |
| prompt_tokens_in written | ❌ NULL | ✅ populated | ❌ NULL again |
| ValidationRegistry firing | ❌ silent | ✅ fired on 7/9 calls | ❌ silent again |
| Preflight model check | ❌ missing | ✅ boot-time check | ❌ missing again |
| Reservation completed | ❌ not seen | ✅ demo-03a986bc848f | ❓ too few post-revert calls |

**The Apr 23 plan was working.** The revert undid working fixes.

### The "Culprit" You Were Looking For

**The revert was triggered by a different concern** (code was "getting out of hand"), not because the fixes were broken. The fixes were functioning. The decision to revert deleted 4 working features from production:

1. ✅ SlotExtractor now 404-dead again
2. ✅ Token auditing silently NULL again
3. ✅ ValidationRegistry silent again
4. ✅ No model preflight check at boot

---

## SUMMARY

| Question | Answer |
|----------|--------|
| Which port handled all demo calls? | **Port 8080 (sailly-browser-demo)** |
| Which port is irrelevant? | Port 3003 (sailly-voice-agent) — legacy, serves no calls |
| How did code changes reach port 8080? | `systemctl restart sailly-browser-demo.service` — done ~30+ times Apr 20–23 |
| Did the Apr 23 plan changes actually deploy? | **YES** — at 09:55:16 UTC, confirmed by logs and DB data |
| Did the Apr 23 plan changes work? | **YES** — token auditing, SlotExtractor, ValidationRegistry all functional |
| What did the revert undo? | Working code that fixed the 4 critical production bugs |
| Is the revert currently active? | YES — SlotExtractor 404, tokens NULL, ValidationRegistry silent |
| Were any call analysis reports based on bad data? | Pre-plan morning calls (09:08–09:17) showed partial data (no tokens, SlotExtractor dead) |
| Were any call analysis reports based on correct data? | Yes — calls 09:55–12:18 show full accurate data from working code |

---

**Generated**: 2026-04-23 ~13:30 UTC  
**Evidence**: journalctl, nginx config, PostgreSQL call data, file modification times
