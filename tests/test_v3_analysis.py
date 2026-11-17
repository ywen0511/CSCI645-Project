import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from csci645_handover.v3_analysis import paired_effect


class AnalysisTest(unittest.TestCase):
    def test_identical_controllers_have_zero_paired_difference(self):
        a = np.random.default_rng(10).integers(0, 2, (5, 3, 20))
        result = paired_effect(a, a, repeats=100)
        self.assertEqual([result[k] for k in ("difference_pp", "ci_low_pp", "ci_high_pp")], [0, 0, 0])

    def test_deterministic_is_not_duplicated_training_evidence(self):
        a, b = np.ones((5, 2, 20)), np.zeros((1, 2, 20))
        result = paired_effect(a, b, repeats=100)
        self.assertEqual(result["difference_pp"], 100)
        self.assertEqual(result["training_seed_pairs"], 5)
        self.assertEqual(result["base_case_clusters"], 20)

    def test_shared_severity_clusters_preserved(self):
        a = np.array([[[1, 0, 1, 0], [0, 1, 0, 1]]])
        result = paired_effect(a, np.zeros_like(a), repeats=100)
        # Every paired cluster has mean .5, hence no bootstrap variance.
        self.assertEqual(result["ci_low_pp"], 50)
        self.assertEqual(result["ci_high_pp"], 50)


if __name__ == "__main__":
    unittest.main()
