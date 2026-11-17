"""CPU tests for the V5 slip mechanism logic, the re-estimating giver reference and the Study B case design."""

import random
import types

import pytest

torch = pytest.importorskip("torch")

from csci645_handover import runtime as rt  # noqa: E402
from csci645_handover import v5_protocol as v5  # noqa: E402
from csci645_handover.core import slip as sl  # noqa: E402
from csci645_handover.core.grasp import GiverCalibrator  # noqa: E402

DT = 1.0 / 120.0
MASS = 0.15


def regulate(target_x, friction_n, onset=1.0, duration=0.25, gains=None, t_end=2.0):
    """Toy 1-D bar with Coulomb friction driven by the regulator; returns (regulator, trajectory)."""
    g = gains or {"kp": 4000.0, "kd": 40.0, "ki": 40000.0, "force_max_n": 30.0}
    reg = sl.SlipRegulator(1, "cpu", regrip_s=0.1, tolerance_m=0.0015, **g)
    reg.reset(torch.tensor([0]), torch.tensor([[target_x, 0.0, 0.0]]), torch.tensor([onset]), torch.tensor([duration]))
    x, v, traj = 0.003, 0.0, []  # arbitrary pre-existing in-grasp offset
    t = 0.0
    while t < t_end:
        d = torch.tensor([[x, 0.0, 0.0]])
        f = float(reg.step(torch.tensor([t]), d, torch.tensor([True]), DT)[0, 0])
        ph = int(reg.phase[0])
        fric = friction_n if ph in (sl.SLIDING,) else 70.0  # re-grip restores the full squeeze
        if abs(v) < 1e-9 and abs(f) <= fric:
            v = 0.0
        else:
            sgn = (v > 0) - (v < 0) if abs(v) >= 1e-9 else (1 if f > 0 else -1)
            a = (f - fric * sgn) / MASS
            v_new = v + a * DT
            if v != 0.0 and (v_new > 0) != (v > 0):
                v_new = 0.0
            v = v_new
        x += v * DT
        traj.append((t, x, f, ph))
        t += DT
    return reg, traj


@pytest.mark.parametrize("target", [-0.007, -0.002, 0.005, 0.010, 0.015])
def test_regulator_reaches_target_with_friction(target):
    reg, traj = regulate(target, friction_n=10.0)
    assert bool(reg.completed[0]) and bool(reg.valid[0])
    assert abs(float(reg.realized[0, 0]) - target) <= 0.0015
    assert all(f == 0.0 for t, _, f, _ in traj if t < 1.0 - 1e-9 or t > 1.0 + 0.25 + 0.1 + DT)


def test_regulator_saturation_makes_slip_invalid():
    reg, _ = regulate(0.015, friction_n=40.0, gains={"kp": 4000.0, "kd": 40.0, "ki": 0.0, "force_max_n": 5.0})
    assert bool(reg.completed[0]) and not bool(reg.valid[0])


def test_no_slip_is_inactive():
    reg = sl.SlipRegulator(2, "cpu", kp=1.0, kd=1.0, ki=1.0, force_max_n=10.0, regrip_s=0.1, tolerance_m=0.0015)
    reg.reset(torch.arange(2), torch.zeros(2, 3), torch.zeros(2), torch.zeros(2))
    for k in range(300):
        f = reg.step(torch.full((2,), k * DT), torch.rand(2, 3), torch.ones(2, dtype=torch.bool), DT)
        assert float(f.abs().max()) == 0.0
    assert not reg.completed.any() and reg.valid.all()


def test_unscored_envs_get_no_force():
    reg = sl.SlipRegulator(1, "cpu", kp=4000.0, kd=40.0, ki=0.0, force_max_n=30.0, regrip_s=0.1, tolerance_m=0.0015)
    reg.reset(torch.tensor([0]), torch.tensor([[0.01, 0, 0]]), torch.tensor([0.0]), torch.tensor([0.25]))
    f = reg.step(torch.tensor([0.1]), torch.zeros(1, 3), torch.tensor([False]), DT)
    assert float(f.abs().max()) == 0.0


def test_minjerk():
    u = torch.tensor([-1.0, 0.0, 0.5, 1.0, 2.0])
    assert torch.allclose(sl.minjerk(u), torch.tensor([0.0, 0.0, 0.5, 1.0, 1.0]))
    assert float(sl.minjerk_rate(torch.tensor([0.5]))) == pytest.approx(1.875)


def test_train_slip_draw_clamps_cumulative():
    g = torch.Generator().manual_seed(0)
    gx = torch.full((5000,), 0.012)
    s, on, du = sl.sample_train_slip(5000, v5.TRAIN_SLIP, gx, g, "cpu")
    assert float((gx + s[:, 0])[du > 0].min()) >= v5.CUMULATIVE_X[0] - 1e-7
    active = du > 0
    assert 0.4 < float(active.float().mean()) < 0.6
    assert float((gx + s[:, 0])[active].max()) <= v5.CUMULATIVE_X[1] + 1e-7
    assert float(s[~active].abs().max()) == 0.0
    assert float(on[active].min()) >= 0.7 and float(on[active].max()) <= 1.4
    assert float(s[:, 1:].abs().max()) == 0.0


def test_tracking_calibrator_follows_a_later_change_and_one_shot_does_not():
    n, frames = 1, 10
    q = torch.tensor([[0.0, 0.0, 0.0, 1.0]])
    track, shot = sl.TrackingCalibrator(n, frames, "cpu", alpha=0.3), GiverCalibrator(n, frames, "cpu")
    ones = torch.ones(n, dtype=torch.bool)
    for k in range(60):
        offset = 0.0 if k < 20 else 0.01  # the bar slips by 1 cm after the window
        meas, kin = torch.tensor([[offset, 0.0, 0.0]]), torch.zeros(n, 3)
        for c in (track, shot):
            c.update(ones, torch.tensor([k]), ones, meas, kin, q)
    assert float(shot.correction(q)[0, 0]) == pytest.approx(0.0)
    assert float(track.correction(q)[0, 0]) == pytest.approx(0.01, abs=1e-4)
    assert int(track.updates[0]) == 50


def test_tracking_ignores_frames_without_giver_contact():
    q = torch.tensor([[0.0, 0.0, 0.0, 1.0]])
    c = sl.TrackingCalibrator(1, 2, "cpu", alpha=0.5)
    on, off = torch.ones(1, dtype=torch.bool), torch.zeros(1, dtype=torch.bool)
    for k in range(10):
        c.update(on, torch.tensor([k]), off if k >= 2 else on, torch.tensor([[0.02, 0, 0]]) if k >= 2 else torch.zeros(1, 3),
                 torch.zeros(1, 3), q)
    assert float(c.correction(q)[0, 0]) == 0.0


def test_case_design_deterministic_paired_and_clamped():
    a = v5.make_cases("final")
    b = v5.make_cases("final")
    assert a == b and len(a) == 8 * 200
    by = {}
    for r in a:
        by.setdefault(r["base_case_id"], {})[r["condition"]] = r
        x = r["grasp_offset_xyz_m"][0] + r["slip_xyz_m"][0]
        if r["slip_duration_s"] > 0:  # cumulative clamp applies to slipping cases (static starts may reach +15 mm)
            assert v5.CUMULATIVE_X[0] - 1e-9 <= x <= v5.CUMULATIVE_X[1] + 1e-9
        if r["slip_duration_s"] > 0:
            assert 0.7 <= r["slip_onset_s"] <= 1.4
            assert r["slip_onset_s"] + r["slip_duration_s"] + 0.1 <= 1.8 + 1e-9
        assert r["slip_xyz_m"][1:] == [0.0, 0.0]
    for conds in by.values():
        onsets = {r["slip_onset_s"] for r in conds.values() if r["slip_duration_s"] > 0}
        assert len(onsets) == 1  # onset paired across conditions
        assert conds["slip_pos_10"]["slip_xyz_m"][0] == pytest.approx(0.010)
        assert conds["slip_after_offset"]["grasp_offset_xyz_m"][0] == pytest.approx(0.010)
        assert conds["slip_after_offset"]["slip_xyz_m"][0] == pytest.approx(-0.010)
        assert conds["clean"]["slip_duration_s"] == 0.0 and conds["static_mixed_id"]["slip_duration_s"] == 0.0
        # the in-grasp start and sensor of the slip_mixed_id case follow the V4 mixed_id rule family
        assert conds["slip_mixed_id"]["observation_error"]["noise_std_m"] == 0.002
    ids = [r["case_id"] for r in a]
    assert len(set(ids)) == len(ids) and all(i.startswith("v5slip-final-") for i in ids)


def test_splits_are_disjoint_and_seeded_apart_from_v4():
    seen = set()
    for split in ("development", "validation", "final"):
        ids = {r["case_id"] for r in v5.make_cases(split)}
        assert not (ids & seen)
        seen |= ids
    assert set(v5.SPLIT_SEEDS.values()).isdisjoint({6456101, 6456201, 6456301, 6457301})


def test_probe_cases():
    rows = v5.probe_cases()
    assert len(rows) == (1 + 7 * 3) * 4
    r = [x for x in rows if x["condition"] == "x+15_on140"][0]
    assert r["slip_xyz_m"][0] == pytest.approx(0.015) and r["slip_onset_s"] == pytest.approx(1.4)


def _fake_cfg(**extra):
    base = dict(method="geometry", geometry_enabled=True, residual_enabled=False, phase_input=True, seed=0,
                align_max=0.025, giver_calibration_window_s=0.5, grasp_uncertainty=True,
                observation_giver_reference=True, observation_sensor={"ema_alpha": 0.2})
    base.update(extra)
    ns = types.SimpleNamespace(**base)
    ns.sim = types.SimpleNamespace(dt=1 / 120)
    ns.scene = types.SimpleNamespace(num_envs=16)
    return ns


def test_v4_config_hash_unchanged_when_slip_is_off():
    v4_like = rt.config_hash(_fake_cfg())
    off = rt.config_hash(_fake_cfg(slip_mechanism=None, slip_train=None, giver_tracking_alpha=None))
    on = rt.config_hash(_fake_cfg(slip_mechanism={"kp": 1.0}, slip_train=None, giver_tracking_alpha=None))
    assert v4_like == off and on != off


def test_runtime_fields_include_v5_controller_switches():
    assert {"giver_tracking_alpha", "slip_mechanism"} <= rt.RUNTIME_FIELDS
    assert "slip_train" not in rt.RUNTIME_FIELDS
    random.seed(0)
