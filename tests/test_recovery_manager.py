import unittest

from recovery.manager import (
    _estimator_recovery_min_free_mib_override,
    _next_estimator_recovery_min_free_mib,
    _recovery_min_free_mib_override,
)


class TestRecoveryManager(unittest.TestCase):
    def test_oblivious_recovery_ladder(self):
        self.assertIsNone(_recovery_min_free_mib_override(0))
        self.assertEqual(_recovery_min_free_mib_override(1), 10 * 1024)
        self.assertEqual(_recovery_min_free_mib_override(2), 20 * 1024)
        self.assertIsNone(_recovery_min_free_mib_override(3))

    def test_estimator_bucket_step(self):
        self.assertEqual(_next_estimator_recovery_min_free_mib(8 * 1024), 10 * 1024)
        self.assertEqual(_next_estimator_recovery_min_free_mib(15 * 1024), 20 * 1024)
        self.assertEqual(_next_estimator_recovery_min_free_mib(25 * 1024), 40 * 1024)
        self.assertIsNone(_next_estimator_recovery_min_free_mib(45 * 1024))

    def test_estimator_recovery_ladder_from_failed_threshold(self):
        self.assertEqual(
            _estimator_recovery_min_free_mib_override(5665, 1),
            10 * 1024,
        )
        self.assertEqual(
            _estimator_recovery_min_free_mib_override(5665, 2),
            20 * 1024,
        )
        self.assertEqual(
            _estimator_recovery_min_free_mib_override(15 * 1024, 1),
            20 * 1024,
        )
        self.assertEqual(
            _estimator_recovery_min_free_mib_override(15 * 1024, 2),
            40 * 1024,
        )
        self.assertIsNone(
            _estimator_recovery_min_free_mib_override(15 * 1024, 3),
        )
    def test_ladder_exhaustion_requires_full_gpu_fallback(self):
        oblivious_override = _recovery_min_free_mib_override(3)
        estimator_override = _estimator_recovery_min_free_mib_override(15 * 1024, 3)

        self.assertIsNone(oblivious_override)
        self.assertIsNone(estimator_override)


if __name__ == "__main__":
    unittest.main()