# Active remote assignment: verified reproduction and uncertain-grasp handover

> **Current entry point: [V4_REMAINING.md](V4_REMAINING.md).** Stage A has completed
> and v3.0.1 is publicly verified. V4 development and acceptance are already uploaded.
> Use the remaining-work document to resume the current state; preserve this original
> scientific/publication contract and do not restart completed stages.


## Mission, scope and authority

You are the remote execution agent for Yan Wen's CSCI 645 project in
`https://github.com/ywen0511/CSCI645-Project`. Execute this document through publication
and fresh-download verification. It is the complete entry point: obtain all context,
code and prior artifacts from GitHub, without the owner's local files or previous chat.
All public code, prose, plots, slides, video labels, release notes and responses must
be English. Resolve routine implementation choices and continue; do not stop at a plan,
passing CPU tests, starting training, or uploading only the best checkpoint.

The owner authorized implementation, available remote GPU execution, commits/pushes,
new experiment tags and new public GitHub Releases including all saved checkpoints and
results. Use already available resources; do not buy/provision compute, change account
settings, force-push, delete evidence or replace a published release. The preparation
machine is CPU-only: **never run Isaac Sim or GPU work on the owner's local machine**.
An unavailable GPU, required simulator access or GitHub write permission is a real
blocker: record the exact missing capability, preserve completed work, and report it.
Elapsed time or a negative scientific result is not permission to fabricate completion.

Work continues the existing two-Franka, two-finger parallel-jaw handover project using
Isaac Sim **through Isaac Lab**, PhysX, fixed commanded orientations, physical grasps
and bounded XYZ residual PPO (2 cm per axis). No dexterous hand, camera pipeline,
hidden object weld, pretrained task substitution or new unrelated project. External
training datasets are unnecessary; collect simulator interaction. Keep the original
proposal and all earlier results intact.

Read this document first, then the referenced repository files as implementation
context. You do not need another instruction from the owner to proceed through both
stages below. Track new work in `POST_V3_STATUS.json`; retain `V3_STATUS.json` as the
completed historical V3 record. Use `docs/post_v3/DECISIONS.md` and `results/post_v3/`
for maintenance evidence, and `docs/v4/`, `configs/v4/`, `results/v4/`, `report/v4/`
for the new experiment. Create missing directories. Never mix new records into V3 files.

## What is already done

V3 is published at
https://github.com/ywen0511/CSCI645-Project/releases/tag/v3.0.0 . Its immutable simulator
source is `experiment-v3` = `3811f5da5ef55638f95f7306e449609877f546df`; delivery tag
`v3.0.0` = `ebfa328b17103c32ae19c13f0a6408ebc55a6459`.
Read `report/v3/report.md`, `docs/v3/VERIFICATION.md` and `results/v3/summary/`.
There are 23 formal runs, 2,600 final cases, 130,000 executed final episodes and
30 published assets including raw records, all saved checkpoints and videos.

The selected combined policies and strongest giver-reference geometric baseline both
reach 100% on the frozen suite. This is a ceiling; it does not establish learned
superiority or general equivalence. Three of five final history policies deteriorate
substantially, and residual-only comparisons do not establish an advantage. The known
rigid grasp transform plus accurate giver proprioception explains why translation
sensor corruption can largely be bypassed. V3 did not perform physical transfer.
These are findings to preserve, not errors to conceal or reasons to weaken a baseline.

Local maintenance corrected the README/entry points and reproduction commands, added
output/dependency hashing to `scripts/v3_jobs.py`, and added a non-mutating archived
suite rebuilder. See `docs/v3/MAINTENANCE.md` and `tests/test_v3_maintenance.py`.
These changes have CPU evidence only until you complete Stage A. The V4 simulator
extension and experiments below are **not yet implemented or executed**.

## Stage A — verify the repairs and publish a maintenance release

1. Clone `study/v3-observation-robustness`, record its exact SHA and make a working
   branch `maintenance/v3-reproduction` (reuse it only if its recorded work is yours).
   Inventory GPU, driver, OS, Python, Isaac Lab/Sim, Torch, RSL-RL, disk space and
   GitHub push/release permissions. Use the existing remote setup and version locks
   from `docs/SETUP_REMOTE.md`, `docs/ENVIRONMENT.md`, `configs/v2/frozen/pip-freeze.txt`.
   Verify installed APIs/examples before changing simulator code. Record actual
   versions and command exit codes; never expose tokens or private filesystem paths.
2. Run the full CPU test suite with CUDA disabled, using an isolated environment
   containing torch, numpy and pytest. Fetch full Git history if the archived-suite
   integration test skips because the experiment commit is absent. Record test totals
   and explain any skip (the Isaac import test needs the remote simulator environment).
3. Execute **sections 1–4 of `docs/v3/REPRODUCE.md` exactly** from new public clones
   and a fresh anonymous download. Record the tooling SHA, command transcript and
   environment. Verify the three rebuilt suite hashes; run archive verification,
   regenerate 35 tables and 6 figures, perform 455 replay and 52 reload episodes and
   the two-iteration resume. The original released checkpoint hash must not change.
   The repair does not require rerunning all 23 formal training runs.
4. Repeat the verification runner: every completed task must be skipped after content
   verification, with no new simulator launch. Separately use disposable CPU fixtures
   to demonstrate: edited output bytes, directory membership changes, changed checkpoint
   inputs and legacy ledgers cannot produce a false cache hit; missing outputs and a
   failed latest attempt cannot be skipped. Never corrupt a real released artifact.
5. Review all replay records for exact expected case-ID sets, uniqueness, valid resets,
   source/checkpoint/suite/config hashes and outcomes, not just exit codes. The comparison
   helper historically does not itself enforce all counts; keep the explicit assertions
   in REPRODUCE and additionally compare expected IDs with the subset suite. Publish all
   discrepancies. Investigate deterministic mismatches on the recorded environment;
   hardware-related differences require a quantified explanation, not deletion of cases.
6. Fix any discovered reproduction issue in the maintenance checkout with CPU tests;
   commit before rerunning. Do not edit `experiment-v3` in place. If a simulator bug
   changes scientific outcomes, preserve the original, make a separately versioned
   correction with the affected comparisons rerun, and distinguish it from maintenance.
7. Publish a new `v3.0.1` maintenance release (use the next unused patch version if
   occupied). Do not overwrite `v3.0.0`. Commit the final English README, reproduction
   instructions, maintenance report, CPU/GPU acceptance evidence and status. Add an
   immutable maintenance source tag and record both the old experiment SHA and the new
   tooling SHA. Include all original scientific assets, byte-identical, plus the new
   source archive, maintenance evidence and instructions. The original bundle may be
   an independently verifiable nested archive; include a parent manifest/inventory
   explaining the layout. Do not blindly reuse the old packager if its hardcoded layout
   would omit new evidence. Create a full asset/member manifest and SHA256SUMS for the
   new bundle; every checkpoint must be downloadable without the original cluster.
8. Download the maintenance release anonymously into another empty directory. Verify
   every asset/member checksum, new source tag, preserved original bundle, all checkpoint
   paths and the revised quickstart. Record this final public verification in a follow-up
   commit, with links to the immutable tested tag; avoid circular self-hashes. A published
   draft or local bundle is not completion. Update Stage A status and proceed to Stage B.

## Stage B — a separately frozen V4 uncertain-grasp study

### Research question and implementation

Determine where a giver-reference controller fails when the true object-to-giver
transform is unknown, and whether calibrated geometry, short observation history or
learned residuals improve handover in that regime. The contribution can be a measured
failure boundary or a strong geometric solution. A positive RL result is not required.

Start a branch `study/v4-grasp-uncertainty` from the verified maintenance commit and
keep the old experiment checkout read-only. Reuse the V3 task, controllers, PPO,
selection, evaluator and delivery tools, adding versioned V4 configuration and tools.
Read `src/csci645_handover/`, `scripts/train.py`, `scripts/eval_matrix.py`, the V3 freeze,
acceptance tests and analysis contracts before modifying behavior.

The mandatory extension is **unknown initial physical translation of the object within
the giver grasp**, persistent within an episode. Separate this true grasp transform
from translation measurement error and from receiver target offsets. Randomize/reset
the physical grasp, settle the simulation and verify stable contact-based support;
do not merely add another sensor bias or secretly update the controller's assumed
transform. Begin development with feasible translations of 0, 2, 5 and 10 mm along
physically supported local axes, random sign. Check actual object/gripper geometry;
reduce the range or axis set before freeze if those values do not produce stable grasps.
Record the achieved transform after settling, not just the requested offset. Keep mass,
friction, object dimensions and orientation fixed in the primary experiment.

Controllers receive the same deployable channels: corrupted object translation,
robot proprioception and the existing permitted contact/phase signals. None may read
the sampled true offset, clean object pose, case label or future measurement. The
success evaluator and privileged debug logs may use ground truth, never the actor
or geometric correction. Fit an explicit calibrated giver-reference baseline from
those same noisy measurements during a fixed pre-handover observation window; account
for calibration time in timing metrics and expose the same window to learned methods.
The historical fixed-transform controller remains a comparison. If the environment
uses ground truth for release gates, either replace it for every method with the common
allowed estimate or explicitly hold that identical oracle component fixed and limit
the research claim; document every such channel before freeze.

Implement the following acceptance checks on CPU where possible and then in Isaac:

- Zero uncertainty reproduces the V3 task; zero residual reproduces its geometric
  parent when all inputs and parameters match.
- Requested and achieved grasp offsets are logged; settling is stable; no hidden weld,
  post-reset scored teleport or ground-truth correction hides uncertainty.
- All policies/baselines use matched sensor histories, calibration timing and controller
  limits; perturbing a privileged debug-only quantity cannot change controller actions.
- Sensor delay/noise/bias, history buffers, phase timers and randomization are independent
  across environments, deterministic from case seeds, and reset without episode leakage.
- Grasp/contact/release timing and independent receiver hold for 2 seconds are physically
  checked. Invalid reset and infrastructure failure are separate from policy failure.
- Single and vectorized environments, checkpoint reload, interrupted resume, partial
  evaluation resume and tampered provenance rejection work. Include long enough runs
  to catch reset leakage; record counts and videos, not only unit-test assertions.

An additional dynamic-slip experiment is **optional secondary scope**: attempt it only
once the mandatory static-transform study and its delivery are secure, using at most
5% of the total compute cap. It must use actual contact dynamics or declared physical
forces, with no teleport in scored time, and have its own predeclared split. If omitted,
mark `not_performed`; never claim slip robustness from static-offset results.

### Development, methods and bounded compute

Use a one-month working horizon: roughly days 1–3 for Stage A and acceptance, 4–8 for
development/pilots, 9–18 for frozen experiments, 19–24 for analysis/mechanisms, and
25–30 for reports/publication/fresh verification. This is a planning guide, not a reason
to skip acceptance. Profile throughput before training. Record GPU-hours, wall time,
transitions, all attempts and failed/resumed jobs. Hard cap: **100 aggregate GPU-hours**
for this continuation on already available hardware, including verification and optional
work. Do not multiply that limit by GPU count. If projected required work cannot fit,
reduce optional work first; publish a documented incomplete result if the mandatory
protocol remains infeasible. Do not silently reduce seeds or inspect final outcomes
while redesigning. Never spend money or request extra resources automatically.

Use independent development/validation/final RNG namespaces `6456101`, `6456201`,
`6456301` and training seeds **111, 222, 333, 444, 555**. A case contains its base-case
ID, physical draw, requested/achieved grasp offset, observation corruption seed and
severity. Pair base cases across methods and severities. Keep split generators stable,
versioned, deterministic and tested; verify disjoint case IDs/random streams.

During development only, calibrate stable grasp ranges and strong geometric baselines.
Measure failure curves before committing to expensive training. If all valid development
cases are at ceiling, expand feasible uncertainty or the calibration/noise interaction
within the physical task before freeze, with a logged rationale. Do not disable useful
sensors for one method, weaken only the baseline, or tune to guarantee a learned win.
If even the feasible boundary remains easy, freeze and publish that finding.

Required baselines (aliases allowed only for truly identical configurations; count once
as an executed method and disclose aliases):

1. Nominal trajectory with the common safety/release semantics.
2. Historical fixed-transform giver-reference geometry.
3. Geometry driven by noisy translation with development-tuned EMA.
4. Calibrated giver-reference geometry using the shared observation window.
5. Best development-selected geometry plus a constant XYZ residual, tuned only on
   development cases with the same 2 cm per-axis bound as PPO.

Use a declared finite development search: at most 36 baseline configurations, including
EMA alpha in {0.2, 0.5, 1.0}, calibration windows in {0.1, 0.25, 0.5} seconds and the
existing geometric alignment range where physically valid. Register the exact grid
before running it. Evaluate offsets for the constant-residual baseline in a separately
logged finite search; count these evaluations in the compute ledger. Select by success,
then lower unsafe-event rate, lower correction magnitude and lower completion time.
Freeze a common geometric parent for all combined-policy profiles. Carry the strongest
baseline into the final comparison rather than choosing a weak historical parent.

Required learned profiles (five seeds each; **25 formal runs**):

| Profile | Training uncertainty | Observation/history | Parent |
|---|---|---|---|
| combined_clean_ff | zero added grasp/sensor uncertainty | one frame | common geometry |
| combined_robust_ff | development-frozen uncertainty distribution | one frame | common geometry |
| combined_robust_history | same robust distribution | four chronological frames | common geometry |
| combined_robust_repeat | same robust distribution | current frame repeated four times | common geometry |
| residual_robust_history | same robust distribution | four chronological frames | nominal trajectory |

Use the existing PPO library and equal architecture/optimizer/horizon conventions except
where input dimensionality necessarily changes; the repeated-current control tests that
confound. The learned outputs stay bounded to 2 cm per axis. Pilot cap: **24 million
aggregate transitions** across all candidates/failed pilot attempts. Formal budget:
10,000,000 requested transitions per run, rounded up identically to complete rollout
batches and recorded (V3 used 10,027,008 with 1,024 environments × 32 steps). Do not carry
pilot weights into formal runs. Select checkpoint candidates at the first saved step
at or after 2, 4, 6, 8 and 10 million transitions using validation only; save step 0 as an
untrained control, never an eligible selection. Preserve every saved periodic checkpoint,
selected, final and latest with optimizer, normalizer, RNG, counters and config metadata.

### Freeze, evaluation and analysis

Use 24 paired base cases per development condition, 40 per validation condition and
200 per final condition. Before freeze, commit a 12-condition table covering clean,
three nonzero feasible grasp severities, sensor-only bias/noise/delay, mixed ID, mixed
OOD and axis/direction boundary checks. Explicitly list all numerical parameters,
calibration window, support/axis choices, held-out directions and training support.
Validation covers six declared ID/diagnostic conditions (240 cases). Final covers all
12 conditions (2,400 cases). Do not call a larger sensor error physical transfer, and
label interpolation/extrapolation relative to the actual training distribution.

Commit acceptance evidence and a preregistration/freeze containing source SHA, all
input hashes, seeds, candidate checkpoints, baseline selection, primary contrasts,
success definition, exclusions, tie-breaks, stopping rules, metrics and compute budget.
Generate the final suite by the frozen generator only after freezing. Use separate
pre-final input and final-suite manifests so rebuilding does not invalidate its own
freeze. Tag clean experiment source as `experiment-v4` before formal training. Never
patch that tag; if an outcome-affecting bug is discovered, version a correction and
rerun affected methods, explaining the original failure.

Use validation mean success, then lower unsafe-event rate, lower residual magnitude
and latest candidate as deterministic checkpoint tie-breaks; define numerical ties
before freeze. Keep the selected and final checkpoints as separate analyses. Final
outcomes may not select checkpoints, baselines, conditions, videos or hyperparameters.

Predeclare two primary paired contrasts on mixed ID at selected checkpoints:
`combined_robust_history - combined_robust_ff` and
`combined_robust_history - best_constant_geometry`. Report success percentage-point
differences with a paired hierarchical bootstrap over training seeds and base-case
clusters, 10,000 draws, fixed analysis seed `6456401`, and Bonferroni 97.5% intervals
for the two contrasts. Preserve cross-condition case pairing; a deterministic baseline
must not be inflated into five independent training seeds. Report individual seed
values, denominator reconciliation, all conditions and final-checkpoint sensitivity.
Handle degenerate ceiling/floor intervals explicitly; no equivalence claim without a
prespecified equivalence test and margin. Secondary comparisons are labeled exploratory.

Report success, drops, collisions/unsafe events, valid reset rate, completion time,
residual norms/saturation, calibration error and achieved grasp offset, stratified by
condition and seed. Invalid-reset counts remain visible. Investigate systemic reset
bugs before final execution; never discard difficult policy failures as invalid resets.

Evaluate all five baselines and both selected/final checkpoints of all 25 policies on
all 2,400 final cases: nominally 55 logical entries / 132,000 episodes, minus only
explicit exact aliases. Publish an index mapping every logical entry to physical raw
files and expected case IDs, hashes and counts. Trace six predeclared cases from
separate supplementary runs if the batching implementation requires it; never replace
formal outcome records with prettier trace runs.

Run mechanisms on a predeclared 60-case subset (five cases per final condition):
zero residual, constant mean residual fitted on development only, history order
permutation and repeated-current observations, using every selected history seed.
Include untrained step-0 controls. Repeat representative baseline/history evaluations
with at least two batch sizes and three execution seeds; report numerical/outcome
mismatches. Replay at least one selected checkpoint from every architecture in a fresh
process and resume two training iterations into a new directory without altering its
source checkpoint. Use these checks to distinguish sensor estimation, fixed offsets,
true history use, and training instability; do not infer causal mechanisms from a single
successful video.

## Reports, artifacts and publication for V4

Produce an English report with abstract, original motivation, V2/V3 findings, V4
question, simulator/controller/sensor semantics, fairness and calibration details,
preregistered protocol, compute, full results with uncertainty, mechanisms, failures,
limitations, related work with verified primary references, reproducibility and
software/AI-assistance disclosure. Keep unsupported claims out. Supply editable source
and a visually reviewed PDF. Do not relabel V3 results as newly measured V4 evidence.
Create a 12–18 slide editable deck, PDF and speaker notes with a coherent course-demo
story, and an 8-clip minimum video set plus a montage. Predeclare representative case
rules before final evaluation: matched nominal/geometry/learned comparisons, an unknown
grasp boundary case, noisy calibration, a failure when one exists, and an intervention.
Include method/seed/case/source/checkpoint labels and a video index; if a designated
failure does not occur, state that rather than searching for a misleading substitute.

Git contains source, version locks, configurations, frozen suites/manifests, tests,
small tables/figures, reports and indices. Large checkpoints, raw records, complete logs,
traces and videos belong in release assets. Split large archives to fit GitHub limits;
never omit intermediate checkpoints merely to simplify uploading. Include:

- Immutable experiment and delivery source archives and their exact SHA/tag references.
- Every saved checkpoint from formal, pilot, smoke and resume runs; deduplicate identical
  bytes only with a complete alias index. Each index entry records run/profile/seed,
  transitions, role, config hash, source SHA, file SHA256 and downloadable asset/member.
- Raw development, validation, final, ablation, replay and acceptance records; training
  curves, failures, resumed attempts, logs, full task ledger and compute accounting.
- Generated tables/figures with scripts; dependency locks; selected/final checkpoint
  decisions; videos/index/montage; report PDF/source and deck/PDF/notes.
- Full release manifest, per-archive member inventory and SHA256SUMS covering all assets
  except the checksum file's self-hash. Audit references for missing/orphaned artifacts.
- A public-source-only `docs/v4/REPRODUCE.md`: explicit absolute workspace variables,
  pinned source roles, anonymous download, safe verification/extraction, CPU regeneration,
  small **complete** replay, checkpoint reload and resume. Include exact commands and
  expected outputs/counts; do not leave required actions as TODOs or assume cluster paths.

Commit and push meaningful milestones and maintain resumable state. Publish `v4.0.0`
(or the next unused V4 version) only after acceptance; do not overwrite V3 releases.
Use an immutable experiment tag for simulation and a distinct delivery tag for reports
and packaging, with accurate provenance if one commit cannot contain both. Reconcile
GitHub asset names/sizes/hashes with the manifest after upload. A release must be
published and publicly downloadable, not only drafted.

From a **new directory with no access to original run outputs**, anonymously download
all published assets, verify checksums and safe archive paths/member inventories,
resolve every checkpoint index entry, regenerate all tables/figures, replay the stated
cases and architectures, and resume a saved checkpoint. Compare results with declared
counts and tolerances and publish the verification transcript and machine-readable
status. Re-run report number/citation/link audits and visually inspect rendered PDF
and slides; decode every video. Scan public text/archives for credentials and private
paths. Any immutable published-bundle fix requires another version, not asset replacement.

## Completion and final response

Set `POST_V3_STATUS.json.complete` to true only when Stage A and the mandatory Stage B
study, analyses, documents, all checkpoint/result uploads and fresh public-download
verification are complete. Keep optional slip status explicit. Include source and
release URLs, test results, experiment counts, actual compute, major findings and
remaining limitations. If external resources prevent completion, mark the exact stage
blocked/incomplete, record resumable commands and artifact locations, publish completed
work where possible, and explain the missing capability. Never label partial work complete.

The final English response must link the maintenance release, V4 release, experiment
and delivery tags, report, metrics, checkpoint index, videos and verification record.
The repository must then let a new reader independently find, download, verify and
reproduce the work without access to this conversation or either agent's local files.
