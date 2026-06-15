import unittest

import pandas as pd

from placement.policies import (
    GPU_MEMORY_GUARD_MIB,
    select_est_bf,
    select_or_magm,
)


class TestPlacementPolicies(unittest.TestCase):
    def test_select_est_bf_picks_smallest_sufficient_gpu(self):
        gpus_with_metrics = pd.DataFrame(
            {
                "GPU_mem_available": [12000, 9000, 7000],
                "smact": [0.10, 0.10, 0.10],
                "smocc": [0.10, 0.10, 0.10],
                "drama": [0.10, 0.10, 0.10],
            },
            index=["0", "1", "2"],
        )

        result = select_est_bf(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_estimation=6000,
            available_gpu_ids=["0", "1", "2"],
            number_of_gpus_requested=1,
        )

        self.assertEqual(list(result.index), ["2"])

    def test_select_est_bf_returns_none_when_not_enough_memory(self):
        gpus_with_metrics = pd.DataFrame(
            {
                "GPU_mem_available": [6400, 6500],
                "smact": [0.10, 0.10],
                "smocc": [0.10, 0.10],
                "drama": [0.10, 0.10],
            },
            index=["0", "1"],
        )

        result = select_est_bf(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_estimation=6000,
            available_gpu_ids=["0", "1"],
            number_of_gpus_requested=1,
        )

        self.assertIsNone(result)

    def test_select_est_bf_uses_configured_memory_guard(self):
        required_mib = 6000 + GPU_MEMORY_GUARD_MIB

        gpus_with_metrics = pd.DataFrame(
            {
                "GPU_mem_available": [
                    required_mib - 1,
                    required_mib,
                ],
                "smact": [0.10, 0.10],
                "smocc": [0.10, 0.10],
                "drama": [0.10, 0.10],
            },
            index=["0", "1"],
        )

        result = select_est_bf(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_estimation=6000,
            available_gpu_ids=["0", "1"],
            number_of_gpus_requested=1,
        )

        self.assertEqual(list(result.index), ["1"])

    def test_select_or_magm_honors_recovery_min_free_override(self):
        gpus_with_metrics = pd.DataFrame(
            {
                "GPU_mem_available": [6000, 12000, 22000],
                "smact": [0.10, 0.10, 0.10],
                "smocc": [0.10, 0.10, 0.10],
                "drama": [0.10, 0.10, 0.10],
            },
            index=["0", "1", "2"],
        )

        result = select_or_magm(
            gpus_with_metrics=gpus_with_metrics,
            available_gpu_ids=["0", "1", "2"],
            number_of_gpus_requested=2,
            recovery_min_free_mib_override=10240,
        )

        self.assertEqual(list(result.index), ["2", "1"])

if __name__ == "__main__":
    unittest.main()