#!/usr/bin/env python3
"""
Google Cloud Secret Manager integration for Sailly Sound Validation.

Usage:
    python3 manage_secrets.py --create xai-api-key "<YOUR_XAI_API_KEY>"
    python3 manage_secrets.py --load xai-api-key
    python3 manage_secrets.py --sync-from-env
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Optional

try:
    from google.cloud import secretmanager
    from google.oauth2 import service_account
except ImportError:
    print("ERROR: google-cloud-secret-manager not installed")
    print("Install with: pip install google-cloud-secret-manager")
    sys.exit(1)


class GoogleSecretsManager:
    """Manage secrets in Google Cloud Secret Manager."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()

    def secret_path(self, secret_id: str) -> str:
        """Build resource name for a secret."""
        return self.client.secret_path(self.project_id, secret_id)

    def create_secret(self, secret_id: str, secret_value: str) -> str:
        """Create or update a secret in Google Secret Manager."""
        parent = self.client.common_project_path(self.project_id)
        
        try:
            # Check if secret exists
            self.client.get_secret(request={"name": self.secret_path(secret_id)})
            print(f"✓ Secret '{secret_id}' exists. Adding new version...")
        except Exception:
            # Create new secret
            print(f"✓ Creating new secret '{secret_id}'...")
            self.client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )

        # Add secret version
        secret = self.client.add_secret_version(
            request={
                "parent": self.secret_path(secret_id),
                "payload": {"data": secret_value.encode("UTF-8")},
            }
        )
        print(f"✓ Secret '{secret_id}' stored in GCP Secret Manager")
        return secret.name

    def get_secret(self, secret_id: str) -> Optional[str]:
        """Retrieve a secret from Google Secret Manager."""
        try:
            secret = self.client.access_secret_version(
                request={"name": f"{self.secret_path(secret_id)}/versions/latest"}
            )
            return secret.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"ERROR: Could not retrieve secret '{secret_id}': {e}")
            return None

    def list_secrets(self) -> list:
        """List all secrets in the project."""
        parent = self.client.common_project_path(self.project_id)
        secrets = self.client.list_secrets(request={"parent": parent})
        return [s.name.split("/")[-1] for s in secrets]


def main():
    parser = argparse.ArgumentParser(
        description="Manage Sailly secrets in Google Cloud Secret Manager"
    )
    parser.add_argument("--project-id", help="GCP Project ID", default="sailly-voice-agent-eu")
    parser.add_argument("--create", nargs=2, metavar=("SECRET_ID", "VALUE"),
                        help="Create/update a secret")
    parser.add_argument("--load", metavar="SECRET_ID", help="Load and print a secret")
    parser.add_argument("--sync-from-env", action="store_true",
                        help="Sync secrets from .env file to GCP")
    parser.add_argument("--list", action="store_true", help="List all secrets")

    args = parser.parse_args()

    manager = GoogleSecretsManager(args.project_id)

    if args.create:
        secret_id, secret_value = args.create
        manager.create_secret(secret_id, secret_value)

    elif args.load:
        secret_value = manager.get_secret(args.load)
        if secret_value:
            print(secret_value)

    elif args.sync_from_env:
        env_file = Path(".env")
        if not env_file.exists():
            print("ERROR: .env file not found")
            sys.exit(1)

        secrets_to_sync = [
            "XAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "DEEPGRAM_API_KEY",
            "OPENAI_API_KEY",
        ]

        for secret_name in secrets_to_sync:
            value = os.getenv(secret_name)
            if value:
                gcp_secret_id = secret_name.lower().replace("_", "-")
                manager.create_secret(gcp_secret_id, value)
            else:
                print(f"⊘ {secret_name} not found in .env, skipping")

    elif args.list:
        secrets = manager.list_secrets()
        print("Secrets in Google Cloud Secret Manager:")
        for secret in secrets:
            print(f"  - {secret}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
