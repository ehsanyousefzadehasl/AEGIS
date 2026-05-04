import unittest
from unittest.mock import patch

import pandas as pd

from telemetry import monitor


def fake_gmetrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "sample_monotonic_time": 100.0,
                "sample_wall_time": "2026-05-04T16:00:00",
                "gpu_uuid": "GPU-test-0",
                "free_gpu_memory": 30000,
                "smact": 10,
                "smocc": 20,
                "drama": 30,
            },
            {
                "sample_monotonic_time": 101.0,
                "sample_wall_time": "2026-05-04T16:00:01",
                "gpu_uuid": "GPU-test-0",
                "free_gpu_memory": 29000,
                "smact": 20,
                "smocc": 30,
                "drama": 40,
            },
            {
                "sample_monotonic_time": 102.0,
                "sample_wall_time": "2026-05-04T16:00:02",
                "gpu_uuid": "GPU-test-0",
                "free_gpu_memory": 28000,
                "smact": 30,
                "smocc": 40,
                "drama": 50,
            },
        ]
    )


class TestMonitorSnapshotSummaries(unittest.TestCase):
    def test_summarize_gmetrics_snapshot_returns_scheduler_compatible_columns(self):
        data = fake_gmetrics()

        with patch.object(monitor, "gpu_uuids", return_value={"GPU-test-0": "0"}), patch.object(
            monitor, "gpu_mem_total", return_value={"GPU-test-0": 40000}
        ):
            out = monitor.summarize_Gmetrics_snapshot(data)

        self.assertIn("GPU-test-0", out.index)

        expected_columns = {
            "GPU_mem_available",
            "GPU_mem_total",
            "window_samples",
            "ewma_alpha",
            "smact_mean",
            "smact_median",
            "smact_p95",
            "smact_ewma",
            "smact_risk",
            "smocc_mean",
            "smocc_median",
            "smocc_p95",
            "smocc_ewma",
            "smocc_risk",
            "drama_mean",
            "drama_median",
            "drama_p95",
            "drama_ewma",
            "drama_risk",
            "smact",
            "smocc",
            "drama",
        }

        self.assertTrue(expected_columns.issubset(set(out.columns)))
        self.assertEqual(int(out.loc["GPU-test-0", "window_samples"]), 3)

        # Backward-compatible aliases used by placement/candidate filtering.
        self.assertEqual(out.loc["GPU-test-0", "smact"], out.loc["GPU-test-0", "smact_risk"])
        self.assertEqual(out.loc["GPU-test-0", "smocc"], out.loc["GPU-test-0", "smocc_risk"])
        self.assertEqual(out.loc["GPU-test-0", "drama"], out.loc["GPU-test-0", "drama_risk"])

    def test_analyze_gmetrics_preserves_existing_public_behavior(self):
        data = fake_gmetrics()

        with patch.object(monitor, "Gmetrics_are_valid", True), patch.object(
            monitor, "Gmetrics", data
        ), patch.object(monitor, "gpu_uuids", return_value={"GPU-test-0": "0"}), patch.object(
            monitor, "gpu_mem_total", return_value={"GPU-test-0": 40000}
        ):
            out = monitor.analyze_Gmetrics()

        self.assertIn("GPU-test-0", out.index)
        self.assertIn("smact", out.columns)
        self.assertIn("smocc", out.columns)
        self.assertIn("drama", out.columns)
        self.assertIn("smact_risk", out.columns)
        self.assertIn("smocc_risk", out.columns)
        self.assertIn("drama_risk", out.columns)

    def test_summarize_gmetrics_snapshot_includes_missing_gpu_with_empty_summary(self):
        data = fake_gmetrics()

        with patch.object(
            monitor,
            "gpu_uuids",
            return_value={
                "GPU-test-0": "0",
                "GPU-test-1": "1",
            },
        ), patch.object(
            monitor,
            "gpu_mem_total",
            return_value={
                "GPU-test-0": 40000,
                "GPU-test-1": 40000,
            },
        ):
            out = monitor.summarize_Gmetrics_snapshot(data)

        self.assertIn("GPU-test-1", out.index)
        self.assertEqual(int(out.loc["GPU-test-1", "window_samples"]), 0)


if __name__ == "__main__":
    unittest.main()