import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.event_cli import main as event_cli_main
from runtime.launcher import build_launch_command


class DummyTask:
    task_id = "task-123"
    task = "/tmp/workload.yaml"


class TestRuntimeLauncher(unittest.TestCase):
    def test_event_cli_records_return_code_when_provided(self):
        with tempfile.TemporaryDirectory() as tmp:
            event_path = Path(tmp) / "events.jsonl"

            with patch.object(
                sys,
                "argv",
                [
                    "event_cli",
                    "--event-path",
                    str(event_path),
                    "--record-json",
                    '{"event":"failed","task_id":"task-123"}',
                    "--return-code",
                    "7",
                ],
            ):
                event_cli_main()

            record = json.loads(event_path.read_text(encoding="utf-8").strip())
            self.assertEqual(record["event"], "failed")
            self.assertEqual(record["task_id"], "task-123")
            self.assertEqual(record["return_code"], 7)

    def test_launch_command_passes_workload_return_code_to_terminal_events(self):
        command = build_launch_command(
            dir="/tmp",
            gpus_identifiers="0",
            command_to_execute="python train.py",
            now="2026-05-04_13:00:00",
            task_obj=DummyTask(),
            event_path="/tmp/events.jsonl",
            run_id="run-123",
        )

        self.assertIn("wait $pid ; rc=$?", command)
        self.assertEqual(command.count('--return-code "$rc"'), 2)


if __name__ == "__main__":
    unittest.main()