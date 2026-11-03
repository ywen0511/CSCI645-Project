"""Task registration test (adapted from the Isaac Lab v3.0.0 external-project template).

Requires an Isaac Lab installation; skipped otherwise.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

HAVE_LAB = importlib.util.find_spec("isaaclab") is not None and importlib.util.find_spec("gymnasium") is not None


@unittest.skipUnless(HAVE_LAB, "Isaac Lab not installed")
class RegistrationTest(unittest.TestCase):
    def test_task_registration(self):
        import gymnasium as gym

        import csci645_handover.tasks as tasks

        spec = gym.spec(tasks.TASK_ID)
        self.assertEqual(spec.entry_point, "csci645_handover.tasks.handover_env:HandoverEnv")
        self.assertEqual(spec.kwargs["env_cfg_entry_point"], "csci645_handover.tasks.handover_env_cfg:HandoverEnvCfg")
        self.assertEqual(spec.kwargs["default_agent"], "rsl_rl")


if __name__ == "__main__":
    unittest.main()
