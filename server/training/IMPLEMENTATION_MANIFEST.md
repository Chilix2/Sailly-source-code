
# Implementation Manifest - Vertex AI Prompt Optimizer & ADK Setup

**Status**: ✅ COMPLETE  
**Date**: April 4, 2026  
**All 6 Todos Completed**

---

## ✅ Todo 1: Install Packages

**Status**: COMPLETED  
**Output**: google-cloud-aiplatform, google-adk installed in venv

```bash
cd /home/charles2/sailly-google-fork
.venv/bin/pip install google-cloud-aiplatform google-adk -q
```

**Verification**:
```bash
.venv/bin/python -c "import google.cloud.aiplatform; import google.adk; print('✅ OK')"
```

---

## ✅ Todo 2: Prepare Optimizer Dataset

**Status**: COMPLETED  
**File Created**: `server/training/prepare_optimizer_dataset.py` (107 lines)  
**Artifact Generated**: `/tmp/optimizer_dataset.jsonl` (30 KB, 220 scenarios)

**What It Does**:
- Converts 220 Tier 2 scenarios to JSONL format
- Each row: `{"question": "...", "target": "{...tool_calls...}"}`
- Format compatible with Vertex AI Prompt Optimizer

**Test**:
```bash
cd /home/charles2/sailly-google-fork
.venv/bin/python -c "from server.training.prepare_optimizer_dataset import prepare_optimizer_dataset; prepare_optimizer_dataset()"
```

**Output**:
```
✅ Created dataset with 220 scenarios
   Path: /tmp/optimizer_dataset.jsonl
   Sample row: {...}
```

---

## ✅ Todo 3: Define Tool Declarations

**Status**: COMPLETED  
**File Created**: `server/training/tool_declarations.py` (234 lines)  
**Artifact Generated**: `/tmp/optimizer_tools.json` (5 KB, 15 tools)

**Tools Defined**:
1. get_menu
2. check_availability
3. create_reservation
4. create_order
5. send_sms
6. verify_address
7. technical_issues_callback
8. update_state
9. transfer_to_human
10. transfer_to_ordering
11. transfer_to_tier2
12. get_date_info
13. get_weather
14. end_call
15. faq

**Test**:
```bash
.venv/bin/python -c "from server.training.tool_declarations import validate_and_export; validate_and_export()"
```

**Output**:
```
✅ Tool definitions exported: /tmp/optimizer_tools.json
   Total tools: 15
```

---

## ✅ Todo 4: Create Optimizer Job Config

**Status**: COMPLETED  
**File Created**: `server/training/run_prompt_optimizer.py` (169 lines)

**What It Does**:
- Extracts current 74-line Tier 2 prompt from `tier2_runner.py`
- Builds Vertex AI CustomJob configuration
- Targets `gemini-2.5-flash` model
- Uses `tool_name_match` (70%) and `tool_parameter_key_match` (30%) metrics

**Configuration**:
```json
{
  "base_model": "gemini-2.5-flash",
  "dataset": "gs://sailly-voice-agent-eu-ai/optimizer_input/optimizer_dataset.jsonl",
  "output": "gs://sailly-voice-agent-eu-ai/optimizer_output/",
  "metrics": {
    "tool_name_match": 0.7,
    "tool_parameter_key_match": 0.3
  }
}
```

**Test (Dry-Run)**:
```bash
.venv/bin/python server/training/run_prompt_optimizer.py
```

**Output**: Full job configuration without submission

**Actual Submission** (After Fixes):
```bash
.venv/bin/python server/training/run_prompt_optimizer.py --submit
```

---

## ✅ Todo 5: Setup ADK Evaluation

**Status**: COMPLETED  
**File Created**: `server/training/adk_eval_setup.py` (352 lines)  
**Artifacts Generated**:
- `/tmp/adk_golden_dataset.json` (40 KB, 220 samples)
- `/tmp/adk_eval_config.json` (2 KB)

**What It Does**:
- Defines ADK evaluation framework
- Creates golden dataset from 220 scenarios
- Provides `tool_trajectory_scorer()` for IN_ORDER matching
- Allows integration with `call_auditor_de.py`

**Key Features**:
- **MatchType.IN_ORDER**: Allows extra tools (e.g., `faq`) between expected ones
- **tool_trajectory_avg_score**: Measures tool sequence accuracy
- **EvalSample**: Dataclass for evaluation samples

**Test**:
```bash
.venv/bin/python server/training/adk_eval_setup.py --export-config --create-golden
```

**Output**:
```
✅ ADK evaluation config exported: /tmp/adk_eval_config.json
📊 Creating golden dataset from Tier 2 scenarios...
   Created 220 evaluation samples
   Saved to /tmp/adk_golden_dataset.json
```

---

## ✅ Todo 6: Setup GCS Bucket

**Status**: COMPLETED  
**File Created**: `server/training/gcs_bucket_setup.py` (188 lines)  
**Bucket Created**: `gs://sailly-voice-agent-eu-ai`

**Folder Structure**:
```
gs://sailly-voice-agent-eu-ai/
├── optimizer_input/
│   └── optimizer_dataset.jsonl
├── optimizer_output/
│   └── (results after job completion)
├── optimizer_configs/
│   └── tool_declarations.json
├── adk_configs/
│   ├── golden_dataset.json
│   └── adk_eval_config.json
└── optimizer_logs/
    └── (job execution logs)
```

**Test**:
```bash
.venv/bin/python server/training/gcs_bucket_setup.py --verify
```

**Output**:
```
✅ Bucket exists: gs://sailly-voice-agent-eu-ai
📁 Optimizer Bucket Structure:
   └── optimizer_input/
   └── optimizer_output/
   └── optimizer_configs/
   └── adk_configs/
   └── optimizer_logs/
```

---

## 🎯 Additional Files Created

### Supporting Scripts

| File | Lines | Purpose |
|------|-------|---------|
| `setup_optimizer_and_adk.py` | 455 | Master orchestration script (runs all steps) |
| `verify_setup.py` | 76 | Final verification checklist |

### Documentation

| File | Purpose |
|------|---------|
| `SETUP_COMPLETE_SUMMARY.md` | Comprehensive implementation summary with architecture |
| `OPTIMIZER_AND_ADK_QUICKSTART.md` | Step-by-step guide for next phases |
| `SETUP_COMPLETE_REPORT.txt` | Detailed report with all metrics and timelines |

---

## 🔍 Verification Results

All checks PASSED ✅

```
✅ Python Packages
   ✓ google-cloud-aiplatform
   ✓ google-adk

✅ Setup Scripts (7 created)
   ✓ prepare_optimizer_dataset.py
   ✓ run_prompt_optimizer.py
   ✓ tool_declarations.py
   ✓ adk_eval_setup.py
   ✓ gcs_bucket_setup.py
   ✓ setup_optimizer_and_adk.py
   ✓ verify_setup.py

✅ Documentation (3 files)
   ✓ SETUP_COMPLETE_SUMMARY.md
   ✓ OPTIMIZER_AND_ADK_QUICKSTART.md
   ✓ SETUP_COMPLETE_REPORT.txt

✅ Generated Artifacts (4 files)
   ✓ optimizer_dataset.jsonl (30 KB)
   ✓ optimizer_tools.json (5 KB)
   ✓ adk_golden_dataset.json (40 KB)
   ✓ adk_eval_config.json (2 KB)

✅ GCS Infrastructure
   ✓ Bucket: gs://sailly-voice-agent-eu-ai
   ✓ Folders: optimizer_input/, optimizer_output/, optimizer_configs/, adk_configs/
```

---

## 🚀 Next Immediate Actions

### Phase 1: Fix 3 Critical Bugs (THIS TURN)

Do NOT run optimizer until these are fixed:

1. **Reservation Commit Logic** (conversation_state.py, conversation_loop.py)
   - Add `ready_for_reservation_commit()` method
   - Add date/time extraction
   - Add German word-number parsing
   - Wire forced create_reservation commit

2. **Response Variation Pools** (response_variations.py)
   - Add reservation-specific pools
   - Prevent Jaccard loop detection

3. **Prompt Restoration** (tier2_runner.py, if needed)
   - If pass rate < 70%, restore REGEL 3

### Phase 2: Validate Fixes

```bash
python -m server.training.audio_training_loop --phase 2 --runs 50
```

Target: Pass rate > 70%

### Phase 3: Run Optimizer

```bash
python server/training/run_prompt_optimizer.py --submit
```

Duration: ~4 hours  
Cost: $15-30

### Phase 4: Apply & Validate

1. Download optimized prompt from GCS
2. Replace in tier2_runner.py
3. Run full validation: 220 scenarios
4. Target: Pass rate > 95%

---

## 📋 Checklist Summary

| Item | Status | Evidence |
|------|--------|----------|
| Packages installed | ✅ | Both packages importable |
| Dataset generated | ✅ | 220 scenarios in JSONL format |
| Tool declarations | ✅ | 15 tools defined |
| Optimizer config | ✅ | Job configuration ready |
| ADK framework | ✅ | Golden dataset + config created |
| GCS infrastructure | ✅ | Bucket created and verified |
| Scripts tested | ✅ | All scripts run without errors |
| Documentation | ✅ | 3 comprehensive guides created |
| Verification passed | ✅ | All checks passed |

---

## 🎯 Success Criteria Met

✅ All 6 todo items completed  
✅ 1,505 lines of Python code written  
✅ 3 documentation guides created  
✅ 4 artifact files generated  
✅ GCS bucket created and verified  
✅ All verification checks passed  
✅ Ready for next phase (fix bugs → validate → run optimizer)

---

**Status**: ✅ READY FOR NEXT PHASE  
**Date Completed**: April 4, 2026  
**Next Action**: Fix 3 critical bugs before running optimizer
