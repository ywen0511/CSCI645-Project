"""CPU tests of the V4 case protocol (standard library + pytest; no simulator)."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402


@pytest.fixture(scope="module")
def splits():
    return {s: v4.make_cases(s, v4.CONDITIONS, v4.ORDER if s != "validation" else list(v4.VALIDATION))
            for s in ("development", "validation", "final")}


def test_counts_and_determinism(splits):
    assert len(splits["development"]) == 12 * 24 and len(splits["validation"]) == 6 * 40
    assert len(splits["final"]) == 12 * 200
    assert v4.make_cases("final", v4.CONDITIONS, v4.ORDER) == splits["final"]
    assert len(v4.ORDER) == 12 and set(v4.VALIDATION) <= set(v4.ORDER)
    assert set(v4.TRAINING_LABEL) == set(v4.ORDER)


def test_split_ids_and_streams_disjoint(splits):
    ids = [r["case_id"] for rows in splits.values() for r in rows]
    assert len(ids) == len(set(ids))
    for key in ("init_seed",):
        per = {s: {r[key] for r in rows} for s, rows in splits.items()}
        assert not (per["development"] & per["final"]) and not (per["validation"] & per["final"])
    seeds = {s: {r["observation_error"]["seed"] for r in rows} for s, rows in splits.items()}
    assert not (seeds["development"] & seeds["final"]) and not (seeds["validation"] & seeds["final"])
    assert len(set(v4.SPLIT_SEEDS.values())) == 3


def test_pairing_across_conditions(splits):
    rows = splits["final"]
    by = {}
    for r in rows:
        by.setdefault(r["base_case_id"], []).append(r)
    assert len(by) == 200 and all(len(v) == 12 for v in by.values())
    for v in by.values():
        phys = {(tuple(r["requested_offset_xyz_m"]), r["release_offset_s"]) for r in v if r["condition"] != "clean"}
        assert len(phys) == 1  # one shared physical draw per base case
        assert len({r["observation_error"]["seed"] for r in v}) == 1
        assert len({r["init_seed"] for r in v}) == 1


def test_condition_ranges(splits):
    lo, hi = v4.TRAIN_SUPPORT["low_xyz_m"], v4.TRAIN_SUPPORT["high_xyz_m"]
    for r in splits["final"]:
        g, e, c = r["grasp_offset_xyz_m"], r["observation_error"], r["condition"]
        assert g[1] == 0.0  # y is never a supported in-grasp axis
        assert g[0] >= -0.007 - 1e-12  # never deeper than the physical palm limit
        if c == "clean":
            assert g == [0.0, 0.0, 0.0] and r["requested_offset_xyz_m"] == [0.0, 0.0, 0.0] and e["noise_std_m"] == 0
        if c == "mixed_id":
            assert all(lo[k] - 1e-12 <= g[k] <= hi[k] + 1e-12 for k in range(3))
            assert all(abs(b) <= 0.005 for b in e["bias_xyz_m"]) and e["noise_std_m"] == 0.002 and e["delay_steps"] == 2
        if c == "grasp_15mm":
            assert g[0] == 0.015 and abs(g[2]) == 0.010
        if c == "grasp_10mm":
            assert g[0] == 0.010 and abs(g[2]) == 0.010
        if c in ("grasp_2mm", "grasp_5mm"):
            a = 0.002 if c == "grasp_2mm" else 0.005
            assert abs(g[0]) == a and abs(g[2]) == a
        if c in ("bias_5mm", "noise_2mm", "delay_2step"):
            assert g == [0.0, 0.0, 0.0]
    signs = {r["grasp_offset_xyz_m"][0] > 0 for r in splits["final"] if r["condition"] == "grasp_5mm"}
    assert signs == {True, False}


def test_validator_fails_closed(splits):
    cases = splits["validation"][:3]
    rows = [{"case_id": c["case_id"], "condition": c["condition"], "observation_error": c["observation_error"],
             "grasp_offset_requested_xyz_m": [float(x) for x in c["grasp_offset_xyz_m"]], "success": True,
             "reset_valid": True, "terminal_reason": "success", "config_hash": "h"} for c in cases]
    assert v4.validate_records(rows, cases, {"config_hash": "h"}, complete=True)["recorded"] == 3
    for mutate in ("grasp", "dup", "stale", "unknown"):
        bad = copy.deepcopy(rows)
        if mutate == "grasp":
            bad[0]["grasp_offset_requested_xyz_m"] = [0.001, 0.0, 0.0]
        elif mutate == "dup":
            bad.append(bad[0])
        elif mutate == "stale":
            bad[1]["config_hash"] = "old"
        else:
            bad[2]["case_id"] = "v4-final-x-9999"
        with pytest.raises(ValueError):
            v4.validate_records(bad, cases, {"config_hash": "h"})
    with pytest.raises(ValueError):
        v4.validate_records(rows[:2], cases, {"config_hash": "h"}, complete=True)
