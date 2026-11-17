"""Train a learned residual method with RSL-RL PPO to a fixed environment-transition budget.

Example:
    python scripts/train.py --method combined --seed 11 \
        --protocol configs/frozen/protocol.json --output runs/combined_seed11
    python scripts/train.py ... --resume runs/combined_seed11/checkpoints/latest.pt

Transitions count every vectorized environment step over all environments (including the scripted
reset-settling steps, during which the residual is disabled). Checkpoints are written at the first PPO
iteration boundary at or after every ``checkpoint_interval_transitions`` (plus the untrained policy at 0
and the final policy). Each checkpoint stores actor/critic (including observation-normalization
statistics), optimizer, iteration, transition counter, curriculum stage, RNG states, and the resolved
configuration hashes. Resume restores them and restarts environments at episode boundaries; it is an
approximate continuation, not a bitwise replay of the simulator state.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--method", choices=["residual", "combined", "combined_no_phase"], required=True)
parser.add_argument("--seed", type=int, required=True)
parser.add_argument("--protocol", default="configs/frozen/protocol.json")
parser.add_argument("--output", required=True)
parser.add_argument("--num-envs", type=int, default=None, help="Overrides protocol training.num_envs.")
parser.add_argument("--transitions", type=int, default=None, help="Overrides the protocol transition budget.")
parser.add_argument("--checkpoint-every", type=int, default=None, help="Overrides checkpoint interval [transitions].")
parser.add_argument("--resume", default=None, help="Checkpoint to resume from.")
parser.add_argument("--run-type", default="final", choices=["smoke", "pilot", "final"])
add_launcher_args(parser)
args = parser.parse_args()


def main():
    import numpy as np
    import torch

    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

    from csci645_handover import runtime as rt
    from csci645_handover.agents.ppo_cfg import HandoverPPORunnerCfg, apply_ppo_overrides, make_runner

    protocol = json.loads(Path(args.protocol).read_text())
    tr = protocol["training"]
    overrides = dict(protocol.get("env_overrides", {}))
    num_envs = args.num_envs or tr.get("num_envs", 1024)
    budget = args.transitions or tr["final_transitions_per_run"]
    ckpt_every = args.checkpoint_every or tr["checkpoint_interval_transitions"]
    device = args.device if getattr(args, "device", None) else "cuda:0"
    overrides["curriculum"] = tr["curriculum"]
    overrides["total_transitions"] = budget
    cfg = rt.build_env_cfg(args.method, num_envs, device, args.seed, overrides)

    agent = apply_ppo_overrides(HandoverPPORunnerCfg(), protocol.get("ppo_overrides", {}))
    agent.seed = args.seed
    agent.device = device
    batch = num_envs * agent.num_steps_per_env
    total_iters = math.ceil(budget / batch)

    out = Path(args.output)
    (out / "checkpoints").mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    with launch_simulation(cfg, args):
        from csci645_handover.tasks.handover_env import HandoverEnv

        env_raw = HandoverEnv(cfg)
        env = RslRlVecEnvWrapper(env_raw, clip_actions=None)
        runner, agent = make_runner(env, agent, log_dir=str(out / "tensorboard"))
        train_cfg = runner.cfg
        actor_init = tr.get("actor_init", "default")
        if actor_init == "zero_mean_output" and not args.resume:
            # v2 option: zero the actor's output layer so the deterministic residual mean is exactly 0 at step 0
            # (exploration noise std is unchanged; the stochastic training actions are NOT zero).
            import torch.nn as nn

            last = [mod for mod in runner.alg.get_policy().mlp.modules() if isinstance(mod, nn.Linear)][-1]
            with torch.no_grad():
                last.weight.zero_()
                last.bias.zero_()
        elif actor_init not in ("default", "zero_mean_output"):
            raise ValueError(f"unknown actor_init {actor_init}")

        meta = {
            "run_id": out.name, "method": args.method, "seed": args.seed, "run_type": args.run_type,
            "protocol": args.protocol, "protocol_sha256": rt.sha256_file(args.protocol),
            "config_hash": rt.config_hash(cfg), "env_cfg": rt.env_cfg_dict(cfg), "agent_cfg": train_cfg,
            "num_envs": num_envs, "rollout_batch_transitions": batch, "requested_transitions": budget,
            "realized_transitions": total_iters * batch, "total_iterations": total_iters,
            "checkpoint_interval_transitions": ckpt_every, "git": rt.git_state(), "hardware": rt.hardware_info(),
            "actor_init": actor_init,
        }
        if protocol.get("protocol_id", "").startswith(("v3", "v4")) and meta["git"]["dirty"]:
            raise RuntimeError("V3/V4 training requires clean committed executable source")
        start_iter, transitions = 0, 0
        if args.resume:
            if protocol.get("protocol_id", "").startswith(("v3", "v4")):
                ck = torch.load(args.resume, map_location="cpu", weights_only=False)
                prior = ck.get("infos", {})
                for key, value in {"method": args.method, "seed": args.seed, "obs_dim": cfg.observation_space,
                                   "config_hash": meta["config_hash"], "protocol_sha256": meta["protocol_sha256"],
                                   "source_commit": meta["git"]["commit"], "source_dirty": False}.items():
                    if prior.get(key) != value:
                        raise ValueError(f"Resume mismatch: {key}={prior.get(key)!r}, expected {value!r}")
            infos = runner.load(args.resume, map_location=device)
            transitions = int(infos["transitions"])
            start_iter = int(infos["iterations_done"])
            rng = infos.get("rng", {})
            if rng:
                torch.set_rng_state(rng["torch_cpu"].cpu())
                if torch.cuda.is_available() and rng.get("torch_cuda") is not None:
                    torch.cuda.set_rng_state(rng["torch_cuda"].cpu())
                np.random.set_state(rng["numpy"])
                random.setstate(rng["python"])
                env_raw.rng.set_state(rng["env"].cpu())  # generator states are CPU ByteTensors, also for CUDA
            meta["resumed_from"] = args.resume
            meta["resumed_transitions"] = transitions
            print(f"[train] resumed at iteration {start_iter}, transitions {transitions}")
        env_raw.set_transition_offset(transitions - int(env_raw.common_step_counter) * num_envs)
        env_raw.reset()  # restart all episodes at a boundary with the current curriculum stage
        (out / ("run_resume.json" if args.resume else "run.json")).write_text(json.dumps(meta, indent=2, default=str))

        log_path = out / "train_log.jsonl"
        ledger_path = out / "checkpoints.jsonl"

        def save_ckpt(tag: str, it_done: int, trans: int) -> None:
            path = out / "checkpoints" / f"{tag}.pt"
            stage = None
            for s in cfg.curriculum:
                if s["fraction_start"] <= min(1.0, trans / budget) < s["fraction_end"]:
                    stage = s
            infos = {
                "transitions": trans, "iterations_done": it_done, "method": args.method, "seed": args.seed,
                "config_hash": meta["config_hash"], "protocol_sha256": meta["protocol_sha256"],
                "source_commit": meta["git"]["commit"], "source_dirty": meta["git"]["dirty"],
                "curriculum_stage": stage, "phase_input": cfg.phase_input, "obs_dim": cfg.observation_space,
                "actor_init": actor_init, "protocol_id": protocol.get("protocol_id", "v1"),
                "rng": {
                    "torch_cpu": torch.get_rng_state(),
                    "torch_cuda": torch.cuda.get_rng_state() if torch.cuda.is_available() else None,
                    "numpy": np.random.get_state(), "python": random.getstate(), "env": env_raw.rng.get_state(),
                },
                "utc": rt.utc_now(),
            }
            runner.current_learning_iteration = it_done
            runner.save(str(path), infos=infos)
            torch.save(torch.load(path, weights_only=False), out / "checkpoints" / "latest.pt")
            row = {"tag": tag, "path": f"checkpoints/{tag}.pt", "transitions": trans, "iterations_done": it_done,
                   "sha256": rt.sha256_file(path), "utc": rt.utc_now()}
            with open(ledger_path, "a") as f:
                f.write(json.dumps(row) + "\n")

        if start_iter == 0:
            save_ckpt("step_000000000", 0, 0)
        next_ckpt = (transitions // ckpt_every + 1) * ckpt_every

        # ---- PPO loop (same structure as OnPolicyRunner.learn, with transition-boundary checkpoints) ----
        obs = env.get_observations().to(device)
        runner.alg.train_mode()
        runner.logger.init_logging_writer()
        t_start = time.time()
        last_stats = dict(env_raw.stats)
        last_scored = env_raw.scored_transitions_total
        scored_cum = 0
        for it in range(start_iter, total_iters):
            t0 = time.time()
            ep_rew = []
            with torch.inference_mode():
                for _ in range(agent.num_steps_per_env):
                    actions = runner.alg.act(obs)
                    obs, rewards, dones, extras = env.step(actions.to(env.device))
                    if not (torch.isfinite(rewards).all() and torch.isfinite(obs["policy"]).all()):
                        raise FloatingPointError(f"Non-finite reward/observation at iteration {it}")
                    obs, rewards, dones = obs.to(device), rewards.to(device), dones.to(device)
                    runner.alg.process_env_step(obs, rewards, dones, extras)
                    runner.logger.process_env_step(rewards, dones, extras, None)
                    ep_rew.append(float(rewards.mean()))
                collect = time.time() - t0
                runner.alg.compute_returns(obs)
            t1 = time.time()
            loss = runner.alg.update()
            learn = time.time() - t1
            runner.current_learning_iteration = it
            runner.logger.log(it=it, start_it=start_iter, total_it=total_iters, collect_time=collect, learn_time=learn,
                              loss_dict=loss, learning_rate=runner.alg.learning_rate,
                              action_std=runner.alg.get_policy().output_std, rnd_weight=None)
            for k, v in loss.items():
                if not math.isfinite(float(v)):
                    raise FloatingPointError(f"Non-finite loss {k}={v} at iteration {it}")
            transitions += batch
            d = {k: env_raw.stats[k] - last_stats[k] for k in env_raw.stats}
            last_stats = dict(env_raw.stats)
            scored_it = env_raw.scored_transitions_total - last_scored
            last_scored = env_raw.scored_transitions_total
            scored_cum += scored_it
            row = {
                "iteration": it + 1, "transitions": transitions, "collect_s": collect, "learn_s": learn,
                "fps": batch / max(1e-6, collect + learn), "mean_step_reward": sum(ep_rew) / len(ep_rew),
                "lr": float(runner.alg.learning_rate),
                "action_std": runner.alg.get_policy().output_std.detach().reshape(-1, 3)[0].cpu().tolist(),
                "scored_transitions": scored_it, "scored_transitions_this_process": scored_cum,
                "episodes": d["episodes"], **{f"train_{k}": v for k, v in d.items() if k != "episodes"},
                **{f"loss_{k}": float(v) for k, v in loss.items()},
                "wall_s": time.time() - t_start, "utc": rt.utc_now(),
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(row) + "\n")
            if (it + 1) % 10 == 0 or it == start_iter:
                print(f"[train] it={it+1}/{total_iters} trans={transitions} fps={row['fps']:.0f} "
                      f"rew={row['mean_step_reward']:.4f} eps={d['episodes']} succ={d['success']} drop={d['drop']}",
                      flush=True)
            if transitions >= next_ckpt or it + 1 == total_iters:
                tag = f"step_{transitions:09d}"
                save_ckpt(tag, it + 1, transitions)
                next_ckpt = (transitions // ckpt_every + 1) * ckpt_every
        save_ckpt("final", total_iters, transitions)
        runner.logger.stop_logging_writer()
        done = {"completed_utc": rt.utc_now(), "transitions": transitions, "iterations": total_iters,
                "scored_transitions_this_process": scored_cum,
                "wall_s": time.time() - t_start}
        (out / "DONE.json").write_text(json.dumps(done, indent=2))
        print(f"[train] done: {done}")
        env.close()


if __name__ == "__main__":
    main()
