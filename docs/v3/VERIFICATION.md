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
   Recorded on the branch in this file and in `results/v3/verification/` after the release is public.

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

## 2. Fresh-download verification

Pending publication of `v3.0.0`.
