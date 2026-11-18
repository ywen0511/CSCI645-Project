#!/usr/bin/env python3
"""Why EMA alpha had no effect in V5 Study A: compare the alpha 1.0 and alpha 0.2 runs field by field (CPU).

Added after v5.0.0 (docs/v5/DECISIONS.md, 2026-11-18); a description of executed runs, not a new analysis.

    python scripts/v5_ema_identity.py --archive raw-study-a.tar.gz [--out results/v5/calibration/ema_identity]
    python scripts/v5_ema_identity.py --records <extracted release>/study_a/primary     (as run by v5_regen.py)

For each (reference, bound) pair, the two configurations differ only in ``observation_sensor.ema_alpha``. The script
compares (1) every field of every per-episode record (2,400 cases per pair) and (2) every field of every sample of
the per-step traces, and classifies each trace sample in which the controller's object estimate differs by phase.

Code path (src/csci645_handover/tasks/handover_env.py, ``_measure``): with ``observation_giver_reference`` on, the
controller's object position is replaced by the giver-kinematic estimate whenever both giver contacts are closed and
the giver has not released; the calibration window averages the unfiltered measurement (``sensor.raw``), not the
EMA output. The EMA output therefore reaches the controller only while settling (the receiver command is pinned to
its start pose) and after the giver releases.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = "631a89fb664d367f32b39b0f8dd695cc09ae80091cb19fca77b778b97df77048"  # v5.0.0 raw-study-a.tar.gz
IDENTIFIERS = {"run_id", "entry_id", "config_hash", "controller_hash", "sensor_ema_alpha"}
ESTIMATE_FIELDS = {"estimated_obj_pos", "controller_obj_pos", "observed_rel_linvel", "align_corr"}
SETTLE, SCORED = 0, 1  # handover_env.py mode codes
PAIRS = [(r, b) for r in ("fixed", "cal050") for b in ("a15", "a25")]


def compare_records(a: list[dict], b: list[dict]) -> dict:
    ra, rb = {r["case_id"]: r for r in a}, {r["case_id"]: r for r in b}
    if set(ra) != set(rb) or len(ra) != len(a) or len(rb) != len(b):
        raise ValueError("record sets differ")
    diff = Counter()
    for cid, x in ra.items():
        y = rb[cid]
        for k in set(x) | set(y):
            if x.get(k) != y.get(k):
                diff[k] += 1
    other = sorted(set(diff) - IDENTIFIERS)
    return {"cases": len(ra), "differing_fields": dict(sorted(diff.items())), "non_identifier_fields_differing": other,
            "identical_terminal_outcomes": sum(ra[c]["terminal_reason"] == rb[c]["terminal_reason"] for c in ra)}


def compare_traces(a: dict, b: dict) -> dict:
    if set(a) != set(b):
        raise ValueError("traced cases differ")
    out = {}
    for case in sorted(a):
        sa, sb = a[case], b[case]
        if len(sa) != len(sb):
            raise ValueError(f"{case}: trace lengths differ")
        fields, phases = Counter(), Counter()
        for x, y in zip(sa, sb):
            for k in set(x) | set(y):
                if x.get(k) != y.get(k):
                    fields[k] += 1
            if x["controller_obj_pos"] != y["controller_obj_pos"]:
                if x["mode"] == SETTLE:
                    phases["settling"] += 1
                elif x["mode"] == SCORED and x["released"]:
                    phases["after_giver_release"] += 1
                else:
                    phases["other"] += 1
        out[case] = {"samples": len(sa), "differing_fields": dict(sorted(fields.items())),
                     "fields_outside_estimator": sorted(set(fields) - ESTIMATE_FIELDS - IDENTIFIERS),
                     "controller_estimate_differs_by_phase": dict(sorted(phases.items())),
                     "executed_command_p_exec_differs": fields.get("p_exec", 0)}
    return out


def compare_pairs(read) -> list[dict]:
    """``read(name)`` returns the bytes of ``study_a/primary/<name>``."""
    pairs = []
    for ref, bound in PAIRS:
        hi, lo = f"ema1p0_{ref}_{bound}", f"ema0p2_{ref}_{bound}"
        jsonl = lambda n: [json.loads(x) for x in read(f"{n}.jsonl").splitlines() if x.strip()]  # noqa: E731
        trace = lambda n: json.loads(read(f"traces/{n}.json"))  # noqa: E731
        pairs.append({"alpha_1p0": hi, "alpha_0p2": lo, "records": compare_records(jsonl(hi), jsonl(lo)),
                      "traces": compare_traces(trace(hi), trace(lo))})
    return pairs


def analyse(archive: Path | None = None, records: Path | None = None) -> dict:
    if (archive is None) == (records is None):
        raise ValueError("give exactly one of archive or records")
    if archive is not None:
        if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA:
            raise ValueError("archive checksum mismatch (expected the v5.0.0 raw-study-a.tar.gz)")
        with tarfile.open(archive) as tar:
            pairs = compare_pairs(lambda n: tar.extractfile(f"study_a/primary/{n}").read())
    else:
        pairs = compare_pairs(lambda n: (records / n).read_bytes())
    n = sum(p["records"]["cases"] for p in pairs)
    same = all(not p["records"]["non_identifier_fields_differing"] for p in pairs)
    phases = Counter()
    for p in pairs:
        for t in p["traces"].values():
            phases.update(t["controller_estimate_differs_by_phase"])
    return {"schema": 1, "source": f"study_a/primary of the v5.0.0 raw-study-a.tar.gz (sha256 {ARCHIVE_SHA})",
            "status": "Descriptive comparison of executed Study A runs, added after v5.0.0.",
            "paired_episodes": n, "all_record_fields_identical_except_identifiers": same,
            "identifier_fields": sorted(IDENTIFIERS),
            "trace_samples_compared": sum(t["samples"] for p in pairs for t in p["traces"].values()),
            "trace_estimate_differences_by_phase": dict(sorted(phases.items())),
            "trace_executed_command_differences": sum(t["executed_command_p_exec_differs"] for p in pairs
                                                      for t in p["traces"].values()),
            "trace_fields_outside_estimator_differing": sorted({f for p in pairs for t in p["traces"].values()
                                                                 for f in t["fields_outside_estimator"]}),
            "pairs": pairs}


def markdown(res: dict) -> str:
    L = ["# V5 Study A - EMA alpha 1.0 vs 0.2, field by field", "",
         f"Paired episodes compared: {res['paired_episodes']:,}. All record fields identical except identifiers "
         f"({', '.join(res['identifier_fields'])}): **{'yes' if res['all_record_fields_identical_except_identifiers'] else 'no'}**.",
         "", "| Pair (alpha 1.0 vs 0.2) | Cases | Identical terminal outcomes | Non-identifier record fields that differ |",
         "|---|---:|---:|---|"]
    for p in res["pairs"]:
        r = p["records"]
        L.append(f"| `{p['alpha_1p0']}` vs `{p['alpha_0p2']}` | {r['cases']:,} | {r['identical_terminal_outcomes']:,} | "
                 f"{', '.join(r['non_identifier_fields_differing']) or 'none'} |")
    L += ["", f"Traces ({res['trace_samples_compared']} samples): the controller's object estimate differs in "
          + ", ".join(f"{v} samples {k.replace('_', ' ')}" for k, v in res["trace_estimate_differences_by_phase"].items())
          + f"; executed receiver command differs in {res['trace_executed_command_differences']} samples; other "
          f"differing fields: {', '.join(res['trace_fields_outside_estimator_differing']) or 'none'}.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--archive", type=Path, help="raw-study-a.tar.gz (checksum verified)")
    g.add_argument("--records", type=Path, help="an extracted study_a/primary directory")
    ap.add_argument("--out", type=Path, default=ROOT / "results/v5/calibration/ema_identity")
    a = ap.parse_args()
    res = analyse(a.archive, a.records)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    (a.out / "summary.md").write_text(markdown(res))
    print(markdown(res))


if __name__ == "__main__":
    main()
