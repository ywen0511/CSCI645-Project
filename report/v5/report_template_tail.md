
## 9. Compute

Every job requested one A100-SXM4-80GB GPU; GPU-hours are LSF run times (including simulator start-up), with failed
and killed jobs counted (`results/v5/compute.json`, `scripts/v5_compute.py`). Total: **{{comp.total}} GPU-hours** of
the 60 GPU-hour cap.

{{table.comp}}

## 10. Limitations

- **One slip model.** The slip is a regulated bar-axis force on a 0.15 kg bar held by friction, with slides of 0 to
  +8 mm toward the receiver. Slides toward the giver's palm and longer slides were not physically reliable in this
  setup and are not tested. Rotational slip, multiple slips, slip during the receiver's grasp, other objects and
  friction values are out of scope.
- **Near-ceiling baselines.** The tracking and constant-offset baselines already succeed on most slip cases, which
  limits how large any learned improvement could be on these suites.
- **Simulation only.** No hardware, vision or dexterous hands; sensing is synthetic (V4 corruption model).
- **Selection noise.** Validation used 160 cases per checkpoint; several candidates tied, and ties were broken by
  the frozen key, not by held-out evidence.
- **Batch layout.** PhysX trajectories can depend on batch layout; repeatability is measured with the same batch
  size, and replays in a single environment (videos, public verification) may differ on a few cases. Every mismatch
  is listed.

## 11. Reproducibility and artifacts

- **Source:** branch `study/v5-calibration-slip`; tags `experiment-v5a` (Study A execution), `experiment-v5b`
  (Study B freeze and execution) and `v5.0.0` (delivery).
- **Release v5.0.0:** every checkpoint of every formal, pilot and probe run with `checkpoints.json`; raw records for
  probe, development, validation, final, mechanisms, repeatability, regression and Study A; traces; logs; report,
  slides, videos; source archives; `SHA256SUMS`, `release_manifest.json`, `REPRODUCE.md`, `VERIFICATION.md`.
- **Regeneration:** `scripts/v5_regen.py` rebuilds every Study A and Study B table and figure from the downloaded raw
  records and compares them with the committed files; `docs/v5/REPRODUCE.md` lists the commands and expected output.
- **Decision log:** `docs/v5/DECISIONS.md` (append-only, UTC times).

## 12. Related work

Learned bimanual handover has been studied mainly with dexterous hands and learned perception [1]; residual learning
also transfers bimanual dexterous skills [2]. Residual reinforcement learning adds a learned correction to a
hand-designed controller [3, 4]. Here the grippers are parallel-jaw and the question is geometric. The simulator is
Isaac Lab on Isaac Sim (PhysX) [5]; PPO [7] is from RSL-RL [6]. Earlier stages of this project are documented in their
own releases [8].

## References

[1] D. Frau-Alfaro, J. Castaño-Amorós, S. Puente, P. Gil, R. Calandra. "Learning Dexterous Object Handover."
IEEE RO-MAN 2025. arXiv:2506.16822.

[2] K. Li, P. Li, T. Liu, Y. Li, S. Huang. "ManipTrans: Efficient Dexterous Bimanual Manipulation Transfer via
Residual Learning." CVPR 2025.

[3] T. Johannink, S. Bahl, A. Nair, J. Luo, A. Kumar, M. Loskyll, J. A. Ojea, E. Solowjow, S. Levine.
"Residual Reinforcement Learning for Robot Control." IEEE ICRA 2019. arXiv:1812.03201.

[4] T. Silver, K. Allen, J. Tenenbaum, L. Kaelbling. "Residual Policy Learning." arXiv:1812.06298, 2018.

[5] M. Mittal et al. "Isaac Lab: A GPU-Accelerated Simulation Framework for Multi-Modal Robot Learning."
arXiv:2511.04831, 2025. Software: Isaac Lab v3.0.0.

[6] C. Schwarke, M. Mittal, N. Rudin, D. Hoeller, M. Hutter. "RSL-RL: A Learning Library for Robotics Research."
arXiv:2509.10771, 2025. Software: rsl-rl-lib 5.5.1.

[7] J. Schulman, F. Wolski, P. Dhariwal, A. Radford, O. Klimov. "Proximal Policy Optimization Algorithms."
arXiv:1707.06347, 2017.

[8] CSCI645-Project releases v1.0.0–v4.0.2, https://github.com/ywen0511/CSCI645-Project/releases.

## Software and AI-assistance disclosure

**Software.** NVIDIA Isaac Sim 6.2.0.0 (PhysX), Isaac Lab v3.0.0, RSL-RL 5.5.1 (PPO), PyTorch 2.11, NumPy,
Matplotlib, imageio/FFmpeg, python-pptx. No external datasets or demonstrations; all training data are simulator
transitions.

**AI assistance.** All AI assistance was Anthropic Claude via Claude Code; no other AI coding assistant was used.
The V5 implementation, probes, experiments, analysis code, figures, this report, the slides and the videos were
produced by Claude Code working from `V5_EXECUTION.md` on the owner's behalf, on the owner's account and compute.
Decisions are logged with UTC times in `docs/v5/DECISIONS.md`; every measured number comes from checked-in scripts
applied to the released raw records (`results/v5/number_audit.json`).
