#!/usr/bin/env python3
"""Derive v3 pilot or frozen training protocols from the draft profiles and the baseline selection (CPU).

    python3 scripts/v3_make_protocols.py pilot                 # configs/v3/pilot/<profile>.json
    python3 scripts/v3_make_protocols.py frozen --utc <UTC>    # configs/v3/frozen/training/<profile>.json

Every profile inherits exactly the estimator of `geometry_common` (EMA alpha, giver-reference) and its
alignment bound; the constant stays zero. Residual-only keeps geometry/gating off (method `residual`) but uses
the same estimator and observations. Training-error mixture, curriculum, PPO settings and budgets come from
the draft profiles (configs/v3/training/) unchanged unless --ppo-overrides is given (pilot evidence only).
Refuses to overwrite an existing file with different content.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ["combined_clean_ff", "combined_robust_ff", "combined_robust_history", "residual_robust_history", "combined_robust_repeat"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["pilot", "frozen"])
    ap.add_argument("--utc", default=None)
    ap.add_argument("--ppo-overrides", default=None, help="JSON applied to every profile (must be justified by pilots)")
    ap.add_argument("--num-envs", type=int, default=None)
    a = ap.parse_args()
    sel = json.loads((ROOT / "configs/v3/baseline_selection.json").read_text())["roles"]["geometry_common"]
    out_dir = ROOT / ("configs/v3/pilot" if a.stage == "pilot" else "configs/v3/frozen/training")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in PROFILES:
        p = json.loads((ROOT / "configs/v3/training" / f"{name}.json").read_text())
        q = copy.deepcopy(p)
        eo = q["env_overrides"]
        eo["observation_sensor"]["ema_alpha"] = sel["ema_alpha"]
        eo["observation_giver_reference"] = bool(sel["giver_reference"])
        eo["align_max"] = sel["align_max_m"]
        if a.ppo_overrides:
            q["ppo_overrides"].update(json.loads(a.ppo_overrides))
        if a.num_envs:
            q["training"]["num_envs"] = a.num_envs
            q["training"]["rollout_batch_transitions"] = a.num_envs * q["training"]["rollout_steps_per_env"]
        q["geometry_common"] = {k: sel[k] for k in ("candidate_id", "ema_alpha", "giver_reference", "align_max_m")}
        if a.stage == "pilot":
            q["protocol_id"] = f"v3-pilot-{name}"
            q["status"] = "pilot (development only; seeds 101/102; not a final result)"
        else:
            q["protocol_id"] = f"v3-final-{name}"
            q["status"] = "frozen"
            q["frozen_utc"] = a.utc
            b = q["training"]["rollout_batch_transitions"]
            req = q["training"]["final_transitions_per_run"]
            q["training"]["realized_transitions_per_run"] = -(-req // b) * b
        text = json.dumps(q, indent=2, sort_keys=True) + "\n"
        f = out_dir / f"{name}.json"
        if f.exists() and f.read_text() != text:
            raise SystemExit(f"refusing to overwrite {f.relative_to(ROOT)} with different content")
        f.write_text(text)
        print("wrote", f.relative_to(ROOT))


if __name__ == "__main__":
    main()
