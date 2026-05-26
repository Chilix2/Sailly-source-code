"""
RealBrowserRun — Run validation scenarios through the REAL browser demo pipeline.

Connects to the browser demo WebSocket, sends synthesized caller audio, collects bot
responses, and scores each scenario with the same call_auditor_de.py used by Phase A.

Produces a browser_validation_report.json comparable to Phase A's ab_results.json,
letting you measure the pipeline gap: Phase A text-only (93.2%) vs browser demo (audio).

Prerequisites:
    1. Voice agent must be running: systemctl start sailly-voice-agent
       (or: cd sailly-google-fork && python server/main.py)
    2. GCP credentials in GOOGLE_APPLICATION_CREDENTIALS (for caller TTS)
    3. DEEPGRAM_API_KEY set (optional — used by AudioInjector internally)

Usage:
    # Single scenario (quick smoke test):
    python -m server.training.run_browser_validation \\
        --ids p1-faq-opening-hours-01 \\
        --ws-url ws://localhost:3003/ws/demo

    # All 4 phases (full RealBrowserRun, overnight):
    python -m server.training.run_browser_validation \\
        --phases 1 2 3 4 \\
        --ws-url ws://localhost:3003/ws/demo \\
        --output /tmp/browser_validation/

    # Fast iteration mode (bucket testing, ~50-70s/scenario instead of ~120s):
    python -m server.training.run_browser_validation \\
        --fast \\
        --ids p2-order-01 p3-reservation-01 p1-faq-01 p3-angry-01 p3-chaos-02 \\
        --output /tmp/browser_smoke/

    # Include multi-intent scenarios:
    python -m server.training.run_browser_validation \\
        --phases 1 2 3 4 --multi-intent \\
        --output /tmp/browser_validation/

    # Compare immediately with Phase A:
    python -m server.training.run_browser_validation \\
        --phases 1 2 3 4 --compare-phase-a /tmp/ab_test_results/ab_results.json

Mode flags:
    --fast    Tighter timeouts for rapid bucket testing (~50-70s/scenario).
              Use during active development / fix iteration.
    --strict  Conservative timeouts for final validation (default, ~120s/scenario).
              Use for overnight / full 280-scenario runs.

Continuous loop (smoke → buckets 1–6 → repeat):
    This module runs one batch and exits. For the full iteration loop on GCP, use:
        scripts/browser_validation_loop.sh
    Set DATABASE_URL for --dashboard-push. Env LOOP_FOREVER=0 runs one cycle only.
"""

import argparse
import asyncio
import importlib
import importlib.util
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_dotenv(env_path: str = "/home/charles2/sailly-google-fork/.env") -> None:
    """Load environment variables from .env file without requiring python-dotenv."""
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key.isidentifier():
            os.environ.setdefault(key, val)


_load_dotenv()

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)

# Phase A baseline pass rate (from latest run) — update after re-runs
PHASE_A_BASELINE = 93.2
_PHASE_A_TOTAL    = 280


@dataclass
class BrowserRunConfig:
    """Timing parameters for SyntheticBrowserClient.

    StrictConfig (default): conservative margins for final/overnight validation.
    FastConfig: tighter timeouts for rapid iteration / bucket testing.
    """
    bot_silence_gap_s: float     # seconds of silence = bot is done speaking
    bot_turn_timeout_s: float    # hard cap waiting for a bot response
    greeting_timeout_s: float    # hard cap waiting for the initial greeting
    inter_turn_silence_s: float  # silence streamed between turns (keeps Deepgram VAD warm)
    post_utterance_tail_s: float # silence tail appended after each user utterance


# Conservative defaults — safe for final / overnight validation
STRICT_CONFIG = BrowserRunConfig(
    bot_silence_gap_s=2.0,
    bot_turn_timeout_s=90.0,
    greeting_timeout_s=25.0,
    inter_turn_silence_s=3.0,
    post_utterance_tail_s=1.5,
)

# Tighter timeouts for rapid iteration / bucket testing
# NOTE: Gemini 2.5-flash latency grows with server uptime (likely Vertex AI rate
# limiting / quota throttling). After ~15 min of operation, peak latency can reach
# 85-95s per turn. Set timeout to 100s to handle worst-case without timing out.
FAST_CONFIG = BrowserRunConfig(
    bot_silence_gap_s=1.5,
    bot_turn_timeout_s=100.0,
    greeting_timeout_s=20.0,
    inter_turn_silence_s=1.5,
    post_utterance_tail_s=0.8,
)

# Module map mirrors ab_test_loop._PHASE_MODULE_MAP
_PHASE_MODULE_MAP = {
    1: ("server.scenarios.phase1_scenarios", "PHASE1_SCENARIOS"),
    2: ("server.scenarios.phase2_scenarios", "PHASE2_SCENARIOS"),
    3: ("server.scenarios.phase3_scenarios", "PHASE3_SCENARIOS"),
    4: ("server.scenarios.phase4_scenarios", "PHASE4_SCENARIOS"),
}
_MULTI_INTENT_MODULE = ("server.scenarios.multi_intent_scenarios", "MULTI_INTENT_SCENARIOS")


def _load_scenarios(
    phases: Optional[List[int]],
    scenario_ids: Optional[List[str]],
    include_multi_intent: bool,
    max_scenarios: Optional[int],
):
    """Load AudioScenario objects — same logic as ab_test_loop._load_scenarios."""
    scenarios = []

    if phases:
        for p in sorted(phases):
            if p not in _PHASE_MODULE_MAP:
                logger.warning(f"Unknown phase {p}, skipping")
                continue
            mod_name, attr = _PHASE_MODULE_MAP[p]
            try:
                mod = importlib.import_module(mod_name)
                phase_scens = getattr(mod, attr)
                scenarios.extend(phase_scens)
                logger.info(f"  Phase {p}: {len(phase_scens)} scenarios")
            except (ImportError, AttributeError) as e:
                logger.error(f"  Phase {p}: failed to load ({e})")

        # Production failures (optional)
        prod_path = (
            Path(__file__).parent.parent / "scenarios" / "production_failures.py"
        )
        if prod_path.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    "server.scenarios.production_failures", str(prod_path)
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                pf = getattr(mod, "PRODUCTION_FAILURE_SCENARIOS", [])
                scenarios.extend(pf)
                if pf:
                    logger.info(f"  Production failures: {len(pf)} scenarios")
            except Exception as e:
                logger.warning(f"  Production failures: failed ({e})")
    else:
        # Legacy mode: load tier2 + fix_validation
        for mod_name, attr in [
            ("server.scenarios.tier2_scenarios", "TIER2_SCENARIOS"),
            ("server.scenarios.fix_validation_scenarios", "FIX_VALIDATION_SCENARIOS"),
        ]:
            try:
                mod = importlib.import_module(mod_name)
                batch = getattr(mod, attr, [])
                scenarios.extend(batch)
            except (ImportError, AttributeError):
                pass

    if include_multi_intent:
        mod_name, attr = _MULTI_INTENT_MODULE
        try:
            mod = importlib.import_module(mod_name)
            mi_scens = getattr(mod, attr, [])
            scenarios.extend(mi_scens)
            logger.info(f"  Multi-intent: {len(mi_scens)} scenarios")
        except (ImportError, AttributeError) as e:
            logger.warning(f"  Multi-intent: {e}")

    # Deduplicate by ID (some phase files define the same scenario ID multiple times).
    # First occurrence wins, preserving load order (phase order).
    seen_ids: set = set()
    deduped = []
    for s in scenarios:
        if s.id not in seen_ids:
            seen_ids.add(s.id)
            deduped.append(s)
    if len(deduped) < len(scenarios):
        logger.debug(f"  Deduplicated: {len(scenarios)} → {len(deduped)} scenarios")
    scenarios = deduped

    if scenario_ids:
        id_set = set(scenario_ids)
        scenarios = [s for s in scenarios if s.id in id_set]
        logger.info(f"  Filtered to {len(scenarios)} scenario(s) by ID")

    if max_scenarios and len(scenarios) > max_scenarios:
        scenarios = scenarios[:max_scenarios]
        logger.info(f"  Capped at {max_scenarios} scenarios")

    return scenarios


def _conv_result_to_audit_turns(result) -> List[Dict]:
    """Convert ConvResult turns to the dict format audit_call expects.

    The Turn-0 init (greeting) fires tools (ai_greeting, get_menu) outside the
    normal turn loop. These are captured in result.tools_called but not in any
    individual ConvTurn. Prepend a synthetic init turn so the auditor's
    all_tools set includes them for the expected_tools coverage check.
    """
    # Tools that appear in the overall result but not in any individual turn
    per_turn_tools: set = set()
    for t in result.turns:
        per_turn_tools.update(t.tools_called or [])
    greeting_tools = [t for t in (result.tools_called or []) if t not in per_turn_tools]

    turns_out = []
    if greeting_tools:
        turns_out.append(
            {
                "turn_idx": -1,
                "user_utterance": "",
                "stt_transcript": "",
                "wer": 0.0,
                "llm_response": "",
                "tts_bytes": 0,
                "tools_called": greeting_tools,
                "latency_ms": 0.0,
                "passed": True,
            }
        )
    turns_out.extend(
        {
            "turn_idx": t.turn_idx,
            "user_utterance": t.caller_text,
            "stt_transcript": t.stt_transcript,
            "wer": t.wer,
            "llm_response": t.bot_response,
            "tts_bytes": t.tts_bytes,
            "tools_called": t.tools_called,
            "latency_ms": t.total_latency_ms,
            "passed": t.passed,
        }
        for t in result.turns
    )
    return turns_out


def _make_audio_injector():
    """Construct an AudioInjector with env-var credentials."""
    from server.training.audio_injector import AudioInjector

    project_id = os.environ.get("GCP_PROJECT_ID", "sailly-voice-agent-eu")
    deepgram_key = os.environ.get("DEEPGRAM_API_KEY", "")
    return AudioInjector(
        google_project_id=project_id,
        deepgram_api_key=deepgram_key,
        tts_voice="de-DE-Wavenet-F",
    )


async def _run_scenario(
    scenario,
    ws_url: str,
    injector,
    inter_scenario_pause: float,
    config: "BrowserRunConfig" = None,
) -> Dict[str, Any]:
    """Run one scenario and return a result dict (auditor scores included)."""
    from server.training.synthetic_browser_client import SyntheticBrowserClient
    from server.training.call_auditor_de import audit_call

    cfg = config or STRICT_CONFIG
    client = SyntheticBrowserClient(
        ws_url=ws_url,
        scenario=scenario,
        audio_injector=injector,
        bot_silence_gap_s=cfg.bot_silence_gap_s,
        bot_turn_timeout_s=cfg.bot_turn_timeout_s,
        greeting_timeout_s=cfg.greeting_timeout_s,
        inter_turn_silence_s=cfg.inter_turn_silence_s,
        post_utterance_tail_s=cfg.post_utterance_tail_s,
    )

    try:
        result = await client.run()
    except Exception as e:
        logger.error(f"  [{scenario.id}] EXCEPTION: {e}")
        return {
            "scenario_id": scenario.id,
            "phase": scenario.phase,
            "category": scenario.category,
            "description": scenario.description,
            "passed": False,
            "error": str(e),
            "tools_got": [],
            "tools_expected": scenario.expected_tools or [],
            "tools_missing": scenario.expected_tools or [],
            "composite_score": 0,
            "end_reason": "error",
        }

    # Run auditor
    try:
        audit_turns = _conv_result_to_audit_turns(result)
        phase_str = scenario.phase  # "phase1" / "phase2" / ...
        try:
            phase_int = int(phase_str.replace("phase", ""))
        except (ValueError, AttributeError):
            phase_int = 0

        audit = audit_call(
            scenario_id=scenario.id,
            phase=phase_int,
            run_number=1,
            turns=audit_turns,
            expected_tools=scenario.expected_tools or [],
            total_latency_ms=result.total_latency_ms,
        )
        composite = audit.composite
        missing = list(audit.tools_missing) if audit.tools_missing else []
        fail_reasons_all = list(audit.failure_reasons) if hasattr(audit, "failure_reasons") else []

        # Browser validation adds ~13-25 s of audio round-trip overhead per turn
        # (3s silence stream + real-time audio + STT + network). The auditor's
        # latency budget (5 s for phase 1) is calibrated for real phone calls.
        # Latency failures are therefore expected and should NOT affect pass/fail
        # for audio pipeline validation. We evaluate FUNCTIONAL correctness only:
        #   • No expected tools missing
        #   • Non-latency failure reasons
        latency_reasons = [r for r in fail_reasons_all if "latency" in r.lower()]
        non_latency_reasons = [r for r in fail_reasons_all if "latency" not in r.lower()]
        # Functional pass = no missing tools AND no non-latency auditor failures
        functional_pass = (not missing) and (not non_latency_reasons)
        passed = functional_pass
        fail_reasons = non_latency_reasons  # only surface functional failures
    except Exception as e:
        logger.warning(f"  [{scenario.id}] Auditor error: {e}")
        passed = result.passed
        composite = 0.0
        missing = [t for t in (scenario.expected_tools or []) if t not in result.tools_called]
        fail_reasons = [str(e)]
        latency_reasons = []

    return {
        "scenario_id": scenario.id,
        "phase": scenario.phase,
        "category": scenario.category,
        "description": scenario.description,
        "passed": passed,
        "composite_score": composite,
        "tools_got": result.tools_called,
        "tools_expected": scenario.expected_tools or [],
        "tools_missing": missing,
        "failure_reasons": fail_reasons,
        "latency_info": latency_reasons,
        "turns": len(result.turns),
        "total_latency_ms": result.total_latency_ms,
        "end_reason": result.end_reason,
    }


def push_to_dashboard(run_id: str, bucket: str, phase_set: str, report: dict, config: dict) -> None:
    """Push validation results to PostgreSQL for dashboard display."""
    if not PSYCOPG2_AVAILABLE:
        logger.warning("[Dashboard] psycopg2 not installed — skipping DB push")
        return
    
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("[Dashboard] DATABASE_URL not set — skipping DB push")
        return
    
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        results = report.get("results", [])
        passed = sum(1 for r in results if r.get("passed"))
        total = len(results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        elapsed_sec = report.get("elapsed_seconds", 0)
        phase_a_baseline = report.get("phase_a_baseline", PHASE_A_BASELINE)
        pipeline_gap = phase_a_baseline - pass_rate if pass_rate > 0 else 0
        
        # Insert or update run summary
        cur.execute("""
            INSERT INTO browser_validation_runs
                (run_id, bucket, phase_set, started_at, finished_at, status, 
                 total_scenarios, passed_count, failed_count, pass_rate, 
                 config, phase_a_baseline, pipeline_gap, total_elapsed_seconds, triggered_by)
            VALUES (%s, %s, %s, NOW(), NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET
                finished_at=NOW(),
                status='completed',
                passed_count=EXCLUDED.passed_count,
                failed_count=EXCLUDED.failed_count,
                pass_rate=EXCLUDED.pass_rate,
                total_elapsed_seconds=EXCLUDED.total_elapsed_seconds
        """, (
            run_id,
            bucket,
            phase_set,
            "completed",
            total,
            passed,
            total - passed,
            pass_rate,
            json.dumps(config),
            phase_a_baseline,
            pipeline_gap,
            elapsed_sec,
            "manual"
        ))
        
        # Insert per-scenario results
        for result in results:
            cur.execute("""
                INSERT INTO browser_validation_results
                    (run_id, scenario_id, phase, category, description, passed,
                     composite_score, tools_expected, tools_got, tools_missing,
                     failure_reasons, latency_info, turn_count, total_latency_ms,
                     end_reason, bot_transcript, user_inputs)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                run_id,
                result.get("scenario_id"),
                result.get("phase"),
                result.get("category"),
                result.get("description"),
                result.get("passed", False),
                result.get("composite_score"),
                result.get("tools_expected", []),
                result.get("tools_got", []),
                result.get("tools_missing", []),
                result.get("failure_reasons", []),
                result.get("latency_info", []),
                result.get("turns"),
                result.get("total_latency_ms"),
                result.get("end_reason"),
                "",  # bot_transcript not in current result structure
                []   # user_inputs would need ConvTurn extraction
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"[Dashboard] Pushed {total} results for run {run_id} to PostgreSQL")
    except Exception as e:
        logger.error(f"[Dashboard] Failed to push results: {e}")


async def run_all(
    ws_url: str,
    phases: Optional[List[int]],
    scenario_ids: Optional[List[str]],
    include_multi_intent: bool,
    max_scenarios: Optional[int],
    output_dir: str,
    compare_phase_a: Optional[str],
    inter_scenario_pause: float = 2.0,
    config: "BrowserRunConfig" = None,
    dashboard_push: bool = False,
    bucket: str = "all",
    phase_set_str: str = "",
    max_concurrent: int = 4,
    stagger_delay_s: float = 10.0,
) -> Dict[str, Any]:
    cfg = config or STRICT_CONFIG
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    mode_label = "FAST" if cfg is FAST_CONFIG else "STRICT"
    logger.info(f"RealBrowserRun [{mode_label} mode | {max_concurrent} parallel | {stagger_delay_s}s stagger] — loading scenarios...")
    logger.info(
        f"  Config: silence_gap={cfg.bot_silence_gap_s}s  turn_timeout={cfg.bot_turn_timeout_s}s  "
        f"greeting_timeout={cfg.greeting_timeout_s}s  inter_turn={cfg.inter_turn_silence_s}s  "
        f"tail={cfg.post_utterance_tail_s}s"
    )
    scenarios = _load_scenarios(phases, scenario_ids, include_multi_intent, max_scenarios)
    if not scenarios:
        logger.error("No scenarios loaded — check --phases or --ids arguments")
        return {}

    logger.info(f"Loaded {len(scenarios)} scenarios. WS: {ws_url}")
    logger.info("Initialising AudioInjector (Google TTS)...")
    injector = _make_audio_injector()

    results_lock = asyncio.Lock()
    results: List[Dict] = []
    passed = 0
    failed = 0
    t_run_start = time.monotonic()

    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_one(scenario, slot_idx: int):
        nonlocal passed, failed
        # Stagger: each slot starts stagger_delay_s later than the previous
        await asyncio.sleep(slot_idx * stagger_delay_s)

        async with semaphore:
            total_so_far = len(results) + 1
            logger.info(f"\n[~{total_so_far}/{len(scenarios)}] {scenario.id} — {scenario.description}")
            result = await _run_scenario(scenario, ws_url, injector, inter_scenario_pause, config=cfg)

            latency_info = result.get("latency_info", [])
            async with results_lock:
                results.append(result)
                if result["passed"]:
                    passed += 1
                    lat_note = f" | {latency_info[0]}" if latency_info else ""
                    logger.info(f"  PASS {scenario.id} — tools: {result['tools_got']}{lat_note}")
                else:
                    failed += 1
                    missing = result.get("tools_missing", [])
                    reasons = result.get("failure_reasons", [])
                    lat_note = f" | ({latency_info[0]})" if latency_info else ""
                    logger.warning(f"  FAIL {scenario.id} — missing: {missing} | reasons: {reasons}{lat_note}")

    # Run all scenarios: split into batches of max_concurrent, staggered within each batch
    batch_size = max_concurrent
    for batch_start in range(0, len(scenarios), batch_size):
        batch = scenarios[batch_start: batch_start + batch_size]
        logger.info(
            f"[Batch {batch_start // batch_size + 1}] Starting {len(batch)} scenarios "
            f"with {stagger_delay_s}s stagger..."
        )
        await asyncio.gather(*[run_one(s, idx) for idx, s in enumerate(batch)])
        # Brief gap between batches so the pipeline fully clears
        if batch_start + batch_size < len(scenarios):
            logger.info("Batch done — 3s cooldown before next batch")
            await asyncio.sleep(3)

    elapsed_s = time.monotonic() - t_run_start
    total = passed + failed
    pass_rate = (passed / total * 100) if total > 0 else 0.0

    # ── Summary ────────────────────────────────────────────────────────────
    sep = "=" * 62
    logger.info(f"\n{sep}")
    logger.info(f"REALBROWERRUN COMPLETE")
    logger.info(f"  Scenarios : {total}")
    logger.info(f"  Passed    : {passed}")
    logger.info(f"  Failed    : {failed}")
    logger.info(f"  Pass rate : {pass_rate:.1f}%")
    logger.info(f"  Elapsed   : {elapsed_s/60:.1f} min")

    gap = PHASE_A_BASELINE - pass_rate
    logger.info(f"\n  Phase A baseline : {PHASE_A_BASELINE:.1f}% ({_PHASE_A_TOTAL} scenarios, text-only)")
    logger.info(f"  RealBrowserRun   : {pass_rate:.1f}% ({total} scenarios, audio round-trip)")
    logger.info(f"  Pipeline gap     : {gap:+.1f}%")
    logger.info(sep)

    # ── Compare with Phase A report (optional) ──────────────────────────────
    if compare_phase_a:
        _compare_with_phase_a(results, compare_phase_a)

    # ── Save reports ──────────────────────────────────────────────────────
    report: Dict[str, Any] = {
        "type": "RealBrowserRun",
        "run_at": datetime.utcnow().isoformat() + "Z",
        "ws_url": ws_url,
        "mode": mode_label,
        "config": {
            "bot_silence_gap_s": cfg.bot_silence_gap_s,
            "bot_turn_timeout_s": cfg.bot_turn_timeout_s,
            "greeting_timeout_s": cfg.greeting_timeout_s,
            "inter_turn_silence_s": cfg.inter_turn_silence_s,
            "post_utterance_tail_s": cfg.post_utterance_tail_s,
        },
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "phase_a_baseline": PHASE_A_BASELINE,
        "pipeline_gap": gap,
        "elapsed_seconds": elapsed_s,
        "results": results,
    }

    report_path = output_path / "browser_validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"\nReport saved: {report_path}")

    failures = [r for r in results if not r.get("passed")]
    if failures:
        fail_path = output_path / "browser_validation_failures.json"
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2, ensure_ascii=False)
        logger.info(f"Failures saved: {fail_path}")

    # Push results to dashboard if requested
    if dashboard_push:
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{bucket}"
        if not phase_set_str:
            phase_set_str = " ".join(map(str, phases)) if phases else "all"
        push_to_dashboard(
            run_id=run_id,
            bucket=bucket,
            phase_set=phase_set_str,
            report=report,
            config=report.get("config", {})
        )

    return report


def _compare_with_phase_a(browser_results: List[Dict], phase_a_path: str):
    """Compare per-scenario results with Phase A (if report exists)."""
    try:
        with open(phase_a_path, encoding="utf-8") as f:
            phase_a = json.load(f)
        a_by_id = {r["scenario_id"]: r for r in phase_a.get("results", [])}
    except Exception as e:
        logger.warning(f"Could not load Phase A report ({e})")
        return

    regressions = []
    improvements = []
    for br in browser_results:
        sid = br["scenario_id"]
        if sid not in a_by_id:
            continue
        a_pass = a_by_id[sid].get("one_live_pass", a_by_id[sid].get("passed", True))
        b_pass = br["passed"]
        if a_pass and not b_pass:
            regressions.append(sid)
        elif not a_pass and b_pass:
            improvements.append(sid)

    if regressions:
        logger.warning(f"\nREGRESSIONS vs Phase A ({len(regressions)}):")
        for sid in regressions:
            br = next(r for r in browser_results if r["scenario_id"] == sid)
            logger.warning(f"  {sid}: missing={br.get('tools_missing')}")
    if improvements:
        logger.info(f"\nIMPROVEMENTS vs Phase A ({len(improvements)}):")
        for sid in improvements:
            logger.info(f"  {sid}")


def _setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_args():
    p = argparse.ArgumentParser(
        description="RealBrowserRun — validate browser demo via audio round-trip",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--ws-url",
        default="ws://localhost:3003/ws/demo",
        help="WebSocket URL of the browser demo endpoint (default: ws://localhost:3003/ws/demo)",
    )
    p.add_argument(
        "--phases",
        nargs="+",
        type=int,
        metavar="N",
        help="Phase numbers to run (1 2 3 4). If omitted, legacy mode is used.",
    )
    p.add_argument(
        "--ids",
        nargs="+",
        metavar="ID",
        help="Run specific scenario IDs only",
    )
    p.add_argument(
        "--multi-intent",
        action="store_true",
        help="Include multi-intent scenarios from multi_intent_scenarios.py",
    )
    p.add_argument(
        "--max-scenarios",
        type=int,
        metavar="N",
        help="Cap total scenarios (useful for quick smoke tests)",
    )
    p.add_argument(
        "--output",
        default="/tmp/browser_validation",
        help="Output directory for reports (default: /tmp/browser_validation)",
    )
    p.add_argument(
        "--compare-phase-a",
        metavar="PATH",
        help="Path to Phase A ab_results.json for per-scenario comparison",
    )
    p.add_argument(
        "--pause",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Pause between scenarios in seconds (default: 2.0)",
    )
    p.add_argument(
        "--dashboard-push",
        action="store_true",
        help="Push results to PostgreSQL browser_validation_runs tables for dashboard display",
    )
    p.add_argument(
        "--bucket",
        type=str,
        default="all",
        help="Bucket name for grouping (e.g., 'smoke', '1', 'all') — for dashboard tracking",
    )
    mode_group = p.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--fast",
        action="store_true",
        help=(
            "Fast iteration mode: tighter timeouts (~50-70s/scenario vs ~120s). "
            "Use for bucket testing and rapid fix iteration. "
            f"Settings: silence_gap={FAST_CONFIG.bot_silence_gap_s}s, "
            f"turn_timeout={FAST_CONFIG.bot_turn_timeout_s}s, "
            f"greeting_timeout={FAST_CONFIG.greeting_timeout_s}s, "
            f"inter_turn={FAST_CONFIG.inter_turn_silence_s}s, "
            f"tail={FAST_CONFIG.post_utterance_tail_s}s"
        ),
    )
    mode_group.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Strict validation mode (default): conservative timeouts for final / overnight runs. "
            f"Settings: silence_gap={STRICT_CONFIG.bot_silence_gap_s}s, "
            f"turn_timeout={STRICT_CONFIG.bot_turn_timeout_s}s, "
            f"greeting_timeout={STRICT_CONFIG.greeting_timeout_s}s, "
            f"inter_turn={STRICT_CONFIG.inter_turn_silence_s}s, "
            f"tail={STRICT_CONFIG.post_utterance_tail_s}s"
        ),
    )
    p.add_argument(
        "--workers",
        type=int,
        default=4,
        metavar="N",
        help="Max concurrent scenarios (default: 4)",
    )
    p.add_argument(
        "--stagger",
        type=float,
        default=10.0,
        metavar="S",
        help="Stagger delay in seconds between concurrent starts (default: 10.0)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _setup_logging(args.verbose)

    if args.fast:
        run_config = FAST_CONFIG
    else:
        # --strict is the default; also used when neither flag is passed
        run_config = STRICT_CONFIG

    # Build phase_set string for dashboard tracking
    phase_set_str = " ".join(map(str, args.phases)) if args.phases else "all"

    asyncio.run(
        run_all(
            ws_url=args.ws_url,
            phases=args.phases,
            scenario_ids=args.ids,
            include_multi_intent=args.multi_intent,
            max_scenarios=args.max_scenarios,
            output_dir=args.output,
            compare_phase_a=args.compare_phase_a,
            inter_scenario_pause=args.pause,
            config=run_config,
            dashboard_push=args.dashboard_push,
            bucket=args.bucket,
            phase_set_str=phase_set_str,
            max_concurrent=args.workers,
            stagger_delay_s=args.stagger,
        )
    )
