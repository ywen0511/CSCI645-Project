# V5 execution assignment — matched calibration ablation and dynamic in-grasp slip

**Active assignment for the remote GPU agent.** Read this whole file before acting. It is
the complete instruction: no chat history, owner-local file or further approval is needed.
Every input is in this repository (branch `study/v5-calibration-slip`) or its public
releases. All public output must be English. Track progress in [V5_STATUS.json](V5_STATUS.json)
and append every decision to [docs/v5/DECISIONS.md](docs/v5/DECISIONS.md).

## 0. Mission, authority and boundaries

You are the remote execution agent for Yan Wen's CSCI 645 project
(https://github.com/ywen0511/CSCI645-Project). V1–V4 are complete and released (latest
v4.0.2). The owner has asked for two new GPU studies and a complete public delivery:

- **Study A — matched calibration ablation (cheap, run first).** Fully specified and frozen
  on CPU before any outcome existed. You execute it exactly; you do not redesign it.
- **Study B — dynamic in-grasp slip.** The one setting where a one-shot calibration goes
  stale and temporal memory has a clear reason to help. You implement, accept, freeze,
  train, evaluate and analyse it under the rules below.
- **Delivery.** Report, slides, videos, every checkpoint and raw record, a new GitHub
  Release `v5.0.0`, public fresh-download verification, and `main` updated.

You are authorized, without asking again, to: implement and fix code; install isolated
compatible dependencies; use the already available remote GPUs (Isaac Lab v3.0.0 / Isaac
Sim 6.2.0.0 / PhysX on NVIDIA A100, see [docs/SETUP_REMOTE.md](docs/SETUP_REMOTE.md));
commit and push to `study/v5-calibration-slip`; open and merge a pull request into `main`;
create new immutable tags (`experiment-v5a`, `experiment-v5b`, `v5.0.0`); upload release
assets and publish releases.

You must not: buy compute or change account/security settings or repository visibility;
force-push; delete or overwrite any existing tag, release or release asset (fix mistakes
with a new version, e.g. `v5.0.1`); delete failed or unfavourable evidence; run Isaac
workloads on the owner's machine; switch simulator, robot, gripper type or task; add
dexterous hands, vision or a hidden weld/attachment; change Study A after reading this
file; or change any benchmark, metric or analysis in order to make reinforcement
learning win. A negative or null result is a valid result and is never a blocker.

Real blockers are only: no compatible GPU, no simulator access, no GitHub write access,
or a documented physical infeasibility of Study B (section 3.2). On a blocker, push all
independent completed work, record the exact missing capability and resume commands in
`V5_STATUS.json`, and leave `complete: false`.

**Compute cap: 60 A100 GPU-hours for all of V5**, including failed jobs and verification
(V4 used 16.18 in total; 25 formal runs took 8.6). Record actual usage with
`scripts/v4_compute.py`-style accounting in `results/v5/compute.json`.

## 1. What is already done on CPU (do not redo)

The commits on this branch after the V4 head `ab2a25c`, made on the owner's machine without any GPU:

| Item | Where |
|---|---|
| Failure taxonomy of all 129,600 V4 final episodes (proposal metrics) | `scripts/v5_failure_taxonomy.py`, `results/v5/cpu/`, `report/final/failure_modes.png` |
| Final overview updated (failure section, V3 counter-example, ManipTrans, unified AI disclosure, V5 pointers) | `report/final/overview*.{md,pdf}`, `scripts/final_review_build.py` |
| Disclosure corrected (Claude Code only; Codex was named in error) | `docs/final_review/REVIEW.md`, `docs/final_review/DEFENSE_NOTES.md` |
| **Study A frozen inputs**: held-out suite, matrices, preregistered plan, FREEZE hashes | `configs/v5/calibration/`, generator `scripts/v5_make_calibration_study.py` |
| **Study A analysis code**, tested on synthetic records | `scripts/v5_calibration_analysis.py`, `tests/test_v5_cpu.py` |

CPU tests: `python -m pytest -q` → 113 passed, 1 skipped (Isaac Lab not installed).
Simulator source (`src/`, `scripts/eval_matrix.py`, `scripts/train.py`,
`configs/v2/protocol.json`) is byte-identical to `experiment-v4`
(`aac4d98274814b1ab121a715db71187e3e1cc0b9`).

## 2. Study A — matched calibration ablation (execute exactly)

**Question.** With EMA alpha and alignment bound held fixed, does the 0.5 s calibrated
giver reference improve success over the fixed nominal transform, on fresh cases?
V4's 5.5% → 94.5% grasp-15 headline changed reference, EMA alpha (1.0 → 0.2) and bound
(15 → 25 mm) together. Study A is a 2 × 2 × 2 factorial of training-free geometry
controllers on 2,400 new held-out cases (12 V4 conditions × 200; split seed 6457301,
disjoint from all V1–V4 seeds). The plan is
[configs/v5/calibration/analysis_plan.json](configs/v5/calibration/analysis_plan.json).

Steps:

1. Verify the freeze: `python scripts/v5_make_calibration_study.py --check` must print PASS.
   If it fails, stop and record why; never regenerate or edit frozen files.
2. Commit-clean source; tag the commit you evaluate from as `experiment-v5a`
   (simulator code must still equal `experiment-v4`; check with
   `git diff --stat experiment-v4 HEAD -- src scripts/eval_matrix.py configs/v2/protocol.json`).
3. Run, from the repository root, on one GPU each (process seeds from the plan):

   ```bash
   python scripts/eval_matrix.py --matrix configs/v5/calibration/matrix_ema1p0.json \
       --output runs/v5/calibration/primary --seed 6457501
   python scripts/eval_matrix.py --matrix configs/v5/calibration/matrix_ema0p2.json \
       --output runs/v5/calibration/primary --seed 6457501
   python scripts/eval_matrix.py --matrix configs/v5/calibration/matrix_repeat_ema0p2.json \
       --output runs/v5/calibration/repeat --seed 6457502
   ```

   Launch them headless through the same GPU wrapper V4 used (`scripts/cluster_v2/gpu_run.sh`
   or its configurable equivalent). Use `--dry-run` first; confirm launcher flags against
   `--help` for the installed Isaac Lab and record the exact commands you ran.
4. **Acceptance gates before analysis.** Every entry has 2,400 records, 0 infra errors,
   clean source. The two anchors must reproduce V4's configuration identity:
   `ema1p0_fixed_a15` (= V4 `geometry_fixed`) must record
   `config_hash ff52ebeb464217fc60d301eb801c3a5b056fa3e4c2de55905e0c5b2ceb8a61c0` and
   `controller_hash c822250edf8d7096a57c6b9483eb445f606ba8a2c71d4430996a9b38e7314b35`;
   `ema0p2_cal050_a25` (= V4 `geometry_calibrated`) must record
   `config_hash 8b3a0a9d62c89028f6e02c1d8c3fb482416f7ddb109a3121a4c834d00f02eb74` and
   `controller_hash 96a1ffc40be5b12405e23d525d3343a67c9bba7846685c7428c04d22d1cb607a`
   (source: `configs/v4/final_matrix_index.json`). A mismatch means the controller differs from V4:
   stop, diagnose, record; do not proceed to claims.
5. Analyse with no edits to the script:
   `python scripts/v5_calibration_analysis.py --records runs/v5/calibration/primary --repeat runs/v5/calibration/repeat --out results/v5/calibration`.
   The decision rule is fixed: a primary contrast (A1 mixed ID, A2 grasp-15; calibrated
   minus fixed at alpha 0.2, bound 25 mm) supports a calibration-only improvement only if
   its Bonferroni 97.5% lower bound is > 0. Report both outcomes as they fall.
6. Also run `scripts/v5_failure_taxonomy.py`-style terminal-reason tables for Study A
   (write a small reader for the new records; do not modify the V4 taxonomy outputs).
7. Traces for the trace cases are produced by the primary matrices; include them.

Any analysis beyond the plan is labelled **post hoc** everywhere it appears.

## 3. Study B — dynamic in-grasp slip

### 3.1 Question and design principles

When the bar slides in the giver's grip *after* the 0.5 s calibration window has closed
and before the receiver grasps, does a learned residual with observation history recover
better than (i) the same residual without history and (ii) the strongest training-free
controller that re-estimates the offset continuously?

Principles that are not negotiable:

- The slip is **physical**: produced by simulated forces/grip changes in PhysX, never by
  teleporting the bar relative to the fingers during the scored phase. The realized
  in-grasp displacement is measured from the simulator and recorded per episode.
- Controllers see only deployable signals (same fairness contract as
  `src/csci645_handover/core/grasp.py`): corrupted translation measurement, measured
  proprioception, contact flags. Never the true offset or the true slip.
- A **strong continuous re-estimating geometric baseline** must exist before any
  learning claim (below). If it solves the task, that is the finding.
- Same success definition, evaluator, physical parameters, case realizations and
  all-scheduled denominator for every method. Failed slip realizations count as failures,
  exactly as invalid resets did in V4.

### 3.2 Implementation and feasibility probe (development only)

Timeline (control 20 Hz, physics 120 Hz): scored phase starts after reset settling; the
calibration window is scored frames 0–9 (0.5 s); receiver nominal grasp `t_grasp = 2.0 s`;
nominal release 2.8 s ± 0.3 s. **Slip onset must lie in [0.7, 1.4] s and the slip must be
complete by 1.8 s.**

The bar (0.15 kg, μ = 1.0) is held only by friction from the giver's fingers (70 N effort
cap). Candidate mechanisms, choose by a documented development probe:

- (a) a transient reduction of giver finger effort combined with a small axial force on
  the bar, restored after the slip;
- (b) an axial external force/impulse on the bar sufficient to overcome friction;
- (c) another physically simulated mechanism with an equally clear justification.

Add opt-in, per-environment config fields (default off, so V1–V4 configurations and their
hashes are unchanged; add a test proving the V4 `config_hash` is unchanged when slip is
off). Case schema additions: `slip_xyz_m` (target, env-local; x = bar axis), `slip_onset_s`,
`slip_duration_s`. Records add `slip_realized_xyz_m`, `slip_error_m`, `slip_valid`.

Probe on development cases only (prefix `v5slip`, development split seed 6458101): targets
x ∈ {−7, −5, −2, +2, +5, +10, +15} mm cumulative offset, z = 0, several onsets. **Acceptance:**
realized slip within ±1.5 mm of target in ≥ 95% of probe episodes per target that you keep;
no giver drop or receiver contact caused by the mechanism itself before t_grasp; the
existing negative controls (no receiver, giver holds, table support) still cannot succeed;
a no-slip case is unchanged from V4 behaviour. Keep only feasible targets; record dropped
ones. Spend at most 6 GPU-hours on probing. If no mechanism passes, Study B is physically
infeasible in this setup: write `docs/v5/SLIP_FEASIBILITY.md` with the evidence, set
`study_b: "infeasible"` in status, skip 3.3–3.6, and still complete Study A and delivery.

### 3.3 Methods

Training-free (evaluated on every suite):

| ID | Description |
|---|---|
| `nominal` | scripted controller |
| `geometry_fixed` | V4 historical fixed geometry |
| `geometry_calibrated` | V4 one-shot 0.5 s calibration, alpha 0.2, bound 25 mm (the common parent) |
| `geometry_ema` | V4 EMA geometry without giver reference |
| `geometry_tracking` | **new**: giver-reference correction re-estimated continuously while the giver holds (e.g. an EMA or sliding window of measured − kinematic in the giver-hand frame, updated every fresh frame after the initial window) |
| `geometry_best` | the strongest training-free configuration selected on development |

Tune `geometry_tracking` (at most 6 configurations: time constant / window length and
bound) and the constant-offset baseline on **development only**, using V4's ranking
(success, then unsafe events, then correction magnitude, then completion time). The
selected strongest training-free controller is `geometry_best`.

Learned (combined residual on the `geometry_calibrated` parent, XYZ bound 2 cm per axis,
fixed orientations, RSL-RL PPO, V4 PPO settings and curriculum, 10,027,008 transitions per
run, seeds 111/222/333/444/555):

- `slip_robust_ff` — current frame only;
- `slip_robust_history` — 4-frame stacked history;
- `slip_robust_repeat` — current frame repeated 4 times (controls for input size).

That is 15 formal runs. Training distribution: V4 robust profile (grasp offsets, sensor
corruption) plus slip drawn from the `slip_mixed_id` rule below with probability 0.5.
Configs go in `configs/v5/slip/training/`, mirroring `configs/v4/training/`. Pilot first
(one seed, ≤ 2 M transitions per profile) to estimate throughput and check that learning
curves move; pilots are labelled and released but never used for claims.

### 3.4 Suites, selection and freeze

Seeds: development 6458101, validation 6458201, final 6458301, analysis 6458401,
evaluation process 6458501, repeatability 6458601. Generate with a
`scripts/v5_make_slip_study.py` that reuses `v4_protocol.make_cases` plus slip fields.
Final conditions (200 paired base cases each; adjust bounds only to the feasible range
established in 3.2, decided before freezing):

| Condition | In-grasp start offset | Slip (x, cumulative bound applies) | Sensor |
|---|---|---|---|
| `clean` | 0 | none | clean |
| `static_mixed_id` | V4 mixed_id | none | V4 mixed_id |
| `slip_pos_5` | 0 | +5 mm | clean |
| `slip_pos_10` | 0 | +10 mm | clean |
| `slip_neg_5` | 0 | −5 mm | clean |
| `slip_after_offset` | x = +10 mm | −10 mm | clean |
| `slip_mixed_id` (**primary**) | V4 mixed_id | uniform [−5, +10] mm, onset uniform [0.7, 1.4] s | V4 mixed_id |
| `slip_mixed_ood` | V4 mixed_ood | uniform [−7, +15] mm | V4 mixed_ood |

Clamp any draw so the cumulative offset stays in the accepted feasible range; record the
clamp rule. Validation uses `clean`, `static_mixed_id`, `slip_pos_10`, `slip_mixed_id`
(40 cases each). Checkpoint candidates every 1 M transitions; step zero is never eligible;
select by validation success, then unsafe rate, then residual magnitude, then later
transitions (exactly V4's rule in `scripts/v4_select_checkpoints.py`). Report selected and
final checkpoints separately.

**Freeze before any final evaluation** in `configs/v5/slip/FREEZE.json`: suites and hashes,
training configs, `geometry_best` choice, matrices, selection rule and
`configs/v5/slip/analysis_plan.json`. Tag `experiment-v5b` at the frozen commit. The plan
must state:

- Primary (selected checkpoints, `slip_mixed_id`): **B1** history − feed-forward;
  **B2** history − `geometry_best`. Paired training-seed × base-case bootstrap, 10,000
  draws, seed 6458401, 95% and Bonferroni 97.5% intervals (the V4 implementation in
  `scripts/final_review_audit.py::paired_bootstrap`). Superiority only if the 97.5% lower
  bound > 0; no equivalence claims.
- Secondary/exploratory: all conditions; repeat − ff (temporal order vs input size);
  `geometry_tracking` − `geometry_calibrated` (does continuous re-estimation fix stale
  calibration); final vs selected checkpoints; regression on `static_mixed_id` and on the
  V4 final suite (`configs/v4/suites/final.jsonl`) for the selected Study B policies.
- Mechanisms on a 60-case subset: reversed history, repeated current frame, and a
  development-fitted constant, as in V4 (`scripts/v4_mechanisms.py`).
- Repeatability: rerun all training-free baselines and one seed of each learned profile in
  a second process (seed 6458601); report terminal-outcome agreement.

### 3.5 Execution and analysis

Run formal training, validation, selection, final evaluation (every method × 8 conditions
× 200 cases; learned × 5 seeds × selected/final), mechanisms, repeatability and the V4
regression. Analyse with a new `scripts/v5_slip_analysis.py` that refuses to run if the
freeze hashes changed, mirrors the Study A script's structure, and is unit-tested on
synthetic records before you look at real outcomes. Produce failure taxonomies including
slip-specific reasons (`slip_valid`, collisions, drops, misalignment at grasp).

### 3.6 Interpretation rules

Write what the frozen analysis shows. If `geometry_tracking` matches or beats learning,
the conclusion is that continuous geometric estimation, not learning, handles slip. If
history beats both comparators (B1 and B2 lower bounds > 0), that is the first held-out
evidence in this project that memory helps, scoped to this slip model. Never relabel an
exploratory result as primary.

## 4. Reports, slides and videos

- `report/v5/report.md` + PDF (template-driven like `report/v4/report_template.md` with a
  values JSON and a check that every number comes from generated data): motivation, V1–V4
  context, Study A, Study B (mechanism, acceptance, feasibility, methods, fairness, freeze,
  results with uncertainty, mechanisms, failure modes, negative findings, limitations),
  compute accounting, references (keep ManipTrans and Frau-Alfaro), and the AI-assistance
  disclosure: **all AI assistance was Anthropic Claude via Claude Code; no other AI
  coding assistant was used.** Visually inspect every PDF page.
- Update `report/final/overview_template.md` and `scripts/final_review_build.py` so the
  project overview summarises V1–V5 (keep it ≤ 8 pages; keep all existing V4 caveats).
- Update the deck: `report/v5/slides.{pptx,pdf}` with speaker notes, 12–18 slides,
  numbers audited against generated data.
- Videos under a frozen `configs/v5/video_rule.json` written before rendering: Study A
  matched fixed vs calibrated on a grasp-15 case; Study B one-shot calibrated vs tracking vs
  history on the same slip case; at least one Study B failure; a no-slip control; plus a
  montage and `videos.json` index with method/seed/case/checkpoint/outcome. Replayed
  outcomes must equal evaluation outcomes; disclose any mismatch.

## 5. Artifacts, release and publication

Keep in Git: source, suites, frozen manifests, selection records, matrix index, summaries,
tables, figures, decision log, run index, compute record, test evidence. Never commit
binary checkpoints or large logs.

Release `v5.0.0` (tag at the delivery commit; distinct from `experiment-v5a/b`) must
contain, split within GitHub asset limits:

- every saved checkpoint of every formal, pilot, smoke and resumed run (intermediate and
  abandoned attempts included) with `checkpoints.json` (run, profile, seed, transitions,
  role, source SHA, config hash, file SHA256, asset name, archive member);
- raw records for probe, development, validation, final, mechanisms, repeatability,
  regression and Study A (primary and repeat), traces, training/evaluation logs and curves;
- report (md/pdf), slides (pptx/pdf), speaker notes, videos and montage;
- source archives of `experiment-v5a`, `experiment-v5b` and the delivery tag;
- `release_manifest.json`, archive-member inventories, `SHA256SUMS`, `RELEASE_NOTES.md`,
  `REPRODUCE.md`, `VERIFICATION.md`.

Scan all public text and archive names for credentials, private hosts and absolute paths,
and for accidental simulator redistribution. Do not modify any v1–v4 release.

## 6. Public verification and close-out

In a new empty directory without access to the original run outputs: anonymously download
every v5.0.0 asset; verify checksums, safe archive paths and member inventories; resolve
every checkpoint index entry; regenerate all Study A and Study B tables/figures from the
downloaded raw records and compare byte-for-byte (explain any float-only difference);
replay a small set of cases (include one Study A anchor and one Study B learned policy),
reload one checkpoint of every architecture, and run a two-iteration resume. Rerun the
CPU test suite in a fresh clone of the tag. Commit the transcript, exit codes and
`results/v5/public_verification.json` after publication. Fix bundle errors only with a
new version.

Then: update `README.md` (V5 entry point and findings), `AGENTS.md` (no active
assignment), mark this file historical at the top, set `V5_STATUS.json.complete` true only
when every gate above passed, open a PR from `study/v5-calibration-slip` into `main` and
merge it (no force-push), and confirm `main` shows the V5 README.

The final English message must link: the source commits/tags, release v5.0.0, report,
slides, Study A and Study B summary metrics (primary contrasts with intervals and the
decision-rule outcome), the checkpoint index, the video index, public verification, GPU
hours used, and any unmet requirement with its reason.
