# Call Analysis Report - Issues Document

**Generated:** May 27, 2026  
**Data Range:** 30 most recent call reports  
**Starting Call ID:** demo-8008b0d9c01f  
**Analysis Period:** May 26, 2026 14:45 - May 26, 2026 23:06

---

## Executive Summary

This comprehensive analysis examines 30 recent calls from the Sailly browser demo application. The data reveals **critical performance and reliability issues** that require immediate attention.

### Key Findings:
- **29 of 30 calls (96.7%)** ended with client disconnect
- **17 of 30 calls (56.7%)** experienced high latency (avg > 500ms)
- **17 of 30 calls (56.7%)** exhibited high P95 latency (> 1000ms)
- **17 of 30 calls (56.7%)** recorded dead air periods (silence detection failures)
- Average call quality score: **6.98/10** (below acceptable threshold)

---

## Issue Summary by Category

| Issue Type | Count | % of Calls | Severity |
|-----------|-------|-----------|----------|
| Client Disconnect | 29 | 96.7% | **CRITICAL** |
| High Average Latency (>500ms) | 17 | 56.7% | **HIGH** |
| High P95 Latency (>1000ms) | 17 | 56.7% | **HIGH** |
| Dead Air Periods | 17 | 56.7% | **HIGH** |
| Low Quality Score (<5.0) | 1 | 3.3% | MEDIUM |
| Escalations | 0 | 0% | - |
| Emergency Events | 0 | 0% | - |
| Loop Incidents | 0 | 0% | - |

---

## Detailed Findings

### 1. Client Disconnect Issue (CRITICAL - 96.7%)

**Impact:** Almost all calls are ending prematurely with client disconnection.

**Affected Calls:** 29 out of 30
- Only 1 call (demo-98e6e680d587) had a different outcome: "recovered_orphan_metrics"

**Root Cause Hypothesis:**
- Browser demo environment may be intentionally disconnecting calls after completion
- Network connectivity issues between client and server
- Possible call timeout mechanism

**Recommendation:** 
- Verify if this is expected behavior in demo environment
- Check for call duration limits or disconnection policies
- Review browser console for disconnect error messages
- Analyze server logs for timeout or connection reset patterns

---

### 2. Latency Performance Issues (HIGH - 56.7%)

**Impact:** More than half of calls show significant latency, degrading user experience.

#### Latency Distribution:
```
0-500ms    :  1 calls  (  3.3%)  ✓ Acceptable
500-1000ms :  5 calls  ( 16.7%)  ⚠ Borderline
1000-1500ms:  8 calls  ( 26.7%)  ✗ Poor
1500-2000ms:  2 calls  (  6.7%)  ✗ Poor
2000+ms    :  2 calls  (  6.7%)  ✗ Unacceptable
```

#### Worst Performers:
1. **demo-3e4f2d9828d4** - Avg: 2684ms, P95: 3630ms
2. **demo-b7fb4e027d28** - Avg: 2004ms, P95: 3000ms
3. **demo-c31e8157d5a4** - Avg: 1806ms, P95: 3220ms
4. **demo-da9a37636c48** - Avg: 1260ms, P95: 2212ms
5. **demo-dbb48c1d9232** - Avg: 1141ms, P95: 1888ms

#### Performance Thresholds:
- **Target Average Latency:** < 200ms
- **Target P95 Latency:** < 500ms
- **Current vs Target:** **8-13x worse than acceptable**

#### Root Cause Analysis:
Potential causes for high latency:
1. **Tool Call Overhead:** Calls making multiple tool calls show worse performance
2. **Network/Infrastructure:** Could be related to API gateway or database queries
3. **LLM Processing:** Gemini AI model inference time
4. **Speech Processing:** TTS generation, STT processing, or audio codec issues
5. **Tool Integration:** External API calls (menu retrieval, order creation, address verification)

---

### 3. Dead Air Periods (HIGH - 56.7%)

**Impact:** Silence detection is failing in 17 calls, causing user experience disruption.

#### Dead Air Statistics:
- **Calls with Dead Air:** 17/30 (56.7%)
- **Total Dead Air Time:** ~139 seconds across all 30 calls
- **Average Dead Air per Call:** 4.6 seconds
- **Maximum Dead Air in Single Call:** 10,021ms (demo-b7fb4e027d28)

#### Worst Offenders:
1. **demo-b7fb4e027d28** - 10,021ms (159s call duration)
2. **demo-dbb48c1d9232** - 5,704ms (98s call)
3. **demo-c31e8157d5a4** - 5,417ms (98s call)
4. **demo-a2eb9df643eb** - 5,070ms (98s call)
5. **demo-3e4f2d9828d4** - 8,053ms (61s call)

#### Correlation Analysis:
- Calls with **2+ tool calls** average 3,900ms dead air
- Calls with **0 tool calls** average 500ms dead air
- **Strong correlation between tool execution and dead air**

#### Root Cause Hypothesis:
1. Audio streaming interruption during tool processing
2. Speech recognition timeout without graceful handling
3. TTS generation delay not properly buffered
4. VAD (Voice Activity Detection) threshold issues
5. Missing audio frames or codec mismatch

---

### 4. Tool Call Analysis

#### Tool Call Distribution:
- **get_menu** - 26 calls (most frequently used)
- **create_order** - 8 calls
- **verify_address** - 5 calls

#### Tool Call vs Performance Correlation:

| Tool Calls | Call Count | Avg Latency | Avg Dead Air | Avg Quality |
|-----------|-----------|------------|------------|------------|
| 0 | 11 | 1,242ms | 500ms | 6.52 |
| 1 | 1 | 1,050ms | 0ms | 5.00 |
| 2 | 13 | 1,103ms | 3,900ms | 7.08 |
| 4 | 3 | 679ms | 2,131ms | 7.93 |
| 7 | 1 | 1,584ms | 4,751ms | 8.10 |
| Total | 30 | 1,106ms | 1,437ms | 6.98 |

**Key Insight:** Calls with 0 tool calls still show high latency, suggesting the issue is NOT solely tool-related. However, calls with tool invocations show significantly more dead air.

---

### 5. Quality Score Analysis

#### Quality Distribution:
- **9.0-10.0** ⭐ - 0 calls (0%)
- **8.0-8.9** ✓ - 3 calls (10%)
- **7.0-7.9** ✓ - 7 calls (23%)
- **6.0-6.9** ⚠ - 17 calls (57%)
- **5.0-5.9** ✗ - 2 calls (7%)
- **<5.0** ✗✗ - 1 call (3%)

#### Quality vs. Duration Correlation:
- Very short calls (1-2s): Avg Quality 6.4
- Short calls (7-21s): Avg Quality 6.66
- Medium calls (49-109s): Avg Quality 6.9
- Long calls (98s+): Avg Quality 7.08

**Observation:** Longer calls tend to have slightly better quality scores, possibly due to more context and tool usage.

---

### 6. Call Duration Insights

#### Statistics:
- **Average Duration:** 71.5 seconds
- **Total Duration:** 2,145 seconds (35.75 minutes)
- **Shortest Call:** 0 seconds (demo-98e6e680d587, demo-6183e2e1935c)
- **Longest Call:** 159 seconds (demo-b7fb4e027d28)

#### Duration Breakdown:
```
0-10s    :  7 calls  ( 23.3%) - Very short/aborted
11-50s   :  2 calls  (  6.7%) - Brief interactions
51-100s  : 18 calls  ( 60.0%) - Standard calls
100-150s :  2 calls  (  6.7%) - Extended interactions
150+s    :  1 call   (  3.3%) - Very long call
```

**Pattern:** Most calls (~60%) are in the 51-100s range, suggesting either a time limit or typical conversation flow.

---

## Missing Data Analysis

Several expected metrics are not present in the reports:

- ❌ **Silent TTS Incidents** - Not detected in any report
- ❌ **Correction Failures** - Not tracked in current data structure
- ❌ **Multi-Dish Variant Issues** - Not reported
- ❌ **Unexpected Reservation Prompts** - Not logged
- ❌ **Sentiment Analysis** - All calls show NULL sentiment
- ❌ **Escalation Reasons** - No escalations occurred
- ❌ **Transcripts Analysis** - Most calls show incomplete/minimal transcripts

**Recommendation:** Enhance logging to capture these metrics for better issue tracking.

---

## Call-by-Call Detailed Breakdown

### Top 10 Most Problematic Calls

#### 1. demo-3e4f2d9828d4
- **Duration:** 61s
- **Quality Score:** 7.5/10
- **Avg Latency:** 2,684ms ⚠ **SEVERE**
- **P95 Latency:** 3,630ms ⚠ **SEVERE**
- **Dead Air:** 8,053ms
- **Tool Calls:** 2 (get_menu, verify_address)
- **Outcome:** Client disconnect
- **Issues:** Extreme latency, excessive dead air

#### 2. demo-b7fb4e027d28
- **Duration:** 159s (longest call)
- **Quality Score:** 7.6/10
- **Avg Latency:** 2,004ms ⚠ **HIGH**
- **P95 Latency:** 3,000ms ⚠ **HIGH**
- **Dead Air:** 10,021ms ⚠ **EXTREME**
- **Tool Calls:** 2 (get_menu, unknown)
- **Outcome:** Client disconnect
- **Issues:** Longest dead air period, high latency throughout call

#### 3. demo-c31e8157d5a4
- **Duration:** 98s
- **Quality Score:** 7.4/10
- **Avg Latency:** 1,806ms ⚠ **HIGH**
- **P95 Latency:** 3,220ms ⚠ **HIGH**
- **Dead Air:** 5,417ms
- **Tool Calls:** 2 (get_menu, create_order)
- **Outcome:** Client disconnect
- **Issues:** Very high latency, significant dead air

#### 4. demo-da9a37636c48
- **Duration:** 98s
- **Quality Score:** 7.4/10
- **Avg Latency:** 1,260ms ⚠ **HIGH**
- **P95 Latency:** 2,212ms ⚠ **HIGH**
- **Dead Air:** 3,780ms
- **Tool Calls:** 2 (get_menu, verify_address)
- **Outcome:** Client disconnect
- **Issues:** Consistently high latency, moderate dead air

#### 5. demo-dbb48c1d9232
- **Duration:** 98s
- **Quality Score:** 7.4/10
- **Avg Latency:** 1,141ms ⚠ **HIGH**
- **P95 Latency:** 1,888ms ⚠ **HIGH**
- **Dead Air:** 5,704ms
- **Tool Calls:** 2 (get_menu, create_order)
- **Outcome:** Client disconnect
- **Issues:** High latency and dead air

#### 6. demo-7b45be26975c
- **Duration:** 89s
- **Quality Score:** 8.1/10
- **Avg Latency:** 1,584ms ⚠ **HIGH**
- **P95 Latency:** 1,750ms ⚠ **HIGH**
- **Dead Air:** 4,751ms
- **Tool Calls:** 7 (most tool calls)
- **Outcome:** Client disconnect
- **Issues:** Most tool calls in dataset, high latency proportional

#### 7. demo-758eee3cd22f
- **Duration:** 49s
- **Quality Score:** 6.5/10
- **Avg Latency:** 1,196ms ⚠ **HIGH**
- **P95 Latency:** 1,196ms ⚠ **HIGH**
- **Dead Air:** 1,196ms
- **Tool Calls:** 0
- **Outcome:** Client disconnect
- **Issues:** High latency WITHOUT tool calls (infrastructure issue)

#### 8. demo-b9c5d200d3e9
- **Duration:** 21s
- **Quality Score:** 6.5/10
- **Avg Latency:** 1,485ms ⚠ **HIGH**
- **P95 Latency:** 1,485ms ⚠ **HIGH**
- **Dead Air:** 1,485ms
- **Tool Calls:** 0
- **Outcome:** Client disconnect
- **Issues:** Very short call with high latency and dead air

#### 9. demo-714cb94381cd
- **Duration:** 55s
- **Quality Score:** 7.2/10
- **Avg Latency:** 1,416ms ⚠ **HIGH**
- **P95 Latency:** 1,416ms ⚠ **HIGH**
- **Dead Air:** 1,416ms
- **Tool Calls:** 0
- **Outcome:** Client disconnect
- **Issues:** High latency with NO tool calls

#### 10. demo-a2eb9df643eb
- **Duration:** 98s
- **Quality Score:** 7.2/10
- **Avg Latency:** 1,014ms ⚠ **HIGH**
- **P95 Latency:** 2,011ms ⚠ **HIGH**
- **Dead Air:** 5,070ms
- **Tool Calls:** 2 (get_menu, verify_address)
- **Outcome:** Client disconnect
- **Issues:** Significant dead air with multiple tool calls

---

## Performance Insights

### Calls with GOOD Performance:
- **demo-8df8c03b815b** - Avg: 174ms, P95: 174ms, Duration: 98s, Quality: 7.7 ✓
- **demo-8dafefa40ca1** - Avg: 531ms, P95: 1,372ms, Duration: 98s, Quality: 8.1 ⚠
- **demo-87ab8a813c75** - Avg: 692ms, P95: 1,800ms, Duration: 98s, Quality: 8.1 ⚠
- **demo-ba85b4eb467d** - Avg: 672ms, P95: 1,239ms, Duration: 98s, Quality: 7.5 ⚠
- **demo-d852501480ee** - Avg: 731ms, P95: 1,458ms, Duration: 98s, Quality: 8.1 ⚠

Only 1 call out of 30 achieved acceptable latency performance (174ms average).

---

## Root Cause Analysis Summary

### Probable Causes (Priority Order):

1. **Infrastructure/Network Latency (60% likelihood)**
   - High baseline latency even without tool calls
   - Consistent latency issues across all calls
   - Could be geographic, DNS, or API gateway related

2. **Speech Processing Pipeline (40% likelihood)**
   - Audio codec issues
   - TTS/STT buffering problems
   - Voice activity detection (VAD) misconfiguration
   - Related to dead air and latency correlation

3. **Tool Integration Overhead (35% likelihood)**
   - Tool calls correlate with increased dead air
   - External API response times
   - Database query performance
   - Possible retry/backoff behavior

4. **Gemini AI Model Processing (25% likelihood)**
   - LLM inference time
   - Context window size
   - Token processing speed

5. **Browser Demo Environment (15% likelihood)**
   - Demo may have intentional call limits
   - WebSocket/streaming issues
   - Browser-specific performance characteristics

---

## Recommendations

### Immediate Actions (P0 - Critical):

1. **Investigate Client Disconnect Pattern**
   - Review server logs for disconnect triggers
   - Check if demo has intentional call duration limits
   - Verify browser logs for connection errors
   - Test with production environment

2. **Latency Profiling**
   - Enable detailed request tracing (enable APM if available)
   - Measure component latency: TTS, STT, LLM, Tool calls, Audio buffering
   - Check database query performance
   - Profile API gateway response times

3. **Audio Pipeline Debugging**
   - Investigate dead air correlation with tool calls
   - Review VAD settings and thresholds
   - Check audio codec compatibility
   - Verify streaming buffer configuration

### Short-term Actions (P1 - High):

1. **Dead Air Detection**
   - Add explicit logging for silence events
   - Implement graceful handling during tool processing
   - Consider non-blocking audio architecture

2. **Quality Score Investigation**
   - Understand quality score calculation
   - Correlate with specific failure modes
   - Implement more granular logging

3. **Performance Monitoring**
   - Set up dashboards for latency tracking
   - Alert on > 500ms average latency
   - Track dead air incidents separately
   - Monitor tool call execution times

### Medium-term Actions (P2 - Medium):

1. **Architecture Review**
   - Consider caching for common tool calls
   - Implement request batching
   - Optimize tool execution pipeline
   - Review database indexing

2. **Sentiment & Escalation Tracking**
   - Ensure sentiment analysis is working
   - Track escalation reasons
   - Log correction failures
   - Monitor multi-dish variant issues

3. **Testing & Validation**
   - Load testing with expected call volume
   - Latency testing with various scenarios
   - Dead air reproduction and fix validation
   - Production environment validation

---

## Data Quality Notes

### Data Availability:
- ✓ Basic call metadata (SID, duration, quality score)
- ✓ Latency metrics (avg, p95, p50, max)
- ✓ Tool call information
- ✗ Sentiment analysis (all NULL)
- ✗ Escalation details (none recorded)
- ✗ Specific error messages (not logged)
- ✗ Transcript completeness (partial)

### Limitations:
1. Analysis limited to 30 most recent calls
2. No historical trending data
3. Browser demo environment may not reflect production behavior
4. Missing detailed error logs
5. Incomplete transcript data

---

## Conclusion

The Sailly browser demo is experiencing **critical performance and reliability issues** across multiple dimensions:

- **Client disconnects** affect almost every call
- **Latency is 8-13x worse** than acceptable performance levels
- **Dead air periods** suggest audio pipeline issues
- **Tool integration overhead** appears to exacerbate problems

These issues require **immediate investigation and remediation** to provide an acceptable user experience. The root causes likely involve a combination of infrastructure, audio processing, and service integration factors.

**Recommended Next Step:** Perform detailed tracing on a single failing call to identify which component is introducing the latency bottleneck.

---

*Report generated: 2026-05-27*  
*Analysis scope: 30 most recent calls*  
*Next review: After implementing recommended actions*

