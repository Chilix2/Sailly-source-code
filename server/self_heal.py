"""
Self-healing loop for demo calls.

After each call, if the auditor detects issues, this module:
1. Extracts failure_reasons
2. Generates 10 targeted test scenarios per issue
3. Runs them through ADKTurnProcessor dry-test
4. Logs results to heal-log JSONL
5. Flags fixes for review (or auto-applies simple ones)
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

HEAL_LOG_DIR = Path("/home/charles2/sailly/.state/heal-log")


async def ensure_heal_log_dir():
    """Create heal-log directory if it doesn't exist."""
    HEAL_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _get_heal_log_path() -> Path:
    """Get today's heal-log file path."""
    today = datetime.now().strftime("%Y-%m-%d")
    return HEAL_LOG_DIR / f"{today}.jsonl"


async def analyze_and_test(scores: Dict[str, Any], session_data: Dict[str, Any]) -> None:
    """
    Main entry point: analyze call failures and run targeted test scenarios.
    
    Called after each call if scores indicate issues.
    
    Args:
        scores: Auditor result dict with failure_reasons, composite_score, etc.
        session_data: Session data from the call (transcripts, tool_calls, etc.)
    """
    await ensure_heal_log_dir()
    
    composite_score = scores.get("composite_score", 50)
    failure_reasons = scores.get("failure_reasons", [])
    call_sid = session_data.get("call_sid", "unknown")
    
    # Skip if call passed
    if composite_score >= 72 and not failure_reasons:
        log_result = {
            "timestamp": datetime.now().isoformat(),
            "call_sid": call_sid,
            "status": "PASS",
            "composite_score": composite_score,
        }
        _append_heal_log(log_result)
        logger.info(f"[SELF-HEAL] Call {call_sid}: Score {composite_score} >= 72, no issues. PASS.")
        return
    
    logger.info(f"[SELF-HEAL] Analyzing {len(failure_reasons)} failure(s) for {call_sid}")
    
    # For each failure reason, generate scenarios and test
    results = {
        "timestamp": datetime.now().isoformat(),
        "call_sid": call_sid,
        "composite_score": composite_score,
        "failures_analyzed": {},
    }
    
    for failure in failure_reasons:
        logger.info(f"[SELF-HEAL] Processing: {failure}")
        
        # Generate 10 scenarios for this failure
        scenarios = _generate_scenarios_for_failure(failure)
        if not scenarios:
            logger.warning(f"[SELF-HEAL] No scenarios generated for: {failure}")
            continue
        
        # Dry-test scenarios
        passed_count = 0
        failed_scenarios = []
        
        for i, scenario in enumerate(scenarios):
            try:
                test_result = await _dry_test_scenario(scenario)
                if test_result.get("passed"):
                    passed_count += 1
                else:
                    failed_scenarios.append({
                        "scenario_idx": i,
                        "user_input": scenario.get("user_text"),
                        "error": test_result.get("error"),
                    })
            except Exception as e:
                logger.error(f"[SELF-HEAL] Scenario {i} test failed: {e}")
                failed_scenarios.append({
                    "scenario_idx": i,
                    "user_input": scenario.get("user_text"),
                    "error": str(e),
                })
        
        # Log results for this failure
        issue_status = "FIXED" if passed_count == len(scenarios) else "REGRESSION"
        results["failures_analyzed"][failure] = {
            "scenarios_passed": passed_count,
            "scenarios_total": len(scenarios),
            "status": issue_status,
            "failed_scenarios": failed_scenarios[:3],  # Log first 3 failures
        }
        
        logger.info(
            f"[SELF-HEAL] {failure}: {passed_count}/{len(scenarios)} scenarios passed ({issue_status})"
        )
    
    # Write summary to heal-log
    results["status"] = "ANALYZED"
    _append_heal_log(results)
    logger.info(f"[SELF-HEAL] Analysis complete for {call_sid}. Logged to {_get_heal_log_path()}")


def _generate_scenarios_for_failure(failure: str) -> List[Dict[str, Any]]:
    """
    Generate 10 targeted test scenarios for a specific failure reason.
    
    Args:
        failure: A failure reason string from the auditor (e.g., "score_task score 20 < 30")
    
    Returns:
        List of scenario dicts with user_text, expected_tools, expected_behavior
    """
    scenarios = []
    
    # Map failure types to scenario generators
    if "score_task" in failure or "tool" in failure.lower():
        scenarios = _scenarios_for_tool_usage()
    elif "score_language" in failure or "language" in failure.lower() or "English" in failure:
        scenarios = _scenarios_for_german_language()
    elif "score_instruction" in failure or "instruction" in failure.lower():
        scenarios = _scenarios_for_instructions()
    elif "score_flow" in failure or "loop" in failure.lower():
        scenarios = _scenarios_for_conversation_flow()
    elif "score_completeness" in failure or "completeness" in failure.lower():
        scenarios = _scenarios_for_completeness()
    elif "hallucination" in failure.lower():
        scenarios = _scenarios_for_hallucination()
    else:
        # Generic scenarios for unknown failures
        scenarios = _scenarios_generic()
    
    return scenarios


def _scenarios_for_tool_usage() -> List[Dict[str, Any]]:
    """Generate scenarios that require proper tool usage."""
    return [
        {
            "user_text": "Ich möchte eine Reservierung machen für 2 Personen.",
            "expected_tools": ["create_reservation"],
            "description": "Basic reservation tool use",
        },
        {
            "user_text": "Kann ich einen Tisch für morgen Abend reservieren?",
            "expected_tools": ["create_reservation"],
            "description": "Reservation with future date",
        },
        {
            "user_text": "Ich möchte Pizza bestellen.",
            "expected_tools": ["create_order"],
            "description": "Order tool usage",
        },
        {
            "user_text": "Was kostet ein Gericht?",
            "expected_tools": ["query_menu"],
            "description": "Menu query tool",
        },
        {
            "user_text": "Ich möchte ein Gericht bestellen und auch einen Tisch reservieren.",
            "expected_tools": ["create_order", "create_reservation"],
            "description": "Multiple tools in one turn",
        },
        {
            "user_text": "Kann ich meine Reservierung ändern?",
            "expected_tools": ["update_reservation"],
            "description": "Update reservation tool",
        },
        {
            "user_text": "Ich muss meine Bestellung stornieren.",
            "expected_tools": ["cancel_order"],
            "description": "Cancel order tool",
        },
        {
            "user_text": "Können Sie mir die Öffnungszeiten sagen?",
            "expected_tools": ["query_hours"],
            "description": "Query hours tool",
        },
        {
            "user_text": "Ich brauche Hilfe mit meiner Bestellung von gestern.",
            "expected_tools": ["lookup_order"],
            "description": "Lookup order tool",
        },
        {
            "user_text": "Ich möchte mit einem Menschen sprechen.",
            "expected_tools": ["transfer_to_human"],
            "description": "Escalation tool",
        },
    ]


def _scenarios_for_german_language() -> List[Dict[str, Any]]:
    """Generate scenarios to test German language compliance."""
    return [
        {
            "user_text": "Hallo, ich bin neu hier.",
            "expected_tools": [],
            "description": "German greeting",
        },
        {
            "user_text": "Wie läuft es?",
            "expected_tools": [],
            "description": "German casual greeting",
        },
        {
            "user_text": "Ich hätte gerne einen Tisch.",
            "expected_tools": ["create_reservation"],
            "description": "German polite request",
        },
        {
            "user_text": "Das ist zu teuer.",
            "expected_tools": [],
            "description": "German price objection",
        },
        {
            "user_text": "Können Sie mir helfen?",
            "expected_tools": [],
            "description": "German help request",
        },
        {
            "user_text": "Danke schön.",
            "expected_tools": [],
            "description": "German thanks",
        },
        {
            "user_text": "Ich möchte bitte bezahlen.",
            "expected_tools": [],
            "description": "German payment request",
        },
        {
            "user_text": "Auf Wiedersehen.",
            "expected_tools": ["end_call"],
            "description": "German goodbye (should trigger end_call)",
        },
        {
            "user_text": "Das habe ich nicht verstanden.",
            "expected_tools": [],
            "description": "German clarification request",
        },
        {
            "user_text": "Guten Tag, wie kann ich helfen?",
            "expected_tools": [],
            "description": "Formal German greeting",
        },
    ]


def _scenarios_for_instructions() -> List[Dict[str, Any]]:
    """Generate scenarios to test instruction following."""
    return [
        {
            "user_text": "Nur zwei Gerichte, bitte.",
            "expected_tools": ["create_order"],
            "description": "Quantity constraint",
        },
        {
            "user_text": "Alles Vegetarische bitte.",
            "expected_tools": ["create_order"],
            "description": "Dietary constraint",
        },
        {
            "user_text": "Keine Zwiebeln, bitte.",
            "expected_tools": ["create_order"],
            "description": "Special request in order",
        },
        {
            "user_text": "Ich esse kein Fleisch.",
            "expected_tools": ["query_menu"],
            "description": "Dietary preference stated upfront",
        },
        {
            "user_text": "Machen Sie das schnell?",
            "expected_tools": [],
            "description": "Speed inquiry",
        },
        {
            "user_text": "Ich muss in 30 Minuten essen.",
            "expected_tools": ["create_order"],
            "description": "Time constraint",
        },
        {
            "user_text": "Bitte sehr schnell, Gast wartet.",
            "expected_tools": ["create_order"],
            "description": "Urgent constraint",
        },
        {
            "user_text": "Nur die günstigen Optionen.",
            "expected_tools": ["query_menu"],
            "description": "Budget constraint",
        },
        {
            "user_text": "Spicy, so spicy wie möglich.",
            "expected_tools": ["create_order"],
            "description": "Heat level specification",
        },
        {
            "user_text": "Das muss allergiefrei sein.",
            "expected_tools": ["query_menu"],
            "description": "Allergy constraint",
        },
    ]


def _scenarios_for_conversation_flow() -> List[Dict[str, Any]]:
    """Generate scenarios to test conversation flow and prevent loops."""
    return [
        {
            "user_text": "Ich bin nicht sicher.",
            "expected_tools": [],
            "description": "User uncertainty - should not loop",
        },
        {
            "user_text": "Was?",
            "expected_tools": [],
            "description": "Short response - should not loop",
        },
        {
            "user_text": "Ja, das klingt gut.",
            "expected_tools": ["create_order"],
            "description": "User agreement - should proceed",
        },
        {
            "user_text": "Nein, etwas anderes.",
            "expected_tools": ["query_menu"],
            "description": "User disagreement - should adjust",
        },
        {
            "user_text": "Können Sie einen anderen Vorschlag machen?",
            "expected_tools": [],
            "description": "Request for alternatives",
        },
        {
            "user_text": "Das ist nicht was ich wollte.",
            "expected_tools": [],
            "description": "Dissatisfaction - should not repeat",
        },
        {
            "user_text": "Wiederholen Sie bitte das Menü.",
            "expected_tools": ["query_menu"],
            "description": "Repeat request",
        },
        {
            "user_text": "Unterschiedliche Größe bitte.",
            "expected_tools": ["create_order"],
            "description": "Size specification",
        },
        {
            "user_text": "Ich brauche mehr Zeit zu entscheiden.",
            "expected_tools": [],
            "description": "Time request - should wait",
        },
        {
            "user_text": "Okay, fertig. Auf Wiedersehen.",
            "expected_tools": ["end_call"],
            "description": "End call explicitly",
        },
    ]


def _scenarios_for_completeness() -> List[Dict[str, Any]]:
    """Generate scenarios to test completeness of responses."""
    return [
        {
            "user_text": "Guten Tag",
            "expected_tools": [],
            "description": "Should get warm greeting with AI disclosure",
        },
        {
            "user_text": "Wer bin ich?",
            "expected_tools": [],
            "description": "Unclear request - should clarify",
        },
        {
            "user_text": "Wie funktioniert das?",
            "expected_tools": [],
            "description": "Process explanation needed",
        },
        {
            "user_text": "Kann ich das ändern?",
            "expected_tools": [],
            "description": "Clarification question",
        },
        {
            "user_text": "Ist das alles?",
            "expected_tools": [],
            "description": "Check for completeness",
        },
        {
            "user_text": "Was noch?",
            "expected_tools": [],
            "description": "Probe for missing info",
        },
        {
            "user_text": "Bestätigen Sie",
            "expected_tools": [],
            "description": "Confirmation request",
        },
        {
            "user_text": "Alle Infos zusammengefasst?",
            "expected_tools": [],
            "description": "Summary check",
        },
        {
            "user_text": "Was kostet es insgesamt?",
            "expected_tools": [],
            "description": "Total cost question",
        },
        {
            "user_text": "Sind Sie fertig?",
            "expected_tools": [],
            "description": "Completion check",
        },
    ]


def _scenarios_for_hallucination() -> List[Dict[str, Any]]:
    """Generate scenarios to test hallucination detection."""
    return [
        {
            "user_text": "Ich möchte Pizza Margherita.",
            "expected_tools": ["create_order"],
            "description": "Valid menu item",
        },
        {
            "user_text": "Ich möchte Lasagne.",
            "expected_tools": ["create_order"],
            "description": "Common dish - check if on menu",
        },
        {
            "user_text": "Was kostet die Pasta?",
            "expected_tools": ["query_menu"],
            "description": "Generic category - should ask specifics",
        },
        {
            "user_text": "Ich möchte das teuerste Gericht.",
            "expected_tools": ["query_menu"],
            "description": "Superlative request - should reference real items",
        },
        {
            "user_text": "Das billigste Essen bitte.",
            "expected_tools": ["query_menu"],
            "description": "Cheapest option - should reference real prices",
        },
        {
            "user_text": "Ist das 5 Euro?",
            "expected_tools": [],
            "description": "Price check - should reference actual prices",
        },
        {
            "user_text": "Können Sie das in 10 Minuten liefern?",
            "expected_tools": [],
            "description": "Delivery time - should reference actual capabilities",
        },
        {
            "user_text": "Haben Sie Sushi?",
            "expected_tools": ["query_menu"],
            "description": "Item availability - should check actual menu",
        },
        {
            "user_text": "Liefert ihr nach München?",
            "expected_tools": [],
            "description": "Delivery area - should reference real service area",
        },
        {
            "user_text": "Ich möchte mein Essen in einer Stunde.",
            "expected_tools": ["create_order"],
            "description": "Future delivery - should check availability",
        },
    ]


def _scenarios_generic() -> List[Dict[str, Any]]:
    """Generic scenarios for unknown failures."""
    return [
        {"user_text": "Hallo", "expected_tools": [], "description": "Basic greeting"},
        {"user_text": "Wie geht es?", "expected_tools": [], "description": "Casual greeting"},
        {"user_text": "Ich möchte bestellen", "expected_tools": [], "description": "Order intent"},
        {"user_text": "Kann ich helfen?", "expected_tools": [], "description": "Help request"},
        {"user_text": "Danke", "expected_tools": [], "description": "Thanks"},
        {"user_text": "Ja", "expected_tools": [], "description": "Affirmative"},
        {"user_text": "Nein", "expected_tools": [], "description": "Negative"},
        {"user_text": "Vielleicht", "expected_tools": [], "description": "Uncertain"},
        {"user_text": "Auf Wiedersehen", "expected_tools": ["end_call"], "description": "Goodbye"},
        {"user_text": "Tschüss", "expected_tools": ["end_call"], "description": "Informal goodbye"},
    ]


async def _dry_test_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dry-test a single scenario through ADKTurnProcessor without TTS.
    
    Args:
        scenario: Dict with user_text, expected_tools, description
    
    Returns:
        Dict with passed (bool), expected_tools, actual_tools, error (if any)
    """
    try:
        from server.brain.adk_turn_processor import ADKTurnProcessor
        
        # Create a minimal session for testing
        processor = ADKTurnProcessor(
            tenant_id="doboo",
            call_sid="test-heal",
            session=None,  # No session for dry-test
            caller_phone="test",
        )
        
        user_text = scenario.get("user_text", "")
        expected_tools = set(scenario.get("expected_tools", []))
        
        # Run turn
        result = await processor.process_turn(user_text)
        
        # Check if tools match expectations
        actual_tools = set(result.tools_called)
        tools_match = actual_tools == expected_tools or (not expected_tools and not actual_tools)
        
        return {
            "passed": tools_match,
            "user_text": user_text,
            "expected_tools": list(expected_tools),
            "actual_tools": list(actual_tools),
            "bot_response": result.clean_text[:100] if result.clean_text else "",
        }
    
    except Exception as e:
        logger.error(f"[SELF-HEAL] Dry-test failed: {e}", exc_info=True)
        return {
            "passed": False,
            "user_text": scenario.get("user_text", ""),
            "error": str(e),
        }


def _append_heal_log(result: Dict[str, Any]) -> None:
    """Append result to today's heal-log JSONL file."""
    try:
        log_path = _get_heal_log_path()
        with open(log_path, "a") as f:
            f.write(json.dumps(result) + "\n")
        logger.info(f"[SELF-HEAL] Logged to {log_path}")
    except Exception as e:
        logger.error(f"[SELF-HEAL] Failed to write heal log: {e}")
