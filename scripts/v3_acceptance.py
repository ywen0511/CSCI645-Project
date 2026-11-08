"""V3 remote acceptance checks that need instrumentation (one simulator process per invocation).

    python scripts/v3_acceptance.py sensor     --output runs/v3/acceptance/sensor.json        # CUDA tensors, no simulator
    python scripts/v3_acceptance.py residual   --output runs/v3/acceptance/residual.json      # check 2 (mechanics)
    python scripts/v3_acceptance.py boundary   --output runs/v3/acceptance/boundary.json      # check 4
    python scripts/v3_acceptance.py dependency --variant ff_ema0p5_giver1 --output ...        # check 5
    python scripts/v3_acceptance.py inputs     --mode stack --checkpoint <smoke ckpt> --output ...   # check 8

Checks that are plain evaluations (physical pipeline, negative controls, zero-residual equality, layout
pairing of the sensor stream, default-path comparison) use scripts/eval_matrix.py with the matrices under
configs/v3/acceptance/ and are judged by scripts/v3_acceptance_report.py. Every subcommand writes a JSON file
with its measurements, the per-check booleans and an overall "ok"; nothing here changes the simulator code.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("check", choices=["sensor", "residual", "boundary", "dependency", "inputs"])
ap.add_argument("--output", required=True)
ap.add_argument("--variant", default="ff_ema0p5_giver1",
                help="dependency: ff|hist5 _ ema1p0|ema0p5 _ giver0|giver1, or 'archived' (no sensor; sensitivity control)")
ap.add_argument("--mode", default="stack", choices=["stack", "repeat_current", "permuted"])
ap.add_argument("--checkpoint", default=None)
ap.add_argument("--seed", type=int, default=6455501)
args_ns, _rest = ap.parse_known_args()

DEV_SUITE = ROOT / "configs/v3/suites/development.jsonl"
MIXED_SENSOR = {"bias_bound_m": 0.005, "noise_std_m": 0.002, "delay_steps": 2, "max_delay_steps": 8,
                "ema_alpha": 0.5, "clean_probability": 0.25}


def dump(obj):
    p = Path(args_ns.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in obj.items() if k in ("check", "ok", "checks")}, indent=1, default=float))


def dev_cases(condition: str, n: int):
    rows = [json.loads(l) for l in DEV_SUITE.read_text().splitlines() if l.strip()]
    return [r for r in rows if r["condition"] == condition][:n]


# ----------------------------------------------------------------------------------- sensor (no simulator)
def check_sensor():
    import torch

    from csci645_handover.core.observation import ObservationHistory, PositionSensor, normal_at

    dev = "cuda:0" if torch.cuda.is_available() else "cpu"
    out, checks = {"check": "sensor", "device": dev, "torch": torch.__version__}, {}
    n, T = 6, 4000
    t = torch.arange(T, dtype=torch.float32, device=dev) * 0.05
    truth = torch.stack([0.1 * torch.sin(t), 0.05 * t, 0.02 * torch.cos(2 * t)], -1)  # analytic moving input [m]
    bias = torch.tensor([[0.005, -0.005, 0.002]] * n, device=dev)
    sigma = torch.tensor([0.0, 0.0, 0.002, 0.004, 0.002, 0.0], device=dev)
    delay = torch.tensor([0, 2, 0, 0, 4, 1], device=dev)
    seeds = torch.tensor([11, 22, 33, 44, 55, 66], device=dev)
    s = PositionSensor(n, dev, max_delay=8, alpha=1.0)
    s.reset(torch.arange(n, device=dev), seeds=seeds, bias=bias, sigma=sigma, delay=delay)
    raw = torch.zeros(T, n, 3, device=dev)
    for k in range(T):
        s.update(truth[k].expand(n, 3), token=k)
        s.update(truth[k].expand(n, 3) + 1.0, token=k)  # repeated read at the same token must not advance
        raw[k] = s.raw
    # delay in control steps and bias: deterministic channels are exact
    d_ok = True
    for i in (0, 1, 5):
        d = int(delay[i])
        exp = torch.stack([truth[max(0, k - d)] for k in range(T)]) + bias[i]
        d_ok &= bool(torch.allclose(raw[:, i], exp, atol=1e-6))
    checks["bias_and_delay_exact"] = d_ok
    # noise moments (raw - delayed truth - bias)
    mom = {}
    for i in (2, 3, 4):
        d = int(delay[i])
        exp = torch.stack([truth[max(0, k - d)] for k in range(T)]) + bias[i]
        e = (raw[:, i] - exp)
        mom[int(i)] = {"sigma": float(sigma[i]), "mean": e.mean(0).tolist(), "std": e.std(0).tolist()}
    checks["noise_moments"] = all(abs(sd - v["sigma"]) < 0.05 * v["sigma"] and all(abs(m) < 4 * v["sigma"] / math.sqrt(T) for m in v["mean"])
                                  for v in mom.values() for sd in v["std"])
    out["noise_moments"] = mom
    checks["repeated_read_idempotent"] = bool((s.frames == T).all())
    # EMA step response: y_k = a*x + (1-a)*y_{k-1}
    a = 0.5
    e = PositionSensor(1, dev, max_delay=0, alpha=a)
    e.reset(torch.tensor([0], device=dev), seeds=[1], bias=[[0, 0, 0]], sigma=[0], delay=[0])
    ys = []
    for k in range(6):
        x = torch.zeros(1, 3, device=dev) if k == 0 else torch.ones(1, 3, device=dev)
        ys.append(float(e.update(x, k)[0, 0]))
    expect = [0.0, 0.5, 0.75, 0.875, 0.9375, 0.96875]
    checks["ema_step_response"] = all(abs(u - v) < 1e-6 for u, v in zip(ys, expect))
    out["ema_response"] = ys
    # finite-difference derivative of a constant-velocity estimate (what the env computes)
    v = torch.tensor([0.02, -0.01, 0.0], device=dev)
    dt = 0.05
    pos = [v * dt * k for k in range(10)]
    fd = [(pos[k] - pos[k - 1]) / dt for k in range(1, 10)]
    checks["finite_difference_velocity"] = all(torch.allclose(f, v, atol=1e-6) for f in fd)
    # layout independence of the exogenous noise: same seeds/frames in a different slot order and batch size
    f = torch.arange(200, device=dev)
    a1 = normal_at(torch.full((200,), 12345, device=dev), f)
    perm = torch.randperm(200, device=dev)
    a2 = normal_at(torch.full((200,), 12345, device=dev), f[perm])
    a3 = torch.stack([normal_at(torch.tensor([12345], device=dev), torch.tensor([int(k)], device=dev))[0] for k in range(200)])
    checks["noise_independent_of_slot_and_batch"] = bool(torch.equal(a1[perm], a2) and torch.equal(a1, a3))
    cpu = normal_at(torch.full((200,), 12345), torch.arange(200))
    out["cuda_vs_cpu_noise_max_abs_diff"] = float((a1.cpu() - cpu).abs().max())
    # history order and reset isolation
    h = ObservationHistory(2, 1, 5, dev)
    for k in range(7):
        h.update(torch.tensor([[float(k)], [10.0 + k]], device=dev), k)
    h.reset(torch.tensor([1], device=dev))
    h.update(torch.tensor([[99.0], [42.0]], device=dev), 7)
    checks["history_oldest_to_newest"] = h.data[0, :, 0].tolist() == [3.0, 4.0, 5.0, 6.0, 99.0]
    checks["history_reset_repeat_first"] = h.data[1, :, 0].tolist() == [42.0] * 5
    out["checks"], out["ok"] = checks, all(checks.values())
    dump(out)


# ----------------------------------------------------------------------------------- simulator helpers
def sim(method: str, num_envs: int, overrides: dict, body):
    from isaaclab.app import add_launcher_args, launch_simulation

    from csci645_handover import runtime as rt

    p = argparse.ArgumentParser()
    add_launcher_args(p)
    largs, _ = p.parse_known_args(_rest)
    prot = json.loads((ROOT / "configs/v2/protocol.json").read_text())
    over = dict(prot.get("env_overrides", {}))
    over.update(overrides)
    cfg = rt.build_env_cfg(method, num_envs, "cuda:0", args_ns.seed, over)
    with launch_simulation(cfg, largs):
        from csci645_handover.tasks.handover_env import HandoverEnv

        env = HandoverEnv(cfg)
        res = body(env, rt)
        res.update({"method": method, "num_envs": num_envs, "overrides": overrides, "git": rt.git_state(),
                    "config_hash": rt.config_hash(env.cfg), "step_dt": env.step_dt, "physics_dt": env.physics_dt,
                    "decimation": env.cfg.decimation})
        dump(res)  # inside the context: code after launch_simulation may never run


# ----------------------------------------------------------------------------------- check 2: residual mechanics
def check_residual():
    def body(env, rt):
        import torch

        from csci645_handover.tasks import handover_env as he

        cases = dev_cases("mixed_id", 4)
        env.set_case_queue(cases)
        env.completed_records, env.traces, env.trace_env_ids = [], {}, []
        env.reset()
        acts = torch.tensor([[-5.0, 0.3, 2.0], [0.5, -0.5, 0.0], [0.0, 0.0, 0.0], [3.0, 3.0, -3.0]], device=env.device)
        bound = env.cfg.residual_bound_m
        stats = {"steps": 0, "scored_steps": 0, "max_err_squash": 0.0, "max_err_compose": 0.0, "settle_nonzero": 0,
                 "accumulation_changes": 0, "release_vs_request_s": []}
        prev = None
        while len(env.completed_records) < len(cases) and stats["steps"] < 3000:
            scored = env.mode == he.SCORED  # the residual of this step is computed from the PRE-step mode
            settle_pre = env.mode == he.SETTLE
            env.step(acts)
            stats["steps"] += 1
            # environments that terminated in this step are reset at its end (_reset_idx zeroes the residual):
            # compare only environments scored both before and after the step
            scored = scored & (env.mode == he.SCORED)
            exp = bound * torch.tanh(acts)
            if scored.any():
                stats["scored_steps"] += int(scored.sum())
                stats["max_err_squash"] = max(stats["max_err_squash"], float((env.residual[scored] - exp[scored]).abs().max()))
                stats["max_err_compose"] = max(stats["max_err_compose"],
                                               float((env.p_cand[scored] - env.p_nom[scored] - env.residual[scored]).abs().max()))
                if prev is not None:
                    both = scored & prev[1]
                    stats["accumulation_changes"] += int(((env.residual - prev[0]).abs().max(-1).values > 1e-9)[both].sum())
            stats["settle_nonzero"] += int((env.residual[settle_pre].abs() > 0).sum())
            prev = (env.residual.clone(), scored.clone())
        for r in env.completed_records:
            if r.get("release_command_time_s") is not None and r.get("release_request_time_s") is not None:
                stats["release_vs_request_s"].append(r["release_command_time_s"] - r["release_request_time_s"])
        checks = {
            "single_squash_bound": stats["max_err_squash"] < 1e-7 and float((bound * torch.tanh(acts)).abs().max()) <= bound,
            "composition_not_accumulated": stats["max_err_compose"] < 1e-6 and stats["accumulation_changes"] == 0,
            "zero_residual_outside_scored": stats["settle_nonzero"] == 0,
            "fixed_release_without_geometry": bool(stats["release_vs_request_s"]) and
            all(-1e-6 <= d <= env.step_dt + 1e-6 for d in stats["release_vs_request_s"]),
            "all_cases_recorded": len(env.completed_records) == len(cases),
        }
        return {"check": "residual", "stats": stats, "checks": checks, "ok": all(checks.values()),
                "records": [{k: r[k] for k in ("case_id", "terminal_reason", "success", "reset_valid")} for r in env.completed_records]}

    sim("residual", 4, {"observation_sensor": MIXED_SENSOR}, body)


# ----------------------------------------------------------------------------------- check 4: reset boundaries
def check_boundary():
    def body(env, rt):
        import torch

        from csci645_handover.tasks import handover_env as he

        cases = dev_cases("mixed_id", 3)
        env.set_case_queue(cases)
        env.completed_records, env.traces, env.trace_env_ids = [], {}, []
        rows = []
        orig = env._get_observations

        def logged():
            o = orig()
            i = 0
            ci = int(env.case_index[i])
            rows.append({"counter": int(env.common_step_counter), "case_index": ci, "mode": int(env.mode[i]),
                         "frames": int(env.sensor.frames[i]), "token": int(env.sensor.token[i]),
                         "truth": env.m["obj_pos"][i].tolist(), "raw": env.sensor.raw[i].tolist(),
                         "estimate": env.sensor.estimate[i].tolist(), "spawn": (env.obj_nominal_local + env.offset[i]).tolist(),
                         "hist": env.obs_history.data[i, :, :3].tolist(), "obs_head": o["policy"][i, -46:-43].tolist(),
                         "delay": int(env.sensor.delay[i]), "bias": env.sensor.bias[i].tolist(),
                         "sigma": float(env.sensor.sigma[i]), "seed": int(env.sensor.seeds[i])})
            return o

        env._get_observations = logged
        env.reset()
        steps = 0
        while len(env.completed_records) < len(cases) and steps < 3000:
            env.step(torch.zeros(1, 3, device=env.device))
            steps += 1
        from csci645_handover.core.observation import normal_at

        frame_ok, first_ok, stale, future_ok, hist_ok, reset_rows = True, True, [], True, True, []
        ep_start = [k for k in range(len(rows)) if (k == 0 or rows[k]["case_index"] != rows[k - 1]["case_index"])
                    and rows[k]["case_index"] >= 0]  # the final reset to IDLE (case_index -1) is not an episode
        for k, r in enumerate(rows):
            if k in ep_start:
                reset_rows.append(k)
                first_ok &= r["frames"] == 1 and r["estimate"] != [0, 0, 0]
                stale.append(max(abs(a - b) for a, b in zip(r["truth"], r["spawn"])))
                hist_ok &= all(h == r["hist"][-1] for h in r["hist"])
            elif r["case_index"] >= 0:
                frame_ok &= r["frames"] == rows[k - 1]["frames"] + 1
        # reconstruct raw from truth: raw_k = truth_{k-d} + bias + sigma * normal(seed, k)
        max_err = 0.0
        for s in ep_start:
            end = next((e for e in ep_start if e > s), len(rows))
            ep = rows[s:end]
            for j, r in enumerate(ep):
                d = r["delay"]
                tru = ep[max(0, j - d)]["truth"]
                nz = normal_at(torch.tensor([r["seed"]]), torch.tensor([r["frames"] - 1]))[0].tolist()
                exp = [tru[a] + r["bias"][a] + r["sigma"] * nz[a] for a in range(3)]
                max_err = max(max_err, max(abs(exp[a] - r["raw"][a]) for a in range(3)))
        future_ok = max_err < 2e-5  # float32 positions + CPU-vs-CUDA transcendental roundoff
        checks = {"one_noise_advance_per_control_frame": frame_ok, "fresh_stream_on_reset": first_ok,
                  "no_stale_object_position_at_reset": max(stale) < 1e-3, "raw_equals_delayed_truth_plus_error": future_ok,
                  "history_repeat_first_on_reset": hist_ok, "episodes": len(ep_start) == len(cases)}
        return {"check": "boundary", "checks": checks, "ok": all(checks.values()), "reset_rows": reset_rows,
                "max_reconstruction_error_m": max_err, "spawn_vs_measured_at_reset_m": stale, "n_rows": len(rows),
                "rows_around_resets": [rows[max(0, k - 2):k + 3] for k in reset_rows],
                "records": [{k: r[k] for k in ("case_id", "terminal_reason", "success", "reset_valid")} for r in env.completed_records]}

    sim("combined", 1, {"observation_sensor": MIXED_SENSOR, "observation_history": 5}, body)


# ----------------------------------------------------------------------------------- check 5: hidden-translation paths
def check_dependency():
    v = args_ns.variant
    if v == "archived":
        over = {}
    else:
        hist, ema, giver = v.split("_")
        over = {"observation_sensor": {**MIXED_SENSOR, "ema_alpha": float(ema[3:].replace("p", "."))},
                "observation_history": 5 if hist == "hist5" else 1, "observation_giver_reference": giver == "giver1"}

    def body(env, rt):
        import torch

        from csci645_handover.tasks import handover_env as he

        cases = dev_cases("mixed_id", 8)
        env.set_case_queue(cases)
        env.completed_records, env.traces, env.trace_env_ids = [], {}, []
        obs, _ = env.reset()
        steps = 0
        snapshots = []
        while steps < 400:
            obs, *_ = env.step(torch.zeros(env.num_envs, 3, device=env.device))
            steps += 1
            sc = env.mode == he.SCORED
            if steps in (int(env.settle_total / env.step_dt) + 10, int(env.settle_total / env.step_dt) + 60) and sc.all():
                o1 = env._get_observations()["policy"].clone()
                cm1 = {k: v.clone() for k, v in (env.controller_m.items() if env.sensor is not None else env.m.items())
                       if torch.is_tensor(v)}
                t1 = env.m["obj_pos"].clone()
                delta = torch.tensor([0.003, -0.002, 0.001], device=env.device)
                pose = torch.cat([env.obj.data.root_pos_w.torch.clone() + delta, env.obj.data.root_quat_w.torch.clone()], -1)
                env.obj.write_root_pose_to_sim_index(root_pose=pose, env_ids=torch.arange(env.num_envs, device=env.device))
                env._measure()
                o2 = env._get_observations()["policy"].clone()
                cm2 = env.controller_m if env.sensor is not None else env.m
                t2 = env.m["obj_pos"].clone()
                keys = ["obj_pos", "grasp_from_obj", "obj_rel_linvel", "obj_rel_speed", "obj_rel_in_recv", "grasp_error"]
                snapshots.append({
                    "step": steps, "truth_shift_m": (t2 - t1).mean(0).tolist(),
                    "obs_max_abs_change": float((o2 - o1).abs().max()),
                    "obs_changed_channels": sorted({int(c) % 46 for c in ((o2 - o1).abs() > 1e-7).nonzero()[:, 1].tolist()}),
                    "controller_max_abs_change": {k: float((cm2[k] - cm1[k]).abs().max()) for k in keys},
                    "giver_reference_active_frac": float(((~env.released) & (env.m["giver_force_l"] > env.cfg.contact_force)
                                                          & (env.m["giver_force_r"] > env.cfg.contact_force)).float().mean()),
                })
                # move it back so the episode continues physically unchanged
                pose[:, :3] -= delta
                env.obj.write_root_pose_to_sim_index(root_pose=pose, env_ids=torch.arange(env.num_envs, device=env.device))
                env._measure()
        nonvac = all(abs(s["truth_shift_m"][0] - 0.003) < 1e-5 for s in snapshots)
        if v == "archived":
            checks = {"truth_shift_applied": nonvac and bool(snapshots),
                      "archived_path_is_sensitive (control)": all(s["obs_max_abs_change"] > 1e-4 for s in snapshots)}
        else:
            checks = {"truth_shift_applied": nonvac and bool(snapshots),
                      "actor_input_unchanged": all(s["obs_max_abs_change"] == 0.0 for s in snapshots),
                      "controller_object_channels_unchanged": all(max(s["controller_max_abs_change"].values()) == 0.0 for s in snapshots)}
        return {"check": "dependency", "variant": v, "snapshots": snapshots, "checks": checks, "ok": all(checks.values()),
                "allowed_accurate_channels": "giver_tcp - recv_tcp (obs 12:15), finger widths (15:17), contact forces (17:21), "
                                             "receiver joints (21:35), object orientation (3:6) and angular velocity (9:12), "
                                             "nominal target (35:38), time (38), residual (39:42), contact phase (42:46)"}

    sim("combined", 8, over, body)


# ----------------------------------------------------------------------------------- check 8: inputs and normalization
def check_inputs():
    mode = args_ns.mode
    over = {"observation_sensor": MIXED_SENSOR, "observation_history": 5,
            "observation_history_mode": "repeat_current" if mode == "repeat_current" else "stack"}
    if mode == "permuted":
        over["observation_history_permutation"] = [4, 2, 0, 3, 1]

    def body(env, rt):
        import torch

        from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper
        from tensordict import TensorDict

        from csci645_handover.agents.ppo_cfg import HandoverPPORunnerCfg, make_runner

        cases = dev_cases("mixed_id", 2)
        env.set_case_queue(cases)
        env.completed_records, env.traces, env.trace_env_ids = [], {}, []
        obs, _ = env.reset()
        cur, full = [], []
        for _ in range(80):
            obs, *_ = env.step(torch.zeros(env.num_envs, 3, device=env.device))
            full.append(obs["policy"].clone())
            # the current single frame, computed without touching the history buffer
            h, md = env.cfg.observation_history, env.cfg.observation_history_mode
            env.cfg.observation_history = 1
            cur.append(env._get_observations()["policy"].clone())
            env.cfg.observation_history = h
        dims_ok = full[-1].shape[-1] == 230 and cur[-1].shape[-1] == 46
        k = 70
        frames = full[k].reshape(env.num_envs, 5, 46)
        if mode == "stack":
            order_ok = all(torch.equal(frames[:, j], cur[k - 4 + j]) for j in range(5))
        elif mode == "repeat_current":
            order_ok = all(torch.equal(frames[:, j], cur[k]) for j in range(5))
        else:
            chron = [cur[k - 4 + j] for j in range(5)]
            order_ok = all(torch.equal(frames[:, j], chron[p]) for j, p in enumerate([4, 2, 0, 3, 1]))
        agent = HandoverPPORunnerCfg()
        agent.device = "cuda:0"
        runner, agent = make_runner(RslRlVecEnvWrapper(env, clip_actions=None), agent, log_dir=None)
        res = {"check": "inputs", "mode": mode, "obs_dim": int(full[-1].shape[-1]), "frame_order_ok": order_ok,
               "obs_groups": dict(agent.obs_groups)}
        checks = {"dims_46_230": dims_ok, "frame_order": order_ok,
                  "critic_sees_only_policy_observation": dict(agent.obs_groups) == {"actor": ["policy"], "critic": ["policy"]}}
        if args_ns.checkpoint:
            infos = runner.load(args_ns.checkpoint, map_location="cuda:0") or {}
            norm = [m for m in runner.alg.get_policy().modules() if hasattr(m, "_mean") or hasattr(m, "mean")]
            sd0 = {k: v.clone() for k, v in runner.alg.get_policy().state_dict().items()}
            pol = runner.get_inference_policy(device="cuda:0")
            for _ in range(20):
                obs, *_ = env.step(pol(TensorDict(obs, batch_size=[env.num_envs])))
            sd1 = runner.alg.get_policy().state_dict()
            changed = [k for k in sd0 if not torch.equal(sd0[k], sd1[k])]
            checks["checkpoint_shape_compatible"] = infos.get("obs_dim") == 230
            checks["normalizer_frozen_at_inference"] = not changed
            res.update(checkpoint_obs_dim=infos.get("obs_dim"), state_changed_during_inference=changed,
                       normalizer_modules=len(norm))
        res["checks"], res["ok"] = checks, all(checks.values())
        return res

    sim("combined", 4, over, body)


if __name__ == "__main__":
    {"sensor": check_sensor, "residual": check_residual, "boundary": check_boundary,
     "dependency": check_dependency, "inputs": check_inputs}[args_ns.check]()
