"""Synthetic-record tests of scripts/v5_slip_sensitivity.py (post hoc invalid-slip exclusion)."""

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import v5_slip_analysis as sa  # noqa: E402
import v5_slip_sensitivity as ss  # noqa: E402
from test_v5_slip_analysis import BASE, SEEDS, make_world  # noqa: E402


@pytest.fixture
def runs(tmp_path, monkeypatch):
    sl, plan, runs = make_world(tmp_path, {**BASE, "slip_robust_history": 1.0, "slip_robust_ff": 1.0,
                                           "slip_robust_repeat": 1.0, "geometry_tracking": 1.0}, n=40)
    monkeypatch.setattr(sa, "SL", sl)
    monkeypatch.setattr(sa, "ROOT", tmp_path)
    monkeypatch.setattr(sa, "check_freeze", lambda: plan)
    return runs


def mark_invalid(path: Path, case_ids):
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    for r in rows:
        if r["case_id"] in case_ids:
            r.update(success=False, terminal_reason="invalid_slip")
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_invalid_slips_are_excluded_from_every_arm(runs):
    # history: invalid slip on 8 cases in seed 111 only; geometry_best (alias of geometry_tracking): 2 other cases
    hist = [f"c-slip_mixed_id-{i:04d}" for i in range(8)]
    mark_invalid(runs / "final/slip_robust_history_s111/slip_robust_history_s111__selected.jsonl", hist)
    mark_invalid(runs / "final/baselines/geometry_tracking.jsonl", ["c-slip_mixed_id-0010", "c-slip_mixed_id-0011"])
    res = ss.analyse(runs, repeats=200)
    (r,) = res["conditions"]
    assert (r["condition"], r["base_cases"], r["excluded_base_cases"], r["kept_base_cases"]) == ("slip_mixed_id", 40, 10, 30)
    assert r["invalid_slip_episodes"] == {"slip_robust_history": 8, "slip_robust_ff": 0, "geometry_best": 2}
    b1, b2 = r["contrasts"]
    assert b1["all_cases"]["difference_pp"] == pytest.approx(-8 / (40 * len(SEEDS)) * 100)
    assert b2["all_cases"]["difference_pp"] == pytest.approx(-8 / 200 * 100 + 2 / 40 * 100)
    for c in (b1, b2):  # every remaining episode succeeds in every arm
        assert c["valid_slip_cases"]["difference_pp"] == 0.0 and c["valid_slip_cases"]["ci97.5"] == [0.0, 0.0]
        assert not c["lower_975_above_zero_valid_slip_cases"]
    assert set(r["success_pct_kept"].values()) == {100.0}
    assert "post hoc" in ss.markdown(res).lower()


def test_incomplete_records_are_refused(runs):
    p = runs / "final/slip_robust_ff_s222/slip_robust_ff_s222__selected.jsonl"
    p.write_text("".join(p.read_text().splitlines(keepends=True)[1:]))
    with pytest.raises(ValueError, match="incomplete"):
        ss.analyse(runs, repeats=20)
