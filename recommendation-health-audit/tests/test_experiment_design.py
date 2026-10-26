import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiment_design import build_plan, two_proportion_sample_size_per_arm


class ExperimentPlanningTests(unittest.TestCase):
    def test_smaller_effect_requires_more_observations(self):
        small = two_proportion_sample_size_per_arm(0.01, 0.05)
        large = two_proportion_sample_size_per_arm(0.01, 0.20)
        self.assertGreater(small, large)
        self.assertGreater(large, 0)

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            two_proportion_sample_size_per_arm(0, 0.1)
        with self.assertRaises(ValueError):
            two_proportion_sample_size_per_arm(0.5, 2)

    def test_plan_labels_scenarios_as_planning_only(self):
        metrics = {"position_comparison": {"ranks_2_to_10_ctr": 0.0013805}}
        plan = build_plan(metrics)
        self.assertIn("planning scenario only", plan["status"])
        self.assertEqual(plan["design"]["randomization_unit"], "User, to keep assignment stable across repeated slates and reduce cross-arm contamination.")
        self.assertEqual(len(plan["power_scenarios"]["scenarios"]), 3)


if __name__ == "__main__":
    unittest.main()
