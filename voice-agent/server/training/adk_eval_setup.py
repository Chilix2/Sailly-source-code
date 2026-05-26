"""ADK Evaluation setup for Sailly restaurant bot."""

import json
from typing import List, Dict, Any, Literal
from dataclasses import dataclass
from enum import Enum


class MatchType(Enum):
    """Tool trajectory matching strategies for ADK evaluation."""
    EXACT = "EXACT"          # Exact sequence match
    IN_ORDER = "IN_ORDER"    # Tools must appear in order but can have others between
    ANY_ORDER = "ANY_ORDER"  # Tools can appear in any order


@dataclass
class ToolCall:
    """Represents a tool call with name and arguments."""
    tool_name: str
    tool_input: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input
        }


@dataclass
class EvalSample:
    """Single evaluation sample for ADK."""
    query: str  # Customer utterance
    expected_tool_sequence: List[ToolCall]  # Expected tools in order
    reference: str = ""  # Optional reference response


def create_golden_dataset_from_scenarios() -> List[Dict[str, Any]]:
    """
    Convert Tier 2 scenarios into ADK evaluation dataset format.
    
    Returns:
        List of evaluation samples
    """
    
    import sys
    from pathlib import Path
    
    # Add parent to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from server.scenarios.tier2_scenarios import TIER2_SCENARIOS
    
    eval_dataset = []
    
    for scenario in TIER2_SCENARIOS:
        if not scenario.turns:
            continue
        
        # Get first customer utterance as the query
        query = scenario.turns[0].user_utterance
        
        # Convert expected_tools to ToolCall format
        tool_calls = [
            ToolCall(tool_name=tool, tool_input={})
            for tool in scenario.expected_tools
        ]
        
        sample = EvalSample(
            query=query,
            expected_tool_sequence=tool_calls,
            reference=""
        )
        
        eval_dataset.append(sample)
    
    return eval_dataset


def tool_trajectory_scorer(
    called_tools: List[str],
    expected_tools: List[str],
    match_type: MatchType = MatchType.IN_ORDER
) -> Dict[str, Any]:
    """
    Score tool call trajectory against expected sequence.
    
    This mimics ADK's tool_trajectory_avg_score metric.
    
    Args:
        called_tools: Actual tools called by the bot
        expected_tools: Expected tools from scenario
        match_type: How strictly to match (EXACT, IN_ORDER, ANY_ORDER)
        
    Returns:
        Score dictionary with details
    """
    
    score = 1.0
    details = {
        "match_type": match_type.value,
        "called": called_tools,
        "expected": expected_tools,
        "missing_tools": [],
        "extra_tools": [],
        "order_violations": 0
    }
    
    if match_type == MatchType.EXACT:
        # Must match exactly
        if called_tools == expected_tools:
            score = 1.0
        else:
            score = 0.0
            details["missing_tools"] = [t for t in expected_tools if t not in called_tools]
            details["extra_tools"] = [t for t in called_tools if t not in expected_tools]
    
    elif match_type == MatchType.IN_ORDER:
        # Tools must appear in order, but extras are allowed
        expected_idx = 0
        
        for called_tool in called_tools:
            if expected_idx < len(expected_tools) and called_tool == expected_tools[expected_idx]:
                expected_idx += 1
            elif called_tool not in expected_tools:
                # Extra tool (like 'faq') — allowed
                pass
        
        if expected_idx == len(expected_tools):
            # All expected tools were called in order
            score = 1.0
        else:
            # Not all expected tools found in order
            missing_count = len(expected_tools) - expected_idx
            score = max(0.0, 1.0 - (missing_count / len(expected_tools)))
            details["missing_tools"] = expected_tools[expected_idx:]
    
    elif match_type == MatchType.ANY_ORDER:
        # Tools can appear in any order
        called_set = set(called_tools)
        expected_set = set(expected_tools)
        
        missing = expected_set - called_set
        extra = called_set - expected_set - {"faq"}  # faq is always allowed
        
        if not missing:
            score = 1.0
        else:
            score = max(0.0, 1.0 - (len(missing) / len(expected_set)))
            details["missing_tools"] = list(missing)
        
        details["extra_tools"] = list(extra)
    
    return {
        "score": score,
        "details": details
    }


class ADKEvaluator:
    """Wrapper for ADK evaluation with Sailly-specific logic."""
    
    def __init__(self, match_type: MatchType = MatchType.IN_ORDER):
        """
        Initialize evaluator.
        
        Args:
            match_type: Tool trajectory matching strategy
        """
        self.match_type = match_type
        self.eval_results = []
    
    def evaluate_sample(
        self,
        sample_id: str,
        called_tools: List[str],
        expected_tools: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate a single sample.
        
        Args:
            sample_id: Unique identifier for the sample
            called_tools: Tools actually called by bot
            expected_tools: Expected tools from scenario
            
        Returns:
            Evaluation result
        """
        
        result = {
            "sample_id": sample_id,
            "trajectory_score": tool_trajectory_scorer(
                called_tools=called_tools,
                expected_tools=expected_tools,
                match_type=self.match_type
            )
        }
        
        self.eval_results.append(result)
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get evaluation summary across all samples.
        
        Returns:
            Summary statistics
        """
        
        if not self.eval_results:
            return {"total_samples": 0, "avg_score": 0.0}
        
        scores = [r["trajectory_score"]["score"] for r in self.eval_results]
        avg_score = sum(scores) / len(scores)
        passed = sum(1 for s in scores if s == 1.0)
        
        return {
            "total_samples": len(self.eval_results),
            "avg_score": avg_score,
            "passed": passed,
            "failed": len(self.eval_results) - passed,
            "pass_rate": passed / len(self.eval_results) if self.eval_results else 0.0
        }


def combined_evaluation(
    scenario_id: str,
    transcript: Dict[str, Any],
    scenario_expected_tools: List[str],
    auditor_score: Dict[str, float],
    adk_match_type: MatchType = MatchType.IN_ORDER
) -> Dict[str, Any]:
    """
    Combine custom auditor score with ADK trajectory evaluation.
    
    Args:
        scenario_id: Scenario identifier
        transcript: Conversation transcript
        scenario_expected_tools: Expected tools from scenario
        auditor_score: Score from call_auditor_de
        adk_match_type: ADK matching strategy
        
    Returns:
        Combined evaluation result
    """
    
    # Extract tools called from transcript
    called_tools = transcript.get("tools_called", [])
    
    # Get ADK trajectory score
    adk_result = tool_trajectory_scorer(
        called_tools=called_tools,
        expected_tools=scenario_expected_tools,
        match_type=adk_match_type
    )
    
    # Combine scores
    combined = {
        "scenario_id": scenario_id,
        "auditor": auditor_score,
        "adk_trajectory": adk_result,
        "overall": {
            "pass": (auditor_score.get("composite", 0) >= 70.0 and 
                    adk_result["score"] == 1.0),
            "auditor_composite": auditor_score.get("composite", 0),
            "adk_trajectory_score": adk_result["score"]
        }
    }
    
    return combined


def export_eval_config(
    output_path: str = "/tmp/adk_eval_config.json"
) -> str:
    """
    Export ADK evaluation configuration as JSON.
    
    Args:
        output_path: Path to save config
        
    Returns:
        Path to saved config
    """
    
    config = {
        "evaluator": "ADK_ToolTrajectoryEvaluator",
        "match_type": "IN_ORDER",
        "eval_metrics": [
            {
                "name": "tool_trajectory_avg_score",
                "description": "Average score of tool call sequences vs expected",
                "threshold": 0.95
            }
        ],
        "tool_config": {
            "allowed_tools": [
                "get_menu", "check_availability", "create_reservation",
                "create_order", "send_sms", "technical_issues_callback",
                "verify_address", "update_state", "transfer_to_human",
                "transfer_to_ordering", "transfer_to_tier2",
                "get_date_info", "get_weather", "end_call", "faq"
            ],
            "always_allowed": ["faq"]  # faq doesn't count as "extra"
        },
        "integration": {
            "alongside": "call_auditor_de.py",
            "not_replacing": True,
            "reason": "ADK covers tool trajectory; auditor covers language, latency, flow"
        }
    }
    
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ ADK evaluation config exported: {output_path}")
    
    return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ADK Evaluation setup")
    parser.add_argument("--export-config", action="store_true", help="Export evaluation config")
    parser.add_argument("--create-golden", action="store_true", help="Create golden dataset from scenarios")
    
    args = parser.parse_args()
    
    if args.export_config:
        export_eval_config()
    
    if args.create_golden:
        print("📊 Creating golden dataset from Tier 2 scenarios...")
        dataset = create_golden_dataset_from_scenarios()
        print(f"   Created {len(dataset)} evaluation samples")
        
        # Save to JSON
        with open("/tmp/adk_golden_dataset.json", "w") as f:
            json.dump(
                [
                    {
                        "query": s.query,
                        "expected_tools": [t.tool_name for t in s.expected_tool_sequence],
                        "reference": s.reference
                    }
                    for s in dataset
                ],
                f,
                indent=2
            )
        print("   Saved to /tmp/adk_golden_dataset.json")
