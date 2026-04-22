import unittest


class TestSchedulerRecoveryLogic(unittest.TestCase):
    def test_force_full_gpu_recovery_blocks_dispatcher_path(self):
        force_full_gpu_recovery = True
        policy_uses_dispatcher = True
        main_queue_length = 1
        recovery_queue_length = 0

        should_enter_dispatcher = (
            not force_full_gpu_recovery
            and policy_uses_dispatcher
            and (main_queue_length != 0 and recovery_queue_length == 0)
        )

        self.assertFalse(should_enter_dispatcher)

    def test_normal_task_can_use_dispatcher_path(self):
        force_full_gpu_recovery = False
        policy_uses_dispatcher = True
        main_queue_length = 1
        recovery_queue_length = 0

        should_enter_dispatcher = (
            not force_full_gpu_recovery
            and policy_uses_dispatcher
            and (main_queue_length != 0 and recovery_queue_length == 0)
        )

        self.assertTrue(should_enter_dispatcher)


if __name__ == "__main__":
    unittest.main()