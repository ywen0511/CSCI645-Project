# V4 final synthesis and independent CPU review

This documentation/analysis supplement preserves every published V4 experiment and
checkpoint. It adds a six-page project synthesis, interpretation corrections, a
retrospective reset-sensitivity analysis, defense notes and an executable CPU audit.

The independent audit reconciles 129,600 final episodes, all success/reset summaries,
two primary bootstrap comparisons, 78 frozen input hashes and 25 selections from
recorded candidate summaries. On the 189 boundary cases valid across all executed
entries, selected robust history remains 30.79 percentage points below calibrated
geometry (exploratory paired 95% interval [-43.60, -18.20]). This is a post hoc
conditional analysis; the original all-scheduled denominator remains primary.

The fixed-versus-calibrated final comparison changes estimator, filtering and alignment
bound. Treat it as a controller-configuration comparison, not an isolated calibration
effect. Primary learning intervals touch zero; no superiority or equivalence is claimed.

Read `overview.pdf` and `REVIEW.md` alongside the archived full report and deck.
`INHERITED_ASSETS.json` contains exact URLs, sizes and SHA-256 for all study assets in
[v4.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.0) and tooling in
[v4.0.1](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.1).
All formal/pilot/smoke checkpoints, logs, raw records, original reports, slides and
videos remain in those releases. They are intentionally reused without modification;
this supplement has no new trained model and no new GPU experiment.

Formal experiment source remains `experiment-v4` at
`aac4d98274814b1ab121a715db71187e3e1cc0b9`. `SOURCE_COMMIT.txt` identifies this
supplement's exact source snapshot. `release_manifest.json` and `SHA256SUMS` cover
its assets. Public-download verification is recorded on branch in
`results/final_review/public_verification.json` once completed; a release candidate
must not be described as publicly verified before that record exists.
