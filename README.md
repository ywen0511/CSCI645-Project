# Robust Bimanual Handover — Complete the Final Delivery

**CSCI 645 Robot Manipulation, Fall 2026 · Yan Wen**  
Repository: https://github.com/ywen0511/CSCI645-Project  
Starting branch: `study/v2-diagnostics`

## Remote agent: this is your complete execution assignment

**Complete every stage below and publish the verified final delivery. This README supplies the owner's full task instruction: no additional task prompt, local file, conversation history, scientific choice, or routine approval from the owner is needed.** Inspect the repository and linked evidence yourself. Implement the repairs, run the required verification and supplementary evaluation, update the report and presentation, upload every required artifact, publish a new GitHub Release, and verify it from a fresh download. Do not stop at a plan, a list of issues, a code patch, a submitted job, or an unpublished release.

This is the **final reproducibility and reporting closeout of the completed v2 study**. The previous `STATUS.json` and README describe v2.0.0 as completed; that does not mark this new assignment complete. Preserve the earlier results and add a separate `delivery_closeout` status. A negative result is acceptable. The goal is a correct, accessible, reproducible delivery, not a forced improvement by reinforcement learning.

All project documentation, reports, logs intended for delivery, release notes, and progress messages must be in English. Preserve upstream attribution and disclose actual software reuse and AI assistance. No course rubric or AI-use policy has been supplied; do not invent requirements or claim compliance with unseen rules.

## Authorization and boundaries

The owner authorizes project code/documentation fixes, isolated dependency setup, evaluation on already available compute, commits and pushes to this repository, new tags, and upload/publication of all project artifacts and GitHub Releases. Perform routine decisions and these actions without requesting another instruction. Do not purchase compute, change account/security settings or repository visibility, expose credentials, force-push shared history, erase unrelated work, or overwrite published tags/releases.

Work from the latest `study/v2-diagnostics`, preserving concurrent changes. Commit and push milestones to this branch; use an isolated worktree if necessary. Keep the two Franka arms with two-finger parallel-jaw grippers, one rigid bar, fixed orientations, Isaac Sim through Isaac Lab, PhysX, and the existing bounded 3-D residual PPO task. Do not start a new v3 research program, change the benchmark to make RL win, or retrain the nine completed runs merely to produce new artifacts.

This README is the updated owner assignment. Its closeout scope and completion rules supersede historical execution briefs that ask to start v1/v2 training again or stop at v2.0.0. Retain applicable integrity rules in [AGENTS.md](AGENTS.md). The full requirements are specified here; linked documents supply existing implementation details and evidence, not missing decisions for the owner to make.

If an actual external capability is missing, complete independent work, preserve exact resume state and commands, and record the concrete blocker. Never fabricate execution or mark incomplete requirements complete. Missing GPU access or upload credentials cannot be solved by documentation alone, but ordinary implementation choices and unfavorable results are not blockers.

## Starting evidence and exact versions

| Purpose | Existing reference |
|---|---|
| v1 historical experiment | `experiment-v1`, commit `7a64505a08fbaa8f0308cc87bcff46ad2c35cb96` |
| v1 published artifacts | [v1.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v1.0.0) |
| v2 immutable experiment source | `experiment-v2`, commit `1d9d0e23eec346c1b1cb3c0c245a1e772df7bedf` |
| v2 original release source | `v2.0.0`, commit `86b193a439539dd88a98a0283c06293c0a1ac8aa` |
| v2 original published artifacts | [v2.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.0.0) |
| Reviewed delivery snapshot before this assignment | commit `3a8fe0a9d071fa5cae61939652611cbf349fd790` |
| Existing protocol and decisions | [PROTOCOL](docs/v2/PROTOCOL.md), [DECISIONS](docs/v2/DECISIONS.md), [frozen configuration](configs/v2/frozen/protocol.json) |
| Existing report and tables | [report](report/v2/report.md), [tables](results/v2/summary/tables.md) |
| Existing reproduction and verification | [REPRODUCE](docs/v2/REPRODUCE.md), [RELEASE_VERIFICATION](docs/v2/RELEASE_VERIFICATION.md) |

The v2 records report nine final training runs of 10,027,008 transitions each and 117,600 evaluation episodes on 2,400 shared cases. Headline all-case success: nominal 65.2%, residual 82.6%, geometry 1.5 cm 96.5%, combined 96.1%, geometry plus development-selected +10 mm constant 99.2%. These are existing results to preserve and verify, not new results to claim you ran.

The installed experiment environment was Isaac Lab v3.0.0, Isaac Sim 6.2.0.0, RSL-RL 5.5.1, PhysX, Python 3.12, PyTorch 2.11/CUDA 13. Follow [SETUP_REMOTE](docs/SETUP_REMOTE.md) and the committed lock; verify actual versions and official APIs. Record hardware, driver, package versions, and environment differences. Do not silently upgrade simulation dependencies. CPU analysis/rendering can use a separate pinned environment, recorded independently.

## Stage 1 — Inventory, archive the task, and reopen delivery status

1. Inspect Git state, release/tag metadata, available compute, disk, dependencies, and write/upload capability without exposing credentials. Download v2.0.0 anonymously and verify its checksum and archive inventories. Read the existing audit, errata, report, code, and release verification records.
2. Archive this execution brief verbatim as `docs/closeout/ASSIGNMENT.md`. Preserve the previous scientific assignment in `docs/v2/ASSIGNMENT.md` and the original proposal unchanged.
3. Create `docs/closeout/PLAN.md` and `docs/closeout/DECISIONS.md`. Add `delivery_closeout` to `STATUS.json`, recording actual stage, completed items, active jobs, source commits, blockers, and next actions. Existing v1/v2 completion records remain historical.
4. Create a machine-readable deliverable manifest and run ledger before execution. Every required result must ultimately map to a source revision, command, input hashes, output hashes, and uploaded asset/member. Preserve failed and resumed attempts with explanations.

## Stage 2 — Repair reproduction as an executable workflow

The current reproduction guide starts at `experiment-v2` but later invokes scripts absent from that tag (`build_report_v2.py`, `build_deck_v2.py`, `package_v2.py`, and `verify_v2_release.py`). `v2_nondeterminism.py` is also absent from `v2.0.0` and was added later. Fix the actual workflow, not only these examples.

- Separate an immutable **experiment checkout** at `experiment-v2` for original simulation/training replay from a pinned **delivery-tools checkout** containing every analysis, verification, rendering, and packaging script. Use explicit working directories and argument paths so no command relies on a previous shell's incidental state. Record both full commit SHAs and the roles of each.
- Before running, automatically check every referenced script exists at its specified revision. Verify the supported CLI arguments against implementation and `--help`. Check all relative links and archive names, including the diagnostics document's `raw-dev.tar.gz` reference against the actual `raw-development.tar.gz` asset.
- Provide a top-level executable entry point, `scripts/closeout.py`, or an equivalently documented driver, with stages for download/integrity, CPU regeneration, simulator replay, supplementary evaluation, rendering, packaging, and verification. This is a deliverable to implement, not an existing command. It must support resume, reject hash/config/source mismatches, and run unattended after initial environment setup. Record its exact tested commands in `docs/closeout/REPRODUCE.md` and update `docs/v2/REPRODUCE.md` to point to the corrected workflow.
- Download every needed input from GitHub or official simulator sources. No required step may depend on the owner's desktop, private cluster paths, or artifacts available only on a previous machine. Make cluster wrappers configurable rather than tied to one internal hostname or scheduler.
- Regenerate v2 selection, development/constant/pilot summaries, final tables, ablation results, residual diagnostics, and nondeterminism summaries from downloaded raw records. Compare numerical outputs to the archived version; explain each difference. Lock analysis dependencies. Distinguish harmless float/plot-render differences from changes in counts or scientific conclusions.
- Check the full documentation path, including commands with placeholders: replace placeholders in the copy-paste quickstart with concrete relative paths or variables initialized in that same block. Parameterized reference commands are acceptable only when their parameters and defaults are explicit. Never claim all commands were tested if only an equivalent private wrapper was tested.
- Exercise CPU unit/integrity tests and the shared simulator negative controls. Confirm a clean nominal handover succeeds and no-receiver, no-release, and table-supported cases cannot satisfy independent receiver holding. Record real simulator evidence separately from mocked tests.

Freeze a supplementary-evaluation source commit before Stage 4. Verify that its task/controller/reward/reset/evaluator code is identical to `experiment-v2`, or explicitly identify any nonbehavioral changes. Keep original experiment tags unchanged. If a correctness defect affects scientific outcomes, document its impact and rerun all affected comparisons consistently; never silently blend corrected and historical results.

## Stage 3 — Correct scientific wording and provenance

Revise the README summary, report Markdown/PDF, slides, diagnostic documents, reproduction notes, and new release notes consistently. Preserve archived v2.0.0 assets and identify current corrections in `docs/closeout/ERRATA.md`.

1. Replace claims such as **“phase input has no effect”** with **“no clear effect was detected under this task, observation set, and training budget”**. Raw contact/timing observations remain available; the ablation removes only the explicit four-channel phase label.
2. Limit **“RL is useful only when geometry is absent”** and similar statements to the evaluated task, controller, reward, PPO configuration, and training distribution. The evidence does not establish a general impossibility result for residual learning.
3. Remove the claim that disagreement on a boundary-enriched replay sample is an **upper bound** on overall disagreement. It is an observed rate on a deliberately selected sample, not a proven population bound. Report its selection rule, numerator, denominator, batch sizes, terminal-reason agreement, and success agreement separately.
4. Distinguish the whole-suite zero-policy-versus-controller differences (2/2,400 and 10/2,400 terminal reasons) from the boundary replay result (487/506 terminal reasons; 492/506 success flags). Neither is a universal simulator noise floor. Do not compare a success-rate difference directly with a terminal-reason disagreement rate as though they were the same statistic.
5. Explain that existing seed/case bootstrap intervals do not separately estimate process/batch-layout variability. Treat the approximately -0.4 percentage-point combined-versus-geometry effect cautiously until Stage 4. Keep the much larger comparison against the tuned constant distinct.
6. Clearly label Stage 4 as a **retrospective robustness check on the already-used v2 suite**, not a newly held-out confirmatory experiment. Do not select checkpoints, constants, thresholds, or reportable subsets from these replays.
7. Check every table label, denominator, percentage-point difference, citation, figure caption, and cross-reference. Preserve distinct v1, v2 development, v2 selected/final, and supplementary results. A missing archived smoke checkpoint reported as superseded must remain explicitly disclosed, not converted into an “all checkpoints preserved” claim.

## Stage 4 — Mandatory bounded repeatability evaluation

This is evaluation of existing checkpoints, **not new training or tuning**. Complete it using available compatible GPU resources. Commit `configs/closeout/repeatability.json`, the run manifest, and the analysis plan before collecting these results.

### Fixed evaluation matrix

- Use all 2,400 frozen v2 final cases with their existing IDs, perturbations, and evaluator, and the downloaded, checksum-verified v2.0.0 checkpoints.
- Controllers: (a) full geometry with the 1.5 cm alignment bound; (b) that same geometry plus the already-selected +10 mm x constant; (c) combined selected checkpoint for each of seeds 11/22/33; (d) combined final checkpoint for each of seeds 11/22/33. Do not change any checkpoint or constant.
- Run **three independent process repeats** at each of **two batch sizes: 900 and 23**. Use the same case ordering and paired process seed in each repeat across controllers, recording the three process seeds (default 6454101/6454102/6454103), actual environment layout, GPU, driver, and software versions. Keep deterministic inference and normalization frozen.
- Deduplicate selected/final entries only when checkpoint bytes, controller settings, and case ordering are identical. Preserve role aliases in the manifest. Maximum work before deduplication is 8 entries x 2,400 cases x 3 repeats x 2 batch sizes = **115,200 scheduled episodes**. Run a short throughput check first and document a finite wall-time estimate and scheduler limits. Failed/incomplete jobs may resume with recorded attempts; do not silently shrink the matrix or launch unbounded retries.
- Save all raw records, provenance, stdout/stderr, infrastructure failures, and exact invocation commands. Reconcile scheduled/recorded/duplicate/missing cases and invalid resets per controller, process, and batch size. Do not hide errors in valid-case-only rates.

### Required analysis

For every process and batch size report controller success, drop, collision, timeout, and invalid/error counts; paired success differences for combined versus geometry and versus geometry plus constant; and terminal-reason/success agreement with the archived result. Report selected and final checkpoint analyses separately.

Report the difference's range and direction across repeats/layouts, not only a pooled average. Retain policy-training-seed identity: three process repeats of a policy are not three new trained seeds, and repeated evaluations of one case are not new independent cases. Use paired case resampling with training-seed grouping where applicable, describe exactly how process repeats are handled, and keep batch layouts as separate sensitivity analyses. Never manufacture a narrow interval by pooling all repeated episodes as independent observations.

Produce `report/closeout/repeatability.md`, machine-readable summaries, figures, and an analysis script. If the small disadvantage changes sign or is inconsistent across layouts, describe it as unresolved/sensitive. If it persists, report the observed stability while limiting the claim to tested settings. Report the constant-control comparison independently even if the small comparison is inconclusive. Keep original v2 numbers intact and show supplemental numbers in a separate table.

## Stage 5 — Finish the report, presentation, and demonstration

- Deliver a revised full English report as Markdown and PDF, including the existing v2 methods/results, corrections, supplementary repeatability findings, limitations, and exact reproduction references. Keep the corrected historical v1 report available with its erratum notice.
- Update the presentation as editable PPTX plus PDF. Align all numbers and claims with the report and clearly identify the supplemental evaluation. Preserve the useful existing demo material.
- Deliver at least the ten existing provenance-linked videos. Decode and verify every MP4 and sidecar. Preserve original case-selection rules and outcomes; identify any replay disagreement. If an existing demo or caption is misleading after corrections, regenerate it with recorded provenance rather than silently relabeling it. Do not cherry-pick new examples to hide negative results.
- Render and visually inspect every report/deck page for clipping, missing figures, illegible plots, broken references, and inconsistent values. Include rendering/build commands and dependencies. Numbers must come from machine-readable summaries.
- Produce `docs/closeout/VERIFICATION.md` with actual checks and outcomes. Update progress status as tasks finish; do not mark final delivery verified until the published-download checks below pass.

## Stage 6 — Upload a complete new release

Publish a new release, **`v2.1.0`** if unused, titled “CSCI 645 final delivery: reproducibility and repeatability”. If that version already exists, inspect it and use the next unused patch version for corrections. Never move or overwrite published tags/assets. Push source and small summaries to `study/v2-diagnostics` and create a separate immutable source tag for the supplementary evaluation. The release tag must include every delivery tool and the final report/deck sources.

The new release must be independently usable: **copy the unchanged v2 checkpoint/raw-data archives into it as well as uploading new artifacts**. Retain their original hashes and provenance. Do not make the reader assemble essential inputs from multiple release pages or rely on the old machine. Preserve v1.0.0 and v2.0.0; original v1-only artifacts may remain linked by immutable URL/hash as historical evidence.

Required contents:

| Artifact group | Required files/data |
|---|---|
| Source and environment | Immutable source tags/SHAs, source snapshot or GitHub source archive, dependency locks, setup commands, frozen v2 and supplementary protocols/suites |
| Checkpoints | All available v2 periodic, step-0, selected, final, and resumable checkpoints for all nine runs; pilot/smoke checkpoints and logs; normalization, actor/critic, optimizer/resume state where originally stored; explicit record of the already-superseded smoke artifact |
| Original experimental evidence | All v2 development, pilot, validation, final, audit, negative-control, trace, and training records/logs from v2.0.0, with original provenance |
| Supplementary evidence | Every Stage 4 raw record, process/batch metadata, failed/resumed attempt, trace used in analysis, and job log |
| Analysis | Reproducible scripts, generated CSV/JSON tables, plots, selection histories, corrections, repeatability analysis, and decision logs |
| Documents | Revised report Markdown/PDF, corrected historical v1 report, presentation PPTX/PDF, audit/errata, standalone reproduction and verification guides |
| Videos | All ten or more MP4s, sidecars, original evaluation/replay outcomes, and usable replay commands |
| Indices and integrity | `runs.json`, `checkpoints.json`, `videos.json`, `manifest.json`, archive member inventories, and `SHA256SUMS` covering every uploaded artifact except itself |

Use stable relative paths within archives. Every indexed item must resolve to an uploaded asset/member; deduplicated items need explicit aliases. Preserve roles and distinctions between original v2 and supplemental records. Scan current source and artifacts for credentials/private paths/internal hostnames; redact packaging copies of private paths without destroying provenance. Document known historical path exposure rather than rewriting shared history. Do not redistribute the simulator itself or proprietary assets contrary to their licenses. Keep large binaries in release assets, split archives within current GitHub limits, and verify all parts.

Assemble and locally validate a draft release, upload every artifact, then publish it. Release notes must explain corrected reproduction, scoped conclusions, supplemental findings, retained original results, superseded artifacts, exact source versions, and a minimal tested download/replay command. “Uploaded” is not the completion criterion; Stage 7 is mandatory.

## Stage 7 — Verify the published delivery from scratch

Use a fresh clone and empty download directory, with no cache of the uploaded files as inputs. Fetch the published release anonymously and run the documented entry point. Record:

1. Public accessibility, expected asset count, sizes, SHA-256 hashes, complete archive inventories, and successful index resolution for every required run/checkpoint/video.
2. Exact release/source revisions and availability of every referenced script. Run the copy-paste quickstart in order. Reproduce the error paths and resume behavior of the driver without corrupting real outputs.
3. Regeneration of original v2 and supplemental tables/figures from downloaded raw records. Compare substantive numerical outputs and document dependency-related byte differences.
4. Separate-process replay of at least one selected and one final checkpoint per learned method (`residual`, `combined`, `combined_no_phase`), with seeds 11/22/33 all represented. Use a fixed list committed before replay: first five case IDs in each of the 12 conditions. Include nominal, geometry, and the matching constant control. Compare terminal reasons and success flags to archived records; report disagreement without claiming bitwise reproducibility or a population upper bound. Reuse a checkpoint file for two roles only when its hash is identical and record that reuse.
5. A real resume smoke test from a downloaded resumable checkpoint into a separate disposable run/output directory. Keep original checkpoints unchanged; cap this check at two PPO iterations and exclude it from scientific results. Record restored counters, optimizer/normalization state, and successful saving/reloading. It is a resume check, not additional final training.
6. Decoding all videos; opening all PDFs and the editable presentation; validating report/deck links and generated numbers; verifying all instructions work without private paths or missing files.

Commit the final verification record and status after these checks. A post-release verification commit may be newer than the immutable release tag: state this explicitly and include its permanent URL in the final delivery index/release notes. Do not move the tag. If an artifact repair is needed, publish a new patch release and verify that release again. Completion cannot be achieved by editing the checklist alone.

## Final repository state and completion

Replace the opening of the final README with a concise actual delivery summary and direct links to the new release, final source tags, report, presentation, tables, checkpoint index, video index, reproduction guide, and verification record. Retain this execution contract in `docs/closeout/ASSIGNMENT.md`. Preserve original v1/v2 records and distinguish them from the supplemental study. The default branch may remain historical; prominently identify `study/v2-diagnostics` as the delivery branch rather than merging unrelated work without review.

- [ ] Corrected reproduction works from clean, explicitly pinned source checkouts; all required scripts exist.
- [ ] Original v2 artifacts and summaries verified; substantive discrepancies explained.
- [ ] Scientific claims, denominators, artifact names, and reproducibility wording corrected consistently.
- [ ] Full repeatability matrix completed and reconciled; selected/final and process/training-seed distinctions preserved.
- [ ] Report and presentation rebuilt and visually checked; all videos verified.
- [ ] Every required checkpoint, raw record, log, config, summary, document, and video uploaded to the new release.
- [ ] Published anonymous download passes integrity, regeneration, checkpoint replay, resume, and media checks.
- [ ] Final README, STATUS, verification record, and artifact indices reflect actual completion and limitations.

Your final message must provide working links to the source commits/tags, published release, report, presentation, summary tables, checkpoint/video indices, and reproduction/verification records. State the substantive findings, whether the small combined-versus-geometry difference survives repeatability checks, all remaining limitations, and any unmet requirement. **Finish and upload the complete delivery; do not ask the owner to supply another execution prompt.**
