"""Isaac Lab task registration (requires an Isaac Lab runtime)."""

import gymnasium as gym

TASK_ID = "CSCI645-Handover-Direct-v0"

gym.register(
    id=TASK_ID,
    entry_point="csci645_handover.tasks.handover_env:HandoverEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "csci645_handover.tasks.handover_env_cfg:HandoverEnvCfg",
        "rsl_rl_cfg_entry_point": "csci645_handover.agents.ppo_cfg:HandoverPPORunnerCfg",
        "default_agent": "rsl_rl",
    },
)
