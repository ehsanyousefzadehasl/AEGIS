import unittest
from types import SimpleNamespace
from unittest.mock import patch

from placement.strategies import execute_placement_strategy


class TestPlacementStrategies(unittest.TestCase):
    def test_unknown_strategy_returns_none(self):
        request = SimpleNamespace()
        self.assertIsNone(execute_placement_strategy("does_not_exist", request))

    @patch("placement.strategies._resolve_gpu_memory_requirement")
    def test_oracle_strategy_dispatches_through_registry(self, mock_requirement):
        mock_requirement.return_value = 123

        def fake_selector(**kwargs):
            return kwargs["gpu_memory_requirement"]

        request = SimpleNamespace(
            gpus_with_metrics="metrics",
            available_gpu_ids=["0", "1"],
            number_of_gpus_requested=1,
            placement_estimate=object(),
        )

        with patch.dict(
            "placement.strategies._STRATEGY_REGISTRY",
            {"oracle_ff": (lambda selector, req: selector(
                gpus_with_metrics=req.gpus_with_metrics,
                gpu_memory_requirement=mock_requirement(req),
                available_gpu_ids=req.available_gpu_ids,
                number_of_gpus_requested=req.number_of_gpus_requested,
            ), fake_selector)},
            clear=False,
        ):
            result = execute_placement_strategy("oracle_ff", request)

        self.assertEqual(result, 123)

    @patch("placement.strategies._resolve_gpu_memory_estimation")
    def test_est_strategy_returns_none_when_estimation_missing(self, mock_estimation):
        mock_estimation.return_value = None

        request = SimpleNamespace(
            policy="PROFILED-MAGM",
            gpus_with_metrics="metrics",
            available_gpu_ids=["0", "1"],
            number_of_gpus_requested=1,
            placement_estimate=object(),
        )

        result = execute_placement_strategy("est_magm", request)
        self.assertIsNone(result)

    def test_round_robin_strategy_returns_selector_result(self):
        request = SimpleNamespace(
            round_robin_generator=object(),
            available_gpu_ids=["0", "1"],
            number_of_gpus_requested=1,
            gpu_ids=["0", "1"],
        )

        def fake_rr_selector(**kwargs):
            return ["1"]

        with patch.dict(
            "placement.strategies._STRATEGY_REGISTRY",
            {"or_rr": (lambda selector, req: selector(
                round_robin_generator=req.round_robin_generator,
                available_gpu_ids=req.available_gpu_ids,
                number_of_gpus_requested=req.number_of_gpus_requested,
                gpu_ids=req.gpu_ids,
            ), fake_rr_selector)},
            clear=False,
        ):
            result = execute_placement_strategy("or_rr", request)

        self.assertEqual(result, ["1"])


if __name__ == "__main__":
    unittest.main()