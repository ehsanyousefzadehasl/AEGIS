import unittest

from placement.inputs import (
    PlacementEstimate,
    get_missing_policy_input_message,
    resolve_peak_memory_estimation_from_estimate,
    resolve_peak_memory_requirement_from_estimate,
    resolve_required_policy_profile_metrics,
)
from workload.resource_profile import ResourceProfile


class TestPlacementInputs(unittest.TestCase):
    def test_resolve_oracle_requirement_from_estimate(self):
        estimate = PlacementEstimate(
            source="oracle_requirement",
            resource_profile=ResourceProfile(
                peak_memory_mib=1234,
                source="task_file_requirement",
            ),
        )
        self.assertEqual(
            resolve_peak_memory_requirement_from_estimate(
                placement_estimate=estimate,
            ),
            1234,
        )

    def test_resolve_profiled_estimation_from_estimate(self):
        estimate = PlacementEstimate(
            source="profiled_metadata",
            resource_profile=ResourceProfile(
                peak_memory_mib=2222,
                source="profiled",
            ),
        )
        self.assertEqual(
            resolve_peak_memory_estimation_from_estimate(
                policy="PROFILED-MAGM",
                placement_estimate=estimate,
            ),
            2222,
        )

    def test_resolve_required_profile_metrics(self):
        estimate = PlacementEstimate(
            source="profiled_metadata",
            resource_profile=ResourceProfile(
                peak_memory_mib=3333,
                source="profiled",
            ),
        )
        self.assertEqual(
            resolve_required_policy_profile_metrics(
                policy="PROFILED-MAGM",
                placement_estimate=estimate,
            ),
            {"peak_memory_mib": 3333},
        )

    def test_missing_profiled_metrics_message(self):
        estimate = PlacementEstimate(
            source="profiled_metadata",
            resource_profile=ResourceProfile(
                source="profiled",
            ),
        )
        self.assertEqual(
            get_missing_policy_input_message(
                policy="PROFILED-MAGM",
                task="task.yaml",
                estimator_name="dummy",
                placement_estimate=estimate,
            ),
            "Could not resolve required profiled metrics for task task.yaml",
        )


if __name__ == "__main__":
    unittest.main()