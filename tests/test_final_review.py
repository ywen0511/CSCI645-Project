"""Integrity and pairing checks for the CPU-only retrospective review."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("final_review_audit", Path(__file__).resolve().parents[1] / "scripts/final_review_audit.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "condition", "provenance", "invalid_success"])
def test_tampered_records_rejected(mutation):
    rows = [{"case_id": i, "condition": "c", "source_dirty": False, "success": True, "reset_valid": True} for i in ("a", "b")]
    suite = {r["case_id"]: copy.copy(r) for r in rows}
    if mutation == "duplicate":
        rows[1]["case_id"] = "a"
    elif mutation == "missing":
        rows.pop()
    elif mutation == "condition":
        rows[0]["condition"] = "wrong"
    elif mutation == "provenance":
        rows[0]["source_dirty"] = True
    else:
        rows[0]["reset_valid"] = False
    with pytest.raises(ValueError):
        review.validate_rows(rows, suite, {"source_dirty": False})


def test_common_valid_is_intersection_in_requested_order():
    a = {i: {"reset_valid": i != "a"} for i in "abcd"}
    b = {i: {"reset_valid": i != "b"} for i in "dcba"}
    assert review.common_valid_case_ids([a, b], list("dcba")) == ["d", "c"]


def test_paired_bootstrap_preserves_matched_outcomes():
    a = np.array([[0, 1, 0, 1], [1, 0, 1, 0]])
    result = review.paired_bootstrap(a, a, repeats=100)
    assert result["difference_pp"] == result["ci_low_pp"] == result["ci_high_pp"] == 0
    result = review.paired_bootstrap(np.ones((5, 4)), np.zeros((1, 4)), repeats=100)
    assert result["difference_pp"] == result["ci_low_pp"] == result["ci_high_pp"] == 100


def test_archive_must_match_published_digest(tmp_path):
    archive = tmp_path / "bad.tar.gz"
    archive.write_bytes(b"not published data")
    with pytest.raises(ValueError, match="checksum mismatch"):
        review.audit(archive)


@pytest.mark.parametrize("tamper", ["asset_bytes", "extra_asset", "omitted_manifest_entry"])
def test_release_verifier_rejects_incomplete_or_tampered_package(tmp_path, monkeypatch, tamper):
    spec = importlib.util.spec_from_file_location("review_package", Path(__file__).resolve().parents[1] / "scripts/final_review_package.py")
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(package, "ROOT", root)
    for rel in package.FILES:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('%PDF-fixture' if p.suffix == '.pdf' else '{"passed": true}')
    for args in (["init", "-q"], ["add", "."],
                 ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"]):
        subprocess.run(["git", *args], cwd=root, check=True)
    directory = tmp_path / "package"
    assert package.build(directory)["passed"]
    if tamper == "asset_bytes":
        (directory / "overview.pdf").write_bytes(b"corrupted")
    elif tamper == "extra_asset":
        (directory / "unlisted.txt").write_text("not published")
    else:
        path = directory / "release_manifest.json"
        manifest = json.loads(path.read_text())
        manifest["assets"].pop()
        path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        package.verify(directory)
