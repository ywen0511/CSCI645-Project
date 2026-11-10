# V4 remaining-work assignment — resume through complete public delivery

> **Historical completed assignment.** V4 is released as v4.0.0 with repaired tooling
> in v4.0.1. Do not restart this training/evaluation mission. The current finite
> assignment is [FINAL_DELIVERY_HANDOFF.md](FINAL_DELIVERY_HANDOFF.md).

## Mission and authorization

You are the remote execution agent for Yan Wen's CSCI 645 project at
https://github.com/ywen0511/CSCI645-Project . Finish the remaining work described here,
including implementation still needed, experiments, analysis, all checkpoints, reports,
videos, published GitHub Release and verification from fresh public downloads. This file
is the entry point; every referenced input is in this repository or its public releases.
No previous chat or owner-local file is required. All public output must be English.

Use branch `study/v4-grasp-uncertainty`. You may implement/fix code, use already available
remote GPUs, install isolated compatible dependencies, commit/push, create new immutable
tags and publish complete releases. Routine steps need no further owner instruction.
Never run GPU/Isaac workloads on the owner's local machine. Do not buy resources,
force-push, change account settings, discard failed evidence or overwrite published tags
or release assets. An unavailable GPU, simulator access or GitHub write credential is a
real blocker: preserve and push independent completed work, record the missing capability
and remaining commands, and keep status incomplete. A negative result is not a blocker.

This continues the same Isaac Sim **using Isaac Lab** / PhysX two-Franka handover with
**two-finger parallel-jaw grippers**, fixed commanded orientations and XYZ PPO residuals
bounded to 2 cm per axis. Do not switch platform, use dexterous hands, fabricate results,
use a hidden weld, or substitute a different research task. No external demonstration
dataset is needed: training uses simulator interaction.

The original scientific/publication contract remains `POST_V3_EXECUTION.md`. This file
resolves its obsolete stage ordering and adds concrete current commands; it does not
waive its evidence requirements. Track work in `POST_V3_STATUS.json` and append decisions
in `docs/v4/DECISIONS.md`. Reconcile concurrent remote progress before resuming work.

## Current checkpoint: what to retain and what remains

Reviewed public base: `f68136211e6b0debac01e5a856f88249d0a7738c`. Later preparation commits
repair workflow tools/docs without changing simulator code or experiment parameters.
Read `docs/v4/CPU_REVIEW.md` and `results/v4/cpu_workflow_review.json` for exact local work.

**Already completed; do not restart:**

- V3 science and release `v3.0.0`. Immutable simulation source `experiment-v3` is
  `3811f5da5ef55638f95f7306e449609877f546df`.
- Stage A maintenance and publicly verified `v3.0.1`, experiment assets preserved byte
  for byte. Maintenance tag `maintenance-v3.0.1` points to
  `c85fded58f776c117368dc02be24405912593e38`. Evidence is in `results/post_v3/`:
  455 replay / 52 reload outcomes agree, resume passes, 34/35 tables are byte-identical
  and one is numerically equal, six figures identical, 457 checkpoint index entries resolve.
- V4 physical-grasp extension, feasibility probes, two baseline development rounds,
  constant-residual search and baseline selection (`configs/v4/development/`).
- Uploaded acceptance A1–A9 and five-profile smoke resume pass. Preserve the first failed
  table-support control and its corrected rerun; lineage is recorded in
  `results/v4/acceptance/PROVENANCE.json`. A1–A3 were rerun at `5089373`; A4–A9/smoke
  are from `f261da3`, with the code difference documented. Do not claim these were rerun
  at the newer preparation commit.

**Pending at the reviewed public checkpoint:** pilots were running/restarted sequentially,
but no complete pilot summary was committed; no `configs/v4/FREEZE.json`, `analysis_plan.json`,
`FINAL_SUITE.json`, `experiment-v4` tag, formal results or V4 report/release existed. Do not
infer completion from the existence of a training script or the protocol specification.
If another worker has since completed a stage, inspect its actual artifacts and continue
from them. Preserve original run source SHAs and all interrupted attempts.

The latest local CPU repairs make freezes require acceptance/pilot evidence, prevent
freeze/final-suite overwrites, require all 25 selection inputs, hash actual checkpoints,
and reject empty/partial manifests. They do not implement remaining video/release tools
or claim new GPU evidence. `python scripts/v4_freeze.py check` is intentionally not ready
until a genuine pilot completion report is present.

## 1. Synchronize, inventory and finish pilots

Use the existing compatible remote environment described in `docs/SETUP_REMOTE.md` and
`configs/v2/frozen/pip-freeze.txt`: recorded Isaac Lab v3.0.0 / Isaac Sim 6.2.0.0 / PhysX,
Python 3.12, Torch 2.11 CUDA 13, RSL-RL 5.5.1. Inventory actual installed versions, GPU/VRAM,
driver, disk, Vulkan setup and GitHub permissions; verify APIs against the installed
version before changes. CPU analysis uses `configs/closeout/requirements-analysis.txt`.
Do not silently substitute a simulator version and label it exact reproduction.

Fetch the latest branch/tags, record its SHA, and inspect active jobs, ledgers, saved
checkpoints and completed outputs before launching anything. Preserve existing local
work and coordinate any concurrent commits. The earlier packed pilot attempt was killed
because one process per GPU had better throughput. Count that attempt, five smoke runs
and resume increments against the 24M pilot cap; do not count resumed cumulative counters
twice. Use one training process per available GPU. Run the full CPU suite first:

```bash
CUDA_VISIBLE_DEVICES='' python -m pytest -q
```

The registered pilot schedule in `results/v4/jobs/pilots.json` is four runs at
5,505,024 transitions each: history seeds 901/902, robust feed-forward seed 901,
residual-only history seed 901. `pilot_eval.json` evaluates 2M, 4M and final checkpoints
on development cases only. Resume the existing runs with their original source/config
provenance; do not reuse their weights for formal training. Archive incomplete and failed
attempts. Reconcile all counts and actual GPU-hours. Inspect stability, losses, reward,
residual saturation, safety events and development performance. Record the formal
configuration decision without inspecting validation/final outcomes. Correct substantive
bugs with a versioned decision and repeat affected acceptance/pilots before freeze.

Commit `results/v4/pilot/summary.json` with this **real-data schema** (the preflight enforces it):

| field | required content |
|---|---|
| `complete` | Boolean true only after all four pilots and their development evaluations finish |
| `all_attempts_accounted` | Boolean true after reconciling successful, interrupted, smoke and resume work |
| `runs` | Exactly four objects: `profile`, `seed`, `status: "completed"`, `transitions: 5505024`; also record source/config/checkpoint/evaluation evidence |
| `other_training_transitions` | Integer extra transitions from smoke/resume/abandoned attempts, counted once |
| `total_training_transitions` | Sum of the four completed runs plus other transitions; at most 24,000,000 |
| `formal_configuration_decision` | Nonempty explanation of retained/changed settings, pilot findings and limitations |
| `evidence` | Nonempty list of `{ "path": "repository-relative small evidence file", "sha256": "actual file SHA256" }` |

Publish small per-run pilot/attempt summaries and evaluation summaries in Git. Include
all raw logs/checkpoints/records in the eventual release and index them in the report.
The gate verifies evidence files/hashes; the agent must also reconcile their contents
against raw artifacts. Do not fill this report with fabricated placeholder success.

Budget remains **100 aggregate GPU-hours for the continuation**, including Stage A,
failed/restarted work, formal training, evaluation and optional work, not 100 per GPU.
Pilot cap is 24M total transitions. Profile throughput and reserve time for delivery.
If mandatory work cannot fit, remove optional work first and report a genuine incomplete
stage rather than silently dropping seeds or expanding the budget.

## 2. Finalize the existing protocol and freeze once

Current research question: where does unknown physical object-to-giver translation break
the old fixed-transform controller, and do calibration, filtering, history or learned
residuals improve performance there? Preserve negative findings. Development already shows
a strong calibrated/EMA baseline; a mixed-ID ceiling is possible. Do not keep redesigning
conditions until RL wins, weaken baselines or grant learned methods privileged ground truth.

The specification is in `docs/v4/PREREGISTRATION.md`; the generator is
`src/csci645_handover/v4_protocol.py`. Retain the developed x/z uncertainty support: x in
[−5,+15] mm and z in [−10,+10] mm during robust training, y zero, 25% zero grasp offset;
OOD includes x to −7 mm, z to ±15 mm and larger sensor corruption. Object mass/friction,
dimensions/orientation remain fixed. Calibration uses the same allowed measurements and
time window for all methods. No scored-time teleport or clean-pose access by controllers.

Required methods: nominal, historical fixed-transform geometry, EMA geometry, calibrated
geometry and best constant residual on geometry (currently zero, an exact calibrated alias).
Learned profiles: combined_clean_ff, combined_robust_ff, combined_robust_history (four frames),
combined_robust_repeat (current frame ×4), residual_robust_history. Five seeds each:
111/222/333/444/555, 10M requested transitions, 10,027,008 realized with the existing rollout.
There are 25 formal runs. Keep residual bounds at 2 cm per axis; geometric alignment's
separately selected bound is 2.5 cm. Do not confuse the two limits.

Splits: development 12×24, validation 6×40, final 12×200 paired base cases; independent
namespaces 6456101/6456201/6456301. Final conditions are clean, grasp_2mm/5mm/10mm/15mm,
bias_5mm, noise_2mm, delay_2step, mixed_id, mixed_ood, boundary_x_minus_7, boundary_z_15.
All methods share each case's draws. Log achieved and requested offsets and invalid resets.

Before freeze, verify per-environment timing/reset/contact semantics and every changed
simulator path against acceptance evidence. If only these CPU tooling/docs changed,
retain the truthful existing acceptance lineage and test the new tools with real pilot
artifacts. Do not report unperformed simulator reruns. Finish the protocol text, analysis
selection rules, source/version locks, video rule and compute/stopping rules before tagging.

Use separate execution and delivery checkouts. The following uses Bash and explicit absolute
paths. Set the workspace and executable paths to the inventoried remote environment,
never to the owner's machine. `T` is your existing synchronized, clean delivery checkout;
`RUNS` is a **new** formal output root. Existing pilots remain at their original location.

```bash
T=$(git rev-parse --show-toplevel)
V4_WORK=$(mktemp -d "${TMPDIR:-/tmp}/csci645-v4.XXXXXX")
E="$V4_WORK/experiment"
RUNS="$V4_WORK/formal"
PY=/absolute/path/to/cpu-python
ISAAC=/absolute/path/to/isaaclab-python
cd "$T"
"$PY" scripts/v4_freeze.py check
```

Do not run `freeze` while required evidence is missing or while source is uncommitted.
Commit completed pilot evidence and any configuration decisions first, then:

```bash
"$PY" scripts/v4_freeze.py freeze
git add configs/v4
git commit -m "Freeze V4 protocol and verified pilot evidence"
git tag -a experiment-v4 -m "Immutable V4 experiment source and pre-final freeze"
git push origin HEAD:study/v4-grasp-uncertainty
git push origin experiment-v4
"$PY" scripts/v4_freeze.py final_suite
"$PY" scripts/v4_freeze.py final_suite
"$PY" scripts/v4_manifests.py train validation
git add configs/v4 results/v4/jobs
git commit -m "Generate V4 final suite and formal execution manifests"
git push origin HEAD:study/v4-grasp-uncertainty
git worktree add --detach "$E" experiment-v4
mkdir -p "$RUNS"
```

If `experiment-v4` or a freeze already exists, verify and reuse its exact provenance;
never move the tag or overwrite the freeze. If a real scientific correction is needed,
use a new explicitly named protocol/tag and rerun affected comparisons. The tagged `E`
contains the frozen simulator/protocols; later matrices/final suites live in `T`. Keep
`E` clean throughout. Repeated final-suite generation must reproduce identical bytes.
Do not edit frozen inputs in `T` and then pretend final-suite reconstruction still matches.

## 3. Formal training, checkpoint selection and held-out evaluation

From `T`, run stages in dependency order. The runner's interpreter argument launches
the simulator through `E/scripts/cluster/isaac_run.sh`; CPU preparation never runs these.

```bash
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/train.json" \
  --repo "$E" --runs-root "$RUNS" --isaac-python "$ISAAC" --dry-run
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/train.json" \
  --repo "$E" --runs-root "$RUNS" --isaac-python "$ISAAC"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/validation.json" \
  --repo "$E" --runs-root "$RUNS" --isaac-python "$ISAAC"
"$PY" "$T/scripts/v4_select_checkpoints.py" --validation "$RUNS/validation" \
  --checkpoint-root "$RUNS/train" --output "$T/results/v4/selection"
"$PY" "$T/scripts/v4_manifests.py" final
```

Record and push selection/matrices before opening final outcomes, then execute:

```bash
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/final.json" \
  --repo "$E" --runs-root "$RUNS" --isaac-python "$ISAAC"
"$PY" "$T/scripts/v4_build_index.py" --runs "$RUNS"
"$PY" "$T/scripts/v4_analyze.py" --root "$RUNS" \
  --index "$T/configs/v4/final_matrix_index.json" --output "$T/results/v4/summary"
```

Check each script's `--help` before use if later remote changes alter its CLI. Use
`--shard I/N` for independent jobs across available GPUs, with exactly one training
process per GPU. Complete all shards of a stage before dependent stages. Do not dry-run
validation before checkpoints exist and mistake missing-input refusal for a simulator bug.

Preserve step 0, every periodic save, selected, final and latest checkpoints, with optimizer,
normalizer, RNG, counters, configuration, source SHA and logs. Step 0 is never eligible for
selection. The five eligible candidates are the first saves at/after 2/4/6/8/10M transitions.
Selection orders validation success descending, unsafe-event rate ascending, residual
magnitude ascending, then latest checkpoint (12-decimal numeric ties). It must verify all
25×6 validation entries of 240 cases, the actual checkpoint hashes and experiment source.
Reconcile invalid resets before selection; do not silently exclude cases or choose by final data.

Final logical matrix is 25 selected + 25 final + five baselines = 55 entries ×2,400 =
132,000 episodes. Exact aliases are declared and evaluated once. With the current zero
constant alias, expect 54 executed entries / 129,600 episodes, unless another genuine exact
alias is documented. One process can evaluate selected/final entries sequentially; do not
confuse process count with entry count. Verify exact case-ID sets, uniqueness, suite/config/
controller/checkpoint/source hashes, valid outcome flags and record counts. The index
builder's header or successful exit is not by itself a full independent provenance audit:
compare indices against frozen matrices and actual checkpoint files too.

Primary contrasts remain history minus robust FF and history minus best constant geometry
on selected-checkpoint mixed ID. Paired hierarchical bootstrap over five training seeds
and base-case clusters, 10,000 draws, seed 6456401; report 95% and Bonferroni 97.5% intervals.
Do not count deterministic geometry as five independent seeds. Publish per-seed results,
all conditions, selected/final sensitivity and degenerate ceiling/floor intervals without
claiming general equivalence. All other comparisons are exploratory. Report success,
drops, collisions, invalid resets, completion time, residual/saturation, calibration error
and actual grasp offsets. Report every failure and quantify hardware/batch differences.

## 4. Mechanisms, repeatability and remaining engineering

These stages are mandatory even if the primary result is zero. The current manifest
builder supports `mech_dev`, `extras`, `traces6`; inspect their exact outputs and run
stages in order:

```bash
"$PY" "$T/scripts/v4_manifests.py" mech_dev
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/mech_dev.json" \
  --repo "$E" --runs-root "$RUNS" --isaac-python "$ISAAC"
"$PY" "$T/scripts/v4_fit_constants.py" --devfit "$RUNS/mechanisms/devfit" \
  --output "$T/results/v4/mechanisms/constant_fits.json"
```

Check that the fitted constants cover all ten selected history runs, only development
cases, and the actual selected checkpoint hashes. Commit the constants, then generate
`extras` and `traces6` and run each resulting manifest with the same runner/source
separation. Record the calibrated/best-constant baseline alias in repeatability too. Build any missing aggregation,
plots or validation tools and test their invariants with CPU fixtures before using them.
Do not claim that a named stage has a complete implementation without inspecting it.

Use the frozen 60-case subset, all selected history seeds, zero-residual parents,
development-fitted constants, reversed history, repeated current frames and untrained
controls. Repeat representative geometry/history evaluations at batch 6 and 20 with
three execution seeds. Keep six-case supplementary traces separate from formal records.
Explain whether effects reflect calibration, a constant offset, actual temporal use,
training instability or randomness. Preserve unfavorable results.

Implement V4 checkpoint reload/resume and video plans/manifests if still missing. Replay
one selected checkpoint of every architecture in fresh processes. Resume two iterations
into a disposable new directory and verify counters/optimizer/normalizer/RNG and the
unchanged source checkpoint hash. Keep all saved resume checkpoints and logs. Re-run the
hash-checked runner and verify completed jobs skip without launching tasks; demonstrate
corruption rejection using disposable CPU fixtures, never released artifacts.

Dynamic physical slip is optional and currently `not_performed`. Do not begin it before
mandatory study and delivery are secure, and use at most 5% of the total compute cap.
If performed, freeze a separate split and use real contact dynamics/declared forces,
never scored-time teleport. Static-offset results alone do not establish slip robustness.

## 5. Report, presentation, artifacts and release

Complete all remaining delivery tooling; reusing V3 tools is encouraged but audit hardcoded
paths, names, counts and source tags. Never publish a V3 bundle relabeled V4. Produce:

- An English report with abstract, course motivation, V2/V3 context, V4 question, controller/
  sensor/calibration/physics details, fairness and information access, frozen methods,
  compute accounting, results/uncertainty, mechanisms, limitations/negative findings,
  verified primary references and software/AI-assistance disclosure. Include editable
  source and a visually inspected PDF; audit every numerical claim against generated data.
- A 12–18 slide editable deck, PDF and speaker notes, with verified figures and readable
  layouts. Distinguish development, pilot, validation and held-out evidence clearly.
- At least eight clips and a montage under the frozen `configs/v4/video_rule.json`, with
  method/seed/case/source/checkpoint/outcome labels and an index. Use the predeclared matched
  comparisons, boundary, noisy calibration, failure/intervention cases. If the designated
  failure does not exist, state it; do not cherry-pick another to manufacture a narrative.
- Source, version locks, suites, frozen manifests, selection records, logical-to-physical
  matrix index, test evidence, tables, figures, decision log and compute/run index in Git.
- Every saved formal/pilot/smoke/resume checkpoint, including intermediate and abandoned
  attempts; raw development/validation/final/mechanism/replay/acceptance records; complete
  training/evaluation logs, curves, traces and task ledgers in release assets. Identical-byte
  deduplication requires a complete alias index. No unexplained missing checkpoint is allowed.

For each checkpoint index entry record run/profile/seed, transitions, role, source SHA,
config hash, file SHA256, asset URL/name and archive member. Include immutable experiment
and delivery source archives. Split large assets within GitHub limits, but never use size
as a reason to omit intermediate checkpoints. Scan public text and archive names for secrets,
private paths/hosts and accidental simulator redistribution. Do not commit binary checkpoints
or large logs to Git; the release must provide them without access to the original cluster.

Create a release manifest and archive-member inventories with sizes/SHA256 for every
asset/member; SHA256SUMS covers everything except its own self-hash. Avoid circular source/
release hashes by distinguishing immutable tagged delivery evidence from post-publication
verification commits. Reconcile artifact completeness against planned runs and saved files,
including failures, and ensure every index path resolves after extraction.

Write `docs/v4/REPRODUCE.md` with **tested commands** using absolute workspace variables,
separate immutable experiment/delivery checkouts, anonymous download, safe extraction,
checksum/coverage checks, CPU table/figure regeneration, a small complete replay, all
architecture reloads and checkpoint resume. Use placeholder-aware matrix resolution.
Do not call a 60-case evaluation one case or instruct the reader to interrupt it early.
A reader must be able to start with only public sources and compatible installed software.

Publish a new `v4.0.0` release or the next unused V4 version, with a distinct immutable
delivery tag and the exact experiment tag. Commit/push meaningful milestones; verify
GitHub branch/tag pointers and each asset's name/size/hash after upload. A draft release,
background job or local bundle is not complete. Existing V3 releases remain untouched.

## 6. Verify the public delivery and close out

Use a new directory with no access to original run outputs. Download all published V4
assets anonymously; verify checksums, safe archive paths and every member inventory;
resolve every checkpoint entry; regenerate all tables/figures; execute the documented
complete replay, architecture reloads and two-iteration resume on available remote GPU.
Compare expected case IDs/counts, hashes and declared outcome tolerances; report every
mismatch rather than relaxing checks to get a pass. Check the report/deck renderings and
numbers, all links and citations, and decode all videos. Repeat using only extracted files
and the documented source checkouts. Fix immutable-bundle errors with another version,
never by replacing published assets. Commit the public verification transcript, source
SHAs, exit codes and machine-readable status after publication.

Only then mark `POST_V3_STATUS.json.complete` true. Explicitly retain optional slip status,
limitations and actual GPU-hours; no completion from absent files or unchecked status flags.
The final English response must link source tags/commits, the release, report, summary
metrics, checkpoint index, video index and fresh-download verification. Any remaining
external blocker must identify incomplete work and exact resume instructions, with all
independently completed artifacts pushed/uploaded where possible.
