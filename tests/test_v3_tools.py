"""CPU integration checks using synthetic fixtures, never scientific results."""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover.v3_protocol import make_cases, sha256, write_json


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToolsTest(unittest.TestCase):
    def test_preparation_and_final_guard(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in ("configs/v2/protocol.json", "configs/v3/protocol.draft.json"):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, target)
            prepare = script("v3_prepare").prepare
            manifest = prepare(root)
            self.assertEqual(manifest["development"]["cases"], 312)
            self.assertEqual(manifest, prepare(root))
            protocols = [json.loads(p.read_text()) for p in (root / "configs/v3/training").glob("*.json")]
            self.assertEqual(sum(len(p["training"]["seeds"]) for p in protocols), 23)
            matrices = [json.loads(p.read_text()) for p in (root / "configs/v3/matrices/development").glob("*.json")]
            self.assertEqual(sum(len(p["entries"]) * 312 for p in matrices), 28080)
            with self.assertRaises(FileNotFoundError):
                prepare(root, final=True)
            self.assertFalse((root / "configs/v3/suites/final.jsonl").exists())

    def test_full_analysis_and_missing_run_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases = [c for c in make_cases("final") if c["case_id"].endswith("0000")]
            suite = root / "synthetic_suite.jsonl"
            suite.write_text("".join(json.dumps(c) + "\n" for c in cases))
            groups = []
            for family in ("combined_clean_ff", "combined_robust_ff", "combined_robust_history", "residual_robust_history", "combined_robust_repeat"):
                for role in ("selected", "final"):
                    for seed in ([11, 22, 33] if family.endswith("repeat") else [11, 22, 33, 44, 55]):
                        groups.append((family, role, seed))
            groups.extend((family, "baseline", None) for family in
                          ("nominal", "geometry_common", "geometry_best_constant", "geometry_raw", "geometry_filtered", "geometry_giver"))
            index = {"suite": suite.name, "entries": []}
            for number, (family, role, seed) in enumerate(groups):
                expected = {"entry_id": str(number), "suite_hash": sha256(suite), "config_hash": "fixture",
                            "controller_hash": "fixture", "checkpoint_sha256": "fixture" if seed else None,
                            "source_commit": "synthetic-test-only", "source_dirty": False, "training_seed": seed}
                records = root / f"fixture_{number}.jsonl"
                rows = [{**c, **expected, "success": True, "reset_valid": True, "terminal_reason": "success",
                         "drop": False, "collision": False, "completion_time_s": 4.0} for c in cases]
                records.write_text("".join(json.dumps(r) + "\n" for r in rows))
                index["entries"].append({"family": family, "role": role, "seed": seed, "records": records.name,
                                         "sha256": sha256(records), "expected": expected})
            ip = root / "index.json"
            write_json(ip, index)
            analyze = script("v3_analyze").analyze
            analyze(root, ip, root / "summary", repeats=16)
            effects = json.loads((root / "summary/paired_effects.json").read_text())
            self.assertEqual(sum(e["primary"] for e in effects), 2)
            self.assertTrue(all(e["difference_pp"] == 0 for e in effects))
            index["entries"].pop()
            write_json(ip, index)
            with self.assertRaises(ValueError):
                analyze(root, ip, root / "bad_summary", repeats=16)


if __name__ == "__main__":
    unittest.main()
