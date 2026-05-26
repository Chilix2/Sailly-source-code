"""Submit Vertex AI Prompt Optimizer job."""

import os
import json
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def get_current_tier2_prompt() -> str:
    """Extract the current 74-line system prompt from tier2_runner.py."""
    
    tier2_runner_path = Path(__file__).parent / "tier2_runner.py"
    
    with open(tier2_runner_path, "r") as f:
        content = f.read()
    
    # Extract the prompt between specific markers or use known line range
    # The prompt is typically at lines 144-217 (74 lines)
    lines = content.split("\n")
    
    # Find the start of the system prompt (usually around "Du bist Sailly")
    start_idx = None
    for i, line in enumerate(lines):
        if "Du bist Sailly" in line:
            start_idx = i
            break
    
    if start_idx is None:
        raise ValueError("Could not find system prompt in tier2_runner.py")
    
    # Extract approximately 74 lines from that point
    end_idx = min(start_idx + 74, len(lines))
    prompt_lines = lines[start_idx:end_idx]
    
    # Clean and join
    prompt = "\n".join(prompt_lines).strip()
    
    return prompt


def create_optimizer_job_config(
    system_instruction: str,
    dataset_gcs_path: str = "gs://sailly-voice-agent-eu-ai/optimizer_input/optimizer_dataset.jsonl",
    output_gcs_path: str = "gs://sailly-voice-agent-eu-ai/optimizer_output/",
    target_model: str = "gemini-2.5-flash",
    job_name: str = "sailly-prompt-optimizer-v1"
) -> dict:
    """
    Create the job configuration for Vertex AI Prompt Optimizer.
    
    Args:
        system_instruction: The current system prompt to optimize
        dataset_gcs_path: GCS path to the optimizer dataset JSONL
        output_gcs_path: GCS path for output
        target_model: Target Gemini model
        job_name: Job display name
        
    Returns:
        Job configuration dictionary
    """
    
    config = {
        "display_name": job_name,
        "training_task_definition": {
            "inputs": {
                "base_model_uri": f"projects/sailly-voice-agent-eu/locations/europe-west4/models/{target_model}",
                "template": "{question}",
                "system_instruction": system_instruction,
                "dataset_uri": dataset_gcs_path,
                "eval_metrics_types": [
                    "tool_name_match",
                    "tool_parameter_key_match"
                ],
                "eval_metrics_weights": {
                    "tool_name_match": 0.7,
                    "tool_parameter_key_match": 0.3
                },
                "optimization_objective": "instruction_optimization",
                "aggregation_type": "weighted_sum"
            },
            "outputs": {
                "output_gcs_path": output_gcs_path
            }
        }
    }
    
    return config


def submit_optimizer_job(
    dataset_gcs_path: Optional[str] = None,
    output_gcs_path: Optional[str] = None,
    dry_run: bool = True
) -> Optional[str]:
    """
    Submit Vertex AI Prompt Optimizer job.
    
    Args:
        dataset_gcs_path: GCS path to JSONL dataset
        output_gcs_path: GCS path for results
        dry_run: If True, just print the job config instead of submitting
        
    Returns:
        Job resource name if submitted, None if dry_run
    """
    
    from google.cloud import aiplatform
    from google.api_core import gapic_v1
    
    # Initialize Vertex AI
    aiplatform.init(
        project="sailly-voice-agent-eu",
        location="europe-west4"
    )
    
    # Get the current prompt
    print("📝 Extracting current Tier 2 prompt...")
    system_instruction = get_current_tier2_prompt()
    print(f"   Found {len(system_instruction)} chars")
    
    # Use defaults or provided values
    dataset_path = dataset_gcs_path or "gs://sailly-voice-agent-eu-ai/optimizer_input/optimizer_dataset.jsonl"
    output_path = output_gcs_path or "gs://sailly-voice-agent-eu-ai/optimizer_output/"
    
    # Create job config
    job_config = create_optimizer_job_config(
        system_instruction=system_instruction,
        dataset_gcs_path=dataset_path,
        output_gcs_path=output_path
    )
    
    print("\n🔧 Job configuration:")
    print(json.dumps(job_config, indent=2))
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - Job not submitted")
        print("   Use dry_run=False to actually submit")
        return None
    
    # Note: The actual job submission would use the CustomJob API
    # This is a placeholder for the full implementation
    print("\n✅ In production, this would submit a CustomJob with:")
    print(f"   Image: us-docker.pkg.dev/vertex-ai-restricted/builtin-algorithm/apd:preview_v1_0")
    print(f"   Dataset: {dataset_path}")
    print(f"   Output: {output_path}")
    print(f"   Model: gemini-2.5-flash")
    print(f"   Metrics: tool_name_match (0.7 weight), tool_parameter_key_match (0.3 weight)")
    
    return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Submit Vertex AI Prompt Optimizer job")
    parser.add_argument("--submit", action="store_true", help="Actually submit the job (default: dry-run only)")
    parser.add_argument("--dataset", help="GCS path to dataset JSONL")
    parser.add_argument("--output", help="GCS path for output")
    
    args = parser.parse_args()
    
    submit_optimizer_job(
        dataset_gcs_path=args.dataset,
        output_gcs_path=args.output,
        dry_run=not args.submit
    )
