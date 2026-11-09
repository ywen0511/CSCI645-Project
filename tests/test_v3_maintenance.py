"""CPU regressions for release reproduction; fixtures are not scientific evidence."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def jobs():
    return script("v3_jobs")


def record(jobs, paths):
    return {"rc": 0, "outputs_exist": True, "inputs": {}, "argv": [], "source_commit": "source",
            "cache_context": {}, "output_fingerprints": {str(p): jobs.fingerprint(p) for p in paths}}


@pytest.mark.parametrize("mutation", ["contents", "add", "remove", "empty_directory"])
def test_directory_cache_detects_changes(jobs, tmp_path, mutation):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    member = artifact / "records.jsonl"
    member.write_text("original\n")
    last = record(jobs, [artifact])
    assert jobs.cache_valid(last, {}, [], "source", [artifact], {})
    if mutation == "contents":
        member.write_text("modified\n")
    elif mutation == "add":
        (artifact / "extra").write_text("unexpected")
    elif mutation == "remove":
        member.unlink()
    else:
        (artifact / "empty").mkdir()
    with pytest.raises(ValueError, match="integrity mismatch"):
        jobs.cache_valid(last, {}, [], "source", [artifact], {})


def test_cache_requires_latest_success_and_provenance(jobs, tmp_path):
    p = tmp_path / "checkpoint"
    p.write_bytes(b"weights")
    last = record(jobs, [p])
    assert not jobs.cache_valid({**last, "rc": 1}, {}, [], "source", [p], {})
    for inputs, source, context in [({"checkpoint": "changed"}, "source", {}),
                                     ({}, "new-source", {}), ({}, "source", {"runner": "new"})]:
        with pytest.raises(ValueError, match="provenance"):
            jobs.cache_valid(last, inputs, [], source, [p], context)
    legacy = {k: v for k, v in last.items() if k != "output_fingerprints"}
    legacy["outputs"] = {str(p): jobs.sha(p)}
    with pytest.raises(ValueError, match="legacy provenance"):
        jobs.cache_valid(legacy, {}, [], "source", [p], {})
    p.unlink()
    assert not jobs.cache_valid(last, {}, [], "source", [p], {})


def test_matrix_checkpoint_and_suite_are_dependencies(jobs, tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "EXEC", tmp_path)
    suite, checkpoint = tmp_path / "cases.jsonl", tmp_path / "weights.pt"
    suite.write_text("{}\n")
    checkpoint.write_bytes(b"first")
    matrix = tmp_path / "matrix.json"
    matrix.write_text(json.dumps({"suite": "cases.jsonl", "entries": [{"id": "policy", "checkpoint": "weights.pt"}]}))
    argv = ["eval.py", "--matrix", str(matrix), "--checkpoint-root", str(tmp_path)]
    (tmp_path / "eval.py").write_text("# fixture")
    before = jobs.input_hashes({}, argv, tmp_path)
    checkpoint.write_bytes(b"second")
    after = jobs.input_hashes({}, argv, tmp_path)
    assert before[str(checkpoint)] != after[str(checkpoint)]
    suite.unlink()
    with pytest.raises(ValueError, match="Required input file missing"):
        jobs.input_hashes({}, argv, tmp_path)


def test_cpu_runner_dry_run_skip_and_corruption(tmp_path):
    # Use a path containing a quote to exercise structured placeholder resolution.
    runs = tmp_path / 'runs with "quotes"'
    program = tmp_path / "write.py"
    program.write_text("import pathlib,sys\npathlib.Path(sys.argv[1]).write_text('verified')\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"name": "cpu_fixture", "tasks": [{"id": "fixture", "kind": "cpu",
        "argv": [str(program), "$RUNS/result.txt"], "outputs": ["$RUNS/result.txt"]}]}))
    cmd = [sys.executable, str(ROOT / "scripts/v3_jobs.py"), "run", "--manifest", str(manifest),
           "--runs-root", str(runs), "--isaac-python", sys.executable, "--allow-dirty"]
    dry = subprocess.run(cmd + ["--dry-run"], capture_output=True, text=True)
    assert dry.returncode == 0, dry.stderr
    assert not (runs / "result.txt").exists()
    for _ in range(2):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
    assert "skip fixture" in proc.stdout
    assert len((runs / "ledger/fixture.jsonl").read_text().splitlines()) == 1
    (runs / "result.txt").write_text("corrupt")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode != 0 and "integrity mismatch" in proc.stderr
    assert (runs / "result.txt").read_text() == "corrupt"


def test_placeholder_resolution_preserves_json(jobs, tmp_path):
    path = tmp_path / 'with "quote" and spaces'
    data = {"suite": "$RUNS/cases.jsonl", "entries": [{"checkpoint": "$RUNS/weights.pt"}]}
    resolved = json.loads(json.dumps(jobs.resolve_json(data, path)))
    assert resolved["suite"] == str(path / "cases.jsonl")


@pytest.fixture
def experiment(tmp_path):
    tool = script("v3_rebuild_suites")
    exists = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", tool.EXPERIMENT], capture_output=True)
    if exists.returncode:
        pytest.skip("Archive rebuild integration requires full Git history (fetch experiment-v3)")
    repo = tmp_path / "experiment"
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(ROOT), str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "--quiet", "--detach", tool.EXPERIMENT], check=True)
    return tool, repo


def test_archived_suites_rebuild_twice_without_changes(experiment, tmp_path):
    tool, repo = experiment
    first = tool.rebuild(repo)
    assert tool.rebuild(repo) == first
    assert first["suites"]["final"]["sha256"] == "98eeac0f05983ceb19e72e0225aeecb421573b464ea0fd4695b88ec2c37639c3"
    output = tmp_path / "copies"
    assert tool.rebuild(repo, output) == first
    assert (output / "final.jsonl").read_bytes() == (repo / "configs/v3/suites/final.jsonl").read_bytes()
    with pytest.raises(FileExistsError):
        tool.rebuild(repo, output)
    with pytest.raises(ValueError, match="outside"):
        tool.rebuild(repo, repo / "copies")
    assert not list(repo.rglob("*.pyc"))
    assert not tool.git(repo, "status", "--porcelain", "--untracked-files=no").strip()


@pytest.mark.parametrize("path", ["configs/v3/SUITES.json", "src/csci645_handover/v3_protocol.py",
                                  "configs/v3/suites/final.jsonl"])
def test_rebuild_refuses_modified_archive(experiment, path):
    tool, repo = experiment
    p = repo / path
    p.write_bytes(p.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="tracked changes"):
        tool.rebuild(repo)
