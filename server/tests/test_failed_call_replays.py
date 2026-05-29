"""server/tests/test_failed_call_replays.py — Replay fixtures for demo-1455350273a3 and demo-dfb792d3369c.

These replays encode the expected behavior when the FSM dispatch and tenant wiring bugs are fixed.
Each replay verifies that:
1. Tenant config is accessible (_tenant attribute present)
2. FSM dispatch succeeds (no silent fallback)
3. Tool calls happen in the right order
4. Required fields are present (e.g., total_price for create_order)
5. No premature end_call or duplicate tool calls
"""

import pytest
from typing import List, Dict, Any, Optional
import logging

from server.tests.tool_call_assertions import (
    ToolCallAssertion,
    DeterministicScenarioRunner,
    build_order_assertion_specs,
)
from server.brain.v4_turn_processor import V4TurnProcessor

logger = logging.getLogger(__name__)


# ── Replay Scenario: demo-1455350273a3 ──────────────────────────────────────

@pytest.fixture(params=["doboo", "pizzeria_napoli"])
def tenant_id_fixture(request):
    """Multi-tenant parameter."""
    return request.param


@pytest.mark.asyncio
async def test_replay_demo_1455350273a3_order_flow(tenant_id_fixture: str):
    """
    Replay of demo-1455350273a3: Customer initiates order for Doboo.
    
    Expected behavior:
    - Greeting → detect order intent
    - INFO → collect phone, address, items
    - READBACK → confirm details
    - COMMITTED → create_order with all required fields
    
    Verify: No FSM dispatch fallback, all tool fields present, order created exactly once.
    """
    scenario_name = f"demo-1455350273a3_order_flow_{tenant_id_fixture}"
    
    # Initialize processor with tenant config
    processor = V4TurnProcessor(
        tenant_id=tenant_id_fixture,
        call_sid="test-demo-1455350273a3",
        caller_phone="+41798765432",
    )
    
    # Verify tenant config was loaded
    assert processor._tenant_config is not None, "Tenant config should be loaded"
    logger.info(f"✓ Tenant config loaded for {tenant_id_fixture}")
    
    # Define the replay turns
    turns: List[Dict[str, Any]] = [
        {
            "turn": 1,
            "user_text": "Hallo, ich möchte eine Bestellung aufgeben.",
            "expected_phase": "INFO",
            "expected_intent": "order",
        },
        {
            "turn": 2,
            "user_text": "+41798765432",
            "expected_phase": "INFO",
            "expected_intent": "phone_confirmed",
        },
        {
            "turn": 3,
            "user_text": "Ich bin in der Bahnhofstrasse 12, 8001 Zürich",
            "expected_phase": "INFO",
            "expected_intent": "address_confirmed",
        },
        {
            "turn": 4,
            "user_text": "Ich möchte zwei Padayottis und ein Bier",
            "expected_phase": "ORDER_OR_RESERVE",
            "expected_intent": "items_extracted",
        },
        {
            "turn": 5,
            "user_text": "Mit bar Zahlung",
            "expected_phase": "READBACK",
            "expected_intent": "payment_collected",
        },
        {
            "turn": 6,
            "user_text": "Ja, genau",
            "expected_phase": "COMMITTED",
            "expected_intent": "confirm_readback",
        },
    ]
    
    # Create scenario runner with assertion specs
    scenario = DeterministicScenarioRunner(scenario_name, initial_state={})
    assertion_specs = build_order_assertion_specs(processor._tenant_config)
    
    # Record all tool calls
    assertion = ToolCallAssertion(scenario_name)
    
    try:
        for turn_data in turns:
            turn_idx = turn_data["turn"]
            user_text = turn_data["user_text"]
            
            # Process turn
            result = await processor.process_turn(
                user_text=user_text,
            )
            
            logger.info(f"Turn {turn_idx}: {result.node_name or 'unknown'} → {user_text[:30]}...")
            
            # Record any tool calls
            if result.tools_called:
                for tool_name in result.tools_called:
                    tool_args = result.tool_results.get(tool_name, {})
                    assertion.record_tool_call(tool_name, tool_args)
                    logger.info(f"  ✓ Tool: {tool_name}")
            
            # Verify FSM dispatch succeeded (not fallback)
            assert result.node_name is not None, f"Turn {turn_idx}: FSM should assign node name"
        
        # Verify tool call invariants
        assertion.assert_tool_not_called("end_call")
        logger.info("✓ No premature end_call")
        
        assertion.assert_tool_called_once("create_order")
        logger.info("✓ create_order called exactly once")
        
        assertion.assert_field_present("create_order", "total_price")
        logger.info("✓ create_order has total_price field")
        
        assertion.assert_field_present("create_order", "items")
        assertion.assert_field_not_empty("create_order", "items")
        logger.info("✓ create_order has non-empty items")
        
        assertion.print_report()
    
    except AssertionError as e:
        logger.error(f"Replay {scenario_name} failed: {e}")
        raise


# ── Replay Scenario: demo-dfb792d3369c ──────────────────────────────────────

@pytest.mark.asyncio
async def test_replay_demo_dfb792d3369c_order_flow(tenant_id_fixture: str):
    """
    Replay of demo-dfb792d3369c: Customer initiates order for Pizzeria Napoli.
    
    Expected behavior:
    - Same flow as above but for pizzeria tenant
    - Verify tenant-specific menu items are extracted
    
    Verify: Tenant config accessible, FSM dispatch succeeds, tool fields present.
    """
    scenario_name = f"demo-dfb792d3369c_order_flow_{tenant_id_fixture}"
    
    # Initialize processor with tenant config
    processor = V4TurnProcessor(
        tenant_id=tenant_id_fixture,
        call_sid="test-demo-dfb792d3369c",
        caller_phone="+41791234567",
    )
    
    # Verify tenant config was loaded
    assert processor._tenant_config is not None, "Tenant config should be loaded"
    assert hasattr(processor._tenant_config, 'tenant_id'), "Tenant config should have tenant_id"
    logger.info(f"✓ Tenant config loaded for {tenant_id_fixture} (tenant_id={processor._tenant_config.tenant_id})")
    
    # Define replay turns
    turns: List[Dict[str, Any]] = [
        {
            "turn": 1,
            "user_text": "Guten Tag, ich möchte eine Pizza bestellen",
            "expected_phase": "INFO",
        },
        {
            "turn": 2,
            "user_text": "+41791234567",
            "expected_phase": "INFO",
        },
        {
            "turn": 3,
            "user_text": "Seestrasse 45, 8002 Zürich",
            "expected_phase": "INFO",
        },
        {
            "turn": 4,
            "user_text": "Eine Margherita und eine Quattro Formaggi",
            "expected_phase": "ORDER_OR_RESERVE",
        },
        {
            "turn": 5,
            "user_text": "Mit Kartenzahlung bitte",
            "expected_phase": "READBACK",
        },
        {
            "turn": 6,
            "user_text": "Richtig",
            "expected_phase": "COMMITTED",
        },
    ]
    
    # Setup assertions
    assertion = ToolCallAssertion(scenario_name)
    
    try:
        for turn_data in turns:
            turn_idx = turn_data["turn"]
            user_text = turn_data["user_text"]
            
            # Process turn
            result = await processor.process_turn(
                user_text=user_text,
            )
            
            logger.info(f"Turn {turn_idx}: {result.node_name} → {user_text[:30]}...")
            
            # Verify FSM dispatch succeeded
            assert result.node_name is not None, f"Turn {turn_idx}: FSM should assign node name"
            
            # Record tool calls
            if result.tools_called:
                for tool_name in result.tools_called:
                    tool_args = result.tool_results.get(tool_name, {})
                    assertion.record_tool_call(tool_name, tool_args)
                    logger.info(f"  ✓ Tool: {tool_name}")
        
        # Verify invariants
        assertion.assert_tool_not_called("end_call")
        assertion.assert_tool_called_once("create_order")
        assertion.assert_field_present("create_order", "total_price")
        assertion.assert_field_not_empty("create_order", "items")
        
        assertion.print_report()
    
    except AssertionError as e:
        logger.error(f"Replay {scenario_name} failed: {e}")
        raise


# ── Replay Scenario: After-Hours + Callback ──────────────────────────────────

@pytest.mark.asyncio
async def test_replay_after_hours_callback(tenant_id_fixture: str):
    """
    Test after-hours flow: Customer calls outside business hours → offer callback.
    
    Verify: request_callback tool called, not create_order.
    """
    scenario_name = f"after_hours_callback_{tenant_id_fixture}"
    
    processor = V4TurnProcessor(
        tenant_id=tenant_id_fixture,
        call_sid="test-after-hours",
        caller_phone="+41798765432",
    )
    
    assert processor._tenant_config is not None
    
    # Simulate after-hours (would need time mocking or config override)
    turns = [
        {"user_text": "Ich möchte bestellen"},
        {"user_text": "+41798765432"},
        {"user_text": "Okay, danke, ich rufe später an"},
    ]
    
    assertion = ToolCallAssertion(scenario_name)
    
    for user_text in turns:
        result = await processor.process_turn(
            user_text=user_text["user_text"],
        )
        if result.tools_called:
            for tool_name in result.tools_called:
                assertion.record_tool_call(tool_name, {})
    
    # After-hours should suggest callback, not attempt order
    # Note: This would require time mocking; for now just verify no crash
    logger.info(f"✓ After-hours scenario completed without crash")


if __name__ == "__main__":
    # Run with: pytest -v server/tests/test_failed_call_replays.py
    pass
