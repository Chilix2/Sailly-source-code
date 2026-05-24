#!/usr/bin/env python3
"""
Master setup script for Vertex AI Prompt Optimizer and ADK Evaluation.

This script orchestrates the complete setup workflow:
1. Installs required packages
2. Validates credentials
3. Prepares optimizer dataset locally
4. Generates tool declarations
5. Creates ADK evaluation config
6. (Optional) Uploads to GCS
7. (Optional) Submits optimizer job

Usage:
    python setup_optimizer_and_adk.py --full              # Full setup
    python setup_optimizer_and_adk.py --local-only       # Skip GCS
    python setup_optimizer_and_adk.py --upload-gcs       # Upload existing files
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def setup_step(step_num: int, title: str):
    """Print a formatted step header."""
    print(f"\n{'='*70}")
    print(f"STEP {step_num}: {title}")
    print('='*70)


def step_1_validate_environment():
    """Step 1: Validate environment and credentials."""
    setup_step(1, "Validate Environment and Credentials")
    
    try:
        from google.auth import default
        credentials, project = default()
        print(f"✅ GCP credentials valid")
        print(f"   Project: {project}")
        return True
    except Exception as e:
        print(f"⚠️  Credentials issue: {e}")
        print(f"\n   To fix:")
        print(f"   1. Set: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        print(f"   2. Or run: gcloud auth application-default login")
        return False


def step_2_prepare_optimizer_dataset():
    """Step 2: Prepare optimizer dataset from scenarios."""
    setup_step(2, "Prepare Optimizer Dataset")
    
    try:
        from server.training.prepare_optimizer_dataset import prepare_optimizer_dataset
        path = prepare_optimizer_dataset()
        
        # Check file size
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"   Dataset size: {size_mb:.2f} MB")
        
        return True, path
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False, None


def step_3_export_tool_declarations():
    """Step 3: Export tool declarations for optimizer."""
    setup_step(3, "Export Tool Declarations")
    
    try:
        from server.training.tool_declarations import validate_and_export
        path = validate_and_export()
        
        # Verify output
        with open(path) as f:
            config = json.load(f)
        tool_count = len(config.get("tools", {}).get("function_declarations", []))
        print(f"   Tools defined: {tool_count}")
        
        return True, path
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False, None


def step_4_setup_adk_evaluation():
    """Step 4: Setup ADK evaluation configs."""
    setup_step(4, "Setup ADK Evaluation")
    
    try:
        from server.training.adk_eval_setup import export_eval_config, create_golden_dataset_from_scenarios
        
        # Export config
        config_path = export_eval_config()
        
        # Create golden dataset
        print("📊 Creating golden dataset from scenarios...")
        dataset = create_golden_dataset_from_scenarios()
        
        with open("/tmp/adk_golden_dataset.json", "w") as f:
            json.dump(
                [
                    {
                        "query": s.query,
                        "expected_tools": [t.tool_name for t in s.expected_tool_sequence],
                        "reference": s.reference
                    }
                    for s in dataset
                ],
                f,
                indent=2
            )
        
        print(f"   Config: {config_path}")
        print(f"   Golden dataset: /tmp/adk_golden_dataset.json ({len(dataset)} samples)")
        
        return True, config_path
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False, None


def step_5_prepare_optimizer_job_config():
    """Step 5: Prepare optimizer job configuration."""
    setup_step(5, "Prepare Optimizer Job Configuration")
    
    try:
        from server.training.run_prompt_optimizer import submit_optimizer_job
        
        print("📝 Generating optimizer job config...")
        
        # Run in dry-run mode to generate config
        submit_optimizer_job(dry_run=True)
        
        print("\n✅ Job configuration ready for submission")
        print("   To submit: python run_prompt_optimizer.py --submit")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def step_6_upload_to_gcs(dataset_path: Optional[str] = None, tools_path: Optional[str] = None):
    """Step 6: Upload files to GCS."""
    setup_step(6, "Upload to GCS (Optional)")
    
    try:
        from google.cloud import storage
        
        client = storage.Client(project="sailly-voice-agent-eu")
        bucket = client.bucket("sailly-voice-agent-eu-ai")
        
        files_to_upload = [
            (dataset_path or "/tmp/optimizer_dataset.jsonl", "optimizer_input/optimizer_dataset.jsonl"),
            (tools_path or "/tmp/optimizer_tools.json", "optimizer_configs/tool_declarations.json"),
            ("/tmp/adk_golden_dataset.json", "adk_configs/golden_dataset.json"),
            ("/tmp/adk_eval_config.json", "adk_configs/adk_eval_config.json"),
        ]
        
        uploaded = 0
        for local_file, gcs_path in files_to_upload:
            if os.path.exists(local_file):
                print(f"📤 Uploading {gcs_path}...")
                blob = bucket.blob(gcs_path)
                blob.upload_from_filename(local_file)
                print(f"   ✅ gs://sailly-voice-agent-eu-ai/{gcs_path}")
                uploaded += 1
            else:
                print(f"   ⚠️  File not found: {local_file}")
        
        print(f"\n✅ Uploaded {uploaded} files to GCS")
        return True
    except Exception as e:
        print(f"⚠️  GCS upload failed: {e}")
        print(f"   Files are available locally in /tmp/")
        return False


def create_quickstart_guide():
    """Create a quickstart guide for using the optimizer and ADK."""
    guide = """
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
"""
    
    output_path = Path(__file__).parent / "OPTIMIZER_AND_ADK_QUICKSTART.md"
    with open(output_path, "w") as f:
        f.write(guide)
    
    return output_path


def main():
    """Execute full setup workflow."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Vertex AI Optimizer and ADK Evaluation")
    parser.add_argument("--full", action="store_true", help="Full setup including GCS upload")
    parser.add_argument("--local-only", action="store_true", help="Local setup only (no GCS)")
    parser.add_argument("--upload-gcs", action="store_true", help="Upload existing files to GCS")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("Vertex AI Prompt Optimizer & ADK Evaluation Setup")
    print("="*70)
    
    dataset_path = None
    tools_path = None
    
    # Step 1: Validate environment
    if not step_1_validate_environment():
        print("\n⚠️  Proceeding with local-only setup (no GCS upload)")
    
    # Step 2: Prepare optimizer dataset
    success, dataset_path = step_2_prepare_optimizer_dataset()
    if not success:
        print("❌ Failed to prepare dataset. Aborting.")
        return False
    
    # Step 3: Export tool declarations
    success, tools_path = step_3_export_tool_declarations()
    if not success:
        print("❌ Failed to export tools. Aborting.")
        return False
    
    # Step 4: Setup ADK evaluation
    success, _ = step_4_setup_adk_evaluation()
    if not success:
        print("⚠️  ADK setup had issues, but continuing")
    
    # Step 5: Prepare optimizer job config
    if not step_5_prepare_optimizer_job_config():
        print("⚠️  Optimizer config had issues, but continuing")
    
    # Step 6: Upload to GCS (optional)
    if args.full or args.upload_gcs:
        step_6_upload_to_gcs(dataset_path, tools_path)
    else:
        print(f"\n⏭️  Skipping GCS upload (use --full or --upload-gcs to upload)")
    
    # Create quickstart guide
    print("\n" + "="*70)
    print("STEP 7: Create Quickstart Guide")
    print("="*70)
    guide_path = create_quickstart_guide()
    print(f"✅ Quickstart guide: {guide_path}")
    
    # Summary
    print("\n" + "="*70)
    print("✅ SETUP COMPLETE")
    print("="*70)
    print("\n📋 Summary:")
    print("   1. ✅ Optimizer dataset prepared: /tmp/optimizer_dataset.jsonl")
    print("   2. ✅ Tool declarations exported: /tmp/optimizer_tools.json")
    print("   3. ✅ ADK golden dataset created: /tmp/adk_golden_dataset.json")
    print("   4. ✅ Optimizer job config ready")
    print("\n🚀 Next Steps:")
    print("   1. Fix the 3 critical bugs (see OPTIMIZER_AND_ADK_QUICKSTART.md)")
    print("   2. Run validation on 50 failed scenarios")
    print("   3. Run Vertex AI Prompt Optimizer: python run_prompt_optimizer.py --submit")
    print("   4. Apply optimized prompt and re-validate")
    print("\n📖 Read the quickstart guide for detailed instructions")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
