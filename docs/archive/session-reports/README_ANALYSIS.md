# Call Analysis Report - File Index

**Analysis Date:** May 27, 2026  
**Scope:** 30 most recent calls from Sailly Browser Demo  
**Starting Point:** demo-8008b0d9c01f

---

## 📋 Generated Report Files

This directory contains a comprehensive analysis of call performance issues. Below is a guide to understanding and using these reports.

### 1. **ISSUES_REPORT.md** (Comprehensive Analysis)
   - **Size:** 16KB
   - **Format:** Markdown
   - **Purpose:** Deep-dive technical analysis
   - **Contains:**
     - Executive summary with key findings
     - Detailed issue breakdowns (Client Disconnect, Latency, Dead Air)
     - Tool call analysis and performance correlations
     - Quality score distribution and insights
     - Call duration patterns
     - Missing data analysis
     - Top 10 worst performers (detailed)
     - Best performers showcase
     - Root cause analysis with probability rankings
     - Comprehensive recommendations
   - **Best For:** Understanding technical details, root cause investigation, presenting to engineering team
   - **Read Time:** 15-20 minutes

### 2. **QUICK_REFERENCE.txt** (Executive Summary)
   - **Size:** 13KB
   - **Format:** Text with ASCII formatting
   - **Purpose:** Quick overview and checklist
   - **Contains:**
     - Analysis parameters
     - Critical issues at a glance
     - Key statistics
     - Performance correlation analysis
     - Tool call breakdown
     - Latency breakdown by bucket
     - Top 5 worst and best performers
     - Root cause priority ranking
     - Recommended next steps (prioritized)
   - **Best For:** Quick reference, sharing with stakeholders, checklist usage
   - **Read Time:** 5-10 minutes

### 3. **SUMMARY_STATS.txt** (Executive Dashboard)
   - **Size:** 7.2KB
   - **Format:** Formatted text with visual indicators
   - **Purpose:** High-level metrics overview
   - **Contains:**
     - Critical issues overview with severity levels
     - Performance metrics (current vs target)
     - Key findings summary
     - Worst performers list
     - Best performers list
     - Root cause hypothesis
     - Immediate actions required
     - Output files reference
   - **Best For:** Presentations, executive briefings, dashboards
   - **Read Time:** 3-5 minutes

### 4. **ACTION_ITEMS.md** (Implementation Roadmap)
   - **Size:** 16KB
   - **Format:** Markdown with checkboxes
   - **Purpose:** Actionable task breakdown
   - **Contains:**
     - Issue-by-issue investigation tasks
     - Monitoring setup tasks
     - Architecture optimization tasks
     - Data collection and logging tasks
     - Validation and testing tasks
     - Phase 1-3 implementation timeline
     - Success metrics and targets
     - Reference data and worst performers
   - **Best For:** Project planning, team assignment, progress tracking
   - **Read Time:** 10-15 minutes

### 5. **call_analysis.json** (Structured Data)
   - **Size:** 16KB
   - **Format:** JSON
   - **Purpose:** Programmatic analysis and tooling
   - **Contains:**
     - All 30 calls with complete metrics
     - Issues breakdown by type
     - Statistics summary
   - **Best For:** Data integration, custom analysis, scripting
   - **Fields:**
     - `call_sid`: Call identifier
     - `call_id`: UUID (short form)
     - `started_at`/`ended_at`: Timestamps
     - `duration_seconds`: Call length
     - `quality_score`: 0-10 rating
     - `avg_latency_ms`/`p95_latency_ms`: Latency metrics
     - `total_tool_calls`: Number of tools invoked
     - And more...

---

## 🎯 How to Use These Reports

### For Different Audiences:

**👤 Executive/Manager:**
1. Start with `SUMMARY_STATS.txt` (5 min read)
2. Review critical issues and recommended actions
3. Use `ACTION_ITEMS.md` for timeline and milestones

**👨‍💻 Engineering Team:**
1. Start with `QUICK_REFERENCE.txt` (10 min read)
2. Deep-dive into `ISSUES_REPORT.md` for details
3. Use `ACTION_ITEMS.md` for task assignment
4. Reference `call_analysis.json` for data validation

**📊 Data Analyst:**
1. Review `call_analysis.json` directly
2. Cross-reference with `ISSUES_REPORT.md` for context
3. Create custom queries and charts

**🧪 QA/Testing:**
1. Review worst performers in all reports
2. Use `ACTION_ITEMS.md` for test scenarios
3. Reference specific call IDs for reproduction

---

## 🔴 Critical Issues Summary

| Issue | Count | Severity | Status |
|-------|-------|----------|--------|
| Client Disconnect | 29/30 | CRITICAL | Investigate |
| High Latency | 17/30 | HIGH | Profile Components |
| Dead Air Periods | 17/30 | HIGH | Debug Audio |
| Low Quality | 1/30 | MEDIUM | Monitor |

**Key Metrics:**
- Average Latency: 1,106ms (8.5x target)
- Average Quality: 6.98/10 (below 8.0 target)
- Best Call Performance: 174ms avg latency
- Worst Call Performance: 2,684ms avg latency

---

## 📍 Worst Performing Calls

These calls should be used for reproduction and testing:

1. **demo-3e4f2d9828d4** - Avg: 2,684ms, P95: 3,630ms, Dead Air: 8,053ms
2. **demo-b7fb4e027d28** - Avg: 2,004ms, P95: 3,000ms, Dead Air: 10,021ms ⚠️
3. **demo-c31e8157d5a4** - Avg: 1,806ms, P95: 3,220ms, Dead Air: 5,417ms
4. **demo-da9a37636c48** - Avg: 1,260ms, P95: 2,212ms, Dead Air: 3,780ms
5. **demo-dbb48c1d9232** - Avg: 1,141ms, P95: 1,888ms, Dead Air: 5,704ms

---

## ✅ Best Performing Call

For comparison and target behavior:

- **demo-8df8c03b815b** - Avg: 174ms, P95: 174ms, Quality: 7.7 ✓

---

## 🚀 Immediate Next Steps

1. **Review Server Logs** - Check for disconnect patterns (30 min)
2. **Enable Tracing** - Add APM instrumentation (2 hours)
3. **Profile Components** - Measure TTS, STT, LLM latency (4 hours)
4. **Set Up Dashboard** - Create performance monitoring (2 hours)

**Total Time Estimate:** ~1 day for investigation setup

---

## 📚 Recommended Reading Order

**If you have 5 minutes:**
- SUMMARY_STATS.txt

**If you have 15 minutes:**
- SUMMARY_STATS.txt
- QUICK_REFERENCE.txt (first half)

**If you have 30 minutes:**
- QUICK_REFERENCE.txt
- ACTION_ITEMS.md (Phase 1 section)

**If you have 1-2 hours:**
- All documents in order:
  1. SUMMARY_STATS.txt
  2. QUICK_REFERENCE.txt
  3. ISSUES_REPORT.md
  4. ACTION_ITEMS.md

**If you want deep technical analysis:**
- ISSUES_REPORT.md (complete read)
- call_analysis.json (programmatic exploration)

---

## 🔧 Tools & Scripts

### Extract Call Data
```bash
python3 /tmp/extract_calls.py
```
This script regenerates the analysis from the raw call reports.

### View Raw Call Reports
```bash
cd /home/charles2/sailly-browser-demo/call_reports/
ls -lt *.json | head -30  # Most recent 30
```

### Analyze Specific Call
```bash
cat /home/charles2/sailly-browser-demo/call_reports/demo-3e4f2d9828d4.json
```

---

## 📞 Key Call IDs for Reference

### Best Performers:
- demo-8df8c03b815b (174ms, quality 7.7)
- demo-8dafefa40ca1 (531ms, quality 8.1)
- demo-87ab8a813c75 (692ms, quality 8.1)

### Worst Performers:
- demo-3e4f2d9828d4 (2,684ms, quality 7.5) - START HERE
- demo-b7fb4e027d28 (2,004ms, quality 7.6) - Extreme dead air
- demo-c31e8157d5a4 (1,806ms, quality 7.4) - High latency

### Interesting Cases:
- demo-8008b0d9c01f (1s, quality 6.4) - Very short call
- demo-7b45be26975c (89s, quality 8.1) - 7 tool calls
- demo-98e6e680d587 (0s, quality 5.0) - Recovered orphan

---

## 📊 Data Quality Notes

### Available Metrics:
- ✅ Basic call metadata (SID, duration, quality)
- ✅ Latency metrics (avg, p95, p50, max)
- ✅ Tool call information
- ✅ Outcome/disposition

### Missing Metrics:
- ❌ Sentiment analysis (all NULL)
- ❌ Escalation details (none recorded)
- ❌ Specific error messages
- ❌ Complete transcripts
- ❌ Silent TTS incidents
- ❌ Correction failures

**Recommendation:** Enhance logging to capture missing metrics for better analysis.

---

## 🔄 Update Frequency

This analysis was generated on **May 27, 2026** and represents:
- 30 most recent calls
- Data from May 26, 2026 14:45 - 23:06

**Next Update:** After implementing recommended fixes or when new issues appear.

---

## ❓ Questions & Support

### What do the metrics mean?
- **avg_latency_ms**: Average response time (target: <200ms)
- **p95_latency_ms**: 95th percentile latency (target: <500ms)
- **quality_score**: 0-10 rating (target: >8.0)
- **dead_air_ms**: Silent periods in call (target: <500ms per call)

### How to interpret latency?
- <200ms: ✅ Good
- 200-500ms: ⚠️ Acceptable
- 500-1000ms: 🟡 Borderline
- 1000-2000ms: 🔴 Poor
- >2000ms: 🔴🔴 Unacceptable

### Where to find raw data?
```
/home/charles2/sailly-browser-demo/call_reports/*.json
```

### How to export data?
```bash
# All calls to JSON
python3 /tmp/extract_calls.py

# Single call analysis
cat call_reports/demo-XXXXXXX.json | jq .
```

---

**Generated by:** Call Analysis Tool  
**Analysis Scope:** Sailly Browser Demo (30 most recent calls)  
**Last Updated:** 2026-05-27 23:32 UTC  
**Status:** READY FOR REVIEW

---

For questions or to request additional analysis, contact the engineering team.
