"""RSL-RL PPO configuration shared by all learned methods (residual, combined, combined_no_phase).

Pilot values from docs/EXPERIMENTS.md; the frozen values are recorded in configs/frozen/.
Actions are *not* clipped by the wrapper (``clip_actions=None``); the environment applies the single
``0.02 * tanh(a)`` squashing. Observation normalization is the model's empirical normalizer.
"""

from isaaclab.utils import configclass

from isaaclab_rl.rsl_rl import RslRlMLPModelCfg, RslRlOnPolicyRunnerCfg, RslRlPpoAlgorithmCfg


@configclass
class HandoverPPORunnerCfg(RslRlOnPolicyRunnerCfg):
    num_steps_per_env = 32
    max_iterations = 1000
    save_interval = 1_000_000  # checkpoints are written by scripts/train.py on transition boundaries
    experiment_name = "csci645_handover"
    init_at_random_ep_len = False  # the episode clock is part of the task; never randomize it
    clip_actions = None
    check_for_nan = True
    obs_groups = {"actor": ["policy"], "critic": ["policy"]}
    actor = RslRlMLPModelCfg(
        hidden_dims=[128, 128],
        activation="elu",
        obs_normalization=True,
        distribution_cfg=RslRlMLPModelCfg.GaussianDistributionCfg(init_std=0.5),
    )
    critic = RslRlMLPModelCfg(hidden_dims=[128, 128], activation="elu", obs_normalization=True)
    algorithm = RslRlPpoAlgorithmCfg(
        value_loss_coef=1.0,
        use_clipped_value_loss=True,
        clip_param=0.2,
        entropy_coef=0.002,
        num_learning_epochs=5,
        num_mini_batches=4,
        learning_rate=3.0e-4,
        schedule="adaptive",
        gamma=0.99,
        lam=0.95,
        desired_kl=0.01,
        max_grad_norm=1.0,
    )


def make_runner(wrapped_env, agent: HandoverPPORunnerCfg, log_dir: str | None):
    """Create the RSL-RL OnPolicyRunner exactly as Isaac Lab's unified train entrypoint does."""
    from isaaclab_rl.rsl_rl import check_rsl_rl_version, create_rsl_rl_runner, handle_deprecated_rsl_rl_cfg

    agent = handle_deprecated_rsl_rl_cfg(agent, check_rsl_rl_version())
    return create_rsl_rl_runner(wrapped_env, agent, log_dir=log_dir), agent


def apply_ppo_overrides(agent: HandoverPPORunnerCfg, overrides: dict) -> HandoverPPORunnerCfg:
    for k, v in (overrides or {}).items():
        target = agent.algorithm if hasattr(agent.algorithm, k) else agent
        if not hasattr(target, k):
            raise KeyError(f"Unknown PPO setting {k}")
        setattr(target, k, v)
    return agent
