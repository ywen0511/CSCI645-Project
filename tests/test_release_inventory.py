"""Integrity tests use synthetic files; they are not experimental artifacts."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_release", ROOT / "scripts/verify_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseInventoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.protocol_path = self.root / "protocol.json"
        protocol = json.loads((ROOT / "configs/protocol.json").read_text())
        protocol["status"] = "frozen"
        self.protocol_path.write_text(json.dumps(protocol))
        self.manifest = {
            "schema_version": 1, "status": "complete",
            "experiment_source_commit": "a" * 40, "analysis_commit": "b" * 40,
            "protocol_sha256": release.digest(self.protocol_path),
            "release_tag": "synthetic-test-only", "artifacts": [],
        }
        for kind in sorted(release.REQUIRED_KINDS - {"checkpoints"}):
            self.add_artifact(kind + ".txt", kind)
        for method in protocol["methods"]:
            if method["learned"]:
                for seed in protocol["training"]["seeds"]:
                    self.add_artifact(f"{method['id']}-{seed}.txt", "checkpoints", method=method["id"], seed=seed)
        self.write_manifest()

    def add_artifact(self, name, kind, **extra):
        path = self.bundle / name
        path.write_text("SYNTHETIC INVENTORY TEST DATA\n")
        self.manifest["artifacts"].append({"path": name, "kind": kind, "size_bytes": path.stat().st_size, "sha256": release.digest(path), **extra})

    def write_manifest(self):
        path = self.bundle / "manifest.json"
        path.write_text(json.dumps(self.manifest))
        entries = {"manifest.json": release.digest(path)}
        entries.update({a["path"]: a["sha256"] for a in self.manifest["artifacts"]})
        (self.bundle / "SHA256SUMS").write_text("".join(f"{sha}  {name}\n" for name, sha in entries.items()))

    def test_valid_inventory(self):
        self.assertEqual(release.verify(self.bundle, self.protocol_path), 16)

    def test_tampered_payload_rejected(self):
        (self.bundle / "report.txt").write_text("corrupted")
        with self.assertRaisesRegex(ValueError, "size|Checksum"):
            release.verify(self.bundle, self.protocol_path)

    def test_missing_seed_rejected(self):
        self.manifest["artifacts"].pop()
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "coverage"):
            release.verify(self.bundle, self.protocol_path)

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            release.safe_path(self.bundle, "../protocol.json")

    def test_checksum_list_tampering_rejected(self):
        (self.bundle / "SHA256SUMS").write_text("")
        with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
            release.verify(self.bundle, self.protocol_path)

    def test_unfrozen_protocol_rejected(self):
        protocol = json.loads(self.protocol_path.read_text())
        protocol["status"] = "pilot_defaults_not_frozen"
        self.protocol_path.write_text(json.dumps(protocol))
        self.manifest["protocol_sha256"] = release.digest(self.protocol_path)
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "frozen"):
            release.verify(self.bundle, self.protocol_path)


if __name__ == "__main__":
    unittest.main()
