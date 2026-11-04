# v2 final results — generated tables

Final suite `configs/v2/suites/final.jsonl`: 12 conditions x 200 cases. Success in % of valid resets. Groups: inner = clean, position_1cm, timing_early_015, timing_late_015, joint_early_1cm_015, joint_late_1cm_015; outer = position_2cm, joint_early_2cm_030, joint_late_2cm_030; extrapolation = position_3cm, joint_early_3cm_045, joint_late_3cm_045.

## Reconciliation

- Expected episodes (manifest): 117600; recorded: 117600; invalid resets: 0; infrastructure errors: 0.
- Reused (identical configuration, not re-run): `ablation_1cm_AHG` = `geometry_1cm`, `ablation_1p5cm_AHG` = `geometry_1p5cm`, `bound_0p010` = `geometry_1cm`, `bound_0p015` = `geometry_1p5cm`
- Problems: none

## Deterministic controllers

| controller | inner | outer | in_training | extrapolation | all | drops | collision eps | timeouts | release timeouts |
|---|---|---|---|---|---|---|---|---|---|
| const_geometry_1cm | 100.0 | 99.8 | 99.9 | 80.7 | 95.1 | 5 | 68 | 32 | 15 |
| const_geometry_1p5cm | 100.0 | 100.0 | 100.0 | 97.0 | 99.2 | 0 | 0 | 18 | 0 |
| const_nominal | 99.9 | 57.0 | 85.6 | 20.3 | 69.3 | 363 | 239 | 155 | 0 |
| geometry_1cm | 100.0 | 93.3 | 97.8 | 74.3 | 91.9 | 0 | 175 | 13 | 12 |
| geometry_1p5cm | 100.0 | 100.0 | 100.0 | 86.2 | 96.5 | 0 | 84 | 1 | 0 |
| nominal | 96.0 | 50.0 | 80.7 | 18.8 | 65.2 | 243 | 496 | 121 | 0 |

## Learned policies (mean over 3 seeds; per-seed values in metrics_per_method.csv)

| method | checkpoint | inner | outer | in_training | extrapolation | all |
|---|---|---|---|---|---|---|
| residual | selected | 99.9 (0.2) | 85.5 (1.8) | 95.1 (0.5) | 45.2 (0.2) | 82.6 (0.4) |
| residual | final | 100.0 (0.0) | 85.6 (1.9) | 95.2 (0.6) | 45.9 (0.3) | 82.9 (0.5) |
| residual | untrained | 96.2 (0.0) | 50.0 (0.0) | 80.8 (0.0) | 18.7 (0.0) | 65.3 (0.0) |
| combined | selected | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) | 84.4 (0.5) | 96.1 (0.1) |
| combined | final | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) | 84.7 (0.1) | 96.2 (0.0) |
| combined | untrained | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) | 86.2 (0.0) | 96.5 (0.0) |
| combined_no_phase | selected | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) | 85.2 (1.2) | 96.3 (0.3) |
| combined_no_phase | final | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) | 84.9 (0.5) | 96.2 (0.1) |
| combined_no_phase | untrained | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) | 86.2 (0.0) | 96.5 (0.0) |

(sd over seeds in parentheses)

## Per-condition success

| condition | relation | nominal | geometry 1 cm | geometry 1.5 cm | geo 1.5 + const | nominal + const | residual sel | combined sel | no-phase sel | combined final |
|---|---|---|---|---|---|---|---|---|---|---|
| clean | in_training | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| position_1cm | in_training | 93.5 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 100.0 | 100.0 | 100.0 |
| position_2cm | in_training | 71.5 | 94.5 | 100.0 | 100.0 | 80.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| timing_early_015 | in_training | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| timing_late_015 | in_training | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| joint_early_1cm_015 | in_training | 92.5 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 100.0 | 100.0 | 100.0 |
| joint_late_1cm_015 | in_training | 90.0 | 100.0 | 100.0 | 100.0 | 99.5 | 99.7 | 100.0 | 100.0 | 100.0 |
| joint_early_2cm_030 | in_training | 13.5 | 94.5 | 100.0 | 100.0 | 10.0 | 57.0 | 100.0 | 100.0 | 100.0 |
| joint_late_2cm_030 | in_training | 65.0 | 91.0 | 100.0 | 100.0 | 81.0 | 99.5 | 100.0 | 100.0 | 100.0 |
| position_3cm | extrapolation | 29.0 | 72.5 | 87.0 | 96.5 | 31.0 | 69.2 | 82.8 | 85.8 | 83.3 |
| joint_early_3cm_045 | extrapolation | 0.0 | 75.0 | 86.0 | 97.0 | 0.0 | 0.0 | 85.5 | 85.5 | 85.5 |
| joint_late_3cm_045 | extrapolation | 27.5 | 75.5 | 85.5 | 97.5 | 30.0 | 66.5 | 84.8 | 84.2 | 85.3 |

## Comparisons (percentage points; 95% CI from the seed x case paired bootstrap)

| analysis | comparison | cases | A | B | A - B | 95% CI | Cohen h | Holm p |
|---|---|---|---|---|---|---|---|---|
| primary | combined - geometry_1p5cm | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - geometry_1p5cm | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - geometry_1p5cm | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - geometry_1p5cm | extrapolation | 84.4 | 86.2 | -1.8 | [-3.1, -0.7] | -0.05 |  |
| primary | combined - geometry_1p5cm | all | 96.1 | 96.5 | -0.4 | [-0.8, -0.2] | -0.02 | 0.004 |
| primary | combined - const_geometry_1p5cm | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - const_geometry_1p5cm | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - const_geometry_1p5cm | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - const_geometry_1p5cm | extrapolation | 84.4 | 97.0 | -12.6 | [-16.0, -9.3] | -0.46 |  |
| primary | combined - const_geometry_1p5cm | all | 96.1 | 99.2 | -3.2 | [-4.0, -2.3] | -0.22 | 0.000 |
| primary | residual - nominal | inner | 99.9 | 96.0 | +3.9 | [+2.8, +5.1] | +0.34 |  |
| primary | residual - nominal | outer | 85.5 | 50.0 | +35.5 | [+31.4, +39.7] | +0.79 |  |
| primary | residual - nominal | in_training | 95.1 | 80.7 | +14.4 | [+12.8, +16.1] | +0.46 |  |
| primary | residual - nominal | extrapolation | 45.2 | 18.8 | +26.4 | [+23.2, +29.8] | +0.58 |  |
| primary | residual - nominal | all | 82.6 | 65.2 | +17.4 | [+15.9, +19.0] | +0.40 | 0.000 |
| primary | residual - const_nominal | inner | 99.9 | 99.9 | -0.0 | [-0.3, +0.2] | -0.01 |  |
| primary | residual - const_nominal | outer | 85.5 | 57.0 | +28.5 | [+24.6, +32.5] | +0.65 |  |
| primary | residual - const_nominal | in_training | 95.1 | 85.6 | +9.5 | [+8.1, +10.9] | +0.33 |  |
| primary | residual - const_nominal | extrapolation | 45.2 | 20.3 | +24.9 | [+21.7, +28.3] | +0.54 |  |
| primary | residual - const_nominal | all | 82.6 | 69.3 | +13.3 | [+12.0, +14.7] | +0.31 | 0.000 |
| primary | combined - combined_no_phase | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - combined_no_phase | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - combined_no_phase | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| primary | combined - combined_no_phase | extrapolation | 84.4 | 85.2 | -0.8 | [-2.5, +0.8] | -0.02 |  |
| primary | combined - combined_no_phase | all | 96.1 | 96.3 | -0.2 | [-0.6, +0.2] | -0.01 | 0.366 |
| secondary_final_checkpoint | combined - geometry_1p5cm | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - geometry_1p5cm | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - geometry_1p5cm | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - geometry_1p5cm | extrapolation | 84.7 | 86.2 | -1.4 | [-2.6, -0.5] | -0.04 |  |
| secondary_final_checkpoint | combined - geometry_1p5cm | all | 96.2 | 96.5 | -0.4 | [-0.6, -0.1] | -0.02 | 0.006 |
| secondary_final_checkpoint | combined - const_geometry_1p5cm | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - const_geometry_1p5cm | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - const_geometry_1p5cm | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - const_geometry_1p5cm | extrapolation | 84.7 | 97.0 | -12.3 | [-15.5, -9.0] | -0.45 |  |
| secondary_final_checkpoint | combined - const_geometry_1p5cm | all | 96.2 | 99.2 | -3.1 | [-3.9, -2.2] | -0.22 | 0.000 |
| secondary_final_checkpoint | residual - nominal | inner | 100.0 | 96.0 | +4.0 | [+2.9, +5.2] | +0.40 |  |
| secondary_final_checkpoint | residual - nominal | outer | 85.6 | 50.0 | +35.6 | [+31.5, +39.8] | +0.79 |  |
| secondary_final_checkpoint | residual - nominal | in_training | 95.2 | 80.7 | +14.5 | [+12.9, +16.3] | +0.47 |  |
| secondary_final_checkpoint | residual - nominal | extrapolation | 45.9 | 18.8 | +27.1 | [+23.7, +30.6] | +0.59 |  |
| secondary_final_checkpoint | residual - nominal | all | 82.9 | 65.2 | +17.7 | [+16.1, +19.2] | +0.41 | 0.000 |
| secondary_final_checkpoint | residual - const_nominal | inner | 100.0 | 99.9 | +0.1 | [+0.0, +0.2] | +0.06 |  |
| secondary_final_checkpoint | residual - const_nominal | outer | 85.6 | 57.0 | +28.6 | [+24.7, +32.7] | +0.65 |  |
| secondary_final_checkpoint | residual - const_nominal | in_training | 95.2 | 85.6 | +9.6 | [+8.2, +11.1] | +0.34 |  |
| secondary_final_checkpoint | residual - const_nominal | extrapolation | 45.9 | 20.3 | +25.6 | [+22.2, +29.0] | +0.55 |  |
| secondary_final_checkpoint | residual - const_nominal | all | 82.9 | 69.3 | +13.6 | [+12.2, +15.0] | +0.32 | 0.000 |
| secondary_final_checkpoint | combined - combined_no_phase | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - combined_no_phase | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - combined_no_phase | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| secondary_final_checkpoint | combined - combined_no_phase | extrapolation | 84.7 | 84.9 | -0.2 | [-1.1, +0.6] | -0.01 |  |
| secondary_final_checkpoint | combined - combined_no_phase | all | 96.2 | 96.2 | -0.1 | [-0.3, +0.1] | -0.00 | 0.601 |
| exploratory | untrained combined - geometry_1p5cm | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | untrained combined - geometry_1p5cm | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | untrained combined - geometry_1p5cm | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | untrained combined - geometry_1p5cm | extrapolation | 86.2 | 86.2 | +0.0 | [-0.5, +0.5] | +0.00 |  |
| exploratory | untrained combined - geometry_1p5cm | all | 96.5 | 96.5 | +0.0 | [-0.1, +0.1] | +0.00 |  |
| exploratory | selected combined - untrained combined | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | selected combined - untrained combined | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | selected combined - untrained combined | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | selected combined - untrained combined | extrapolation | 84.4 | 86.2 | -1.8 | [-3.2, -0.6] | -0.05 |  |
| exploratory | selected combined - untrained combined | all | 96.1 | 96.5 | -0.4 | [-0.8, -0.1] | -0.02 |  |
| exploratory | final combined - untrained combined | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | final combined - untrained combined | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | final combined - untrained combined | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | final combined - untrained combined | extrapolation | 84.7 | 86.2 | -1.4 | [-2.6, -0.3] | -0.04 |  |
| exploratory | final combined - untrained combined | all | 96.2 | 96.5 | -0.4 | [-0.7, -0.1] | -0.02 |  |
| exploratory | selected residual - untrained residual | inner | 99.9 | 96.2 | +3.6 | [+2.6, +4.7] | +0.32 |  |
| exploratory | selected residual - untrained residual | outer | 85.5 | 50.0 | +35.5 | [+31.4, +39.6] | +0.79 |  |
| exploratory | selected residual - untrained residual | in_training | 95.1 | 80.8 | +14.3 | [+12.6, +16.0] | +0.46 |  |
| exploratory | selected residual - untrained residual | extrapolation | 45.2 | 18.7 | +26.6 | [+23.3, +30.0] | +0.58 |  |
| exploratory | selected residual - untrained residual | all | 82.6 | 65.3 | +17.3 | [+15.8, +18.9] | +0.40 |  |
| exploratory | geometry_1p5cm - geometry_1cm | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | geometry_1p5cm - geometry_1cm | outer | 100.0 | 93.3 | +6.7 | [+4.7, +8.7] | +0.52 |  |
| exploratory | geometry_1p5cm - geometry_1cm | in_training | 100.0 | 97.8 | +2.2 | [+1.6, +2.9] | +0.30 |  |
| exploratory | geometry_1p5cm - geometry_1cm | extrapolation | 86.2 | 74.3 | +11.8 | [+9.3, +14.5] | +0.30 |  |
| exploratory | geometry_1p5cm - geometry_1cm | all | 96.5 | 91.9 | +4.6 | [+3.8, +5.5] | +0.20 |  |
| exploratory | const_geometry_1p5cm - geometry_1p5cm | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | const_geometry_1p5cm - geometry_1p5cm | outer | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | const_geometry_1p5cm - geometry_1p5cm | in_training | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | const_geometry_1p5cm - geometry_1p5cm | extrapolation | 97.0 | 86.2 | +10.8 | [+7.7, +14.0] | +0.41 |  |
| exploratory | const_geometry_1p5cm - geometry_1p5cm | all | 99.2 | 96.5 | +2.7 | [+1.9, +3.5] | +0.20 |  |
| exploratory | const_nominal - nominal | inner | 99.9 | 96.0 | +3.9 | [+2.8, +5.1] | +0.34 |  |
| exploratory | const_nominal - nominal | outer | 57.0 | 50.0 | +7.0 | [+3.0, +11.0] | +0.14 |  |
| exploratory | const_nominal - nominal | in_training | 85.6 | 80.7 | +4.9 | [+3.4, +6.5] | +0.13 |  |
| exploratory | const_nominal - nominal | extrapolation | 20.3 | 18.8 | +1.5 | [-1.0, +4.0] | +0.04 |  |
| exploratory | const_nominal - nominal | all | 69.3 | 65.2 | +4.1 | [+2.8, +5.4] | +0.09 |  |
| exploratory | const_geometry_1cm - geometry_1cm | inner | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | +0.00 |  |
| exploratory | const_geometry_1cm - geometry_1cm | outer | 99.8 | 93.3 | +6.5 | [+4.5, +8.5] | +0.44 |  |
| exploratory | const_geometry_1cm - geometry_1cm | in_training | 99.9 | 97.8 | +2.2 | [+1.5, +2.9] | +0.25 |  |
| exploratory | const_geometry_1cm - geometry_1cm | extrapolation | 80.7 | 74.3 | +6.3 | [+3.3, +9.5] | +0.15 |  |
| exploratory | const_geometry_1cm - geometry_1cm | all | 95.1 | 91.9 | +3.2 | [+2.3, +4.1] | +0.13 |  |
| exploratory | geometry_1p5cm - nominal | inner | 100.0 | 96.0 | +4.0 | [+2.9, +5.2] | +0.40 |  |
| exploratory | geometry_1p5cm - nominal | outer | 100.0 | 50.0 | +50.0 | [+46.0, +54.0] | +1.57 |  |
| exploratory | geometry_1p5cm - nominal | in_training | 100.0 | 80.7 | +19.3 | [+17.6, +21.1] | +0.91 |  |
| exploratory | geometry_1p5cm - nominal | extrapolation | 86.2 | 18.8 | +67.3 | [+63.7, +71.2] | +1.48 |  |
| exploratory | geometry_1p5cm - nominal | all | 96.5 | 65.2 | +31.3 | [+29.5, +33.2] | +0.89 |  |

Collision-episode rate differences (pp):

| analysis | comparison | cases | A - B | 95% CI |
|---|---|---|---|---|
| primary | combined - geometry_1p5cm | extrapolation | +2.6 | [+1.3, +3.9] |
| primary | combined - geometry_1p5cm | all | +0.7 | [+0.3, +1.1] |
| primary | combined - const_geometry_1p5cm | extrapolation | +16.6 | [+13.6, +19.6] |
| primary | combined - const_geometry_1p5cm | all | +4.2 | [+3.4, +5.0] |
| primary | residual - nominal | extrapolation | -7.7 | [-10.9, -4.7] |
| primary | residual - nominal | all | -2.0 | [-6.9, +1.4] |
| primary | residual - const_nominal | extrapolation | +5.9 | [+2.7, +9.4] |
| primary | residual - const_nominal | all | +8.8 | [+3.7, +12.3] |
| primary | combined - combined_no_phase | extrapolation | +1.8 | [-0.1, +3.8] |
| primary | combined - combined_no_phase | all | +0.5 | [+0.0, +1.0] |
| secondary_final_checkpoint | combined - geometry_1p5cm | extrapolation | +2.4 | [+1.3, +3.8] |
| secondary_final_checkpoint | combined - geometry_1p5cm | all | +0.7 | [+0.3, +1.0] |
| secondary_final_checkpoint | combined - const_geometry_1p5cm | extrapolation | +16.4 | [+13.5, +19.4] |
| secondary_final_checkpoint | combined - const_geometry_1p5cm | all | +4.2 | [+3.3, +5.0] |
| secondary_final_checkpoint | residual - nominal | extrapolation | -6.4 | [-10.2, -3.1] |
| secondary_final_checkpoint | residual - nominal | all | -1.6 | [-7.0, +2.0] |
| secondary_final_checkpoint | residual - const_nominal | extrapolation | +7.2 | [+3.4, +11.2] |
| secondary_final_checkpoint | residual - const_nominal | all | +9.1 | [+3.5, +13.0] |
| secondary_final_checkpoint | combined - combined_no_phase | extrapolation | +0.2 | [-0.7, +1.2] |
| secondary_final_checkpoint | combined - combined_no_phase | all | +0.1 | [-0.2, +0.4] |

## Geometry component ablations and alignment bounds (held-out)

**Alignment bound 1cm** — success %

| combination | inner | outer | in_training | extrapolation | all |
|---|---|---|---|---|---|
| none | 96.2 | 50.0 | 80.8 | 18.5 | 65.2 |
| A | 100.0 | 85.3 | 95.1 | 49.0 | 83.6 |
| H | 96.2 | 50.3 | 80.9 | 18.0 | 65.2 |
| G | 96.0 | 68.7 | 86.9 | 29.3 | 72.5 |
| AH | 100.0 | 85.2 | 95.1 | 49.2 | 83.6 |
| AG | 100.0 | 93.3 | 97.8 | 74.5 | 92.0 |
| HG | 96.1 | 69.2 | 87.1 | 29.0 | 72.6 |
| AHG | 100.0 | 93.3 | 97.8 | 74.3 | 91.9 |

| effect | inner | outer | in_training | extrapolation | all |
|---|---|---|---|---|---|
| A | +3.9 [+2.8, +5.0] | +29.8 [+26.4, +33.0] | +12.5 [+11.1, +14.0] | +38.0 [+34.6, +41.6] | +18.9 [+17.5, +20.3] |
| H | +0.0 [-0.1, +0.2] | +0.2 [-0.1, +0.5] | +0.1 [-0.0, +0.2] | -0.2 [-0.6, +0.1] | +0.0 [-0.1, +0.1] |
| G | -0.1 [-0.2, -0.0] | +13.4 [+11.2, +15.8] | +4.4 [+3.6, +5.2] | +18.1 [+15.6, +21.0] | +7.8 [+6.9, +8.8] |
| AH | -0.0 [-0.2, +0.1] | -0.2 [-0.6, +0.0] | -0.1 [-0.2, +0.0] | +0.2 [-0.1, +0.6] | -0.0 [-0.2, +0.1] |
| AG | +0.1 [+0.0, +0.2] | -5.3 [-6.9, -3.9] | -1.7 [-2.2, -1.2] | +7.2 [+5.8, +8.7] | +0.5 [-0.0, +1.1] |
| HG | +0.0 [-0.1, +0.1] | +0.1 [-0.1, +0.3] | +0.0 [-0.1, +0.1] | -0.0 [-0.4, +0.2] | +0.0 [-0.1, +0.1] |
| AHG | +0.0 [-0.1, +0.1] | +0.0 [-0.2, +0.2] | +0.0 [-0.1, +0.1] | -0.1 [-0.4, +0.2] | -0.0 [-0.1, +0.1] |

**Alignment bound 1.5cm** — success %

| combination | inner | outer | in_training | extrapolation | all |
|---|---|---|---|---|---|
| none | 96.2 | 50.0 | 80.8 | 18.7 | 65.3 |
| A | 100.0 | 99.0 | 99.7 | 57.5 | 89.1 |
| H | 96.2 | 50.3 | 80.9 | 18.0 | 65.2 |
| G | 96.2 | 68.7 | 87.0 | 29.3 | 72.6 |
| AH | 100.0 | 99.0 | 99.7 | 57.5 | 89.1 |
| AG | 100.0 | 100.0 | 100.0 | 86.5 | 96.6 |
| HG | 96.0 | 69.2 | 87.1 | 27.8 | 72.2 |
| AHG | 100.0 | 100.0 | 100.0 | 86.2 | 96.5 |

| effect | inner | outer | in_training | extrapolation | all |
|---|---|---|---|---|---|
| A | +3.8 [+2.8, +4.9] | +40.0 [+36.5, +43.4] | +15.9 [+14.3, +17.4] | +48.5 [+45.0, +52.2] | +24.0 [+22.5, +25.6] |
| H | -0.0 [-0.2, +0.1] | +0.2 [+0.0, +0.5] | +0.0 [-0.1, +0.2] | -0.6 [-1.1, -0.2] | -0.1 [-0.3, +0.0] |
| G | -0.1 [-0.2, +0.0] | +9.9 [+8.3, +11.6] | +3.2 [+2.6, +3.8] | +19.5 [+17.0, +22.3] | +7.3 [+6.5, +8.2] |
| AH | +0.0 [-0.1, +0.2] | -0.2 [-0.5, -0.0] | -0.0 [-0.2, +0.1] | +0.5 [+0.0, +0.9] | +0.1 [-0.1, +0.2] |
| AG | +0.1 [-0.0, +0.2] | -8.9 [-10.5, -7.4] | -2.9 [-3.5, -2.3] | +9.3 [+7.8, +11.0] | +0.1 [-0.5, +0.8] |
| HG | -0.0 [-0.1, +0.1] | +0.0 [-0.1, +0.2] | -0.0 [-0.1, +0.1] | -0.3 [-0.6, -0.0] | -0.1 [-0.2, +0.0] |
| AHG | +0.0 [-0.1, +0.1] | -0.0 [-0.2, +0.1] | +0.0 [-0.1, +0.1] | +0.1 [-0.1, +0.4] | +0.0 [-0.1, +0.1] |

| alignment bound | inner | outer | in_training | extrapolation | all |
|---|---|---|---|---|---|
| 0.005 m | 100.0 | 85.8 | 95.3 | 50.3 | 84.0 |
| 0.010 m | 100.0 | 93.3 | 97.8 | 74.3 | 91.9 |
| 0.015 m | 100.0 | 100.0 | 100.0 | 86.2 | 96.5 |
| 0.020 m | 100.0 | 100.0 | 100.0 | 93.2 | 98.3 |

## Residual behaviour of learned policies (held-out, episode means over scored steps)

| entry | mean signed residual x/y/z [mm] | across-case std x/y/z [mm] | slope x vs object x | corr | RMS [mm] | failures (object x > +20 mm) |
|---|---|---|---|---|---|---|
| combined_no_phase_seed11__final | -1.88 / +0.33 / -0.77 | 0.41 / 0.38 / 1.03 | +0.006 | +0.15 | 3.07 | 91 (90) |
| combined_no_phase_seed11__selected | -2.01 / +0.88 / -0.91 | 0.43 / 0.33 / 1.05 | +0.011 | +0.28 | 3.30 | 93 (92) |
| combined_no_phase_seed22__final | -0.93 / -0.27 / +1.14 | 0.28 / 0.43 / 0.70 | +0.007 | +0.27 | 2.99 | 87 (87) |
| combined_no_phase_seed22__selected | +1.01 / -0.42 / +5.05 | 1.12 / 0.79 / 0.31 | -0.039 | -0.37 | 6.68 | 93 (77) |
| combined_no_phase_seed33__final | -0.99 / -0.74 / -0.35 | 0.28 / 0.66 / 0.69 | -0.004 | -0.14 | 2.91 | 93 (92) |
| combined_no_phase_seed33__selected | -0.41 / -3.28 / +2.40 | 0.71 / 0.79 / 0.82 | -0.014 | -0.22 | 4.77 | 81 (79) |
| combined_seed11__final | -2.12 / +0.44 / -0.94 | 0.31 / 0.32 / 0.83 | -0.013 | -0.44 | 3.98 | 92 (92) |
| combined_seed11__selected | -2.44 / +0.32 / -0.93 | 0.30 / 0.37 / 0.73 | -0.008 | -0.30 | 4.26 | 97 (96) |
| combined_seed22__final | -2.08 / +1.10 / -1.12 | 0.28 / 0.42 / 0.76 | +0.015 | +0.58 | 3.34 | 91 (91) |
| combined_seed22__selected | -2.08 / +1.10 / -1.12 | 0.28 / 0.42 / 0.76 | +0.015 | +0.58 | 3.34 | 92 (92) |
| combined_seed33__final | -1.17 / +3.03 / -3.25 | 0.57 / 0.45 / 1.11 | -0.001 | -0.02 | 6.42 | 92 (92) |
| combined_seed33__selected | -1.17 / +3.03 / -3.25 | 0.57 / 0.45 / 1.12 | -0.001 | -0.02 | 6.42 | 92 (92) |
| residual_seed11__final | -1.16 / -0.26 / -1.04 | 2.06 / 1.07 / 2.87 | +0.126 | +0.66 | 6.56 | 423 (88) |
| residual_seed11__selected | -1.17 / -0.26 / -1.04 | 2.04 / 1.07 / 2.87 | +0.125 | +0.66 | 6.56 | 427 (93) |
| residual_seed22__final | -2.88 / +1.73 / +0.80 | 2.12 / 1.18 / 2.60 | +0.116 | +0.58 | 7.87 | 411 (91) |
| residual_seed22__selected | -2.89 / +1.74 / +0.80 | 2.11 / 1.19 / 2.60 | +0.115 | +0.58 | 7.88 | 414 (94) |
| residual_seed33__final | -1.77 / +3.83 / -0.91 | 1.52 / 1.77 / 2.32 | +0.094 | +0.66 | 8.01 | 399 (91) |
| residual_seed33__selected | -1.83 / +4.01 / -0.34 | 1.59 / 1.58 / 2.26 | +0.097 | +0.65 | 7.80 | 410 (92) |

## Checkpoint selection (validation, 400 cases)

| run | candidates (success % / collision % / RMS residual mm) | selected | tied on success |
|---|---|---|---|
| combined_no_phase_seed11 | 002031616: 98.0/2.0/4.76; 004030464: 97.0/3.2/4.13; 006029312: 97.8/2.5/3.39; 008028160: 98.0/2.0/3.35; 010027008: 98.0/2.2/3.07 | step_008028160 | 3 |
| combined_no_phase_seed22 | 002031616: 98.5/2.0/6.64; 004030464: 98.2/2.0/4.30; 006029312: 98.0/2.0/3.04; 008028160: 98.0/2.0/2.90; 010027008: 98.0/2.0/3.03 | step_002031616 | 1 |
| combined_no_phase_seed33 | 002031616: 98.2/1.8/4.89; 004030464: 98.0/2.0/2.81; 006029312: 97.5/3.2/3.71; 008028160: 98.0/2.0/2.91; 010027008: 98.0/2.0/2.97 | step_002031616 | 1 |
| combined_seed11 | 002031616: 98.0/2.2/5.81; 004030464: 96.2/3.8/5.66; 006029312: 98.0/2.5/4.52; 008028160: 98.0/2.2/4.15; 010027008: 98.0/2.5/3.91 | step_008028160 | 4 |
| combined_seed22 | 002031616: 94.2/7.2/5.88; 004030464: 97.8/3.2/4.75; 006029312: 98.0/2.2/3.82; 008028160: 98.0/2.0/3.50; 010027008: 98.0/2.0/3.38 | step_010027008 | 3 |
| combined_seed33 | 002031616: 95.8/8.0/10.03; 004030464: 97.8/3.2/9.18; 006029312: 98.0/2.8/7.78; 008028160: 98.0/2.0/6.73; 010027008: 98.2/2.5/6.48 | step_010027008 | 1 |
| residual_seed11 | 002031616: 57.5/27.8/7.75; 004030464: 69.0/24.8/8.25; 006029312: 85.2/29.2/7.71; 008028160: 95.2/27.0/6.91; 010027008: 95.8/20.5/6.43 | step_010027008 | 1 |
| residual_seed22 | 002031616: 65.2/31.5/9.96; 004030464: 79.0/21.0/7.89; 006029312: 89.0/31.5/8.09; 008028160: 95.0/32.8/7.73; 010027008: 95.0/29.8/7.50 | step_010027008 | 2 |
| residual_seed33 | 002031616: 60.5/27.8/10.77; 004030464: 73.2/31.5/8.27; 006029312: 86.8/31.0/7.56; 008028160: 94.2/26.5/7.62; 010027008: 94.2/30.2/7.76 | step_008028160 | 2 |
