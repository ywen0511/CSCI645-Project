## 3. Task and physical setup

**Platform.** Isaac Sim 6.2.0.0 through Isaac Lab v3.0.0 (GA, October 2026) with the Isaac Sim PhysX
backend for every method; PyTorch 2.11 (CUDA 13.0), Warp 1.17, RSL-RL 5.5.1. The task is an external
Isaac Lab project (Direct single-agent workflow) whose metadata derives from the official template
generator. All experiments ran on one NVIDIA A100-SXM4-40GB per job (driver 580.159.03, Ubuntu 24.04).
Physics runs at 120 Hz and control at 20 Hz (decimation 6).

**Scene.** Two fixed-base Franka Panda arms with their two-finger parallel-jaw grippers face each other
1.24 m apart (giver at x = -0.62 m, receiver at x = +0.62 m rotated by 180 deg). The object is a rigid bar
of 0.18 x 0.035 x 0.035 m and 0.15 kg (friction 1.0) whose long axis is the world x axis, centered at
(0, 0, 0.50) m. A kinematic table (top at 0.20 m) under the handover region only serves drop detection.
The giver grasps the bar's -x end and the receiver approaches its +x end along -x; both hands keep fixed
orientations with the approach axis along the bar and the fingers closing horizontally (world y), so the
bar's weight is carried by friction only. The TCP is 0.1034 m from the `panda_hand` frame along its z axis,
inside the finger pads (finger geometry spans 0.0585-0.1123 m). Each TCP is inserted 0.025 m into its
end of the bar. The gripper drive (k = 2000 N/m, d = 100 N s/m, 70 N effort cap, 0.2 m/s) squeezes the bar
with about 17 N per finger.

**Low-level control (shared).** Both arms track Cartesian position targets with fixed orientations through
Isaac Lab's damped-least-squares differential IK on the hand frame, evaluated every physics substep in the
world frame, with joint-space PD (400/80) and joint-limit clamping. Arm links have gravity disabled (Isaac
Lab's high-PD IK convention); the object has gravity. A common workspace box limits the receiver target.

**Reset and perturbations.** Each episode starts with a 0.9 s scripted settling phase (learning disabled):
the bar is pinned at its start pose while the giver servos to the shifted hold pose and closes; then the
pin is removed and the bar rests in the giver's grasp for 0.3 s. A start is valid only if both giver fingers
press the bar (> 0.2 N), nothing else supports it, it is still, no prohibited contact occurs and the realized
displacement is within 8 mm of the requested one; otherwise the same case is retried (at most 3 attempts).
The spatial perturbation shifts the giver and bar together by `d` (uniform per axis), so the bar is
displaced relative to the receiver's fixed nominal grasp target for the whole approach. The release
perturbation shifts the giver's release request to `t_request = 2.8 s + delta_t`.

**Episode schedule (time from the end of settling).** The receiver moves on minimum-jerk segments from its
start (0.16 m behind the grasp point) to a pre-grasp point (0.06 m behind) at 1.0 s and to the nominal grasp
point at 2.0 s, then holds. Its finger target ramps closed from 2.0 s to 2.8 s. The giver holds until its
release command, opens immediately and retreats 0.10 m along -x starting 0.3 s after the *actual* command.
The horizon is 8.0 s.

## 4. Methods

**Residual action.** One policy outputs `a in R^3`; the receiver's candidate target is
`p_cand(t) = p_nom(t) + 0.02 m * tanh(a_t)` (per axis, relative to the current nominal target, never
accumulated). The residual is active only in the scored phase. Gripper and giver commands are scripted.

**Geometry module (training-free, identical in `geometry`, `combined`, `combined_no_phase`).**
1. *Relative-target alignment* (before stable receiver contact):
   `p = p_cand + clip(k (g_obj - g_nom), -c, c)` with `g_obj` the receiver grasp point computed from the
   measured bar pose and a fixed object-to-grasp transform, `g_nom` the nominal grasp point, `k = 1`,
   `c = 0.01 m` per axis (the in-range perturbation envelope).
2. *Shared-holding coordination:* when the receiver-stability proxy first holds, the receiver target is
   anchored at its actual TCP position `p_a`; afterwards `p = p_a + clip(p_cand - p_nom, -0.01, 0.01)`,
   so the residual is still applied but cannot pull the two grippers apart by more than 1 cm per axis.
   The giver hold target is frozen until release.
3. *Release gate:* release only at or after the request and only when the stability proxy holds; if it does
   not hold within 1.0 s after the request, the episode ends as `release_timeout`.

The receiver-stability proxy requires an object-filtered normal force above 0.2 N on *both* receiver fingers,
object motion relative to the receiver hand below 0.03 m/s and 0.5 rad/s, continuously for 0.15 s. Relative
motion is computed by finite differences of the measured poses over one control step, because PhysX reports
biased velocities for a body squeezed between fingers (a static, gripped bar reported about 1 rad/s).

**Methods compared.** `nominal` (scripted, release on request), `geometry` (scripted + geometry module),
`residual` (PPO residual, no geometry), `combined` (PPO residual through the geometry module) and
`combined_no_phase` (as `combined`, trained and evaluated with the four explicit contact-phase channels
zeroed). Geometry is a state-feedback controller with access to object pose and contacts, not an
information-free baseline.

**Observations (46 dimensions, all learned methods).** Receiver grasp-point error (3), object orientation
error relative to the receiver hand (3, axis-angle), object linear and angular motion relative to the
receiver hand (3 + 3), giver-to-receiver TCP offset (3), both gripper gaps (2), tanh-scaled object-filtered
normal forces on all four fingers (4), receiver arm joint positions and scaled velocities (7 + 7), nominal
target minus receiver TCP (3), normalized episode time (1), previous residual (3) and the explicit
contact-phase one-hot from measured raw contacts: giver only, both, receiver only, neither (4). The ablation
zeros these four channels before RSL-RL's empirical normalization, in training and evaluation alike.

**Rewards (shared).** Per control step: approach `1.0 (1 - tanh(|g_obj - p_tcp| / 0.02)) dt` before release;
independent-holding progress `2.0 dt` while the evaluator's hold timer runs; one-time terminal terms
+10 (success), -5 (drop), -5 (prohibited collision), -2 (release timeout); residual magnitude
`-0.5 |r/0.02|^2 dt` and action change `-0.5 |dr/0.02|^2 dt`. Rewards are separate from the evaluator.

**PPO.** RSL-RL 5.5.1 PPO, actor and critic MLPs [128, 128] (ELU) with empirical observation normalization,
initial action std 0.5, learning rate 3e-4 with the adaptive KL schedule (target 0.01), gamma 0.99,
lambda 0.95, clip 0.2, 5 epochs, 4 minibatches, entropy 0.002, 1024 environments x 32 steps per iteration.
Timeouts bootstrap (truncation); drops, collisions, release timeouts and successes are terminal. Training
perturbations follow the fixed transition-based curriculum of the protocol (0-20 %: none; 20-50 %:
+/-5 mm; 50-100 %: +/-10 mm and +/-0.15 s).

## 5. Outcome definition

The evaluator is independent of rewards and controllers. **Success** requires 2.0 continuous seconds in
which the giver has been commanded to release, its fingers are open (gap > 0.07 m) and do not touch the
bar, the table does not touch the bar, both receiver fingers press the bar, the bar is above 0.35 m, it has
moved less than 2 cm in the receiver-hand frame since the release command and its motion relative to the
receiver hand is below 0.05 m/s; the timer resets whenever any condition breaks. **Drop**: bar below 0.35 m
or more than 0.6 m horizontally from the handover center. **Prohibited collision**: any arm link (1-7) or
hand contact, or finger contact with the table or a non-object body, above 1 N; counted as an event,
terminal when sustained for 0.25 s. Terminal precedence: infrastructure error > prohibited collision >
drop > release timeout > episode timeout; success only without a simultaneous disqualifying event.
Diagnostics (overlapping, not causal proof): grasp-point error > 1 cm at 2.4 s (misalignment), release
command without the stability proxy holding (premature release), giver-receiver TCP separation change
> 1 cm during shared holding (conflicting motion).
