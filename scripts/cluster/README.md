# Cluster wrappers (closeout)

Both wrappers are optional; the driver `scripts/closeout.py` has no scheduler dependency.

| script | purpose | configuration (environment variables) |
|---|---|---|
| `isaac_run.sh ISAAC_PYTHON <args>` | run one experiment-checkout command in an Isaac Lab v3.0.0 environment (called by the driver's simulator stages) | `CLOSEOUT_VK_ICD_DIR` (optional user-space NVIDIA Vulkan ICD folder, not distributed here), `CLOSEOUT_NODE_TMP` (node-local cache folder) |
| `lsf_submit.sh NAME HH:MM GPUS <command>` | submit one self-terminating job to IBM Spectrum LSF | `CLOSEOUT_LSF_QUEUE` (required), `CLOSEOUT_LSF_HOST`, `CLOSEOUT_LSF_PROFILE`, `CLOSEOUT_LSF_LOGS`, `CLOSEOUT_LSF_CORES` |

Example (one GPU per shard): `CLOSEOUT_LSF_QUEUE=<gpu queue> scripts/cluster/lsf_submit.sh rep0 04:00 1 python3 scripts/closeout.py --work <work> repeatability --shard 0/4 --isaac-python <isaac python>`.
With another scheduler, run the same driver command in its job script. The v2-era wrappers in
`scripts/cluster_v2/` are kept as the historical record of the v2 runs.
