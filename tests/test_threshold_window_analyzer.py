import tempfile
import unittest
from pathlib import Path

import pandas as pd

from evaluation.threshold_sensitivity.analyze_solo_windows import (
    build_long_window_metrics,
    discover_window_columns,
    summarize_stability,
)


class TestThresholdWindowAnalyzer(unittest.TestCase):
    def test_discover_window_columns(self):
        df = pd.DataFrame(
            columns=[
                "run_id",
                "smact_risk_w5s",
                "smact_risk_w30s",
                "smact_risk_w200s",
                "smocc_risk_w30s",
                "unrelated",
            ]
        )

        found = discover_window_columns(df, ["smact_risk", "smocc_risk"])

        self.assertEqual(sorted(found.keys()), [5.0, 30.0, 200.0])
        self.assertEqual(found[30.0]["smact_risk"], "smact_risk_w30s")
        self.assertEqual(found[30.0]["smocc_risk"], "smocc_risk_w30s")

    def test_build_long_window_metrics(self):
        df = pd.DataFrame(
            [
                {
                    "run_id": "r1",
                    "task_path": "a.yaml",
                    "smact_risk_w5s": 10.0,
                    "smact_risk_w30s": 20.0,
                    "smact_risk_w200s": 25.0,
                }
            ]
        )

        long_df = build_long_window_metrics(df, ["smact_risk"])

        self.assertEqual(len(long_df), 3)
        self.assertEqual(sorted(long_df["summary_window_seconds"].tolist()), [5.0, 30.0, 200.0])

    def test_summarize_stability_against_reference_window(self):
        df = pd.DataFrame(
            [
                {
                    "run_id": "r1",
                    "smact_risk_w5s": 10.0,
                    "smact_risk_w30s": 20.0,
                    "smact_risk_w200s": 25.0,
                },
                {
                    "run_id": "r2",
                    "smact_risk_w5s": 20.0,
                    "smact_risk_w30s": 28.0,
                    "smact_risk_w200s": 30.0,
                },
            ]
        )

        long_df = build_long_window_metrics(df, ["smact_risk"])
        summary = summarize_stability(long_df, reference_window=200.0)

        row_30 = summary[
            (summary["metric"] == "smact_risk")
            & (summary["summary_window_seconds"] == 30.0)
        ].iloc[0]

        self.assertEqual(int(row_30["n"]), 2)
        self.assertAlmostEqual(row_30["mean_abs_error"], 3.5)


if __name__ == "__main__":
    unittest.main()