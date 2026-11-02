#!/usr/bin/env python3
"""Check repository handoff integrity without Isaac Sim or third-party packages."""

import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    required = [
        "README.md", "AGENTS.md", "STATUS.json", "configs/protocol.json",
        "docs/REMOTE_AGENT_PROMPT.md", "docs/PROJECT_SPEC.md",
        "docs/IMPLEMENTATION.md", "docs/ENVIRONMENT.md", "docs/EXPERIMENTS.md",
        "docs/RUNBOOK.md", "docs/RELEASE.md", "docs/DECISIONS.md",
        "docs/REFERENCES.md", "proposal/provenance.json",
        "proposal/CSCI645_Project_Proposal_YanWen.pdf", "proposal/proposal.txt",
        "scripts/verify_release.py",
    ]
    for name in required:
        if not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0:
            errors.append(f"Missing or empty: {name}")
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        if "/Users/" in content or "/home/" in content:
            errors.append(f"Machine-specific home path in {path.relative_to(ROOT)}")
        if re.search(r"[\u3400-\u9fff]", content):
            errors.append(f"Non-English CJK content in {path.relative_to(ROOT)}")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            target = target.split(' "', 1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = (path.parent / unquote(parsed.path)).resolve()
            if not destination.exists():
                errors.append(f"Broken local link in {path.relative_to(ROOT)}: {target}")
    try:
        protocol = json.loads((ROOT / "configs/protocol.json").read_text())
        ids = [m["id"] for m in protocol["methods"]]
        expected = {"nominal", "geometry", "residual", "combined", "combined_no_phase"}
        if set(ids) != expected or len(ids) != len(expected):
            errors.append("Expected exactly five distinct methods")
        learned = [m for m in protocol["methods"] if m["learned"]]
        if len(learned) != 3 or len(set(protocol["training"]["seeds"])) != 3:
            errors.append("Expected three trained methods and three distinct seeds")
        if protocol["task"]["success_hold_s"] != 2.0:
            errors.append("Success must require two seconds of independent holding")
        if protocol["policy"]["action_dim"] != 3:
            errors.append("Initial residual action must have three position dimensions")
        conditions = protocol["evaluation"]["conditions"]
        if len({c["id"] for c in conditions}) != len(conditions):
            errors.append("Duplicate evaluation condition IDs")
        json.loads((ROOT / "STATUS.json").read_text())
        provenance = json.loads((ROOT / "proposal/provenance.json").read_text())
        for item in provenance["files"]:
            path = ROOT / "proposal" / item["name"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                errors.append(f"Proposal integrity mismatch: {item['name']}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Invalid handoff metadata: {exc}")
    if errors:
        print("Handoff validation failed:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 1
    episodes = (len(learned) * len(protocol["training"]["seeds"]) + 2) * len(conditions) * protocol["evaluation"]["episodes_per_condition"]
    print(f"Handoff checks passed. Protocol schedules {episodes:,} final evaluation episodes.")
    print("This checks documents/configuration only; no simulator or trained policy was verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
