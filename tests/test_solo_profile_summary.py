import unittest

import pandas as pd

from evaluation.runners.summarize_solo_profile_analysis import (
    build_summary,
    markdown_table,
    summarize_label_distribution,
    summarize_profile_score_components,
)


class TestSoloProfileSummary(unittest.TestCase):
    def test_markdown_table_handles_missing_columns(self):
        df = pd.DataFrame([{"a": 1}])
        text = markdown_table(df, ["missing"], max_rows=5)
        self.assertIn("missing", text.lower())

    def test_summarize_label_distribution(self):
        labels = pd.DataFrame(
            [
                {"lucid_style_class_200s": "Tiny"},
                {"lucid_style_class_200s": "Tiny"},
                {"lucid_style_class_200s": "Jumbo"},
            ]
        )

        text = summarize_label_distribution(labels)

        self.assertIn("Tiny", text)
        self.assertIn("Jumbo", text)
        self.assertIn("2", text)

    def test_build_summary_contains_main_sections(self):
        labels = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "source_gpu_count": 1,
                    "gpu_label": "single",
                    "lucid_style_pressure_score_200s": 0.9,
                    "lucid_style_ss_200s": 2,
                    "lucid_style_class_200s": "Jumbo",
                }
            ]
        )

        comparison = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "source_gpu_count": 1,
                    "gpu_label": "single",
                    "metric": "smact",
                    "stat": "profile_stat_score",
                    "value_200s": 20.0,
                    "value_full": 30.0,
                    "abs_error_200s_vs_full": 10.0,
                    "relative_error_200s_vs_full": 0.333,
                }
            ]
        )

        characterization = pd.DataFrame(
            [
                {
                    "workload_id": "bert",
                    "coarse_resource_label": "compute_heavy",
                }
            ]
        )

        text = build_summary(
            labels=labels,
            comparison=comparison,
            characterization=characterization,
            top_k=5,
        )

        self.assertIn("Lucid-style 200s profile labels", text)
        self.assertIn("Largest 200s-vs-full mismatches", text)
        self.assertIn("Jumbo", text)
        self.assertIn("compute_heavy", text)
        
    def test_summarize_profile_score_components(self):
        comparison = pd.DataFrame(
            [
                {
                    "metric": "smact",
                    "stat": "mean",
                    "value_200s": 10.0,
                    "value_full": 20.0,
                    "abs_error_200s_vs_full": 10.0,
                    "relative_error_200s_vs_full": 0.5,
                },
                {
                    "metric": "smact",
                    "stat": "profile_stat_score",
                    "value_200s": 15.0,
                    "value_full": 25.0,
                    "abs_error_200s_vs_full": 10.0,
                    "relative_error_200s_vs_full": 0.4,
                },
            ]
        )

        out = summarize_profile_score_components(comparison)

        self.assertIn("mean_200s", out.columns)
        self.assertIn("mean_full", out.columns)
        self.assertIn("mean_abs_error", out.columns)
        self.assertIn("profile_stat_score", set(out["stat"]))

if __name__ == "__main__":
    unittest.main()