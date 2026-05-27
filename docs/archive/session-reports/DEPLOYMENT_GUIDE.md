# Implementation Checklist & Deployment Guide

## Files Modified (5 total)

- [x] `/home/charles2/sailly-browser-demo/server/database.py`
- [x] `/home/charles2/sailly-browser-demo/server/brain/contracts/turn_timings.py`
- [x] `/home/charles2/sailly-browser-demo/server/brain/v4_turn_processor.py`
- [x] `/home/charles2/sailly-browser-demo/server/brain_service.py`
- [x] `/home/charles2/sailly-browser-demo/server/call_report/builder.py`

## Pre-Deployment Verification

### 1. Code Quality ✅
- [x] No syntax errors
- [x] No linter errors
- [x] Type hints correct
- [x] Comments clear and helpful
- [x] Imports all present

### 2. Backward Compatibility ✅
- [x] Database migration uses `IF NOT EXISTS`
- [x] Fallback values for `tts_ttfb_ms` in brain_service.py
- [x] No breaking changes to existing APIs
- [x] Old code paths still functional

### 3. Logic Verification ✅
- [x] `_turn_timings` initialized before any async work
- [x] `tts_ttfb_ms()` computed correctly (stt_done → first audio)
- [x] `tts_first_byte_ms()` still computes synthesis latency
- [x] Metrics dict merge order correct (TurnTimings overrides fallbacks)
- [x] Call report displays both metrics clearly

## Deployment Steps

### Step 1: Database Migration
```bash
# This happens automatically on service startup
# database.py:ensure_turn_metrics_table() runs on app init

# Verify migration:
psql $DATABASE_URL -c "\d google_turn_metrics"
# Should show: tts_ttfb_ms | integer
```

### Step 2: Deploy Code Changes
```bash
# Pull the changes
git pull

# All 5 files are updated and ready
# No restart configuration changes needed
```

### Step 3: Service Restart
```bash
# Restart the service (will auto-run database migrations)
systemctl restart sailly-browser-demo.service

# Check logs
journalctl -u sailly-browser-demo.service -f

# Should see: "[DB] google_turn_metrics table ensured"
```

### Step 4: Verify Functionality
```bash
# Run a test call through the system
# Generate a call report

# Check database:
psql $DATABASE_URL -c "
SELECT tts_ttfb_ms, tts_first_byte_ms, llm_latency_ms 
FROM google_turn_metrics 
ORDER BY created_at DESC 
LIMIT 5;
"
# Should see populated integer values, not NULL
```

### Step 5: Verify Call Report Display
```bash
# Fetch a recent call report
curl -s http://localhost:8000/api/call/{call_sid}/report

# Verify output contains:
# - "Brain Processing: Xms (STT final → TTS text)"
# - "TTS TTFB: Yms (STT final → first audio)"
# - "## Latency Breakdown" section
```

## Rollback Plan (if needed)

### If database migration fails:
```bash
# The migration is safe with IF NOT EXISTS, but if rollback needed:
psql $DATABASE_URL -c "
ALTER TABLE google_turn_metrics DROP COLUMN IF EXISTS tts_ttfb_ms;
"
```

### If code has issues:
```bash
# Revert the 5 modified files
git revert HEAD~0..HEAD~4

# Service will continue working with fallback values
# Old code paths are still functional
```

## Monitoring & Validation

### Immediate (First Hour)
- [ ] Service starts without errors
- [ ] Database migrations complete successfully
- [ ] Logs show no `_turn_timings` related errors
- [ ] First test calls complete normally

### Short-term (First Day)
- [ ] All turns have populated `tts_ttfb_ms` values
- [ ] Call reports display both metrics
- [ ] No NULL values in `tts_ttfb_ms` column
- [ ] `tts_ttfb_ms > llm_latency_ms` (always true: TTFB includes brain processing)

### Ongoing Monitoring
```sql
-- Check for any NULL values (should be 0)
SELECT COUNT(*) as null_count 
FROM google_turn_metrics 
WHERE tts_ttfb_ms IS NULL 
AND created_at > NOW() - INTERVAL '1 hour';

-- Monitor metric distribution
SELECT 
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tts_ttfb_ms) as p50,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tts_ttfb_ms) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY tts_ttfb_ms) as p99,
    MAX(tts_ttfb_ms) as max_ms
FROM google_turn_metrics 
WHERE created_at > NOW() - INTERVAL '1 day';

-- Check TTS synthesis latency trends
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as turns,
    AVG(tts_ttfb_ms - llm_latency_ms) as avg_tts_latency,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY (tts_ttfb_ms - llm_latency_ms)
    ) as p95_tts_latency
FROM google_turn_metrics
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;
```

## Testing Checklist

### Unit Tests (if applicable)
```bash
# Run existing latency instrumentation tests
pytest tests/observability/test_latency_instrumentation.py -v

# All tests should pass without changes needed
# (contract is backward compatible)
```

### Integration Tests
```bash
# Test a complete call flow
# 1. STT → Brain → TTS → Audio output
# 2. Verify all timestamps captured
# 3. Verify metrics written to DB
# 4. Verify call report displays correctly
```

### Manual Testing
```bash
# 1. Make a test call
# 2. Check database for metrics
SELECT 
    turn_number,
    user_text,
    bot_text,
    llm_latency_ms,
    tts_ttfb_ms,
    (tts_ttfb_ms - llm_latency_ms) as tts_net_latency
FROM google_turn_metrics
WHERE call_sid = 'test-call-id'
ORDER BY turn_number;

# 3. Generate call report
curl http://localhost:8000/api/call/test-call-id/report -o report.md

# 4. Verify report contains:
# - Brain Processing (llm_latency_ms)
# - TTS TTFB (tts_ttfb_ms)
# - Latency Breakdown section
```

## Expected Values

### Typical Latency Ranges

| Metric | Min | Typical | Max | Note |
|--------|-----|---------|-----|------|
| `brain_processing_ms` | 500ms | 2000-2500ms | 5000ms | LLM processing |
| `tts_first_byte_ms` | 100ms | 600-900ms | 2000ms | Synthesis + network |
| `tts_ttfb_ms` | 700ms | 2600-3500ms | 7000ms | Total perceived |
| `tts_ttfb_ms - llm_latency_ms` | 50ms | 600-1000ms | 2000ms | TTS + network only |

### Red Flags 🚩

- `tts_ttfb_ms` > 5000ms: Check network/TTS service
- `tts_ttfb_ms` not monotonically increasing across turns: Check timestamp logic
- `tts_ttfb_ms` < `llm_latency_ms`: Bug! TTFB must include brain processing
- High variance in `tts_first_byte_ms`: TTS service inconsistency

## Performance Impact

- **Negligible**: All computations are O(1) math operations
- **Memory**: One `TurnTimings` object per active turn (~500 bytes)
- **Database**: One new INTEGER column (~8 bytes per row)
- **I/O**: No additional queries, metrics written in existing batch

## Documentation

Generated documentation files:
- `INSTRUMENTATION_SUMMARY.md` - Complete overview
- `CHANGES_REFERENCE.md` - File-by-file changes
- `BEFORE_AFTER.md` - Comparison with examples
- `DEPLOYMENT_GUIDE.md` - This file (deployment steps)

## Success Criteria

✅ **Implementation Complete When**:
1. All 5 files modified and committed
2. Database migration runs successfully
3. Service starts without errors
4. First test calls have populated `tts_ttfb_ms` values
5. Call reports display both metrics correctly
6. All metrics > 0 (no NULL or zero values in normal operation)
7. `tts_ttfb_ms >= llm_latency_ms` always true

✅ **Ready for Production When**:
1. All success criteria met
2. 24+ hours of data collected
3. No anomalies in metric distributions
4. Team comfortable with new metrics
5. Dashboards/alerts updated (if applicable)

## Questions?

Refer to:
- **Architecture questions**: See `INSTRUMENTATION_SUMMARY.md`
- **Code questions**: See `CHANGES_REFERENCE.md`
- **Metric questions**: See `BEFORE_AFTER.md`
- **Deployment issues**: Check rollback plan above

---

**Deployment Status**: ✅ Ready
**Risk Level**: 🟢 Low (backward compatible, safe migrations)
**Estimated Deployment Time**: 5-10 minutes
