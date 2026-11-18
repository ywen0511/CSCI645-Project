#!/usr/bin/env python3
"""Assemble the V5 release directory (CPU, standard library). Run from a clean delivery checkout at the tag.

    python3 scripts/v5_package.py --runs <v5 runs root: formal/, calibration/, probe/, slip_dev_r*/, pilot_r*/, lsf_logs/> \
        --exp-a <clean experiment-v5a checkout> --exp-b <clean experiment-v5b checkout> --tag v5.0.0 \
        --output <release dir> --redact /private/prefix=<WORK> --redact-regex 'host[0-9]+=<cluster-node>'

Archives (each split below --max-bytes; member inventories with size and SHA-256 for every member):
  source-experiment-v5a / source-experiment-v5b / source-<tag> .tar.gz   git archives of the three commits
  checkpoints-formal-<profile>.tar.gz     every saved checkpoint + run metadata/logs of the 15 formal runs
  checkpoints-pilot.tar.gz                pilots (round 1 on the superseded slide distribution, round 2)
  raw-study-a.tar.gz                      Study A primary + repeat records and traces
  raw-development.tar.gz                  slip feasibility probe (rounds 1-2) and development rounds 1-2
  raw-validation / raw-final / raw-extras .tar.gz   formal records (extras: repeatability, V4 regression,
                                          mechanisms incl. development fits, resolved matrices)
  logs.tar.gz                             job/scheduler logs, ledgers, runner logs
  analysis.tar.gz                         results/v5, configs/v5, report/v5
  videos.tar.gz + videos.json             clips, montage, sidecars
Loose documents: report.md/pdf, slides.pptx/pdf, speaker_notes.md, REPRODUCE.md, VERIFICATION.md, RELEASE_NOTES.md.
Indices: run_index.json, checkpoints.json (every checkpoint -> run, profile, seed, transitions, roles, source commit,
config hash, SHA-256, asset, member; alias ledger for identical bytes), release_manifest.json,
archive_inventories.json, SHA256SUMS (every asset except itself). Text members are redacted (private path prefixes,
host names); scientific content is unchanged.
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


CANDIDATES = {"step_001015808", "step_002031616", "step_003014656", "step_004030464", "step_005013504", "step_006029312",
              "step_007012352", "step_008028160", "step_009011200", "step_010027008"}


def main():
    global STAGE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--exp-a", required=True)
    ap.add_argument("--exp-b", required=True)
    ap.add_argument("--tag", default="v5.0.0")
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
    head = git(ROOT, "rev-parse", "HEAD")
    ea, eb = git(a.exp_a, "rev-parse", "HEAD"), git(a.exp_b, "rev-parse", "HEAD")
    for repo in (ROOT, a.exp_a, a.exp_b):
        if git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise SystemExit(f"{repo}: checkout must be clean")
    if ea != git(ROOT, "rev-parse", "experiment-v5a^{commit}") or eb != git(ROOT, "rev-parse", "experiment-v5b^{commit}"):
        raise SystemExit("experiment checkouts are not at experiment-v5a / experiment-v5b")
    out = Path(a.output)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite")
    out.mkdir(parents=True)
    STAGE = Path(tempfile.mkdtemp(prefix="v5pkg_"))
    R = Path(a.runs)
    F = R / "formal"
    pk = Packer(out, a.max_bytes)
    for repo, name, rev in ((a.exp_a, "source-experiment-v5a", ea), (a.exp_b, "source-experiment-v5b", eb),
                            (ROOT, f"source-{a.tag}", head)):
        p = STAGE / f"{name}.tar.gz"
        subprocess.run(["git", "-C", str(repo), "archive", "--format=tar.gz", f"--prefix=CSCI645-Project-{name}/", "-o", str(p), rev], check=True)
        shutil.copy2(p, out / p.name)
        with tarfile.open(p) as t:
            pk.inv[p.name] = [{"path": m.name, "size_bytes": m.size, "sha256": hashlib.sha256(t.extractfile(m).read()).hexdigest()}
                              for m in t.getmembers() if m.isfile()]
    profiles = sorted({d.name.rsplit("_s", 1)[0] for d in (F / "train").iterdir() if d.is_dir()})
    for prof in profiles:
        ms = []
        for d in sorted((F / "train").glob(f"{prof}_s*")):
            ms += tree(d, f"formal/train/{d.name}")
        pk.tar(f"checkpoints-formal-{prof}", ms)
    pk.tar("checkpoints-pilot", tree(R / "pilot_r1", "pilot_r1") + tree(R / "pilot_r2", "pilot_r2"))
    pk.tar("raw-study-a", tree(R / "calibration", "study_a"))
    pk.tar("raw-development", tree(R / "probe", "development/probe") + tree(R / "slip_dev_r1", "development/round1")
           + tree(R / "slip_dev_r2", "development/round2"))
    pk.tar("raw-validation", tree(F / "validation", "validation"))
    pk.tar("raw-final", tree(F / "final", "final"))
    pk.tar("raw-extras", tree(F / "repeat", "repeat") + tree(F / "regression", "regression")
           + tree(F / "mechanisms", "mechanisms") + tree(F / "_resolved", "resolved_matrices"))
    logs = []
    for sub in ("logs", "ledger", "runner_logs"):
        logs += tree(F / sub, f"formal/{sub}")
    logs += tree(R / "lsf_logs", "lsf_logs")
    pk.tar("logs", logs)
    pk.tar("analysis", tree(ROOT / "results/v5", "results/v5") + tree(ROOT / "configs/v5", "configs/v5")
           + tree(ROOT / "report/v5", "report/v5", exclude=("render",)))
    vd = F / "videos"
    pk.tar("videos", tree(vd, "videos"))
    vix = json.loads((vd / "videos.json").read_text())
    vlist = [{"video": c["video"], "member": f"videos/{c['video']}", "sidecar": f"videos/{c['sidecar']}", "frames": c["decoded_frames"],
              "sha256": c["sha256"], "category": c["category"], "method": c["method"], "run_id": c["run_id"],
              "case_id": c["case_id"], "checkpoint": c["checkpoint"], "checkpoint_sha256": c["checkpoint_sha256"],
              "evaluation_outcome": c["evaluation_outcome"], "replay_outcome": c["replay_outcome"],
              "replay_matches_evaluation": c["replay_matches_evaluation"], "source_commit": c["source_commit"]}
             for c in vix["clips"]]
    vlist.append({"video": "montage.mp4", "member": "videos/montage.mp4", "frames": vix["montage"]["frames"],
                  "sha256": vix["montage"]["sha256"], "category": "montage"})
    (STAGE / "videos.json").write_text(json.dumps(vlist, indent=1) + "\n")
    docs = [(ROOT / "report/v5/report.md", "report.md"), (ROOT / "report/v5/report.pdf", "report.pdf"),
            (ROOT / "report/v5/slides.pptx", "slides.pptx"), (ROOT / "report/v5/slides.pdf", "slides.pdf"),
            (ROOT / "report/v5/speaker_notes.md", "speaker_notes.md"), (ROOT / "docs/v5/REPRODUCE.md", "REPRODUCE.md"),
            (ROOT / "docs/v5/VERIFICATION.md", "VERIFICATION.md"), (ROOT / "docs/v5/RELEASE_NOTES.md", "RELEASE_NOTES.md"),
            (STAGE / "videos.json", "videos.json")]
    for s, n in docs:
        if not s.exists():
            raise SystemExit(f"missing {s}")
        shutil.copy2(redacted(s), out / n)

    ck, by_sha, ck_info = [], {}, {}
    for led in R.rglob("checkpoints.jsonl"):
        rj = led.parent / "run.json"
        meta = json.loads(rj.read_text()) if rj.exists() else {}
        rows = [json.loads(x) for x in led.read_text().splitlines() if x.strip()]
        for row in rows:
            ck_info[str(led.parent / row["path"])] = {"seed": meta.get("seed"), "transitions": row["transitions"],
                                                      "source_commit": (meta.get("git") or {}).get("commit"),
                                                      "config_hash": meta.get("config_hash"), "protocol": meta.get("protocol")}
        lt = led.parent / "checkpoints" / "latest.pt"
        if lt.exists() and rows:
            ck_info[str(lt)] = {**ck_info.get(str(led.parent / rows[-1]["path"]), {}), "transitions": rows[-1]["transitions"]}
    sel = json.loads((ROOT / "results/v5/slip/selection/selection.json").read_text())
    for src, (asset, member) in sorted(pk.where.items()):
        if not member.endswith(".pt"):
            continue
        run, tag = member.split("/")[-3], Path(member).stem
        row = next(r for r in pk.inv[asset] if r["path"] == member)
        kind = member.split("/")[0]
        roles = []
        if kind == "formal":
            roles += ["untrained"] if tag == "step_000000000" else []
            roles += ["final"] if tag == "final" else []
            roles += ["resume"] if tag == "latest" else []
            roles += ["selected"] if sel.get(run, {}).get("selected") == tag else []
            roles += ["validation_candidate"] if tag in CANDIDATES else []
        else:
            roles.append("pilot")
        info = ck_info.get(src, {})
        e = {"run": run, "category": kind, "tag": tag, "roles": roles, "asset": asset, "member": member,
             "sha256": row["sha256"], "size_bytes": row["size_bytes"], "profile": run.rsplit("_s", 1)[0],
             "seed": info.get("seed"), "transitions": info.get("transitions"), "source_commit": info.get("source_commit"),
             "config_hash": info.get("config_hash"), "protocol": info.get("protocol")}
        e["identical_bytes_as"] = by_sha.get(row["sha256"])
        by_sha.setdefault(row["sha256"], f"{asset}:{member}")
        ck.append(e)
    (out / "checkpoints.json").write_text(json.dumps(ck, indent=1) + "\n")
    runs = []
    for d in sorted((F / "train").iterdir()):
        if d.is_dir():
            meta = json.loads((d / "run.json").read_text())
            done = json.loads((d / "DONE.json").read_text())
            runs.append({"run": d.name, "type": "final", "profile": d.name.rsplit("_s", 1)[0], "seed": meta["seed"],
                         "source_commit": meta["git"]["commit"], "source_dirty": meta["git"]["dirty"],
                         "protocol": meta["protocol"], "protocol_sha256": meta["protocol_sha256"], "config_hash": meta["config_hash"],
                         "realized_transitions": done["transitions"], "scored_transitions": done.get("scored_transitions_this_process"),
                         "selected": sel[d.name]["selected"], "resumed": (d / "run_resume.json").exists(),
                         "checkpoints": sum(1 for c in ck if c["run"] == d.name and c["category"] == "formal")})
    for base, typ in ((R / "pilot_r1", "pilot_r1_superseded_distribution"), (R / "pilot_r2", "pilot_r2")):
        for d in sorted(base.iterdir()) if base.exists() else []:
            if d.is_dir() and (d / "run.json").exists():
                meta = json.loads((d / "run.json").read_text())
                runs.append({"run": f"{base.name}/{d.name}", "type": typ, "seed": meta["seed"], "source_commit": meta["git"]["commit"],
                             "protocol": meta["protocol"], "config_hash": meta["config_hash"],
                             "status": "completed" if (d / "DONE.json").exists() else "incomplete",
                             "checkpoints": sum(1 for c in ck if c["member"].startswith(f"{base.name}/{d.name}/"))})
    (out / "run_index.json").write_text(json.dumps(runs, indent=1) + "\n")
    (out / "archive_inventories.json").write_text(json.dumps({k: pk.inv[k] for k in sorted(pk.inv)}, indent=1) + "\n")
    assets = [{"name": f.name, "size_bytes": f.stat().st_size, "sha256": sha(f)} for f in sorted(out.iterdir())
              if f.name not in ("release_manifest.json", "SHA256SUMS")]
    man = {"tag": a.tag, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "delivery_commit": head,
           "experiment_tags": {"experiment-v5a": ea, "experiment-v5b": eb}, "assets": assets,
           "logical_runs": {r["run"]: {k: r.get(k) for k in ("type", "status", "checkpoints", "source_commit", "config_hash",
                                                             "protocol_sha256", "selected")} for r in runs},
           "coverage": "SHA256SUMS covers every asset except itself; release_manifest.json lists every other asset; "
                       "archive_inventories.json lists every member (size, SHA-256), including the source archives",
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
