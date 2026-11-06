# v2 development diagnostics — generated tables

Suite `configs/v2/suites/development.jsonl` (sha256 `4118cb5e5eae5b5f…`), 450 cases, 50 per condition. Development evidence only. Success in % of valid resets (all resets were valid unless noted).

## Controls

| controller | non-stress (300) | stress (150) | all (450) | drops | collision eps | timeouts | release timeouts | invalid resets |
|---|---|---|---|---|---|---|---|---|
| nominal | 96.0 | 48.0 | 80.0 | 8 | 54 | 29 | 0 | 0 |
| geometry_zero | 100.0 | 95.3 | 98.4 | 0 | 9 | 0 | 0 | 0 |
| const_geometry_1cm_x+003mm (selected constant) | 100.0 | 100.0 | 100.0 | 0 | 0 | 0 | 0 | 0 |
| const_nominal_x+004mm (selected constant) | 100.0 | 51.3 | 83.8 | 10 | 28 | 35 | 0 | 0 |
| combined_init_s11 | 100.0 | 98.7 | 99.6 | 0 | 3 | 0 | 0 | 0 |
| combined_init_s22 | 100.0 | 100.0 | 100.0 | 0 | 2 | 0 | 0 | 0 |
| combined_init_s33 | 100.0 | 89.3 | 96.4 | 0 | 18 | 0 | 0 | 0 |
| combined_final_s11 | 100.0 | 88.7 | 96.2 | 0 | 17 | 0 | 0 | 0 |
| combined_final_s22 | 100.0 | 94.7 | 98.2 | 0 | 12 | 0 | 0 | 0 |
| combined_final_s33 | 100.0 | 93.3 | 97.8 | 0 | 11 | 0 | 0 | 0 |
| residual_init_s11 | 99.7 | 49.3 | 82.9 | 8 | 41 | 32 | 0 | 0 |
| residual_init_s22 | 100.0 | 50.7 | 83.6 | 8 | 36 | 34 | 0 | 0 |
| residual_init_s33 | 91.0 | 44.7 | 75.6 | 8 | 82 | 25 | 0 | 0 |
| residual_final_s11 | 100.0 | 52.0 | 84.0 | 2 | 44 | 35 | 0 | 0 |
| residual_final_s22 | 100.0 | 54.0 | 84.7 | 1 | 54 | 32 | 0 | 0 |
| residual_final_s33 | 100.0 | 61.3 | 87.1 | 0 | 52 | 28 | 0 | 0 |
| combined_no_phase_final_s11 | 100.0 | 89.3 | 96.4 | 0 | 17 | 0 | 0 | 0 |
| combined_no_phase_final_s22 | 100.0 | 92.0 | 97.3 | 0 | 15 | 0 | 0 | 0 |
| combined_no_phase_final_s33 | 100.0 | 94.0 | 98.0 | 0 | 12 | 0 | 0 | 0 |

## Constant-offset search (x only, y = z = 0)

**geometry_1cm** — selected x = +3 mm

| x [mm] | success / 450 | stress success / 150 | collision eps | drops |
|---|---|---|---|---|
| -5 | 421 | 121 | 29 | 0 |
| -4 | 429 | 129 | 24 | 0 |
| -3 | 431 | 131 | 20 | 0 |
| -2 | 436 | 136 | 16 | 0 |
| -1 | 440 | 140 | 10 | 0 |
| +0 | 443 | 143 | 9 | 0 |
| +1 | 447 | 147 | 4 | 0 |
| +2 | 450 | 150 | 2 | 0 |
| +3 **(selected)** | 450 | 150 | 0 | 0 |
| +4 | 450 | 150 | 0 | 0 |
| +5 | 450 | 150 | 0 | 0 |

**nominal** — selected x = +4 mm

| x [mm] | success / 450 | stress success / 150 | collision eps | drops |
|---|---|---|---|---|
| -5 | 317 | 60 | 110 | 8 |
| -4 | 328 | 65 | 96 | 8 |
| -3 | 334 | 66 | 85 | 8 |
| -2 | 341 | 66 | 78 | 8 |
| -1 | 357 | 72 | 64 | 8 |
| +0 | 360 | 72 | 54 | 8 |
| +1 | 368 | 72 | 46 | 8 |
| +2 | 376 | 76 | 36 | 8 |
| +3 | 377 | 77 | 33 | 9 |
| +4 **(selected)** | 377 | 77 | 28 | 10 |
| +5 | 376 | 76 | 27 | 10 |

**geometry_1p5cm** — selected x = +0 mm

| x [mm] | success / 450 | stress success / 150 | collision eps | drops |
|---|---|---|---|---|
| -5 | 442 | 142 | 10 | 0 |
| -4 | 446 | 146 | 4 | 0 |
| -3 | 449 | 149 | 3 | 0 |
| -2 | 450 | 150 | 0 | 0 |
| -1 | 450 | 150 | 0 | 0 |
| +0 **(selected)** | 450 | 150 | 0 | 0 |
| +1 | 450 | 150 | 0 | 0 |
| +2 | 450 | 150 | 0 | 0 |
| +3 | 450 | 150 | 0 | 0 |
| +4 | 450 | 150 | 0 | 0 |
| +5 | 450 | 150 | 0 | 0 |

## Paired differences (percentage points; 95% CI, seed x case bootstrap)

| comparison | cases | metric | A | B | A - B | 95% CI |
|---|---|---|---|---|---|---|
| combined_init - geometry_zero | all | success | 98.7 | 98.4 | +0.2 | [-2.0, +2.1] |
| combined_init - geometry_zero | all | collision | 1.7 | 2.0 | -0.3 | [-2.2, +1.9] |
| combined_init - geometry_zero | stress | success | 96.0 | 95.3 | +0.7 | [-5.6, +6.2] |
| combined_init - geometry_zero | stress | collision | 5.1 | 6.0 | -0.9 | [-6.4, +5.3] |
| combined_init - geometry_zero | non_stress | success | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] |
| combined_init - geometry_zero | non_stress | collision | 0.0 | 0.0 | +0.0 | [+0.0, +0.0] |
| combined_final - geometry_zero | all | success | 97.4 | 98.4 | -1.0 | [-2.4, -0.1] |
| combined_final - geometry_zero | all | collision | 3.0 | 2.0 | +1.0 | [+0.1, +2.2] |
| combined_final - geometry_zero | stress | success | 92.2 | 95.3 | -3.1 | [-7.3, +0.0] |
| combined_final - geometry_zero | stress | collision | 8.9 | 6.0 | +2.9 | [+0.4, +6.4] |
| combined_final - geometry_zero | non_stress | success | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] |
| combined_final - geometry_zero | non_stress | collision | 0.0 | 0.0 | +0.0 | [+0.0, +0.0] |
| combined_final - geometry_const | all | success | 97.4 | 100.0 | -2.6 | [-4.4, -1.1] |
| combined_final - geometry_const | all | collision | 3.0 | 0.0 | +3.0 | [+1.5, +4.7] |
| combined_final - geometry_const | stress | success | 92.2 | 100.0 | -7.8 | [-13.1, -3.3] |
| combined_final - geometry_const | stress | collision | 8.9 | 0.0 | +8.9 | [+4.4, +14.0] |
| combined_final - geometry_const | non_stress | success | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] |
| combined_final - geometry_const | non_stress | collision | 0.0 | 0.0 | +0.0 | [+0.0, +0.0] |
| combined_final - combined_init | all | success | 97.4 | 98.7 | -1.3 | [-3.6, +0.9] |
| combined_final - combined_init | all | collision | 3.0 | 1.7 | +1.3 | [-0.9, +3.6] |
| combined_final - combined_init | stress | success | 92.2 | 96.0 | -3.8 | [-10.4, +2.9] |
| combined_final - combined_init | stress | collision | 8.9 | 5.1 | +3.8 | [-2.4, +10.2] |
| combined_final - combined_init | non_stress | success | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] |
| combined_final - combined_init | non_stress | collision | 0.0 | 0.0 | +0.0 | [+0.0, +0.0] |
| geometry_const - geometry_zero | all | success | 100.0 | 98.4 | +1.6 | [+0.4, +2.9] |
| geometry_const - geometry_zero | all | collision | 0.0 | 2.0 | -2.0 | [-3.3, -0.9] |
| geometry_const - geometry_zero | stress | success | 100.0 | 95.3 | +4.7 | [+1.3, +8.7] |
| geometry_const - geometry_zero | stress | collision | 0.0 | 6.0 | -6.0 | [-10.0, -2.7] |
| geometry_const - geometry_zero | non_stress | success | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] |
| geometry_const - geometry_zero | non_stress | collision | 0.0 | 0.0 | +0.0 | [+0.0, +0.0] |
| residual_init - nominal | all | success | 80.7 | 80.0 | +0.7 | [-4.1, +4.7] |
| residual_init - nominal | all | collision | 11.8 | 12.0 | -0.2 | [-4.7, +5.8] |
| residual_init - nominal | stress | success | 48.2 | 48.0 | +0.2 | [-4.2, +5.1] |
| residual_init - nominal | stress | collision | 28.0 | 27.3 | +0.7 | [-4.9, +6.9] |
| residual_init - nominal | non_stress | success | 96.9 | 96.0 | +0.9 | [-4.4, +5.3] |
| residual_init - nominal | non_stress | collision | 3.7 | 4.3 | -0.7 | [-5.4, +5.3] |
| residual_final - nominal | all | success | 85.3 | 80.0 | +5.3 | [+2.9, +8.0] |
| residual_final - nominal | all | collision | 11.1 | 12.0 | -0.9 | [-2.7, +0.9] |
| residual_final - nominal | stress | success | 55.8 | 48.0 | +7.8 | [+2.4, +14.2] |
| residual_final - nominal | stress | collision | 28.0 | 27.3 | +0.7 | [-1.8, +3.1] |
| residual_final - nominal | non_stress | success | 100.0 | 96.0 | +4.0 | [+2.0, +6.3] |
| residual_final - nominal | non_stress | collision | 2.7 | 4.3 | -1.7 | [-4.1, +0.4] |
| residual_final - nominal_const | all | success | 85.3 | 83.8 | +1.5 | [-0.7, +3.8] |
| residual_final - nominal_const | all | collision | 11.1 | 6.2 | +4.9 | [+2.9, +7.0] |
| residual_final - nominal_const | stress | success | 55.8 | 51.3 | +4.4 | [-2.0, +11.3] |
| residual_final - nominal_const | stress | collision | 28.0 | 18.7 | +9.3 | [+5.3, +13.8] |
| residual_final - nominal_const | non_stress | success | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] |
| residual_final - nominal_const | non_stress | collision | 2.7 | 0.0 | +2.7 | [+0.7, +5.1] |
| residual_final - residual_init | all | success | 85.3 | 80.7 | +4.6 | [+0.7, +9.7] |
| residual_final - residual_init | all | collision | 11.1 | 11.8 | -0.7 | [-6.5, +3.9] |
| residual_final - residual_init | stress | success | 55.8 | 48.2 | +7.6 | [+1.3, +14.9] |
| residual_final - residual_init | stress | collision | 28.0 | 28.0 | +0.0 | [-6.7, +5.3] |
| residual_final - residual_init | non_stress | success | 100.0 | 96.9 | +3.1 | [+0.0, +8.4] |
| residual_final - residual_init | non_stress | collision | 2.7 | 3.7 | -1.0 | [-6.9, +3.8] |
| nominal_const - nominal | all | success | 83.8 | 80.0 | +3.8 | [+1.6, +6.2] |
| nominal_const - nominal | all | collision | 6.2 | 12.0 | -5.8 | [-8.0, -3.8] |
| nominal_const - nominal | stress | success | 51.3 | 48.0 | +3.3 | [-2.0, +8.7] |
| nominal_const - nominal | stress | collision | 18.7 | 27.3 | -8.7 | [-13.3, -4.7] |
| nominal_const - nominal | non_stress | success | 100.0 | 96.0 | +4.0 | [+2.0, +6.3] |
| nominal_const - nominal | non_stress | collision | 0.0 | 4.3 | -4.3 | [-7.0, -2.3] |
| combined_no_phase_final - combined_final [exploratory] | all | success | 97.3 | 97.4 | -0.1 | [-1.5, +1.2] |
| combined_no_phase_final - combined_final [exploratory] | all | collision | 3.3 | 3.0 | +0.3 | [-0.7, +1.4] |
| combined_no_phase_final - combined_final [exploratory] | stress | success | 91.8 | 92.2 | -0.4 | [-4.4, +3.8] |
| combined_no_phase_final - combined_final [exploratory] | stress | collision | 9.8 | 8.9 | +0.9 | [-2.2, +4.2] |
| combined_no_phase_final - combined_final [exploratory] | non_stress | success | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] |
| combined_no_phase_final - combined_final [exploratory] | non_stress | collision | 0.0 | 0.0 | +0.0 | [+0.0, +0.0] |

## Residual behaviour of archived v1 checkpoints (valid episodes, means over scored steps)

| entry | mean signed residual x/y/z [mm] | across-case std x/y/z [mm] | RMS [mm] | slope res_x vs offset_x | corr | exec - cand [mm] |
|---|---|---|---|---|---|---|
| combined_final_s11 | -2.46 / +2.46 / -0.42 | 0.39 / 0.42 / 0.39 | 4.36 | +0.013 | +0.25 | 10.42 |
| combined_final_s22 | -1.01 / +1.29 / -0.77 | 0.32 / 0.44 / 0.44 | 4.37 | +0.001 | +0.01 | 9.45 |
| combined_final_s33 | -1.72 / -0.67 / -1.44 | 0.14 / 0.50 / 0.87 | 3.31 | -0.000 | -0.02 | 9.92 |
| combined_init_s11 | +1.40 / +0.45 / -0.18 | 0.02 / 0.04 / 0.03 | 1.58 | -0.001 | -0.58 | 9.59 |
| combined_init_s22 | +0.99 / -0.18 / -0.98 | 0.03 / 0.06 / 0.02 | 2.27 | -0.003 | -0.60 | 9.70 |
| combined_init_s33 | -2.52 / -0.04 / +0.05 | 0.04 / 0.05 / 0.06 | 2.57 | -0.001 | -0.13 | 9.61 |
| combined_no_phase_final_s11 | -2.15 / +4.98 / -0.70 | 0.27 / 0.40 / 0.31 | 5.61 | -0.008 | -0.21 | 10.45 |
| combined_no_phase_final_s22 | -2.44 / +6.70 / -1.26 | 0.26 / 0.49 / 0.24 | 7.61 | +0.013 | +0.37 | 11.69 |
| combined_no_phase_final_s33 | -0.74 / -1.97 / -1.85 | 0.31 / 0.48 / 0.60 | 3.86 | -0.004 | -0.10 | 9.86 |
| residual_final_s11 | -1.47 / +2.18 / -1.30 | 0.85 / 2.74 / 2.74 | 7.04 | +0.074 | +0.65 | 0.00 |
| residual_final_s22 | -2.98 / +1.02 / -1.82 | 1.57 / 2.47 / 1.96 | 6.59 | +0.155 | +0.74 | 0.00 |
| residual_final_s33 | -1.27 / -1.07 / -2.45 | 1.41 / 2.57 / 1.22 | 6.13 | +0.089 | +0.47 | 0.00 |
| residual_init_s11 | +1.43 / +0.47 / -0.18 | 0.07 / 0.09 / 0.14 | 1.64 | -0.001 | -0.09 | 0.00 |
| residual_init_s22 | +1.02 / -0.16 / -0.96 | 0.43 / 0.24 / 0.27 | 2.31 | +0.032 | +0.55 | 0.00 |
| residual_init_s33 | -2.56 / -0.06 / +0.04 | 0.11 / 0.04 / 0.16 | 2.62 | -0.000 | -0.01 | 0.00 |

## Geometry component ablation (residual = 0, alignment bound 1 cm)

| controller | non-stress (300) | stress (150) | all (450) | drops | collision eps | timeouts | release timeouts | invalid resets |
|---|---|---|---|---|---|---|---|---|
| none | 96.0 | 48.0 | 80.0 | 8 | 54 | 29 | 0 | 0 |
| A | 100.0 | 81.3 | 93.8 | 0 | 10 | 18 | 0 | 0 |
| H | 96.3 | 48.0 | 80.2 | 8 | 54 | 29 | 0 | 0 |
| G | 96.0 | 68.7 | 86.9 | 1 | 54 | 4 | 1 | 0 |
| AH | 100.0 | 82.0 | 94.0 | 0 | 9 | 18 | 0 | 0 |
| AG | 100.0 | 94.7 | 98.2 | 0 | 9 | 0 | 0 | 0 |
| HG | 96.3 | 69.3 | 87.3 | 1 | 54 | 3 | 1 | 0 |
| AHG | 100.0 | 94.7 | 98.2 | 0 | 9 | 0 | 0 | 0 |

Reproduction checks (same process, same cases):

- `geom_AHG` vs `geometry_zero`: terminal reason differs in 1/450 cases; completion time differs in 0 successful cases.
- `geom_none` vs `nominal`: terminal reason differs in 0/450 cases; completion time differs in 0 successful cases.
- `geom_bound_0p010` vs `geometry_zero`: terminal reason differs in 0/450 cases; completion time differs in 0 successful cases.

Factorial effects on success (percentage points, 2^3 contrasts; 95% CI over cases):

| effect | all | stress | non-stress |
|---|---|---|---|
| A | +12.4 [+9.6, +15.3] | +29.7 [+23.3, +36.3] | +3.8 [+1.8, +6.2] |
| H | +0.2 [+0.0, +0.5] | +0.3 [+0.0, +0.8] | +0.2 [+0.0, +0.5] |
| G | +5.7 [+3.9, +7.6] | +17.0 [+12.2, +22.7] | +0.0 [+0.0, +0.0] |
| AH | -0.1 [-0.4, +0.1] | +0.0 [-0.5, +0.5] | -0.2 [-0.5, +0.0] |
| AG | -1.3 [-2.3, -0.4] | -4.0 [-7.0, -1.2] | +0.0 [+0.0, +0.0] |
| HG | +0.0 [-0.2, +0.2] | +0.0 [-0.5, +0.5] | +0.0 [+0.0, +0.0] |
| AHG | -0.1 [-0.3, +0.0] | -0.3 [-0.8, +0.0] | +0.0 [+0.0, +0.0] |

Conditional effects on stress cases (pp):

- A|H=off,G=off: +33.3
- A|H=off,G=on: +26.0
- A|H=on,G=off: +34.0
- A|H=on,G=on: +25.3
- H|A=off,G=off: +0.0
- H|A=off,G=on: +0.7
- H|A=on,G=off: +0.7
- H|A=on,G=on: +0.0
- G|A=off,H=off: +20.7
- G|A=off,H=on: +21.3
- G|A=on,H=off: +13.3
- G|A=on,H=on: +12.7

## Alignment-bound sensitivity (full geometry, residual = 0)

| controller | non-stress (300) | stress (150) | all (450) | drops | collision eps | timeouts | release timeouts | invalid resets |
|---|---|---|---|---|---|---|---|---|
| 0.5 cm | 100.0 | 82.0 | 94.0 | 0 | 27 | 0 | 0 | 0 |
| 1.0 cm | 100.0 | 95.3 | 98.4 | 0 | 8 | 0 | 0 | 0 |
| 1.5 cm | 100.0 | 100.0 | 100.0 | 0 | 0 | 0 | 0 | 0 |
| 2.0 cm | 100.0 | 100.0 | 100.0 | 0 | 0 | 0 | 0 | 0 |
