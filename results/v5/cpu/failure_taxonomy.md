# V4 failure taxonomy (derived from v4.0.0 raw final records)

Exclusive terminal reasons as % of all scheduled episodes (learned rows: selected checkpoints, five seeds pooled). Success completion time is the median over successful episodes.

## grasp_15mm

| Controller | Success | Collision | Drop | Episode timeout | Release timeout | Invalid reset | Median completion (s) | Failed: misaligned / premature / conflicting |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nominal | 38.5 | 57.5 | 3.5 | 0.5 | 0.0 | 0.0 | 4.90 | 123: 24 / 8 / 0 |
| Fixed geometry | 5.5 | 94.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.90 | 189: 14 / 0 / 0 |
| EMA geometry | 94.0 | 6.0 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 12: 1 / 0 / 0 |
| Calibrated geometry | 94.5 | 5.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 11: 1 / 0 / 0 |
| Robust feed-forward | 96.5 | 3.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 35: 0 / 0 / 0 |
| Robust history | 99.1 | 0.8 | 0.1 | 0.0 | 0.0 | 0.0 | 4.85 | 9: 8 / 0 / 0 |
| Repeated current frame | 96.2 | 3.8 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 38: 6 / 0 / 0 |
| Residual-only history | 40.3 | 49.6 | 9.5 | 0.6 | 0.0 | 0.0 | 4.90 | 597: 190 / 98 / 0 |

## mixed_id

| Controller | Success | Collision | Drop | Episode timeout | Release timeout | Invalid reset | Median completion (s) | Failed: misaligned / premature / conflicting |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nominal | 59.5 | 33.5 | 5.5 | 1.5 | 0.0 | 0.0 | 4.90 | 81: 25 / 15 / 0 |
| Fixed geometry | 69.5 | 30.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 61: 19 / 0 / 0 |
| EMA geometry | 99.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 2: 1 / 0 / 0 |
| Calibrated geometry | 98.5 | 1.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 3: 2 / 0 / 0 |
| Robust feed-forward | 99.4 | 0.6 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 6: 1 / 0 / 0 |
| Robust history | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 0: 0 / 0 / 0 |
| Repeated current frame | 99.5 | 0.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 5: 1 / 0 / 0 |
| Residual-only history | 56.3 | 29.6 | 9.4 | 4.7 | 0.0 | 0.0 | 4.90 | 437: 196 / 109 / 0 |

## mixed_ood

| Controller | Success | Collision | Drop | Episode timeout | Release timeout | Invalid reset | Median completion (s) | Failed: misaligned / premature / conflicting |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nominal | 59.0 | 30.5 | 6.5 | 4.0 | 0.0 | 0.0 | 4.90 | 82: 29 / 22 / 0 |
| Fixed geometry | 73.5 | 26.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 53: 19 / 0 / 0 |
| EMA geometry | 90.5 | 4.5 | 0.0 | 0.0 | 5.0 | 0.0 | 5.10 | 19: 12 / 0 / 0 |
| Calibrated geometry | 94.5 | 5.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 11: 9 / 0 / 0 |
| Robust feed-forward | 94.5 | 5.5 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 55: 5 / 0 / 0 |
| Robust history | 97.0 | 2.8 | 0.1 | 0.0 | 0.1 | 0.0 | 4.90 | 30: 23 / 0 / 0 |
| Repeated current frame | 91.3 | 8.7 | 0.0 | 0.0 | 0.0 | 0.0 | 4.85 | 87: 25 / 0 / 0 |
| Residual-only history | 53.7 | 29.9 | 12.1 | 4.3 | 0.0 | 0.0 | 4.90 | 463: 242 / 142 / 0 |

## boundary_x_minus_7

| Controller | Success | Collision | Drop | Episode timeout | Release timeout | Invalid reset | Median completion (s) | Failed: misaligned / premature / conflicting |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nominal | 48.0 | 44.5 | 0.5 | 3.5 | 0.0 | 3.5 | 4.85 | 97: 85 / 17 / 0 |
| Fixed geometry | 96.0 | 1.0 | 0.0 | 0.0 | 0.0 | 3.0 | 4.85 | 2: 2 / 0 / 0 |
| EMA geometry | 96.0 | 0.0 | 0.0 | 0.0 | 0.0 | 4.0 | 4.85 | 0: 0 / 0 / 0 |
| Calibrated geometry | 96.5 | 0.5 | 0.0 | 0.0 | 0.0 | 3.0 | 4.85 | 1: 0 / 0 / 0 |
| Robust feed-forward | 88.2 | 8.4 | 0.0 | 0.0 | 0.0 | 3.4 | 4.85 | 84: 0 / 0 / 0 |
| Robust history | 65.2 | 31.2 | 0.0 | 0.0 | 0.0 | 3.6 | 4.85 | 312: 148 / 0 / 0 |
| Repeated current frame | 91.2 | 5.2 | 0.0 | 0.0 | 0.0 | 3.6 | 4.85 | 52: 0 / 0 / 0 |
| Residual-only history | 42.3 | 43.1 | 6.6 | 4.5 | 0.0 | 3.5 | 4.85 | 542: 448 / 167 / 0 |

