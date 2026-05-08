"""
src/main.py — CLI entry point

python -m src.main [--suite smoke|core|all] [--only SCENARIO] [--phase N] [--runs K] [--json-out FILE] [--md-out FILE] [--verbose]
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

from .config import load_config
from .persona import CallerPersona, precheck_openai_api_key
from .scenario_loader import (
    load_all_scenarios,
    get_scenarios_by_suite,
    get_scenarios_by_phase,
)
from .runner import ScenarioRunner
from .scoring import Scorer


def setup_logging(verbose: bool):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(name)s - %(levelname)s: %(message)s",
    )


async def main():
    """Main CLI entry point."""
    try:
        config = load_config()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    setup_logging(config.verbose)
    logger = logging.getLogger("main")

    # Precheck OPENAI_API_KEY
    try:
        precheck_openai_api_key()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Initialize persona
    prompts_dir = Path(__file__).parent.parent / "prompts"
    system_prompt = prompts_dir / "caller_system.de.txt"
    if not system_prompt.exists():
        logger.error(f"System prompt not found: {system_prompt}")
        sys.exit(1)

    try:
        persona = CallerPersona(config.openai_api_key, str(system_prompt))
    except Exception as e:
        logger.error(f"Failed to initialize persona: {e}")
        sys.exit(1)

    # Load scenarios
    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    if not scenarios_dir.exists():
        logger.error(f"Scenarios directory not found: {scenarios_dir}")
        sys.exit(1)

    all_scenarios = load_all_scenarios(scenarios_dir)
    logger.info(f"Loaded {len(all_scenarios)} scenarios")

    # Filter scenarios
    if config.only_scenario:
        scenarios = [s for s in all_scenarios if s.id == config.only_scenario]
        if not scenarios:
            logger.error(f"Scenario not found: {config.only_scenario}")
            sys.exit(1)
    elif config.phase is not None:
        scenarios = get_scenarios_by_phase(all_scenarios, config.phase)
    else:
        scenarios = get_scenarios_by_suite(all_scenarios, config.suite)

    logger.info(f"Running {len(scenarios)} scenarios ({config.suite} suite, {config.runs} run(s) each)")

    # Run scenarios
    all_results = []
    for run_num in range(config.runs):
        logger.info(f"=== RUN {run_num + 1}/{config.runs} ===")
        for scenario in scenarios:
            logger.info(f"Running scenario: {scenario.id}")
            runner = ScenarioRunner(
                scenario=scenario,
                ws_url=config.ws_url,
                pg_dsn=config.pg_dsn,
                persona=persona,
                system_prompt_path=str(system_prompt),
            )
            try:
                result = await runner.run()
                all_results.append(result)
            except Exception as e:
                logger.exception(f"Failed to run {scenario.id}")
                all_results.append({
                    "scenario_id": scenario.id,
                    "passed": False,
                    "error": str(e),
                })

    # Generate reports
    logger.info("Generating reports...")

    scorer = Scorer()

    # Aggregate JSON
    if config.json_output:
        agg_json = scorer.generate_aggregate_json(all_results)
        with open(config.json_output, "w") as f:
            json.dump(agg_json, f, indent=2)
        logger.info(f"JSON report written: {config.json_output}")

    # Aggregate MD
    if config.md_output:
        agg_md = scorer.generate_aggregate_report_md(all_results)
        with open(config.md_output, "w") as f:
            f.write(agg_md)
        logger.info(f"Markdown report written: {config.md_output}")
    else:
        # Print to stdout by default
        agg_md = scorer.generate_aggregate_report_md(all_results)
        print("\n" + agg_md)

    # Print summary
    passed = sum(1 for r in all_results if r.get("passed"))
    logger.info(f"\n===== SUMMARY =====")
    logger.info(f"Passed: {passed}/{len(all_results)}")
    if passed < len(all_results):
        failed = [r.get("scenario_id") for r in all_results if not r.get("passed")]
        logger.info(f"Failed: {failed}")

    sys.exit(0 if passed == len(all_results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
