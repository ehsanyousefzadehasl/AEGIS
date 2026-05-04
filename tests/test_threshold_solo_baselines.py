import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evaluation.threshold_sensitivity.run_solo_baselines import (
    build_live_runner_command,
    load_spec_paths,
    resolve_maybe_relative,
    safe_name,
)


class TestThresholdSoloBaselines(unittest.TestCase):
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

            specs = load_spec_paths(
                SimpleNamespace(spec=None, spec_list=str(manifest)),
                root,
            )

            self.assertEqual(specs[0], (root / "workloads/a.yaml").resolve())
            self.assertEqual(specs[1], Path("/workloads/b.yaml").resolve())

    def test_build_live_runner_command_includes_shared_outputs_and_gpu_id(self):
        args = SimpleNamespace(
            user="threshold-exp",
            estimator="None",
            window_seconds=30.0,
            ttfk_timeout=300.0,
            window_timeout=600.0,
            finish_timeout=0.0,
            poll_seconds=0.5,
            gpu_uuid=None,
            gpu_id="0",
        )

        cmd = build_live_runner_command(
            spec_path=Path("/repo/spec.yaml"),
            workdir=Path("/repo"),
            run_id="run-123",
            event_path=Path("/suite/events/run-123.jsonl"),
            output_csv=Path("/suite/live_threshold_measurements.csv"),
            index_csv=Path("/suite/index.csv"),
            args=args,
        )

        self.assertIn("--task", cmd)
        self.assertIn("/repo/spec.yaml", cmd)
        self.assertIn("--run-id", cmd)
        self.assertIn("run-123", cmd)
        self.assertIn("--output-csv", cmd)
        self.assertIn("/suite/live_threshold_measurements.csv", cmd)
        self.assertIn("--index-csv", cmd)
        self.assertIn("/suite/index.csv", cmd)
        self.assertIn("--gpu-id", cmd)
        self.assertIn("0", cmd)


if __name__ == "__main__":
    unittest.main()