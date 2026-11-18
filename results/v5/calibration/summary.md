# V5 Study A - matched calibration ablation (preregistered)

| Primary | Condition | Calibrated minus fixed (pp) | 95% CI | 97.5% CI | Calibration-only improvement |
|---|---|---:|---|---|---|
| A1 | mixed_id | +29.5 | [+23.5, +36.0] | [+22.5, +36.5] | supported |
| A2 | grasp_15mm | +93.0 | [+89.0, +96.0] | [+88.5, +96.5] | supported |

Exploratory factorial main effects (95% CI):

| Condition | Factor | Effect (pp) | 95% CI |
|---|---|---:|---|
| mixed_id | reference (cal050 minus fixed) | +24.8 | [+19.2, +30.5] |
| mixed_id | ema (ema0p2 minus ema1p0) | +0.0 | [+0.0, +0.0] |
| mixed_id | bound (a25 minus a15) | +3.2 | [+1.3, +5.3] |
| grasp_15mm | reference (cal050 minus fixed) | +79.8 | [+75.5, +83.8] |
| grasp_15mm | ema (ema0p2 minus ema1p0) | +0.0 | [+0.0, +0.0] |
| grasp_15mm | bound (a25 minus a15) | +5.8 | [+2.3, +9.3] |
| mixed_ood | reference (cal050 minus fixed) | +17.8 | [+12.0, +23.5] |
| mixed_ood | ema (ema0p2 minus ema1p0) | +0.0 | [+0.0, +0.0] |
| mixed_ood | bound (a25 minus a15) | +3.2 | [+1.0, +5.7] |

Success (%) by configuration and condition:

| Config | bias_5mm | boundary_x_minus_7 | boundary_z_15 | clean | delay_2step | grasp_10mm | grasp_15mm | grasp_2mm | grasp_5mm | mixed_id | mixed_ood | noise_2mm |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ema1p0_fixed_a15 | 100.0 | 96.0 | 100.0 | 100.0 | 100.0 | 39.0 | 7.5 | 100.0 | 96.0 | 72.0 | 74.5 | 100.0 |
| ema1p0_fixed_a25 | 100.0 | 96.0 | 100.0 | 100.0 | 100.0 | 40.5 | 0.0 | 100.0 | 100.0 | 70.5 | 74.5 | 100.0 |
| ema1p0_cal050_a15 | 100.0 | 96.0 | 100.0 | 100.0 | 100.0 | 85.5 | 74.0 | 100.0 | 96.0 | 92.0 | 89.0 | 100.0 |
| ema1p0_cal050_a25 | 100.0 | 97.5 | 100.0 | 100.0 | 100.0 | 100.0 | 93.0 | 100.0 | 100.0 | 100.0 | 95.5 | 100.0 |
| ema0p2_fixed_a15 | 100.0 | 96.0 | 100.0 | 100.0 | 100.0 | 39.0 | 7.5 | 100.0 | 96.0 | 72.0 | 74.5 | 100.0 |
| ema0p2_fixed_a25 | 100.0 | 96.0 | 100.0 | 100.0 | 100.0 | 40.5 | 0.0 | 100.0 | 100.0 | 70.5 | 74.5 | 100.0 |
| ema0p2_cal050_a15 | 100.0 | 96.0 | 100.0 | 100.0 | 100.0 | 85.5 | 74.0 | 100.0 | 96.0 | 92.0 | 89.0 | 100.0 |
| ema0p2_cal050_a25 | 100.0 | 97.5 | 100.0 | 100.0 | 100.0 | 100.0 | 93.0 | 100.0 | 100.0 | 100.0 | 95.5 | 100.0 |
