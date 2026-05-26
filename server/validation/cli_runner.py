"""
CLI entry point for sound validation.

Examples
--------
python -m server.validation.cli_runner run --phase a --parallel 5
python -m server.validation.cli_runner run_phase_a --parallel 3
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from server.validation.phase_runner import print_summary, run_phase
from server.validation.phases.definitions import PHASE_SCENARIO_DIRS


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )


async def _cmd_run(
    *,
    phase: str,
    parallel: int,
    ws_url: str | None,
    max_duration_sec: float,
    no_fix: bool,
) -> int:
    results = await run_phase(
        phase,
        max_concurrent=parallel,
        sailly_ws_url=ws_url,
        max_duration_sec=max_duration_sec,
        run_fix_auditor=not no_fix,
    )
    print_summary(results)
    errors = [r for r in results if r.error]
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sailly sound validation (audio bridge)")
    parser.add_argument("-v", "--verbose", action="store_true")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--parallel", type=int, default=3)
    common.add_argument("--ws-url", default=None, help="Override SAILLY_VALIDATION_WS_URL")
    common.add_argument("--max-duration-sec", type=float, default=180.0)
    common.add_argument("--no-fix", action="store_true", help="Skip FixAuditor hook")

    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", parents=[common])
    p_run.add_argument(
        "--phase",
        required=True,
        choices=sorted(PHASE_SCENARIO_DIRS.keys()),
    )

    for letter in sorted(PHASE_SCENARIO_DIRS.keys()):
        sub.add_parser(
            f"run_phase_{letter}",
            parents=[common],
            help=f"Run all scenarios in phase {letter.upper()}",
        )

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if args.command == "run":
        return asyncio.run(
            _cmd_run(
                phase=args.phase,
                parallel=args.parallel,
                ws_url=args.ws_url,
                max_duration_sec=args.max_duration_sec,
                no_fix=args.no_fix,
            )
        )

    if args.command.startswith("run_phase_"):
        letter = args.command.replace("run_phase_", "")
        return asyncio.run(
            _cmd_run(
                phase=letter,
                parallel=args.parallel,
                ws_url=args.ws_url,
                max_duration_sec=args.max_duration_sec,
                no_fix=args.no_fix,
            )
        )

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
