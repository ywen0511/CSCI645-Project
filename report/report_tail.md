## 10. Discussion

**Hypothesis 1 (geometry reduces premature release and improves alignment): supported.** Geometry alone
raised stress success from 47.8 % to 93.3 % (+45.5 [+41.5, +49.5] points) and in-range success from 95.5 %
to 100 %, removed every drop, and turned the joint-early-stress condition from 11.5 % to 94.5 % by delaying
release by 0.17 s on average until the receiver held the bar.

**Hypothesis 2 (residual learning improves spatial alignment over nominal): supported in-range, weakly
under stress.** Trained residual policies reached 100 % on all in-range conditions (nominal 95.5 %) and
improved stress success by +7.9 [+4.6, +11.7] points, but they cannot change release timing and remain at
16 % on joint early stress. The primary (selected) residual results are confounded by the untrained step-0
selection described in Section 7.1.

**Hypothesis 3 (the combination addresses both error sources): not supported beyond geometry.** With the
selected checkpoints, combined and geometry are indistinguishable (+1.2 [-4.3, +5.4] on stress); with
trained final checkpoints, combined is slightly worse than geometry on stress cases (-3.4 [-6.3, -1.1]).
The residual is learned only within +/-1 cm, where geometry already succeeds, so there is little left to
learn in-distribution and its corrections do not transfer to the larger stress offsets. This is the
"geometry already solves the task" case anticipated in the specification.

**Hypothesis 4 (explicit contact phase helps): no detectable effect.** Raw contact forces and time carry
the same information here.

**Protocol lesson.** Validation drawn only from the training distribution cannot rank policies when a
training-free component already solves that distribution, and "earliest step" tie-breaking then selects
untrained policies. A validation suite that includes harder (but still non-test) cases, or a tie-break on
validation return, would avoid this; we report the frozen result and the declared secondary analysis
instead of changing the rule after the fact.

## 11. Limitations

* Simulation only (Isaac Sim PhysX); contact parameters, gripper drive and friction are idealized and
  physics properties were not randomized. No real robot.
* Fixed orientations and **translation-only** initial perturbations; no claim about 6-DoF pose robustness.
  One object, one grasp configuration, two fixed arm bases.
* The nominal controller is a fixed script with a tracking lag of about 9 mm at the nominal grasp time; the
  failure boundary (palm contact at about +0.9 cm extra insertion) is narrow, which makes outcomes sensitive
  to millimetre-scale biases, including those of untrained policies.
* Geometry has privileged access to the measured object pose and contacts; it is a state-feedback
  controller, not an information-free baseline. Its alignment bound (1 cm) was set on development cases.
* Three training seeds give limited precision; the clean condition is deterministic, so its 200 cases are
  repeats rather than independent samples. Batched GPU physics is not bitwise reproducible across batch
  compositions (single-environment video replays are compared with the evaluation records in the video
  index).
* Isaac Sim requires a Vulkan driver even headless; on GPU nodes without NVIDIA graphics libraries we used
  user-space libraries extracted from the matching driver installer (no system changes). Videos use the
  Newton Warp ray-tracing renderer (direct lighting) because the A100 GPUs lack RT cores.

## 12. Conclusion

In this controlled two-Franka handover, an explicit, training-free geometric layer — bounded object-relative
target correction, shared-holding anchoring and contact-gated release with a 1 s cap — is what makes the
handover robust: it lifts stress-case success from 48 % to 93 % and removes all drops. A bounded PPO
residual helps the fixed script on in-range errors but adds nothing on top of geometry and slightly hurts
outside its training range, and the explicit contact-phase input has no measurable effect.

## 13. Reproducibility

Source: `experiment-v1` (commit `7a64505a`) for all experiments; later commits add analysis, report and
release material only (task code verified identical). Frozen protocol, suites, environment lock and setup
are in `configs/frozen/` and `docs/SETUP_REMOTE.md`; exact commands in `docs/REPRODUCE.md`. The GitHub
Release contains every raw episode record (19,800 final, 5,400 validation, plus the secondary analysis),
training logs, all checkpoints of all nine runs (selected, final, resumable and every periodic checkpoint),
videos with a provenance index, and SHA-256 checksums. `scripts/analyze.py` regenerates every table and
figure in this report from the downloaded raw records.

## References

[1] D. Frau-Alfaro, J. Castaño-Amorós, S. Puente, P. Gil, R. Calandra. "Learning Dexterous Object Handover."
34th IEEE International Conference on Robot and Human Interactive Communication (RO-MAN), 2025, pp. 380-387.
doi:10.1109/RO-MAN63969.2025.11217592. arXiv:2506.16822.

[2] T. Johannink, S. Bahl, A. Nair, J. Luo, A. Kumar, M. Loskyll, J. A. Ojea, E. Solowjow, S. Levine.
"Residual Reinforcement Learning for Robot Control." IEEE ICRA 2019, pp. 6023-6029.
doi:10.1109/ICRA.2019.8794127.

[3] T. Silver, K. Allen, J. Tenenbaum, L. Kaelbling. "Residual Policy Learning." arXiv:1812.06298, 2018.

[4] K. Li, P. Li, T. Liu, Y. Li, S. Huang. "ManipTrans: Efficient Dexterous Bimanual Manipulation Transfer
via Residual Learning." CVPR 2025.

[5] Y. Zhu, J. Wong, A. Mandlekar, R. Martín-Martín, et al. "robosuite: A Modular Simulation Framework and
Benchmark for Robot Learning." arXiv:2009.12293, 2020.

[6] M. Mittal et al. "Isaac Lab: A GPU-Accelerated Simulation Framework for Multi-Modal Robot Learning."
arXiv:2511.04831, 2025. Software: Isaac Lab v3.0.0, https://github.com/isaac-sim/IsaacLab.

[7] C. Schwarke, M. Mittal, N. Rudin, D. Hoeller, M. Hutter. "RSL-RL: A Learning Library for Robotics
Research." arXiv:2509.10771, 2025. Software: rsl-rl-lib 5.5.1.

[8] J. Schulman, F. Wolski, P. Dhariwal, A. Radford, O. Klimov. "Proximal Policy Optimization Algorithms."
arXiv:1707.06347, 2017.

## Software and AI-assistance disclosure

**Software reused.** NVIDIA Isaac Sim 6.2.0.0 (PhysX), Isaac Lab v3.0.0 (BSD-3-Clause; Franka Panda asset
configuration, differential IK controller, contact sensors, RSL-RL wrapper and runner helpers, external-project
template metadata), RSL-RL 5.5.1 (PPO, BSD-3-Clause), PyTorch 2.11, NumPy, Matplotlib, imageio/FFmpeg. The
Franka Panda model is NVIDIA's official Isaac Lab asset. The gripper gains follow Isaac Lab's legacy Franka
configuration and the arm gains its high-PD IK preset. No external datasets or demonstrations were used.

**AI assistance.** The implementation, experiments, analysis code, figures and this report were produced by
an AI coding agent (Anthropic Claude, operating through Claude Code) working from the repository's written
specification on the owner's behalf, under the owner's account and compute. The agent chose engineering
details and pilot calibrations (all logged in docs/DECISIONS.md), ran every experiment and wrote the text;
all reported numbers are generated by the checked-in analysis scripts from the archived raw records. The
original proposal (`proposal/`) was written before this work and is unchanged. No course rules on AI use
were provided with the assignment, so no claim of compliance with such rules is made.
