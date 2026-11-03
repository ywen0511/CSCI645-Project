# Generated tables (do not edit; regenerate with scripts/analyze.py)

## Success rate (%) by method and condition (mean over training seeds; sd in parentheses)

| condition | nominal | geometry | residual | combined | combined_no_phase |
|---|---|---|---|---|---|
| clean | 100.0 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| position_in | 91.5 | 100.0 | 99.8 (0.3) | 100.0 (0.0) | 100.0 (0.0) |
| position_stress | 66.0 | 92.0 | 70.0 (3.0) | 93.5 (4.8) | 94.0 (6.1) |
| timing_early_in | 100.0 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| timing_late_in | 100.0 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| joint_early_in | 90.5 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| joint_late_in | 91.0 | 100.0 | 99.8 (0.3) | 100.0 (0.0) | 100.0 (0.0) |
| joint_early_stress | 11.5 | 94.5 | 15.2 (6.0) | 95.3 (5.1) | 96.0 (5.6) |
| joint_late_stress | 66.0 | 93.5 | 73.5 (4.4) | 94.7 (5.8) | 95.5 (5.6) |
| ALL_IN_RANGE | 95.5 | 100.0 | 99.9 (0.1) | 100.0 (0.0) | 100.0 (0.0) |
| ALL_STRESS | 47.8 | 93.3 | 52.9 (4.4) | 94.5 (5.2) | 95.2 (5.8) |

## Drop rate (%)

| condition | nominal | geometry | residual | combined | combined_no_phase |
|---|---|---|---|---|---|
| clean | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| position_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| position_stress | 2.5 | 0.0 | 1.8 | 0.0 | 0.0 |
| timing_early_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| timing_late_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| joint_early_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| joint_late_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| joint_early_stress | 13.0 | 0.0 | 9.0 | 0.0 | 0.0 |
| joint_late_stress | 3.5 | 0.0 | 2.0 | 0.0 | 0.0 |

## Paired differences in success rate (percentage points, 95% bootstrap CI)

| comparison | condition | diff | CI |
|---|---|---|---|
| combined - nominal | clean | +0.0 | [+0.0, +0.0] |
| combined - nominal | position_in | +8.5 | [+5.0, +12.5] |
| combined - nominal | position_stress | +27.5 | [+20.0, +34.8] |
| combined - nominal | timing_early_in | +0.0 | [+0.0, +0.0] |
| combined - nominal | timing_late_in | +0.0 | [+0.0, +0.0] |
| combined - nominal | joint_early_in | +9.5 | [+5.5, +14.0] |
| combined - nominal | joint_late_in | +9.0 | [+5.5, +13.5] |
| combined - nominal | joint_early_stress | +83.8 | [+76.5, +90.0] |
| combined - nominal | joint_late_stress | +28.7 | [+20.5, +36.5] |
| combined - nominal | ALL_IN_RANGE | +4.5 | [+3.3, +5.7] |
| combined - nominal | ALL_STRESS | +46.7 | [+40.3, +52.6] |
| combined - geometry | clean | +0.0 | [+0.0, +0.0] |
| combined - geometry | position_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | position_stress | +1.5 | [-3.8, +6.3] |
| combined - geometry | timing_early_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | timing_late_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | joint_early_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | joint_late_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | joint_early_stress | +0.8 | [-4.8, +5.5] |
| combined - geometry | joint_late_stress | +1.2 | [-5.0, +6.5] |
| combined - geometry | ALL_IN_RANGE | +0.0 | [+0.0, +0.0] |
| combined - geometry | ALL_STRESS | +1.2 | [-4.3, +5.4] |
| combined - residual | clean | +0.0 | [+0.0, +0.0] |
| combined - residual | position_in | +0.2 | [+0.0, +1.0] |
| combined - residual | position_stress | +23.5 | [+16.2, +31.2] |
| combined - residual | timing_early_in | +0.0 | [+0.0, +0.0] |
| combined - residual | timing_late_in | +0.0 | [+0.0, +0.0] |
| combined - residual | joint_early_in | +0.0 | [+0.0, +0.0] |
| combined - residual | joint_late_in | +0.2 | [+0.0, +1.0] |
| combined - residual | joint_early_stress | +80.2 | [+70.7, +88.5] |
| combined - residual | joint_late_stress | +21.2 | [+12.8, +29.7] |
| combined - residual | ALL_IN_RANGE | +0.1 | [+0.0, +0.2] |
| combined - residual | ALL_STRESS | +41.6 | [+33.8, +48.7] |
| combined - combined_no_phase | clean | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | position_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | position_stress | -0.5 | [-8.0, +7.3] |
| combined - combined_no_phase | timing_early_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | timing_late_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | joint_early_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | joint_late_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | joint_early_stress | -0.7 | [-8.2, +6.7] |
| combined - combined_no_phase | joint_late_stress | -0.8 | [-8.7, +7.0] |
| combined - combined_no_phase | ALL_IN_RANGE | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | ALL_STRESS | -0.7 | [-7.7, +6.6] |
| geometry - nominal | clean | +0.0 | [+0.0, +0.0] |
| geometry - nominal | position_in | +8.5 | [+5.0, +12.5] |
| geometry - nominal | position_stress | +26.0 | [+20.0, +32.0] |
| geometry - nominal | timing_early_in | +0.0 | [+0.0, +0.0] |
| geometry - nominal | timing_late_in | +0.0 | [+0.0, +0.0] |
| geometry - nominal | joint_early_in | +9.5 | [+5.5, +13.5] |
| geometry - nominal | joint_late_in | +9.0 | [+5.0, +13.0] |
| geometry - nominal | joint_early_stress | +83.0 | [+78.0, +88.0] |
| geometry - nominal | joint_late_stress | +27.5 | [+21.5, +34.0] |
| geometry - nominal | ALL_IN_RANGE | +4.5 | [+3.4, +5.7] |
| geometry - nominal | ALL_STRESS | +45.5 | [+41.5, +49.5] |
| residual - nominal | clean | +0.0 | [+0.0, +0.0] |
| residual - nominal | position_in | +8.3 | [+4.8, +12.3] |
| residual - nominal | position_stress | +4.0 | [+0.0, +8.5] |
| residual - nominal | timing_early_in | +0.0 | [+0.0, +0.0] |
| residual - nominal | timing_late_in | +0.0 | [+0.0, +0.0] |
| residual - nominal | joint_early_in | +9.5 | [+5.5, +14.0] |
| residual - nominal | joint_late_in | +8.8 | [+5.0, +13.0] |
| residual - nominal | joint_early_stress | +3.7 | [-1.7, +10.5] |
| residual - nominal | joint_late_stress | +7.5 | [+2.2, +13.5] |
| residual - nominal | ALL_IN_RANGE | +4.4 | [+3.3, +5.6] |
| residual - nominal | ALL_STRESS | +5.1 | [+1.2, +10.0] |

Count reconciliation: scheduled 19800, recorded 19800, invalid resets 0, infrastructure errors 0.
