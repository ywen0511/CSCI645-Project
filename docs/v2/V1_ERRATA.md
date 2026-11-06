# v1 errata

Verified issues in the published v1 study (tag `experiment-v1`, release `v1.0.0`). The v1 tag, release
assets and raw records are unchanged. Corrected presentations are in the v2 release and in the working
copies of `README.md` and `report/report_results.md` / `report/report.md` (marked with a correction note).
Evidence: [AUDIT.md](AUDIT.md).

| # | Issue | Where | Effect on v1 numbers | Correction |
|---|---|---|---|---|
| E1 | Aggregate case counts mislabelled: "in-range (1,400 cases)" and "stress (400 cases)". The analysis pools conditions by the substring `stress`, so the aggregates contain **1,200 non-stress cases** (clean + 5 in-range conditions, 200 each) and **600 stress cases** (3 conditions x 200). | README results table; report Section 6 main table; release notes | None. The percentages were computed on 1,200 and 600 cases; only the labels were wrong. Regenerating the tables from the downloaded raw records reproduces every published number byte for byte. | Labels changed to "non-stress conditions incl. clean (1,200 cases)" and "stress conditions (600 cases)". |
| E2 | Recorded `episode_return` omits the reward of the terminal step. The evaluator record is written in `_get_dones`, which Isaac Lab calls before `_get_rewards`; the terminal step's reward (including the +10 success, -5 drop/collision or -2 release-timeout term) was therefore never added to the record. Example: clean nominal success, recorded 4.66 vs full return 14.76 (terminal-step reward 10.1). | `episode_return` field of every v1 evaluation record | None on any published table, figure, selection or conclusion: no v1 analysis used `episode_return`; PPO trained on the per-step reward buffer, which does include the terminal reward; learning curves use the mean training step reward. | Fixed in v2 source: records carry the full `episode_return` plus `episode_return_excl_terminal_step` and `terminal_step_reward`. v1 records are not rewritten. |
| E3 | "Untrained step-0 policy" was described as an untrained/zero-information control. Its deterministic mean is not zero: each seed's random initialization outputs a near-constant residual (x = +1.4, +1.0, -2.5 mm for combined seeds 11/22/33; across-case std <= 0.04 mm). Primary v1 combined results for 8 of 9 runs therefore measure geometry plus a small seed-specific constant offset. | report Sections 6-7 interpretation | The numbers are correct; their interpretation as "geometry + untrained network" is incomplete. On v2 development cases the step-0 policies follow the constant-offset curve (e.g. seed 33 with -2.5 mm: 96.4% vs geometry 98.4%). | Stated explicitly in the v2 report; v2 tests a zero-mean actor initialization. |

Not errata (checked and confirmed correct): case-ID sets and counts (19,800 primary and 16,200 secondary
records, identical case IDs across files, 0 duplicates, 0 invalid resets, 0 infrastructure errors),
checkpoint hashes and transition counts versus archives and ledgers, the selection files versus the
evaluated checkpoints, the secondary-analysis numbers quoted in the follow-up brief (stress success:
residual 55.8%, combined 89.9%, combined_no_phase 90.3%; combined - geometry -3.4 pp), success logic
(two continuous seconds of receiver-only holding, giver open, no giver/table support) and negative controls.
