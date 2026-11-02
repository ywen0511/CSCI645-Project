# Remote environment and reproducibility

## Preflight

The source was prepared on a machine that is not the intended training host. No GPU model, allocation limit, exact installed simulator version, or final submission date was supplied. Discover those facts on the execution host; do not assume local paths or local simulator availability.

Record OS/architecture, GPU model/count/VRAM, NVIDIA driver, available RAM/disk, Python, CUDA/PyTorch, Isaac Sim, Isaac Lab release and commit, RL library version, rendering mode, physics backend, and headless/video support. Verify access to the required official robot assets. Ensure logs contain no tokens or credential values.

Use the exact pinned release's installation instructions and compatibility table:

- [Isaac Lab repository and compatibility](https://github.com/isaac-sim/IsaacLab)
- [Isaac Sim cross-product compatibility](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/compatibility.html)
- [Isaac Lab releases](https://github.com/isaac-sim/IsaacLab/releases)
- [Isaac Sim system requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)

Online documentation changes. Never mix an old paper's Isaac Lab 1.x/2.x example, a current development branch API, and a different Isaac Sim installation without an explicit migration. Pin a released compatible pair or preserve a working supported remote setup. Record the exact pair rather than declaring all versions interchangeable. Major version changes may affect quaternion ordering, array access, task registration, and launch commands.

For this project, select Isaac Sim with the PhysX backend and maintain it across all methods. New Isaac Lab versions may expose other backends; do not accidentally use a backend that bypasses the chosen Isaac Sim workflow. Do not install obsolete Isaac Gym just because a reference paper used it.

## Installation and smoke checks

1. Create an isolated supported environment or versioned container. Do not modify an unrelated shared environment.
2. Run an official simple simulation example, then a Franka task-space-control example.
3. Run a short official PPO example to test the training integration, checkpoint save/load, and headless execution.
4. Verify a video can be rendered/encoded and that required assets remain accessible.
5. Generate an external Isaac Lab project using that release's template and install it in editable mode.

Commit exact working commands in `docs/SETUP_REMOTE.md` once verified. Include dependency lock/export, container digest or Dockerfile if used, asset names/versions and official acquisition instructions, and environment variables with safe example values. No remote home paths or secret values should be required by the instructions.

Avoid unnecessary visual workloads during training. Camera rendering is not required for state-based policies. Benchmark end-to-end environment transitions/second rather than quoting an unrelated official task's throughput.

## GitHub access and persistence

Verify that authenticated tooling can push to `ywen0511/CSCI645-Project`, create tags/releases, upload assets, and read them back. The repository being public does not imply write access. Prefer available GitHub API tooling or the GitHub CLI. Use existing credential mechanisms; never place tokens in source, command logs, reports, or release assets.

Do not rely on ephemeral CI artifacts or a temporary remote filesystem for final delivery. Publish checkpoints/logs/videos as GitHub Release assets. If a token lacks release capability, continue implementable work, retain bundles and checksums, and report that precise publication blocker. Do not mark publication complete.

## Reproduction from a clean clone

Before final publication, verify in a clean checkout or isolated project install:

1. Follow only the committed setup instructions.
2. Acquire official assets from documented sources; the owner's computer must not be involved.
3. Run one nominal and one geometry episode.
4. Download a published selected checkpoint and its config/normalization dependencies.
5. Evaluate at least ten specified cases, then verify the full evaluation can be invoked.
6. Regenerate the summary tables/figures from downloaded raw data.

Record limitations such as hardware-dependent floating-point variation, platform restrictions, licensed simulator downloads, or assets requiring an account. Do not redistribute restricted simulator packages; document how to obtain them legitimately.
