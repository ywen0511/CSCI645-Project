# V5 Study B - dynamic in-grasp slip (preregistered analysis)

| Primary | Contrast | Condition | Difference (pp) | 95% CI | 97.5% CI | Superiority |
|---|---|---|---:|---|---|---|
| B1 | slip_robust_history - slip_robust_ff | slip_mixed_id | -1.0 | [-3.1, +0.9] | [-3.4, +1.3] | not established |
| B2 | slip_robust_history - geometry_best | slip_mixed_id | +0.9 | [-2.2, +4.1] | [-2.6, +4.6] | not established |

Success (%) by method and condition (learned: five seeds pooled):

| Method | Checkpoints | clean | static_mixed_id | slip_pos_5 | slip_pos_8 | slip_after_offset | slip_mixed_id | slip_mixed_ood |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| nominal | baseline | 100.0 | 52.5 | 60.0 | 52.0 | 62.0 | 46.0 | 48.5 |
| geometry_fixed | baseline | 100.0 | 69.0 | 94.0 | 77.0 | 98.5 | 52.5 | 59.5 |
| geometry_ema | baseline | 100.0 | 100.0 | 100.0 | 95.5 | 97.5 | 92.0 | 85.5 |
| geometry_calibrated | baseline | 100.0 | 100.0 | 100.0 | 97.5 | 99.5 | 90.0 | 80.5 |
| geometry_tracking | baseline | 100.0 | 100.0 | 100.0 | 96.5 | 99.5 | 92.0 | 87.5 |
| best_constant_geometry | baseline | 100.0 | 100.0 | 100.0 | 97.5 | 99.0 | 94.5 | 92.5 |
| geometry_best | baseline | 100.0 | 100.0 | 100.0 | 96.5 | 99.5 | 92.0 | 87.5 |
| slip_robust_ff | selected | 100.0 | 99.9 | 100.0 | 96.8 | 98.9 | 93.9 | 90.7 |
| slip_robust_ff | final | 100.0 | 100.0 | 100.0 | 97.0 | 98.8 | 93.8 | 90.9 |
| slip_robust_history | selected | 100.0 | 99.0 | 100.0 | 96.9 | 99.4 | 92.9 | 91.4 |
| slip_robust_history | final | 60.0 | 63.0 | 80.5 | 78.0 | 79.2 | 63.7 | 59.1 |
| slip_robust_repeat | selected | 100.0 | 100.0 | 100.0 | 97.0 | 98.9 | 94.2 | 88.9 |
| slip_robust_repeat | final | 100.0 | 100.0 | 100.0 | 96.8 | 99.0 | 93.6 | 88.8 |

Exploratory contrasts (95% CI):

| Contrast | Condition | Difference (pp) | 95% CI |
|---|---|---:|---|
| B1 (slip_robust_history - slip_robust_ff) | clean | +0.0 | [+0.0, +0.0] |
| B1 (slip_robust_history - slip_robust_ff) | static_mixed_id | -0.9 | [-3.3, +0.4] |
| B1 (slip_robust_history - slip_robust_ff) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| B1 (slip_robust_history - slip_robust_ff) | slip_pos_8 | +0.1 | [-1.7, +1.8] |
| B1 (slip_robust_history - slip_robust_ff) | slip_after_offset | +0.5 | [+0.0, +1.4] |
| B1 (slip_robust_history - slip_robust_ff) | slip_mixed_ood | +0.7 | [-3.8, +5.0] |
| B2 (slip_robust_history - geometry_best) | clean | +0.0 | [+0.0, +0.0] |
| B2 (slip_robust_history - geometry_best) | static_mixed_id | -1.0 | [-3.4, +0.0] |
| B2 (slip_robust_history - geometry_best) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| B2 (slip_robust_history - geometry_best) | slip_pos_8 | +0.4 | [-1.6, +2.3] |
| B2 (slip_robust_history - geometry_best) | slip_after_offset | -0.1 | [-0.6, +0.0] |
| B2 (slip_robust_history - geometry_best) | slip_mixed_ood | +3.9 | [-0.9, +8.7] |
| repeat_minus_ff (slip_robust_repeat - slip_robust_ff) | clean | +0.0 | [+0.0, +0.0] |
| repeat_minus_ff (slip_robust_repeat - slip_robust_ff) | static_mixed_id | +0.1 | [+0.0, +0.6] |
| repeat_minus_ff (slip_robust_repeat - slip_robust_ff) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| repeat_minus_ff (slip_robust_repeat - slip_robust_ff) | slip_pos_8 | +0.2 | [-1.1, +1.4] |
| repeat_minus_ff (slip_robust_repeat - slip_robust_ff) | slip_after_offset | +0.0 | [-0.8, +0.8] |
| repeat_minus_ff (slip_robust_repeat - slip_robust_ff) | slip_mixed_id | +0.3 | [-1.5, +2.0] |
| repeat_minus_ff (slip_robust_repeat - slip_robust_ff) | slip_mixed_ood | -1.8 | [-5.1, +1.4] |
| history_minus_repeat (slip_robust_history - slip_robust_repeat) | clean | +0.0 | [+0.0, +0.0] |
| history_minus_repeat (slip_robust_history - slip_robust_repeat) | static_mixed_id | -1.0 | [-3.4, +0.0] |
| history_minus_repeat (slip_robust_history - slip_robust_repeat) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| history_minus_repeat (slip_robust_history - slip_robust_repeat) | slip_pos_8 | -0.1 | [-1.6, +1.3] |
| history_minus_repeat (slip_robust_history - slip_robust_repeat) | slip_after_offset | +0.5 | [+0.0, +1.3] |
| history_minus_repeat (slip_robust_history - slip_robust_repeat) | slip_mixed_id | -1.3 | [-3.6, +0.9] |
| history_minus_repeat (slip_robust_history - slip_robust_repeat) | slip_mixed_ood | +2.5 | [-2.2, +7.2] |
| tracking_minus_calibrated (geometry_tracking - geometry_calibrated) | clean | +0.0 | [+0.0, +0.0] |
| tracking_minus_calibrated (geometry_tracking - geometry_calibrated) | static_mixed_id | +0.0 | [+0.0, +0.0] |
| tracking_minus_calibrated (geometry_tracking - geometry_calibrated) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| tracking_minus_calibrated (geometry_tracking - geometry_calibrated) | slip_pos_8 | -1.0 | [-2.5, +0.0] |
| tracking_minus_calibrated (geometry_tracking - geometry_calibrated) | slip_after_offset | +0.0 | [+0.0, +0.0] |
| tracking_minus_calibrated (geometry_tracking - geometry_calibrated) | slip_mixed_id | +2.0 | [-2.0, +6.0] |
| tracking_minus_calibrated (geometry_tracking - geometry_calibrated) | slip_mixed_ood | +7.0 | [+3.0, +11.5] |
| history_minus_tracking (slip_robust_history - geometry_tracking) | clean | +0.0 | [+0.0, +0.0] |
| history_minus_tracking (slip_robust_history - geometry_tracking) | static_mixed_id | -1.0 | [-3.4, +0.0] |
| history_minus_tracking (slip_robust_history - geometry_tracking) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| history_minus_tracking (slip_robust_history - geometry_tracking) | slip_pos_8 | +0.4 | [-1.6, +2.3] |
| history_minus_tracking (slip_robust_history - geometry_tracking) | slip_after_offset | -0.1 | [-0.6, +0.0] |
| history_minus_tracking (slip_robust_history - geometry_tracking) | slip_mixed_id | +0.9 | [-2.2, +4.1] |
| history_minus_tracking (slip_robust_history - geometry_tracking) | slip_mixed_ood | +3.9 | [-0.9, +8.7] |
| ff_minus_calibrated_parent (slip_robust_ff - geometry_calibrated) | clean | +0.0 | [+0.0, +0.0] |
| ff_minus_calibrated_parent (slip_robust_ff - geometry_calibrated) | static_mixed_id | -0.1 | [-0.6, +0.0] |
| ff_minus_calibrated_parent (slip_robust_ff - geometry_calibrated) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| ff_minus_calibrated_parent (slip_robust_ff - geometry_calibrated) | slip_pos_8 | -0.7 | [-2.0, +0.2] |
| ff_minus_calibrated_parent (slip_robust_ff - geometry_calibrated) | slip_after_offset | -0.6 | [-1.6, +0.0] |
| ff_minus_calibrated_parent (slip_robust_ff - geometry_calibrated) | slip_mixed_id | +3.9 | [+0.9, +7.3] |
| ff_minus_calibrated_parent (slip_robust_ff - geometry_calibrated) | slip_mixed_ood | +10.2 | [+5.9, +15.0] |
| history_minus_calibrated_parent (slip_robust_history - geometry_calibrated) | clean | +0.0 | [+0.0, +0.0] |
| history_minus_calibrated_parent (slip_robust_history - geometry_calibrated) | static_mixed_id | -1.0 | [-3.4, +0.0] |
| history_minus_calibrated_parent (slip_robust_history - geometry_calibrated) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| history_minus_calibrated_parent (slip_robust_history - geometry_calibrated) | slip_pos_8 | -0.6 | [-2.5, +0.9] |
| history_minus_calibrated_parent (slip_robust_history - geometry_calibrated) | slip_after_offset | -0.1 | [-0.6, +0.0] |
| history_minus_calibrated_parent (slip_robust_history - geometry_calibrated) | slip_mixed_id | +2.9 | [-0.8, +6.8] |
| history_minus_calibrated_parent (slip_robust_history - geometry_calibrated) | slip_mixed_ood | +10.9 | [+5.4, +16.5] |
| final_minus_selected (slip_robust_ff:final - slip_robust_ff:selected) | clean | +0.0 | [+0.0, +0.0] |
| final_minus_selected (slip_robust_ff:final - slip_robust_ff:selected) | static_mixed_id | +0.1 | [+0.0, +0.6] |
| final_minus_selected (slip_robust_ff:final - slip_robust_ff:selected) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| final_minus_selected (slip_robust_ff:final - slip_robust_ff:selected) | slip_pos_8 | +0.2 | [-0.9, +1.4] |
| final_minus_selected (slip_robust_ff:final - slip_robust_ff:selected) | slip_after_offset | -0.1 | [-1.1, +0.8] |
| final_minus_selected (slip_robust_ff:final - slip_robust_ff:selected) | slip_mixed_id | -0.1 | [-2.0, +1.8] |
| final_minus_selected (slip_robust_ff:final - slip_robust_ff:selected) | slip_mixed_ood | +0.2 | [-1.8, +2.2] |
| final_minus_selected (slip_robust_history:final - slip_robust_history:selected) | clean | -40.0 | [-80.0, +0.0] |
| final_minus_selected (slip_robust_history:final - slip_robust_history:selected) | static_mixed_id | -36.0 | [-66.1, -5.8] |
| final_minus_selected (slip_robust_history:final - slip_robust_history:selected) | slip_pos_5 | -19.5 | [-56.6, +0.0] |
| final_minus_selected (slip_robust_history:final - slip_robust_history:selected) | slip_pos_8 | -18.9 | [-55.1, +0.6] |
| final_minus_selected (slip_robust_history:final - slip_robust_history:selected) | slip_after_offset | -20.2 | [-56.7, -0.6] |
| final_minus_selected (slip_robust_history:final - slip_robust_history:selected) | slip_mixed_id | -29.2 | [-57.9, -3.9] |
| final_minus_selected (slip_robust_history:final - slip_robust_history:selected) | slip_mixed_ood | -32.3 | [-58.8, -8.2] |
| final_minus_selected (slip_robust_repeat:final - slip_robust_repeat:selected) | clean | +0.0 | [+0.0, +0.0] |
| final_minus_selected (slip_robust_repeat:final - slip_robust_repeat:selected) | static_mixed_id | +0.0 | [+0.0, +0.0] |
| final_minus_selected (slip_robust_repeat:final - slip_robust_repeat:selected) | slip_pos_5 | +0.0 | [+0.0, +0.0] |
| final_minus_selected (slip_robust_repeat:final - slip_robust_repeat:selected) | slip_pos_8 | -0.2 | [-0.9, +0.4] |
| final_minus_selected (slip_robust_repeat:final - slip_robust_repeat:selected) | slip_after_offset | +0.1 | [-0.6, +0.8] |
| final_minus_selected (slip_robust_repeat:final - slip_robust_repeat:selected) | slip_mixed_id | -0.6 | [-2.6, +1.3] |
| final_minus_selected (slip_robust_repeat:final - slip_robust_repeat:selected) | slip_mixed_ood | -0.1 | [-2.4, +2.0] |

Repeatability (second process, seed 6458601):

| Entry | Matching terminal outcomes |
|---|---:|
| nominal | 1400/1400 |
| geometry_fixed | 1400/1400 |
| geometry_ema | 1400/1400 |
| geometry_calibrated | 1400/1400 |
| geometry_tracking | 1400/1400 |
| best_constant_geometry | 1400/1400 |
| slip_robust_ff_s111__selected | 1400/1400 |
| slip_robust_history_s111__selected | 1400/1400 |
| slip_robust_repeat_s111__selected | 1400/1400 |

Regression on the V4 final suite (no slip; selected policies):

| Method | Condition | V5 slip-trained (%) | V4 selected (%) |
|---|---|---:|---:|
| slip_robust_ff | clean | 100.0 | 100.0 |
| slip_robust_ff | grasp_2mm | 100.0 | 100.0 |
| slip_robust_ff | grasp_5mm | 100.0 | 100.0 |
| slip_robust_ff | grasp_10mm | 100.0 | 100.0 |
| slip_robust_ff | grasp_15mm | 96.6 | 96.5 |
| slip_robust_ff | bias_5mm | 100.0 | 100.0 |
| slip_robust_ff | noise_2mm | 100.0 | 100.0 |
| slip_robust_ff | delay_2step | 100.0 | 100.0 |
| slip_robust_ff | mixed_id | 99.7 | 99.4 |
| slip_robust_ff | mixed_ood | 98.0 | 94.5 |
| slip_robust_ff | boundary_x_minus_7 | 95.3 | 88.2 |
| slip_robust_ff | boundary_z_15 | 100.0 | 100.0 |
| slip_robust_history | clean | 100.0 | 100.0 |
| slip_robust_history | grasp_2mm | 99.9 | 100.0 |
| slip_robust_history | grasp_5mm | 97.0 | 98.5 |
| slip_robust_history | grasp_10mm | 100.0 | 100.0 |
| slip_robust_history | grasp_15mm | 100.0 | 99.1 |
| slip_robust_history | bias_5mm | 100.0 | 100.0 |
| slip_robust_history | noise_2mm | 100.0 | 100.0 |
| slip_robust_history | delay_2step | 100.0 | 100.0 |
| slip_robust_history | mixed_id | 99.8 | 100.0 |
| slip_robust_history | mixed_ood | 97.4 | 97.0 |
| slip_robust_history | boundary_x_minus_7 | 81.9 | 65.2 |
| slip_robust_history | boundary_z_15 | 99.2 | 98.8 |
| slip_robust_repeat | clean | 100.0 | 100.0 |
| slip_robust_repeat | grasp_2mm | 100.0 | 100.0 |
| slip_robust_repeat | grasp_5mm | 100.0 | 99.8 |
| slip_robust_repeat | grasp_10mm | 100.0 | 100.0 |
| slip_robust_repeat | grasp_15mm | 96.9 | 96.2 |
| slip_robust_repeat | bias_5mm | 100.0 | 100.0 |
| slip_robust_repeat | noise_2mm | 100.0 | 100.0 |
| slip_robust_repeat | delay_2step | 100.0 | 100.0 |
| slip_robust_repeat | mixed_id | 99.8 | 99.5 |
| slip_robust_repeat | mixed_ood | 97.1 | 91.3 |
| slip_robust_repeat | boundary_x_minus_7 | 94.8 | 91.2 |
| slip_robust_repeat | boundary_z_15 | 100.0 | 100.0 |

Mechanisms on 60 slip_mixed_id cases (parent zero residual: 48):

| Run | Selected | Reversed | Current only | Dev-fitted constant |
|---|---:|---:|---:|---:|
| slip_robust_history_s111 | 52 (60) | 52 (60) | 52 (60) | 52 (60) |
| slip_robust_history_s222 | 52 (60) | 52 (60) | 52 (60) | 52 (60) |
| slip_robust_history_s333 | 52 (60) | 52 (60) | 52 (60) | 52 (60) |
| slip_robust_history_s444 | 52 (60) | 52 (60) | 52 (60) | 52 (60) |
| slip_robust_history_s555 | 52 (60) | 52 (60) | 52 (60) | 52 (60) |
