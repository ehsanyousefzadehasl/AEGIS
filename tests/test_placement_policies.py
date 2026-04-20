import unittest

import pandas as pd

from placement.policies import select_est_bf


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

        self.assertEqual(list(result.index), ["1"])

    def test_select_est_bf_returns_none_when_not_enough_memory(self):
        gpus_with_metrics = pd.DataFrame(
            {
                "GPU_mem_available": [7000, 7500],
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


if __name__ == "__main__":
    unittest.main()