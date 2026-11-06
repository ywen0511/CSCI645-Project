#!/usr/bin/env python3
"""Verify a downloaded (or locally packaged) v2 release bundle (CPU only, standard library).

    python3 scripts/verify_v2_release.py --bundle downloads/v2 [--extracted downloads/v2/x]

Checks: SHA256SUMS against every file; manifest sizes and hashes; every archive member against
archive_inventories.json (re-hashed); every checkpoint/video index entry resolves to an inventoried member
with the indexed hash; every expected final run (3 methods x 3 seeds) has step 0, all periodic checkpoints,
the selected, final and latest checkpoints; the final-evaluation raw records reconcile with the evaluation
manifest (all expected entries, all cases, no duplicates). Prints a JSON summary; exit code 1 on any problem.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", required=True)
    a = ap.parse_args()
    B = Path(a.bundle)
    probs, out = [], {}
    sums = {}
    for line in (B / "SHA256SUMS").read_text().splitlines():
        h, name = line.split(maxsplit=1)
        sums[name] = h
        if not (B / name).exists():
            probs.append(f"missing {name}")
        elif sha_file(B / name) != h:
            probs.append(f"sha mismatch {name}")
    out["sha256sums_checked"] = len(sums)
    man = json.loads((B / "manifest.json").read_text())
    for asset in man["assets"]:
        p = B / asset["name"]
        if not p.exists() or p.stat().st_size != asset["size_bytes"] or sha_file(p) != asset["sha256"]:
            probs.append(f"manifest mismatch {asset['name']}")
    out["manifest_assets"] = len(man["assets"])
    inv = json.loads((B / "archive_inventories.json").read_text())
    members = {}
    n = 0
    finals = {}
    for arch, rows in inv.items():
        want = {r["path"]: r for r in rows}
        seen = set()
        with tarfile.open(B / arch, "r:gz") as tf:
            for ti in tf:
                if not ti.isfile():
                    continue
                data = tf.extractfile(ti).read()
                r = want.get(ti.name)
                if r is None:
                    probs.append(f"unlisted {arch}:{ti.name}")
                    continue
                if sha_bytes(data) != r["sha256"] or len(data) != r["size_bytes"]:
                    probs.append(f"member mismatch {arch}:{ti.name}")
                seen.add(ti.name)
                members[(arch, ti.name)] = r["sha256"]
                n += 1
                if arch == "raw-final-eval.tar.gz" and ti.name.endswith(".jsonl") and not ti.name.endswith("eval_runs.jsonl"):
                    finals[Path(ti.name).stem] = [json.loads(x) for x in io.BytesIO(data).read().decode().splitlines() if x.strip()]
                if arch == "raw-final-eval.tar.gz" and ti.name.endswith("final_manifest.json"):
                    out["_final_manifest"] = json.loads(data)
        for p in set(want) - seen:
            probs.append(f"missing member {arch}:{p}")
    out["archive_members_checked"] = n
    ck = json.loads((B / "checkpoints.json").read_text())
    out["checkpoint_index_superseded"] = sum(1 for e in ck if e.get("superseded"))
    for e in ck:
        if e.get("superseded"):
            continue
        key = (e["asset"], e["member"])
        if key not in members:
            probs.append(f"checkpoint index entry unresolved: {key}")
        elif members[key] != e.get("sha256", e.get("ledger_sha256")):
            probs.append(f"checkpoint hash mismatch: {key}")
    out["checkpoint_index_entries"] = len(ck)
    roles = {}
    for e in ck:
        if e.get("role"):
            roles.setdefault(e["run_id"], set()).add(e["role"])
    for m in ("residual", "combined", "combined_no_phase"):
        for s in (11, 22, 33):
            rid = f"{m}_seed{s}"
            if roles.get(rid) != {"untrained", "selected", "final", "resume"}:
                probs.append(f"{rid}: roles {roles.get(rid)}")
            steps = sorted(e["transitions"] for e in ck if e["run_id"] == rid and e.get("tag", "").startswith("step_"))
            if len(steps) < 11 or steps[0] != 0:
                probs.append(f"{rid}: periodic checkpoints {steps}")
    vids = json.loads((B / "videos.json").read_text())
    for v in vids:
        key = ("videos.tar.gz", v["member"])
        if members.get(key) != v["sha256"]:
            probs.append(f"video unresolved/mismatch {v['video']}")
        if not v.get("replay_matches_evaluation"):
            probs.append(f"video replay disagrees: {v['video']}")
    out["videos"] = len(vids)
    fm = out.pop("_final_manifest", None)
    if fm is None:
        probs.append("final_manifest.json not found in raw-final-eval")
    else:
        recorded = 0
        for eid, nexp in fm["expected_episodes"].items():
            rows = finals.get(eid)
            if rows is None:
                probs.append(f"final records missing for {eid}")
                continue
            ids = [r["case_id"] for r in rows]
            recorded += len(rows)
            if len(rows) != nexp or len(set(ids)) != len(ids):
                probs.append(f"{eid}: {len(rows)} records / {len(set(ids))} unique, expected {nexp}")
        out["final_expected"] = fm["expected_total"]
        out["final_recorded"] = recorded
    runs = json.loads((B / "runs.json").read_text())
    out["runs"] = {"final": sum(r["run_type"] == "final" for r in runs), "pilot_or_smoke": sum(r["run_type"] != "final" for r in runs)}
    out["problems"] = probs
    out["ok"] = not probs
    print(json.dumps(out, indent=1))
    sys.exit(0 if not probs else 1)


if __name__ == "__main__":
    main()
