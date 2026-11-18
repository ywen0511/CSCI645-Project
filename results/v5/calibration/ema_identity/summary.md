# V5 Study A - EMA alpha 1.0 vs 0.2, field by field

Paired episodes compared: 9,600. All record fields identical except identifiers (config_hash, controller_hash, entry_id, run_id, sensor_ema_alpha): **yes**.

| Pair (alpha 1.0 vs 0.2) | Cases | Identical terminal outcomes | Non-identifier record fields that differ |
|---|---:|---:|---|
| `ema1p0_fixed_a15` vs `ema0p2_fixed_a15` | 2,400 | 2,400 | none |
| `ema1p0_fixed_a25` vs `ema0p2_fixed_a25` | 2,400 | 2,400 | none |
| `ema1p0_cal050_a15` vs `ema0p2_cal050_a15` | 2,400 | 2,400 | none |
| `ema1p0_cal050_a25` vs `ema0p2_cal050_a25` | 2,400 | 2,400 | none |

Traces (460 samples): the controller's object estimate differs in 164 samples after giver release, 32 samples settling; executed receiver command differs in 0 samples; other differing fields: none.
