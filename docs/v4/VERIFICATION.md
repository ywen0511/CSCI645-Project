# V4 verification record

1. **Release-candidate check (before publication).** The release directory is built with `scripts/v4_package.py` from
   a clean checkout of tag `v4.0.0` and a clean checkout of `experiment-v4`, then checked with
   `python -I scripts/v4_verify.py --bundle <dir> --extract <empty dir>` and `scripts/v4_regen.py`.
2. **Public-download verification (after publication).** New empty directories, public clones only, anonymous download
   of every asset, then `docs/v4/REPRODUCE.md` sections 1–3 verbatim.

Both results are recorded below in a commit made after the release is published (the tagged copy of this file cannot
contain them without a circular self-hash).
