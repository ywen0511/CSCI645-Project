"""CPU-only sensor invariants; never initializes a simulator/CUDA/MPS device."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import torch

from csci645_handover.core.observation import ObservationHistory, PositionSensor, normal_at


class SensorTest(unittest.TestCase):
    def test_identity_and_repeat_read(self):
        s = PositionSensor(2, "cpu")
        p = torch.tensor([[1., 2., 3.], [4., 5., 6.]])
        torch.testing.assert_close(s.update(p, 0), p, rtol=0, atol=0)
        torch.testing.assert_close(s.update(p + 1, 0), p, rtol=0, atol=0)
        self.assertEqual(s.frames.tolist(), [1, 1])
        torch.testing.assert_close(s.update(p + 1, 1), p + 1, rtol=0, atol=0)

    def test_delay_causal_and_startup(self):
        s = PositionSensor(1, "cpu", max_delay=2)
        s.reset([0], delay=[2], bias=[[0.1, 0., 0.]])
        values = []
        for k in range(5):
            values.append(s.update(torch.full((1, 3), float(k)), k).clone())
        for k, value in enumerate(values):
            expected = torch.full((1, 3), float(max(0, k - 2)))
            expected[:, 0] += 0.1
            torch.testing.assert_close(value, expected)

    def test_seed_pairing_independent_of_slot_and_reset(self):
        a, b = PositionSensor(3, "cpu"), PositionSensor(1, "cpu")
        a.reset([0, 1, 2], seeds=[43, 72, 99], sigma=[0.01] * 3)
        b.reset([0], seeds=[72], sigma=[0.01])
        for k in range(10):
            if k == 4:
                a.reset([0, 2], seeds=[999, 1000])
            va, vb = a.update(torch.zeros(3, 3), k), b.update(torch.zeros(1, 3), k)
            torch.testing.assert_close(va[1], vb[0], rtol=0, atol=0)

    def test_reset_retry_replays_same_errors(self):
        s = PositionSensor(1, "cpu", alpha=0.2)
        s.reset([0], seeds=[99], sigma=[0.002], delay=[2])
        before = [s.update(torch.ones(1, 3) * k, k).clone() for k in range(8)]
        s.reset([0])
        after = [s.update(torch.ones(1, 3) * k, k + 20).clone() for k in range(8)]
        for a, b in zip(before, after):
            torch.testing.assert_close(a, b, rtol=0, atol=0)

    def test_filter_no_future_and_reset_no_leak(self):
        s = PositionSensor(2, "cpu", alpha=0.5)
        s.update(torch.zeros(2, 3), 0)
        torch.testing.assert_close(s.update(torch.ones(2, 3), 1), torch.full((2, 3), 0.5))
        s.reset([0])
        out = s.update(torch.ones(2, 3) * 10, 2)
        torch.testing.assert_close(out[0], torch.full((3,), 10.))
        torch.testing.assert_close(out[1], torch.full((3,), 5.25))

    def test_noise_moments_and_lag(self):
        # Broad statistical guard for accidentally correlated/constant hash streams.
        n = 30000
        z = normal_at(torch.full((n,), 12345, dtype=torch.long), torch.arange(n)).double()
        self.assertLess(abs(float(z.mean())), 0.025)
        self.assertLess(abs(float(z.std()) - 1), 0.025)
        self.assertLess(abs(float((z[1:] * z[:-1]).mean())), 0.025)

    def test_invalid_settings_rejected(self):
        with self.assertRaises(ValueError):
            PositionSensor(1, "cpu", alpha=0)
        s = PositionSensor(1, "cpu", max_delay=2)
        for kwargs in ({"delay": [3]}, {"sigma": [-0.1]}, {"bias": [[float("nan"), 0, 0]]}):
            with self.assertRaises(ValueError):
                s.reset([0], **kwargs)


class HistoryTest(unittest.TestCase):
    def test_order_padding_idempotence_and_partial_reset(self):
        h = ObservationHistory(2, 1, 3, "cpu")
        torch.testing.assert_close(h.update(torch.tensor([[1.], [2.]]), 0), torch.tensor([[1., 1., 1.], [2., 2., 2.]]))
        h.update(torch.tensor([[3.], [4.]]), 1)
        torch.testing.assert_close(h.update(torch.tensor([[99.], [99.]]), 1), torch.tensor([[1., 1., 3.], [2., 2., 4.]]))
        h.reset([0])
        torch.testing.assert_close(h.update(torch.tensor([[5.], [6.]]), 2), torch.tensor([[5., 5., 5.], [2., 4., 6.]]))


if __name__ == "__main__":
    unittest.main()
