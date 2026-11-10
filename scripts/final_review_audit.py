#!/usr/bin/env python3
"""Independent CPU review of published V4 raw outcomes; never imports the simulator.

python scripts/final_review_audit.py --archive downloads/v4-review/raw-final.tar.gz
The archive is read without extracting files. Existing scientific outputs are read-only.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = "26b27cd5f9d97f1a6dea85412ecb050aba772eb84fee6bd9a9f18038bf7cf627"
EXPERIMENT = "aac4d98274814b1ab121a715db71187e3e1cc0b9"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text())


def paired_bootstrap(a, b, confidence=0.95, repeats=10000, seed=6456401):
    """Independent implementation for a single condition, paired seeds and cases."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    require(a.ndim == b.ndim == 2 and a.shape[1] == b.shape[1], "unaligned cases")
    require(a.shape[0] == b.shape[0] or min(a.shape[0], b.shape[0]) == 1, "unaligned seeds")
    require(min(a.shape + b.shape) > 0, "empty sample")
    delta = a - b
    nseed, ncase = delta.shape
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(repeats):
        seeds = rng.integers(nseed, size=nseed)
        cases = rng.integers(ncase, size=ncase)
        draws.append(delta[np.ix_(seeds, cases)].mean() * 100)
    tail = (1 - confidence) / 2
    lo, hi = np.quantile(draws, [tail, 1 - tail])
    return {"difference_pp": float(delta.mean() * 100), "ci_low_pp": float(lo),
            "ci_high_pp": float(hi), "confidence": confidence,
            "bootstrap_repeats": repeats, "bootstrap_seed": seed}


def validate_rows(rows, suite, expected):
    require(len(rows) == len(suite), "wrong record count")
    by_id = {r["case_id"]: r for r in rows}
    require(len(by_id) == len(rows), "duplicate case_id")
    require(set(by_id) == set(suite), "missing or extra case_id")
    for case_id, r in by_id.items():
        require(r["condition"] == suite[case_id]["condition"], "condition mismatch")
        for key, value in expected.items():
            require(key in r and r[key] == value, f"provenance mismatch: {key}")
        require(type(r["success"]) is bool and type(r["reset_valid"]) is bool, "nonboolean outcome")
        require(r["reset_valid"] or not r["success"], "invalid reset scored as success")
    return by_id


def common_valid_case_ids(datasets, ids):
    """Intersect the same case IDs across every executed entry; never filter per method."""
    return [i for i in ids if all(d[i]["reset_valid"] for d in datasets)]


def audit(archive):
    require(digest(archive.read_bytes()) == ARCHIVE_SHA, "raw archive checksum mismatch")
    index = load("configs/v4/final_matrix_index.json")
    suite_bytes = (ROOT / index["suite"]).read_bytes()
    require(digest(suite_bytes) == index["suite_sha256"], "suite checksum mismatch")
    suite = {r["case_id"]: r for r in map(json.loads, suite_bytes.splitlines())}
    require(len(suite) == 2400, "suite size mismatch")
    conditions = sorted({r["condition"] for r in suite.values()})
    ids = {c: sorted((i for i in suite if suite[i]["condition"] == c),
                     key=lambda i: suite[i]["base_case_id"]) for c in conditions}
    require(len(conditions) == 12 and all(len(v) == 200 for v in ids.values()), "suite strata")
    data, groups = {}, defaultdict(list)
    with tarfile.open(archive) as tar:
        names = [m.name for m in tar.getmembers()]
        require(len(names) == len(set(names)), "duplicate archive names")
        for entry in index["entries"]:
            path = entry["records"]
            if path not in data:
                member = tar.getmember(path)
                require(member.isfile(), f"not a regular file: {path}")
                raw = tar.extractfile(member).read()
                require(digest(raw) == entry["sha256"], f"record checksum mismatch: {path}")
                rows = validate_rows([json.loads(x) for x in raw.splitlines()], suite, entry["expected"])
                data[path] = {i: {k: r[k] for k in ("success", "reset_valid", "condition")} for i, r in rows.items()}
            else:
                require(entry.get("alias_of") == "geometry_calibrated", "undeclared alias")
                require(entry["sha256"] == next(e["sha256"] for e in index["entries"]
                                               if e["records"] == path), "alias hash mismatch")
            groups[(entry["family"], entry["role"])].append((entry["seed"], data[path]))
    require(len(data) == 54 and len(index["entries"]) == 55, "matrix size mismatch")
    for g in groups.values():
        g.sort(key=lambda x: -1 if x[0] is None else x[0])

    def array(family, role, case_ids):
        return np.array([[d[i]["success"] for i in case_ids] for _, d in groups[(family, role)]], float)

    for row in load("results/v4/summary/family_condition_summary.json"):
        a = array(row["family"], row["role"], ids[row["condition"]])
        require(np.allclose(a.mean(axis=1), row["success_rate_per_seed"], atol=1e-12, rtol=0), "per-seed rate mismatch")
        require(abs(a.mean() - row["success_rate_mean"]) < 1e-12, "family rate mismatch")
        invalid = sum(not d[i]["reset_valid"] for _, d in groups[(row["family"], row["role"])] for i in ids[row["condition"]])
        require(invalid == row["invalid_resets_total"], "invalid reset total mismatch")

    primary = []
    for row in load("results/v4/summary/paired_effects.json"):
        if not row["primary"]:
            continue
        require(row["conditions"] == ["mixed_id"], "unexpected primary condition")
        a, b = [array(row[side], row[f"{side}_role"], ids["mixed_id"]) for side in ("left", "right")]
        for conf, original in ((0.95, row), (0.975, row["bonferroni_97_5"])):
            result = paired_bootstrap(a, b, confidence=conf)
            for k in ("difference_pp", "ci_low_pp", "ci_high_pp"):
                require(abs(result[k] - original[k]) < 1e-9, f"primary estimate mismatch: {k}")
            primary.append({"left": row["left"], "right": row["right"], **result})
    require(len(primary) == 4, "expected two primary contrasts and two confidence levels")

    invalid_sets = [{i for i, r in d.items() if not r["reset_valid"]} for d in data.values()]
    invalid_union = set.union(*invalid_sets)
    boundary = "boundary_x_minus_7"
    require(all(suite[i]["condition"] == boundary for i in invalid_union), "invalid resets outside boundary")
    common = common_valid_case_ids(list(data.values()), ids[boundary])
    sensitivity = []
    for family in ("combined_robust_history", "combined_robust_ff", "combined_robust_repeat"):
        for cohort, case_ids in (("all_scheduled", ids[boundary]), ("common_valid_posthoc", common)):
            a, b = array(family, "selected", case_ids), array("geometry_calibrated", "baseline", case_ids)
            sensitivity.append({"family": family, "cohort": cohort, "cases_per_seed": len(case_ids),
                                "success_pct_per_seed": (a.mean(axis=1) * 100).tolist(),
                                "success_pct": float(a.mean() * 100), "parent_success_pct": float(b.mean() * 100),
                                **paired_bootstrap(a, b)})

    freeze = load("configs/v4/FREEZE.json")
    for path, sha in freeze["inputs"].items():
        blob = subprocess.check_output(["git", "show", f"{EXPERIMENT}:{path}"], cwd=ROOT)
        require(digest(blob) == sha, f"frozen source mismatch: {path}")
    selections = []
    for run in freeze["runs"]:
        s = load(f"results/v4/selection/{run}.json")
        require(all(c["transitions"] > 0 for c in s["candidates"]), "step zero eligible")
        best = min(s["candidates"], key=lambda c: (-round(c["success_rate"], 12), round(c["unsafe_rate"], 12),
                   round(c["residual_magnitude_m"], 12), -c["transitions"]))
        require(best["tag"] == s["selected"], "selection mismatch")
        selections.append({"run": run, "selected": best["tag"]})
    values = load("results/v4/report_values.json")
    template = (ROOT / "report/v4/report_template.md").read_text()
    rendered = re.sub(r"\{\{([A-Za-z0-9_.\-]+)\}\}", lambda m: values[m[1]]["text"], template)
    require(rendered == (ROOT / "report/v4/report.md").read_text(), "report template drift")
    dev = load("results/v4/development/round2_summary.json")
    matched = {name: {c: dev[name][c] for c in ("grasp_15mm", "mixed_id", "mixed_ood")}
               for name in ("ema0p2_fixed_a25", "ema0p2_cal050_a25")}
    return {"schema": 1, "scope": "CPU audit of published V4 records; no simulation or training",
            "archive_sha256": ARCHIVE_SHA, "experiment_commit": EXPERIMENT, "passed": True,
            "executed_files": len(data), "executed_episodes": sum(map(len, data.values())),
            "logical_entries": len(index["entries"]), "frozen_inputs_verified": len(freeze["inputs"]),
            "all_published_success_and_invalid_reset_summaries_match": True,
            "primary_recomputed": primary, "selection_from_recorded_validation_summaries": selections,
            "published_report_matches_template": True,
            "invalid_reset_records": sum(map(len, invalid_sets)),
            "invalid_in_any_entry": sorted(invalid_union),
            "invalid_in_every_entry": sorted(set.intersection(*invalid_sets)),
            "common_valid_boundary_cases": len(common), "boundary_sensitivity": sensitivity,
            "matched_development_only": matched,
            "limits": ["No independent GPU replay or checkpoint-weight validation in this review.",
                       "Selection is checked against recorded candidate summaries, not reloaded raw validation files.",
                       "Common-valid analysis is post hoc and conditional on outcomes of the reset procedure.",
                       "The primary all-scheduled denominator and all published scientific outputs are unchanged."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results/final_review/audit.json")
    args = parser.parse_args()
    result = audit(args.archive)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"PASS: {result['executed_episodes']} episodes; {result['common_valid_boundary_cases']} common-valid boundary cases; {args.out}")


if __name__ == "__main__":
    main()
