"""Write the fully resolved, frozen protocol (configs/frozen/protocol.json) and the case suites.

Usage (needs the Isaac Lab Python environment for config resolution; no simulator is launched):
    python scripts/freeze_protocol.py --pilot-protocol configs/protocol.json --output configs/frozen

The frozen protocol keeps every field of the pilot protocol, sets ``status`` to ``frozen`` and adds the
resolved task configuration (all task-level parameters, identical for every method except the method
flags), the PPO configuration, the rollout batch and realized transition budget, and the task
configuration hash that every run/evaluation record must carry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot-protocol", default="configs/protocol.json")
    ap.add_argument("--output", default="configs/frozen")
    ap.add_argument("--num-envs", type=int, default=1024)
    ap.add_argument("--freeze-date", required=True)
    a = ap.parse_args()

    from csci645_handover import runtime as rt
    from csci645_handover.agents.ppo_cfg import HandoverPPORunnerCfg
    from csci645_handover.tasks.handover_env_cfg import METHODS, HandoverEnvCfg, apply_method

    proto = json.loads(Path(a.pilot_protocol).read_text())
    cfg = HandoverEnvCfg()
    apply_method(cfg, "nominal")
    cfg.__post_init__()
    task = rt.env_cfg_dict(cfg)
    for k in ("method", "geometry_enabled", "residual_enabled", "phase_input", "seed", "num_envs", "log_dir"):
        task.pop(k, None)
    agent = HandoverPPORunnerCfg()
    batch = a.num_envs * agent.num_steps_per_env
    budget = proto["training"]["final_transitions_per_run"]
    iters = math.ceil(budget / batch)
    frozen = dict(proto)
    frozen["status"] = "frozen"
    frozen["freeze_date"] = a.freeze_date
    frozen["config_hash"] = rt.config_hash(cfg)
    frozen["config_id"] = frozen["config_hash"][:16]
    frozen["platform"] = dict(proto["platform"], isaac_lab="v3.0.0", isaac_sim="6.2.0.0", physics="isaacsim_physx",
                              rl_library="rsl-rl-lib 5.5.1")
    frozen["task_resolved"] = task
    frozen["methods_resolved"] = METHODS
    frozen["ppo"] = agent.to_dict()
    frozen["training"] = dict(proto["training"], num_envs=a.num_envs, rollout_steps_per_env=agent.num_steps_per_env,
                              rollout_batch_transitions=batch, iterations_per_run=iters,
                              realized_transitions_per_run=iters * batch,
                              transition_definition="vectorized environment steps x environments, including the "
                                                    "scripted reset-settling steps (residual disabled)")
    frozen["env_overrides"] = {}
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "protocol.json"
    data = json.dumps(frozen, indent=2, sort_keys=True, default=str) + "\n"
    if path.exists() and path.read_text() != data:
        raise SystemExit(f"{path} exists with different content; a frozen protocol is never overwritten")
    path.write_text(data)
    sha = hashlib.sha256(data.encode()).hexdigest()
    print(f"frozen protocol: {path} sha256={sha} config_hash={frozen['config_hash']}")
    subprocess.run([sys.executable, str(Path(__file__).parent / "make_suites.py"), "--protocol", str(path),
                    "--output", str(out / "suites")], check=True)
    (out / "PROTOCOL_SHA256").write_text(f"{sha}  protocol.json\n")


if __name__ == "__main__":
    main()
