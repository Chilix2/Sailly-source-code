"""Setup and verify GCS bucket for optimizer configs and results."""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def get_project_id() -> str:
    """Get GCP project ID from environment or credentials."""
    project_id = os.getenv("GCP_PROJECT_ID", "sailly-voice-agent-eu")
    return project_id


def get_bucket_name() -> str:
    """Get or create optimizer bucket name."""
    return os.getenv("OPTIMIZER_GCS_BUCKET", "sailly-voice-agent-eu-ai")


def verify_and_create_bucket(
    bucket_name: Optional[str] = None,
    project_id: Optional[str] = None,
    region: str = "eu"
) -> dict:
    """
    Verify GCS bucket exists, create if needed.
    
    Args:
        bucket_name: Bucket name (default: sailly-voice-agent-eu-ai)
        project_id: GCP project ID (default: sailly-voice-agent-eu)
        region: Region for the bucket (default: eu)
        
    Returns:
        Dictionary with bucket info and status
    """
    
    from google.cloud import storage
    from google.api_core.exceptions import AlreadyExists
    
    bucket_name = bucket_name or get_bucket_name()
    project_id = project_id or get_project_id()
    
    client = storage.Client(project=project_id)
    
    # Check if bucket exists
    bucket = client.bucket(bucket_name)
    
    try:
        if bucket.exists():
            print(f"✅ Bucket exists: gs://{bucket_name}")
            return {
                "status": "verified",
                "bucket": bucket_name,
                "uri": f"gs://{bucket_name}",
                "created": False
            }
    except Exception as e:
        print(f"⚠️  Error checking bucket: {e}")
    
    # Try to create bucket
    print(f"📦 Creating bucket: gs://{bucket_name}")
    
    try:
        bucket = client.create_bucket(
            bucket_name,
            location=region.upper()
        )
        print(f"✅ Bucket created: gs://{bucket_name}")
        return {
            "status": "created",
            "bucket": bucket_name,
            "uri": f"gs://{bucket_name}",
            "created": True
        }
    except AlreadyExists:
        print(f"✅ Bucket already exists: gs://{bucket_name}")
        return {
            "status": "verified",
            "bucket": bucket_name,
            "uri": f"gs://{bucket_name}",
            "created": False
        }
    except Exception as e:
        print(f"❌ Failed to create bucket: {e}")
        return {
            "status": "error",
            "bucket": bucket_name,
            "uri": f"gs://{bucket_name}",
            "error": str(e)
        }


def setup_bucket_paths(bucket_name: Optional[str] = None) -> dict:
    """
    Create standard folder structure for optimizer workflow.
    
    Args:
        bucket_name: Bucket name
        
    Returns:
        Dictionary with all path URIs
    """
    
    bucket_name = bucket_name or get_bucket_name()
    
    paths = {
        "input": f"gs://{bucket_name}/optimizer_input/",
        "dataset": f"gs://{bucket_name}/optimizer_input/optimizer_dataset.jsonl",
        "output": f"gs://{bucket_name}/optimizer_output/",
        "logs": f"gs://{bucket_name}/optimizer_logs/",
        "configs": f"gs://{bucket_name}/optimizer_configs/"
    }
    
    print(f"\n📁 Optimizer Bucket Structure (gs://{bucket_name}):")
    print(f"   └── optimizer_input/")
    print(f"       └── optimizer_dataset.jsonl")
    print(f"   └── optimizer_output/")
    print(f"   └── optimizer_logs/")
    print(f"   └── optimizer_configs/")
    
    return paths


def validate_credentials() -> bool:
    """
    Validate GCP credentials are available.
    
    Returns:
        True if credentials are valid
    """
    
    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError
    
    try:
        credentials, project = default()
        print(f"✅ GCP credentials valid")
        print(f"   Project: {project}")
        return True
    except DefaultCredentialsError:
        print(f"❌ No valid GCP credentials found")
        print(f"   Set GOOGLE_APPLICATION_CREDENTIALS or run: gcloud auth application-default login")
        return False


def create_service_account_key_hint() -> str:
    """Print hint for using service account key."""
    
    hint = """
If using a service account key file:
1. Set environment variable:
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sailly-voice-agent-key.json

2. Verify it's set:
   echo $GOOGLE_APPLICATION_CREDENTIALS

3. Test authentication:
   gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS
"""
    return hint


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup GCS bucket for optimizer")
    parser.add_argument("--verify", action="store_true", help="Verify/create bucket")
    parser.add_argument("--validate-creds", action="store_true", help="Validate credentials")
    parser.add_argument("--bucket", help="Bucket name (default: sailly-voice-agent-eu-ai)")
    
    args = parser.parse_args()
    
    if args.validate_creds:
        validate_credentials()
    
    if args.verify:
        result = verify_and_create_bucket(bucket_name=args.bucket)
        print(f"\nResult: {result}")
        
        if result["status"] in ["created", "verified"]:
            paths = setup_bucket_paths(bucket_name=args.bucket)
            print(f"\nPaths configuration:")
            for key, path in paths.items():
                print(f"   {key}: {path}")
        else:
            print(create_service_account_key_hint())
