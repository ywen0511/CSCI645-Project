"""CPU tests of the V4 in-grasp offset sampler and calibrated giver reference (no simulator)."""
import math
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from csci645_handover.core.grasp import (GiverCalibrator, quat_apply, quat_apply_inverse, sample_train_offsets,
                                          window_frames)


def rot_matrix_xyzw(q):
    x, y, z, w = q
    return torch.tensor([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def test_quaternion_helpers_match_rotation_matrix():
    g = torch.Generator().manual_seed(0)
    q = torch.randn(16, 4, generator=g)
    q = q / q.norm(dim=-1, keepdim=True)
    v = torch.randn(16, 3, generator=g)
    ref = torch.stack([rot_matrix_xyzw(qq.tolist()) @ vv for qq, vv in zip(q, v)])
    assert torch.allclose(quat_apply(q, v), ref, atol=1e-5)
    assert torch.allclose(quat_apply_inverse(q, quat_apply(q, v)), v, atol=1e-5)


def test_giver_hand_frame_quaternion_axes():
    # the task's giver hand: z (approach) along +x world, y (finger travel) along +y world
    s = 1 / math.sqrt(2)
    q = torch.tensor([[0.0, s, 0.0, s]])  # 90 deg about y: hand z -> world x
    assert torch.allclose(quat_apply(q, torch.tensor([[0.0, 0.0, 1.0]])), torch.tensor([[1.0, 0.0, 0.0]]), atol=1e-6)


@pytest.mark.parametrize("window,frames", [(0.1, 2), (0.25, 5), (0.5, 10)])
def test_window_frames(window, frames):
    assert window_frames(window, 0.05) == frames


def run_window(cal, n, frames_seq, meas, kin, q, valid=None, fresh=None):
    for k in frames_seq:
        f = torch.full((n,), k, dtype=torch.long)
        cal.update(torch.ones(n, dtype=torch.bool) if fresh is None else fresh, f,
                   torch.ones(n, dtype=torch.bool) if valid is None else valid(k), meas(k), kin, q)


def test_calibrator_mean_timing_and_isolation():
    n = 3
    q = torch.tensor([[0.0, 0.0, 0.0, 1.0]] * n)
    kin = torch.zeros(n, 3)
    true = torch.tensor([[0.005, 0.0, -0.002], [0.0, 0.0, 0.0], [-0.01, 0.0, 0.01]])
    noise = lambda k: torch.tensor([[0.001 * (-1) ** k, 0, 0]] * n)  # noqa: E731
    cal = GiverCalibrator(n, 4, "cpu")
    run_window(cal, n, [-3, -2, -1], lambda k: true + 1.0, kin, q)  # settling frames never count
    assert cal.count.tolist() == [0, 0, 0] and not cal.closed.any()
    run_window(cal, n, [0, 1, 2], lambda k: true + noise(k), kin, q)
    assert not cal.closed.any() and torch.equal(cal.correction(q), torch.zeros(n, 3))  # fixed transform until closed
    run_window(cal, n, [3], lambda k: true + noise(k), kin, q)
    assert cal.closed.all() and cal.count.tolist() == [4, 4, 4]
    assert torch.allclose(cal.correction(q), true, atol=1e-7)  # alternating noise cancels over 4 frames
    run_window(cal, n, [4, 5, 6], lambda k: true + 0.5, kin, q)  # later frames never change the estimate
    assert torch.allclose(cal.correction(q), true, atol=1e-7)
    cal.reset(torch.tensor([1]))
    assert cal.count.tolist() == [4, 0, 4] and cal.closed.tolist() == [True, False, True]
    assert torch.allclose(cal.correction(q)[[0, 2]], true[[0, 2]], atol=1e-7)


def test_calibrator_skips_invalid_and_repeated_frames():
    n = 2
    q = torch.tensor([[0.0, 0.0, 0.0, 1.0]] * n)
    kin = torch.zeros(n, 3)
    cal = GiverCalibrator(n, 3, "cpu")
    valid = lambda k: torch.tensor([k != 1, False])  # noqa: E731
    run_window(cal, n, [0, 1, 2], lambda k: torch.full((n, 3), float(k)), kin, q, valid=valid)
    assert cal.count.tolist() == [2, 0] and cal.closed.all()
    assert torch.allclose(cal.offset_h[0], torch.full((3,), 1.0))  # mean of frames 0 and 2
    assert torch.equal(cal.correction(q)[1], torch.zeros(3))  # no valid frame -> fixed transform
    cal.reset(torch.arange(n))
    stale = torch.tensor([False, True])
    run_window(cal, n, [0, 1, 2], lambda k: torch.ones(n, 3), kin, q, fresh=stale)
    assert cal.count.tolist() == [0, 3]  # repeated reads at one token never accumulate


def test_calibrator_rotates_with_hand_frame():
    s = 1 / math.sqrt(2)
    q = torch.tensor([[0.0, s, 0.0, s]])
    cal = GiverCalibrator(1, 1, "cpu")
    world = torch.tensor([[0.004, 0.0, -0.003]])
    cal.update(torch.tensor([True]), torch.tensor([0]), torch.tensor([True]), world, torch.zeros(1, 3), q)
    assert torch.allclose(cal.correction(q), world, atol=1e-7)
    assert not torch.allclose(cal.offset_h, world)


def test_train_offsets_bounds_clean_and_determinism():
    spec = {"bound_xyz_m": [0.005, 0.0, 0.004], "clean_probability": 0.25}
    a = sample_train_offsets(4000, spec, torch.Generator().manual_seed(7), "cpu")
    b = sample_train_offsets(4000, spec, torch.Generator().manual_seed(7), "cpu")
    assert torch.equal(a, b)
    assert (a[:, 0].abs() <= 0.005).all() and (a[:, 1] == 0).all() and (a[:, 2].abs() <= 0.004).all()
    clean = (a == 0).all(-1).float().mean().item()
    assert 0.2 < clean < 0.3
    assert torch.equal(sample_train_offsets(5, None, torch.Generator(), "cpu"), torch.zeros(5, 3))
