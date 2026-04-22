import tempfile
import unittest
from pathlib import Path
from threading import Lock
from unittest.mock import Mock, patch

from queueing.task_queue import Task, Tasks
from runtime.dispatch import dispatch_selected_job


class TestRuntimeDispatch(unittest.TestCase):
    @patch("runtime.dispatch.dequeue_selected_job")
    def test_pid_capture_failure_requeues_main_task(self, mock_dequeue):
        with tempfile.TemporaryDirectory() as tmp:
            task_path = f"{tmp}/a.rad"
            task_obj = Task("u", tmp, task_path)

            main_queue = Tasks()
            recovery_queue = Tasks()
            logger = Mock()

            result = dispatch_selected_job(
                selected=object(),
                task_obj=task_obj,
                user="u",
                dir=tmp,
                task=task_path,
                environment="env",
                command_to_execute="python train.py",
                assigned_gpu_ids=["GPU-0"],
                now="2026-04-21_12:00:00",
                main_queue=main_queue,
                recovery_queue=recovery_queue,
                main_lock=Lock(),
                recovery_lock=Lock(),
                command_generator=Mock(return_value="echo launch"),
                command_executor=Mock(),
                launch_and_get_pid=Mock(return_value=None),
                launch_task=Mock(),
                async_resolve_and_update=Mock(),
                logger=logger,
            )

            self.assertIsNone(result)
            self.assertEqual(main_queue.length(), 1)
            self.assertIs(main_queue.whole_list()[0], task_obj)
            self.assertEqual(recovery_queue.length(), 0)
            logger.error.assert_called()
            mock_dequeue.assert_called_once()

            events_path = Path(tmp) / "events.jsonl"
            self.assertTrue(events_path.exists())
            self.assertIn('"event": "launch_failed"', events_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()