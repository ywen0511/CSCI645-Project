# Final CPU review of the completed V4 study

Reviewed on 2026-11-10 against branch commit `0cef74fc92007e6e86f4e378b4635f7b4185ec0b`.
This review adds interpretation corrections and retrospective analysis. It does not
change training, checkpoints, frozen suites, original reports, tags or released assets.
Use the [project overview](../../report/final/overview.md) for the current synthesis;
read the archived V4 report and slides with the corrections below.

## What was independently checked

The public v4.0.0 `raw-final.tar.gz` was downloaded and checked against SHA-256
`26b27cd5f9d97f1a6dea85412ecb050aba772eb84fee6bd9a9f18038bf7cf627`.
[The CPU audit](../../scripts/final_review_audit.py) reads the archive without extraction.
[Machine-readable evidence](../../results/final_review/audit.json) records:

- 54 executed files, 2,400 unique expected cases per file, 129,600 total episodes;
  55 logical entries, including the declared calibrated-baseline alias.
- Every executed file hash and expected record provenance field matches its index.
  Every published per-seed and family success rate and invalid-reset count agrees.
- Both selected-checkpoint primary contrasts reproduce at 95% and 97.5% confidence,
  using an independent implementation of the specified paired bootstrap.
- All 78 frozen input hashes match Git blobs at immutable experiment commit
  `aac4d98274814b1ab121a715db71187e3e1cc0b9`.
- All 25 selections match the frozen ranking applied to their recorded validation
  candidate summaries. This check does not independently reload raw validation data.
- The published report Markdown exactly matches its numeric template substitution.
  This verifies rendering consistency, not the truth of every handwritten sentence.

No GPU or simulator was launched. Checkpoint weights were not downloaded or independently
replayed by this review. Prior fresh-public-download replay, reload, resume and full
artifact verification are documented separately in [V4 verification](../v4/VERIFICATION.md).

## Corrections to apply when reading the archived report and deck

| Item | Accurate interpretation | Source / affected material |
|---|---|---|
| Calibration attribution | The final fixed-to-calibrated comparison changes reference, EMA alpha (1.0 to 0.2), and alignment bound (15 to 25 mm). The 5.5% to 94.5% grasp-15 result and +29.0 pp mixed-ID effect compare complete controller configurations; they do not isolate calibration. | `configs/v4/analysis_plan.json`, summary and sections 6.2/12; slides 1/6/14 |
| Matched development evidence | At alpha 0.2 and a 25 mm bound, fixed versus calibrated succeeds in 0/24 versus 24/24 grasp-15 cases, 17/24 versus 24/24 mixed-ID cases, and 18/24 versus 22/24 mixed-OOD cases. This supports the mechanism on development data only. | `results/v4/development/round2_summary.json`; these data helped select the controller |
| Failure threshold | The tested grasp-5 condition changes both x and z to signed 5 mm; grasp-10 and grasp-15 use positive x with signed 10 mm z. These discrete conditions show degradation, not a precisely identified continuous x-only threshold. | `configs/v4/analysis_plan.json` |
| EMA contrast direction | In section 6.2, the contrast is **calibrated minus EMA**: mixed ID -0.5 pp [-1.5, 0.0], mixed OOD +4.0 pp [0.0, 8.5], at 95% confidence. Intervals touch zero; do not claim established superiority. | `results/v4/summary/paired_effects.json` |
| Constant-offset mechanism | On the 60-case subset, a development-fitted constant has at least as many successes as each selected **combined** history policy (60/60/60/60/59 versus 57/58/59/59/55). This is not identical case-level behavior, not a statement about every residual-only policy, and not proof that history is generally useless. | Archived report section 7 and mechanism tables; release wording / speaker notes |
| Project-wide learning result | V2 residual-only learning improved over nominal control, while combined learning did not beat strong geometry. Do not summarize V1-V4 as “RL never helped.” | `report/v2/report.md`, summary |
| Reproducibility counts | The 424 checkpoint count is index entries, including roles/aliases, not necessarily 424 unique weight files. The remote record reports 2,160/2,160 repeatability outcomes but 323/324 trace outcomes, with one discrepancy disclosed. | `docs/v4/VERIFICATION.md`, report section 8 |
| Compute | The report's 16.0 A100 GPU-hours predates final verification; the later full-continuation record is 16.18. | `results/v4/compute_final.json` |
| Related work | Prior work includes dexterous handover; the cited individual paper does not establish that the entire field mainly uses dexterous hands or learned perception. | [Frau-Alfaro et al.](https://arxiv.org/abs/2506.16822), report section 12 |
| AI assistance | Remote implementation/experiments/delivery used an AI coding agent, as disclosed in V4. Local workflow maintenance, this independent audit and synthesis also used Codex. Do not attribute all local code authorship to the owner. | Archived disclosure and this review |

## Reset sensitivity: new, explicitly post hoc

Across 54 executed entries, 380 invalid-reset records occur only at x = -7 mm.
There are 11 case IDs invalid in at least one entry and four invalid in every entry.
The intersection valid in all entries contains 189 paired base cases. We retain exactly
this same intersection for every compared method and training seed; we do not let each
method discard its own failures.

| Selected controller | All 200 cases: success | Common 189: success | Parent on common 189 | Difference on common 189, 95% CI |
|---|---:|---:|---:|---:|
| Robust history | 65.2% | 68.68% | 99.47% | -30.79 pp [-43.60, -18.20] |
| Robust feed-forward | 88.2% | 91.43% | 99.47% | -8.04 pp [-26.14, +1.06] |
| Repeated current frame | 91.2% | 94.81% | 99.47% | -4.66 pp [-14.29, +1.06] |

These intervals use 10,000 paired seed/case bootstrap draws, seed 6456401, conditional
on the fixed retained set. They are exploratory, unadjusted, and do not model uncertainty
from choosing that set. Conditioning on reset validity can introduce selection effects.
The original all-scheduled denominator remains the primary analysis. The history deficit
persists in this sensitivity analysis; invalid resets alone do not explain it.

## Presentation and remaining scope

All 12 archived report pages and 16 slide pages were rendered and checked for gross
clipping or missing content. Dense archived tables remain better read in the Markdown
version. The new concise PDF is a supplement, not a replacement for full methods and
all-condition tables. A large training extension is not needed to complete this study.
The remaining assignment is [final public delivery](../../FINAL_DELIVERY_HANDOFF.md),
with no new GPU experiment required. A matched-configuration held-out calibration
ablation would be a separately planned post hoc study, not a repair to the existing
primary contrast. Dynamic slip, real hardware and new objects remain future work.
