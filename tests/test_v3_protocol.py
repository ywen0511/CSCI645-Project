import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from csci645_handover.v3_protocol import make_cases, validate_records
from csci645_handover.runtime import V2_CONTROLLER_DEFAULTS, config_hash


class ProtocolTest(unittest.TestCase):
    def test_disabled_v3_fields_preserve_legacy_config_hash(self):
        old = SimpleNamespace(sim=SimpleNamespace(dt=1/120), scene=SimpleNamespace(num_envs=32), observation_space=46)
        new = copy.deepcopy(old)
        for key, value in V2_CONTROLLER_DEFAULTS.items():
            setattr(new, key, value)
        self.assertEqual(config_hash(old), config_hash(new))
        new.observation_sensor = {"noise_std_m": 0.002}
        self.assertNotEqual(config_hash(old), config_hash(new))

    def test_disjoint_reproducible_splits(self):
        splits = [make_cases(k) for k in ("development", "validation", "final")]
        self.assertEqual([len(s) for s in splits], [312, 240, 2600])
        self.assertEqual(splits[0], make_cases("development"))
        ids = [r["case_id"] for s in splits for r in s]
        self.assertEqual(len(set(ids)), len(ids))
        seed_sets = [{r["observation_error"]["seed"] for r in s} for s in splits]
        self.assertFalse(seed_sets[0] & seed_sets[1] | seed_sets[0] & seed_sets[2] | seed_sets[1] & seed_sets[2])

    def test_paired_severities_and_clean(self):
        cases = {c["condition"]: c for c in make_cases("development") if c["case_id"].endswith("0000")}
        for name, c in cases.items():
            if name != "clean":
                self.assertEqual(c["requested_offset_xyz_m"], cases["physical_only"]["requested_offset_xyz_m"])
                self.assertEqual(c["release_offset_s"], cases["physical_only"]["release_offset_s"])
        self.assertEqual(cases["clean"]["requested_offset_xyz_m"], [0, 0, 0])
        self.assertEqual(cases["delay_4step"]["observation_error"]["delay_steps"], 4)

    def test_completion_does_not_trust_status_file(self):
        cases = make_cases("development")[:2]
        rows = [{"case_id": c["case_id"], "condition": c["condition"], "observation_error": c["observation_error"],
                 "success": True, "reset_valid": True, "terminal_reason": "success", "checkpoint_sha256": "abc"}
                for c in cases]
        expected = {"checkpoint_sha256": "abc"}
        self.assertEqual(validate_records(rows, cases, expected, complete=True)["missing"], 0)
        for bad in (rows[:1], rows + rows[:1], [{**rows[0], "case_id": "extra"}, rows[1]],
                    [{**rows[0], "checkpoint_sha256": "changed"}, rows[1]]):
            with self.assertRaises(ValueError):
                validate_records(bad, cases, expected, complete=True)
        bad = copy.deepcopy(rows)
        bad[0]["observation_error"]["seed"] += 1
        with self.assertRaises(ValueError):
            validate_records(bad, cases, expected)


if __name__ == "__main__":
    unittest.main()
