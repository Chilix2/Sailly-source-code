"""
tests/test_scenario_load.py — Unit tests for scenario loading
"""
import unittest
from pathlib import Path
from src.scenario_loader import load_scenario_file, load_all_scenarios


class TestScenarioLoader(unittest.TestCase):
    def test_load_phase0_greeting(self):
        """Load phase 0 greeting scenario."""
        scenario_path = Path(__file__).parent.parent / "scenarios" / "phase0" / "test_0_1_greeting.yaml"
        if not scenario_path.exists():
            self.skipTest(f"Scenario not found: {scenario_path}")

        scenario = load_scenario_file(scenario_path)
        self.assertIsNotNone(scenario)
        self.assertEqual(scenario.id, "phase0_test_0_1_greeting")
        self.assertEqual(scenario.phase, 0)

    def test_load_phase1_reservation(self):
        """Load phase 1 reservation scenario."""
        scenario_path = Path(__file__).parent.parent / "scenarios" / "phase1" / "test_1_1_clean_reservation.yaml"
        if not scenario_path.exists():
            self.skipTest(f"Scenario not found: {scenario_path}")

        scenario = load_scenario_file(scenario_path)
        self.assertIsNotNone(scenario)
        self.assertEqual(scenario.phase, 1)
        self.assertGreater(len(scenario.caller_goal), 0)
        self.assertIn("name", scenario.caller_identity)


if __name__ == "__main__":
    unittest.main()
