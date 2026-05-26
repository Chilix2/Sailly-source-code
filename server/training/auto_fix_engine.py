"""
Auto-Fix Engine — Claude Haiku 4.5 integration for automatic bug fixing.

Called once per bucket iteration (after all scenarios in that bucket run).
Analyzes all failures, proposes ONE targeted fix via Claude Haiku, applies it,
then re-runs the entire bucket to observe regression immediately.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import anthropic

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of an auto-fix attempt."""
    applied: bool
    tier: int  # 1 = keyword, 2 = Claude, 3 = human notify
    changes: List[str]  # What was changed
    revert_file: Optional[str] = None  # Path to .bak file for revert
    reason: str = ""  # Why the fix was applied (or not)
    error: Optional[str] = None  # Error message if failed


class AutoFixEngine:
    """
    Proposes and applies fixes to failing scenarios using Claude Haiku.
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-haiku-4-5"
        self.repo_dir = Path("/home/charles2/sailly-google-fork")
        self.node_manager = self.repo_dir / "server/training/node_manager.py"

    async def analyze_failures(
        self,
        bucket_name: str,
        failed_scenarios: List[Dict[str, Any]],
        pass_rate: float,
    ) -> Dict[str, Any]:
        """
        Analyze failure patterns in failed scenarios.
        
        Args:
            bucket_name: e.g., "1_order"
            failed_scenarios: List of failed scenario results
            pass_rate: Current bucket pass rate
        
        Returns:
            Dict with: missing_tools, patterns, recommendations
        """
        # Cluster failures by missing tool
        missing_by_tool = {}
        for scenario in failed_scenarios:
            tools_missing = scenario.get("tools_missing", [])
            for tool in tools_missing:
                if tool not in missing_by_tool:
                    missing_by_tool[tool] = []
                missing_by_tool[tool].append(scenario.get("scenario_id", "unknown"))

        return {
            "bucket": bucket_name,
            "total_failed": len(failed_scenarios),
            "pass_rate": pass_rate,
            "missing_by_tool": missing_by_tool,
            "failure_reasons": [s.get("failure_reasons", []) for s in failed_scenarios[:3]],
        }

    async def propose_fix(
        self,
        bucket_name: str,
        failed_analysis: Dict[str, Any],
        attempt_num: int,
    ) -> Optional[Dict[str, str]]:
        """
        Send failure context to Claude Haiku and get a fix proposal.
        
        Args:
            bucket_name: Bucket name
            failed_analysis: Output from analyze_failures()
            attempt_num: Which fix attempt (1-3)
        
        Returns:
            Dict with: {file, find, replace, reason, risk} or None if no fix proposed
        """
        missing_by_tool = failed_analysis.get("missing_by_tool", {})
        pass_rate = failed_analysis.get("pass_rate", 0.0)

        # Read relevant code section
        try:
            node_mgr_code = self.node_manager.read_text()
            # Extract keyword lists
            kw_section = node_mgr_code[: min(len(node_mgr_code), 5000)]
        except Exception as e:
            logger.error(f"Failed to read node_manager.py: {e}")
            kw_section = "(could not read code)"

        prompt = f"""German restaurant voice agent — bucket fix request.

**Bucket:** {bucket_name}
**Pass rate:** {pass_rate*100:.1f}%
**Attempt:** {attempt_num}/3

**Failing by missing tool:**
{json.dumps(missing_by_tool, indent=2, ensure_ascii=False)}

**Failure reasons (samples):**
{json.dumps(failed_analysis.get('failure_reasons', [])[:2], indent=2, ensure_ascii=False)}

**Relevant code (node_manager.py keyword lists):**
```
{kw_section[:2000]}
```

**Task:**
Propose ONE targeted fix to improve the {pass_rate*100:.1f}% pass rate.

If the most common missing tool is in the keyword lists, suggest adding new keywords.
If it's a logic issue, suggest a code change.

Return JSON ONLY (no explanation):
{{
  "file": "server/training/node_manager.py",
  "find": "exact existing text to search for (must be unique in file)",
  "replace": "replacement text",
  "reason": "why this fixes the failures",
  "risk": "low|medium|high"
}}

If no clear fix is found, return:
{{
  "reason": "insufficient data / pattern unclear",
  "deferred": true
}}
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Extract JSON
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]

            fix = json.loads(text)

            if fix.get("deferred"):
                logger.info(f"Claude deferred fix: {fix.get('reason')}")
                return None

            return fix

        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            return None

    async def apply_fix(self, fix: Dict[str, str]) -> FixResult:
        """
        Apply a proposed fix to the codebase.
        
        Args:
            fix: Dict with file, find, replace, reason, risk
        
        Returns:
            FixResult object
        """
        file_path = self.repo_dir / fix.get("file", "")
        find_text = fix.get("find", "")
        replace_text = fix.get("replace", "")
        reason = fix.get("reason", "")

        if not file_path.exists():
            return FixResult(
                applied=False,
                tier=2,
                changes=[],
                reason=reason,
                error=f"File not found: {file_path}",
            )

        try:
            code = file_path.read_text()

            # Validate: find string exists and is unique
            if find_text not in code:
                return FixResult(
                    applied=False,
                    tier=2,
                    changes=[],
                    reason=reason,
                    error=f"find string not found in {file_path}",
                )

            if code.count(find_text) > 1:
                return FixResult(
                    applied=False,
                    tier=2,
                    changes=[],
                    reason=reason,
                    error=f"find string is not unique in {file_path} (found {code.count(find_text)} times)",
                )

            # Backup
            bak_file = file_path.with_suffix(".py.bak")
            bak_file.write_text(code)
            logger.info(f"Backed up {file_path} → {bak_file}")

            # Apply fix
            new_code = code.replace(find_text, replace_text, 1)
            file_path.write_text(new_code)
            logger.info(f"Applied fix to {file_path}")

            return FixResult(
                applied=True,
                tier=2,
                changes=[reason],
                revert_file=str(bak_file),
                reason=reason,
            )

        except Exception as e:
            logger.error(f"Error applying fix: {e}", exc_info=True)
            return FixResult(
                applied=False,
                tier=2,
                changes=[],
                reason=reason,
                error=str(e),
            )

    async def revert_fix(self, bak_file: str) -> bool:
        """
        Revert a fix by restoring the backup file.
        
        Args:
            bak_file: Path to .bak backup file
        
        Returns:
            True if successful, False otherwise
        """
        bak_path = Path(bak_file)
        target_path = bak_path.with_suffix("").with_suffix(".py")

        try:
            if not bak_path.exists():
                logger.error(f"Backup file not found: {bak_path}")
                return False

            # Restore
            target_path.write_text(bak_path.read_text())
            bak_path.unlink()
            logger.info(f"Reverted {target_path}")
            return True

        except Exception as e:
            logger.error(f"Error reverting fix: {e}", exc_info=True)
            return False

    async def run_fix_cycle(
        self,
        bucket_name: str,
        failed_scenarios: List[Dict[str, Any]],
        pass_rate: float,
        attempt_num: int,
    ) -> FixResult:
        """
        Run one full fix cycle: analyze → propose → apply.
        
        Args:
            bucket_name: Bucket name
            failed_scenarios: List of failed scenario results
            pass_rate: Current pass rate
            attempt_num: Which attempt (1-3)
        
        Returns:
            FixResult object
        """
        # Analyze
        analysis = await self.analyze_failures(bucket_name, failed_scenarios, pass_rate)
        logger.info(f"Failure analysis: {json.dumps(analysis, ensure_ascii=False)}")

        # Propose
        fix = await self.propose_fix(bucket_name, analysis, attempt_num)
        if not fix:
            return FixResult(
                applied=False,
                tier=3,
                changes=[],
                reason="Claude deferred or no proposal generated",
            )

        logger.info(f"Claude fix proposal: {json.dumps(fix, indent=2, ensure_ascii=False)}")

        # Apply
        result = await self.apply_fix(fix)
        return result


# Demo
async def demo():
    engine = AutoFixEngine()
    
    failed_scenarios = [
        {
            "scenario_id": "p2-order-01",
            "tools_missing": ["create_order"],
            "failure_reasons": ["bot did not recognize order intent"],
        },
        {
            "scenario_id": "p2-order-03",
            "tools_missing": ["create_order"],
            "failure_reasons": ["missing order confirmation"],
        },
    ]

    result = await engine.run_fix_cycle(
        bucket_name="1_order",
        failed_scenarios=failed_scenarios,
        pass_rate=0.75,
        attempt_num=1,
    )

    print(f"Fix result: {result}")


if __name__ == "__main__":
    asyncio.run(demo())
