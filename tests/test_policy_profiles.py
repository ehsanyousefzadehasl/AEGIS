import unittest

from placement.profiles import (
    policy_estimate_source,
    policy_placement_strategy,
    policy_required_profile_metrics,
    policy_uses_dispatcher,
)


class TestPolicyProfiles(unittest.TestCase):
    def test_exclusive_policy_profile(self):
        self.assertEqual(policy_estimate_source("exclusive"), "none")
        self.assertFalse(policy_uses_dispatcher("exclusive"))
        self.assertIsNone(policy_placement_strategy("exclusive"))
        self.assertEqual(policy_required_profile_metrics("exclusive"), ())

    def test_oracle_ff_policy_profile(self):
        self.assertEqual(policy_estimate_source("oracle-FF"), "oracle")
        self.assertTrue(policy_uses_dispatcher("oracle-FF"))
        self.assertEqual(policy_placement_strategy("oracle-FF"), "oracle_ff")
        self.assertEqual(policy_required_profile_metrics("oracle-FF"), ())

    def test_or_rr_policy_profile(self):
        self.assertEqual(policy_estimate_source("OR-RR"), "none")
        self.assertTrue(policy_uses_dispatcher("OR-RR"))
        self.assertEqual(policy_placement_strategy("OR-RR"), "or_rr")
        self.assertEqual(policy_required_profile_metrics("OR-RR"), ())

    def test_profiled_magm_policy_profile(self):
        self.assertEqual(policy_estimate_source("PROFILED-MAGM"), "profiled_metadata")
        self.assertTrue(policy_uses_dispatcher("PROFILED-MAGM"))
        self.assertEqual(policy_placement_strategy("PROFILED-MAGM"), "est_magm")
        self.assertEqual(
            policy_required_profile_metrics("PROFILED-MAGM"),
            ("peak_memory_mib",),
        )
        
    def test_best_fit_estimate_policy_profiles(self):
        self.assertEqual(policy_estimate_source("EST-BF"), "task_file_estimate")
        self.assertTrue(policy_uses_dispatcher("EST-BF"))
        self.assertEqual(policy_placement_strategy("EST-BF"), "est_bf")
        self.assertEqual(policy_required_profile_metrics("EST-BF"), ())

        self.assertEqual(policy_estimate_source("ONLINE-EST-BF"), "online_estimate")
        self.assertTrue(policy_uses_dispatcher("ONLINE-EST-BF"))
        self.assertEqual(policy_placement_strategy("ONLINE-EST-BF"), "est_bf")
        self.assertEqual(policy_required_profile_metrics("ONLINE-EST-BF"), ())

        self.assertEqual(policy_estimate_source("PROFILED-BF"), "profiled_metadata")
        self.assertTrue(policy_uses_dispatcher("PROFILED-BF"))
        self.assertEqual(policy_placement_strategy("PROFILED-BF"), "est_bf")
        self.assertEqual(
            policy_required_profile_metrics("PROFILED-BF"),
            ("peak_memory_mib",),
        )

if __name__ == "__main__":
    unittest.main()