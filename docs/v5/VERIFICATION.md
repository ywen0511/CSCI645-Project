# V5 verification record

Release **v5.0.0** (all V5 study data: checkpoints, raw records, logs, videos, report, slides). Study A execution source:
`experiment-v5a` = `13cda3af2699f0ebfdd50affb4d27fb6dde877e8`; Study B freeze and execution source: `experiment-v5b` =
`db62bd1dbb3bb077ad4b67f3b3cd934e677db522`. The public-download verification after publication is appended on the branch
(section 3) with its machine-readable record `results/v5/public_verification.json`.

## 1. GPU verification rehearsal (2026-11-18 05:54 UTC, before tagging)

The public-verification GPU stage (`results/v5/jobs/verification_a.json`, `verification.json`) was rehearsed on the
cluster against the original run outputs, from clean checkouts of `experiment-v5a`, `experiment-v5b` and the delivery
commit `9b1fe2b`, so that the tagged instructions are known to run (V4's first tag lacked this stage).

| task | result |
|---|---|
| Study A anchor `ema0p2_cal050_a25` (= V4 `geometry_calibrated`), 60 held-out cases, batch 20 | 60/60 terminal outcomes equal the published batch-240 records |
| `geometry_best` on the 60-case `slip_mixed_id` subset, batch 20 | 57/60 equal |
| `slip_robust_history_s111` (selected) on the same subset, batch 20 | 54/60 equal |
| reload of the seed-111 selected checkpoint of each architecture (7 cases each) | 21/21 equal |
| two PPO iterations resumed from `slip_robust_history_s111/checkpoints/latest.pt` | 306 → 308 iterations; counters, optimizer, normalizer and RNG state checked |
| case IDs, slip/sensor/grasp specifications, checkpoint SHA-256, configuration and controller hashes | all equal |

All 9 outcome differences are slip-validity flips (7 `success` → `invalid_slip`, 2 `invalid_slip` → `success`): the
realized slide depends on the batch layout of the shared PhysX scene. No other outcome changed. The report (Section 8)
states this.

## 2. Release-candidate check (2026-11-18, before tagging)

Built locally with `scripts/v5_package.py` from the delivery commit `e8d1756` and clean clones of both experiment tags;
verified with `scripts/v5_verify.py` and regenerated with `scripts/v5_regen.py` (pinned analysis environment).

| check | result |
|---|---|
| assets | 29 (304.1 MB); `SHA256SUMS` lists 28, 0 bad, 0 unlisted; manifest covers all other assets |
| archive members | 5,297 re-hashed, 0 problems, safe paths |
| checkpoints | 225 index entries resolve; 15 formal runs × (step 0, 10 periodic, final, latest, selected); 6 pilot runs |
| raw records | Study A 10 files × 2,400; Study B final 36 files × 1,400 = 50,400; validation 165 files × 160 |
| media / documents | report.pdf 13 pages, slides.pdf 13 pages, slides.pptx 13 slides; 9 clips and the montage decode |
| leak scan | 0 hits (text members, member names, loose documents) |
| regeneration | 24 of 24 JSON/Markdown tables byte-identical; 6 of 6 figures byte-identical |

The candidate's verifier failed once on a manifest-key mismatch between `v5_package.py` and `v5_verify.py` (fixed in
`cb74e87`; the bundle itself was valid). The tagged release is rebuilt from the tag with the same procedure.
