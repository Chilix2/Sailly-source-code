"""
Phase 4 Scenario Generator

Analyzes Phase 1-3 results to find:
  - Lowest-scored scenarios (any dimension < 85)
  - Timed-out scenarios
  - Tool-call failures
  - STT trouble spots

Then uses GPT-4o-mini to generate 400+ NEW adversarial scenarios targeting
the exact weaknesses found, plus a fresh batch of random hard/mixed scenarios.

Returns a list of AudioScenario objects ready for ConversationLoop.
"""

import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Scenario dataclass (mirrors server/scenarios/tier1_scenarios.py)
# --------------------------------------------------------------------------- #
from server.scenarios.tier1_scenarios import AudioScenario, ScenarioTurn


# --------------------------------------------------------------------------- #
# Failure analysis
# --------------------------------------------------------------------------- #

def analyze_failures(phase_stats: Dict, raw_transcript_dir) -> Dict:
    """
    Read raw transcripts and PhaseStats to extract failure patterns.
    Returns a structured summary for the GPT prompt.
    """
    import pathlib

    analysis = {
        "total_calls": 0,
        "timeouts": [],
        "tool_failures": [],          # expected but not called
        "low_score_scenarios": [],    # any dim < 85
        "stt_failures": [],           # WER issues
        "categories_by_fail_rate": {},
        "sample_bad_transcripts": [],  # first few turns of failed calls
    }

    transcript_dir = pathlib.Path(raw_transcript_dir)
    if not transcript_dir.exists():
        logger.warning("No raw_transcripts dir — using phase stats only")
    else:
        files = sorted(transcript_dir.glob("*.json"))[:300]  # cap to avoid huge prompt
        cat_counts: Dict[str, Dict] = {}

        for fpath in files:
            try:
                rec = json.loads(fpath.read_text())
            except Exception:
                continue

            analysis["total_calls"] += 1
            sid      = rec.get("scenario_id", "?")
            cat      = sid.split("-")[0] + "-" + sid.split("-")[1] if "-" in sid else sid
            passed   = rec.get("passed", False)
            timed    = rec.get("timed_out", False)
            tools_ok = set(rec.get("expected_tools", [])) <= set(rec.get("tools_called", []))
            scores   = {
                k: rec.get(k, 100)
                for k in ("score_task", "score_lang", "score_instr", "score_stt")
            }
            low_dims = [k for k, v in scores.items() if v < 85]

            if timed:
                analysis["timeouts"].append(sid)
            if rec.get("expected_tools") and not tools_ok:
                analysis["tool_failures"].append({
                    "id": sid,
                    "expected": rec.get("expected_tools"),
                    "got": rec.get("tools_called", []),
                })
            if low_dims:
                analysis["low_score_scenarios"].append({
                    "id": sid, "dims": low_dims, "scores": scores
                })

            # Category fail tracking
            if cat not in cat_counts:
                cat_counts[cat] = {"total": 0, "fail": 0}
            cat_counts[cat]["total"] += 1
            if not passed:
                cat_counts[cat]["fail"] += 1

            # Sample bad transcript (first 3 turns)
            if not passed and len(analysis["sample_bad_transcripts"]) < 10:
                turns = rec.get("turns", [])[:3]
                if turns:
                    analysis["sample_bad_transcripts"].append({
                        "id": sid,
                        "turns": [
                            {"caller": t.get("user_utterance", ""), "bot": t.get("llm_response", "")[:120]}
                            for t in turns
                        ]
                    })

        # Rank categories by fail rate
        analysis["categories_by_fail_rate"] = sorted(
            [
                {"cat": c, "fail_rate": v["fail"] / max(v["total"], 1), **v}
                for c, v in cat_counts.items()
                if v["total"] >= 2
            ],
            key=lambda x: x["fail_rate"],
            reverse=True,
        )[:15]

    # Also pull phase-level stats
    analysis["phase_summary"] = {
        ph: {
            "pass": st.passed, "fail": st.failed,
            "timeout": st.timed_out, "fix": st.fixed,
            "pass_rate": round(st.pass_rate, 2),
            "avg_latency_s": round(st.total_latency / max(st.total, 1) / 1000, 1),
        }
        for ph, st in phase_stats.items()
    }

    return analysis


# --------------------------------------------------------------------------- #
# GPT-4o-mini scenario generation
# --------------------------------------------------------------------------- #

GENERATION_SYSTEM = """
Du generierst Test-Szenarien für einen deutschsprachigen Restaurant-KI-Anrufassistenten
namens "Sailly" für das Restaurant DOBOO in Bonn (koreanische Küche).

Das System hat zwei Tiers:
- Tier 1 (Gemini Live): Begrüßung, FAQ, Weiterleitung
- Tier 2 (Cascade): Bestellungen, Reservierungen, Tool-Aufrufe

Verfügbare Tools: ai_greeting, end_call, transfer_to_tier2, create_reservation,
create_order, send_sms, technical_issues_callback, request_callback

Generiere Test-Szenarien als JSON-Array. Jedes Szenario hat:
{
  "id": "p4-<kategorie>-<nummer>",
  "category": "<kategorie>",
  "description": "<kurze Beschreibung des Gesprächsziels>",
  "opener": "<erster Satz des Anrufers auf Deutsch>",
  "expected_tools": ["<tool1>", ...],
  "difficulty": <1-5>,
  "noise_variant": "clean|restaurant_bg|street|speakerphone",
  "persona": "<Persona-Beschreibung für den Anrufer>"
}

Kategorien: greeting, faq, reservation, order, tool_call, adversarial,
dialect, code_switch, edge_case, stress_test, tier_switch, escalation
"""

GENERATION_USER_TEMPLATE = """
Analysiere diese Ergebnisse aus Phase 1-3 und generiere exakt {count} neue Test-Szenarien.

PHASE-ERGEBNISSE:
{phase_summary}

HÄUFIGSTE FEHLER-KATEGORIEN:
{fail_categories}

TOOL-AUFRUF-FEHLER:
{tool_failures}

NIEDRIG BEWERTETE SZENARIEN:
{low_scores}

TIMEOUTS ({n_timeouts} Stück — diese Szenarien liefen zu lange):
{timeouts}

ANWEISUNGEN:
1. Erstelle 120 Szenarien die die FEHLER oben gezielt beheben
2. Erstelle 80 adversarielle Szenarien (unhöflich, ungeduldig, KI-feindlich, macht Witze)
3. Erstelle 60 Dialekt-Szenarien (Kölsch, Bairisch, Berlinerisch gemischt)
4. Erstelle 60 Tier-Switch-Szenarien (Anrufer wechselt zwischen Tier1/Tier2-Fragen)
5. Erstelle 50 Tool-Call-Szenarien (alle Tools müssen korrekt ausgelöst werden)
6. Erstelle 30 Code-Switch-Szenarien (Deutsch/Englisch gemischt)

Gesamt: {count} Szenarien. Antworte NUR mit dem JSON-Array, kein anderer Text.
"""


async def generate_scenarios_gpt(
    analysis: Dict,
    openai_key: str,
    target_count: int = 400,
) -> List[Dict]:
    """Call GPT-4o-mini to generate target_count scenario specs."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=openai_key)

    # Build compact summary for prompt
    phase_summary = json.dumps(analysis.get("phase_summary", {}), indent=2)
    fail_cats = json.dumps(analysis.get("categories_by_fail_rate", [])[:10], indent=2)
    tool_fails = json.dumps(analysis.get("tool_failures", [])[:15], indent=2)
    low_scores = json.dumps(analysis.get("low_score_scenarios", [])[:15], indent=2)
    timeouts = json.dumps(analysis.get("timeouts", [])[:20], indent=2)

    user_msg = GENERATION_USER_TEMPLATE.format(
        count=target_count,
        phase_summary=phase_summary,
        fail_categories=fail_cats,
        tool_failures=tool_fails,
        low_scores=low_scores,
        n_timeouts=len(analysis.get("timeouts", [])),
        timeouts=timeouts,
    )

    logger.info(f"🤖 Generating {target_count} Phase 4 scenarios via GPT-4o-mini...")

    # GPT-4o-mini has 128k context — split into 2 batches of 200 to stay safe
    batch_size = 200
    all_specs: List[Dict] = []

    for batch_num, batch_start in enumerate(range(0, target_count, batch_size), 1):
        batch_count = min(batch_size, target_count - batch_start)
        logger.info(f"  Batch {batch_num}: generating {batch_count} scenarios...")

        batch_user = user_msg.replace(str(target_count), str(batch_count)).replace(
            "120 Szenarien", f"{int(batch_count*0.30)} Szenarien"
        ).replace(
            "80 adversarielle", f"{int(batch_count*0.20)} adversarielle"
        ).replace(
            "60 Dialekt", f"{int(batch_count*0.15)} Dialekt"
        ).replace(
            "60 Tier-Switch", f"{int(batch_count*0.15)} Tier-Switch"
        ).replace(
            "50 Tool-Call", f"{int(batch_count*0.12)} Tool-Call"
        ).replace(
            "30 Code-Switch", f"{int(batch_count*0.08)} Code-Switch"
        )

        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": GENERATION_SYSTEM},
                    {"role": "user",   "content": batch_user},
                ],
                max_tokens=16000,
                temperature=0.9,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content
            # GPT sometimes wraps in {"scenarios": [...]}
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                batch_specs = parsed
            elif isinstance(parsed, dict):
                batch_specs = parsed.get("scenarios", parsed.get("items", list(parsed.values())[0] if parsed else []))
            else:
                batch_specs = []

            all_specs.extend(batch_specs)
            logger.info(f"  Batch {batch_num}: got {len(batch_specs)} scenarios")
        except Exception as e:
            logger.error(f"  Batch {batch_num} failed: {e}")

    logger.info(f"✅ Total generated: {len(all_specs)} scenario specs")
    return all_specs


def specs_to_audio_scenarios(specs: List[Dict], n_target: int = 300) -> List[AudioScenario]:
    """Convert raw GPT spec dicts → AudioScenario objects."""
    scenarios = []

    for i, spec in enumerate(specs):
        if not isinstance(spec, dict):
            continue

        sid      = spec.get("id") or f"p4-gen-{i+1:03d}"
        opener   = spec.get("opener") or spec.get("first_utterance") or "Hallo, ich habe eine Frage."
        desc     = spec.get("description") or spec.get("goal") or sid
        cat      = spec.get("category", "generated")
        tools    = spec.get("expected_tools") or []
        noise    = spec.get("noise_variant", "clean")
        diff     = int(spec.get("difficulty", 3))

        # Ensure noise_variant is valid
        if noise not in ("clean", "restaurant_bg", "street", "speakerphone"):
            noise = random.choice(["clean", "restaurant_bg", "street", "speakerphone"])

        scen = AudioScenario(
            id=sid,
            phase="phase4",
            category=cat,
            description=desc,
            turns=[ScenarioTurn(user_utterance=opener)],
            expected_tools=tools if isinstance(tools, list) else [],
            noise_variant=noise,
            n_runs=1,
            seed=42 + i,
        )
        scenarios.append(scen)

    # Shuffle and cap at n_target
    random.shuffle(scenarios)
    result = scenarios[:n_target]
    logger.info(f"✅ Phase 4: {len(result)} scenarios ready (from {len(specs)} generated)")
    return result


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #

async def build_phase4_scenarios(
    phase_stats: Dict,
    run_dir,
    openai_key: str,
    target_scenarios: int = 400,
    n_calls: int = 300,
) -> List[AudioScenario]:
    """
    Full pipeline:
      1. Analyze Phase 1-3 results
      2. Generate 400+ scenarios with GPT-4o-mini
      3. Return 300 AudioScenario objects
    """
    logger.info("=" * 80)
    logger.info("  PHASE 4 PREPARATION — Analyzing Phase 1-3 results...")
    logger.info("=" * 80)

    # Step 1: analyze
    transcript_dir = run_dir / "raw_transcripts"
    analysis = analyze_failures(phase_stats, transcript_dir)

    logger.info(f"  Total calls analyzed : {analysis['total_calls']}")
    logger.info(f"  Timeouts found       : {len(analysis['timeouts'])}")
    logger.info(f"  Tool failures        : {len(analysis['tool_failures'])}")
    logger.info(f"  Low-score scenarios  : {len(analysis['low_score_scenarios'])}")
    logger.info(f"  Worst categories     : "
                f"{[c['cat'] for c in analysis['categories_by_fail_rate'][:5]]}")

    # Step 2: generate
    specs = await generate_scenarios_gpt(analysis, openai_key, target_count=target_scenarios)

    if len(specs) < 50:
        logger.warning(f"  Only {len(specs)} specs generated — padding with hardcoded fallbacks")
        specs.extend(_hardcoded_fallback_specs(target_scenarios - len(specs)))

    # Step 3: convert → AudioScenario
    scenarios = specs_to_audio_scenarios(specs, n_target=n_calls)
    return scenarios


def _hardcoded_fallback_specs(n: int) -> List[Dict]:
    """Fallback specs if GPT generation fails."""
    openers = [
        ("Ich möchte einen Tisch für 8 Personen reservieren, aber ich bin glutenintolerant und zwei meiner Gäste sind vegan.", "reservation", ["create_reservation"], "restaurant_bg"),
        ("Was kostet das Bibimbap und kann ich extra Kimchi dazu bekommen?", "faq", [], "clean"),
        ("Ich hab vor 20 Minuten bestellt und nichts ist angekommen. Das ist eine absolute Frechheit!", "adversarial", ["send_sms"], "street"),
        ("Können Sie mir das Menü auf Englisch erklären? My German isn't perfect.", "code_switch", [], "clean"),
        ("Servus, i hätt gern a Reservation für heut Abend, so gegen achte", "dialect", ["create_reservation"], "clean"),
        ("Ich rufe wegen eines technischen Problems an, meine App funktioniert nicht.", "escalation", ["technical_issues_callback"], "speakerphone"),
        ("Gibt es Parkplätze in der Nähe? Und wie lange ist die Wartezeit heute Abend?", "faq", [], "restaurant_bg"),
        ("Ich möchte das komplette Menü für 20 Personen bestellen, Lieferung bitte.", "order", ["create_order", "send_sms"], "clean"),
        ("Können Sie mich mit einem menschlichen Mitarbeiter verbinden? Ich vertraue KI nicht.", "adversarial", ["transfer_to_human"], "clean"),
        ("Hallo? Hallo?! Können Sie mich hören? Die Verbindung ist sehr schlecht.", "edge_case", [], "speakerphone"),
    ]
    specs = []
    for i in range(n):
        opener_data = openers[i % len(openers)]
        specs.append({
            "id": f"p4-fallback-{i+1:03d}",
            "category": opener_data[1],
            "description": opener_data[0][:60],
            "opener": opener_data[0],
            "expected_tools": opener_data[2],
            "difficulty": random.randint(3, 5),
            "noise_variant": opener_data[3],
            "persona": "Anspruchsvoller Anrufer mit komplexem Anliegen",
        })
    return specs
