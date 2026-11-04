"""Resolve and freeze the v2 protocol (needs the Isaac Lab Python environment; no simulator is launched).

    python scripts/freeze_v2.py --protocol configs/v2/protocol.json --output configs/v2/frozen --freeze-utc 2026-11-04T07:00:00Z

Writes ``configs/v2/frozen/protocol.json`` (the protocol plus the resolved task configuration, the task
configuration hash every v2 training/evaluation record must carry, a controller hash per deterministic
controller, PPO settings and the realized rollout budget), ``PROTOCOL_SHA256`` and ``SUITES_SHA256``.
A frozen file is never overwritten with different content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", default="configs/v2/protocol.json")
    ap.add_argument("--output", default="configs/v2/frozen")
    ap.add_argument("--freeze-utc", required=True)
    a = ap.parse_args()

    from csci645_handover import runtime as rt
    from csci645_handover.agents.ppo_cfg import HandoverPPORunnerCfg
    from csci645_handover.tasks.handover_env_cfg import METHODS

    proto = json.loads((ROOT / a.protocol).read_text())
    tr = proto["training"]
    cfg = rt.build_env_cfg("combined", tr["num_envs"], "cpu", 0, dict(proto["env_overrides"]))
    task = rt.env_cfg_dict(cfg)
    for k in ("method", "geometry_enabled", "residual_enabled", "phase_input", "seed", "num_envs", "log_dir"):
        task.pop(k, None)
    agent = HandoverPPORunnerCfg()
    batch = tr["num_envs"] * agent.num_steps_per_env
    iters = math.ceil(tr["final_transitions_per_run"] / batch)
    ctrl = {}
    for cid, c in proto["deterministic_controllers"].items():
        d = rt.build_env_cfg(c["method"], 1, "cpu", 0, dict(proto["env_overrides"]))
        for k, v in c["overrides"].items():
            if k not in rt.RUNTIME_FIELDS:
                raise SystemExit(f"{cid}: {k} is not a runtime field")
            setattr(d, k, v)
        ctrl[cid] = {"config_hash": rt.config_hash(d), "controller_hash": rt.controller_hash(d)}
    learned = {}
    for m in tr["methods"]:
        d = rt.build_env_cfg(m, 1, "cpu", 0, dict(proto["env_overrides"]))
        learned[m] = {"config_hash": rt.config_hash(d), "controller_hash": rt.controller_hash(d)}
    suites = json.loads((ROOT / "configs/v2/suites/SUITES.json").read_text())
    for name in ("validation", "final"):
        p = ROOT / suites[name]["path"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != suites[name]["sha256"]:
            raise SystemExit(f"{p} does not match SUITES.json")
    frozen = dict(proto)
    frozen.update({
        "status": "frozen", "freeze_utc": a.freeze_utc,
        "config_hash": rt.config_hash(cfg), "config_id": rt.config_hash(cfg)[:16],
        "task_resolved": task, "methods_resolved": METHODS, "ppo": agent.to_dict(),
        "controller_hashes": ctrl, "learned_method_hashes": learned,
        "suites": {k: suites[k] for k in ("development", "development_feasibility", "development_valproxy", "validation", "final") if k in suites},
    })
    frozen["training"] = dict(tr, rollout_steps_per_env=agent.num_steps_per_env, rollout_batch_transitions=batch,
                              iterations_per_run=iters, realized_transitions_per_run=iters * batch)
    out = ROOT / a.output
    out.mkdir(parents=True, exist_ok=True)
    data = json.dumps(frozen, indent=2, sort_keys=True, default=str) + "\n"
    path = out / "protocol.json"
    if path.exists() and path.read_text() != data:
        raise SystemExit(f"{path} exists with different content; a frozen protocol is never overwritten")
    path.write_text(data)
    sha = hashlib.sha256(data.encode()).hexdigest()
    (out / "PROTOCOL_SHA256").write_text(f"{sha}  protocol.json\n")
    (out / "SUITES_SHA256").write_text("".join(f"{suites[k]['sha256']}  {suites[k]['path']}\n" for k in sorted(frozen["suites"])))
    print(f"frozen: {path} sha256={sha} config_hash={frozen['config_hash']} realized={iters * batch}")


if __name__ == "__main__":
    main()
