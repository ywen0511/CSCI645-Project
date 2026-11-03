# Generated tables (do not edit; regenerate with scripts/analyze.py)

## Success rate (%) by method and condition (mean over training seeds; sd in parentheses)

| condition | nominal | geometry | residual | combined | combined_no_phase |
|---|---|---|---|---|---|
| clean | 100.0 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| position_in | 91.5 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| position_stress | 66.0 | 92.0 | 75.2 (1.6) | 88.8 (3.4) | 89.3 (2.3) |
| timing_early_in | 100.0 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| timing_late_in | 100.0 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| joint_early_in | 90.5 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| joint_late_in | 91.0 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| joint_early_stress | 11.5 | 94.5 | 16.3 (7.3) | 90.8 (2.5) | 91.2 (1.2) |
| joint_late_stress | 66.0 | 93.5 | 75.8 (2.4) | 90.2 (2.0) | 90.5 (1.5) |
| ALL_IN_RANGE | 95.5 | 100.0 | 100.0 (0.0) | 100.0 (0.0) | 100.0 (0.0) |
| ALL_STRESS | 47.8 | 93.3 | 55.8 (3.1) | 89.9 (2.6) | 90.3 (1.6) |

## Drop rate (%)

| condition | nominal | geometry | residual | combined | combined_no_phase |
|---|---|---|---|---|---|
| clean | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| position_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| position_stress | 2.5 | 0.0 | 0.0 | 0.0 | 0.0 |
| timing_early_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| timing_late_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| joint_early_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| joint_late_in | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| joint_early_stress | 13.0 | 0.0 | 0.7 | 0.0 | 0.0 |
| joint_late_stress | 3.5 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired differences in success rate (percentage points, 95% bootstrap CI)

| comparison | condition | diff | CI |
|---|---|---|---|
| combined - nominal | clean | +0.0 | [+0.0, +0.0] |
| combined - nominal | position_in | +8.5 | [+5.0, +12.5] |
| combined - nominal | position_stress | +22.8 | [+16.7, +29.5] |
| combined - nominal | timing_early_in | +0.0 | [+0.0, +0.0] |
| combined - nominal | timing_late_in | +0.0 | [+0.0, +0.0] |
| combined - nominal | joint_early_in | +9.5 | [+5.5, +14.0] |
| combined - nominal | joint_late_in | +9.0 | [+5.5, +13.5] |
| combined - nominal | joint_early_stress | +79.3 | [+73.2, +85.2] |
| combined - nominal | joint_late_stress | +24.2 | [+18.2, +30.5] |
| combined - nominal | ALL_IN_RANGE | +4.5 | [+3.3, +5.7] |
| combined - nominal | ALL_STRESS | +42.1 | [+37.6, +46.6] |
| combined - geometry | clean | +0.0 | [+0.0, +0.0] |
| combined - geometry | position_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | position_stress | -3.2 | [-7.3, -0.3] |
| combined - geometry | timing_early_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | timing_late_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | joint_early_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | joint_late_in | +0.0 | [+0.0, +0.0] |
| combined - geometry | joint_early_stress | -3.7 | [-7.3, -1.0] |
| combined - geometry | joint_late_stress | -3.3 | [-6.7, -0.8] |
| combined - geometry | ALL_IN_RANGE | +0.0 | [+0.0, +0.0] |
| combined - geometry | ALL_STRESS | -3.4 | [-6.3, -1.1] |
| combined - residual | clean | +0.0 | [+0.0, +0.0] |
| combined - residual | position_in | +0.0 | [+0.0, +0.0] |
| combined - residual | position_stress | +13.7 | [+8.3, +19.5] |
| combined - residual | timing_early_in | +0.0 | [+0.0, +0.0] |
| combined - residual | timing_late_in | +0.0 | [+0.0, +0.0] |
| combined - residual | joint_early_in | +0.0 | [+0.0, +0.0] |
| combined - residual | joint_late_in | +0.0 | [+0.0, +0.0] |
| combined - residual | joint_early_stress | +74.5 | [+65.0, +83.0] |
| combined - residual | joint_late_stress | +14.3 | [+9.2, +19.8] |
| combined - residual | ALL_IN_RANGE | +0.0 | [+0.0, +0.0] |
| combined - residual | ALL_STRESS | +34.2 | [+28.9, +39.3] |
| combined - combined_no_phase | clean | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | position_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | position_stress | -0.5 | [-4.8, +3.5] |
| combined - combined_no_phase | timing_early_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | timing_late_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | joint_early_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | joint_late_in | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | joint_early_stress | -0.3 | [-3.5, +2.3] |
| combined - combined_no_phase | joint_late_stress | -0.3 | [-3.2, +2.3] |
| combined - combined_no_phase | ALL_IN_RANGE | +0.0 | [+0.0, +0.0] |
| combined - combined_no_phase | ALL_STRESS | -0.4 | [-3.4, +2.4] |
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
| residual - nominal | position_in | +8.5 | [+5.0, +12.5] |
| residual - nominal | position_stress | +9.2 | [+5.5, +13.5] |
| residual - nominal | timing_early_in | +0.0 | [+0.0, +0.0] |
| residual - nominal | timing_late_in | +0.0 | [+0.0, +0.0] |
| residual - nominal | joint_early_in | +9.5 | [+5.5, +14.0] |
| residual - nominal | joint_late_in | +9.0 | [+5.5, +13.5] |
| residual - nominal | joint_early_stress | +4.8 | [-1.8, +12.7] |
| residual - nominal | joint_late_stress | +9.8 | [+5.7, +14.5] |
| residual - nominal | ALL_IN_RANGE | +4.5 | [+3.3, +5.7] |
| residual - nominal | ALL_STRESS | +7.9 | [+4.6, +11.7] |

Count reconciliation: scheduled 19800, recorded 19800, invalid resets 0, infrastructure errors 0.
