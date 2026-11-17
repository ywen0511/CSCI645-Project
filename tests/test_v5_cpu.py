"""CPU tests for the V5 local work: failure taxonomy, Study A freeze and Study A analysis."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tax = load("v5_failure_taxonomy")
study = load("v5_make_calibration_study")
ana = load("v5_calibration_analysis")


def row(reason, **kw):
    r = {"case_id": kw.pop("case_id", "c"), "success": reason == "success", "terminal_reason": reason,
         "reset_valid": reason != "invalid_reset", "collision": reason == "prohibited_collision",
         "drop": reason == "drop", "completion_time_s": 4.0 if reason == "success" else float("nan"),
         "flag_misaligned_at_grasp": False, "flag_premature_release": False, "flag_conflicting_motion": False}
    r.update(kw)
    return r


def test_taxonomy_counts_and_flags_only_among_failed_valid():
    rows = [row("success", flag_misaligned_at_grasp=True), row("prohibited_collision", flag_misaligned_at_grasp=True),
            row("drop", flag_premature_release=True), row("invalid_reset", flag_misaligned_at_grasp=True)]
    s = tax.summarize(rows)
    assert s["terminal_reason_counts"] == {"success": 1, "prohibited_collision": 1, "drop": 1, "episode_timeout": 0,
                                           "release_timeout": 0, "invalid_reset": 1}
    assert s["failed_valid_episodes"] == 2
    assert s["flags_among_failed_counts"] == {"misaligned": 1, "premature_release": 1, "conflicting_motion": 0}
    assert s["completion_time_s_successes"]["median"] == 4.0


@pytest.mark.parametrize("bad", [{"success": True, "terminal_reason": "drop"},
                                 {"reset_valid": True, "terminal_reason": "invalid_reset", "success": False},
                                 {"terminal_reason": "teleported", "success": False}])
def test_taxonomy_rejects_inconsistent_rows(bad):
    with pytest.raises(ValueError):
        tax.summarize([row("success") | bad])


def test_study_a_inputs_are_frozen_and_reproducible():
    subprocess.run([sys.executable, str(ROOT / "scripts/v5_make_calibration_study.py"), "--check"], check=True)
    plan = ana.load_plan()
    assert len(plan["configurations"]) == 8
    assert {c["id"] for c in plan["configurations"]} >= {"ema1p0_fixed_a15", "ema0p2_cal050_a25",
                                                          "ema0p2_fixed_a25"}
    suite = [json.loads(x) for x in (ROOT / plan["suite"]["path"]).read_text().splitlines()]
    assert len(suite) == 2400 and all(r["suite_version"] == 4 for r in suite)
    v4 = ROOT / "configs/v4/suites/final.jsonl"
    if v4.exists():
        old = {json.loads(x)["init_seed"] for x in v4.read_text().splitlines()}
        assert not old & {r["init_seed"] for r in suite}


def test_matched_primary_arms_differ_only_in_reference():
    m = json.loads((ROOT / "configs/v5/calibration/matrix_ema0p2.json").read_text())
    e = {x["id"]: x["overrides"] for x in m["entries"]}
    assert e["ema0p2_fixed_a25"] == {"align_max": 0.025}
    assert e["ema0p2_cal050_a25"] == {"align_max": 0.025, "giver_calibration_window_s": 0.5}
    assert m["base_overrides"]["observation_sensor"]["ema_alpha"] == 0.2


def write_records(tmp, plan, success_fn):
    suite = [json.loads(x) for x in (ROOT / plan["suite"]["path"]).read_text().splitlines()]
    for c in plan["configurations"]:
        lines = []
        for case in suite:
            ok = success_fn(c, case)
            lines.append(json.dumps({"case_id": case["case_id"], "condition": case["condition"], "success": ok,
                                     "reset_valid": True, "terminal_reason": "success" if ok else "prohibited_collision",
                                     "source_dirty": False, "source_commit": "abc"}))
        (tmp / f"{c['id']}.jsonl").write_text("\n".join(lines) + "\n")


def test_analysis_on_synthetic_records(tmp_path):
    plan = ana.load_plan()
    # calibration succeeds everywhere; fixed fails on mixed_id only when bound is 25 mm -> reference x bound interaction
    write_records(tmp_path, plan, lambda c, case: c["reference"] == "cal050" or not
                  (case["condition"] == "mixed_id" and c["bound"] == "a25"))
    res = ana.analyse(tmp_path, None, repeats=200)
    a1 = next(p for p in res["primary"] if p["id"] == "A1")
    a2 = next(p for p in res["primary"] if p["id"] == "A2")
    assert a1["difference_pp"] == pytest.approx(100.0) and a1["supports_calibration_only_improvement"]
    assert a2["difference_pp"] == pytest.approx(0.0) and not a2["supports_calibration_only_improvement"]
    me = {(m["condition"], m["factor"]): m["difference_pp"] for m in res["secondary_exploratory"]["main_effects"]}
    assert me[("mixed_id", "reference")] == pytest.approx(50.0)
    assert me[("mixed_id", "bound")] == pytest.approx(-50.0)
    assert me[("mixed_id", "ema")] == pytest.approx(0.0)
    ia = {(i["condition"], i["factors"][1]): i["difference_pp"] for i in res["secondary_exploratory"]["interactions"]}
    assert ia[("mixed_id", "bound")] == pytest.approx(100.0)  # calibration effect: 100 at a25 minus 0 at a15
    assert ia[("mixed_id", "ema")] == pytest.approx(0.0)


def test_analysis_rejects_incomplete_records(tmp_path):
    plan = ana.load_plan()
    write_records(tmp_path, plan, lambda c, case: True)
    f = tmp_path / "ema0p2_fixed_a25.jsonl"
    f.write_text("\n".join(f.read_text().splitlines()[:-1]) + "\n")
    with pytest.raises(ValueError, match="incomplete"):
        ana.analyse(tmp_path, None, repeats=10)
