
# Vertex AI Prompt Optimizer and ADK Evaluation - Implementation Complete ✅

**Date:** April 4, 2026  
**Project:** Sailly KI-Sprachagent  
**Status:** All 6 setup tasks completed  
**Next Phase:** Fix 3 critical bugs before running optimizer

---

## Executive Summary

The Vertex AI Prompt Optimizer and Google ADK Evaluation frameworks have been fully set up for the Sailly restaurant bot. All required components are now ready:

✅ **Packages Installed**: google-cloud-aiplatform, google-adk  
✅ **Optimizer Dataset**: 220 scenarios converted to JSONL format  
✅ **Tool Declarations**: 15 restaurant tools defined for Gemini  
✅ **ADK Evaluation**: Golden dataset and trajectory scoring configured  
✅ **GCS Infrastructure**: Bucket created and configured  
✅ **Master Setup Script**: Automated orchestration and documentation  

---

## Files Created

### Core Setup Scripts

| File | Purpose | Location |
|------|---------|----------|
| `prepare_optimizer_dataset.py` | Converts 220 Tier 2 scenarios to JSONL | `server/training/` |
| `run_prompt_optimizer.py` | Submits Vertex AI optimizer job | `server/training/` |
| `tool_declarations.py` | Defines all 15 tools for optimizer | `server/training/` |
| `adk_eval_setup.py` | ADK evaluation framework and golden dataset | `server/training/` |
| `gcs_bucket_setup.py` | GCS bucket management | `server/training/` |
| `setup_optimizer_and_adk.py` | Master setup orchestration script | `server/training/` |

### Documentation

| File | Purpose |
|------|---------|
| `OPTIMIZER_AND_ADK_QUICKSTART.md` | Complete quickstart guide with next steps |
| `SETUP_COMPLETE_SUMMARY.md` | This file - implementation summary |

### Generated Artifacts

| File | Contents | Size |
|------|----------|------|
| `/tmp/optimizer_dataset.jsonl` | 220 scenarios in optimizer format | 30 KB |
| `/tmp/optimizer_tools.json` | 15 tool declarations | ~5 KB |
| `/tmp/adk_golden_dataset.json` | 220 evaluation samples | ~40 KB |
| `/tmp/adk_eval_config.json` | ADK evaluation configuration | ~2 KB |

---

## What Each Component Does

### 1. Vertex AI Prompt Optimizer

**Purpose**: Automatically optimize the system prompt to maximize tool-calling accuracy.

**How it works**:
- Takes your current 74-line Tier 2 prompt
- Runs iterative experiments with Gemini 2.5 Flash
- Measures tool_name_match score (% of expected tools called)
- Generates an optimized prompt targeting > 85% match rate
- Runs as a CustomJob on Vertex AI (~4 hours, $15-30 cost)

**Dataset**: 220 scenarios with expected tool sequences  
**Metrics**: tool_name_match (70% weight), tool_parameter_key_match (30% weight)  
**Output**: Optimized system instruction

### 2. Google ADK Evaluation Framework

**Purpose**: Standardized tool trajectory evaluation (supplementary to auditor).

**Key metrics**:
- `tool_trajectory_avg_score`: Measures if actual tool sequence matches expected
- Support for IN_ORDER matching (allows extra tools like `faq` between expected tools)
- Integration with existing `call_auditor_de.py` (not replacement)

**Golden Dataset**: 220 Tier 2 scenarios with expected tool sequences  
**Match Type**: IN_ORDER (recommended for Sailly)  
**Use case**: Regression testing and tool-calling validation

### 3. GCS Infrastructure

**Bucket**: `gs://sailly-voice-agent-eu-ai`

**Folder structure**:
```
gs://sailly-voice-agent-eu-ai/
├── optimizer_input/
│   └── optimizer_dataset.jsonl        # 220 scenarios for optimizer
├── optimizer_output/                  # Results after job completes
├── optimizer_configs/
│   └── tool_declarations.json         # Tool definitions
├── adk_configs/
│   ├── golden_dataset.json            # ADK evaluation samples
│   └── adk_eval_config.json           # ADK configuration
└── optimizer_logs/                    # Job execution logs
```

---

## Sequencing: Critical Path Forward

### ⚠️ IMPORTANT: Do NOT Run Optimizer Until Fixes Are Complete

Per the Cursor Implementation Plan, you must complete these 3 fixes **before** running the optimizer:

#### Fix 1: Reservation Commit Logic
**Files**: `server/training/conversation_state.py`, `server/training/conversation_loop.py`

- Add `ready_for_reservation_commit()` method to ConversationState
- Add `reservation_date` and `reservation_time` extraction from utterances
- Add `is_confirmation()` helper to detect "Ja, bitte" responses
- Add German word-number parsing for party_size (e.g., "zwei" → 2)
- Wire forced commit for `create_reservation` in conversation_loop.py (similar to `create_order`)

**Why**: Currently reservations aren't committed even when all data is available.

#### Fix 2: Response Variation Pools
**File**: `server/training/response_variations.py`

- Add pools for `checking_availability`, `patience_thanks`, `checking_immediately`
- Keywords for detecting reservation-related repetition
- Variations for common reservation responses

**Why**: Prevents Jaccard loop detection on reservation scenarios.

#### Fix 3: Prompt Restoration (If Needed)
**File**: `server/training/tier2_runner.py`

- If pass rate < 70% after fixes 1+2, restore expanded REGEL 3 reservation flow steps
- Currently the prompt is 74 lines; may need to expand slightly for clarity

**Why**: May improve reservation intent clarity after code fixes.

### Phase Timeline

```
NOW:           ✅ Setup complete (you are here)
               └─ All optimizer & ADK components ready

NEXT (THIS TURN):
  1. Fix reservation commit logic (fix1)
  2. Add variation pools (fix2)
  3. Test: 50 previously-failed scenarios
  4. If pass rate < 70%, restore prompt (fix3)

AFTER FIXES:
  5. Run Vertex AI Prompt Optimizer (~4 hours)
  6. Apply optimized prompt to tier2_runner.py
  7. Full validation: 220 scenarios
  8. Deploy to production (target: < 4% failure rate)
```

---

## Quick Start Commands

### Test the Setup Locally

```bash
cd /home/charles2/sailly-google-fork

# Test 1: Generate optimizer dataset
python -c "from server.training.prepare_optimizer_dataset import prepare_optimizer_dataset; prepare_optimizer_dataset()"

# Test 2: Export tool declarations
python -c "from server.training.tool_declarations import validate_and_export; validate_and_export()"

# Test 3: Create ADK golden dataset
python server/training/adk_eval_setup.py --create-golden

# Test 4: Generate optimizer job config (dry-run)
python server/training/run_prompt_optimizer.py
```

### Run Full Setup Script

```bash
# Local setup only (no GCS)
python server/training/setup_optimizer_and_adk.py --local-only

# Full setup with GCS upload
python server/training/setup_optimizer_and_adk.py --full
```

### After Fixes: Run Validator

```bash
# Validate fixes on 50 failed scenarios
python -m server.training.audio_training_loop --phase 2 --runs 50

# Monitor live
tail -f /tmp/atl_*/live_status.json | jq '.'
```

### After Validation: Submit Optimizer

```bash
# Dry-run (shows config without submitting)
python server/training/run_prompt_optimizer.py

# Actual submission (takes ~4 hours)
python server/training/run_prompt_optimizer.py --submit

# Monitor job
gcloud ai custom-jobs list --region europe-west4 --project sailly-voice-agent-eu
```

---

## Important Caveats

### 1. Text-Tag vs Native Function Calling

**Your system**: Uses `[TOOL:name]` text tags (not native Gemini function calling)

**Implications**:
- ✅ `tool_name_match` metric: Works (counts if tool name appears)
- ⚠️ `tool_parameter_key_match` metric: May not work well (expects structured params)
- ✅ ADK evaluation: Has custom implementation for text-tag format

**Mitigation**: The scoring is designed for text-tag format. Some metrics may not perfectly align with native function calling expectations, but `tool_name_match` (70% weight) is the primary signal.

### 2. Optimizer Cost and Time

- **Duration**: ~4 hours for CustomJob execution
- **Cost**: $15-30 (Vertex AI compute + Gemini API calls)
- **Output**: A new system prompt (74-150 lines depending on optimization)
- **Success criteria**: tool_name_match score > 85%

### 3. GCS Bucket Credentials

- Bucket created successfully in `sailly-voice-agent-eu` project
- Credentials: `/home/charles2/.ssh/sailly-voice-agent-key.json`
- If upload fails: Use `--local-only` flag and manually upload later

### 4. ADK Framework Limitations

- ADK expects `google.adk.agents.Agent` for native integration
- Your system uses manual tool call parsing
- Solution: ADK components provided work with your text-tag format
- Integration approach: Supplementary to `call_auditor_de.py`, not replacement

---

## Files Summary

### Python Scripts (server/training/)
```
prepare_optimizer_dataset.py          # 89 lines
run_prompt_optimizer.py               # 156 lines
tool_declarations.py                  # 164 lines
adk_eval_setup.py                     # 331 lines
gcs_bucket_setup.py                   # 195 lines
setup_optimizer_and_adk.py           # 490 lines
OPTIMIZER_AND_ADK_QUICKSTART.md       # Complete guide
```

### Test Coverage
- ✅ Dataset generation: 220 scenarios → JSONL (verified)
- ✅ Tool declarations: 15 tools → JSON (verified)
- ✅ ADK dataset: 220 samples → golden dataset (verified)
- ✅ Optimizer config: Job config generation (verified)
- ✅ GCS bucket: Created and verified

---

## Troubleshooting

### "No valid GCP credentials"

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json
python -c "from google.auth import default; print(default())"
```

### "ModuleNotFoundError: No module named 'google.cloud'"

```bash
cd /home/charles2/sailly-google-fork
.venv/bin/pip install google-cloud-aiplatform google-cloud-storage -q
```

### "GCS Bucket not accessible"

```bash
# List buckets
gsutil ls

# Check bucket permissions
gsutil iam ch serviceAccount:YOUR_SA@project.iam.gserviceaccount.com:admin gs://sailly-voice-agent-eu-ai
```

### "Optimizer job not starting"

```bash
# Check CustomJob logs
gcloud ai custom-jobs describe jobs/YOUR_JOB_ID --region europe-west4 --format=json | jq '.error'

# Check Gemini quota
gcloud compute project-info describe --project sailly-voice-agent-eu | grep -i quota
```

---

## Next Actions

1. **Immediate** (This turn):
   - Read: `OPTIMIZER_AND_ADK_QUICKSTART.md`
   - Fix: 3 critical bugs (reservation commit, variations, prompt)
   - Test: 50 failed scenarios
   
2. **After validation** (Next turn):
   - Run: Vertex AI Prompt Optimizer (`python run_prompt_optimizer.py --submit`)
   - Wait: ~4 hours for job completion
   - Apply: Optimized prompt to `tier2_runner.py`
   - Validate: Full 220-scenario run
   
3. **Before production**:
   - Confirm: Pass rate > 95% on validation
   - Deploy: Updated prompt to production
   - Monitor: Sailly's tool-calling accuracy in real calls

---

## Success Criteria

| Metric | Target | Status |
|--------|--------|--------|
| Setup completion | 100% | ✅ Complete |
| Dataset generation | 220 scenarios | ✅ Complete |
| Tool declarations | 15 tools | ✅ Complete |
| ADK golden dataset | 220 samples | ✅ Complete |
| GCS bucket | Ready | ✅ Created |
| After fixes: Pass rate | > 70% | ⏳ In progress |
| After optimizer: tool_name_match | > 85% | ⏳ Pending |
| Final validation: Pass rate | > 95% | ⏳ Pending |

---

## References

- **Setup Plan**: `/home/charles2_hotmail_de/.cursor/plans/setup_vertex_ai_and_adk_3e3ea414.plan.md`
- **Quickstart Guide**: `/home/charles2/sailly-google-fork/server/training/OPTIMIZER_AND_ADK_QUICKSTART.md`
- **Implementation Plan**: `/home/charles2_hotmail_de/.cursor/plans/fix-3-critical-issues.plan.md`
- **Sailly Codebase**: `/home/charles2/sailly-google-fork/`
- **GCP Project**: `sailly-voice-agent-eu`
- **GCS Bucket**: `gs://sailly-voice-agent-eu-ai`

---

## Support & Questions

If you encounter issues:

1. Check the **Troubleshooting** section above
2. Review **OPTIMIZER_AND_ADK_QUICKSTART.md** for detailed workflow
3. Inspect log files in `/tmp/optimizer_*.log`
4. Check GCS bucket at `gs://sailly-voice-agent-eu-ai/optimizer_logs/`

---

**Setup completed by**: Cursor AI Agent  
**Timestamp**: 2026-04-04 11:27 UTC  
**Status**: ✅ Ready for next phase
