#!/usr/bin/env python3
"""Outcome differences between zero-residual untrained policies and the identical deterministic controller.

    python3 scripts/v2_nondeterminism.py --final <raw>/final/eval > results/v2/summary/nondeterminism_untrained_vs_zero.json

The zero-mean untrained combined/combined_no_phase policies output exactly zero residual, i.e. they are 1.5 cm
geometry; the untrained residual policies are nominal. Any terminal-reason difference is simulator
nondeterminism across evaluation processes / batch layouts.
"""

import argparse
import glob
import json


def load(p):
    return {json.loads(line)["case_id"]: json.loads(line) for line in open(p)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--final", required=True)
    a = ap.parse_args()
    G = load(glob.glob(f"{a.final}/det_*/geometry_1p5cm.jsonl")[0])
    N = load(glob.glob(f"{a.final}/det_*/nominal.jsonl")[0])
    out = {}
    for m, ref, name in (("combined", G, "geometry_1p5cm"), ("combined_no_phase", G, "geometry_1p5cm"), ("residual", N, "nominal")):
        for s in (11, 22, 33):
            U = load(f"{a.final}/{m}_seed{s}/{m}_seed{s}__untrained.jsonl")
            assert all(r["residual_abs_max_m"] == 0 for r in U.values())
            d = [c for c in U if U[c]["terminal_reason"] != ref[c]["terminal_reason"]]
            out[f"{m}_seed{s}_untrained_vs_{name}"] = {"cases": len(U), "terminal_reason_differs": len(d), "examples": sorted(d)[:4]}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
