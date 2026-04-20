import unittest
from types import SimpleNamespace
from unittest.mock import patch

from placement.dispatcher import dispatch_policy_placement


class TestPlacementDispatcher(unittest.TestCase):
    @patch("placement.dispatcher.execute_placement_strategy")
    def test_round_robin_dispatch_returns_gpu_ids_directly(self, mock_execute):
        mock_execute.return_value = ["0", "1"]

        assigned_gpu_ids = dispatch_policy_placement(
            policy="OR-RR",
            gpus_with_metrics=None,
            available_gpu_ids=["0", "1", "2"],
            number_of_gpus_requested=2,
            placement_estimate=None,
            round_robin_generator=object(),
            gpu_ids=["0", "1", "2"],
        )

        self.assertEqual(assigned_gpu_ids, ["0", "1"])
        mock_execute.assert_called_once()

    @patch("placement.dispatcher.execute_placement_strategy")
    def test_non_round_robin_dispatch_normalizes_dataframe_like_index(self, mock_execute):
        mock_execute.return_value = SimpleNamespace(index=["2", "3"])

        assigned_gpu_ids = dispatch_policy_placement(
            policy="OR-MAGM",
            gpus_with_metrics=object(),
            available_gpu_ids=["0", "1", "2", "3"],
            number_of_gpus_requested=2,
            placement_estimate=None,
            round_robin_generator=None,
            gpu_ids=["0", "1", "2", "3"],
        )

        self.assertEqual(list(assigned_gpu_ids), ["2", "3"])
        mock_execute.assert_called_once()

    @patch("placement.dispatcher.execute_placement_strategy")
    def test_dispatch_propagates_no_assignment(self, mock_execute):
        mock_execute.return_value = None

        assigned_gpu_ids = dispatch_policy_placement(
            policy="OR-MAGM",
            gpus_with_metrics=object(),
            available_gpu_ids=["0", "1"],
            number_of_gpus_requested=1,
            placement_estimate=None,
            round_robin_generator=None,
            gpu_ids=["0", "1"],
        )

        self.assertIsNone(assigned_gpu_ids)
        mock_execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()