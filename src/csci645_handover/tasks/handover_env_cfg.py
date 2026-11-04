"""Configuration of the two-Franka parallel-jaw handover task (Isaac Lab 3.0, Isaac Sim PhysX).

Frames and conventions
----------------------
* Environment-local world frame: origin on the ground under the handover center, +z up. All positions
  below are environment-local; the task adds ``scene.env_origins``.
* Quaternions are ``(x, y, z, w)`` (Isaac Lab 3.0 convention).
* The giver base sits at ``-x`` and faces ``+x``; the receiver base sits at ``+x`` rotated 180 deg about z.
* The object is a rigid bar whose long axis is world x. The giver grasps its ``-x`` end and the receiver
  approaches its ``+x`` end along ``-x``. Both hands point along the bar axis, and both grippers close
  along world y (side faces; friction carries the weight), so the two hands never share space.
* TCP = ``panda_hand`` origin + ``R_hand @ (0, 0, tcp_offset)``, the center of the finger pads (verified
  against finger geometry by ``scripts/inspect_scene.py``).
"""

from __future__ import annotations

import math

from isaaclab_physx.physics import PhysxCfg
from isaaclab_physx.sim.schemas import PhysxCollisionCfg, PhysxRigidBodyCfg

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg, RigidObjectCfg
from isaaclab.envs import DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg
from isaaclab.sim import RigidBodyMaterialCfg, SimulationCfg
from isaaclab.utils import clone, configclass, replace

from isaaclab_assets.robots import FRANKA_PANDA_CFG

# ----------------------------------------------------------------------------------------------
# Robot
# ----------------------------------------------------------------------------------------------

HAND_PATH = (
    "Geometry/panda_link0/panda_link1/panda_link2/panda_link3/panda_link4/panda_link5/panda_link6/panda_link7/panda_hand"
)
"""Body path of ``panda_hand`` inside the flat ``franka_panda.usda`` asset (as used by the official lift task)."""

FRANKA_HANDOVER_CFG = clone(FRANKA_PANDA_CFG)
FRANKA_HANDOVER_CFG.spawn.variants["Physics"] = "physx"
FRANKA_HANDOVER_CFG.spawn.activate_contact_sensors = True
# Task-space control with differential IK: stiff joint PD and no gravity on the arm links (as in the
# official FRANKA_PANDA_HIGH_PD_CFG). The object keeps gravity.
FRANKA_HANDOVER_CFG.spawn.rigid_props.disable_gravity = True
FRANKA_HANDOVER_CFG.actuators = {
    "panda_arm": replace(FRANKA_PANDA_CFG.actuators["panda_arm"], stiffness=400.0, damping=80.0),
    # Gripper: legacy Isaac Lab Franka finger gains (k=2000 N/m, d=100 N s/m) with a 70 N effort cap and a
    # 0.2 m/s finger speed limit. Closing onto the 35 mm bar with a closed target gives ~35 N per finger.
    # (The lift-task gains k=350, d=175 have a 0.5 s time constant and did not close in time; see DECISIONS.)
    "panda_hand": replace(
        FRANKA_PANDA_CFG.actuators["panda_hand"],
        joint_effort_limit=70.0,
        actuator_velocity_limit=0.2,
        joint_velocity_limit=0.2,
        stiffness=2000.0,
        damping=100.0,
        armature=0.1,
    ),
    "panda_finger2_passive": replace(
        FRANKA_PANDA_CFG.actuators["panda_finger2_passive"],
        joint_effort_limit=1.0,
        actuator_velocity_limit=0.2,
        joint_velocity_limit=0.2,
        armature=0.1,
    ),
}

GIVER_BASE_POS = (-0.62, 0.0, 0.0)
RECEIVER_BASE_POS = (0.62, 0.0, 0.0)
YAW_180 = (0.0, 0.0, 1.0, 0.0)


def _finger_sensor(robot: str, finger: str) -> ContactSensorCfg:
    return ContactSensorCfg(
        prim_path=f"{{ENV_REGEX_NS}}/{robot}/{HAND_PATH}/{finger}",
        filter_prim_paths_expr=["{ENV_REGEX_NS}/Object", "{ENV_REGEX_NS}/Table"],
        history_length=0,
    )


def _link_sensor(robot: str) -> ContactSensorCfg:
    # Net contact force on every rigid body of the robot (used for prohibited-contact monitoring).
    return ContactSensorCfg(prim_path=f"{{ENV_REGEX_NS}}/{robot}/Geometry/.*", history_length=0)


# ----------------------------------------------------------------------------------------------
# Scene
# ----------------------------------------------------------------------------------------------

OBJECT_SIZE = (0.18, 0.035, 0.035)
OBJECT_MASS = 0.15
HANDOVER_CENTER = (0.0, 0.0, 0.50)
TABLE_SIZE = (0.30, 0.30, 0.20)


@configclass
class HandoverSceneCfg(InteractiveSceneCfg):
    giver: ArticulationCfg = replace(
        FRANKA_HANDOVER_CFG,
        prim_path="{ENV_REGEX_NS}/Giver",
        init_state=replace(FRANKA_HANDOVER_CFG.init_state, pos=GIVER_BASE_POS, rot=(0.0, 0.0, 0.0, 1.0)),
    )
    receiver: ArticulationCfg = replace(
        FRANKA_HANDOVER_CFG,
        prim_path="{ENV_REGEX_NS}/Receiver",
        init_state=replace(FRANKA_HANDOVER_CFG.init_state, pos=RECEIVER_BASE_POS, rot=YAW_180),
    )
    object: RigidObjectCfg = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Object",
        spawn=sim_utils.CuboidCfg(
            size=OBJECT_SIZE,
            physics_material=RigidBodyMaterialCfg(static_friction=1.0, dynamic_friction=1.0, restitution=0.0),
            rigid_props=PhysxRigidBodyCfg(
                solver_position_iteration_count=16, solver_velocity_iteration_count=1, disable_gravity=False,
                max_depenetration_velocity=1.0,
            ),
            collision_props=[sim_utils.UsdPhysicsCollisionCfg(), PhysxCollisionCfg(contact_offset=0.002)],
            mass_props=sim_utils.MassCfg(mass=OBJECT_MASS),
            activate_contact_sensors=True,
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.85, 0.45, 0.10)),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=HANDOVER_CENTER, rot=(0.0, 0.0, 0.0, 1.0)),
    )
    table: RigidObjectCfg = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Table",
        spawn=sim_utils.CuboidCfg(
            size=TABLE_SIZE,
            rigid_props=sim_utils.UsdPhysicsRigidBodyCfg(kinematic_enabled=True),
            collision_props=sim_utils.UsdPhysicsCollisionCfg(),
            physics_material=RigidBodyMaterialCfg(static_friction=0.8, dynamic_friction=0.8),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.30, 0.22, 0.18)),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=(0.0, 0.0, TABLE_SIZE[2] / 2), rot=(0.0, 0.0, 0.0, 1.0)),
    )
    plane = AssetBaseCfg(
        prim_path="/World/GroundPlane", spawn=sim_utils.GroundPlaneCfg(), collision_group=-1
    )
    light = AssetBaseCfg(
        prim_path="/World/light", spawn=sim_utils.DomeLightCfg(color=(0.8, 0.8, 0.8), intensity=3000.0)
    )
    giver_lf = _finger_sensor("Giver", "panda_leftfinger")
    giver_rf = _finger_sensor("Giver", "panda_rightfinger")
    recv_lf = _finger_sensor("Receiver", "panda_leftfinger")
    recv_rf = _finger_sensor("Receiver", "panda_rightfinger")
    object_contact = ContactSensorCfg(
        prim_path="{ENV_REGEX_NS}/Object", filter_prim_paths_expr=["{ENV_REGEX_NS}/Table"], history_length=0
    )
    giver_links = _link_sensor("Giver")
    recv_links = _link_sensor("Receiver")


# ----------------------------------------------------------------------------------------------
# Task
# ----------------------------------------------------------------------------------------------


@configclass
class HandoverEnvCfg(DirectRLEnvCfg):
    """Direct-workflow handover task. Method-specific fields are set by :func:`apply_method`."""

    # ---- method (see configs/protocol.json) ----
    method: str = "nominal"
    geometry_enabled: bool = False
    residual_enabled: bool = False
    phase_input: bool = True

    # ---- timing ----
    physics_hz: int = 120
    decimation: int = 6
    settle_pin_s: float = 0.30
    """Settling stage 1: object pinned at its (shifted) start pose while the giver moves to it, fingers open."""
    settle_close_s: float = 0.30
    """Settling stage 2: giver fingers close, object still pinned."""
    settle_free_s: float = 0.30
    """Settling stage 3: object released into the giver's grasp; validity checked at the end."""
    reset_max_attempts: int = 3
    horizon_s: float = 8.0
    episode_length_s: float = 3 * 0.9 + 8.0 + 0.5
    """Upper bound only (settling retries + horizon); the scored horizon is enforced by the task clock."""

    # ---- nominal schedule (seconds from end of settling) ----
    t_pregrasp: float = 1.0
    t_grasp: float = 2.0
    t_close_start: float = 2.0
    close_duration: float = 0.8
    t_release_nominal: float = 2.8
    retreat_delay: float = 0.3
    retreat_duration: float = 0.7
    retreat_distance: float = 0.10

    # ---- geometry of the handover ----
    handover_center: tuple[float, float, float] = HANDOVER_CENTER
    object_size: tuple[float, float, float] = OBJECT_SIZE
    grasp_insertion: float = 0.025
    """Depth of each TCP inside its object end along the bar axis [m]."""
    pregrasp_backoff: float = 0.06
    start_backoff: float = 0.16
    tcp_offset: float = 0.1034
    """Distance of the TCP from the ``panda_hand`` origin along the hand z axis [m]."""
    finger_open: float = 0.04
    finger_closed: float = 0.0
    ik_joint_limit_gain: float = 0.0
    """Null-space joint-limit avoidance gain of the shared differential-IK controller (all methods).
    0 = exact tracking; good joint seeds keep the arms >= 0.1 rad from their limits (scripts/inspect_scene.py)."""
    giver_seed_q: list | None = [1.01, -0.686, -0.939, -2.386, -2.779, 2.648, -0.082]
    """Arm joint configuration written at reset for the giver (IK solution of the nominal hold pose)."""
    receiver_seed_q: list | None = [-0.513, -1.115, 0.582, -2.802, 2.551, 2.777, -1.268]
    """Arm joint configuration written at reset for the receiver (IK solution of the start pose)."""

    # ---- negative controls (Gate 1 checks only; empty for every experiment) ----
    negative_control: str = ""
    table_size_override: list | None = None
    """Negative-control runs only: replace the table size, e.g. [0.06, 0.30, 0.20] for the table-support check."""
    """"" | "no_receiver" (receiver never approaches) | "giver_holds" (no release request) |
    "table_support" (table raised under the object so it rests on the table after release)."""

    # ---- residual ----
    residual_bound_m: float = 0.02

    # ---- geometry module ----
    align_gain: float = 1.0
    align_max: float = 0.010
    """Per-axis alignment bound = the in-range perturbation envelope (pilot: 0.015 removed ~all stress error)."""
    sep_tol: float = 0.01
    release_max_wait_s: float = 1.0
    # ---- v2 controller options (defaults reproduce v1 exactly; omitted from the config hash at default) ----
    geom_align: bool = True
    """Geometry component A (alignment). Only used when ``geometry_enabled``."""
    geom_anchor: bool = True
    """Geometry component H (shared-holding anchor). Only used when ``geometry_enabled``."""
    geom_gate: bool = True
    """Geometry component G (contact-gated release with cap). Only used when ``geometry_enabled``."""
    constant_residual_m: list | None = None
    """Constant-offset control: a fixed Cartesian residual [m] used in place of a policy action, composed
    exactly like the learned residual (scored steps only, clipped to +-residual_bound_m per axis)."""
    stab_min_finger_force: float = 0.2
    stab_max_rel_lin_speed: float = 0.03
    stab_max_rel_ang_speed: float = 0.5
    stab_dwell_s: float = 0.15

    # ---- outcome evaluator ----
    success_hold_s: float = 2.0
    contact_force: float = 0.2
    table_force: float = 0.2
    giver_open_width: float = 0.07
    drift_tol: float = 0.02
    rel_speed_tol: float = 0.05
    drop_height: float = 0.35
    workspace_radius: float = 0.6
    collision_force: float = 1.0
    collision_terminal_s: float = 0.25
    misalign_tol: float = 0.01
    misalign_check_time: float = 2.4
    """Episode time of the grasp-misalignment diagnostic (just before receiver finger contact in clean runs)."""
    conflict_tol: float = 0.01
    reset_offset_tol: float = 0.008
    """Maximum |realized - requested| start displacement for a valid reset [m]."""
    reset_max_obj_speed: float = 0.05

    # ---- rewards (shared by all learned methods; values recorded before final training) ----
    rew_approach: float = 1.0
    rew_approach_scale: float = 0.02
    rew_hold: float = 2.0
    rew_success: float = 10.0
    rew_drop: float = -5.0
    rew_collision: float = -5.0
    rew_release_timeout: float = -2.0
    rew_residual_l2: float = -0.5
    rew_action_rate: float = -0.5

    # ---- training perturbation curriculum (fraction of the transition budget) ----
    curriculum: list = [
        {"fraction_start": 0.0, "fraction_end": 0.2, "position_bound_m": 0.0, "release_offset_bound_s": 0.0},
        {"fraction_start": 0.2, "fraction_end": 0.5, "position_bound_m": 0.005, "release_offset_bound_s": 0.0},
        {"fraction_start": 0.5, "fraction_end": 1.0, "position_bound_m": 0.01, "release_offset_bound_s": 0.15},
    ]
    total_transitions: int = 10_000_000

    # ---- spaces ----
    action_space = 3
    observation_space = 46
    state_space = 0

    sim: SimulationCfg = SimulationCfg(
        dt=1.0 / 120.0,
        render_interval=6,
        physics=PhysxCfg(
            bounce_threshold_velocity=0.01,
            gpu_max_rigid_patch_count=4 * 5 * 2**15,
            gpu_found_lost_pairs_capacity=2**24,
        ),
    )
    scene: HandoverSceneCfg = HandoverSceneCfg(num_envs=64, env_spacing=2.5, replicate_physics=True)

    def __post_init__(self):
        self.sim.dt = 1.0 / self.physics_hz
        self.sim.render_interval = self.decimation
        settle = self.settle_pin_s + self.settle_close_s + self.settle_free_s
        self.episode_length_s = self.reset_max_attempts * settle + self.horizon_s + 0.5
        if self.table_size_override is not None:
            self.scene.table.spawn.size = tuple(self.table_size_override)


METHODS = {
    "nominal": dict(geometry_enabled=False, residual_enabled=False, phase_input=False),
    "geometry": dict(geometry_enabled=True, residual_enabled=False, phase_input=False),
    "residual": dict(geometry_enabled=False, residual_enabled=True, phase_input=True),
    "combined": dict(geometry_enabled=True, residual_enabled=True, phase_input=True),
    "combined_no_phase": dict(geometry_enabled=True, residual_enabled=True, phase_input=False),
}


def apply_method(cfg: HandoverEnvCfg, method: str) -> HandoverEnvCfg:
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}; expected one of {sorted(METHODS)}")
    cfg.method = method
    for k, v in METHODS[method].items():
        setattr(cfg, k, v)
    return cfg


def fixed_hand_quat(approach_sign: float) -> tuple[float, float, float, float]:
    """Hand orientation (xyzw): z axis (approach) along ``approach_sign * x``, y axis (finger travel) along world +y.

    Fingers close horizontally across the bar's 35 mm width, so only friction carries the bar's weight and a
    release before the receiver has a grip drops it (vertical closing let the lower finger catch the bar).
    """
    import torch

    from isaaclab.utils.math import quat_from_matrix

    z = torch.tensor([approach_sign, 0.0, 0.0])
    y = torch.tensor([0.0, 1.0, 0.0])
    x = torch.linalg.cross(y, z)
    rot = torch.stack([x, y, z], dim=-1)
    q = quat_from_matrix(rot.unsqueeze(0))[0]
    return tuple(float(v) for v in q)


