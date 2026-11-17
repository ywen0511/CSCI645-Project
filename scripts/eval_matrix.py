"""Evaluate a matrix of controller configurations on one case suite in a single simulator process (v2).

The matrix is a JSON file::

    {"name": "dev_diagnostics", "suite": "configs/v2/suites/development.jsonl", "num_envs": 450,
     "protocol": "configs/frozen/protocol.json",          # optional: env_overrides + ppo_overrides
     "base_overrides": {},                                  # applied when the env is built
     "trace_cases": ["development-clean-0000", ...],        # traced for entries with "trace": true
     "entries": [
        {"id": "geometry_zero", "method": "geometry", "overrides": {}},
        {"id": "geometry_const_x+002", "method": "geometry", "overrides": {"constant_residual_m": [0.002, 0, 0]}},
        {"id": "combined_s11_final", "method": "combined", "checkpoint": "v1/combined_seed11/checkpoints/final.pt",
         "training_seed": 11, "trace": true}]}

Entry overrides may only touch fields that are safe to change on a live environment
(``runtime.RUNTIME_FIELDS``); everything else belongs in ``base_overrides`` (one process per base).
Before each entry the runtime fields are restored to the base values, so entries never leak settings.

Outputs in --output: ``<entry id>.jsonl`` (one record per case), ``traces/<entry id>.json``, ``eval_runs.jsonl``
(provenance per executed chunk) and ``matrix_status.json`` (scheduled/recorded/missing per entry).
Resume: existing records are checked against suite/config/controller/checkpoint hashes and completed case
IDs are skipped; a mismatch is an error (never mixes protocols). Units: meters, seconds.

Example:
    python scripts/eval_matrix.py --matrix configs/v2/matrices/dev_diagnostics.json \
        --output runs/v2/dev/diagnostics --checkpoint-root runs/v1_download
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--matrix", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--only", default="", help="Comma-separated entry IDs (default: all).")
parser.add_argument("--checkpoint-root", default="", help="Prefix for relative checkpoint paths.")
parser.add_argument("--num-envs", type=int, default=None)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--dry-run", action="store_true", help="Validate the matrix and print expected counts.")
add_launcher_args(parser)
args = parser.parse_args()


def resolve_ckpt(p: str | None) -> str | None:
    if not p:
        return None
    q = Path(p)
    if not q.is_absolute() and args.checkpoint_root:
        q = Path(args.checkpoint_root) / q
    return str(q)


def main():
    import torch

    from csci645_handover import runtime as rt
    from csci645_handover.core.case_suites import read_suite
    from csci645_handover.tasks.handover_env_cfg import METHODS

    mx = json.loads(Path(args.matrix).read_text())
    protocol = json.loads(Path(mx["protocol"]).read_text()) if mx.get("protocol") else {}
    base_over = dict(protocol.get("env_overrides", {}))
    base_over.update(mx.get("base_overrides", {}))
    cases_all, s_hash = read_suite(mx["suite"])
    only = {x for x in args.only.split(",") if x}
    entries = [e for e in mx["entries"] if not only or e["id"] in only]
    ids = [e["id"] for e in mx["entries"]]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate entry IDs in matrix")
    for e in entries:
        if e["method"] not in METHODS:
            raise SystemExit(f"{e['id']}: unknown method {e['method']}")
        bad = set(e.get("overrides", {})) - rt.RUNTIME_FIELDS
        if bad:
            raise SystemExit(f"{e['id']}: overrides {sorted(bad)} are not runtime-safe; use base_overrides")
        learned = METHODS[e["method"]]["residual_enabled"]
        if learned != bool(e.get("checkpoint")):
            raise SystemExit(f"{e['id']}: learned methods need a checkpoint; deterministic ones must not have one")
        if e.get("checkpoint") and not Path(resolve_ckpt(e["checkpoint"])).exists():
            raise SystemExit(f"{e['id']}: checkpoint not found: {resolve_ckpt(e['checkpoint'])}")

    def entry_cases(e):
        cs = cases_all
        if e.get("conditions"):
            keep = set(e["conditions"])
            cs = [c for c in cs if c["condition"] in keep]
        return cs

    expected = {e["id"]: len(entry_cases(e)) for e in entries}
    print(f"[eval_matrix] {mx.get('name')}: {len(entries)} entries, {sum(expected.values())} episodes scheduled",
          flush=True)
    if args.dry_run:
        print(json.dumps(expected, indent=1))
        return

    num_envs = args.num_envs or mx.get("num_envs") or min(len(cases_all), 900)
    device = args.device if getattr(args, "device", None) else "cuda:0"
    cfg = rt.build_env_cfg("combined", num_envs, device, args.seed, base_over)
    base_runtime = {k: getattr(cfg, k) for k in rt.RUNTIME_FIELDS}
    out = Path(args.output)
    (out / "traces").mkdir(parents=True, exist_ok=True)
    trace_ids = set(mx.get("trace_cases", []))
    status = {}

    with launch_simulation(cfg, args):
        from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper
        from tensordict import TensorDict

        from csci645_handover.agents.ppo_cfg import HandoverPPORunnerCfg, apply_ppo_overrides, make_runner
        from csci645_handover.tasks.handover_env import HandoverEnv

        env = HandoverEnv(cfg)
        git = rt.git_state()
        agent = apply_ppo_overrides(HandoverPPORunnerCfg(), protocol.get("ppo_overrides", {}))
        agent.device = device
        runner, agent = make_runner(RslRlVecEnvWrapper(env, clip_actions=None), agent, log_dir=None)

        for e in entries:
            for k, v in base_runtime.items():
                setattr(env.cfg, k, v)
            for k, v in METHODS[e["method"]].items():
                setattr(env.cfg, k, v)
            env.cfg.method = e["method"]
            for k, v in e.get("overrides", {}).items():
                setattr(env.cfg, k, v)
            env.refresh_task_parameters()
            c_hash, k_hash = rt.config_hash(env.cfg), rt.controller_hash(env.cfg)
            ckpt = resolve_ckpt(e.get("checkpoint"))
            ck_sha, infos, policy, mismatch = None, {}, None, None
            if ckpt:
                ck_sha = rt.sha256_file(ckpt)
                infos = runner.load(ckpt, map_location=device) or {}
                if infos.get("method") not in (None, e["method"]):
                    raise SystemExit(f"{e['id']}: checkpoint method {infos.get('method')} != {e['method']}")
                if infos.get("phase_input") not in (None, env.cfg.phase_input):
                    raise SystemExit(f"{e['id']}: checkpoint phase_input does not match the observation mask")
                if infos.get("config_hash") not in (None, c_hash):
                    mismatch = {"checkpoint_config_hash": infos.get("config_hash"), "eval_config_hash": c_hash}
                    if not e.get("allow_config_mismatch"):
                        raise SystemExit(f"{e['id']}: checkpoint config hash {infos.get('config_hash')} != {c_hash}; "
                                         "set allow_config_mismatch to evaluate under a different controller")
                net = runner.get_inference_policy(device=device)

                def policy(obs, net=net):
                    return net(TensorDict(obs, batch_size=[env.num_envs]))

            path = out / f"{e['id']}.jsonl"
            existing = rt.read_jsonl(path)
            if cases_all and cases_all[0].get("suite_version") in (3, 4):
                if cases_all[0]["suite_version"] == 4:
                    from csci645_handover.v4_protocol import validate_records
                else:
                    from csci645_handover.v3_protocol import validate_records

                # V3 caches must match the exact source and sensor realizations, not just counts.
                validate_records(existing, entry_cases(e), {
                    "suite_hash": s_hash, "config_hash": c_hash, "controller_hash": k_hash,
                    "checkpoint_sha256": ck_sha, "entry_id": e["id"],
                    "source_commit": git["commit"], "source_dirty": False,
                })
                if git["dirty"]:
                    raise SystemExit("V3 evaluation requires clean committed executable source")
            seen = set()
            for r in existing:
                if r["case_id"] in seen:
                    raise SystemExit(f"Duplicate record for {r['case_id']} in {path}")
                seen.add(r["case_id"])
                for key, val in (("suite_hash", s_hash), ("config_hash", c_hash), ("controller_hash", k_hash),
                                 ("checkpoint_sha256", ck_sha), ("entry_id", e["id"])):
                    if r.get(key) != val:
                        raise SystemExit(f"Existing record in {path} has {key}={r.get(key)!r}, expected {val!r}")
            cases = entry_cases(e)
            todo = [c for c in cases if c["case_id"] not in seen]
            print(f"[eval_matrix] {e['id']}: {len(existing)} existing, {len(todo)} to run", flush=True)
            if todo:
                tr = trace_ids if e.get("trace") else set()
                records, info = rt.run_cases(env, todo, policy=policy, trace_case_ids=tr)
                traces = info.pop("traces")
                for r in records:
                    r.update(entry_id=e["id"], group=e.get("group"), label=e.get("label"), method=e["method"],
                             run_id=e.get("run_id", e["id"]), training_seed=e.get("training_seed"),
                             checkpoint=Path(ckpt).stem if ckpt else None, checkpoint_sha256=ck_sha,
                             checkpoint_transitions=infos.get("transitions"), overrides=e.get("overrides", {}),
                             suite_hash=s_hash, config_hash=c_hash, controller_hash=k_hash,
                             config_mismatch=mismatch, source_commit=git["commit"], source_dirty=git["dirty"])
                rt.write_jsonl(path, records, append=True)
                got = {r["case_id"] for r in records}
                missing = [c["case_id"] for c in todo if c["case_id"] not in got]
                meta = {"entry_id": e["id"], "matrix": args.matrix, "matrix_sha256": rt.sha256_file(args.matrix),
                        "suite": mx["suite"], "suite_hash": s_hash, "config_hash": c_hash, "controller_hash": k_hash,
                        "checkpoint": e.get("checkpoint"), "checkpoint_sha256": ck_sha, "config_mismatch": mismatch,
                        "git": git, "hardware": rt.hardware_info(), "utc": rt.utc_now(), "missing_cases": missing,
                        "env_cfg": rt.env_cfg_dict(env.cfg), **info}
                rt.write_jsonl(out / "eval_runs.jsonl", [meta], append=True)
                if traces:
                    tp = out / "traces" / f"{e['id']}.json"
                    old = json.loads(tp.read_text()) if tp.exists() else {}
                    old.update(traces)
                    tp.write_text(json.dumps(old))
                n = len(records)
                print(f"[eval_matrix] {e['id']}: ran {n}, success={sum(r['success'] for r in records)}/{n} "
                      f"drop={sum(r['drop'] for r in records)} coll={sum(r['collision'] for r in records)} "
                      f"wall={info['wall_s']:.0f}s", flush=True)
            final = rt.read_jsonl(path)
            if cases_all and cases_all[0].get("suite_version") in (3, 4):
                validate_records(final, cases, {
                    "suite_hash": s_hash, "config_hash": c_hash, "controller_hash": k_hash,
                    "checkpoint_sha256": ck_sha, "entry_id": e["id"],
                    "source_commit": git["commit"], "source_dirty": False,
                }, complete=True)
            status[e["id"]] = {"scheduled": len(cases), "recorded": len(final),
                               "missing": len({c["case_id"] for c in cases} - {r["case_id"] for r in final}),
                               "success": sum(r["success"] for r in final)}
            torch.cuda.empty_cache()
        prev = json.loads((out / "matrix_status.json").read_text()) if (out / "matrix_status.json").exists() else {}
        prev.update(status)
        (out / "matrix_status.json").write_text(json.dumps(prev, indent=1, sort_keys=True))
        print("[eval_matrix] MATRIX_DONE", flush=True)
        env.close()


if __name__ == "__main__":
    main()
