# Call Reports - Phase 0-7 Metrics Integration

## Summary

Yes! The call reports generated on sailly.tech are **now automatically updated** with all Phase 0-7 metrics. Every new call report will include:

✅ TTS latency measurements (Phase 3)  
✅ Validation pass tracking (Phase 2)  
✅ Slot extraction counts (Phase 1)  
✅ Barge-in success tracking (Phase 4)  
✅ All existing metrics (latency p50/p95, LLM, STT, etc.)

---

## How It Works

### Automatic Report Generation
The cron job at `scripts/cron/generate_new_call_reports.py` runs **every minute** and:

1. Queries `google_calls` for calls created after the last run
2. For each new call, generates:
   - `{call_sid}-analysis.md` (Markdown report for web viewing)
   - `{call_sid}-analysis.json` (JSON data for API/dashboard)
3. Saves to `call_reports/{YYYY-MM-DD}/{HH}/` directory

### What Gets Updated in Reports

The report now includes a **Phase 0-7 Metrics Section** showing:

```
| [Phase 3] TTS latency      | p50 / max ms (N turns) | Measured timing |
| [Phase 2] Validation passes | N turns                | Pass tracking   |
| [Phase 1] Slot extractions  | N turns                | Extraction count|
```

Plus existing checks:
- Latency p50/p95/max
- Loop incidents
- Barge-in successes
- Error codes
- LLM and STT metrics

---

## Next New Call Generation

### When Reports Are Generated

Reports are generated **automatically** for each call when:
1. Call completes and data is persisted to PostgreSQL
2. The cron job runs (every minute)
3. It detects a new call with `started_at > last_run_time`

### Timeline

- **Call ends** → Data written to `google_calls`, `google_turn_metrics`, etc.
- **Within 60 seconds** → Cron job runs and generates reports
- **Report ready** → Available on sailly.tech dashboard
- **Metrics included** → Full Phase 0-7 data in the report

---

## Accessing Reports

### Manual Generation
```bash
cd /home/charles2/sailly-browser-demo
source .env
./venv/bin/python scripts/cron/generate_new_call_reports.py
```

### Programmatic Access
```bash
# Via API endpoint (if available)
curl http://localhost:8080/api/dashboard/call-report/{call_sid}?report_format=markdown

# Via direct file
cat call_reports/{YYYY-MM-DD}/{HH}/{call_sid}-analysis.md
```

### View on Dashboard
- Go to sailly.tech call history
- Click on a call to see the full markdown report
- Phase 0-7 metrics visible in "Aggregate health" section

---

## Report Structure

The markdown report includes:

### Section 1: Call Overview
- Call SID, caller, timestamps, duration
- Quality score, avg/p95/max latency
- Outcome, escalation status

### Section 2: Aggregate Health **← NEW PHASE 0-7 DATA HERE**
- **[Phase 3] TTS latency** - p50, max, and count of measured turns
- **[Phase 2] Validation passes** - number of turns with validation data
- **[Phase 1] Slot extractions** - number of turns with slot data
- Plus existing: latency percentiles, loop incidents, barge-in counts, errors

### Section 3: Environment Snapshot
- LLM model, STT settings, TTS settings
- Monitoring thresholds
- Build SHA

### Section 4: Turn-by-Turn Transcript
- User utterance → Bot response
- Metrics flags (latency alerts, error codes)
- Tool calls
- Caller-annotated issues (if any: "Achtung Sailly: ...")

### Section 5: Achtung Sailly Insights
- Caller-provided feedback on issues
- Cross-referenced with metrics

---

## Data Flow for Next Call

Here's what happens when the next call completes:

```
1. Call ends
   ↓
2. brain_service.finalize_call() writes to PostgreSQL:
   - google_calls (call header)
   - google_turn_metrics (row per turn with Phase 0-7 data)
   - google_transcripts (utterances)
   - google_tool_calls (executed tools)
   ↓
3. Cron job runs (within 60 seconds):
   - Detects new call
   - Queries all metrics tables
   - Calls build_call_report_markdown()
   ↓
4. Updated builder.py:
   - Calculates Phase 0-7 aggregates:
     * TTS latency p50/max
     * Validation pass count
     * Slot extraction count
   - Includes in "Aggregate health" section
   ↓
5. Report generated with NEW metrics:
   - {call_sid}-analysis.md
   - {call_sid}-analysis.json
   ↓
6. Available on sailly.tech dashboard
```

---

## Modified Files

- `server/call_report/builder.py` — Updated to:
  - Extract Phase 0-7 metrics from turn data
  - Calculate aggregates (TTS p50/max, validation count, slot extraction count)
  - Include Phase 0-7 section in markdown report

---

## Verification

### Check Recent Reports
```bash
ls -lah call_reports/
# Should show directories for recent dates/hours
```

### View Report Content
```bash
# Find latest report
LATEST=$(find call_reports -name "*-analysis.md" -type f | sort | tail -1)
cat "$LATEST" | grep -A 10 "Aggregate health"
# Should show Phase 0-7 metrics
```

### Monitor Cron Job
```bash
tail -f /tmp/call-report-cron.log
# Will show: "Found N new calls" with Phase 0-7 data in reports
```

---

## Summary

✅ **Call reports now include Phase 0-7 metrics**  
✅ **Automatic generation on every new call (within 60 seconds)**  
✅ **Data visible in sailly.tech dashboard**  
✅ **No manual intervention required**  

**Next call** that completes will automatically generate a report with:
- TTS latency measurements
- Validation pass counts
- Slot extraction counts
- All existing metrics

The system is ready to go! 🚀
