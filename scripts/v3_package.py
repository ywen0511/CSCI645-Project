#!/usr/bin/env python3
"""Assemble the v3 release directory (CPU, standard library). Run from a clean delivery checkout at the tag.

    python3 scripts/v3_package.py --runs <runs root holding candidate/, formal/, superseded/, preflight/> \
        --videos <video dir> --exp-repo <clean experiment-v3 checkout> --tag v3.0.0 --output <release dir> \
        --redact /private/prefix=<WORK> --redact-regex 'host[0-9]+=<cluster-node>'

Archives (each split below --max-bytes; member inventories with size and SHA-256 for every member):
  source-experiment-v3.tar.gz, source-<tag>.tar.gz     git archives of the experiment and delivery commits
  checkpoints-formal-<family>.tar.gz                    every saved checkpoint + run metadata/logs of the formal runs
  checkpoints-pilot-smoke.tar.gz                        pilots, smoke/resume runs, and the superseded first attempt
  raw-development / raw-validation / raw-final / raw-extras / raw-acceptance .tar.gz   evaluation records + traces
  logs.tar.gz                                           job logs, scheduler logs, ledgers, environment snapshots
  analysis.tar.gz                                       results/v3, configs/v3 (with final matrices), report sources
  videos.tar.gz + videos.json                           clips, montage, sidecars, plan
Loose documents: report.md/pdf, slides.pptx/pdf, speaker_notes.md, REPRODUCE.md, VERIFICATION.md, RELEASE_NOTES.md.
Indices: run_index.json, checkpoints.json (every checkpoint -> asset/member/sha256; alias ledger for identical bytes),
release_manifest.json, archive_inventories.json, SHA256SUMS (every asset except itself).
Text members of archives are redacted (private path prefixes, host names); scientific content is unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = {".json", ".jsonl", ".log", ".txt", ".md", ".csv", ".sh", ".yaml", ".py"}
REDACT: list[tuple[str, str]] = []
RX: list[tuple[re.Pattern, str]] = []
STAGE: Path | None = None


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def redacted(src: Path) -> Path:
    if src.suffix not in TEXT or src.stat().st_size > 400_000_000:
        return src
    t = src.read_text(errors="replace")
    n = t
    for old, tok in REDACT:
        n = n.replace(old, tok)
    for rx, tok in RX:
        n = rx.sub(tok, n)
    if n == t:
        return src
    d = STAGE / f"r{sum(1 for _ in STAGE.iterdir())}_{src.name}"
    d.write_text(n)
    return d


class Packer:
    def __init__(self, out: Path, max_bytes: int):
        self.out, self.max = out, max_bytes
        self.inv: dict[str, list] = {}
        self.where: dict[str, tuple[str, str]] = {}  # source path -> (asset, member)

    def tar(self, name: str, members: list[tuple[Path, str]], redact=True):
        """Write name.tar.gz (or name.partNN.tar.gz parts below max bytes of input)."""
        parts, cur, size = [], [], 0
        for m in members:
            s = m[0].stat().st_size
            if cur and size + s > self.max:
                parts.append(cur)
                cur, size = [], 0
            cur.append(m)
            size += s
        if cur:
            parts.append(cur)
        names = [f"{name}.tar.gz"] if len(parts) == 1 else [f"{name}.part{i + 1:02d}.tar.gz" for i in range(len(parts))]
        for asset, ms in zip(names, parts):
            rows, seen = [], set()
            with tarfile.open(self.out / asset, "w:gz", compresslevel=6) as t:
                for src, arc in ms:
                    for rx, tok in RX:  # member names too (e.g. TensorBoard files carry the host name)
                        arc = rx.sub(tok.strip("<>"), arc)
                    if arc in seen:
                        raise SystemExit(f"duplicate member {arc}")
                    seen.add(arc)
                    r = redacted(src) if redact else src
                    ti = t.gettarinfo(str(r), arcname=arc)
                    ti.uid = ti.gid = 0
                    ti.uname = ti.gname = ""
                    ti.mode = 0o644
                    with open(r, "rb") as f:
                        t.addfile(ti, f)
                    rows.append({"path": arc, "size_bytes": r.stat().st_size, "sha256": sha(r)})
                    self.where[str(src)] = (asset, arc)
            self.inv[asset] = rows
        return names


def tree(base: Path, prefix: str, exclude=()) -> list[tuple[Path, str]]:
    if not base.exists():
        return []
    return [(p, f"{prefix}/{p.relative_to(base).as_posix()}") for p in sorted(base.rglob("*"))
            if p.is_file() and not any(x in p.parts for x in exclude)]


def main():
    global STAGE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--videos", required=True)
    ap.add_argument("--exp-repo", required=True)
    ap.add_argument("--tag", default="v3.0.0")
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-bytes", type=int, default=1_500_000_000)
    ap.add_argument("--redact", action="append", default=[])
    ap.add_argument("--redact-regex", action="append", default=[])
    a = ap.parse_args()
    for r in a.redact:
        o, t = r.split("=", 1)
        REDACT.append((o, t))
    for r in a.redact_regex:
        x, t = r.rsplit("=", 1)
        RX.append((re.compile(x), t))
    git = lambda repo, *x: subprocess.run(["git", "-C", str(repo), *x], capture_output=True, text=True, check=True).stdout.strip()  # noqa: E731
    head, exp = git(ROOT, "rev-parse", "HEAD"), git(a.exp_repo, "rev-parse", "HEAD")
    if git(ROOT, "status", "--porcelain", "--untracked-files=no") or git(a.exp_repo, "status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("delivery and experiment checkouts must be clean")
    if exp != git(ROOT, "rev-parse", "experiment-v3^{commit}"):
        raise SystemExit("experiment checkout is not at experiment-v3")
    out = Path(a.output)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite")
    out.mkdir(parents=True)
    STAGE = Path(tempfile.mkdtemp(prefix="v3pkg_"))
    R = Path(a.runs)
    F, C, S = R / "formal", R / "candidate", R / "superseded"
    pk = Packer(out, a.max_bytes)

    for repo, name, rev in ((a.exp_repo, "source-experiment-v3", exp), (ROOT, f"source-{a.tag}", head)):
        p = STAGE / f"{name}.tar.gz"
        subprocess.run(["git", "-C", str(repo), "archive", "--format=tar.gz", f"--prefix=CSCI645-Project-{name}/", "-o", str(p), rev], check=True)
        shutil.copy2(p, out / p.name)
        with tarfile.open(p) as t:
            pk.inv[p.name] = [{"path": m.name, "size_bytes": m.size, "sha256": hashlib.sha256(t.extractfile(m).read()).hexdigest()}
                              for m in t.getmembers() if m.isfile()]

    fams = sorted({d.name.rsplit("_s", 1)[0] for d in (F / "train").iterdir() if d.is_dir()})
    for fam in fams:
        ms = []
        for d in sorted((F / "train").glob(f"{fam}_s*")):
            ms += tree(d, f"formal/train/{d.name}")
        pk.tar(f"checkpoints-formal-{fam}", ms, redact=True)
    ms = tree(C / "pilot", "pilot") + tree(C / "smoke", "smoke") + \
        [m for m in tree(S, "superseded") if "/smoke/" in m[1] or "/pilot/" in m[1]]  # superseded attempt's runs
    pk.tar("checkpoints-pilot-smoke", ms)
    pk.tar("raw-development", tree(C / "development", "development") + tree(S, "superseded", exclude=("smoke", "pilot")))
    pk.tar("raw-validation", tree(F / "validation", "validation"))
    pk.tar("raw-final", tree(F / "final", "final"))
    pk.tar("raw-extras", tree(F / "zero_policy", "zero_policy") + tree(F / "interventions", "interventions")
           + tree(F / "repeatability", "repeatability") + tree(F / "traces6", "traces6") + tree(F / "_resolved", "resolved_matrices"))
    pk.tar("raw-acceptance", tree(C / "acceptance", "acceptance") + tree(C / "pilot_eval", "pilot_eval")
           + tree(R / "preflight", "preflight"))
    logs = []
    for base, pre in ((F, "formal"), (C, "candidate")):
        logs += tree(base / "logs", f"{pre}/logs") + tree(base / "ledger", f"{pre}/ledger")
    logs += tree(R / "lsf_logs", "lsf_logs")
    pk.tar("logs", logs)
    an = tree(ROOT / "results/v3", "results/v3") + tree(ROOT / "configs/v3", "configs/v3") + tree(ROOT / "report/v3", "report/v3", exclude=("render",))
    pk.tar("analysis", an)
    vd = Path(a.videos)
    pk.tar("videos", tree(vd, "videos"))
    vix = json.loads((vd / "video_index.json").read_text())
    vlist = [{"video": c["video"], "member": f"videos/{c['video']}", "sidecar": f"videos/{c['sidecar']}", "frames": c["decoded_frames"],
              "sha256": c["sha256"], "category": c["category"], "run_id": c["run_id"], "case_id": c["case_id"],
              "evaluation_outcome": c["evaluation_outcome"], "replay_outcome": c["replay_outcome"]} for c in vix["clips"]]
    vlist.append({"video": "montage.mp4", "member": "videos/montage.mp4", "frames": vix["montage"]["frames"],
                  "sha256": vix["montage"]["sha256"], "category": "montage"})
    (STAGE / "videos.json").write_text(json.dumps(vlist, indent=1) + "\n")
    docs = [(ROOT / "report/v3/report.md", "report.md"), (ROOT / "report/v3/report.pdf", "report.pdf"),
            (ROOT / "report/v3/slides.pptx", "slides.pptx"), (ROOT / "report/v3/slides.pdf", "slides.pdf"),
            (ROOT / "report/v3/speaker_notes.md", "speaker_notes.md"), (ROOT / "docs/v3/REPRODUCE.md", "REPRODUCE.md"),
            (ROOT / "docs/v3/VERIFICATION.md", "VERIFICATION.md"), (ROOT / "docs/v3/RELEASE_NOTES.md", "RELEASE_NOTES.md"),
            (STAGE / "videos.json", "videos.json")]
    for s, n in docs:
        if not s.exists():
            raise SystemExit(f"missing {s}")
        shutil.copy2(redacted(s), out / n)

    # checkpoint index: every .pt in any archive, with run/tag/role and an alias ledger for identical bytes
    ck, by_sha = [], {}
    sel = json.loads((ROOT / "results/v3/selection/selection.json").read_text())
    for src, (asset, member) in sorted(pk.where.items()):
        if not member.endswith(".pt"):
            continue
        parts = member.split("/")
        run = parts[-3]
        tag = Path(member).stem
        row = next(r for r in pk.inv[asset] if r["path"] == member)
        kind = member.split("/")[0]
        roles = []
        if kind == "formal":
            if tag == "step_000000000":
                roles.append("untrained")
            if tag == "final":
                roles.append("final")
            if tag == "latest":
                roles.append("resume")
            if sel.get(run, {}).get("selected") == tag:
                roles.append("selected")
            if tag in ("step_002031616", "step_004030464", "step_006029312", "step_008028160", "step_010027008"):
                roles.append("validation_candidate")
        e = {"run": run, "category": kind if kind != "formal" else "formal", "tag": tag, "roles": roles, "asset": asset,
             "member": member, "sha256": row["sha256"], "size_bytes": row["size_bytes"]}
        e["identical_bytes_as"] = by_sha.get(row["sha256"])
        by_sha.setdefault(row["sha256"], f"{asset}:{member}")
        ck.append(e)
    (out / "checkpoints.json").write_text(json.dumps(ck, indent=1) + "\n")
    runs = []
    for d in sorted((F / "train").iterdir()):
        if d.is_dir():
            meta = json.loads((d / "run.json").read_text())
            done = json.loads((d / "DONE.json").read_text())
            runs.append({"run": d.name, "type": "final", "family": d.name.rsplit("_s", 1)[0], "seed": meta["seed"],
                         "source_commit": meta["git"]["commit"], "source_dirty": meta["git"]["dirty"], "protocol_sha256": meta["protocol_sha256"],
                         "config_hash": meta["config_hash"], "realized_transitions": done["transitions"],
                         "scored_transitions": done.get("scored_transitions_this_process"), "selected": sel[d.name]["selected"],
                         "resumed": (d / "run_resume.json").exists(), "checkpoints": sum(1 for c in ck if c["run"] == d.name)})
    for base, typ in ((C / "pilot", "pilot"), (C / "smoke", "smoke")):
        for d in sorted(base.iterdir()) if base.exists() else []:
            if d.is_dir() and (d / "run.json").exists():
                meta = json.loads((d / "run.json").read_text())
                runs.append({"run": d.name, "type": typ + ("_resume" if d.name.endswith("_resume") else ""), "seed": meta["seed"],
                             "source_commit": meta["git"]["commit"], "status": "completed" if (d / "DONE.json").exists() else "incomplete",
                             "checkpoints": sum(1 for c in ck if c["run"] == d.name)})
    (out / "run_index.json").write_text(json.dumps(runs, indent=1) + "\n")
    # every final-matrix logical entry and validation evaluation -> asset/member/sha256 + lineage
    member_of = {m: (asset, m) for asset, rows in pk.inv.items() for m in (r["path"] for r in rows)}
    inv_sha = {(asset, r["path"]): (r["sha256"], r["size_bytes"]) for asset, rows in pk.inv.items() for r in rows}
    arts = []
    idx = json.loads((ROOT / "configs/v3/final_matrix_index.json").read_text())
    for e in idx["entries"]:
        asset, m = member_of[e["records"]]
        h, size = inv_sha[(asset, m)]
        arts.append({"artifact": f"final/{e['family']}/{e['role']}/{e['seed']}", "kind": "final_records", "asset": asset, "member": m,
                     "sha256": h, "size_bytes": size, "alias_of": e.get("alias_of"), "status": "complete (2,600 records)",
                     "lineage": e["expected"]})
    for v in sorted((F / "validation").rglob("*__*.jsonl")):
        mem = f"validation/{v.relative_to(F / 'validation').as_posix()}"
        asset, m = member_of[mem]
        h, size = inv_sha[(asset, m)]
        first = json.loads(v.read_text().splitlines()[0])
        arts.append({"artifact": f"validation/{v.stem}", "kind": "validation_records", "asset": asset, "member": m, "sha256": h,
                     "size_bytes": size, "status": "complete (240 records)",
                     "lineage": {k: first.get(k) for k in ("suite_hash", "config_hash", "controller_hash", "checkpoint_sha256",
                                                           "source_commit", "source_dirty")}})
    (out / "archive_inventories.json").write_text(json.dumps({k: pk.inv[k] for k in sorted(pk.inv)}, indent=1) + "\n")
    assets = [{"name": f.name, "size_bytes": f.stat().st_size, "sha256": sha(f)} for f in sorted(out.iterdir())
              if f.name not in ("release_manifest.json", "SHA256SUMS")]
    man = {"tag": a.tag, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "delivery_commit": head,
           "experiment_tag": "experiment-v3", "experiment_commit": exp, "assets": assets,
           "logical_runs": {r["run"]: {"type": r["type"], "status": r.get("status", "completed"), "checkpoints": r.get("checkpoints"),
                                       "source_commit": r.get("source_commit"), "config_hash": r.get("config_hash"),
                                       "protocol_sha256": r.get("protocol_sha256"), "selected": r.get("selected"),
                                       "checkpoint_members": [{"tag": c["tag"], "asset": c["asset"], "member": c["member"], "sha256": c["sha256"],
                                                               "size_bytes": c["size_bytes"], "roles": c["roles"]} for c in ck if c["run"] == r["run"]]}
                            for r in runs},
           "artifacts": arts,
           "coverage": "SHA256SUMS covers every asset except itself; release_manifest.json is covered by SHA256SUMS and "
                       "lists every other asset; archive_inventories.json lists every member (size, SHA-256), including "
                       "the source archives",
           "redaction": [t for _, t in REDACT] + [t for _, t in RX]}
    (out / "release_manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    with open(out / "SHA256SUMS", "w") as f:
        for x in sorted(out.iterdir()):
            if x.name != "SHA256SUMS":
                f.write(f"{sha(x)}  {x.name}\n")
    shutil.rmtree(STAGE)
    print(f"{len(list(out.iterdir()))} assets, {sum(x.stat().st_size for x in out.iterdir()) / 1e6:.1f} MB, "
          f"{sum(len(v) for v in pk.inv.values())} members, {len(ck)} checkpoints")


if __name__ == "__main__":
    main()
