# V4 verification record

Two releases: **v4.0.0** (all study data: checkpoints, raw records, logs, videos, report, slides) and **v4.0.1**
(delivery patch: the GPU verification stage missing from v4.0.0; data unchanged). Experiment source of every formal run:
`experiment-v4` = `aac4d98274814b1ab121a715db71187e3e1cc0b9`. Machine-readable evidence: `results/v4/verification/`.

## 1. Release-candidate check (2026-11-10, before publishing v4.0.0)

Built with `scripts/v4_package.py` from clean checkouts of `v4.0.0` (`0160e37`) and `experiment-v4` on the GPU cluster.
The first candidate failed its own leak scan (306 hits: the user name inside node temporary paths, missed by a
word-boundary pattern); it was rebuilt with a corrected pattern and never uploaded. Second candidate:

| check | result |
|---|---|
| assets | 30 (468.6 MB); `SHA256SUMS` lists 29, 0 bad, 0 unlisted; manifest covers all other assets |
| archive members | 5,007 re-hashed, 0 problems, safe paths |
| checkpoints | 424 index entries resolve; 25 formal runs × (step 0, 10 periodic, final, latest, selected) |
| raw records | 54 final files × 2,400 = 129,600; 150 validation files × 240 |
| media / documents | report.pdf 12 pages, slides.pdf 16 pages, slides.pptx 16 slides |
| leak scan | 0 hits (text members, member names, loose JSON/MD) |
| regeneration | 35 of 35 JSON/CSV byte-identical; 8 of 8 figures byte-identical |

All 30 assets were uploaded from the cluster and reconciled with GitHub (name, size, SHA-256) before the draft was
published (05:08 UTC).

## 2. Public-download verification of v4.0.0 instructions (05:09–05:12 UTC) — sections 1–2 passed, section 3 failed

From a new empty directory with public clones only and an anonymous download: `SHA256SUMS` OK, verifier ok, 35/35
tables and 8/8 figures identical. Section 3 stopped at once: tag `v4.0.0` did not contain
`results/v4/jobs/verification.json` (generated stage missing). Fixed in a new delivery tag `v4.0.1` (no tag moved,
no asset replaced; see `docs/v4/DECISIONS.md`).

## 3. Public-download verification with v4.0.1 instructions (05:19–05:26 UTC) — passed

New empty directory; `docs/v4/REPRODUCE.md` sections 1–3 executed verbatim from the `v4.0.1` copy (job script:
`results/v4/verification/fresh_job.sh`; transcript: `fresh_transcript.log`); clones of `v4.0.1` (`c561eb4`) and
`experiment-v4` (`aac4d98`) from the public URL, no credential helper; anonymous download of all 30 v4.0.0 assets
and all 6 v4.0.1 assets.

| step | result |
|---|---|
| `sha256sum -c SHA256SUMS` (v4.0.0 and v4.0.1) | all OK |
| `v4_verify.py` | ok: 5,007 members re-hashed, 424 checkpoints resolved, 25 complete formal runs, 54 × 2,400 final and 150 × 240 validation records, 11 MP4s decoded (10 clips + montage), report 12 pages, slides 16, 0 leak hits |
| `v4_regen.py` | 35 of 35 tables byte-identical, 8 of 8 figures byte-identical |
| GPU replay (60-case subset, batch 20) | geometry_calibrated 60/60 and combined_robust_history_s111 (selected) 60/60 terminal outcomes equal the published batch-240 records |
| reload (12 cases, one selected checkpoint per architecture) | 60/60 equal for all five profiles |
| comparator (`v4_fresh_compare.py`) | ok: exact case-ID sets, no duplicates, 0 invalid resets, identical sensor/grasp specs, checkpoint SHA-256 and config hashes; 0 mismatches |
| resume (two PPO iterations into a new directory) | counters, optimizer, normalizer and RNG restored and advanced; reload identical; released `latest.pt` SHA-256 unchanged (`a7dade5c…`, equal to the checkpoint index) |
| repeated runner | 9 of 9 tasks skipped after content verification |

Compute for the whole continuation, including both public verifications: `results/v4/compute_final.json`
(16.18 A100 GPU-hours; the report's 16.0 was computed before the verification jobs).
