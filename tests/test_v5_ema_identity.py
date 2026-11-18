"""Synthetic tests of scripts/v5_ema_identity.py (EMA alpha 1.0 vs 0.2 field-by-field comparison)."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("v5_ema_identity", ROOT / "scripts/v5_ema_identity.py")
ei = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ei)


def rec(cid, alpha, **kw):
    return {"case_id": cid, "terminal_reason": "success", "completion_time_s": 4.2, "run_id": f"r{alpha}",
            "config_hash": f"h{alpha}", "sensor_ema_alpha": alpha, **kw}


def sample(mode, released, est, p_exec=(0.0, 0.0, 0.5)):
    return {"mode": mode, "released": released, "controller_obj_pos": est, "estimated_obj_pos": est,
            "p_exec": list(p_exec)}


def test_records_identical_except_identifiers():
    a = [rec("c1", 1.0), rec("c2", 1.0)]
    b = [rec("c1", 0.2), rec("c2", 0.2)]
    r = ei.compare_records(a, b)
    assert r["non_identifier_fields_differing"] == [] and r["identical_terminal_outcomes"] == 2
    assert set(r["differing_fields"]) == {"run_id", "config_hash", "sensor_ema_alpha"}


def test_records_report_a_real_difference():
    r = ei.compare_records([rec("c1", 1.0)], [rec("c1", 0.2, completion_time_s=4.3)])
    assert r["non_identifier_fields_differing"] == ["completion_time_s"]
    with pytest.raises(ValueError):
        ei.compare_records([rec("c1", 1.0)], [rec("c2", 0.2)])


def test_trace_differences_are_classified_by_phase():
    a = {"case": [sample(0, False, [0, 0, 1.0]), sample(1, False, [0, 0, 1.0]), sample(1, True, [0, 0, 1.0])]}
    b = {"case": [sample(0, False, [0, 0, 1.1]), sample(1, False, [0, 0, 1.0]), sample(1, True, [0, 0, 1.2])]}
    t = ei.compare_traces(a, b)["case"]
    assert t["controller_estimate_differs_by_phase"] == {"settling": 1, "after_giver_release": 1}
    assert t["executed_command_p_exec_differs"] == 0 and t["fields_outside_estimator"] == []
    b["case"][1] = sample(1, False, [0, 0, 1.3], p_exec=(0.0, 0.0, 0.6))
    t = ei.compare_traces(a, b)["case"]
    assert t["controller_estimate_differs_by_phase"]["other"] == 1
    assert t["executed_command_p_exec_differs"] == 1 and t["fields_outside_estimator"] == ["p_exec"]


def test_directory_input_round_trip(tmp_path):
    for ref, bound in ei.PAIRS:
        for alpha, tag in ((1.0, "ema1p0"), (0.2, "ema0p2")):
            name = f"{tag}_{ref}_{bound}"
            (tmp_path / f"{name}.jsonl").write_text(json.dumps(rec("c1", alpha)) + "\n")
            (tmp_path / "traces").mkdir(exist_ok=True)
            (tmp_path / "traces" / f"{name}.json").write_text(json.dumps({"case": [sample(1, False, [0, 0, 1.0])]}))
    res = ei.analyse(records=tmp_path)
    assert res["paired_episodes"] == 4 and res["all_record_fields_identical_except_identifiers"]
    assert res["trace_executed_command_differences"] == 0
    with pytest.raises(ValueError):
        ei.analyse()
