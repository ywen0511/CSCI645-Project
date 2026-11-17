# Reproducing the archived V3 study

Use only the public Git repository, release assets and official simulator distribution.
This revision corrects paths and placeholder handling in the old instructions. Sections
1–4 were executed verbatim on the GPU cluster on 2026-11-09 (tooling `4d7beb3`) and passed;
the record is in [MAINTENANCE.md](MAINTENANCE.md) and `results/post_v3/stage_a/`. The
[original verification](VERIFICATION.md) records the earlier v3.0.0 execution. The same
assets are also available through the maintenance release `v3.0.1` (section 6).

## 1. Create three distinct checkouts (CPU)

Run the blocks in the same Bash shell. Choose a **new** workspace; the command below
creates one automatically. All subsequent paths are absolute, independent of `cd`.

```bash
set -eu
V3_WORK=$(mktemp -d "${TMPDIR:-/tmp}/csci645-reproduce.XXXXXX")
T="$V3_WORK/tooling"
D="$V3_WORK/delivery"
E="$V3_WORK/experiment"
B="$V3_WORK/release"
X="$V3_WORK/extracted"
R="$V3_WORK/replay"
G="$V3_WORK/regenerated"
REPO_URL=https://github.com/ywen0511/CSCI645-Project.git
git clone --branch study/v3-observation-robustness "$REPO_URL" "$T"
git -C "$T" rev-parse HEAD > "$V3_WORK/tooling_commit.txt"
git clone --branch v3.0.0 "$REPO_URL" "$D"
git clone --branch experiment-v3 "$REPO_URL" "$E"
test "$(git -C "$E" rev-parse HEAD)" = 3811f5da5ef55638f95f7306e449609877f546df
test "$(git -C "$D" rev-parse HEAD)" = ebfa328b17103c32ae19c13f0a6408ebc55a6459
```

`T` contains repaired tooling. Pin its recorded commit when repeating this procedure;
never assume a moving branch is an immutable source reference. `D` contains the
archived analysis/delivery source. `E` is the unchanged simulator source used for every
V3 replay and resume. Do not copy maintenance changes into `E`.

The archived CPU analysis lock uses Python 3.13.9 and
[requirements-analysis.txt](../../configs/closeout/requirements-analysis.txt).
The remote simulator environment is Isaac Lab v3.0.0 / Isaac Sim 6.2.0.0 / PhysX,
Python 3.12, RSL-RL 5.5.1 and PyTorch 2.11 (CUDA 13), as recorded in
[SETUP_REMOTE.md](../SETUP_REMOTE.md) and [the environment lock](../../configs/v2/frozen/pip-freeze.txt).
Check installed versions against these records. Rendering also needs Chrome/Chromium
and LibreOffice. Do not silently substitute a different simulator and call it exact reproduction.

## 2. Download, verify and regenerate (CPU)

```bash
python3.13 -m venv "$V3_WORK/analysis-env"
PY="$V3_WORK/analysis-env/bin/python"
"$PY" -m pip install -r "$D/configs/closeout/requirements-analysis.txt"
"$PY" -I "$T/scripts/v3_download.py" --tag v3.0.0 --output "$B"
"$PY" -I "$D/scripts/v3_verify.py" --bundle "$B" --extract "$X" --output "$V3_WORK/bundle_verify.json"
"$PY" "$D/scripts/v3_regen.py" --runs "$X" --work "$G"
"$PY" "$T/scripts/v3_rebuild_suites.py" --experiment-repo "$E" --check
"$PY" "$T/scripts/v3_rebuild_suites.py" --experiment-repo "$E" --output "$V3_WORK/rebuilt-suites"
```

The verifier checks release/member checksums, safely extracts archives, resolves the
457 checkpoint-index entries, reconciles final/validation counts, decodes videos and
opens documents. Downloading consumes about 461 MB; extraction needs additional space.
`$X/formal/train` contains released checkpoints; `$X/final` and `$X/validation` hold records.
`$G/regen.json` reports regeneration and comparison of 35 tables and 6 figures. Exit code 0
allows files that are numerically equal within a relative tolerance of 1e-9 (`float_only`).
On the 2026-11-09 run (AMD EPYC node) `mechanisms/mechanisms.json` was `float_only`: 116
least-squares values differed by at most 8.9e-16 (BLAS rounding); the other 34 files and all
6 figures (`$G/figures/*.png` against `$D/results/v3/figures/`) were byte-identical.

The suite rebuilder is standard-library-only and reads the original generator from
`E`. It checks all 60 frozen inputs, with one explicit historical exception:
`SUITES.json` gained its final entry after freeze. It retrieves and hashes the
pre-final Git bytes, checks that only that entry was added, and compares every generated
suite and manifest field with the archive. It never rewrites `FREEZE.json` or `E`;
`--check` is repeatable, and `--output` refuses an existing directory. Do not use
`v3_prepare.py --final` to rebuild an already finalized archive.

## 3. Small complete replay (remote GPU only)

Set `ISAAC` to the absolute Python executable of the installed compatible simulator
environment. Find it from the remote environment inventory; this is the only
machine-specific executable path below. Set `CLOSEOUT_VK_ICD_DIR` if the documented
cluster wrapper requires a user-space Vulkan ICD. No simulator is launched in CPU preparation.

```bash
ISAAC=/absolute/path/to/isaaclab-env/bin/python
test -x "$ISAAC"
mkdir -p "$R/formal"
ln -s "$X/formal/train" "$R/formal/train"
ln -s "$X/final" "$R/final"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/verification.json"   --repo "$E" --runs-root "$R" --isaac-python "$ISAAC"   --only replay65_geometry_common --dry-run
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/verification.json"   --repo "$E" --runs-root "$R" --isaac-python "$ISAAC"   --only replay65_geometry_common --task-timeout-s 3600
```

This executes **all 65 cases**, with 23 environments. It is not a one-case example;
let it finish. Results are in `$R/replay65/geometry_common/geometry_common.jsonl`.
The runner resolves `$DELIVERY` and `$RUNS` inside JSON matrices. Do not pass the
unresolved delivery matrix directly to `eval_matrix.py`. Dry-run resolves dependencies
and writes local resolved JSON, but never launches a task.

## 4. All replay, reload and resume checks (remote GPU)

```bash
"$PY" - "$X/formal/train/combined_robust_history_s11/checkpoints/latest.pt" > "$V3_WORK/resume-input.sha256" <<'HASH'
import hashlib, pathlib, sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
HASH
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/verification.json"   --repo "$E" --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600
"$PY" "$T/scripts/v3_fresh_compare.py" --x "$R" --output "$V3_WORK/fresh_gpu.json"
"$PY" - "$V3_WORK/fresh_gpu.json" "$X/formal/train/combined_robust_history_s11/checkpoints/latest.pt"   "$V3_WORK/resume-input.sha256" <<'CHECK'
import hashlib, json, pathlib, sys
r = json.loads(pathlib.Path(sys.argv[1]).read_text())
assert len(r['replay65']) == 7 and all(x['cases'] == 65 for x in r['replay65'])
assert len(r['reload']) == 4 and all(x['cases'] == 13 for x in r['reload'])
assert r['summary']['mismatches'] == 0 and r['resume']['ok']
for x in r['replay65'] + r['reload']:
    assert not x['missing_in_final'] and x['invalid_resets'] == 0
    assert x['terminal_equal'] == x['success_equal'] == x['cases']
    assert x['observation_error_equal'] and x['checkpoint_sha256_equal']
assert hashlib.sha256(pathlib.Path(sys.argv[2]).read_bytes()).hexdigest() == pathlib.Path(sys.argv[3]).read_text().strip()
CHECK
```

Expected coverage: 455 replay and 52 reload episodes, plus two resumed PPO iterations
(306 to 308; 10,027,008 to 10,092,544 transitions) into `$R/resume_check`, preserving the
released checkpoint. Execute sequentially: resume inspection depends on resume training.
The comparator's exit code alone is not an acceptance gate; the explicit count/content
assertions above are required. Investigate and report all mismatches, including hardware
nondeterminism; do not erase them or relax checks merely to pass.

Then audit the replay records themselves (case-ID sets against the subset suites,
uniqueness, resets, source/suite/config/checkpoint hashes, outcomes; standard library only):

```bash
"$PY" -I "$T/scripts/post_v3_replay_audit.py" --replay "$R" --extracted "$X" --tooling "$T" \
    --experiment-sha 3811f5da5ef55638f95f7306e449609877f546df --checkpoint-index "$B/checkpoints.json" \
    --output "$V3_WORK/replay_audit.json"
```

Expected: `{"entries": 11, "replay65_episodes": 455, "reload_episodes": 52, "discrepancies": 0}`.

Repeat the runner command once: all 13 tasks should skip only after hashes and
provenance match. Preserve the new ledger separately from the historical release ledger.
Symlinks above are read-only input references, not declared task outputs.

## 5. Full final reevaluation (optional reproduction, remote GPU)

```bash
F="$V3_WORK/full-final"
mkdir "$F"
ln -s "$X/formal/train" "$F/train"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/final.json"   --repo "$E" --runs-root "$F" --isaac-python "$ISAAC" --task-timeout-s 3600
```

This runs 50 executed entries of 2,600 cases. The aliases are declared in
`configs/v3/final_matrices/baseline_aliases.json`. `--shard I/N` may distribute independent
final tasks across available GPUs. Do not shard a manifest with task dependencies
without scheduling its stages. Full retraining is unnecessary for maintenance acceptance;
the historical training/selection contract is [V3_EXECUTION.md](../../V3_EXECUTION.md).
A new training run needs its own validation-selected matrices, not the old selection.

## 6. Using the maintenance release v3.0.1 (CPU)

`v3.0.1` contains every `v3.0.0` asset byte-identical inside `v3.0.0-original-assets.tar`,
plus the maintenance source, evidence and indices. To start from it instead of `v3.0.0`,
replace the download line of section 2 with:

```bash
B1="$V3_WORK/release-v3.0.1"
"$PY" -I "$T/scripts/v3_download.py" --tag v3.0.1 --output "$B1"
"$PY" -I "$T/scripts/post_v3_verify_release.py" --bundle "$B1" --original-out "$B" \
    --output "$V3_WORK/maintenance_release_verify.json"
```

This checks `SHA256SUMS`, manifest coverage, safe paths and every member hash of every
archive, extracts the 30 original assets into `$B`, checks them against the manifest and the
original `SHA256SUMS`, and resolves all 457 entries of `checkpoint_locations.json` by hashing
the checkpoint inside its original archive. Expected: `"ok": true`, 30 original assets,
457 checkpoints resolved. Continue with the `v3_verify.py` line of section 2 unchanged.

## Integrity and limits

The repaired runner requires the **latest** attempt to succeed and verifies input files,
matrix suite/protocol/checkpoint dependencies, resolved arguments, execution commit,
runner context, and output file/directory fingerprints before skipping. Modified complete
outputs or legacy provenance are refused; preserve them and use a fresh run directory.
Missing outputs may resume through the underlying script's provenance checks. Directory
fingerprints cover content and membership and reject symlinks. Old ledgers are historical
evidence, not upgraded cache certificates. Use `T` for the runner and `E` for execution.

The inherited simulator shutdown watchdog can terminate a process after its shutdown
marker; output existence alone is not scientific validation. Always check case counts,
provenance and outcome comparisons above. CPU regression tests use synthetic fixtures;
they do not establish physics fidelity or revalidate the reported success rates.
