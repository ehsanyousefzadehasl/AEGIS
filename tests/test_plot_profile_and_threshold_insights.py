import unittest

import pandas as pd

from evaluation.runners.plot_profile_and_threshold_insights import (
    prepare_component_rollup,
    prepare_per_workload_heatmap,
    prepare_profile_score_mismatches,
    prepare_window_stability,
    short_label,
)


class TestPlotProfileAndThresholdInsights(unittest.TestCase):
    def test_short_label_truncates(self):
        value = "x" * 100
        out = short_label(value, max_len=12)
        self.assertEqual(len(out), 12)
        self.assertTrue(out.endswith("..."))

    def test_prepare_profile_score_mismatches(self):
        df = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "metric": "smact",
                    "stat": "aegis_profile_risk",
                    "value_200s": 0.5,
                    "value_full": 1.0,
                    "relative_error_200s_vs_full": 0.5,
                },
                {
                    "workload_id": "bert",
                    "metric": "smact",
                    "stat": "mean",
                    "value_200s": 0.5,
                    "value_full": 1.0,
                    "relative_error_200s_vs_full": 0.5,
                },
            ]
        )

        out = prepare_profile_score_mismatches(df)

        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["relative_error_percent"], 50.0)

    def test_prepare_window_stability(self):
        df = pd.DataFrame(
            [
                {
                    "metric": "smact_risk",
                    "summary_window_seconds": 30.0,
                    "reference_window_seconds": 200.0,
                    "mean_abs_error": 0.1,
                },
                {
                    "metric": "smact_mean",
                    "summary_window_seconds": 30.0,
                    "reference_window_seconds": 200.0,
                    "mean_abs_error": 0.2,
                },
            ]
        )

        out = prepare_window_stability(df, reference_window=200.0)

        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["metric"], "smact_risk")

    def test_prepare_component_rollup(self):
        df = pd.DataFrame(
            [
                {
                    "risk_component": "mean",
                    "summary_window_seconds": 30.0,
                    "weighted_mean_abs_error": 0.1,
                },
                {
                    "risk_component": "not_used",
                    "summary_window_seconds": 30.0,
                    "weighted_mean_abs_error": 0.2,
                },
            ]
        )

        out = prepare_component_rollup(df)

        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["risk_component"], "mean")

    def test_prepare_per_workload_heatmap(self):
        df = pd.DataFrame(
            [
                {
                    "task_path": "/tmp/bert.yaml",
                    "base_metric": "smact",
                    "risk_abs_error": 0.1,
                    "mean_abs_error": 0.2,
                },
                {
                    "task_path": "/tmp/bert.yaml",
                    "base_metric": "smocc",
                    "risk_abs_error": 0.2,
                    "mean_abs_error": 0.3,
                },
                {
                    "task_path": "/tmp/gpt.yaml",
                    "base_metric": "drama",
                    "risk_abs_error": 0.3,
                    "mean_abs_error": 0.4,
                },
            ]
        )

        out = prepare_per_workload_heatmap(df, top_k=2, component="mean")

        self.assertIn("smact", out.columns)
        self.assertIn("smocc", out.columns)
        self.assertIn("drama", out.columns)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()