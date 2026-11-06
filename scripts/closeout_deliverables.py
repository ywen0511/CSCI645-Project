#!/usr/bin/env python3
"""Fill results/closeout/deliverables.json from a packaged release directory (CPU, standard library).

    python3 scripts/closeout_deliverables.py --release <release dir> --records <work>/records --status produced

Each deliverable is mapped to the source revision(s), the producing command (from the driver's stage
records), input hashes, and the uploaded assets/archive members with their SHA-256. --status sets the state
(produced -> uploaded -> verified); the verify step of a published download upgrades it to "verified".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAP = {
    "source_tags": {"assets": ["source-{tag}.tar.gz"], "stage": "package",
                    "revisions": ["experiment-v2", "closeout-eval-v1", "{tag}"]},
    "environment_locks": {"members": [("configs-and-docs.tar.gz", "configs/v2/frozen/pip-freeze.txt"),
                                      ("configs-and-docs.tar.gz", "configs/closeout/requirements-analysis.txt")],
                          "stage": "package"},
    "protocols_suites": {"members": [("configs-and-docs.tar.gz", "configs/v2/frozen/protocol.json"),
                                     ("configs-and-docs.tar.gz", "configs/v2/suites/final.jsonl"),
                                     ("configs-and-docs.tar.gz", "configs/closeout/repeatability.json"),
                                     ("configs-and-docs.tar.gz", "configs/closeout/verification_replay.json")],
                         "stage": "package"},
    "checkpoints_v2": {"prefix": "checkpoints-", "stage": "download_v2.0.0", "index": "checkpoints.json"},
    "raw_v2": {"assets": ["raw-final-eval.tar.gz", "raw-validation.tar.gz", "raw-development.tar.gz",
                          "raw-pilot-eval.tar.gz", "raw-audit.tar.gz", "logs.tar.gz"], "stage": "download_v2.0.0"},
    "raw_closeout": {"assets": ["closeout-repeatability.tar.gz", "closeout-negative-controls.tar.gz"],
                     "stage": "repeatability", "index": "runs.json"},
    "analysis": {"assets": ["closeout-results.tar.gz", "configs-and-docs.tar.gz"], "stage": "analyze"},
    "documents": {"assets": ["report.md", "report.pdf", "report-v1-corrected.pdf", "deck.pptx", "deck.pdf",
                             "repeatability.md", "ERRATA.md", "REPRODUCE.md", "VERIFICATION.md"], "stage": "render"},
    "videos": {"assets": ["videos.tar.gz", "videos.json"], "stage": "download_v2.0.0", "index": "videos.json"},
    "indices": {"assets": ["runs.json", "checkpoints.json", "videos.json", "manifest.json", "archive_inventories.json",
                           "SHA256SUMS"], "stage": "package"},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--release", required=True)
    ap.add_argument("--records", required=True)
    ap.add_argument("--status", default="produced", choices=["produced", "uploaded", "verified"])
    ap.add_argument("--verification", default=None, help="verify record of the published download (for 'verified')")
    a = ap.parse_args()
    rel = Path(a.release)
    man = json.loads((rel / "manifest.json").read_text())
    sums = {l.split()[1]: l.split()[0] for l in (rel / "SHA256SUMS").read_text().splitlines() if l.strip()}
    inv = json.loads((rel / "archive_inventories.json").read_text())
    recs = {p.stem: json.loads(p.read_text()) for p in Path(a.records).glob("*.json")}
    D = json.loads((ROOT / "results/closeout/deliverables.json").read_text())
    tag = man["tag"]
    for d in D["deliverables"]:
        m = MAP[d["id"]]
        outs = []
        for n in m.get("assets", []):
            n = n.format(tag=tag)
            outs.append({"asset": n, "sha256": sums.get(n) or ("(SHA256SUMS itself)" if n == "SHA256SUMS" else None)})
        if "prefix" in m:
            outs += [{"asset": n, "sha256": h} for n, h in sorted(sums.items()) if n.startswith(m["prefix"])]
        for asset, member in m.get("members", []):
            row = next((r for r in inv.get(asset, []) if r["path"] == member), None)
            outs.append({"asset": asset, "member": member, "sha256": row and row.get("sha256")})
        if any(o["sha256"] is None for o in outs):
            raise SystemExit(f"{d['id']}: unresolved output {[o for o in outs if o['sha256'] is None]}")
        stage = m["stage"]
        r = next((v for k, v in recs.items() if k.startswith(stage)), {})
        d.update({"status": a.status, "outputs": outs, "index": m.get("index"),
                  "source_revision": {"release_source_commit": man["release_source_commit"],
                                      "experiment_commit": man["experiment_commit"],
                                      "supplementary_evaluation_commit": man["supplementary_evaluation_commit"]},
                  "command": f"python3 scripts/closeout.py --work <work> {stage.split('_')[0].replace('download', 'download --tag v2.0.0')}",
                  "stage_record": f"{stage}.json in closeout records" if r else None,
                  "inputs": ([{"release": "v2.0.0", "SHA256SUMS": recs.get("download_v2.0.0", {}).get("sha256sums")}]
                             if "download_v2.0.0" in recs else [])})
        if d["id"] in ("checkpoints_v2", "raw_v2", "videos"):
            d["provenance"] = "copied unchanged from release v2.0.0 (same bytes; hashes in manifest.json copied_unchanged_from_v2.0.0)"
    D["release"] = tag
    if a.verification:
        D["verification"] = a.verification
    (ROOT / "results/closeout/deliverables.json").write_text(json.dumps(D, indent=1) + "\n")
    print(json.dumps({d["id"]: [len(d["outputs"]), d["status"]] for d in D["deliverables"]}))


if __name__ == "__main__":
    main()
