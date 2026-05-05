import unittest

import pandas as pd

from evaluation.runners.analyze_solo_profile_results import (
    add_equal_weight_profile_scores,
    build_200s_vs_full,
    build_lucid_style_profile_labels,
    build_horus_oracle_inputs,
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
        long_df = add_equal_weight_profile_scores(long_df)

        risk_row = long_df[
            (long_df["metric"] == "smact")
            & (long_df["window"] == "200s")
            & (long_df["stat"] == "profile_stat_score")
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
        long_df = add_equal_weight_profile_scores(long_df)
        comparison = build_200s_vs_full(long_df)

        row = comparison[
            (comparison["metric"] == "smact")
            & (comparison["stat"] == "profile_stat_score")
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
        long_df = add_equal_weight_profile_scores(long_df)
        characterization = build_workload_characterization(
            long_df,
            compute_threshold=50.0,
            memory_threshold=30.0,
        )

        self.assertEqual(characterization.iloc[0]["coarse_resource_label"], "compute_heavy")
        self.assertIn("smact_profile_stat_score_full", characterization.columns)

    def test_build_lucid_style_profile_labels(self):
        df = pd.DataFrame(
            [
                {
                    "workload_id": "tiny",
                    "run_id": "r1",
                    "spec_path": "tiny.yaml",
                    "gpu_count": 1,
                    "smact_mean_200s": 1.0,
                    "smact_median_200s": 1.0,
                    "smact_mode_200s": 1.0,
                    "smact_max_200s": 1.0,
                    "smocc_mean_200s": 1.0,
                    "smocc_median_200s": 1.0,
                    "smocc_mode_200s": 1.0,
                    "smocc_max_200s": 1.0,
                    "drama_mean_200s": 1.0,
                    "drama_median_200s": 1.0,
                    "drama_mode_200s": 1.0,
                    "drama_max_200s": 1.0,
                    "gpu_memory_peak_200s_mib": 100.0,
                },
                {
                    "workload_id": "medium",
                    "run_id": "r2",
                    "spec_path": "medium.yaml",
                    "gpu_count": 1,
                    "smact_mean_200s": 20.0,
                    "smact_median_200s": 20.0,
                    "smact_mode_200s": 20.0,
                    "smact_max_200s": 20.0,
                    "smocc_mean_200s": 20.0,
                    "smocc_median_200s": 20.0,
                    "smocc_mode_200s": 20.0,
                    "smocc_max_200s": 20.0,
                    "drama_mean_200s": 20.0,
                    "drama_median_200s": 20.0,
                    "drama_mode_200s": 20.0,
                    "drama_max_200s": 20.0,
                    "gpu_memory_peak_200s_mib": 1000.0,
                },
                {
                    "workload_id": "jumbo",
                    "run_id": "r3",
                    "spec_path": "jumbo.yaml",
                    "gpu_count": 1,
                    "smact_mean_200s": 90.0,
                    "smact_median_200s": 90.0,
                    "smact_mode_200s": 90.0,
                    "smact_max_200s": 90.0,
                    "smocc_mean_200s": 90.0,
                    "smocc_median_200s": 90.0,
                    "smocc_mode_200s": 90.0,
                    "smocc_max_200s": 90.0,
                    "drama_mean_200s": 90.0,
                    "drama_median_200s": 90.0,
                    "drama_mode_200s": 90.0,
                    "drama_max_200s": 90.0,
                    "gpu_memory_peak_200s_mib": 9000.0,
                },
            ]
        )

        long_df = normalize_profile_dataframe(df, gpu_count=1)
        long_df = add_equal_weight_profile_scores(long_df)
        labels = build_lucid_style_profile_labels(long_df)

        classes = dict(zip(labels["workload_id"], labels["lucid_style_class_200s"]))

        self.assertEqual(classes["tiny"], "Tiny")
        self.assertEqual(classes["medium"], "Medium")
        self.assertEqual(classes["jumbo"], "Jumbo")

        scores = dict(zip(labels["workload_id"], labels["lucid_style_ss_200s"]))

        self.assertEqual(scores["tiny"], 0)
        self.assertEqual(scores["medium"], 1)
        self.assertEqual(scores["jumbo"], 2)

    def test_build_horus_oracle_inputs(self):
        df = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "run_id": "r1",
                    "spec_path": "bert.yaml",
                    "gpu_count": 1,
                    "gputl_mean_200s": 60.0,
                    "gputl_mean_full": 70.0,
                    "gputl_median_200s": 55.0,
                    "gputl_median_full": 65.0,
                    "gputl_max_200s": 90.0,
                    "gputl_max_full": 95.0,
                    "gpu_memory_peak_200s_mib": 1000.0,
                    "gpu_memory_peak_full_mib": 1200.0,
                }
            ]
        )

        long_df = normalize_profile_dataframe(df, gpu_count=1)
        horus = build_horus_oracle_inputs(long_df)

        row = horus.iloc[0]

        self.assertEqual(row["horus_oracle_util_full"], 70.0)
        self.assertEqual(row["horus_profile_util_200s"], 60.0)
        self.assertEqual(row["horus_oracle_util_median_full"], 65.0)
        self.assertEqual(row["horus_oracle_util_max_full"], 95.0)
        self.assertEqual(row["horus_oracle_memory_full_mib"], 1200.0)
        self.assertEqual(row["horus_abs_error_200s_vs_full_util"], 10.0)

    def test_aegis_profile_risk_is_only_computed_when_p95_and_ewma_exist(self):
        df = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "run_id": "r1",
                    "spec_path": "bert.yaml",
                    "gpu_count": 1,
                    "smact_mean_200s": 10.0,
                    "smact_median_200s": 20.0,
                    "smact_p95_200s": 30.0,
                    "smact_ewma_200s": 40.0,
                }
            ]
        )

        long_df = normalize_profile_dataframe(df, gpu_count=1)
        long_df = add_equal_weight_profile_scores(long_df)

        risk_row = long_df[
            (long_df["metric"] == "smact")
            & (long_df["window"] == "200s")
            & (long_df["stat"] == "aegis_profile_risk")
        ].iloc[0]

        self.assertEqual(risk_row["value"], 25.0)

        
if __name__ == "__main__":
    unittest.main()