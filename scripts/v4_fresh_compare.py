#!/usr/bin/env python3
"""Compare public-download V4 replays/reloads/resume with the published final records (CPU, standard library).

    python3 -I scripts/v4_fresh_compare.py --x <extracted release with replay60/, reload/, resume_check/> \
        --index configs/v4/final_matrix_index.json --output <fresh_gpu.json>

replay60: geometry_calibrated and combined_robust_history_s111 selected on the 60-case subset (batch 20); reload: one
selected checkpoint per architecture on 12 cases (first case of each condition); resume: two PPO iterations. Checks
exact case-ID sets against the subset suites, uniqueness, valid resets, observation-error and grasp-offset specs,
checkpoint SHA-256 and terminal outcomes against the published batch-240 final records. Every mismatch is listed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--x", required=True)
    ap.add_argument("--index", default=str(ROOT / "configs/v4/final_matrix_index.json"))
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    X = Path(a.x)
    idx = {(e["family"], e["role"], e["seed"]): e["records"] for e in json.loads(Path(a.index).read_text())["entries"]}
    suites = {"replay60": [json.loads(l)["case_id"] for l in (ROOT / "configs/v4/suites/final_subset60.jsonl").read_text().splitlines() if l.strip()],
              "reload": [json.loads(l)["case_id"] for l in (ROOT / "configs/v4/suites/final_reload12.jsonl").read_text().splitlines() if l.strip()]}
    out = {"replay60": [], "reload": [], "mismatches": []}
    for kind in ("replay60", "reload"):
        for d in sorted((X / kind).iterdir()):
            f = next(p for p in d.glob("*.jsonl") if p.name != "eval_runs.jsonl")
            rows = jl(f)
            entry = f.stem
            key = (entry, "baseline", None) if "__" not in entry else (entry.split("__")[0].rsplit("_s", 1)[0], "selected",
                                                                       int(entry.split("__")[0].rsplit("_s", 1)[1]))
            pub = {r["case_id"]: r for r in jl(X / idx[key])}
            ids = [r["case_id"] for r in rows]
            row = {"entry": entry, "cases": len(rows), "unique": len(set(ids)) == len(ids),
                   "id_set_equal": sorted(ids) == sorted(suites[kind]),
                   "invalid_resets": sum(not r["reset_valid"] for r in rows),
                   "terminal_equal": sum(r["terminal_reason"] == pub[r["case_id"]]["terminal_reason"] for r in rows),
                   "success_equal": sum(r["success"] == pub[r["case_id"]]["success"] for r in rows),
                   "specs_equal": all(r["observation_error"] == pub[r["case_id"]]["observation_error"] and
                                      r["grasp_offset_requested_xyz_m"] == pub[r["case_id"]]["grasp_offset_requested_xyz_m"] for r in rows),
                   "checkpoint_sha256_equal": all(r.get("checkpoint_sha256") == pub[r["case_id"]].get("checkpoint_sha256") for r in rows),
                   "config_hash_equal": all(r["config_hash"] == pub[r["case_id"]]["config_hash"] for r in rows)}
            for r in rows:
                if r["terminal_reason"] != pub[r["case_id"]]["terminal_reason"]:
                    out["mismatches"].append({"kind": kind, "entry": entry, "case": r["case_id"], "fresh": r["terminal_reason"],
                                              "published": pub[r["case_id"]]["terminal_reason"]})
            out[kind].append(row)
    ins = X / "resume_check/inspect.json"
    out["resume"] = json.loads(ins.read_text()) if ins.exists() else None
    out["summary"] = {"replay60_episodes": sum(r["cases"] for r in out["replay60"]),
                      "replay60_terminal_equal": sum(r["terminal_equal"] for r in out["replay60"]),
                      "reload_episodes": sum(r["cases"] for r in out["reload"]),
                      "reload_terminal_equal": sum(r["terminal_equal"] for r in out["reload"]),
                      "mismatches": len(out["mismatches"]), "resume_ok": bool(out["resume"] and out["resume"].get("ok"))}
    out["ok"] = (len(out["replay60"]) == 2 and len(out["reload"]) == 5
                 and all(r["unique"] and r["id_set_equal"] and r["invalid_resets"] == 0 and r["specs_equal"]
                         and r["checkpoint_sha256_equal"] and r["config_hash_equal"] for r in out["replay60"] + out["reload"])
                 and out["summary"]["resume_ok"])
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({**out["summary"], "ok": out["ok"]}))


if __name__ == "__main__":
    main()
