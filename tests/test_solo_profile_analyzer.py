import unittest

import pandas as pd

from evaluation.runners.analyze_solo_profile_results import (
    add_equal_weight_profile_risk,
    build_200s_vs_full,
    build_workload_characterization,
    normalize_profile_dataframe,
    parse_profile_column,
)


class TestSoloProfileAnalyzer(unittest.TestCase):
    def test_parse_1gpu_profile_columns(self):
        parsed = parse_profile_column("smact_mean_200s", "single")
        self.assertEqual(parsed["gpu_label"], "single")
        self.assertEqual(parsed["metric"], "smact")
        self.assertEqual(parsed["stat"], "mean")
        self.assertEqual(parsed["window"], "200s")

        parsed = parse_profile_column("gpu_memory_peak_full_mib", "single")
        self.assertEqual(parsed["metric"], "gpu_memory_peak_mib")
        self.assertEqual(parsed["stat"], "peak")
        self.assertEqual(parsed["window"], "full")

    def test_parse_2gpu_profile_columns(self):
        parsed = parse_profile_column("smact_mean_200s_gpu_a", "unknown")
        self.assertEqual(parsed["gpu_label"], "gpu_a")
        self.assertEqual(parsed["metric"], "smact")
        self.assertEqual(parsed["stat"], "mean")
        self.assertEqual(parsed["window"], "200s")

        parsed = parse_profile_column("gpu_memory_peak_full_mib_sum", "unknown")
        self.assertEqual(parsed["gpu_label"], "sum")
        self.assertEqual(parsed["metric"], "gpu_memory_peak_mib")
        self.assertEqual(parsed["stat"], "peak")
        self.assertEqual(parsed["window"], "full")

    def test_equal_weight_profile_risk(self):
        df = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "run_id": "r1",
                    "spec_path": "bert.yaml",
                    "gpu_count": 1,
                    "smact_mean_200s": 10.0,
                    "smact_median_200s": 20.0,
                    "smact_mode_200s": 30.0,
                    "smact_max_200s": 40.0,
                }
            ]
        )

        long_df = normalize_profile_dataframe(df, gpu_count=1)
        long_df = add_equal_weight_profile_risk(long_df)

        risk_row = long_df[
            (long_df["metric"] == "smact")
            & (long_df["window"] == "200s")
            & (long_df["stat"] == "profile_risk")
        ].iloc[0]

        self.assertEqual(risk_row["value"], 25.0)

    def test_build_200s_vs_full_includes_profile_risk(self):
        df = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "run_id": "r1",
                    "spec_path": "bert.yaml",
                    "gpu_count": 1,
                    "smact_mean_200s": 10.0,
                    "smact_median_200s": 20.0,
                    "smact_mode_200s": 30.0,
                    "smact_max_200s": 40.0,
                    "smact_mean_full": 20.0,
                    "smact_median_full": 30.0,
                    "smact_mode_full": 40.0,
                    "smact_max_full": 50.0,
                }
            ]
        )

        long_df = normalize_profile_dataframe(df, gpu_count=1)
        long_df = add_equal_weight_profile_risk(long_df)
        comparison = build_200s_vs_full(long_df)

        row = comparison[
            (comparison["metric"] == "smact")
            & (comparison["stat"] == "profile_risk")
        ].iloc[0]

        self.assertEqual(row["value_200s"], 25.0)
        self.assertEqual(row["value_full"], 35.0)
        self.assertEqual(row["abs_error_200s_vs_full"], 10.0)

    def test_build_workload_characterization_uses_profile_risk(self):
        df = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "run_id": "r1",
                    "spec_path": "bert.yaml",
                    "gpu_count": 1,
                    "smact_mean_full": 60.0,
                    "smact_median_full": 60.0,
                    "smact_mode_full": 60.0,
                    "smact_max_full": 60.0,
                    "smocc_mean_full": 30.0,
                    "smocc_median_full": 30.0,
                    "smocc_mode_full": 30.0,
                    "smocc_max_full": 30.0,
                    "drama_mean_full": 10.0,
                    "drama_median_full": 10.0,
                    "drama_mode_full": 10.0,
                    "drama_max_full": 10.0,
                    "gpu_memory_peak_full_mib": 1200.0,
                }
            ]
        )

        long_df = normalize_profile_dataframe(df, gpu_count=1)
        long_df = add_equal_weight_profile_risk(long_df)
        characterization = build_workload_characterization(
            long_df,
            compute_threshold=50.0,
            memory_threshold=30.0,
        )

        self.assertEqual(characterization.iloc[0]["coarse_resource_label"], "compute_heavy")
        self.assertIn("smact_profile_risk_full", characterization.columns)


if __name__ == "__main__":
    unittest.main()