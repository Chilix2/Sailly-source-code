"""
src/config.py — Configuration loader (env + CLI args)
"""
import argparse
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    openai_api_key: str
    ws_url: str
    pg_dsn: str
    only_scenario: str | None = None
    phase: int | None = None
    suite: str = "smoke"  # smoke, core, all
    runs: int = 1
    verbose: bool = False
    json_output: str | None = None
    md_output: str | None = None


def load_config() -> Config:
    """Parse environment + CLI args into Config."""
    parser = argparse.ArgumentParser(description="Sailly v4 caller-bot training loop")
    parser.add_argument("--only", default=None, help="Run single scenario by name")
    parser.add_argument("--phase", type=int, default=None, help="Run only scenarios from phase N")
    parser.add_argument("--suite", choices=["smoke", "core", "all"], default="smoke",
                        help="Preset suite (smoke / core / all)")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per scenario")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--json-output", default=None, help="Write JSON results to this file")
    parser.add_argument("--md-output", default=None, help="Write markdown report to this file")
    parser.add_argument("--url", default=None, help="WebSocket URL (default: env SAILLY_WS_URL)")
    parser.add_argument("--dsn", default=None, help="Postgres DSN (default: env SAILLY_PG_DSN)")

    args = parser.parse_args()

    # Load from environment with fallbacks — accept Anthropic or OpenAI key
    openai_api_key = (
        os.environ.get("ANTHROPIC_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )
    if not openai_api_key:
        raise ValueError("Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set. Cannot proceed.")

    ws_url = args.url or os.environ.get("SAILLY_WS_URL", "ws://127.0.0.1:8080/ws/headless")
    pg_dsn = args.dsn or os.environ.get("SAILLY_PG_DSN",
                                        "postgresql://sailly:sailly@localhost:5432/sailly")

    return Config(
        openai_api_key=openai_api_key,
        ws_url=ws_url,
        pg_dsn=pg_dsn,
        only_scenario=args.only,
        phase=args.phase,
        suite=args.suite,
        runs=args.runs,
        verbose=args.verbose,
        json_output=args.json_output,
        md_output=args.md_output,
    )
