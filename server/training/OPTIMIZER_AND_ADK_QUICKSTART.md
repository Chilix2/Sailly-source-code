
# Vertex AI Prompt Optimizer & ADK Evaluation Quickstart

## What's Been Set Up

1. ✅ **Packages Installed**
   - google-cloud-aiplatform: Vertex AI SDK
   - google-adk: Google Agent Development Kit

2. ✅ **Optimizer Components Created**
   - `prepare_optimizer_dataset.py`: Converts 220 scenarios to JSONL format
   - `run_prompt_optimizer.py`: Submits optimizer job to Vertex AI
   - `tool_declarations.py`: Defines all 15 restaurant tools
   - Dataset: `/tmp/optimizer_dataset.jsonl` (220 scenarios)
   - Tools config: `/tmp/optimizer_tools.json`

3. ✅ **ADK Evaluation Components**
   - `adk_eval_setup.py`: ADK evaluation framework
   - `tool_declarations.py`: Tool declarations for ADK
   - Golden dataset: `/tmp/adk_golden_dataset.json` (220 scenarios)
   - Config: `/tmp/adk_eval_config.json`

4. ✅ **GCS Infrastructure**
   - Bucket: gs://sailly-voice-agent-eu-ai
   - Paths:
     - optimizer_input/ — Input datasets
     - optimizer_output/ — Results after optimization
     - optimizer_configs/ — Tool declarations and configs
     - adk_configs/ — ADK golden datasets and configs
     - optimizer_logs/ — Job logs

## Next Steps (IMPORTANT SEQUENCING)

### Phase 1: Fix the 3 Critical Bugs (BEFORE running optimizer)

Per the Cursor Implementation Plan, you must fix these issues first:

1. **fix1-reservation-commit**: Add `ready_for_reservation_commit()` to ConversationState
   - File: `server/training/conversation_state.py`
   - Add: `reservation_date` and `reservation_time` extraction
   - Add: `is_confirmation()` helper
   - Add: German word-number parsing for `party_size`

2. **fix2-variation-pools**: Add reservation-specific response variations
   - File: `server/training/response_variations.py`
   - Add: `checking_availability`, `patience_thanks`, `checking_immediately` pools

3. **fix3-prompt-if-needed**: Verify Tier 2 prompt if pass rate < 70%
   - File: `server/training/tier2_runner.py`
   - Restore REGEL 3 reservation flow steps if needed

### Phase 2: Run Validation After Fixes

```bash
cd /home/charles2/sailly-google-fork

# Test the fixes with 50 failed scenarios
python -m server.training.audio_training_loop --phase 2 --runs 50 --scenarios previous_failures

# Monitor results
tail -f /tmp/atl_*/live_status.json | jq '.'
```

### Phase 3: Run Vertex AI Prompt Optimizer (After validation passes > 70%)

```bash
cd /home/charles2/sailly-google-fork

# Option A: Dry-run to verify config
python server/training/run_prompt_optimizer.py

# Option B: Actually submit the job (takes ~4 hours)
python server/training/run_prompt_optimizer.py --submit

# Monitor job status
gcloud ai custom-jobs list --region europe-west4 --project sailly-voice-agent-eu
```

### Phase 4: Apply Optimized Prompt

After the optimizer completes:

```bash
# 1. Download optimized prompt from GCS
gsutil cp gs://sailly-voice-agent-eu-ai/optimizer_output/optimized_prompt.txt /tmp/

# 2. Replace in tier2_runner.py
cp /tmp/optimized_prompt.txt server/training/tier2_runner.py

# 3. Validate with ADK
python server/training/adk_eval_setup.py --validate-against-optimized

# 4. Run full training loop
python -m server.training.audio_training_loop --phase 2 --runs 220
```

## Files Created

```
server/training/
  ├── prepare_optimizer_dataset.py    # Generate JSONL dataset for optimizer
  ├── run_prompt_optimizer.py         # Submit Vertex AI job
  ├── tool_declarations.py            # Tool definitions for optimizer
  ├── adk_eval_setup.py               # ADK evaluation framework
  └── gcs_bucket_setup.py             # GCS bucket management

/tmp/
  ├── optimizer_dataset.jsonl         # 220 scenarios in optimizer format
  ├── optimizer_tools.json            # Tool declarations
  ├── adk_golden_dataset.json         # 220 scenarios for ADK
  └── adk_eval_config.json            # ADK evaluation config
```

## Important Caveats

### Text-Tag vs Native Function Calling

Your system uses `[TOOL:name]` text tags, not native Gemini function calling. This means:

- ✅ The `tool_name_match` metric will work (counts if tool name appears)
- ⚠️ The `tool_parameter_key_match` metric may not work (native function calling)
- ✅ The ADK evaluation provides a custom implementation that works with text tags

### Optimizer Runtime & Costs

- **Duration**: ~4 hours for a CustomJob on Vertex AI
- **Cost**: Compute VM + Gemini API calls during optimization
  - Estimate: $15–30 depending on model and iteration count
- **Output**: Optimized system instruction (74 lines → ??)
- **Metric**: tool_name_match score improvement (target: > 85%)

### ADK Evaluation

- **In your workflow**: Supplementary to `call_auditor_de.py`, not replacement
- **What it adds**: Standardized tool trajectory scoring (`IN_ORDER` mode)
- **Integration**: Can run alongside existing auditor or as standalone

## Troubleshooting

### Credentials Error

```bash
# Set credentials file
export GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json

# Verify
python -c "from google.auth import default; print(default())"
```

### GCS Bucket Not Found

```bash
# List buckets
gsutil ls

# Create new bucket
gsutil mb gs://new-bucket-name
```

### Optimizer Job Not Starting

```bash
# Check logs
gcloud ai custom-jobs describe jobs/JOB_ID --region europe-west4

# Check Gemini quotas
gcloud compute project-info describe --project sailly-voice-agent-eu
```

## Contact & Support

- Documentation: `/home/charles2/sailly-google-fork/server/training/`
- Plan: `/home/charles2_hotmail_de/.cursor/plans/setup_vertex_ai_and_adk_3e3ea414.plan.md`
- Issues: Check `/tmp/optimizer_*.log` for job details
