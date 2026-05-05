import unittest

import pandas as pd

from evaluation.threshold_sensitivity.summarize_solo_windows import (
    build_per_workload_risk_components,
    build_summary,
    split_risk_component_metric,
)


class TestThresholdWindowSummary(unittest.TestCase):
    def test_split_risk_component_metric(self):
        self.assertEqual(split_risk_component_metric("smact_mean"), ("smact", "mean"))
        self.assertEqual(split_risk_component_metric("smocc_p95"), ("smocc", "p95"))
        self.assertEqual(split_risk_component_metric("drama_ewma"), ("drama", "ewma"))
        self.assertEqual(split_risk_component_metric("gpu_memory"), (None, None))

    def test_build_per_workload_risk_components(self):
        long_df = pd.DataFrame(
            [
                {
                    "row_index": 0,
                    "run_id": "r1",
                    "task_path": "a.yaml",
                    "summary_window_seconds": 30.0,
                    "metric": "smact_mean",
                    "value": 10.0,
                },
                {
                    "row_index": 0,
                    "run_id": "r1",
                    "task_path": "a.yaml",
                    "summary_window_seconds": 200.0,
                    "metric": "smact_mean",
                    "value": 12.0,
                },
                {
                    "row_index": 0,
                    "run_id": "r1",
                    "task_path": "a.yaml",
                    "summary_window_seconds": 30.0,
                    "metric": "smact_risk",
                    "value": 20.0,
                },
                {
                    "row_index": 0,
                    "run_id": "r1",
                    "task_path": "a.yaml",
                    "summary_window_seconds": 200.0,
                    "metric": "smact_risk",
                    "value": 25.0,
                },
            ]
        )

        out = build_per_workload_risk_components(
            long_df,
            decision_window=30.0,
            reference_window=200.0,
        )

        self.assertEqual(len(out), 1)
        row = out.iloc[0]

        self.assertEqual(row["base_metric"], "smact")
        self.assertEqual(row["mean_w30s"], 10.0)
        self.assertEqual(row["mean_w200s"], 12.0)
        self.assertEqual(row["risk_w30s"], 20.0)
        self.assertEqual(row["risk_w200s"], 25.0)
        self.assertEqual(row["risk_abs_error"], 5.0)

    def test_build_summary_contains_per_workload_section(self):
        long_df = pd.DataFrame(
            [
                {
                    "row_index": 0,
                    "run_id": "r1",
                    "task_path": "a.yaml",
                    "summary_window_seconds": 30.0,
                    "metric": "smact_risk",
                    "value": 20.0,
                },
                {
                    "row_index": 0,
                    "run_id": "r1",
                    "task_path": "a.yaml",
                    "summary_window_seconds": 200.0,
                    "metric": "smact_risk",
                    "value": 25.0,
                },
            ]
        )

        text = build_summary(
            stability=pd.DataFrame(),
            long_df=long_df,
            measurements=pd.DataFrame(),
            reference_window=200.0,
            decision_window=30.0,
            top_k=10,
        )

        self.assertIn("Per-workload risk-component breakdown", text)
        self.assertIn("a.yaml", text)


if __name__ == "__main__":
    unittest.main()