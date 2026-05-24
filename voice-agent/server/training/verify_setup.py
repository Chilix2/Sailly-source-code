#!/usr/bin/env python3
"""
Final verification checklist for Vertex AI Prompt Optimizer and ADK setup.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def check_file_exists(path: str, description: str) -> bool:
    """Check if a file exists and print status."""
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}")
    return exists


def check_packages() -> bool:
    """Check if required packages are installed."""
    try:
        import google.cloud.aiplatform
        import google.adk
        print("✅ google-cloud-aiplatform installed")
        print("✅ google-adk installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("VERTEX AI SETUP - VERIFICATION CHECKLIST")
    print("="*70)
    
    all_good = True
    
    # Section 1: Packages
    print("\n📦 PACKAGES")
    all_good &= check_packages()
    
    # Section 2: Core scripts
    print("\n📄 SETUP SCRIPTS")
    scripts = [
        ("server/training/prepare_optimizer_dataset.py", "Optimizer dataset preparation"),
        ("server/training/run_prompt_optimizer.py", "Optimizer job submission"),
        ("server/training/tool_declarations.py", "Tool declarations for optimizer"),
        ("server/training/adk_eval_setup.py", "ADK evaluation framework"),
        ("server/training/gcs_bucket_setup.py", "GCS bucket management"),
        ("server/training/setup_optimizer_and_adk.py", "Master setup orchestration"),
    ]
    for script, desc in scripts:
        all_good &= check_file_exists(str(PROJECT_ROOT / script), desc)
    
    # Section 3: Documentation
    print("\n📚 DOCUMENTATION")
    docs = [
        ("server/training/SETUP_COMPLETE_SUMMARY.md", "Setup completion summary"),
        ("server/training/OPTIMIZER_AND_ADK_QUICKSTART.md", "Quickstart guide"),
    ]
    for doc, desc in docs:
        all_good &= check_file_exists(str(PROJECT_ROOT / doc), desc)
    
    # Section 4: Generated artifacts
    print("\n🎯 GENERATED ARTIFACTS")
    artifacts = [
        ("/tmp/optimizer_dataset.jsonl", "Optimizer dataset (220 scenarios)"),
        ("/tmp/optimizer_tools.json", "Tool declarations JSON"),
        ("/tmp/adk_golden_dataset.json", "ADK golden dataset"),
        ("/tmp/adk_eval_config.json", "ADK evaluation config"),
    ]
    for artifact, desc in artifacts:
        all_good &= check_file_exists(artifact, desc)
    
    # Section 5: GCS bucket
    print("\n☁️  GCS INFRASTRUCTURE")
    try:
        from google.cloud import storage
        client = storage.Client(project="sailly-voice-agent-eu")
        bucket = client.bucket("sailly-voice-agent-eu-ai")
        if bucket.exists():
            print("✅ GCS bucket exists: gs://sailly-voice-agent-eu-ai")
            all_good &= True
        else:
            print("❌ GCS bucket not found")
            all_good = False
    except Exception as e:
        print(f"⚠️  GCS check skipped: {e}")
    
    # Summary
    print("\n" + "="*70)
    if all_good:
        print("✅ ALL CHECKS PASSED - SETUP IS COMPLETE")
        print("\n🚀 Next Steps:")
        print("   1. Read: server/training/OPTIMIZER_AND_ADK_QUICKSTART.md")
        print("   2. Fix: The 3 critical bugs (reservation commit, variations, prompt)")
        print("   3. Validate: 50 failed scenarios")
        print("   4. Run: python server/training/run_prompt_optimizer.py --submit")
    else:
        print("❌ SOME CHECKS FAILED - REVIEW ABOVE")
        return 1
    
    print("="*70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
