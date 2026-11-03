"""Pure-logic tests (no simulator): residual bounds, schedule, release gate, dwell, success timer,
outcome precedence, partial resets, phase ablation, case suites. Requires torch and numpy."""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

HAVE_TORCH = importlib.util.find_spec("torch") is not None and importlib.util.find_spec("numpy") is not None

if HAVE_TORCH:
    import torch

    from csci645_handover.core import outcomes as oc
    from csci645_handover.core.case_suites import build_suites, curriculum_stage, read_suite, suite_hash, write_suite
    from csci645_handover.core.geometry import (
        GeometryCfg, GeometryCoordinator, StabilityCfg, StabilityTracker, release_decision,
    )
    from csci645_handover.core.policy_io import (
        apply_phase_mask, compose_candidate, contact_phase_onehot, residual_from_action,
    )
    from csci645_handover.core.schedule import NominalSchedule, giver_target, receiver_finger_target, receiver_nominal_target


def _signals(n, **kw):
    base = dict(
        t=torch.zeros(n), finite=torch.ones(n, dtype=torch.bool), released=torch.zeros(n, dtype=torch.bool),
        giver_width=torch.zeros(n), giver_force_l=torch.zeros(n), giver_force_r=torch.zeros(n),
        recv_force_l=torch.zeros(n), recv_force_r=torch.zeros(n), table_force=torch.zeros(n),
        obj_pos=torch.tensor([[0.0, 0.0, 0.5]]).repeat(n, 1), obj_rel_in_recv=torch.zeros(n, 3),
        obj_rel_speed=torch.zeros(n), collision_force=torch.zeros(n), release_timeout=torch.zeros(n, dtype=torch.bool),
        recv_stable_at_release=torch.ones(n, dtype=torch.bool), grasp_error=torch.zeros(n),
        giver_tcp=torch.zeros(n, 3), recv_tcp=torch.zeros(n, 3), handover_center=torch.tensor([0.0, 0.0, 0.5]),
    )
    base.update(kw)
    return base


@unittest.skipUnless(HAVE_TORCH, "torch/numpy not installed")
class ResidualTest(unittest.TestCase):
    def test_bounds_and_zero(self):
        a = torch.tensor([[1e6, -1e6, 0.0], [3.0, -0.2, 0.7]])
        r = residual_from_action(a, 0.02)
        self.assertTrue((r.abs() <= 0.02 + 1e-12).all())
        self.assertEqual(float(residual_from_action(torch.zeros(1, 3), 0.02).abs().sum()), 0.0)

    def test_no_accumulation(self):
        p_nom = torch.tensor([[0.1, 0.2, 0.3]])
        r = residual_from_action(torch.ones(1, 3), 0.02)
        p1 = compose_candidate(p_nom, r, torch.tensor([True]))
        p2 = compose_candidate(p_nom, r, torch.tensor([True]))  # same action again: same target
        torch.testing.assert_close(p1, p2)
        torch.testing.assert_close(compose_candidate(p_nom, r, torch.tensor([False])), p_nom)


@unittest.skipUnless(HAVE_TORCH, "torch/numpy not installed")
class ScheduleTest(unittest.TestCase):
    def test_waypoints(self):
        s = NominalSchedule()
        start, pre, grasp = torch.tensor([0.3, 0, 0.5]), torch.tensor([0.2, 0, 0.5]), torch.tensor([0.1, 0, 0.5])
        t = torch.tensor([0.0, 1.0, 2.0, 5.0])
        p = receiver_nominal_target(t, start, pre, grasp, s)
        torch.testing.assert_close(p[0], start)
        torch.testing.assert_close(p[1], pre)
        torch.testing.assert_close(p[2], grasp)
        torch.testing.assert_close(p[3], grasp)

    def test_finger_ramp_and_retreat_anchor(self):
        s = NominalSchedule()
        f = receiver_finger_target(torch.tensor([1.9, 2.0, 2.4, 3.0]), 0.04, 0.0, s)
        torch.testing.assert_close(f, torch.tensor([0.04, 0.04, 0.02, 0.0]))
        hold = torch.zeros(2, 3)
        cmd = torch.tensor([float("inf"), 2.0])
        g = giver_target(torch.tensor([5.0, 5.0]), hold, cmd, torch.tensor([-1.0, 0, 0]), s)
        self.assertEqual(float(g[0].abs().sum()), 0.0)  # never released -> never retreats
        self.assertAlmostEqual(float(g[1, 0]), -s.retreat_distance, places=6)  # anchored to actual command


@unittest.skipUnless(HAVE_TORCH, "torch/numpy not installed")
class ReleaseGateTest(unittest.TestCase):
    def test_geometry_off_fixed_request(self):
        t_req = torch.tensor([2.65, 2.65])
        released = torch.zeros(2, dtype=torch.bool)
        stable = torch.tensor([False, True])
        now, to = release_decision(torch.tensor([2.65, 2.60]), t_req, released, stable, False, 1.0)
        self.assertEqual(now.tolist(), [True, False])  # releases on request even without stability
        self.assertFalse(to.any())

    def test_geometry_gate_and_cap(self):
        t_req = torch.full((3,), 2.8)
        released = torch.zeros(3, dtype=torch.bool)
        stable = torch.tensor([True, False, False])
        now, to = release_decision(torch.tensor([2.7, 3.0, 3.85]), t_req, released, stable, True, 1.0)
        self.assertEqual(now.tolist(), [False, False, False])  # never before the request
        self.assertEqual(to.tolist(), [False, False, True])  # waits at most 1.0 s
        now, _ = release_decision(torch.tensor([2.8]), torch.tensor([2.8]), torch.zeros(1, dtype=torch.bool),
                                  torch.tensor([True]), True, 1.0)
        self.assertTrue(bool(now[0]))

    def test_dwell_physical_time(self):
        st = StabilityTracker(StabilityCfg(dwell_s=0.15), 1, "cpu")
        raw = torch.tensor([True])
        flags = [bool(st.update(raw, torch.tensor([0.05 * (k + 1)]), 0.05)[0]) for k in range(4)]
        self.assertEqual(flags, [False, False, True, True])  # 3 x 0.05 s = 0.15 s
        self.assertFalse(bool(st.update(torch.tensor([False]), torch.tensor([0.25]), 0.05)[0]))


@unittest.skipUnless(HAVE_TORCH, "torch/numpy not installed")
class GeometryTest(unittest.TestCase):
    def test_alignment_bounded_and_anchor(self):
        g = GeometryCoordinator(GeometryCfg(align_gain=1.0, align_max=0.015, sep_tol=0.01), 2, "cpu")
        p_nom = torch.zeros(2, 3)
        grasp_nom = torch.zeros(3)
        grasp_obj = torch.tensor([[0.01, 0, 0], [0.03, 0, 0]])
        out = g(torch.zeros(2), p_nom, p_nom, grasp_obj, grasp_nom, torch.zeros(2, 3), torch.zeros(2, dtype=torch.bool))
        torch.testing.assert_close(out["p_exec"], torch.tensor([[0.01, 0, 0], [0.015, 0, 0]]))
        self.assertEqual(out["align_saturated"].tolist(), [False, True])
        tcp = torch.tensor([[0.5, 0.5, 0.5], [0.0, 0.0, 0.0]])
        res = torch.tensor([[0.02, 0, 0], [0.0, 0, 0]])
        out = g(torch.ones(2), p_nom + res, p_nom, grasp_obj, grasp_nom, tcp, torch.tensor([True, False]))
        torch.testing.assert_close(out["p_exec"][0], torch.tensor([0.51, 0.5, 0.5]))  # anchor + clamped residual
        self.assertTrue(bool(out["shared_saturated"][0]))
        g.reset(torch.tensor([0]))
        self.assertFalse(bool(g.anchored[0]))

    def test_zero_residual_reproduces_controller(self):
        g = GeometryCoordinator(GeometryCfg(), 1, "cpu")
        p_nom = torch.tensor([[0.1, 0.0, 0.5]])
        out = g(torch.zeros(1), p_nom + 0.0, p_nom, p_nom, p_nom[0], p_nom, torch.zeros(1, dtype=torch.bool))
        torch.testing.assert_close(out["p_exec"], p_nom)


@unittest.skipUnless(HAVE_TORCH, "torch/numpy not installed")
class OutcomeTest(unittest.TestCase):
    def _holding(self, n):
        return dict(released=torch.ones(n, dtype=torch.bool), giver_width=torch.full((n,), 0.08),
                    recv_force_l=torch.ones(n), recv_force_r=torch.ones(n))

    def test_success_needs_two_continuous_seconds(self):
        ev = oc.OutcomeEvaluator(oc.OutcomeCfg(), 1, "cpu")
        active = torch.ones(1, dtype=torch.bool)
        dt = 0.05
        reasons = []
        for k in range(70):
            kw = self._holding(1)
            if k == 20:  # one broken step resets the timer
                kw["table_force"] = torch.ones(1)
            reasons.append(int(ev.update(_signals(1, t=torch.tensor([3.0 + k * dt]), **kw), active, dt, 2.0, 8.0)[0]))
        first = reasons.index(oc.SUCCESS)
        self.assertEqual(first, 20 + 40)  # 40 steps x 0.05 s after the break

    def test_no_success_while_supported(self):
        for extra in ({"table_force": torch.ones(1)}, {"giver_force_l": torch.ones(1)},
                      {"giver_width": torch.zeros(1)}, {"released": torch.zeros(1, dtype=torch.bool)}):
            ev = oc.OutcomeEvaluator(oc.OutcomeCfg(), 1, "cpu")
            for k in range(100):
                kw = self._holding(1)
                kw.update(extra)
                r = ev.update(_signals(1, t=torch.tensor([3.0 + k * 0.05]), **kw), torch.ones(1, dtype=torch.bool), 0.05, 2.0, 8.0)
                self.assertNotEqual(int(r[0]), oc.SUCCESS)

    def test_precedence(self):
        ev = oc.OutcomeEvaluator(oc.OutcomeCfg(collision_terminal_s=0.0), 1, "cpu")
        kw = dict(finite=torch.zeros(1, dtype=torch.bool), collision_force=torch.full((1,), 10.0),
                  obj_pos=torch.tensor([[0.0, 0.0, 0.1]]), release_timeout=torch.ones(1, dtype=torch.bool),
                  t=torch.tensor([8.0]))
        r = ev.update(_signals(1, **kw), torch.ones(1, dtype=torch.bool), 0.05, 2.0, 8.0)
        self.assertEqual(int(r[0]), oc.INFRA_ERROR)
        kw["finite"] = torch.ones(1, dtype=torch.bool)
        ev.reset(torch.tensor([0]))
        self.assertEqual(int(ev.update(_signals(1, **kw), torch.ones(1, dtype=torch.bool), 0.05, 2.0, 8.0)[0]), oc.COLLISION)
        kw["collision_force"] = torch.zeros(1)
        ev.reset(torch.tensor([0]))
        self.assertEqual(int(ev.update(_signals(1, **kw), torch.ones(1, dtype=torch.bool), 0.05, 2.0, 8.0)[0]), oc.DROP)
        kw["obj_pos"] = torch.tensor([[0.0, 0.0, 0.5]])
        ev.reset(torch.tensor([0]))
        self.assertEqual(int(ev.update(_signals(1, **kw), torch.ones(1, dtype=torch.bool), 0.05, 2.0, 8.0)[0]), oc.RELEASE_TIMEOUT)

    def test_partial_reset_isolated(self):
        ev = oc.OutcomeEvaluator(oc.OutcomeCfg(), 2, "cpu")
        for k in range(10):
            ev.update(_signals(2, t=torch.full((2,), 3.0 + 0.05 * k), **self._holding(2)), torch.ones(2, dtype=torch.bool), 0.05, 2.0, 8.0)
        ev.reset(torch.tensor([1]))
        self.assertGreater(float(ev.hold_timer[0]), 0.4)
        self.assertEqual(float(ev.hold_timer[1]), 0.0)
        self.assertTrue(bool(ev.ref_set[0]))
        self.assertFalse(bool(ev.ref_set[1]))


@unittest.skipUnless(HAVE_TORCH, "torch/numpy not installed")
class PhaseTest(unittest.TestCase):
    def test_onehot_from_contacts(self):
        g = torch.tensor([True, True, False, False])
        r = torch.tensor([False, True, True, False])
        torch.testing.assert_close(contact_phase_onehot(g, r), torch.eye(4))

    def test_mask_only_phase_channels(self):
        obs = torch.randn(5, 46)
        out = apply_phase_mask(obs, slice(42, 46), phase_input=False)
        self.assertEqual(float(out[:, 42:46].abs().sum()), 0.0)
        torch.testing.assert_close(out[:, :42], obs[:, :42])
        torch.testing.assert_close(apply_phase_mask(obs, slice(42, 46), True), obs)
        # empirical normalization of an all-zero channel stays zero: (0 - 0) / (0 + eps) = 0
        mean, std = out[:, 42:46].mean(0), out[:, 42:46].std(0)
        self.assertEqual(float(((out[:, 42:46] - mean) / (std + 1e-2)).abs().sum()), 0.0)


@unittest.skipUnless(HAVE_TORCH, "torch/numpy not installed")
class CaseSuiteTest(unittest.TestCase):
    def test_repeatable_disjoint_and_bounded(self):
        protocol = json.loads((ROOT / "configs/protocol.json").read_text())
        a = build_suites(protocol, "cfg")
        b = build_suites(protocol, "cfg")
        for k in a:
            self.assertEqual(suite_hash(a[k]), suite_hash(b[k]))
        ids = [set(c["case_id"] for c in a[k]) for k in a]
        self.assertFalse(ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
        self.assertEqual(len(a["final"]), 9 * 200)
        self.assertEqual(len(a["validation"]), 100)
        conds = {c["id"]: c for c in protocol["evaluation"]["conditions"]}
        for case in a["final"]:
            bound = conds[case["condition"]]["position_bound_m"]
            self.assertTrue(all(abs(v) <= bound + 1e-12 for v in case["requested_offset_xyz_m"]))
            self.assertEqual(case["release_offset_s"], conds[case["condition"]]["release_offset_s"])
        for case in a["validation"]:
            self.assertLessEqual(abs(case["release_offset_s"]), 0.15)

    def test_roundtrip(self):
        import tempfile

        protocol = json.loads((ROOT / "configs/protocol.json").read_text())
        cases = build_suites(protocol, "cfg")["validation"]
        with tempfile.TemporaryDirectory() as d:
            h = write_suite(Path(d) / "v.jsonl", cases)
            back, h2 = read_suite(Path(d) / "v.jsonl")
            self.assertEqual(h, h2)
            self.assertEqual(back, cases)

    def test_curriculum(self):
        cur = json.loads((ROOT / "configs/protocol.json").read_text())["training"]["curriculum"]
        self.assertEqual(curriculum_stage(cur, 0.0)["position_bound_m"], 0.0)
        self.assertEqual(curriculum_stage(cur, 0.3)["position_bound_m"], 0.005)
        self.assertEqual(curriculum_stage(cur, 0.99)["release_offset_bound_s"], 0.15)
        self.assertEqual(curriculum_stage(cur, 1.0)["position_bound_m"], 0.01)


if __name__ == "__main__":
    unittest.main()
