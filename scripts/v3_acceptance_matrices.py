#!/usr/bin/env python3
"""Write the evaluation-based v3 acceptance suites/matrices (CPU only; deterministic; idempotent).

    python3 scripts/v3_acceptance_matrices.py

Outputs under configs/v3/acceptance/ (all cases are development cases; nothing touches validation/final):
  suite_small.jsonl          first 4 physical_only + first 4 mixed_id development cases
  suite_layout.jsonl         first 12 mixed_id + first 11 noise_4mm development cases (23 cases)
  suite_layout_rev.jsonl     the same 23 cases in reverse order (re-ordered case queue)
  suite_physical.jsonl       the 24 physical_only development cases (zero sensor error)
  suite_physical_v2fmt.jsonl the same cases without v3 sensor fields, for the archived default path
  a1_b1.json / a1_b8.json    nominal + geometry, mixed sensor (EMA 0.5), batch 1 and 8      (check 1)
  neg_<control>.json         negative controls with the v3 sensor, batch 8                   (check 1)
  a3_b1 / a3_b23 / a3_b23rev geometry with traced cases, batch 1, 23, 23 reversed           (check 3)
  a6_sensor0 / a6_archived   zero-error v3 sensor path vs archived default path, batch 24     (check 6)
  a2_<profile>_<role>        zero-residual equality (step-0 smoke checkpoints vs controller)  (check 2)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "configs/v3/acceptance"
PROT = "configs/v2/protocol.json"
MIXED = {"bias_bound_m": 0.005, "noise_std_m": 0.002, "delay_steps": 2, "max_delay_steps": 8, "ema_alpha": 0.5,
         "clean_probability": 0.25}


def w(name, obj):
    p = A / name
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=1, sort_keys=True) + "\n" if not isinstance(obj, str) else obj
    p.write_text(text)


def main():
    dev = [json.loads(l) for l in (ROOT / "configs/v3/suites/development.jsonl").read_text().splitlines() if l.strip()]
    by = {}
    for c in dev:
        by.setdefault(c["condition"], []).append(c)
    js = lambda rows: "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)  # noqa: E731
    small = by["physical_only"][:4] + by["mixed_id"][:4]
    layout = by["mixed_id"][:12] + by["noise_4mm"][:11]
    w("suite_small.jsonl", js(small))
    w("suite_layout.jsonl", js(layout))
    w("suite_layout_rev.jsonl", js(list(reversed(layout))))
    w("suite_physical.jsonl", js(by["physical_only"]))
    v2 = []
    for c in by["physical_only"]:
        c = {k: v for k, v in c.items() if k not in ("observation_error", "base_case_id")}
        c["suite_version"] = 1
        v2.append(c)
    w("suite_physical_v2fmt.jsonl", js(v2))
    det = [{"id": "nominal", "method": "nominal", "trace": True},
           {"id": "geometry_1p5cm", "method": "geometry", "overrides": {"align_max": 0.015}, "trace": True}]
    base = {"observation_sensor": MIXED}
    for b in (1, 8):
        w(f"a1_b{b}.json", {"name": f"v3acc_a1_b{b}", "suite": "configs/v3/acceptance/suite_small.jsonl", "num_envs": b,
                             "protocol": PROT, "base_overrides": base, "trace_cases": [small[0]["case_id"], small[4]["case_id"]],
                             "entries": det})
    for neg, extra in (("no_receiver", {}), ("giver_holds", {}), ("table_support", {"table_size_override": [0.06, 0.30, 0.20]})):
        w(f"neg_{neg}.json", {"name": f"v3acc_neg_{neg}", "suite": "configs/v3/acceptance/suite_small.jsonl", "num_envs": 8,
                               "protocol": PROT, "base_overrides": {**base, "negative_control": neg, **extra},
                               "trace_cases": [small[0]["case_id"]], "entries": det})
    tr = [layout[0]["case_id"], layout[5]["case_id"], layout[12]["case_id"], layout[22]["case_id"]]
    geo = [{"id": "geometry_1p5cm", "method": "geometry", "overrides": {"align_max": 0.015}, "trace": True}]
    for name, suite, b in (("a3_b1", "suite_layout.jsonl", 1), ("a3_b23", "suite_layout.jsonl", 23),
                           ("a3_b23rev", "suite_layout_rev.jsonl", 23)):
        w(f"{name}.json", {"name": f"v3acc_{name}", "suite": f"configs/v3/acceptance/{suite}", "num_envs": b,
                            "protocol": PROT, "base_overrides": {"observation_sensor": {**MIXED, "ema_alpha": 1.0}},
                            "trace_cases": tr, "entries": geo})
    ph = [by["physical_only"][0]["case_id"], by["physical_only"][1]["case_id"]]
    w("a6_sensor0.json", {"name": "v3acc_a6_sensor0", "suite": "configs/v3/acceptance/suite_physical.jsonl", "num_envs": 24,
                          "protocol": PROT, "base_overrides": {"observation_sensor": {**MIXED, "ema_alpha": 1.0}},
                          "trace_cases": ph, "entries": det})
    w("a6_archived.json", {"name": "v3acc_a6_archived", "suite": "configs/v3/acceptance/suite_physical_v2fmt.jsonl",
                           "num_envs": 24, "protocol": PROT, "base_overrides": {}, "trace_cases": ph, "entries": det})
    print("wrote", sorted(p.name for p in A.iterdir()))


def zero_residual_matrices(smoke_root: str):
    """Check 2: step-0 (zero-mean) checkpoints of each smoke profile vs the matching deterministic controller,
    same training protocol, same suite and batch size, one entry per fresh process (--only)."""
    pairs = [("combined_robust_ff", "combined", "geometry"), ("combined_robust_history", "combined", "geometry"),
             ("residual_robust_history", "residual", "nominal")]
    for prof, method, det in pairs:
        w(f"a2_{prof}.json", {"name": f"v3acc_a2_{prof}", "suite": "configs/v3/acceptance/suite_layout.jsonl", "num_envs": 23,
                               "protocol": f"configs/v3/training/{prof}.json",
                               "trace_cases": [], "entries": [
                                   {"id": f"{prof}_step0", "method": method, "checkpoint":
                                    f"smoke_{prof}_s101/checkpoints/step_000000000.pt", "training_seed": 101},
                                   {"id": det, "method": det, "overrides": {"align_max": 0.015} if det == "geometry" else {}}]})


if __name__ == "__main__":
    main()
    zero_residual_matrices("runs/v3/smoke")
