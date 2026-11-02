# References and implementation starting points

Links were inspected while preparing the handoff. They are reference sources, not evidence that their code has been executed in this project. Check the exact version and license before reuse and cite what is actually used.

## Proposal references

### Learning Dexterous Object Handover

Daniel Frau-Alfaro, Julio Castano-Amoros, Santiago Puente, Pablo Gil, Roberto Calandra, 2025.

- [Paper](https://arxiv.org/abs/2506.16822)
- [Project and video](https://aurova.ua.es/bimanual_handover/)
- [Author repository](https://github.com/AUROVA-LAB/aurova_reinforcement_learning)

Relevant for handover phases, reward design, perturbations, and Isaac Lab task organization. The paper uses multi-finger hands; this project uses parallel-jaw grippers. The repository's setup examples include older Isaac Lab layouts. Confirm versions, assets, and training instructions rather than assuming compatibility with current releases. The original proposal lists RO-MAN 2025; verify the final venue metadata from the primary publication before formatting the final bibliography.

### ManipTrans: Efficient Dexterous Bimanual Manipulation Transfer via Residual Learning

Kailin Li, Puhao Li, Tengyu Liu, Yuyang Li, Siyuan Huang, CVPR 2025.

- [Paper](https://openaccess.thecvf.com/content/CVPR2025/papers/Li_ManipTrans_Efficient_Dexterous_Bimanual_Manipulation_Transfer_via_Residual_Learning_CVPR_2025_paper.pdf)
- [Project](https://maniptrans.github.io/)
- [Official code](https://github.com/ManipTrans/ManipTrans)

Relevant for residual learning under interaction constraints. Full reproduction requires a different scope: dexterous hands, demonstration processing, pretrained imitators, and an older Isaac Gym stack. This project does not require its datasets or checkpoints. Read the method for context; do not convert the assignment into a full ManipTrans reproduction.

## Useful task references

- [robosuite TwoArmHandover source](https://github.com/ARISE-Initiative/robosuite/blob/master/robosuite/environments/manipulation/two_arm_handover.py): useful observation/reward/success structure for handover. Uses MuJoCo; reference the design without silently replacing Isaac Sim. Its built-in success test is not automatically equivalent to this project's two-second independent holding test.
- [Efficient Bimanual Handover and Rearrangement via Symmetry-Aware Actor-Critic Learning](https://sites.google.com/view/bimanual/): project videos include two Franka arms and disturbance recovery. A conceptual/video reference; this handoff does not establish a ready-to-run official implementation.
- [HIL-SERL project](https://hil-serl.github.io/) and [code](https://github.com/rail-berkeley/hil-serl): real-robot handover and human-in-the-loop learning. Useful behavior reference; real-robot demonstrations and hardware workflows are outside this project's scope.

## Official engineering documentation

- [Isaac Lab repository](https://github.com/isaac-sim/IsaacLab)
- [Isaac Lab release history](https://github.com/isaac-sim/IsaacLab/releases)
- [External project generator](https://isaac-sim.github.io/IsaacLab/main/source/developer-tools/template_generator.html)
- [Differential IK example](https://isaac-sim.github.io/IsaacLab/main/source/how-to/run_diff_ik.html)
- [Contact sensors, versioned example](https://isaac-sim.github.io/IsaacLab/v2.3.1/source/overview/core-concepts/sensors/contact_sensor.html)
- [Isaac Sim compatibility](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/compatibility.html)

Use documentation matching the installed release. The versioned contact example illustrates the concept, not a guarantee that its API works unchanged in another version. Track copied code, licenses, asset sources, and substantial adaptations in the final repository and report.
