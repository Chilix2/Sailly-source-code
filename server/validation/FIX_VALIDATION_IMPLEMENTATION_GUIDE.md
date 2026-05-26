# Fix Validation Loop Implementation Guide

## Status: ✅ Ready to Integrate

**Latest Version**: April 11, 2026 @ 02:53 UTC  
**Source**: Archived from `sailly-google-fork_ARCHIVED_2026-04-20/training_backup_20260411_025359/`  
**Files Location**: `/home/charles2/sailly-browser-demo/server/validation/`

---

## Files Available

### Core Files (Copied to Current Repo)
1. **`fix_validation_loop.py`** (42 KB, 970 lines)
   - Main fix validation orchestrator
   - Runs scenarios through ADKRunner + auditor (script-only, no audio)
   - Validates across 12 failure buckets
   - 3-step gate validation per bucket (Step 1, 2, 3)
   - Tier 1 (100% required) and Tier 2 (60% required) thresholds
   - Generates real-time HTML dashboard
   - Saves JSON state/results for monitoring

2. **`ab_test_loop.py`** (69 KB)
   - Supporting A/B test loop framework
   - Runner pool + auditor integration
   - Cost tracking + performance metrics

### Supporting Files (From Archive, Use as Reference)
- `fix_validation_buckets.py` — Bucket definitions
- `fix_validation_scenarios.py` — Scenario loaders
- `call_auditor_de.py` — German call auditing logic
- `ab_test_scenarios.py` — Scenario helpers

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  loop_runner_v2.py (ORCHESTRATOR)                          │
│  - Sentinel early-exit                                     │
│  - Cascade collapse clustering                             │
│  - Surgical fix ordering (by dependency depth)             │
│  - One-fix-at-a-time with smoke gate                       │
│  - LLM-as-Judge (Haiku validates Opus fixes)               │
│  - Atomic patch + auto-revert                              │
│  - Heartbeat + watchdog monitoring                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  fix_validation_loop.py (TEST RUNNER - SCRIPT ONLY)        │
│  - No audio, no Grok calls                                 │
│  - Uses ADKRunner + Tier2AudioRunner (Google Gemini)       │
│  - Audits calls via call_auditor_de.py                     │
│  - Tracks 12 failure buckets                               │
│  - Step-gated validation (Step 1 → Step 2 → Step 3)        │
│  - Returns pass_rate per bucket                            │
│  - Generates JSON results + HTML dashboard                 │
└─────────────────────────────────────────────────────────────┘
```

---

## How It Works

### Step 1: Initialize FixValidationLoop
```python
from server.validation.fix_validation_loop import FixValidationLoop

loop = FixValidationLoop(
    output_dir="reports",
    max_concurrent=5,
    call_timeout=60.0,
)
```

### Step 2: Run Validation
```python
import asyncio

results = asyncio.run(
    loop.run_full_validation(
        failed_ids_filter=None,  # or pass failing scenario IDs
        single_bucket=None,      # or run single bucket only
    )
)
```

### Step 3: Check Results
```python
# Results structure:
{
    "status": "completed",  # pending / running / completed
    "buckets": [
        {
            "name": "greeting_fallback",
            "priority": 1,
            "tier": 1,
            "pass_threshold": 1.0,
            "combined_rate": 0.95,  # Step 1+2+3 pass rate
            "status": "validated"    # pending / running / validated / unresolved
        },
        ...
    ],
    "scenario_results": [...],  # Raw pass/fail for each scenario
    "dashboard_url": "file:///tmp/fix_validation_dashboard.html"
}
```

---

## Integration with loop_runner_v2.py

### TODO: Update loop_runner_v2.py

Replace the `_run_scenarios()` function to use `FixValidationLoop`:

```python
async def _run_scenarios(
    phase: str,
    workers: int,
    scenario_ids: Optional[list[str]] = None,
    max_duration_sec: float = 180.0,
) -> list[ScenarioOutcome]:
    """
    Run validation scenarios via FixValidationLoop (script-only, no audio).
    """
    from server.validation.fix_validation_loop import FixValidationLoop
    
    loop = FixValidationLoop(
        output_dir="reports",
        max_concurrent=workers,
        call_timeout=max_duration_sec,
    )
    
    # Run and collect results
    report = await loop.run_full_validation()
    
    # Convert to ScenarioOutcome for clustering
    outcomes = []
    for result in report["scenario_results"]:
        outcomes.append(ScenarioOutcome(
            scenario_id=result["scenario_id"],
            persona=result.get("bucket", "unknown"),
            passed=result["pass"],
            failure_tags=result.get("failures", []),
            last_turns=[],  # Not captured in fix_validation_loop
            duration_s=result.get("duration_s", 0.0),
        ))
    
    return outcomes
```

---

## Key Features

### ✅ Script-Only (No Audio)
- Uses `Tier2AudioRunner` (Google Gemini LLM)
- No Grok/xAI API calls
- No STT/TTS infrastructure
- Runs locally with asyncio

### ✅ 3-Step Gate Validation
Each bucket goes through:
1. **Step 1**: Run 10 scenarios → must pass threshold
2. **Step 2**: Run 10 different scenarios → combined 1+2 must pass
3. **Step 3**: Run 10 more scenarios → combined 1+2+3 must pass

If ANY step fails → retry from Step 1 (max 3 attempts)

### ✅ Tier-Based Thresholds
- **Tier 1** (compliance-critical): 100% pass rate required
- **Tier 2** (quality/reliability): 60% pass rate required

### ✅ Real-Time Dashboard
- HTML dashboard auto-generated
- JSON checkpoint saved after each bucket
- Heartbeat monitoring for watchdog
- Cost tracking (USD per call)

### ✅ Cost Tracking
Each scenario tracks:
- `cost_usd`: Estimated Google API cost
- `latency_ms`: End-to-end duration
- `tools_called`: List of tools invoked

---

## Configuration

### Environment Variables
```bash
# Required for Google Gemini calls
export GCP_PROJECT_ID="sailly-voice-agent-eu"

# Optional
export DEEPGRAM_API_KEY="..."  # If using Deepgram STT
export OPENAI_API_KEY="..."    # For fallback LLM
```

### Runtime Parameters
```python
FixValidationLoop(
    output_dir: str = "reports",           # Where to save results
    max_concurrent: int = 5,               # Asyncio worker pool size
    call_timeout: float = 60.0,            # Per-scenario timeout
    use_checkpoint: bool = True,           # Resume from checkpoint if exists
)
```

---

## Output Files

After running, check:
- `reports/fix_validation_state.json` — Checkpoint (bucket status)
- `reports/fix_validation_scenarios.json` — All scenario results
- `reports/fix_validation_dashboard.html` — Real-time visualization

---

## Next Steps

1. **Test FixValidationLoop in isolation**
   ```bash
   cd /home/charles2/sailly-browser-demo
   python3 -c "
   import asyncio
   from server.validation.fix_validation_loop import FixValidationLoop
   
   loop = FixValidationLoop(output_dir='reports', max_concurrent=3)
   result = asyncio.run(loop.run_full_validation())
   print(f'Status: {result[\"status\"]}')
   print(f'Buckets: {len(result[\"buckets\"])}')
   "
   ```

2. **Integrate into loop_runner_v2.py**
   - Replace `_run_scenarios()` to use FixValidationLoop
   - Keep sentinel, clustering, fix generation, smoke gate logic

3. **Run integrated loop_runner_v2**
   ```bash
   python3 -m server.validation.loop_runner_v2 \
       --phase a \
       --workers 5 \
       --threshold 0.98 \
       --max-attempts 3
   ```

---

## References

- **Latest Version**: `/home/charles2/sailly-browser-demo/server/validation/fix_validation_loop.py`
- **Archive Source**: `/home/charles2/sailly-google-fork_ARCHIVED_2026-04-20/training_backup_20260411_025359/`
- **Documentation**: This file

---

## Version History

| Date | Source | Size | Status |
|------|--------|------|--------|
| Apr 11 02:53 | ARCHIVED_2026-04-20 | 42KB | ✅ Latest (Current) |
| Apr 10 14:24 | ARCHIVED_2026-04-20 | 42KB | Previous |
| Apr 09 16:09 | ARCHIVED_2026-04-20 | 40KB | Older |

---

**Last Updated**: May 4, 2026 @ 20:57 UTC  
**Status**: Ready for Integration ✅
