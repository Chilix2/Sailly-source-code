"""
Scenario Variations Generator — Create 4 paraphrase variants per anchor scenario.

For each anchor scenario (e.g., p2-order-01), generates 4 variations with:
  - Different caller phrasing / wording
  - Same expected tools (destination unchanged)
  - Same phase
  - Reuses the audio pipeline (TTS → real-time playback)

Used by real_browser_validation.py to expand bucket coverage without new scenario definitions.
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import anthropic

logger = logging.getLogger(__name__)


@dataclass
class ScenarioVariant:
    """A paraphrase variant of an anchor scenario."""
    scenario_id: str
    variant_num: int  # 1-4
    original_caller_text: str
    variant_caller_text: str  # paraphrased
    expected_tools: List[str]
    phase: int
    category: str


class VariationGenerator:
    """Generates caller-utterance variants for an anchor scenario."""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model = "claude-3-5-haiku-20241022"  # Haiku for speed & cost

    async def generate_variants(
        self,
        scenario_id: str,
        original_caller_text: str,
        expected_tools: List[str],
        phase: int,
        category: str,
        num_variants: int = 4,
    ) -> List[ScenarioVariant]:
        """
        Generate variants by paraphrasing the original caller utterance.

        Args:
            scenario_id: e.g., "p2-order-01"
            original_caller_text: e.g., "I want to order a pizza"
            expected_tools: e.g., ["create_order"]
            phase: scenario phase (1-4)
            category: e.g., "order", "greeting", "reservation"
            num_variants: how many variants to generate (default 4)

        Returns:
            List of ScenarioVariant objects with paraphrased caller text.
        """
        variants = []

        prompt = f"""You are generating {num_variants} natural paraphrase variants of a restaurant customer utterance.

**Context:**
- Category: {category} (German restaurant booking/ordering scenario)
- Phase: {phase}
- Expected bot actions: {', '.join(expected_tools)}

**Original caller utterance (German):**
"{original_caller_text}"

**Task:**
Generate {num_variants} natural German paraphrases of this utterance. Each variant should:
1. Express the same intent (same expected_tools will be triggered)
2. Use different wording, pacing, or politeness level
3. Vary in length (some shorter, some longer)
4. Sound natural for phone/voice

**Output format (JSON array):**
[
  {{"variant": 1, "text": "paraphrase 1"}},
  {{"variant": 2, "text": "paraphrase 2"}},
  ...
]

Generate ONLY the JSON array, no explanation."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Parse JSON
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            
            paraphrases = json.loads(text)
            
            for para in paraphrases:
                variant_num = para.get("variant", len(variants) + 1)
                variant_text = para.get("text", original_caller_text)
                
                variants.append(
                    ScenarioVariant(
                        scenario_id=scenario_id,
                        variant_num=variant_num,
                        original_caller_text=original_caller_text,
                        variant_caller_text=variant_text,
                        expected_tools=expected_tools,
                        phase=phase,
                        category=category,
                    )
                )
                
                logger.info(
                    f"Generated variant {variant_num}: {scenario_id} → {variant_text[:60]}"
                )

        except Exception as e:
            logger.warning(
                f"Failed to generate variants for {scenario_id}: {e}. "
                f"Using original text {num_variants} times."
            )
            # Fallback: use original text
            for i in range(1, num_variants + 1):
                variants.append(
                    ScenarioVariant(
                        scenario_id=scenario_id,
                        variant_num=i,
                        original_caller_text=original_caller_text,
                        variant_caller_text=original_caller_text,
                        expected_tools=expected_tools,
                        phase=phase,
                        category=category,
                    )
                )

        return variants


# Predefined scenario definitions (anchor scenarios per bucket)
# These are loaded from the actual scenario definitions in the codebase.
# For now, we define a mapping of bucket → anchor scenarios.

BUCKET_SCENARIOS = {
    "1_order": [
        "p2-order-01",
        "p2-order-03",
        "p2-order-04",
        "p2-order-05",
        "p2-order-07",
        "p2-order-12",
        "p2-order-043",
        "p2-order-046",
        "p3-impatient-02",
        "p4-hard_to_hear-02",
    ],
    "2_greeting": [
        "p1-faq-01",
        "p1-faq-05",
        "p1-faq-10",
        "p1-faq-16",
        "p2-faq-01",
        "p3-faq-01",
        "p3-faq-002",
        "p3-faq-04",
        "p3-faq-05",
    ],
    "3_reservation": [
        "p2-reservation-01",
        "p3-reservation-005",
        "p3-reservation-006",
        "p3-reservation-010",
        "p3-reservation-05",
        "p4-elderly-02",
    ],
    "4_dual_intent": [
        "p3-chaos-01",
        "p3-chaos-06",
        "p3-chaos-001",
        "p3-sleepy-01",
        "p3-sleepy-03",
        "p3-sleepy-04",
    ],
    "5_escalation": [
        "p3-angry-01",
        "p3-angry-02",
        "p3-angry-05",
        "p4-escalation-04",
        "p4-frustration-06",
        "p1-transfer-agent-01",
    ],
    "6_edge_cases": [
        "p4-elderly-01",
        "p4-hard_to_hear-02",
        "p3-accent-04",
        "p3-accent-07",
        "p4-technical-03",
        "p4-parking-08",
    ],
}

# Map scenario ID to (phase, category, original_caller_text)
# This should be loaded from the actual scenario definitions.
# For now, placeholder mapping:
SCENARIO_METADATA = {
    "p2-order-01": {
        "phase": 2,
        "category": "order",
        "caller_text": "Ich möchte eine Pizza bestellen.",
        "expected_tools": ["create_order"],
    },
    "p3-reservation-01": {
        "phase": 3,
        "category": "reservation",
        "caller_text": "Ich möchte einen Tisch reservieren.",
        "expected_tools": ["create_reservation"],
    },
    "p1-faq-01": {
        "phase": 1,
        "category": "greeting",
        "caller_text": "Guten Tag, ich habe eine Frage.",
        "expected_tools": ["get_menu", "transfer_to_tier2"],
    },
    # ... populate from actual scenario definitions
}


def expand_bucket_with_variants(
    bucket_name: str,
    anchor_scenarios: List[str],
    num_variants: int = 4,
    generator: Optional[VariationGenerator] = None,
) -> List[str]:
    """
    Expand a bucket of anchor scenarios into variants.

    Args:
        bucket_name: e.g., "1_order"
        anchor_scenarios: list of scenario IDs
        num_variants: variants per scenario (default 4)
        generator: VariationGenerator instance (creates one if None)

    Returns:
        List of expanded scenario IDs (original + variant IDs)
    """
    if generator is None:
        generator = VariationGenerator()

    expanded = []
    
    for scenario_id in anchor_scenarios:
        # Add original
        expanded.append(scenario_id)
        
        # Add variants (as pseudo-scenario IDs for tracking)
        for i in range(2, num_variants + 1):
            variant_id = f"{scenario_id}-v{i}"
            expanded.append(variant_id)

    logger.info(
        f"Bucket {bucket_name}: {len(anchor_scenarios)} anchors → "
        f"{len(expanded)} scenarios (with {num_variants} variants)"
    )

    return expanded


if __name__ == "__main__":
    # Quick test: generate variants for a single scenario
    import asyncio

    async def test():
        gen = VariationGenerator()
        variants = await gen.generate_variants(
            scenario_id="p2-order-01",
            original_caller_text="Ich möchte eine Pizza bestellen.",
            expected_tools=["create_order"],
            phase=2,
            category="order",
            num_variants=4,
        )
        for v in variants:
            print(f"Variant {v.variant_num}: {v.variant_caller_text}")

    asyncio.run(test())
