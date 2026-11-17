"""Synthetic-record tests of scripts/v5_slip_analysis.py (written before any Study B final outcome existed)."""

import json
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v5_slip_analysis as sa  # noqa: E402

CONDS = ["clean", "slip_mixed_id"]
SEEDS = [111, 222, 333, 444, 555]
ROLES = {"nominal": "nominal", "geometry_calibrated": "geometry_calibrated", "geometry_tracking": "tracking_a",
         "geometry_fixed": "geometry_fixed", "geometry_ema": "geometry_ema",
         "best_constant_geometry": "geometry_calibrated", "geometry_best": "tracking_a"}
ALIASES = {"best_constant_geometry": "geometry_calibrated", "geometry_best": "geometry_tracking"}


def make_world(tmp: Path, p_succ: dict, n=40, dirty=False):
    """p_succ[method] = success probability (deterministic pattern from a seeded RNG)."""
    sl = tmp / "configs/v5/slip"
    cases = [{"case_id": f"c-{c}-{i:04d}", "base_case_id": f"b-{i:04d}", "condition": c,
              "slip_xyz_m": [0.005, 0.0, 0.0] if c != "clean" else [0.0, 0.0, 0.0], "slip_onset_s": 1.0}
             for c in CONDS for i in range(n)]
    (sl / "suites").mkdir(parents=True)
    (sl / "suites/final.jsonl").write_text("".join(json.dumps(r) + "\n" for r in cases))
    (sl / "matrices/final_baselines").mkdir(parents=True)
    (sl / "matrices/final_baselines/aliases.json").write_text(json.dumps({"declared_aliases": ALIASES}))
    plan = {"study": "synthetic", "suites": {"final": {"path": "configs/v5/slip/suites/final.jsonl", "sha256": "x"},
                                             "v4_final_noslip": {"path": "none"}},
            "seeds": {"analysis": 6458401}, "learned": {"seeds": SEEDS},
            "training_free": {"roles": ROLES},
            "primary": {"condition": "slip_mixed_id",
                        "contrasts": [{"id": "B1", "left": "slip_robust_history", "right": "slip_robust_ff"},
                                      {"id": "B2", "left": "slip_robust_history", "right": "geometry_best"}]}}
    rng = np.random.default_rng(0)

    def recs(method, seed=None):
        p = p_succ[method]
        out = []
        for c in cases:
            ok = bool(rng.random() < p)
            out.append({"case_id": c["case_id"], "condition": c["condition"], "success": ok,
                        "terminal_reason": "success" if ok else "prohibited_collision", "reset_valid": True,
                        "source_dirty": dirty, "source_commit": "abc", "slip_xyz_m": c["slip_xyz_m"],
                        "slip_onset_s": c["slip_onset_s"], "training_seed": seed, "collision": not ok, "drop": False,
                        "completion_time_s": 4.9 if ok else None, "flag_misaligned_at_grasp": False,
                        "flag_premature_release": False, "flag_conflicting_motion": False})
        return out

    runs = tmp / "runs"
    (runs / "final/baselines").mkdir(parents=True)
    for role in ROLES:
        if role in ALIASES:
            continue
        (runs / "final/baselines" / f"{role}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs(role)))
    for prof in sa.PROFILES:
        for s in SEEDS:
            d = runs / f"final/{prof}_s{s}"
            d.mkdir(parents=True)
            for k in ("selected", "final"):
                (d / f"{prof}_s{s}__{k}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs(prof, s)))
    return sl, plan, runs


@pytest.fixture
def world(tmp_path, monkeypatch):
    def build(p_succ, **kw):
        sl, plan, runs = make_world(tmp_path, p_succ, **kw)
        monkeypatch.setattr(sa, "SL", sl)
        monkeypatch.setattr(sa, "ROOT", tmp_path)
        monkeypatch.setattr(sa, "check_freeze", lambda: plan)
        return runs
    return build


BASE = {"nominal": 0.5, "geometry_calibrated": 0.7, "geometry_tracking": 0.8, "geometry_fixed": 0.4,
        "geometry_ema": 0.6}


def test_history_better_than_both_comparators_is_detected(world):
    runs = world({**BASE, "slip_robust_history": 0.99, "slip_robust_ff": 0.5, "slip_robust_repeat": 0.5})
    res = sa.analyse(runs, repeats=400)
    b1, b2 = res["primary"]
    assert b1["id"] == "B1" and b1["superiority_established"] and b1["difference_pp"] > 30
    assert b2["superiority_established"]
    assert b1["ci97.5"][0] <= b1["ci95"][0] <= b1["difference_pp"] <= b1["ci95"][1] <= b1["ci97.5"][1]


def test_no_difference_is_not_superiority(world):
    runs = world({**BASE, "slip_robust_history": 0.8, "slip_robust_ff": 0.8, "slip_robust_repeat": 0.8})
    res = sa.analyse(runs, repeats=400)
    assert not res["primary"][0]["superiority_established"]
    assert not res["primary"][1]["superiority_established"]


def test_alias_roles_resolve_to_the_executed_entry(world):
    runs = world({**BASE, "slip_robust_history": 0.8, "slip_robust_ff": 0.8, "slip_robust_repeat": 0.8})
    res = sa.analyse(runs, repeats=200)
    cell = lambda m: next(c for c in res["cells"] if c["method"] == m and c["condition"] == "slip_mixed_id")  # noqa: E731
    assert cell("geometry_best")["success_pct"] == cell("geometry_tracking")["success_pct"]
    assert cell("best_constant_geometry")["success_pct"] == cell("geometry_calibrated")["success_pct"]


def test_dirty_source_is_refused(world):
    runs = world({**BASE, "slip_robust_history": 0.8, "slip_robust_ff": 0.8, "slip_robust_repeat": 0.8}, dirty=True)
    with pytest.raises(ValueError, match="dirty"):
        sa.analyse(runs, repeats=50)


def test_missing_case_is_refused(world):
    runs = world({**BASE, "slip_robust_history": 0.8, "slip_robust_ff": 0.8, "slip_robust_repeat": 0.8})
    p = runs / "final/slip_robust_ff_s111/slip_robust_ff_s111__selected.jsonl"
    p.write_text("".join(p.read_text().splitlines(keepends=True)[1:]))
    with pytest.raises(ValueError, match="incomplete"):
        sa.analyse(runs, repeats=50)


def test_slip_metadata_must_match_the_suite(world):
    runs = world({**BASE, "slip_robust_history": 0.8, "slip_robust_ff": 0.8, "slip_robust_repeat": 0.8})
    p = runs / "final/baselines/nominal.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines()]
    rows[-1]["slip_xyz_m"] = [0.009, 0.0, 0.0]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(ValueError, match="slip_xyz_m"):
        sa.analyse(runs, repeats=50)


def test_invalid_slip_counts_as_failure_and_is_tabulated(world):
    runs = world({**BASE, "slip_robust_history": 0.8, "slip_robust_ff": 0.8, "slip_robust_repeat": 0.8})
    p = runs / "final/baselines/geometry_calibrated.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines()]
    rows[-1].update(success=False, terminal_reason="invalid_slip", slip_active=True, slip_valid=False, slip_completed=True,
                    slip_error_m=0.003, receiver_contact_before_grasp=False)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    res = sa.analyse(runs, repeats=50)
    t = next(c for c in res["taxonomy"] if c["method"] == "geometry_calibrated" and c["condition"] == "slip_mixed_id")
    assert t["terminal_reason_counts"]["invalid_slip"] == 1
    md = sa.markdown(res)
    assert "B1" in md and "B2" in md
