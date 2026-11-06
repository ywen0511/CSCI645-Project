# v2 cluster wrappers (LSF)

The exact job scripts used for the v2 study, with private paths replaced by environment variables:

| variable | meaning |
|---|---|
| `CSCI645_WORK` | work root holding `envs/csci645proj` (conda env), `projs/code/{csci645-project, csci645-project-exp, csci645-project-v2exp}` and `runs/` |
| `CSCI645_OPS` | folder with the user-space NVIDIA Vulkan ICD bundle `nvidia_580.159.03/` (default `$CSCI645_WORK/projs/code/csci645_ops`) |
| `LSF_QUEUE`, `LSF_HOST`, `LSF_PROFILE` | queue, optional host, and the LSF profile to source |
| `LSF_SSH` | optional command prefix to reach the LSF login node from a laptop (`wait_jobs.sh`) |

`csci645-project-exp` must be a clean clone at `experiment-v1`, `csci645-project-v2exp` a clean clone at
`experiment-v2`; the job scripts refuse dirty or untagged sources. Every GPU job requests one GPU, has a
wall-clock limit and exits when its work is done. Stage order and commands: `docs/v2/REPRODUCE.md`.

| script | stage |
|---|---|
| `stage0_job.sh` | smoke test and negative controls |
| `replay_v1_job.sh` | v1 replay with the experiment-v1 source (batch 23 and 1) |
| `matrix_job.sh MATRIX OUT` | any development matrix |
| `smoke_job.sh`, `pilot_job.sh PROTOCOL METHOD SEED TRANSITIONS RUN_ID` | pilots |
| `freeze_job.sh UTC` (CPU queue) | protocol freeze + environment lock |
| `final_train_job.sh METHOD SEED` | final training (resumes from latest.pt) + validation of candidates |
| `final_eval_job.sh MATRIX NAME` | final evaluation matrices |
| `video_job.sh PLAN` | video recording |
