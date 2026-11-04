#!/usr/bin/env python3
"""Stage 1 audit: reconcile the downloaded v1.0.0 raw records, checkpoints and selection (CPU only).

    python3 scripts/v2_audit_v1.py --bundle downloads/v1.0.0 --extracted downloads/v1.0.0/extracted \
        --output results/v2/audit/v1_reconciliation.json

Checks per evaluation file: record count, condition counts, non-stress/stress grouping, identical case-ID sets
across methods, duplicates, invalid resets, infrastructure errors, checkpoint SHA-256 versus the extracted
archive member and the release index, recorded checkpoint transitions versus the training ledger, and the
selected checkpoint versus the v1 selection files. Also recomputes grouped success from raw records.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_dir(d: Path) -> dict[str, list[dict]]:
    return {f.name: [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
            for f in sorted(d.glob("*.jsonl")) if f.name != "eval_runs.jsonl"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    B, X = Path(a.bundle), Path(a.extracted)
    R = X / "results"
    index = {r["run_id"]: r for r in json.loads((B / "checkpoints.json").read_text())}
    suite = [json.loads(x) for x in (R / "suites/final.jsonl").read_text().splitlines() if x.strip()]
    suite_ids = {c["case_id"] for c in suite}
    cond_counts = collections.Counter(c["condition"] for c in suite)
    out = {"suite": {"cases": len(suite), "conditions": dict(cond_counts),
                     "non_stress_cases": sum(v for k, v in cond_counts.items() if "stress" not in k),
                     "stress_cases": sum(v for k, v in cond_counts.items() if "stress" in k),
                     "non_stress_conditions": sorted(k for k in cond_counts if "stress" not in k),
                     "stress_conditions": sorted(k for k in cond_counts if "stress" in k)},
           "analyses": {}, "problems": []}
    for name, sub in (("primary", "eval"), ("secondary_final_checkpoint", "eval_final_checkpoint")):
        files = load_dir(R / sub)
        rows_out = {}
        for fn, rows in files.items():
            ids = [r["case_id"] for r in rows]
            st = [r for r in rows if "stress" in r["condition"]]
            ns = [r for r in rows if "stress" not in r["condition"]]
            rec = {
                "records": len(rows), "unique_case_ids": len(set(ids)), "duplicates": len(ids) - len(set(ids)),
                "case_ids_equal_suite": set(ids) == suite_ids, "invalid_resets": sum(not r["reset_valid"] for r in rows),
                "infrastructure_errors": sum(r["terminal_reason"] == "infrastructure_error" for r in rows),
                "non_stress_records": len(ns), "stress_records": len(st),
                "success_non_stress": sum(r["success"] for r in ns) / max(1, len(ns)),
                "success_stress": sum(r["success"] for r in st) / max(1, len(st)),
                "success_all": sum(r["success"] for r in rows) / max(1, len(rows)),
                "terminal_reasons": dict(collections.Counter(r["terminal_reason"] for r in rows)),
            }
            run_id = rows[0].get("run_id")
            ck_sha = {r.get("checkpoint_sha256") for r in rows}
            ck_tr = {r.get("checkpoint_transitions") for r in rows}
            if run_id in index:
                tag = rows[0]["checkpoint"]
                member = X / run_id / "checkpoints" / f"{tag}.pt"
                rec["checkpoint"] = tag
                rec["checkpoint_sha256_records"] = sorted(x for x in ck_sha if x)
                rec["checkpoint_sha256_member"] = sha(member) if member.exists() else None
                rec["checkpoint_sha256_index"] = index[run_id]["member_sha256"].get(f"{tag}.pt")
                rec["checkpoint_hash_consistent"] = (len(ck_sha) == 1 and rec["checkpoint_sha256_member"] in ck_sha
                                                     and rec["checkpoint_sha256_index"] in ck_sha)
                led = [json.loads(x) for x in (R / "train" / run_id / "checkpoints.jsonl").read_text().splitlines() if x.strip()]
                led_tr = {r["tag"]: r["transitions"] for r in led}
                rec["checkpoint_transitions_records"] = sorted(x for x in ck_tr if x is not None)
                rec["checkpoint_transitions_ledger"] = led_tr.get(tag)
                rec["transitions_consistent"] = ck_tr == {led_tr.get(tag)}
                if name == "primary":
                    sel = json.loads((R / "selection" / f"{run_id}.json").read_text())
                    chosen = sel.get("selected", sel).get("checkpoint") if isinstance(sel.get("selected", sel), dict) else sel.get("selected")
                    rec["selection_file_choice"] = chosen
                    rec["selection_consistent"] = (chosen == tag) and (index[run_id]["selected_checkpoint"] == tag)
                for k in ("checkpoint_hash_consistent", "transitions_consistent", "selection_consistent"):
                    if rec.get(k) is False:
                        out["problems"].append(f"{name}/{fn}: {k} is False")
            for k in ("duplicates", "invalid_resets", "infrastructure_errors"):
                if rec[k]:
                    out["problems"].append(f"{name}/{fn}: {k}={rec[k]}")
            if not rec["case_ids_equal_suite"]:
                out["problems"].append(f"{name}/{fn}: case IDs differ from the suite")
            rows_out[fn] = rec
        out["analyses"][name] = {"files": len(files), "records": sum(len(v) for v in files.values()), "per_file": rows_out}
    out["label_audit"] = ("v1 tables labelled the non-stress aggregate '1,400 in-range cases' and the stress aggregate "
                          "'400 cases'; the analysis code pools conditions by the substring 'stress', i.e. "
                          f"{out['suite']['non_stress_cases']} non-stress cases (incl. clean) and "
                          f"{out['suite']['stress_cases']} stress cases.")
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"problems": out["problems"], "suite": out["suite"],
                      "records": {k: v["records"] for k, v in out["analyses"].items()}}, indent=1))


if __name__ == "__main__":
    main()
