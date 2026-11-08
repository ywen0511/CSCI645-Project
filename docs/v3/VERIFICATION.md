# v3 verification

Status: **pre-publication**. This file is filled in two passes:

1. **Release-candidate check** (before tagging `v3.0.0`): the assembled asset directory is verified with
   `scripts/v3_verify.py` and all tables are regenerated from its extracted raw records with
   `scripts/v3_regen.py`.
2. **Fresh-download verification** (after publication): a new directory, anonymous download of every public
   asset, checksum and member verification, table regeneration, the 65-case GPU replay, checkpoint reloads for
   every formal architecture, a two-iteration resume, and the documented quickstart. Recorded on the branch
   (`docs/v3/VERIFICATION.md`, `results/v3/verification/`).

Results will be recorded below.
