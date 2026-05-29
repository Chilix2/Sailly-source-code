"""server/tests/tool_call_assertions.py — Deterministic tool call verification.

Provides AgentSpec/AgentAssert-like patterns for verifying that:
1. Tool calls happen at expected phases
2. Tool calls contain required fields
3. Tool call order matches invariants
4. Side effects (e.g., orders, reservations, callbacks) execute exactly once

Used by Phase 6 (Deterministic Tool-Result Assertions) testing.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)


# ── ToolCall Spec ────────────────────────────────────────────────────────────

@dataclass
class ToolCallSpec:
    """Specification for an expected tool call in a deterministic scenario."""
    tool_name: str
    expected_fields: Dict[str, Any]  # e.g., {"total_price": ..., "items": [...]}
    required_fields: List[str]  # Must be present
    optional_fields: List[str] = None
    min_args: int = 0
    max_args: int = None
    
    def __post_init__(self):
        if self.optional_fields is None:
            self.optional_fields = []


# ── ToolCallAssertion ────────────────────────────────────────────────────────

class ToolCallAssertion:
    """Assert tool call invariants in a deterministic replay or live scenario."""
    
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.recorded_calls: List[Dict[str, Any]] = []
        self.assertion_log: List[str] = []
    
    def record_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any = None):
        """Record a tool call for later inspection."""
        call = {
            'tool_name': tool_name,
            'args': args,
            'result': result,
        }
        self.recorded_calls.append(call)
        logger.debug(f"[ToolCallAssertion] Recorded {tool_name} for scenario {self.scenario_name}")
    
    def assert_tool_called(self, tool_name: str) -> bool:
        """Assert that a tool was called at least once."""
        found = any(c['tool_name'] == tool_name for c in self.recorded_calls)
        msg = f"Tool {tool_name}: {'✓' if found else '✗'}"
        self.assertion_log.append(msg)
        if not found:
            raise AssertionError(f"Expected {tool_name} to be called in scenario {self.scenario_name}")
        return found
    
    def assert_tool_not_called(self, tool_name: str) -> bool:
        """Assert that a tool was NOT called."""
        found = any(c['tool_name'] == tool_name for c in self.recorded_calls)
        msg = f"Tool NOT {tool_name}: {'✓' if not found else '✗'}"
        self.assertion_log.append(msg)
        if found:
            raise AssertionError(f"Expected {tool_name} NOT to be called in scenario {self.scenario_name}")
        return not found
    
    def assert_tool_called_with(self, tool_name: str, expected_args: Dict[str, Any]) -> bool:
        """Assert that a tool was called with specific arguments."""
        matching = []
        for call in self.recorded_calls:
            if call['tool_name'] != tool_name:
                continue
            args = call['args']
            if all(args.get(k) == v for k, v in expected_args.items()):
                matching.append(call)
        
        found = len(matching) > 0
        msg = f"Tool {tool_name} with args {expected_args}: {'✓' if found else '✗'}"
        self.assertion_log.append(msg)
        if not found:
            raise AssertionError(
                f"Expected {tool_name} with args {expected_args} in scenario {self.scenario_name}; "
                f"got {[c['args'] for c in self.recorded_calls if c['tool_name'] == tool_name]}"
            )
        return found
    
    def assert_tool_called_once(self, tool_name: str) -> bool:
        """Assert that a tool was called exactly once (critical for state mutations)."""
        count = sum(1 for c in self.recorded_calls if c['tool_name'] == tool_name)
        found = count == 1
        msg = f"Tool {tool_name} called exactly once: {'✓' if found else '✗'} (got {count})"
        self.assertion_log.append(msg)
        if not found:
            raise AssertionError(
                f"Expected {tool_name} to be called exactly once in scenario {self.scenario_name}; got {count}"
            )
        return found
    
    def assert_tool_call_order(self, tool_sequence: List[str]) -> bool:
        """Assert that tools were called in a specific order (e.g., verify_address, then create_order)."""
        call_names = [c['tool_name'] for c in self.recorded_calls]
        
        # Check if sequence is a subsequence of actual calls
        j = 0
        for name in tool_sequence:
            while j < len(call_names) and call_names[j] != name:
                j += 1
            if j >= len(call_names):
                msg = f"Tool sequence {tool_sequence} NOT found in {call_names}"
                self.assertion_log.append(msg)
                raise AssertionError(msg)
            j += 1
        
        msg = f"Tool sequence {tool_sequence}: ✓"
        self.assertion_log.append(msg)
        return True
    
    def assert_field_present(self, tool_name: str, field_name: str) -> bool:
        """Assert that all calls to tool_name include field_name."""
        calls = [c for c in self.recorded_calls if c['tool_name'] == tool_name]
        if not calls:
            msg = f"No calls to {tool_name} found"
            self.assertion_log.append(msg)
            raise AssertionError(msg)
        
        all_present = all(field_name in c['args'] for c in calls)
        msg = f"Field {field_name} in {tool_name}: {'✓' if all_present else '✗'}"
        self.assertion_log.append(msg)
        if not all_present:
            raise AssertionError(
                f"Field {field_name} not present in all {tool_name} calls"
            )
        return all_present
    
    def assert_field_not_empty(self, tool_name: str, field_name: str) -> bool:
        """Assert that field is not empty (not None, not empty list, etc.)."""
        calls = [c for c in self.recorded_calls if c['tool_name'] == tool_name]
        if not calls:
            msg = f"No calls to {tool_name} found"
            self.assertion_log.append(msg)
            raise AssertionError(msg)
        
        all_nonempty = all(
            c['args'].get(field_name) not in [None, "", [], {}] 
            for c in calls
        )
        msg = f"Field {field_name} in {tool_name} non-empty: {'✓' if all_nonempty else '✗'}"
        self.assertion_log.append(msg)
        if not all_nonempty:
            raise AssertionError(
                f"Field {field_name} is empty in some {tool_name} calls"
            )
        return all_nonempty
    
    def report(self) -> str:
        """Return formatted report of all assertions."""
        header = f"\n{'='*60}\nScenario: {self.scenario_name}\n{'='*60}\n"
        body = "\n".join(self.assertion_log)
        return f"{header}{body}\n"
    
    def print_report(self):
        """Print formatted report."""
        print(self.report())


# ── Scenario Runner ──────────────────────────────────────────────────────────

class DeterministicScenarioRunner:
    """Run a deterministic replay scenario and verify tool call invariants."""
    
    def __init__(self, scenario_name: str, initial_state: Optional[Dict[str, Any]] = None):
        self.scenario_name = scenario_name
        self.initial_state = initial_state or {}
        self.assertion = ToolCallAssertion(scenario_name)
    
    async def run_scenario_with_assertions(
        self,
        turns: List[Dict[str, Any]],
        processor: Any,  # V4TurnProcessor or similar
        assertion_specs: List[ToolCallSpec],
    ) -> Dict[str, Any]:
        """Run a scenario with deterministic turns and verify tool calls."""
        
        result = {
            'scenario': self.scenario_name,
            'turns_executed': 0,
            'tool_calls_recorded': [],
            'assertions_passed': [],
            'assertions_failed': [],
        }
        
        try:
            # Execute each turn
            for turn_idx, turn in enumerate(turns):
                user_text = turn.get('user_text', '')
                
                # Process turn
                turn_result = await processor.process_turn(
                    user_text=user_text,
                )
                
                result['turns_executed'] += 1
                
                # Extract tool calls from turn result
                if turn_result.tools_called:
                    for tool_name in turn_result.tools_called:
                        self.assertion.record_tool_call(
                            tool_name=tool_name,
                            args=turn_result.tool_results.get(tool_name, {}),
                        )
                        result['tool_calls_recorded'].append({
                            'turn': turn_idx,
                            'tool': tool_name,
                        })
            
            # Run assertions
            for spec in assertion_specs:
                try:
                    if hasattr(self.assertion, f'assert_{spec.tool_name}'):
                        getattr(self.assertion, f'assert_{spec.tool_name}')()
                    else:
                        self.assertion.assert_tool_called(spec.tool_name)
                        self.assertion.assert_field_present(spec.tool_name, 'total_price')
                    result['assertions_passed'].append(spec.tool_name)
                except AssertionError as e:
                    result['assertions_failed'].append(str(e))
        
        except Exception as e:
            logger.error(f"[DeterministicScenarioRunner] Scenario {self.scenario_name} failed: {e}", exc_info=True)
            result['error'] = str(e)
        
        return result


# ── Example Assertion Builders ───────────────────────────────────────────────

def build_order_assertion_specs(tenant_ctx) -> List[ToolCallSpec]:
    """Build standard assertions for a successful order flow."""
    return [
        ToolCallSpec(
            tool_name="verify_address",
            expected_fields={},
            required_fields=["address"],
        ),
        ToolCallSpec(
            tool_name="create_order",
            expected_fields={},
            required_fields=["items", "customer_name", "phone", "address", "total_price"],
        ),
    ]


def build_reservation_assertion_specs(tenant_ctx) -> List[ToolCallSpec]:
    """Build standard assertions for a successful reservation flow."""
    return [
        ToolCallSpec(
            tool_name="verify_address",
            expected_fields={},
            required_fields=["address"],
        ),
        ToolCallSpec(
            tool_name="create_reservation",
            expected_fields={},
            required_fields=["party_size", "date", "time", "customer_name", "phone"],
        ),
    ]
