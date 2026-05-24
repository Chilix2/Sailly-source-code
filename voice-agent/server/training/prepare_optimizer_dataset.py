"""Prepare Vertex AI Prompt Optimizer dataset from Tier 2 scenarios."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

# Import scenarios
from server.scenarios.tier2_scenarios import TIER2_SCENARIOS


def prepare_optimizer_dataset(output_path: str = "/tmp/optimizer_dataset.jsonl") -> str:
    """
    Convert Tier 2 scenarios to Vertex AI Prompt Optimizer format.
    
    Each row is a JSON object with:
    - question: First customer utterance from the scenario
    - target: Expected tool calls in optimizer format
    
    Args:
        output_path: Path to write the JSONL file
        
    Returns:
        Path to the generated JSONL file
    """
    
    dataset = []
    
    for scenario in TIER2_SCENARIOS:
        if not scenario.turns:
            continue
        
        # Get first customer utterance as the question
        question = scenario.turns[0].user_utterance
        
        # Format expected tools as optimizer target
        # The optimizer expects this structure for tool_name_match evaluation
        tool_calls = [
            {"name": tool, "arguments": {}}
            for tool in scenario.expected_tools
        ]
        
        target = {
            "content": "",
            "tool_calls": tool_calls
        }
        
        # Create the dataset row
        row = {
            "question": question,
            "target": json.dumps(target)  # target must be a string for JSONL
        }
        
        dataset.append(row)
    
    # Write to JSONL
    with open(output_path, "w") as f:
        for row in dataset:
            f.write(json.dumps(row) + "\n")
    
    print(f"✅ Created dataset with {len(dataset)} scenarios")
    print(f"   Path: {output_path}")
    print(f"   Sample row: {json.dumps(dataset[0], indent=2)}")
    
    return output_path


def upload_to_gcs(local_path: str, gcs_path: str) -> str:
    """
    Upload the dataset to Google Cloud Storage.
    
    Args:
        local_path: Local file path
        gcs_path: GCS path like gs://bucket/path/file.jsonl
        
    Returns:
        GCS path
    """
    from google.cloud import storage
    
    # Parse GCS path
    parts = gcs_path.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    blob_path = parts[1] if len(parts) > 1 else "optimizer_dataset.jsonl"
    
    # Upload
    client = storage.Client(project="sailly-voice-agent-eu")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    
    print(f"✅ Uploaded to GCS: {gcs_path}")
    return gcs_path


if __name__ == "__main__":
    # Prepare dataset locally
    local_path = prepare_optimizer_dataset()
    
    # Optionally upload to GCS (requires valid credentials)
    try:
        gcs_bucket = os.getenv("OPTIMIZER_GCS_BUCKET", "sailly-voice-agent-eu-ai")
        gcs_path = f"gs://{gcs_bucket}/optimizer_input/optimizer_dataset.jsonl"
        upload_to_gcs(local_path, gcs_path)
    except Exception as e:
        print(f"⚠️  GCS upload skipped: {e}")
        print(f"   Dataset available locally at: {local_path}")
