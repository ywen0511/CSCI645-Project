# v3 verification

Two passes:

1. **Release-candidate check** (before tagging `v3.0.0`; recorded below). The candidate asset directory was built
   with `scripts/v3_package.py` from the delivery commit preceding the tag. The published release was then rebuilt
   from the tagged commit, which adds only this file, the two JSON records it cites, and a change in
   `scripts/v3_regen.py` that records the index path relative to the repository; the rebuilt release was
   verified again with `v3_verify.py` before upload.
2. **Fresh-download verification** (after publication): new directory, anonymous download of every public asset,
   checksums and member inventories, safe extraction, regeneration of every table, the 65-case GPU replay,
   reloads of every formal checkpoint architecture, a two-iteration resume and the documented quickstart.
   Recorded below (done 2026-11-08, all checks passed).

## 1. Release-candidate check (2026-11-08 22:28 UTC)

Commands (delivery checkout, CPU environment of `configs/closeout/requirements-analysis.txt`):

```bash
python3 scripts/v3_package.py --runs <runs> --videos <runs>/formal/videos --exp-repo <clean experiment-v3 checkout> \
    --tag v3.0.0 --output rc1 --redact <private prefixes>=<tokens> --redact-regex <host/user patterns>
python -I scripts/v3_verify.py --bundle rc1 --extract rc1_check/x --output rc1_check/verify.json     # exit 0
python scripts/v3_regen.py --runs rc1_check/x --work rc1_check/regen                                   # exit 0
```

| check | result |
|---|---|
| assets | 30 (461.0 MB); `SHA256SUMS` lists 29 (all but itself), 0 bad, 0 unlisted |
| `release_manifest.json` | lists all 28 other assets with matching size/SHA-256; experiment commit `3811f5da` |
| archive members | 4,943 members re-hashed against `archive_inventories.json` (source archives included), 0 problems, safe paths |
| checkpoints | 457 entries resolve with matching SHA-256; 23 formal runs (5/5/5/5/3 per family), each with step 0, ten periodic saves, final, latest and the selected tag; 18 pilot/smoke/resume runs |
| raw final records | 50 executed entries × 2,600 = 130,000 records (135,200 logical with aliases) |
| raw validation records | 138 files × 240 |
| videos | 9 MP4s (8 clips + montage) decode with the expected frame counts |
| documents | report.pdf 19 pages, slides.pdf 15 pages, slides.pptx 15 slides open |
| leak scan | 0 hits for private path prefixes, host names and user names in text members, member names and loose JSON/MD assets |
| table regeneration | 8 steps exit 0 (selection, summary, mechanisms, repeatability, interventions, zero-policy, traces, figures); 35 of 35 generated JSON/CSV files byte-identical to the committed `results/v3/` |

Machine-readable: [`results/v3/verification/release_candidate_verify.json`](../../results/v3/verification/release_candidate_verify.json),
[`results/v3/verification/release_candidate_regen.json`](../../results/v3/verification/release_candidate_regen.json).

## 2. Fresh-download verification (2026-11-08 22:34–22:49 UTC) — passed

Public release: https://github.com/ywen0511/CSCI645-Project/releases/tag/v3.0.0 (30 assets, 460,979,095 bytes).
Two new, empty directories were used: one on a CPU workstation and one on the GPU cluster. Neither used the
original training files. Clones came from the public GitHub URL with no credential helper and no token;
assets were downloaded anonymously through the public API and `browser_download_url`s
(`scripts/v3_download.py`, standard library, no token read or sent).

| step | command (from the clone at the tag unless noted) | exit | result |
|---|---|---|---|
| clone | `git clone https://github.com/ywen0511/CSCI645-Project.git; git checkout v3.0.0` | 0 | HEAD `ebfa328b17103c32ae19c13f0a6408ebc55a6459`; experiment clone at `experiment-v3` = `3811f5da5ef55638f95f7306e449609877f546df` |
| download | `python3 -I scripts/v3_download.py --tag v3.0.0` (branch tool) | 0 | 30 assets, 461.0 MB, sizes match the API ([`fresh_cpu_download_log.json`](../../results/v3/verification/fresh_cpu_download_log.json)) |
| checksums | `sha256sum -c SHA256SUMS` | 0 | 29 of 29 OK (both machines) |
| environment | `python3.13 -m venv` + `pip install -r configs/closeout/requirements-analysis.txt` | 0 | attempts 1–2 failed: `python3.13` was not on PATH and `python3` was 3.10, which cannot install the pins; attempt 3 used Python 3.13.9 (all attempts in [`fresh_cpu_steps.jsonl`](../../results/v3/verification/fresh_cpu_steps.jsonl)) |
| release verifier | `python -I scripts/v3_verify.py --bundle download --extract x` | 0 | ok on both machines: manifest covers all assets; 4,947 members re-hashed, 0 problems; 457 checkpoints resolve; 23 formal runs complete (step 0, 10 periodic, final, latest, selected); 50 × 2,600 final and 138 × 240 validation records; 9 MP4s decode; report.pdf 19 pages, slides 15; 0 leak hits ([`fresh_cpu_verify.json`](../../results/v3/verification/fresh_cpu_verify.json), [`fresh_gpu_node_verify.json`](../../results/v3/verification/fresh_gpu_node_verify.json)) |
| quickstart / table regeneration | `python scripts/v3_regen.py --runs x --work regen` | 0 | 8 steps exit 0; **35 of 35** JSON/CSV tables byte-identical to `results/v3/` at the tag; all 6 regenerated figures byte-identical ([`fresh_cpu_regen.json`](../../results/v3/verification/fresh_cpu_regen.json)) |
| GPU replay, reloads, resume | `scripts/v3_jobs.py run --manifest results/v3/jobs/verification.json --runs-root x --repo <experiment-v3 clone>` (1 × A100-SXM4-40GB, LSF) | 0 | 13 of 13 tasks rc 0, no watchdog events ([`fresh_gpu_steps.jsonl`](../../results/v3/verification/fresh_gpu_steps.jsonl)) |

**65-case replay** (predeclared subset, batch 23, seed 6455501; published records: batch 256): geometry_common,
geometry_best_constant and the five selected history policies, 455 episodes. **455 of 455** terminal outcomes
equal the published final records. Every case's observation-error spec and every checkpoint SHA-256 matches. 0
invalid resets.

**Checkpoint reloads** (one selected checkpoint of each other formal architecture/estimator profile:
combined_clean_ff, combined_robust_ff, combined_robust_repeat, residual_robust_history; 13 cases each, first case
of every condition): **52 of 52** terminal outcomes equal the published records. combined_robust_history is
reloaded by the replay above.

**Resume** (downloaded `formal/train/combined_robust_history_s11/checkpoints/latest.pt`, two PPO iterations into a
disposable directory): iterations 306 → 308, transitions 10,027,008 → 10,092,544, optimizer step count 6,120 →
6,160, all 8 normalizer tensors and 11 model tensors present and updated, RNG state present, saved checkpoint
reloads identically. The original file's SHA-256 was unchanged before and after
(`fc452c3622a9455a34120d39957d0b4de17ce2466bccdcb947e2746d72e1512d`).

**Mismatches:** none in the replay, the reloads, the regenerated tables or the figures. PhysX determinism is not
promised in general: the supplementary trace runs (batch 6) disagreed with the batch-256 records on 2 of 300
case-entry pairs, both for the seed-11 history *final* checkpoint (report Section 8).

Machine-readable summary: [`results/v3/verification/verification.json`](../../results/v3/verification/verification.json)
and [`fresh_gpu.json`](../../results/v3/verification/fresh_gpu.json).
