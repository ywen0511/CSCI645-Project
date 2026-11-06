#!/usr/bin/env python3
"""Compare a resumed checkpoint with the checkpoint it resumed from (needs torch; run with the Isaac Lab Python).

    python scripts/closeout_inspect_ckpt.py --before <downloaded latest.pt> --after <disposable run>/checkpoints/final.pt \
        --expect-iterations 308 --expect-transitions 10092544 --output inspect.json

Records the restored and saved counters, the optimizer state, the observation-normalisation statistics and the
RNG state, then reloads the saved file a second time to prove it round-trips. Exit code 1 if a check fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def tensors(d, prefix=""):
    import torch
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(tensors(v, f"{prefix}{k}."))
    elif isinstance(d, (list, tuple)):
        for i, v in enumerate(d):
            out.update(tensors(v, f"{prefix}{i}."))
    elif isinstance(d, torch.Tensor):
        out[prefix[:-1]] = d
    return out


def main():
    import torch

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--expect-iterations", type=int, required=True)
    ap.add_argument("--expect-transitions", type=int, required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    b = torch.load(a.before, map_location="cpu", weights_only=False)
    f = torch.load(a.after, map_location="cpu", weights_only=False)
    f2 = torch.load(a.after, map_location="cpu", weights_only=False)  # second, independent reload

    def info(ck):
        inf = ck.get("infos", ck)
        return {"iterations_done": inf.get("iterations_done"), "transitions": inf.get("transitions"),
                "keys": sorted(ck.keys())}

    norm_keys = lambda ck: {k: v for k, v in tensors(ck).items() if "normalizer" in k.lower() or "obs_norm" in k.lower()}
    opt_b, opt_f = ck_opt(b), ck_opt(f)
    nb, nf = norm_keys(b), norm_keys(f)
    model_b, model_f = tensors(b.get("model_state_dict", b.get("actor_state_dict", {}))), \
        tensors(f.get("model_state_dict", f.get("actor_state_dict", {})))
    changed = sum(int(not torch.equal(model_b[k], model_f[k])) for k in model_b if k in model_f)
    norm_changed = sum(int(not torch.equal(nb[k], nf[k])) for k in nb if k in nf)
    same_reload = all(torch.equal(v, tensors(f2)[k]) for k, v in tensors(f).items())
    ib, iF = info(b), info(f)
    rep = {
        "before": {"file": Path(a.before).name, "sha256": hashlib.sha256(Path(a.before).read_bytes()).hexdigest(), **ib},
        "after": {"file": Path(a.after).name, "sha256": hashlib.sha256(Path(a.after).read_bytes()).hexdigest(), **iF},
        "expected_after": {"iterations_done": a.expect_iterations, "transitions": a.expect_transitions},
        "optimizer_state_present": {"before": opt_b is not None, "after": opt_f is not None},
        "optimizer_step_counts": {"before": opt_steps(opt_b), "after": opt_steps(opt_f)},
        "normalizer_tensors": {"before": len(nb), "after": len(nf), "changed_by_2_iterations": norm_changed},
        "model_tensors": len(model_b), "model_tensors_changed_by_2_iterations": changed,
        "rng_state_present": {"before": "rng" in b.get("infos", b), "after": "rng" in f.get("infos", f)},
        "reload_identical": same_reload,
    }
    checks = {
        "counters_restored_and_advanced": iF["iterations_done"] == a.expect_iterations
        and iF["transitions"] == a.expect_transitions and ib["iterations_done"] == a.expect_iterations - 2,
        "optimizer_state_saved": opt_f is not None and opt_b is not None,
        "normalizer_present": len(nf) > 0 and len(nf) == len(nb),
        "parameters_updated": changed > 0,
        "reload_identical": same_reload,
    }
    rep["checks"] = checks
    rep["ok"] = all(checks.values())
    Path(a.output).write_text(json.dumps(rep, indent=1, default=str) + "\n")
    print(json.dumps(rep, indent=1, default=str))
    raise SystemExit(0 if rep["ok"] else 1)


def ck_opt(ck):
    for k in ("optimizer_state_dict", "optimizer"):
        if k in ck:
            return ck[k]
    return None


def opt_steps(opt):
    try:
        st = opt["state"]
        v = next(iter(st.values()))
        s = v.get("step")
        return float(s) if s is not None else None
    except Exception:
        return None


if __name__ == "__main__":
    main()
