# Scientific and task specification

## 1. Question and hypotheses

Does combining explicit geometric coordination with learned bounded position corrections improve a simulated two-arm handover under initial-object-position and nominal-release-timing errors?

Test, rather than assume, these hypotheses:

- Geometry reduces premature release through contact-conditioned release gating and improves alignment through relative-target correction.
- Residual learning improves spatial alignment relative to the fixed nominal controller.
- Their combination can address both error sources, but may have limited benefit if geometry already solves the task or suppresses useful residual actions.
- Providing an explicit contact-phase label may improve learning efficiency or robustness; it need not do so.

Required methods: `nominal`, `geometry`, `residual`, `combined`, `combined_no_phase`. See the experiment protocol for fair comparisons. Do not claim novelty for inventing handover or residual RL; the contribution is the controlled implementation and comparison under the specified perturbations.

## 2. Scene and scope

- Two fixed-base Franka arms, each with a two-finger parallel-jaw gripper; one giver, one receiver.
- One rigid rectangular object with separate graspable regions. A suggested starting size is 0.18 x 0.035 x 0.035 m and mass 0.15 kg. Validate jaw clearance, reachability, contact stability, and collision geometry before freezing these values.
- Choose a central handover region reachable by both arms with fixed end-effector orientations. Set base poses using measured workspace checks rather than arbitrary copied coordinates.
- Use a table/ground for scene realism and drop detection, but no support under the object during the scored handover.
- Constant gravity, mass, friction, restitution, actuator settings, solver settings, and object geometry across main experiments. Do not add domain randomization of these physical parameters.
- No cameras in policy inputs. Rendering is for inspection and demonstrations only.
- No real robot, human demonstration collection, dexterous fingers, object classification, or full task motion planner required.
- Focus on initial **translation** perturbations. Orientation targets remain fixed and initial object orientation is fixed in the primary study. State this limitation explicitly; do not describe it as full 6-DoF pose robustness.

## 3. Frames, units, and low-level control

Use meters, seconds, radians, and newtons. Document world, robot-base, object, and grasp/TCP frames. Define the grasp TCP from the actual fingertip geometry, not an unverified wrist origin. Confirm quaternion ordering for the pinned Isaac Lab version and test transform round trips.

Use task-space targets with an existing differential IK controller and joint position/impedance actuation. Hold orientation targets fixed while changing position targets. Apply common workspace, joint, and velocity limits to every method. This common controller must not secretly implement the experimental geometry module.

Initial timing defaults: physics at 120 Hz, control at 20 Hz (decimation 6). Inspect contact stability and increase physics accuracy if necessary during pilot work, then freeze settings for every method. All dwell and timing thresholds are in physical seconds, not hard-coded frame counts.

## 4. Reset and persistent spatial perturbation

Initialize a genuinely grasped object before the scored episode. A short scripted settling phase may position the object and close the giver fingers, with learning disabled. No fixed joint, hidden weld, disabled gravity, or object pose teleportation may support holding after the scored episode begins.

A practical translation perturbation is to shift the initial giver TCP and object together by a sampled small displacement, preserving their grasp transform, then keep the giver at that shifted holding pose until release. The receiver's nominal grasp target stays fixed. This induces an object-to-nominal-target error without starting with an impossible or broken giver grasp. Object-only perturbations inside the fingers are optional pilot work, not the default.

Verify that the perturbation persists to receiver approach. A giver controller that moves back to the original position can accidentally remove it. Log requested displacement and actual object displacement after settling. Use identical settled starts for paired methods within the tolerance established during pilot work.

Initialization validity requires stable giver contact, object clear of supports, low object-relative velocity, and no initial inter-arm collision. A failed reset is not a handover failure, but must be counted and reported separately. Cap retries at three. Do not silently discard hard evaluation cases or resample until success: use deterministic retries for the same case, and flag unresolved cases and denominator changes. Final evaluation requires all scheduled cases valid or an explicit incomplete-data explanation.

## 5. Nominal controller and episode clock

Construct a fixed, smooth receiver trajectory through approach, grasp, and post-release hold positions. Use a pre-grasp clearance waypoint. Giver holds its initialized pose, opens on a scheduled request, and retreats after opening. Gripper closing is scheduled and shared across methods.

Suggested nominal schedule, to calibrate in pilot work:

| Event | Time from end of reset settling |
|---|---:|
| Receiver reaches pre-grasp waypoint | 1.0 s |
| Receiver reaches nominal grasp position | 2.0 s |
| Receiver begins closing | 2.0 s |
| Nominal giver release request | 2.8 s |
| End of receiver hold target | Until success or timeout |
| Episode horizon | 8.0 s |

Nominal release request time is `t_request = t_nominal_release + delta_t`. Negative `delta_t` means early release. For `nominal` and `residual`, this request must cause release without a contact-based delay. The realized gripper opening and loss-of-contact times are logged separately from command time.

Receiver pre-release and hold targets stay near the grasp region. Giver retreat is anchored to the **actual** release command, not the original clock; otherwise the geometry method could drag a held object away while waiting. Every method uses the same post-release retreat rule. If opening or retreat takes longer than the nominal trajectory, this is captured by completion time.

## 6. Residual action

Use one policy, initially controlling only the receiver's Cartesian position offset:

`p_candidate(t) = p_nominal(t) + residual_scale * tanh(a_t)`

with three action dimensions and a proposed per-axis bound of 0.02 m. The offset is relative to the current nominal target, not accumulated each time step. If the RL wrapper already bounds actions, document exactly where scaling/clipping occurs; do not accidentally apply two different squashing rules.

Orientation, giver trajectory, and gripper open/close commands are not learned. Initially apply residuals during receiver approach, closing/shared holding, and receiver-only holding; disable them during reset and after termination. Apply the same fixed action smoothing, if used, to all learned methods and retain previous-action observations. Log raw policy output, requested residual, and executed target.

## 7. Geometric coordination

Implement a deterministic, training-free module with three explicit responsibilities:

1. **Relative-target alignment:** compute the receiver grasp point from object pose and a fixed object-to-receiver grasp transform. Apply a bounded correction toward it to the candidate target during the grasp approach. Avoid unbounded exact tracking that unintentionally eliminates every spatial error. Log the correction; choose gain/limits from development-only cases.
2. **Shared-holding coordination:** after stable receiver contact, anchor both grip frames to the common object configuration and limit changes in their relative separation. Use a documented compliant target or bounded relative-target projection; do not command conflicting independent translations. Freeze the giver hold target while gating release. The module must still process the residual rather than silently replacing it with an unrelated controller.
3. **Release gate:** once the scheduled release request occurs, release only after the receiver-stability proxy is satisfied. Never release before the request. Wait at most 1.0 s beyond the request as an initial default; if stability never appears, terminate with `release_timeout` rather than force a successful transfer or wait indefinitely.

For `geometry`, the residual is zero. For `combined`, pass the candidate target through the same geometry module, with identical gains, thresholds, and release logic. Reset all anchors and timers independently for each environment.

The receiver-stability proxy should use both finger-to-object contacts, low object-to-receiver relative motion, and a continuous dwell window (initially 0.15 s). Object-specific contact filtering is essential: table or robot contact does not establish object grasp. Initial candidate thresholds are 0.2 N per finger, relative linear speed below 0.03 m/s, and relative angular speed below 0.5 rad/s. Calibrate against actual force traces; contact is a proxy, not proof of independent support. Add hysteresis/debouncing if needed and record the final rule.

Inspect geometry saturation frequency and the difference between requested and executed residuals. If geometry removes all policy authority, document and correct the design during pilots, or report that limitation; do not quietly tune it after viewing test results.

## 8. Observations and contact phase

Use the same state-observation design for all learned methods except the declared ablation:

- Receiver-to-object grasp-point displacement and relative orientation representation.
- Object linear/angular motion relative to the receiver.
- Giver-to-receiver relative position.
- Both gripper widths and object-specific per-finger contact signals.
- Relevant joint position/velocity information if needed for controllability.
- Nominal trajectory progress / episode time and previous residual action.
- Explicit contact-phase one-hot label: giver only, both, receiver only, neither.

The contact phase derives from measured contacts, not the intended controller phase, success labels, future events, or reset seed. Define raw contact versus stable grasp separately. The ablation zeros the explicit four phase channels before normalization for both training and inference, retaining dimensionality, all other inputs, and geometry access to contacts. Normalization must not reintroduce nonzero phase values. This is an **explicit phase-label ablation**, not a claim to remove all contact information. Low-level contacts and elapsed time remain available.

Do not give the policy hidden sampled release offsets, future release events, or ground-truth success decisions. Document final observation ordering, frames, scales, dimensions, normalization, and any change from these defaults.

## 9. Outcomes and failure labels

Success requires at least 2.0 continuous seconds of receiver-only holding after giver release, with giver fingers open, no giver-object contact, no table/ground support, and no drop. Check that the object stays near the receiver grasp transform with bounded drift and speed. Start the clock only when these conditions hold, reset it when they break, and terminate on success. Store the thresholds and raw signals that justify the decision. Avoid counting a transient finger collision as a grasp.

Distinguish simulator failure from task failure. Detect NaN/Inf, corrupted assets, invalid state writes, and physics instability as infrastructure errors; do not merge them into success-rate denominators without disclosure. Task failures include object drop, release-gate timeout, episode timeout, and non-permitted collision. Calibrate a drop-height/workspace rule and use sustained support/contact checks as appropriate.

Log diagnostic flags for misalignment at grasp time, release before receiver stability, and opposing motion during shared holding. Flags may overlap and are not definitive causal proof. Preserve one terminal reason with deterministic precedence: infrastructure error, prohibited collision, drop, release timeout, episode timeout; success only if no simultaneous disqualifying event exists. Report both terminal outcomes and overlapping diagnostics.

Allowed contacts are finger-object contacts needed for grasping. Define prohibited link-link/environment contacts and force/debounce thresholds in the resolved config. Report collision count/rate even if a minor contact is not terminal. Never penalize intended finger-object contact as a collision.

## 10. Reward and invariants

Use shared rewards across all trained variants, separate from the independent success evaluator. Start with normalized, bounded dense terms plus a dominant terminal success term:

- Approach progress / proximity to the actual receiver grasp point while approaching.
- Post-release receiver-only holding progress with a finite cap.
- One-time success bonus; one-time drop and prohibited-collision penalties.
- Small residual-magnitude and action-change penalties; optional small time penalty.

Do not reward endless dual holding. Phase-local dense rewards need finite duration/caps, and the fixed horizon must be enforced. Reward scales are pilot choices recorded before final training; do not claim the initial sketch is already tuned.

Required invariants: zero residual reproduces the corresponding deterministic controller; turning geometry off preserves fixed release requests; ablation changes only the explicit observation channels; action bounds hold; target offsets do not accumulate; contact-derived success cannot occur while the giver/table supports the object; all evaluation methods use identical physics and evaluator code.
