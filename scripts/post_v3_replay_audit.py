#!/usr/bin/env python3
"""Record-level audit of the Stage A (POST_V3) GPU replay/reload outputs (CPU, standard library only).

    python3 -I scripts/post_v3_replay_audit.py --replay <R> --extracted <X> --tooling <T> --experiment-sha <sha> \
        --output <audit.json>

For every replay65/ and reload/ entry it checks, beyond the comparator's exit code:
  * the recorded case-ID set equals the expected subset suite exactly (configs/v3/suites/final_subset65.jsonl or
    final_reload13.jsonl in the tooling checkout), with no duplicate IDs;
  * every reset is valid and no record is an infrastructure error;
  * source_commit equals the immutable experiment commit and source_dirty is false;
  * suite_hash equals the SHA-256 of the subset suite file; config/controller hashes, checkpoint SHA-256,
    the entry ID (declared exact aliases resolve to the executed role, configs/v3/final_matrices/baseline_aliases.json),
    observation-error specs and terminal outcomes equal the published final records of the same entry;
  * the checkpoint SHA-256 equals the release checkpoint index (checkpoints.json) entry for that file.
Every discrepancy is listed; nothing is excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replay", required=True)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--tooling", required=True)
    ap.add_argument("--experiment-sha", required=True)
    ap.add_argument("--checkpoint-index", default=None, help="release checkpoints.json (default: <extracted>/../release)")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    R, X, T = Path(a.replay), Path(a.extracted), Path(a.tooling)
    idx = json.loads((T / "configs/v3/final_matrix_index.json").read_text())
    aliases = json.loads((T / "configs/v3/final_matrices/baseline_aliases.json").read_text())  # role -> executed role
    final_of = {(e["family"], e["role"], e["seed"]): e["records"] for e in idx["entries"]}
    ck_index_path = Path(a.checkpoint_index) if a.checkpoint_index else X.parent / "release" / "checkpoints.json"
    ck_index = json.loads(ck_index_path.read_text())
    ck_sha = {}
    for row in ck_index:  # release index rows: run, category, tag, asset, member, sha256, ...
        if row.get("category") == "formal":
            ck_sha[f"{row['run']}/checkpoints/{row['tag']}.pt"] = row["sha256"]
    suites = {"replay65": T / "configs/v3/suites/final_subset65.jsonl", "reload": T / "configs/v3/suites/final_reload13.jsonl"}
    out = {"experiment_sha": a.experiment_sha, "entries": [], "discrepancies": [],
           "checkpoint_index_entries": len(ck_sha)}

    def bad(entry, what, detail=None):
        out["discrepancies"].append({"entry": entry, "check": what, "detail": detail})

    for kind in ("replay65", "reload"):
        suite = suites[kind]
        expected_ids = [json.loads(l)["case_id"] for l in suite.read_text().splitlines() if l.strip()]
        suite_hash = sha(suite)
        for d in sorted((R / kind).iterdir()):
            files = [f for f in d.glob("*.jsonl") if f.name != "eval_runs.jsonl"]
            if len(files) != 1:
                bad(d.name, "record_file_count", len(files))
                continue
            f = files[0]
            rows = jl(f)
            entry = f.stem
            ids = [r["case_id"] for r in rows]
            if "__" in entry:
                fam, s = entry.split("__")[0].rsplit("_s", 1)
                key = (fam, "selected", int(s))
            else:
                key = (entry, "baseline", None)
            pub = {r["case_id"]: r for r in jl(X / final_of[key])}
            row = {"kind": kind, "entry": entry, "records": len(rows), "expected": len(expected_ids),
                   "unique": len(set(ids)) == len(ids), "id_set_equal": sorted(ids) == sorted(expected_ids),
                   "invalid_resets": sum(not r["reset_valid"] for r in rows),
                   "infra_errors": sum(r["terminal_reason"] == "infra_error" for r in rows),
                   "source_commit_ok": all(r["source_commit"] == a.experiment_sha and r["source_dirty"] is False for r in rows),
                   "suite_hash_ok": all(r["suite_hash"] == suite_hash for r in rows),
                   "terminal_equal": sum(r["terminal_reason"] == pub[r["case_id"]]["terminal_reason"] for r in rows if r["case_id"] in pub),
                   "success": sum(r["success"] for r in rows)}
            for field in ("config_hash", "controller_hash", "checkpoint_sha256", "observation_error"):
                row[f"{field}_equal"] = all(r.get(field) == pub.get(r["case_id"], {}).get(field) for r in rows)
            # a declared exact alias is published under the executed role's entry ID
            row["published_entry_id"] = aliases.get(entry, entry)
            row["entry_id_equal"] = all(r["entry_id"] == entry and pub.get(r["case_id"], {}).get("entry_id") == row["published_entry_id"]
                                        for r in rows)
            if rows and rows[0].get("checkpoint_sha256"):
                run = entry.split("__")[0]
                ck = rows[0]["checkpoint"]
                want = ck_sha.get(f"{run}/checkpoints/{ck}.pt")
                row["checkpoint_index_ok"] = want == rows[0]["checkpoint_sha256"]
            out["entries"].append(row)
            for k in ("unique", "id_set_equal", "source_commit_ok", "suite_hash_ok", "config_hash_equal",
                      "controller_hash_equal", "checkpoint_sha256_equal", "observation_error_equal", "entry_id_equal"):
                if not row[k]:
                    bad(entry, k)
            if row.get("checkpoint_index_ok") is False:
                bad(entry, "checkpoint_index_ok")
            if row["invalid_resets"] or row["infra_errors"]:
                bad(entry, "resets_or_infra", [row["invalid_resets"], row["infra_errors"]])
            if row["terminal_equal"] != len(rows):
                for r in rows:
                    if r["terminal_reason"] != pub[r["case_id"]]["terminal_reason"]:
                        bad(entry, "terminal_outcome", {"case": r["case_id"], "replay": r["terminal_reason"],
                                                        "published": pub[r["case_id"]]["terminal_reason"]})
    out["summary"] = {"entries": len(out["entries"]),
                      "replay65_episodes": sum(e["records"] for e in out["entries"] if e["kind"] == "replay65"),
                      "reload_episodes": sum(e["records"] for e in out["entries"] if e["kind"] == "reload"),
                      "discrepancies": len(out["discrepancies"])}
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"]))
    raise SystemExit(1 if out["discrepancies"] else 0)


if __name__ == "__main__":
    main()
