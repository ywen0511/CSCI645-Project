"""v2 pure-logic tests: geometry component flags, v2 selection rule, constant-offset grid ordering."""

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
HAVE_TORCH = importlib.util.find_spec("torch") is not None

from csci645_handover.selection import select_v2  # noqa: E402

if HAVE_TORCH:
    import torch

    from csci645_handover.core.geometry import GeometryCfg, GeometryCoordinator, release_decision


@unittest.skipUnless(HAVE_TORCH, "torch not installed")
class GeometryFlagsTest(unittest.TestCase):
    def _run(self, **flags):
        g = GeometryCoordinator(GeometryCfg(1.0, 0.01, 0.01, 1.0, **flags), 2, "cpu")
        p_nom = torch.zeros(2, 3)
        p_cand = torch.tensor([[0.0, 0.0, 0.0], [0.03, 0.0, 0.0]])
        grasp = torch.tensor([[0.004, -0.02, 0.0], [0.0, 0.0, 0.0]])
        tcp = torch.tensor([[0.1, 0.1, 0.1], [0.2, 0.2, 0.2]])
        stable = torch.tensor([False, True])
        return g(torch.zeros(2), p_cand, p_nom, grasp, torch.zeros(3), tcp, stable)

    def test_full_matches_definition(self):
        out = self._run()
        torch.testing.assert_close(out["p_exec"][0], torch.tensor([0.004, -0.01, 0.0]))
        torch.testing.assert_close(out["p_exec"][1], torch.tensor([0.21, 0.2, 0.2]))  # anchor + clamped dev

    def test_no_alignment_adds_zero(self):
        out = self._run(align_enabled=False)
        torch.testing.assert_close(out["p_exec"][0], torch.zeros(3))
        self.assertFalse(bool(out["align_saturated"].any()))

    def test_no_anchor_keeps_candidate(self):
        out = self._run(anchor_enabled=False)
        self.assertFalse(bool(out["anchored"].any()))
        torch.testing.assert_close(out["p_exec"][1], torch.tensor([0.03, 0.0, 0.0]))

    def test_gate_off_follows_schedule(self):
        t = torch.tensor([3.0]); req = torch.tensor([2.8]); rel = torch.tensor([False]); st = torch.tensor([False])
        now, to = release_decision(t, req, rel, st, False, 1.0)
        self.assertTrue(bool(now[0])); self.assertFalse(bool(to[0]))
        now, _ = release_decision(t, req, rel, st, True, 1.0)
        self.assertFalse(bool(now[0]))


class SelectionV2Test(unittest.TestCase):
    def c(self, t, s, col, sq):
        return {"checkpoint": f"step_{t}", "transitions": t, "success_rate": s, "collision_rate": col,
                "residual_sq_norm_mean_m2": sq}

    def test_step0_excluded(self):
        cands = [self.c(0, 1.0, 0.0, 0.0), self.c(2_000_000, 0.9, 0.0, 1e-4)]
        self.assertEqual(select_v2(cands)["transitions"], 2_000_000)

    def test_tie_breaks(self):
        a, b = self.c(2_000_000, 0.9, 0.01, 1e-4), self.c(4_000_000, 0.9, 0.0, 2e-4)
        self.assertIs(select_v2([a, b]), b)  # fewer collisions wins
        a, b = self.c(2_000_000, 0.9, 0.0, 1e-4), self.c(4_000_000, 0.9, 0.0, 2e-4)
        self.assertIs(select_v2([a, b]), a)  # smaller residual wins
        a, b = self.c(2_000_000, 0.9, 0.0, 1e-4), self.c(4_000_000, 0.9, 0.0, 1e-4)
        self.assertIs(select_v2([a, b]), b)  # latest wins a full tie

    def test_missing_metric_rejected(self):
        with self.assertRaises(ValueError):
            select_v2([{"checkpoint": "x", "transitions": 1, "success_rate": 1.0, "collision_rate": None,
                        "residual_sq_norm_mean_m2": 0.0}])


if __name__ == "__main__":
    unittest.main()
