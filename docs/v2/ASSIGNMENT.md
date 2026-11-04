> Archived copy of the follow-up assignment (README of commit `a3bb983`). Text unchanged; relative links were rewritten to resolve from `docs/v2/`.

# Robust Bimanual Handover — Execute the Follow-up Study

**Geometric Coordination and Residual Reinforcement Learning for Robust Bimanual Handover**  
CSCI 645 Robot Manipulation, Fall 2026 · Yan Wen  
Repository: https://github.com/ywen0511/CSCI645-Project

## Start here: the assignment is to finish and publish

**Remote agent: execute this README end to end. Audit the completed v1 study, implement and run the diagnostics and component ablations below, complete a bounded v2 training/evaluation study, write the evidence-based report, and publish all source and experimental artifacts in a new GitHub Release.** Reading this README is the owner's only required handoff. Follow its repository links yourself. Do not require the owner's local files, previous conversations, screenshots, or further explanations of the scientific goal.

The earlier project has already been implemented and published. This is a new follow-up assignment, not an instruction to start from a scaffold or repeat all v1 training. At the time this brief was written, `STATUS.json` said `completed`; that describes **v1 only**. Initialize a distinct follow-up status before working. Completion of v1 does not satisfy this assignment.

Continue through analysis, packaging, upload, and independent download verification. Do not stop after a plan, code changes, CPU tests, a pilot, a submitted cluster job, or a draft release. Lack of improvement is a valid scientific result and is not a reason to stop. An unavailable resource or credential is a blocker to record accurately, not permission to claim completion.

All repository text, reports, metadata, code documentation, release notes, and execution progress updates must be in English.

## Authorization, scope, and precedence

The owner authorizes routine project implementation/debugging, isolated dependency installation, experiments on already available compute, commits and pushes to this repository, new project tags, and upload/publication of checkpoints, results, videos, and reports. These steps do not require repeated confirmation. Do not purchase compute, alter account/security settings or repository visibility, erase unrelated data, force-push shared history, or replace published releases/tags.

Start from the latest `impl/handover` branch and create a follow-up work branch, preferably `study/v2-diagnostics`; resume that branch if it already contains this assignment's work. Inspect existing changes before proceeding and preserve other contributors' work. Push meaningful milestones and leave the final README pointing to the final source branch, immutable source tag, and release. Opening a PR to the default branch is authorized; merging is not needed for delivery. The final source must be reachable remotely, not only in an unmerged local checkout.

This README is the owner's updated scientific assignment. Where older execution prompts describe v1 budgets, selection rules, completion status, or output locations, the follow-up requirements here take precedence. Preserve the old documents as historical context and clearly distinguish the v2 addendum. Read [AGENTS.md](../../AGENTS.md), [PROJECT_SPEC](../../docs/PROJECT_SPEC.md), [EXPERIMENTS](../../docs/EXPERIMENTS.md), [IMPLEMENTATION](../../docs/IMPLEMENTATION.md), [RUNBOOK](../../docs/RUNBOOK.md), and [RELEASE](../../docs/RELEASE.md); retain their applicable integrity and implementation requirements. Read the archived [original execution brief](https://github.com/ywen0511/CSCI645-Project/blob/4314a0fa6aac360b10300ad3cff8739822c128f0/README.md) if needed. No local proposal access is required: the submitted proposal is in [proposal/](../../proposal/).

**Keep the research scope:** two Franka Panda arms, two-finger parallel-jaw grippers, one rigid bar, simulated handover, Isaac Sim **through Isaac Lab**, PhysX physics, and a bounded three-dimensional receiver position residual trained with PPO. Keep orientations fixed. Do not switch to dexterous hands, another simulator, vision, real hardware, or a new task. A different renderer for videos is acceptable only if physics remains unchanged and this is documented.

## What already exists and what needs explaining

| Existing artifact | Location |
|---|---|
| Immutable v1 release, including raw results and checkpoints | [v1.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v1.0.0) |
| Exact v1 experiment source | [experiment-v1](https://github.com/ywen0511/CSCI645-Project/tree/experiment-v1), commit `7a64505a08fbaa8f0308cc87bcff46ad2c35cb96` |
| v1 report and results | [report/report.md](../../report/report.md), [primary](../../results/summary/primary/), [secondary](../../results/summary/secondary/) |
| Setup and reproduction | [SETUP_REMOTE](../../docs/SETUP_REMOTE.md), [REPRODUCE](../../docs/REPRODUCE.md), [ENVIRONMENT](../../docs/ENVIRONMENT.md) |
| Calibration and release evidence | [DECISIONS](../../docs/DECISIONS.md), [RELEASE_VERIFICATION](../../docs/RELEASE_VERIFICATION.md) |
| Frozen v1 protocol | [configs/frozen/protocol.json](../../configs/frozen/protocol.json) |

The reported v1 platform is Isaac Lab v3.0.0 / Isaac Sim 6.2.0.0 / RSL-RL 5.5.1 on A100-40GB. Verify actual availability and compatibility from installed packages and official documentation before running; do not silently upgrade the experiment environment. Nine PPO runs completed 10,027,008 transitions each. Primary evaluation contains 19,800 episodes: 1,800 shared cases for two deterministic controllers and nine learned-policy runs. These are archived claims to verify, not newly executed results.

The frozen v1 selector chose the **untrained step-0 policy in eight of nine runs** because validation success was saturated and the tie-break favored the earliest step. Never describe those primary combined results as evidence of a trained-policy benefit. In the separately declared final-checkpoint analysis, stress success was nominal 47.8%, geometry 93.3%, residual 55.8%, combined 89.9%, and combined without phase 90.3%. The reported combined-minus-geometry difference was -3.4 percentage points, 95% CI [-6.3, -1.1].

There is a known presentation inconsistency to audit: v1 README/report labels say 1,400 in-range and 400 stress cases. The frozen nine-condition suite instead contains **1,200 non-stress cases including clean, and 600 stress cases**, 200 per condition. Reconcile from raw case IDs and analysis code; do not infer that every metric is wrong from this labeling error.

The scientific questions for this follow-up are:

1. Are the v1 artifacts and reported conclusions reproducible, and are there measurement or aggregation defects?
2. Does a learned residual provide useful state-dependent correction beyond zero, random initialization, and a tuned constant offset?
3. How much do alignment, shared-holding anchoring, and contact-gated release each contribute?
4. Does the conclusion depend on the geometric correction bound?
5. Under a preregistered, harder but feasible training/validation distribution, does residual learning add robust value over a strong geometry controller?

## Execution order and required outputs

All paths under `docs/v2/`, `configs/v2/`, `results/v2/`, and `report/v2/` below are **deliverables to create**, not files assumed to exist. Keep v1 frozen files and archived assets intact. Existing scripts are reusable starting points; inspect their actual `--help` and implementations before use. Implement missing options, methods, and orchestration instead of pretending the current CLI already supports this study.

### Stage 0 — Preflight, recovery, and status

1. Inspect Git state, existing releases, current status, disk, installed simulator assets, NVIDIA driver/GPU/memory, and available scheduler/compute allocation. Verify GitHub write and release-upload capability without exposing credentials. Read the setup/reproduction documents. Use an isolated environment and pin exact versions and physics backend.
2. Download v1.0.0 assets, verify checksums and archive inventories, and build an index of source SHAs, checkpoints, suites, and run metadata. Use a separate clean checkout for v1 replay so follow-up edits cannot change its behavior.
3. Create `docs/v2/PLAN.md` with stage order, compute estimate, budgets, output locations, and proposed diagnostic protocol. Update `STATUS.json` to distinguish `v1_completed: true` from follow-up stage, completed steps, next actions, blockers, active jobs, source SHA, and artifact locations. Maintain `docs/v2/DECISIONS.md` with UTC timestamps and evidence.
4. Run applicable CPU checks and a simulator smoke test. Reproduce nominal and geometry clean success and the negative controls: no receiver, giver never releases, and table-supported object must not count as successful independent receiver holding.

### Stage 1 — Audit v1 before changing scientific behavior

Write `docs/v2/AUDIT.md` with each check, evidence, conclusion, and any correction:

- Reconcile condition groups, unique case IDs, scheduled/recorded counts, invalid resets, errors, checkpoint hashes, selected transition counts, and primary versus secondary analyses. Regenerate the main v1 tables from downloaded raw records. Verify the 1,200/600 grouping.
- Replay a fixed, recorded sample of archived checkpoints in separate processes, including untrained and trained policies. Include cases near failure boundaries. Compare terminal reasons, contact/holding traces, and batch sizes. Report disagreement rates; do not promise bitwise GPU-physics replay.
- Inspect action scaling, normalization at evaluation, geometry composition, anchoring, release timing, reward and termination order, reset retries, timeout bootstrapping, and per-environment state isolation. Confirm that any reported episode return includes the terminal step reward; inspect the interaction between `_get_dones`, `_collect_records`, and `_get_rewards` rather than assuming it does. Determine whether any defect affects only logging or also training/selection/outcomes.
- Confirm success requires two continuous seconds of receiver-only holding, giver open and no giver/table support, using the shared evaluator. Verify physical signals with traces and negative controls, not just mocked tests.
- Generate an errata document, `docs/v2/V1_ERRATA.md`, including the case-count labels and any additional verified issues. Correct current working documentation/report sources where appropriate, with an explicit correction note. Never overwrite v1 tags, published report assets, or raw records. Put corrected historical presentations in the new release.

If a bug changes physics, rewards, resets, observations, success logic, or selection, document its impact and use a new versioned protocol. Preserve original v1 results and identify which comparisons require rerunning all affected methods. Do not silently mix corrected runs with original runs.

### Stage 2 — Diagnose residuals without retraining everything

Before collecting new comparative results, commit `configs/v2/diagnostics.json` and a fixed diagnostic development suite. Use fresh development cases (default seed `6453028`, 50 cases per v1 condition = 450) and record suite hashes. It is acceptable to use already-seen v1 results as development evidence; they are no longer unseen test evidence for this follow-up.

Run these controls on identical cases and settings:

| Controller | Definition |
|---|---|
| Nominal | Original fixed script, no geometry, zero residual |
| Geometry + zero | Full geometry, explicitly zero residual |
| Geometry + initialization | Each archived combined step-0 policy, seeds 11/22/33 |
| Geometry + trained | Each archived combined final policy, seeds 11/22/33 |
| Geometry + constant | A fixed Cartesian offset selected on development cases only |
| Nominal + constant | Same constant-offset search procedure without geometry |
| Residual checkpoints | Archived residual step-0 and final policies, seeds 11/22/33 |

For constant controls, use an initial one-dimensional x-offset grid of -5 to +5 mm in 1 mm increments (y=z=0), motivated by the documented palm-contact boundary. Freeze the grid before evaluation and retain all candidate scores. Pick by success, then fewer collision episodes, then smaller absolute offset, then ascending signed offset. Use the identical residual bounds, control frequency, and target composition as the learned policy. Do not tune constants on validation or final test. Any expanded grid is a separate, documented pilot decision within the budget.

Report per-condition success/drop/collision/timeout counts, offset sensitivity, and policy-minus-zero and policy-minus-constant paired differences. For representative predeclared case IDs, save time series of observations, raw action, bounded residual, nominal/candidate/executed targets, geometry correction and clipping, grasp error, contact forces, stability, release request/command, reward components, and independent-hold timer. Plot signed x/y/z residuals, not just action norms. Relate action variation to object offset and failure location. If the behavior is explained by a constant bias, say so.

Use deterministic policy inference with frozen normalization. Separate action magnitude from the effect that survives geometry and workspace clamps. Publish `report/v2/diagnostics.md`, trace data, generated figures, and all evaluation records.

### Stage 3 — Geometry component ablations and bound sensitivity

Implement independent flags for alignment (A), shared-holding anchor (H), and release gate (G). The full A+H+G configuration must reproduce the original geometry behavior; verify this before comparing ablations. Keep the same observations available, physical scene, nominal schedule, residual=0, evaluator, and case suite across these controls.

Evaluate the eight deterministic combinations: none, A, H, G, A+H, A+G, H+G, and A+H+G. Define disabled components precisely: no alignment adds zero correction; no anchor uses the current candidate/nominal target; no release gate follows the scheduled release request. Contact measurements used by enabled components remain available. These are implementation ablations, not claims of equal information requirements.

Evaluate full geometry with per-axis alignment bounds 0.005, 0.010, 0.015, and 0.020 m. Include the existing 0.010 m setting and the previously strong 0.015 m development setting. Keep other parameters fixed. Preserve results even if a larger bound solves every case. **Do not weaken geometry to manufacture an RL advantage.**

Run development diagnostics now. Before final evaluation, freeze the ablation matrix and bound values and repeat them on the new held-out v2 suite without choosing the reported configuration from test scores. Reuse identical deterministic records where configurations are exactly equal; index the reuse explicitly. Report conditional effects and interactions rather than attributing the full geometry gain to a single component. Deliver `report/v2/geometry_ablation.md`, tables, plots, and raw records.

### Stage 4 — Design, pilot, and freeze v2

V2 training is part of the assignment. Proceed after correctness checks pass; it does not require a positive pilot result or further owner approval. A ceiling effect or a negative learning result is a result to report. Do not use it to skip the final experiment.

Write `docs/v2/PROTOCOL.md` and `configs/v2/protocol.json`. Start with these bounded defaults, adjust only on development/pilot evidence, then freeze:

- Preserve the single bar, fixed orientations, 3D residual (2 cm per axis), contact-based evaluator, and PPO implementation. Keep the original 1 cm full-geometry controller as a historical control and a 1.5 cm full-geometry controller as the default stronger comparator. Any different stronger comparator must be chosen on development evidence and committed before final runs; include the specified bound sweep regardless. Re-run the constant-offset development search with the chosen stronger geometry setting and freeze that matching constant for the primary combined-versus-constant comparison; retain the original-setting constant as a diagnostic control.
- A harder curriculum starts at clean/small offsets and reaches uniform translation offsets of +/-2 cm per axis and release offsets of +/-0.30 s. The previous +/-1 cm distribution is already solved by geometry. Inspect reset feasibility, physical solvability, geometry saturation, and failures before freezing. If necessary, select the largest feasible range from 1, 1.5, and 2 cm using development evidence, record the reason, and do not silently change the task.
- Keep a common training distribution, transition budget, reward definition, physical parameters, and action bounds across residual, combined, and combined_no_phase. Combined and combined_no_phase use the same stronger geometry controller. The latter masks only the four explicit phase channels; state that raw contact/timing information remains available.
- A change to reward weights or residual initialization must be motivated by Stage 2 evidence, use at most two clearly specified pilot configurations, and apply consistently where applicable. A zero-mean actor initialization can be tested, but do not confuse zero policy mean with zero stochastic training actions. Do not add unrelated algorithms or broad hyperparameter searches.
- Reserve separate suite seeds: development `6453028`, validation `6453027`, final `6453026`. Check disjoint case IDs and sampled continuous perturbations where applicable. Repeated clean/timing-only deterministic scenes are repeats, not independent physical diversity. New test samples address case reuse; they do not make the research hypothesis independent of v1 findings. Disclose that v2 is informed by v1.
- Validation: 400 fixed cases, balanced across clean/in-range and harder feasible position/timing combinations. Include cases that can distinguish controllers; quantify saturation on development/proxy checks. Do not inspect final-policy test results to alter validation.
- Default final suite: the original nine condition structures with 200 cases each, but fresh random draws. It includes clean, position +/-1 cm and +/-2 cm, timing +/-0.15 s, joint +/-1 cm with +/-0.15 s, and joint +/-2 cm with +/-0.30 s. Add three 200-case extrapolation conditions at +/-3 cm: position only, joint early (-0.45 s), and joint late (+0.45 s), **only if development feasibility checks pass before freeze**. Otherwise record their exclusion and retain all nine core conditions. The core's old stress conditions may now be in-training-distribution; label each condition by its actual v2 relation to training rather than reusing misleading OOD labels.
- Pilot training budget: at most 15M aggregate environment transitions including smoke training. Pilot seeds 101/102, distinct from final seeds. Prefer short single-seed comparisons; do not rerun all nine final runs during tuning. Record every pilot, including unsuccessful ones.
- Final training: methods residual, combined, combined_no_phase x seeds 11/22/33 = nine runs, each 10M requested transitions rounded to whole rollouts. Count reset/settling steps explicitly as in v1 and also report scored/control-active transitions. Do not increase the budget merely because combined fails to win.
- Checkpoint selection: retain step 0 as a named untrained control, **exclude it from the trained-policy candidate set**. Candidates are the first checkpoints at or after 2M, 4M, 6M, 8M, and 10M transitions. Select by highest validation success, then lowest collision-episode rate, then lowest mean bounded residual squared norm over scored steps, then latest transition count. Verify that all required metrics are well-defined and implement the exact rule before freeze. Report all candidate scores and ties; do not claim that excluding step 0 fixes validation saturation.
- Evaluate both the selected trained checkpoint and the final checkpoint for every run as separately declared analyses. If they are the same file, reuse records with explicit provenance. The final-checkpoint analysis is mandatory, not triggered by whether the primary result looks favorable.

Before final runs, publish the protocol, case manifests/hashes, exact environment lock, source SHA, method flags, constants selected on development, statistical analysis plan, and video selection rule in a clean source commit tagged `experiment-v2` (or an unused versioned successor if that tag exists). Test fixtures or development runs may exercise final-suite generation/format, but do not use final outcomes for tuning. A post-freeze behavior change requires a new version and rerunning affected comparisons, not editing frozen files in place.

The initial budget is 105M training transitions total (15M pilot + 90M final, plus documented rollout rounding). Estimate evaluation/replay overhead from measured throughput and available allocation. Do not provision paid resources or leave unbounded jobs. If resources cannot support the fixed final matrix, preserve results and record a concrete incomplete requirement; do not silently reduce seeds or episodes and call the study complete.

### Stage 5 — Final evaluation and analysis

Evaluate on the frozen v2 suite: nominal; historical full geometry; stronger full geometry; both development-selected constant controls with their documented geometry setting; the eight component combinations and four alignment bounds; all selected and final learned policies; and the three untrained combined initializations from the v2 runs. Deduplicate exact deterministic configurations and selected=final checkpoint files transparently. Generate an explicit evaluation manifest and expected counts from this matrix before launching jobs; reconcile it against recorded episodes afterward.

Use the same case realizations and shared evaluator. Log scheduled, recorded, duplicate, missing, invalid-reset, infrastructure-error, success, drop, collision, and timeout counts. Preserve every attempted case and retry reason. Report invalid reset rates and both valid-case and scheduled-case success so excluded failures cannot inflate performance. Use per-seed summaries and paired case comparisons, with seed-aware uncertainty for learned methods; do not treat three policy seeds times the same cases as independent training replicates. Retain condition-level results and equal-condition summaries so clean repeats cannot conceal difficult failures.

Primary questions: trained combined versus its matching stronger geometry controller; trained combined versus geometry plus a development-selected constant; residual versus nominal and nominal plus constant; combined versus combined_no_phase. Also report the geometry component and bound comparisons. Use confidence intervals, effect sizes, and explicit exploratory labels for additional comparisons. Document limits from three seeds, multiple comparisons, privileged state/contact observations, and simulation-only evidence.

The report must distinguish original v1, corrected v1 presentation, development diagnostics, v2 pilots, v2 selected checkpoints, v2 final checkpoints, and untrained controls. Never blend them into one headline number. Explain mechanisms with traces and failure examples. A supported conclusion that strong geometry is sufficient and residual RL adds no measurable benefit is an acceptable final outcome.

### Stage 6 — Report, videos, packaging, and publication

Create a complete English `report/v2/report.md` and rendered PDF with methods, protocol deviations, results, uncertainty, learning curves, geometry ablations, constant controls, failure analysis, limitations, and reproduction instructions. Include a concise presentation deck (PDF plus editable source) explaining the task, methods, main comparisons, negative findings, and demo. Check rendered report/deck pages for clipping, missing figures, and inconsistent numbers; derive tables from machine-readable summaries. Verify cited references, preserve upstream attribution, and disclose actual software reuse and AI assistance. No course rubric, final template, or AI-use policy was supplied; do not invent requirements or claim compliance with unseen rules.

Publish at least ten MP4 demonstrations, including matched-case controller comparisons, a timing failure rescued by release gating, an alignment-bound example, and trained-policy successes/failures where present. Freeze a deterministic selection rule before final outcomes (for example, lowest case ID satisfying each specified outcome category). If a requested outcome category is empty, state that and select a declared fallback; do not invent a failure or hide one. Record source SHA, protocol/suite hashes, method/seed, checkpoint hash, case ID, renderer, original evaluation outcome, replay outcome, and replay command for every video. Physics must match evaluation. Explain any replay disagreement.

Create/update executable orchestration so a fresh agent can run or resume stages and regenerate every figure/table. Deliver `docs/v2/REPRODUCE.md` with exact tested commands for setup, download, verification, one deterministic episode, one policy replay, all diagnostic stages, pilot/final training, evaluation, analysis, videos, report, and packaging. Separate existing commands from newly implemented ones. A resume must skip only artifacts that pass hashes/config/source checks, detect incomplete jobs, and avoid mixing protocols. No command may depend on the owner's desktop path.

Publish a **new** final release, default `v2.0.0` if unused. Do not overwrite `v1.0.0`, `experiment-v1`, or an existing v2 release. If this assignment has already been completed, audit the existing delivery and repair missing pieces through a new version instead of duplicating all experiments.

The release must contain all of the following:

- Complete source reachable through immutable tags, plus environment lock, frozen configurations/suites, executable reproduction instructions, decision log, audit, errata, and deviations.
- All raw episode records for diagnostics, ablations, validation, selected/final test evaluation, replays, and negative controls; all pilot/training logs and machine-readable run indices, including failed or resumed attempts.
- **Every periodic checkpoint from every v2 training run**, step 0, selected, final, and resumable/latest checkpoints; also retain pilot checkpoints and logs, grouped and labelled separately. Include actor/critic, normalization state, optimizer/training state needed for resume, transitions, seed, method, schema, and source/config hashes. Deduplicated files are allowed only with complete index mappings. Existing v1 assets can be referenced by immutable URL/hash rather than uploaded twice.
- CSV/JSON summaries, analysis scripts, figures, diagnostic traces, Markdown/PDF report, presentation PDF/editable source, all videos and sidecars.
- `runs.json`, `checkpoints.json`, `videos.json`, `manifest.json`, archive member inventories, and `SHA256SUMS`. Every expected run and checkpoint must resolve to an uploaded asset/member; explain unavailable artifacts rather than silently omitting them. Split archives within GitHub's current asset limits. Do not commit large binaries into normal Git history.

Prefer a draft release while assembling, then publish after local validation. From a fresh directory download the **published** assets, verify sizes/hashes/archive inventories, regenerate figures/tables from downloaded raw records, and replay at least one selected and one final checkpoint for each learned method (include each seed across the sample), plus deterministic baselines. Check a documented sample of boundary cases in separate processes and report replay agreement. Decode every delivered video and verify index links. Confirm public accessibility without relying on the uploading session. Write `docs/v2/RELEASE_VERIFICATION.md` with commands, environment, counts, differences, and final URLs. A published but unverified release is not complete.

## Completion checklist

- [ ] Preflight and simulator/negative-control checks passed; v1 remains intact.
- [ ] v1 artifacts audited, 1,200/600 labels reconciled, errata and any impact analysis published.
- [ ] Zero, untrained, trained, and constant-offset controls completed with traces and raw data.
- [ ] Geometry component ablations and bound sensitivity completed on development and held-out v2 cases.
- [ ] Bounded pilots completed; v2 source/protocol/suites/selection/analysis frozen before final runs.
- [ ] Nine final training runs complete; all checkpoint candidates validated; selected and final policies evaluated.
- [ ] Evaluation manifest reconciled; uncertainty, failures, exclusions, and negative findings reported.
- [ ] Report, presentation, figures, and at least ten provenance-linked videos rendered and checked.
- [ ] All source, raw results, logs, checkpoints, configs, and artifact indices uploaded to a new published release.
- [ ] Fresh download, hashes, table/figure regeneration, video decoding, and checkpoint replay verified.
- [ ] README and STATUS updated with actual follow-up findings, source/tag, release, and remaining limitations.

Keep the execution contract in the final README or link an archived copy. Mark the follow-up complete only when every required item is fulfilled. If blocked, save exact resume commands, job/checkpoint state, completed artifacts, blocker evidence, and the smallest missing external capability; do not label a partial release as a completed study.

Your final message to the owner must link the final source commit/tag, release, report, presentation, summary tables, checkpoint index, video index, and reproduction guide. State the main findings, whether learning improved on strong geometry and constant controls, verification results, and every unmet requirement. **The requested deliverable is a completed, uploaded, reproducible study, not another proposal.**
