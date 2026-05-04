import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evaluation.threshold_sensitivity.run_solo_baselines import (
    DEFAULT_SUMMARY_WINDOWS,
    build_live_runner_command,
    load_spec_paths,
    safe_name,
)


class TestThresholdSoloRunner(unittest.TestCase):
    def test_safe_name_replaces_path_unfriendly_characters(self):
        self.assertEqual(safe_name("bert/base bs=32"), "bert_base_bs_32")

    def test_load_spec_paths_ignores_blank_lines_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "specs.txt"
            manifest.write_text(
                "\n# comment\nworkloads/a.yaml\n/workloads/b.yaml\n",
                encoding="utf-8",
            )

            args = SimpleNamespace(
                spec=None,
                spec_list=str(manifest),
                limit=None,
            )

            specs = load_spec_paths(args, root)

            self.assertEqual(specs[0], (root / "workloads/a.yaml").resolve())
            self.assertEqual(specs[1], Path("/workloads/b.yaml").resolve())

    def test_load_spec_paths_applies_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "specs.txt"
            manifest.write_text(
                "a.yaml\nb.yaml\nc.yaml\n",
                encoding="utf-8",
            )

            args = SimpleNamespace(
                spec=None,
                spec_list=str(manifest),
                limit=2,
            )

            specs = load_spec_paths(args, root)

            self.assertEqual(len(specs), 2)
            self.assertEqual(specs[0], (root / "a.yaml").resolve())
            self.assertEqual(specs[1], (root / "b.yaml").resolve())

    def test_build_command_includes_default_summary_windows(self):
        args = SimpleNamespace(
            user="threshold-exp",
            estimator="None",
            window_seconds=30.0,
            summary_windows=DEFAULT_SUMMARY_WINDOWS,
            ttfk_timeout=300.0,
            window_timeout=900.0,
            finish_timeout=0.0,
            poll_seconds=0.5,
            gpu_uuid=None,
            gpu_id="0",
        )

        cmd = build_live_runner_command(
            spec_path=Path("/repo/workload.yaml"),
            workdir=Path("/repo"),
            run_id="run-123",
            event_path=Path("/suite/events/run-123.jsonl"),
            output_csv=Path("/suite/live_threshold_measurements.csv"),
            index_csv=Path("/suite/index.csv"),
            args=args,
        )

        self.assertIn("--task", cmd)
        self.assertIn("/repo/workload.yaml", cmd)
        self.assertIn("--window-seconds", cmd)
        self.assertIn("30.0", cmd)
        self.assertIn("--summary-windows", cmd)
        self.assertIn(DEFAULT_SUMMARY_WINDOWS, cmd)
        self.assertIn("--gpu-id", cmd)
        self.assertIn("0", cmd)
        self.assertIn("--output-csv", cmd)
        self.assertIn("/suite/live_threshold_measurements.csv", cmd)
        self.assertIn("--index-csv", cmd)
        self.assertIn("/suite/index.csv", cmd)


if __name__ == "__main__":
    unittest.main()