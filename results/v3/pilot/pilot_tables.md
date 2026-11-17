# v3 pilots (development only; not results)

| pilot | transitions | fps | losses finite | train success (last 20%) | dev success /144 | resid. mean [mm] | resid. max [mm] | clip [mm] | align sat. | mean resid. x,y,z [mm] |
|---|---|---|---|---|---|---|---|---|---|---|
| combined_clean_ff_s101 | 2,752,512 | 9759 | True | 99.9% | 144 | 5.62 | 13.68 | 0.00 | 0.296 | -0.46, -5.08, -3.35 |
| combined_robust_ff_s101 | 2,752,512 | 9593 | True | 99.7% | 144 | 6.21 | 12.41 | 0.00 | 0.300 | -2.74, -0.23, -5.90 |
| combined_robust_ff_s102 | 2,752,512 | 9244 | True | 100.0% | 144 | 3.88 | 12.33 | 0.00 | 0.301 | -3.41, 1.36, 1.09 |
| combined_robust_history_s101 | 2,752,512 | 9257 | True | 99.7% | 144 | 3.25 | 5.33 | 0.00 | 0.301 | -0.94, -0.03, -2.42 |
| combined_robust_history_s102 | 2,752,512 | 9657 | True | 99.6% | 144 | 6.12 | 10.98 | 0.00 | 0.304 | 0.03, 3.06, 0.60 |
| combined_robust_repeat_s101 | 2,752,512 | 9475 | True | 100.0% | 144 | 3.85 | 9.53 | 0.00 | 0.300 | -2.29, -0.27, -2.33 |
| residual_robust_history_s101 | 2,752,512 | 9060 | True | 76.9% | 120 | 2.42 | 6.39 | 0.00 | 0.000 | 0.11, -0.30, -0.16 |
| residual_robust_history_s102 | 2,752,512 | 8832 | True | 77.2% | 110 | 2.13 | 6.52 | 0.00 | 0.000 | 1.15, 0.84, -0.68 |
