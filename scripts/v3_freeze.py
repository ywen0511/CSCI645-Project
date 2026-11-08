#!/usr/bin/env python3
"""Write configs/v3/FREEZE.json (CPU). Run on a clean checkout of the tested candidate commit.

    python3 scripts/v3_freeze.py --utc <UTC from date -u>

Records status=frozen, the tested candidate source commit (HEAD; must be clean), the GPU acceptance evidence
(results/v3/acceptance.json, which must report all_pass) and SHA-256 of every input the final study depends on:
executable source (src/**, train/eval/scripted/video scripts, suite generator), the draft design, the five frozen
training protocols, the baseline selection, development/validation suites, frozen validation matrices, the
final-condition design (v3_protocol.CONDITIONS), the selection rule (selection.py) and budgets. Afterwards
`python scripts/v3_prepare.py --final` re-checks every hash before generating the final suite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ["src/csci645_handover/**/*.py", "scripts/train.py", "scripts/eval_matrix.py", "scripts/run_scripted.py",
            "scripts/record_video.py", "scripts/v3_prepare.py", "configs/v3/protocol.draft.json",
            "configs/v3/frozen/training/*.json", "configs/v3/frozen/matrices/validation/*.json",
            "configs/v3/baseline_selection.json", "configs/v3/suites/development.jsonl", "configs/v3/suites/validation.jsonl",
            "configs/v3/SUITES.json", "configs/v2/protocol.json", "configs/v3/video_rule.json", "results/v3/acceptance.json"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--utc", required=True)
    a = ap.parse_args()
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], capture_output=True,
                           text=True).stdout.strip()
    if dirty:
        raise SystemExit("freeze requires a clean, committed candidate")
    acc = json.loads((ROOT / "results/v3/acceptance.json").read_text())
    if not acc.get("all_pass"):
        raise SystemExit("GPU acceptance has not passed; refusing to freeze")
    files = {}
    for pat in PATTERNS:
        hits = sorted(p for p in ROOT.glob(pat) if p.is_file() and "__pycache__" not in p.parts)
        if not hits:
            raise SystemExit(f"freeze input missing: {pat}")
        for p in hits:
            files[p.relative_to(ROOT).as_posix()] = sha(p)
    prots = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "configs/v3/frozen/training").glob("*.json"))}
    freeze = {
        "status": "frozen", "frozen_utc": a.utc, "source_commit": head,
        "gpu_acceptance_evidence": {"path": "results/v3/acceptance.json", "sha256": sha(ROOT / "results/v3/acceptance.json")},
        "files": files,
        "formal_runs": {k: {"method": v["training"]["methods"][0], "seeds": v["training"]["seeds"],
                            "requested_transitions": v["training"]["final_transitions_per_run"],
                            "realized_transitions": v["training"]["realized_transitions_per_run"],
                            "num_envs": v["training"]["num_envs"], "protocol_id": v["protocol_id"]} for k, v in prots.items()},
        "selection_rule": "src/csci645_handover/selection.py:select_v2 on 240 validation cases at the first saved step "
                          "at/after 2,4,6,8,10M transitions; step 0 is an untrained control and never eligible",
        "final_design": "src/csci645_handover/v3_protocol.py: 13 conditions x 200 cases, split seed 6455301; "
                        "main matrix 6 baselines + 23 runs x {selected, final} = 135,200 episodes, batch 256, one fresh "
                        "process per entry",
        "primary_contrasts": ["combined_robust_history - combined_robust_ff (selected, mixed_id)",
                              "combined_robust_history - geometry_best_constant (selected, mixed_id)"],
        "bootstrap": {"repeats": 10000, "seed": 6455401, "familywise": "Bonferroni 97.5% for the two primary contrasts"},
    }
    (ROOT / "configs/v3/FREEZE.json").write_text(json.dumps(freeze, indent=1, sort_keys=True) + "\n")
    print(f"frozen {len(files)} files at {head}")


if __name__ == "__main__":
    main()
