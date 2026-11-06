#!/usr/bin/env python3
"""Closeout driver: one entry point for the v2 delivery closeout (standard library only).

Two checkouts with fixed roles:
  * delivery-tools checkout (--tools, default: the checkout holding this file) - every analysis, verification,
    rendering and packaging script, and the closeout configs/matrices;
  * experiment checkout (--exp, default <work>/src/experiment-v2) - a clean clone at tag experiment-v2 that runs
    every simulator command. ``checkout`` creates it; simulator stages refuse a dirty or wrong checkout.

All outputs go under --work (default ./closeout_work). Every stage writes <work>/records/<stage>.json with its
commands, input/output SHA-256 and return codes; every simulator task appends attempts to
<work>/ledger/<task>.jsonl. Stages are resumable: completed work with matching hashes is skipped, a hash/config/
source mismatch is an error, and simulator tasks are retried at most --max-attempts times in total.

Stages (run in this order; ``all-cpu`` runs the CPU ones):
  checkout       clone/verify the experiment checkout at experiment-v2 (clean, exact tag)
  check          scripts exist at their revision; CLI flags in the docs exist; relative links and asset names
                 resolve; simulator source identical in both checkouts
  download       anonymous download of a release (--tag, default v2.0.0), sha256 check, member re-hash, extract
  regen          regenerate v2 summaries from downloaded raw records and compare with results/v2 (CPU)
  negative       simulator: clean nominal episode + no_receiver / giver_holds / table_support controls (GPU)
  replay         simulator: predeclared verification replay (configs/closeout/verification_replay.json) (GPU)
  repeatability  simulator: Stage 4 tasks from results/closeout/repeatability/run_manifest.json (GPU)
                 --shard I/N runs every N-th task; --throughput runs the short throughput check only
  analyze        Stage 4 analysis (scripts/closeout_repeatability.py) (CPU)
  video-replay   simulator: re-render the committed video plan (configs/closeout/video_plan.json) (GPU)
  resume-smoke   simulator: resume a downloaded latest.pt for <= 2 PPO iterations into a disposable dir (GPU)
  render         build report PDF/HTML and deck PPTX/PDF (CPU; needs Chrome/Chromium and LibreOffice)
  package        assemble the release directory (CPU)
  verify         verify a release directory or a fresh download (CPU)

Simulator stages need --isaac-python (or $CLOSEOUT_ISAAC_PYTHON): the Python of an Isaac Lab v3.0.0 /
Isaac Sim 6.2.0.0 environment built per docs/SETUP_REMOTE.md. They run through scripts/cluster/isaac_run.sh,
which only sets node-local caches and an optional user-space Vulkan ICD ($CLOSEOUT_VK_ICD_DIR).

Example (fresh machine, from the delivery-tools checkout):
    W=$PWD/closeout_work
    python3 scripts/closeout.py --work $W checkout
    python3 scripts/closeout.py --work $W download --tag v2.0.0
    python3 scripts/closeout.py --work $W check
    python3 scripts/closeout.py --work $W regen
    python3 scripts/closeout.py --work $W negative --isaac-python /path/to/isaaclab/python
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

TOOLS_DEFAULT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/ywen0511/CSCI645-Project.git"
EXPERIMENT_TAG = "experiment-v2"
EXPERIMENT_SHA = "1d9d0e23eec346c1b1cb3c0c245a1e772df7bedf"
SIM_SOURCE = ["src", "scripts/eval_matrix.py", "scripts/evaluate.py", "scripts/train.py", "scripts/run_scripted.py",
              "scripts/record_video.py"]


class StageError(SystemExit):
    pass


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_tree(root: Path, rel: list[str]) -> str:
    """Hash of file paths + bytes under the given repo-relative paths (files or directories)."""
    h = hashlib.sha256()
    files = []
    for r in rel:
        p = root / r
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files += [q for q in p.rglob("*") if q.is_file() and "__pycache__" not in q.parts]
    for q in sorted(files):
        h.update(q.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(sha_file(q).encode())
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def git_state(repo: Path) -> dict:
    try:
        head = git(repo, "rev-parse", "HEAD")
        dirty = bool(git(repo, "status", "--porcelain", "--untracked-files=no"))
        tags = git(repo, "tag", "--points-at", "HEAD").split()
        return {"commit": head, "dirty": dirty, "tags": tags}
    except Exception as e:  # not a git checkout (e.g. extracted source archive)
        return {"commit": None, "dirty": None, "tags": [], "error": str(e)}


class Ctx:
    def __init__(self, a):
        self.a = a
        self.tools = Path(a.tools).resolve()
        self.work = Path(a.work).resolve()
        self.exp = Path(a.exp).resolve() if a.exp else self.work / "src" / EXPERIMENT_TAG
        self.inputs = self.work / "inputs"
        for d in ("records", "ledger", "logs"):
            (self.work / d).mkdir(parents=True, exist_ok=True)

    def x(self, tag: str | None = None) -> Path:
        """Extracted archives of the input release (--inputs-tag). v2.1.0 contains byte-identical copies of the
        v2.0.0 checkpoint/raw archives, so either release yields the same layout."""
        return self.inputs / (tag or self.a.inputs_tag) / "x"

    def record(self, stage: str, body: dict) -> Path:
        body = {"stage": stage, "utc": utc(), "host": "<redacted>" if self.a.redact_host else socket.gethostname(),
                "tools": git_state(self.tools), "experiment": git_state(self.exp) if self.exp.exists() else None,
                **body}
        p = self.work / "records" / f"{stage}.json"
        p.write_text(json.dumps(body, indent=1) + "\n")
        print(f"[closeout] {stage}: record {p}", flush=True)
        return p

    def run(self, cmd: list[str], cwd: Path, log: Path | None = None, env: dict | None = None, check=True) -> dict:
        t0 = dt.datetime.now(dt.timezone.utc)
        print(f"[closeout] $ (cd {cwd}) {' '.join(map(str, cmd))}", flush=True)
        if log:
            log.parent.mkdir(parents=True, exist_ok=True)
            with open(log, "ab") as f:
                f.write(f"\n### {utc()} cwd={cwd}\n### {' '.join(map(str, cmd))}\n".encode())
                f.flush()
                r = subprocess.run(list(map(str, cmd)), cwd=cwd, stdout=f, stderr=subprocess.STDOUT,
                                   env={**os.environ, **(env or {})})
        else:
            r = subprocess.run(list(map(str, cmd)), cwd=cwd, env={**os.environ, **(env or {})})
        rec = {"cmd": [str(c) for c in cmd], "cwd": self.rel(cwd), "rc": r.returncode, "start": t0.isoformat(),
               "wall_s": (dt.datetime.now(dt.timezone.utc) - t0).total_seconds(),
               "log": self.rel(log) if log else None}
        if check and r.returncode != 0:
            raise StageError(f"command failed rc={r.returncode}: {' '.join(map(str, cmd))} (log: {log})")
        return rec

    def rel(self, p) -> str | None:
        if p is None:
            return None
        p = Path(p).resolve()
        for base, tag in ((self.work, "$WORK"), (self.tools, "$TOOLS"), (self.exp, "$EXP")):
            try:
                return f"{tag}/{p.relative_to(base).as_posix()}"
            except ValueError:
                pass
        return p.name

    # ---- simulator plumbing -------------------------------------------------------------------------
    def isaac(self) -> str:
        py = self.a.isaac_python or os.environ.get("CLOSEOUT_ISAAC_PYTHON")
        if not py or not Path(py).exists():
            raise StageError("simulator stage needs --isaac-python or $CLOSEOUT_ISAAC_PYTHON (Isaac Lab v3.0.0 env)")
        return py

    def require_exp(self):
        st = git_state(self.exp)
        if st["commit"] != EXPERIMENT_SHA or st["dirty"]:
            raise StageError(f"experiment checkout {self.exp} must be clean at {EXPERIMENT_TAG} ({EXPERIMENT_SHA}); "
                             f"found {st}. Run the 'checkout' stage.")
        diff = sim_source_diff(self.tools, self.exp)
        if diff:
            raise StageError(f"simulator source differs between checkouts: {diff}")
        return st

    def sim(self, py_args: list[str], log: Path) -> dict:
        cmd = ["bash", str(self.tools / "scripts/cluster/isaac_run.sh"), self.isaac(), *py_args]
        return self.run(cmd, cwd=self.exp, log=log, env={"REPO": str(self.exp)}, check=False)

    def resolved_matrix(self, rel_matrix: str, out_dir: Path, conditions: list[str] | None = None) -> Path:
        """Copy a tools-checkout matrix with suite/protocol paths made absolute (the experiment checkout lacks
        the closeout suites). The committed matrix hash is kept in the copy's '_source' field."""
        src = self.tools / rel_matrix
        mx = json.loads(src.read_text())
        for k in ("suite", "protocol"):  # keep repo-relative paths when the experiment checkout has identical bytes
            mine, theirs = self.tools / mx[k], self.exp / mx[k]
            if not (theirs.exists() and sha_file(theirs) == sha_file(mine)):
                mx[k] = str(mine)
        mx["_source"] = {"matrix": rel_matrix, "sha256": sha_file(src)}
        if conditions:  # throughput check only: restrict every entry to these conditions
            for e in mx["entries"]:
                e["conditions"] = list(conditions)
            mx["_source"]["conditions"] = list(conditions)
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / ("resolved_" + Path(rel_matrix).name)
        text = json.dumps(mx, indent=1) + "\n"
        if p.exists() and p.read_text() != text:
            raise StageError(f"{p} exists with different content (matrix changed?)")
        p.write_text(text)
        return p


def sim_source_diff(a: Path, b: Path) -> list[str]:
    out = []
    for r in SIM_SOURCE:
        if sha_tree(a, [r]) != sha_tree(b, [r]):
            out.append(r)
    return out


# ------------------------------------------------------------------------------------------------ stages
def st_checkout(c: Ctx):
    if not c.exp.exists():
        c.exp.parent.mkdir(parents=True, exist_ok=True)
        c.run(["git", "clone", "--quiet", c.a.repo_url, str(c.exp)], cwd=c.work)
        c.run(["git", "-c", "advice.detachedHead=false", "checkout", "--quiet", EXPERIMENT_TAG], cwd=c.exp)
    st = git_state(c.exp)
    if st["commit"] != EXPERIMENT_SHA:
        raise StageError(f"{c.exp} is at {st['commit']}, expected {EXPERIMENT_TAG} = {EXPERIMENT_SHA}")
    if st["dirty"]:
        raise StageError(f"{c.exp} has local modifications")
    diff = sim_source_diff(c.tools, c.exp)
    c.record("checkout", {"experiment_checkout": {"path": c.rel(c.exp), **st, "role": "simulator source"},
                          "tools_checkout": {"path": "$TOOLS", **git_state(c.tools),
                                             "role": "analysis/verification/rendering/packaging + closeout configs"},
                          "simulator_source_files": SIM_SOURCE, "simulator_source_identical": not diff,
                          "differences": diff})
    if diff:
        raise StageError(f"simulator source differs: {diff}")


REQUIRED_SCRIPTS = {
    # role -> scripts that must exist in that checkout
    "experiment": ["scripts/eval_matrix.py", "scripts/evaluate.py", "scripts/train.py", "scripts/run_scripted.py",
                   "scripts/record_video.py", "scripts/make_ckpt_matrix.py"],
    "tools": ["scripts/closeout.py", "scripts/closeout_make_configs.py", "scripts/closeout_repeatability.py",
              "scripts/closeout_regen_compare.py", "scripts/closeout_package.py", "scripts/closeout_verify.py",
              "scripts/closeout_check_numbers.py", "scripts/closeout_inspect_ckpt.py",
              "scripts/download_release.py", "scripts/verify_archives.py", "scripts/verify_v2_release.py",
              "scripts/v2_select.py", "scripts/v2_analyze_final.py", "scripts/v2_analyze_dev.py",
              "scripts/v2_select_constants.py", "scripts/v2_analyze_pilots.py", "scripts/v2_nondeterminism.py",
              "scripts/v2_compare_replay.py", "scripts/build_report_v2.py", "scripts/build_deck_v2.py",
              "scripts/cluster/isaac_run.sh", "scripts/cluster/lsf_submit.sh"],
}
DOCS_WITH_COMMANDS = ["docs/closeout/REPRODUCE.md", "docs/v2/REPRODUCE.md", "README.md"]
ARGPARSE_RE = re.compile(r"add_argument\(\s*[\"'](--[a-z0-9-]+)[\"']")


def script_flags(path: Path) -> set[str]:
    text = path.read_text()
    flags = set(ARGPARSE_RE.findall(text))
    if "add_launcher_args" in text:  # Isaac Lab AppLauncher flags (verified against the installed version)
        flags |= {"--device", "--enable_cameras", "--livestream", "--verbose", "--info", "--experience",
                  "--rendering_mode", "--kit_args", "--anim_recording_enabled", "--anim_recording_start_time",
                  "--anim_recording_stop_time", "--xr", "--visualizer", "--headless"}
    if "add_rsl_rl_args" in text:
        flags |= {"--experiment_name", "--run_name", "--resume", "--load_run", "--checkpoint", "--logger",
                  "--log_project_name"}
    flags.add("--help")
    return flags


def doc_commands(md: str) -> list[tuple[str, list[str]]]:
    """(script, flags) for every `scripts/X.py ...` invocation inside fenced code blocks (joined continuations)."""
    out = []
    for block in re.findall(r"```(?:bash|sh)?\n(.*?)```", md, flags=re.S):
        block = re.sub(r"\\\n\s*", " ", block)
        for line in block.splitlines():
            for m in re.finditer(r"((?:[\w.$/{}-]*/)?scripts/[\w/]+\.(?:py|sh))((?:\s+(?![|&;>]).*?)?)(?=$|\s[|&;]|\s>)", line):
                script = re.sub(r"^.*?(scripts/)", r"\1", m.group(1))
                flags = re.findall(r"(?<!\S)(--[a-z0-9-]+)", m.group(2) or "")
                out.append((script, flags))
    return out


def md_links(root: Path, files: list[Path]) -> list[dict]:
    bad = []
    for f in files:
        text = f.read_text(errors="replace")
        for m in re.finditer(r"\]\(([^)\s]+)\)", text):
            t = m.group(1).split("#")[0]
            if not t or re.match(r"^[a-z]+:", t):
                continue
            # verbatim archives of README-based assignments keep the README's repository-root-relative links
            base = root if f.name == "ASSIGNMENT.md" and f.parent.name in ("closeout",) else f.parent
            if not (base / t).exists():
                bad.append({"file": f.relative_to(root).as_posix(), "target": m.group(1)})
    return bad


def st_check(c: Ctx):
    res = {"scripts": {}, "doc_commands": [], "links": [], "asset_names": [], "simulator_source": {}}
    ok = True
    for role, scripts in REQUIRED_SCRIPTS.items():
        root = c.exp if role == "experiment" else c.tools
        miss = [s for s in scripts if not (root / s).exists()]
        res["scripts"][role] = {"checkout": git_state(root), "required": scripts, "missing": miss}
        ok &= not miss
    # documented commands: the script must exist in the checkout the doc assigns it to, every flag must exist
    for d in DOCS_WITH_COMMANDS:
        p = c.tools / d
        if not p.exists():
            continue
        for script, flags in doc_commands(p.read_text()):
            where = c.exp if (c.exp / script).exists() and script in REQUIRED_SCRIPTS["experiment"] else c.tools
            sp = where / script
            if not sp.exists():
                res["doc_commands"].append({"doc": d, "script": script, "problem": "missing"})
                ok = False
                continue
            if script.endswith(".py"):
                unknown = sorted(set(flags) - script_flags(sp))
                if unknown:
                    res["doc_commands"].append({"doc": d, "script": script, "problem": f"unknown flags {unknown}"})
                    ok = False
    # --help of every CPU tool (proves the parser accepts the documented interface without Isaac Lab)
    helps = {}
    for s in REQUIRED_SCRIPTS["tools"]:
        if s.endswith(".py"):
            r = subprocess.run([sys.executable, str(c.tools / s), "--help"], capture_output=True, text=True)
            helps[s] = r.returncode
            ok &= r.returncode == 0
    res["help_rc"] = helps
    mds = [p for p in c.tools.rglob("*.md") if ".git" not in p.parts and "closeout_work" not in p.parts
           and not p.is_relative_to(c.work)]
    res["links"] = md_links(c.tools, mds)
    ok &= not res["links"]
    # archive/asset names mentioned in current docs must exist in a release asset list we ship
    known = set()
    for sums in sorted(c.inputs.glob("*/SHA256SUMS")):  # every downloaded release's asset list
        known |= {l.split()[1] for l in sums.read_text().splitlines() if l.strip()}
    res["asset_lists"] = [c.rel(p) for p in sorted(c.inputs.glob("*/SHA256SUMS"))]
    if known:
        for d in ["report/v2/diagnostics.md", "report/v2/report.md", "docs/closeout/REPRODUCE.md",
                  "docs/v2/REPRODUCE.md", "README.md"]:
            p = c.tools / d
            if p.exists():
                for n in sorted(set(re.findall(r"`([\w.-]+\.(?:tar\.gz|zip|pptx|pdf|json|md))`", p.read_text()))):
                    if n.startswith(("raw-", "checkpoints-", "videos", "logs", "results", "configs-", "closeout-", "source-",
                                     "v2.0.0-")) and n not in known:
                        res["asset_names"].append({"doc": d, "name": n})
                        ok = False
    if c.exp.exists():
        res["simulator_source"] = {"identical": not sim_source_diff(c.tools, c.exp),
                                   "differences": sim_source_diff(c.tools, c.exp)}
        ok &= res["simulator_source"]["identical"]
    res["ok"] = ok
    c.record("check", res)
    if not ok:
        print(json.dumps({k: v for k, v in res.items() if k in ("doc_commands", "links", "asset_names")}, indent=1))
        raise StageError("check failed (see record)")


def st_download(c: Ctx):
    tag = c.a.tag
    d = c.inputs / tag
    d.mkdir(parents=True, exist_ok=True)
    marker = d / ".verified.json"
    if marker.exists() and (d / "SHA256SUMS").exists():
        m = json.loads(marker.read_text())
        if m.get("sha256sums") == sha_file(d / "SHA256SUMS") and (d / "x").exists():
            print(f"[closeout] download {tag}: already verified, skipping", flush=True)
            return
    cmds = []
    env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    r = subprocess.run([sys.executable, "-I", str(c.tools / "scripts/download_release.py"), "--repo", c.a.repo,
                        "--tag", tag, "--output", str(d)], env=env)
    cmds.append({"cmd": f"download_release.py --tag {tag}", "rc": r.returncode})
    if r.returncode:
        raise StageError("download failed")
    sums = {}
    for line in (d / "SHA256SUMS").read_text().splitlines():
        h, n = line.split(None, 1)
        sums[n.strip().lstrip("*")] = h
    bad = [n for n, h in sums.items() if sha_file(d / n) != h]
    if bad:
        raise StageError(f"checksum mismatch: {bad}")
    if (d / "x").exists():
        shutil.rmtree(d / "x")
    rec = c.run([sys.executable, "-I", str(c.tools / "scripts/verify_archives.py"), "--bundle", str(d), "--extract",
                 str(d / "x")], cwd=c.work, log=c.work / "logs" / f"download_{tag}.log")
    cmds.append(rec)
    assets = sorted(p.name for p in d.iterdir() if p.is_file() and not p.name.startswith("."))
    body = {"tag": tag, "assets": len(assets), "checksums_ok": len(sums), "sha256sums": sha_file(d / "SHA256SUMS"),
            "commands": cmds, "extract": c.rel(d / "x")}
    marker.write_text(json.dumps(body, indent=1))
    c.record(f"download_{tag}", body)


def st_regen(c: Ctx):
    x = c.x()
    if not x.exists():
        raise StageError(f"run 'download --tag {c.a.inputs_tag}' first")
    out = c.work / "regen"
    log = c.work / "logs" / "regen.log"
    py = sys.executable
    T = c.tools
    cmds = [
        ([py, T / "scripts/v2_select.py", "--train-root", x, "--validation", x / "final/validation",
          "--suite", T / "configs/v2/suites/validation.jsonl", "--output", out / "final/selection"]),
        ([py, T / "scripts/v2_analyze_final.py", "--final", x / "final/eval", "--manifest",
          T / "configs/v2/matrices/final/final_manifest.json", "--selection", out / "final/selection", "--train", x,
          "--output", out / "summary"]),
        ([py, T / "scripts/v2_analyze_dev.py", "--dev", x / "dev", "--output", out / "diagnostics", "--n-boot", "4000"]),
        ([py, T / "scripts/v2_select_constants.py", "--dev", x / "dev", "--output", out / "diagnostics/constants_v2.json"]),
        ([py, T / "scripts/v2_analyze_pilots.py", "--pilot", x / "pilot", "--output", out / "pilot"]),
    ]
    # trace figures of results/v2/diagnostics/figures (same commands as the v2 study)
    F, D, TT = out / "diagnostics/figures", x / "dev", x / "dev/failure_traces/traces"
    pt = [py, T / "scripts/v2_plot_traces.py"]
    for case in ("v2dev-position_stress-0000", "v2dev-joint_early_stress-0000", "v2dev-joint_late_stress-0000",
                 "v2dev-position_in-0000"):
        cmds.append(pt + ["--case", case, "--trace", D / "controls/traces/geometry_zero.json",
                          "--trace", D / "controls/traces/const_geometry_1cm_x+003mm.json",
                          "--trace", D / "learned/traces/combined_final_s11.json",
                          "--trace", D / "learned/traces/combined_init_s33.json", "--output", F / f"trace_geometry_{case}.png"])
        cmds.append(pt + ["--case", case, "--trace", D / "controls/traces/nominal.json",
                          "--trace", D / "controls/traces/const_nominal_x+004mm.json",
                          "--trace", D / "learned/traces/residual_final_s22.json", "--output", F / f"trace_nominal_{case}.png"])
    for name, case, trs in [
            ("residual_drop", "v2dev-joint_early_stress-0003", ["nominal", "residual_final_s22"]),
            ("geometry_deep_insertion", "v2dev-joint_early_stress-0035",
             ["geometry_zero", "const_geometry_1cm_x+003mm", "combined_final_s11"]),
            ("combined_bias", "v2dev-joint_early_stress-0017", ["geometry_zero", "const_geometry_1cm_x+003mm", "combined_final_s11"]),
            ("nominal_timeout", "v2dev-joint_early_stress-0000", ["nominal", "const_nominal_x+004mm", "residual_final_s22"])]:
        cmds.append(pt + ["--case", case] + [a for t in trs for a in ("--trace", TT / f"{t}.json")]
                    + ["--output", F / f"failtrace_{name}_{case}.png"])
    (F).mkdir(parents=True, exist_ok=True)
    recs = [c.run(cmd, cwd=c.work, log=log) for cmd in cmds]
    nd = out / "summary/nondeterminism_untrained_vs_zero.json"
    with open(nd, "w") as f:
        r = subprocess.run([py, str(T / "scripts/v2_nondeterminism.py"), "--final", str(x / "final/eval")], stdout=f)
    recs.append({"cmd": ["v2_nondeterminism.py", "--final", "$X/final/eval", ">", c.rel(nd)], "rc": r.returncode})
    if r.returncode:
        raise StageError("v2_nondeterminism.py failed")
    cmp_out = c.work / "regen/comparison.json"
    recs.append(c.run([py, T / "scripts/closeout_regen_compare.py", "--regen", out, "--archived", T / "results/v2",
                       "--output", cmp_out], cwd=c.work, log=log))
    comp = json.loads(cmp_out.read_text())
    try:
        import numpy  # noqa: F401
        npv = numpy.__version__
    except Exception:
        npv = None
    c.record("regen", {"inputs": {"extract": c.rel(x)}, "commands": recs, "python": sys.version.split()[0],
                       "numpy": npv, "comparison": c.rel(cmp_out), "summary": comp.get("summary")})


def sim_task(c: Ctx, task: str, matrix_rel: str, entry: str | None, out: Path, seed: int, num_envs: int,
             scheduled: int, extra: list[str] | None = None, conditions: list[str] | None = None) -> dict:
    """Run (or resume) one eval_matrix task; returns its status. Ledger: <work>/ledger/<task>.jsonl."""
    led = c.work / "ledger" / f"{task.replace('/', '_')}.jsonl"
    attempts = [json.loads(l) for l in led.read_text().splitlines()] if led.exists() else []
    status_p = out / "matrix_status.json"

    def done() -> bool:
        if not status_p.exists():
            return False
        st = json.loads(status_p.read_text())
        ents = [entry] if entry else list(st)
        return all(e in st and st[e]["recorded"] == st[e]["scheduled"] and st[e]["missing"] == 0 for e in ents)

    if done():
        return {"task": task, "state": "complete", "attempts": len(attempts)}
    if len(attempts) >= c.a.max_attempts:
        return {"task": task, "state": "failed_max_attempts", "attempts": len(attempts)}
    mx = c.resolved_matrix(matrix_rel, out / "_matrix", conditions)
    args = ["scripts/eval_matrix.py", "--matrix", str(mx), "--output", str(out), "--checkpoint-root", str(c.x()),
            "--seed", str(seed), "--num-envs", str(num_envs), *(["--only", entry] if entry else []), *(extra or [])]
    log = c.work / "logs" / f"{task.replace('/', '_')}.attempt{len(attempts) + 1}.log"
    rec = c.sim(args, log)
    st = json.loads(status_p.read_text()) if status_p.exists() else {}
    rec.update({"task": task, "attempt": len(attempts) + 1, "utc_end": utc(), "process_seed": seed,
                "num_envs": num_envs, "entry": entry, "matrix": matrix_rel,
                "matrix_sha256": sha_file(c.tools / matrix_rel), "resolved_matrix_sha256": sha_file(mx),
                "status": st, "complete": done(), "host": socket.gethostname(),
                "gpu": gpu_info(), "experiment_commit": git_state(c.exp)["commit"],
                "tools_commit": git_state(c.tools)["commit"]})
    if rec["complete"]:
        rec["outputs"] = {p.name: sha_file(p) for p in sorted(out.glob("*.jsonl"))}
    with open(led, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return {"task": task, "state": "complete" if rec["complete"] else f"incomplete_rc{rec['rc']}",
            "attempts": len(attempts) + 1}


def gpu_info() -> list[str]:
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=60)
        dev = os.environ.get("CUDA_VISIBLE_DEVICES")
        return [f"CUDA_VISIBLE_DEVICES={dev}"] + r.stdout.strip().splitlines()
    except Exception as e:
        return [f"nvidia-smi unavailable: {e}"]


def env_snapshot(c: Ctx, name: str):
    """Record the simulator environment once per job (versions; pip freeze hash)."""
    p = c.work / "env" / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    fr = subprocess.run([c.isaac(), "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    pins = {k: v for k, v in (l.split("==", 1) for l in fr.splitlines() if "==" in l)
            if k.lower() in ("isaaclab", "isaacsim", "isaacsim-core", "rsl-rl-lib", "torch", "numpy", "warp-lang")}
    py = subprocess.run([c.isaac(), "-c", "import sys;print(sys.version.split()[0])"], capture_output=True,
                        text=True).stdout.strip()
    lock = c.tools / "configs/v2/frozen/pip-freeze.txt"
    p.write_text(json.dumps({"utc": utc(), "host": socket.gethostname(), "gpu": gpu_info(), "python": py,
                             "pins": pins, "pip_freeze_sha256": hashlib.sha256(fr.encode()).hexdigest(),
                             "matches_frozen_lock": fr.strip() == lock.read_text().strip() if lock.exists() else None},
                            indent=1))
    (c.work / "env" / f"{name}.pip-freeze.txt").write_text(fr)


def st_negative(c: Ctx):
    c.require_exp()
    env_snapshot(c, "negative")
    out = c.work / "sim/negative"
    runs = [("nominal_clean", ["--method", "nominal", "--num-envs", "1", "--episodes", "1"]),
            ("geometry_clean", ["--method", "geometry", "--num-envs", "1", "--episodes", "1", "--set", "align_max=0.015"]),
            ("neg_no_receiver", ["--method", "nominal", "--num-envs", "20", "--episodes", "20",
                                 "--set", 'negative_control="no_receiver"']),
            ("neg_giver_holds", ["--method", "nominal", "--num-envs", "20", "--episodes", "20",
                                 "--set", 'negative_control="giver_holds"']),
            ("neg_table_support", ["--method", "nominal", "--num-envs", "20", "--episodes", "20",
                                   "--set", 'negative_control="table_support"', "--set", "table_size_override=[0.06,0.30,0.20]"])]
    recs = []
    for name, args in runs:
        o = out / name
        if (o / "_done.json").exists():
            recs.append(json.loads((o / "_done.json").read_text()))
            continue
        r = c.sim(["scripts/run_scripted.py", *args, "--output", str(o)], c.work / "logs" / f"negative_{name}.log")
        r["outcomes"] = outcome_counts(o)
        r["name"] = name
        if r["rc"] == 0:
            (o / "_done.json").write_text(json.dumps(r, indent=1))
        recs.append(r)
    ok = all(r["rc"] == 0 for r in recs)
    c.record("negative", {"runs": recs, "ok": ok})
    if not ok:
        raise StageError("a negative-control run failed")


def outcome_counts(d: Path) -> dict:
    cnt = {}
    for f in d.rglob("*.jsonl"):
        for l in f.read_text().splitlines():
            try:
                r = json.loads(l)
            except Exception:
                continue
            if "terminal_reason" in r:
                k = f"{r['terminal_reason']}|success={r.get('success')}"
                cnt[k] = cnt.get(k, 0) + 1
    return cnt


def st_replay(c: Ctx):
    c.require_exp()
    env_snapshot(c, "replay")
    cfg = json.loads((c.tools / "configs/closeout/verification_replay.json").read_text())
    out = c.work / "sim/replay"
    s = sim_task(c, "replay", "configs/closeout/matrices/verification_replay.json", None, out,
                 cfg["process_seed"], cfg["num_envs"], len(cfg["case_ids"]) * len(cfg["entries"]))
    if s["state"] != "complete":
        c.record("replay", {"status": s})
        raise StageError(f"replay incomplete: {s}")
    cmpo = c.work / "sim/replay_comparison.json"
    rec = c.run([sys.executable, c.tools / "scripts/closeout_repeatability.py", "agreement", "--archived",
                 c.x() / "final/eval", "--replay", out, "--output", cmpo], cwd=c.work, log=c.work / "logs/replay.log")
    c.record("replay", {"status": s, "comparison_cmd": rec, "comparison": c.rel(cmpo),
                        "summary": json.loads(cmpo.read_text()).get("summary")})


def st_repeatability(c: Ctx):
    c.require_exp()
    man = json.loads((c.tools / "results/closeout/repeatability/run_manifest.json").read_text())
    cfg_sha = sha_file(c.tools / man["config"])
    if cfg_sha != man["config_sha256"]:
        raise StageError("repeatability config changed after the run manifest was frozen")
    tasks = man["tasks"]
    for t in tasks:
        if sha_file(c.tools / t["matrix"]) != t["matrix_sha256"]:
            raise StageError(f"{t['task']}: matrix hash differs from the frozen manifest")
    if c.a.throughput:
        # Short throughput check (not part of the results): one learned entry on the 200 'clean' cases at each
        # batch size, in its own output folder.
        env_snapshot(c, "throughput")
        res = []
        for b in (900, 23):
            t = next(t for t in tasks if t["batch_size"] == b and t["entry"] == "combined_seed11__final")
            out = c.work / "sim/throughput" / f"b{b}"
            res.append(sim_task(c, f"throughput_b{b}", t["matrix"], t["entry"], out, t["process_seed"], b, 200,
                                conditions=["clean"]))
        c.record("throughput", {"tasks": res, "cases_per_task": 200, "ledger": "$WORK/ledger/throughput_b*.jsonl"})
        return
    i, n = (int(v) for v in c.a.shard.split("/"))
    mine = [t for k, t in enumerate(tasks) if k % n == i]
    env_snapshot(c, f"repeatability_shard{i}of{n}")
    states = []
    for t in mine:
        states.append(sim_task(c, t["task"], t["matrix"], t["entry"], c.work / "sim" / t["output"], t["process_seed"],
                               t["batch_size"], t["scheduled"]))
        print(f"[closeout] {states[-1]}", flush=True)
    c.record(f"repeatability_shard{i}of{n}", {"tasks": states})


def st_analyze(c: Ctx):
    """Stage 4 analysis. Default inputs: this work folder's sim/ and ledger/; with --from-release the records come
    from the extracted closeout-repeatability archive of the input release (x/closeout/{sim,ledger})."""
    x = c.x()
    sim, led = (x / "closeout/sim", x / "closeout/ledger") if c.a.from_release else (c.work / "sim", c.work / "ledger")
    out = c.work / "analysis/repeatability"
    rec = c.run([sys.executable, c.tools / "scripts/closeout_repeatability.py", "analyze", "--sim", sim,
                 "--archived", x / "final/eval", "--ledger", led, "--output", out],
                cwd=c.work, log=c.work / "logs/analyze.log")
    cmp = {}
    ref = c.tools / "results/closeout/repeatability"
    for f in sorted(out.glob("*.csv")) + sorted(out.glob("*.json")):
        g = ref / f.name
        cmp[f.name] = "identical" if g.exists() and g.read_bytes() == f.read_bytes() else ("differs" if g.exists() else "no committed copy")
    c.record("analyze", {"command": rec, "inputs": {"sim": c.rel(sim), "ledger": c.rel(led), "archived": c.rel(x / "final/eval")},
                         "output": c.rel(out), "comparison_with_committed": cmp})


def st_resume_smoke(c: Ctx):
    c.require_exp()
    env_snapshot(c, "resume_smoke")
    run = c.a.resume_run
    src = c.x() / run / "checkpoints/latest.pt"
    if not src.exists():
        raise StageError(f"no resumable checkpoint {src}")
    before = sha_file(src)
    out = c.work / "sim/resume_smoke" / run
    if out.exists():
        shutil.rmtree(out)  # disposable directory owned by this stage
    method, seed = run.rsplit("_seed", 1)
    meta = json.loads((c.x() / run / "run.json").read_text())
    batch, done_t = int(meta["rollout_batch_transitions"]), int(meta["realized_transitions"])
    budget = done_t + 2 * batch  # exactly two PPO iterations after the restored counter; no periodic save before
    r = c.sim(["scripts/train.py", "--method", method, "--seed", seed, "--protocol",
               str(c.tools / "configs/v2/frozen/protocol.json"), "--run-type", "smoke", "--resume", str(src),
               "--transitions", str(budget), "--output", str(out)], c.work / "logs/resume_smoke.log")
    insp = c.work / "sim/resume_smoke" / f"{run}_inspect.json"
    r2 = c.sim([str(c.tools / "scripts/closeout_inspect_ckpt.py"), "--before", str(src), "--after",
                str(out / "checkpoints/final.pt"), "--expect-iterations", str(int(meta["total_iterations"]) + 2),
                "--expect-transitions", str(budget), "--output", str(insp)], c.work / "logs/resume_smoke.log")
    after = sha_file(src)
    body = {"source_checkpoint": c.rel(src), "sha256_before": before, "sha256_after": after,
            "source_unchanged": before == after, "train": r, "inspect": r2, "output": c.rel(out),
            "budget_transitions": budget, "inspection": json.loads(insp.read_text()) if insp.exists() else None}
    c.record("resume_smoke", body)
    if r["rc"] or r2["rc"] or before != after:
        raise StageError("resume smoke failed")


def st_render(c: Ctx):
    T = c.tools
    vers = {}
    for name, exe in (("chrome", c.a.chrome), ("libreoffice", c.a.soffice)):
        try:
            vers[name] = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=120).stdout.strip()
        except Exception as e:
            vers[name] = f"unavailable: {e}"
    try:
        import markdown, pptx  # noqa: F401
        vers["python-markdown"], vers["python-pptx"] = markdown.__version__, pptx.__version__
    except Exception:
        pass
    vers["python"] = sys.version.split()[0]
    (T / "results/closeout/render_environment.json").write_text(json.dumps(vers, indent=1) + "\n")
    recs = [c.run([sys.executable, T / "scripts/build_report_v2.py", "--chrome", c.a.chrome], cwd=T,
                  log=c.work / "logs/render.log"),
            c.run([sys.executable, T / "scripts/build_deck_v2.py", "--soffice", c.a.soffice], cwd=T,
                  log=c.work / "logs/render.log")]
    c.record("render", {"commands": recs, "versions": vers})


def st_package(c: Ctx):
    head = git_state(c.tools)
    if head["dirty"]:
        raise StageError("package needs a clean delivery-tools checkout")
    cmd = [sys.executable, c.tools / "scripts/closeout_package.py", "--work", c.work, "--tag", c.a.release_tag,
           "--source-commit", head["commit"], "--output", c.work / "release" / c.a.release_tag]
    for r in c.a.redact:
        cmd += ["--redact", r]
    for r in c.a.redact_regex:
        cmd += ["--redact-regex", r]
    rec = c.run(cmd, cwd=c.tools, log=c.work / "logs/package.log")
    rec["cmd"] = [x if not any(x.startswith(r.split("=")[0]) for r in c.a.redact) else "<redaction rule>" for x in rec["cmd"]]
    c.record("package", {"command": rec, "source_commit": head["commit"]})


def st_verify(c: Ctx):
    bundle = Path(c.a.bundle) if c.a.bundle else c.inputs / c.a.tag
    rec = c.run([sys.executable, "-I", c.tools / "scripts/closeout_verify.py", "--bundle", bundle,
                 "--extract", c.work / "verify" / bundle.name / "x", "--output", c.work / "verify" / f"{bundle.name}.json"],
                cwd=c.work, log=c.work / "logs/verify.log")
    c.record(f"verify_{bundle.name}", {"command": rec})


def st_video_replay(c: Ctx):
    """Re-render the committed video plan from the downloaded checkpoints (single environment, experiment checkout)
    and compare each replay outcome with the archived evaluation record and the v2.0.0 sidecar."""
    c.require_exp()
    env_snapshot(c, "video_replay")
    plan = json.loads((c.tools / "configs/closeout/video_plan.json").read_text())
    only = set(c.a.only.split(",")) if c.a.only else None
    out = c.work / "sim/video_replay"
    out.mkdir(parents=True, exist_ok=True)
    resolved = []
    for v in plan["videos"]:
        if only and v["video"] not in only:
            continue
        resolved.append({**v, "checkpoint": str(c.x() / v["checkpoint"]) if v["checkpoint"] else None,
                         "eval_records": str(c.x() / v["eval_records"]), "output": str(out / v["video"])})
    rp = out / "resolved_video_plan.json"
    rp.write_text(json.dumps(resolved, indent=1))
    r = c.sim(["scripts/record_video.py", "--plan", str(rp), "--suite", plan["suite"], "--protocol", plan["protocol"]],
              c.work / "logs/video_replay.log")
    old = {v["video"]: v for v in json.loads((c.inputs / c.a.inputs_tag / "videos.json").read_text())}
    rows = []
    for v in resolved:
        side = Path(v["output"]).with_suffix(".json")
        sc = json.loads(side.read_text()) if side.exists() else {}
        ro, eo = sc.get("replay_outcome") or {}, old[v["video"]]["evaluation_outcome"]
        rows.append({"video": v["video"], "rendered": Path(v["output"]).exists(),
                     "replay_terminal_reason": ro.get("terminal_reason"), "evaluation_terminal_reason": eo["terminal_reason"],
                     "replay_matches_evaluation": ro.get("terminal_reason") == eo["terminal_reason"]
                     and ro.get("success") == eo["success"],
                     "v2.0.0_replay_terminal_reason": old[v["video"]]["replay_outcome"]["terminal_reason"]})
    c.record("video_replay", {"command": r, "videos": rows,
                              "all_match": all(x["replay_matches_evaluation"] for x in rows) and bool(rows)})
    if r["rc"]:
        raise StageError("video replay failed")


STAGES = {"checkout": st_checkout, "check": st_check, "download": st_download, "regen": st_regen,
          "negative": st_negative, "replay": st_replay, "repeatability": st_repeatability, "analyze": st_analyze,
          "resume-smoke": st_resume_smoke, "render": st_render, "package": st_package, "verify": st_verify,
          "video-replay": st_video_replay}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=[*STAGES, "all-cpu"])
    ap.add_argument("--work", default="closeout_work", help="output root (default ./closeout_work)")
    ap.add_argument("--tools", default=str(TOOLS_DEFAULT), help="delivery-tools checkout (default: this checkout)")
    ap.add_argument("--exp", default=None, help="experiment checkout (default <work>/src/experiment-v2)")
    ap.add_argument("--repo", default="ywen0511/CSCI645-Project", help="GitHub repository for downloads")
    ap.add_argument("--repo-url", default=REPO_URL)
    ap.add_argument("--tag", default="v2.1.0", help="release to download/verify")
    ap.add_argument("--inputs-tag", default="v2.1.0", help="downloaded release whose archives feed regen/sim stages")
    ap.add_argument("--from-release", action="store_true", help="analyze: read Stage 4 records from the input release")
    ap.add_argument("--isaac-python", default=None)
    ap.add_argument("--shard", default="0/1", help="repeatability: I/N")
    ap.add_argument("--throughput", action="store_true", help="repeatability: throughput check only")
    ap.add_argument("--max-attempts", type=int, default=3, help="simulator task attempts in total (1 + resumes)")
    ap.add_argument("--resume-run", default="combined_seed11")
    ap.add_argument("--only", default="", help="video-replay: comma-separated video file names")
    ap.add_argument("--chrome", default=os.environ.get("CLOSEOUT_CHROME", "google-chrome"))
    ap.add_argument("--soffice", default=os.environ.get("CLOSEOUT_SOFFICE", "libreoffice"))
    ap.add_argument("--release-tag", default="v2.1.0")
    ap.add_argument("--bundle", default=None, help="verify: release directory (default: <work>/inputs/<tag>)")
    ap.add_argument("--redact-host", action="store_true", help="write <redacted> instead of the host name")
    ap.add_argument("--redact", action="append", default=[], help="package: OLD=TOKEN path redaction")
    ap.add_argument("--redact-regex", action="append", default=[], help="package: REGEX=TOKEN redaction")
    a = ap.parse_args(argv)
    c = Ctx(a)
    stages = ["download", "check", "regen"] if a.stage == "all-cpu" else [a.stage]
    for s in stages:
        STAGES[s](c)


if __name__ == "__main__":
    main()
