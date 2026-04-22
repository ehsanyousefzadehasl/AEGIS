import unittest
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path
from threading import Lock

from recovery.manager import (
    _capacity_recovery_buckets_mib,
    _classify_recovery_failure,
    _estimator_recovery_min_free_mib_override,
    _next_estimator_recovery_min_free_mib,
    _recovery_min_free_mib_override,
    recovery,
)
from queueing.task_queue import Task, Tasks


class TestRecoveryManager(unittest.TestCase):
    def test_oblivious_recovery_ladder(self):
        self.assertIsNone(_recovery_min_free_mib_override(0, 40 * 1024))
        self.assertEqual(_recovery_min_free_mib_override(1, 40 * 1024), 10 * 1024)
        self.assertEqual(_recovery_min_free_mib_override(2, 40 * 1024), 20 * 1024)
        self.assertEqual(_recovery_min_free_mib_override(3, 40 * 1024), 30 * 1024)
        self.assertIsNone(_recovery_min_free_mib_override(4, 40 * 1024))

    def test_estimator_bucket_step(self):
        self.assertEqual(_next_estimator_recovery_min_free_mib(8 * 1024, 40 * 1024), 10 * 1024)
        self.assertEqual(_next_estimator_recovery_min_free_mib(15 * 1024, 40 * 1024), 20 * 1024)
        self.assertEqual(_next_estimator_recovery_min_free_mib(25 * 1024, 40 * 1024), 30 * 1024)
        self.assertIsNone(_next_estimator_recovery_min_free_mib(35 * 1024, 40 * 1024))

    def test_estimator_recovery_ladder_from_failed_threshold(self):
        self.assertEqual(
            _estimator_recovery_min_free_mib_override(5665, 1, 40 * 1024),
            10 * 1024,
        )
        self.assertEqual(
            _estimator_recovery_min_free_mib_override(5665, 2, 40 * 1024),
            20 * 1024,
        )
        self.assertEqual(
            _estimator_recovery_min_free_mib_override(15 * 1024, 1, 40 * 1024),
            20 * 1024,
        )
        self.assertEqual(
            _estimator_recovery_min_free_mib_override(15 * 1024, 2, 40 * 1024),
            30 * 1024,
        )
        self.assertIsNone(
            _estimator_recovery_min_free_mib_override(15 * 1024, 3, 40 * 1024),
        )

    def test_recovery_ladder_exhaustion_represents_terminal_fallback(self):
        self.assertIsNone(_recovery_min_free_mib_override(4, 40 * 1024))
        self.assertIsNone(_estimator_recovery_min_free_mib_override(15 * 1024, 3, 40 * 1024))
    
    def test_capacity_recovery_buckets_scale_with_gpu_memory(self):
        self.assertEqual(
            _capacity_recovery_buckets_mib(40 * 1024),
            (10 * 1024, 20 * 1024, 30 * 1024),
        )
        self.assertEqual(
            _capacity_recovery_buckets_mib(80 * 1024),
            (20 * 1024, 40 * 1024, 60 * 1024),
        )
        
    def test_recovery_stops_after_failed_full_gpu_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            err_path = tmp_path / "err-2026-04-21_12:00:00-tid.log"

            err_path.write_text(
                f"{tmp}+env+python x.py+{tmp}/a.rad+u+tid+2026-04-21_12:00:00+3+1\n"
                "OOM\n",
                encoding="utf-8",
            )

            handled_crashes = []
            recovery_queue = Tasks()
            recovery_lock = Lock()
            logger = Mock()

            recovery(
                dirs=[tmp],
                handled_crashes=handled_crashes,
                task_cls=Task,
                recovery_queue=recovery_queue,
                recovery_lock=recovery_lock,
                logger=logger,
                policy="OR-MAGM",
                estimator_name="horus",
            )

            self.assertEqual(recovery_queue.length(), 0)
            self.assertIn(str(err_path), handled_crashes)
            logger.warning.assert_called()

    def test_non_oom_failure_does_not_block_later_oom_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            non_oom_err = tmp_path / "err-2026-04-21_12:00:00-nonoom.log"
            non_oom_err.write_text(
                f"{tmp}+env+python bad.py+{tmp}/bad.rad+u+nonoom+2026-04-21_12:00:00+0+0\n"
                "unsuccessful\n",
                encoding="utf-8",
            )

            oom_err = tmp_path / "err-2026-04-21_12:00:01-oom.log"
            oom_err.write_text(
                f"{tmp}+env+python train.py+{tmp}/good.rad+u+oomtask+2026-04-21_12:00:01+0+0\n"
                "RESOURCE_EXHAUSTED\n",
                encoding="utf-8",
            )

            handled_crashes = []
            recovery_queue = Tasks()
            recovery_lock = Lock()
            logger = Mock()

            recovery(
                dirs=[tmp],
                handled_crashes=handled_crashes,
                task_cls=Task,
                recovery_queue=recovery_queue,
                recovery_lock=recovery_lock,
                logger=logger,
                policy="OR-MAGM",
                estimator_name="horus",
            )

            self.assertEqual(recovery_queue.length(), 1)
            self.assertEqual(recovery_queue.whole_list()[0].task_id, "oomtask")
            self.assertIn(str(non_oom_err), handled_crashes)
            self.assertIn(str(oom_err), handled_crashes)
            logger.warning.assert_called()
            logger.info.assert_called()

    def test_classifier_ignores_oom_substring_in_recovery_header(self):
        lines = [
            "/tmp+env+python bad.py+/tmp/bad.rad+u+nonoom+2026-04-21_12:00:00+0+0\n",
            "unsuccessful\n",
        ]

        self.assertEqual(_classify_recovery_failure(lines), "nonzero_exit")

    def test_non_oom_failure_is_not_requeued(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            err_path = tmp_path / "err-2026-04-21_12:00:00-nonoom.log"

            err_path.write_text(
                f"{tmp}+env+python bad.py+{tmp}/bad.rad+u+nonoom+2026-04-21_12:00:00+0+0\n"
                "unsuccessful\n",
                encoding="utf-8",
            )

            handled_crashes = []
            recovery_queue = Tasks()
            recovery_lock = Lock()
            logger = Mock()

            recovery(
                dirs=[tmp],
                handled_crashes=handled_crashes,
                task_cls=Task,
                recovery_queue=recovery_queue,
                recovery_lock=recovery_lock,
                logger=logger,
                policy="OR-MAGM",
                estimator_name="horus",
            )

            self.assertEqual(recovery_queue.length(), 0)
            self.assertIn(str(err_path), handled_crashes)
            logger.warning.assert_called()

    def test_classifier_detects_framework_oom_messages(self):
        self.assertEqual(
            _classify_recovery_failure(
                ["header\n", "RuntimeError: CUDA out of memory\n"]
            ),
            "oom",
        )
        self.assertEqual(
            _classify_recovery_failure(
                ["header\n", "ResourceExhaustedError: OOM when allocating tensor with shape\n"]
            ),
            "oom",
        )

    def test_classifier_detects_conda_and_generic_failures_as_non_oom(self):
        self.assertEqual(
            _classify_recovery_failure(
                [
                    "header\n",
                    "ERROR conda.cli.main_run:execute(125): `conda run ...` failed.\n",
                    "non-ok-status\n",
                ]
            ),
            "non_ok_status",
        )
        self.assertEqual(
            _classify_recovery_failure(["header\n", "unsuccessful\n"]),
            "nonzero_exit",
        )

    @patch("recovery.manager._recovery_total_mem_mib", return_value=40 * 1024)
    def test_oom_recovery_requeues_task_with_capacity_aware_override(self, _mock_total_mem):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            err_path = tmp_path / "err-2026-04-21_12:00:00-oomtask.log"

            err_path.write_text(
                f"{tmp}+env+python train.py+{tmp}/good.rad+u+oomtask+2026-04-21_12:00:00+0+0\n"
                "RuntimeError: CUDA out of memory\n",
                encoding="utf-8",
            )

            handled_crashes = []
            recovery_queue = Tasks()
            recovery_lock = Lock()
            logger = Mock()

            recovery(
                dirs=[tmp],
                handled_crashes=handled_crashes,
                task_cls=Task,
                recovery_queue=recovery_queue,
                recovery_lock=recovery_lock,
                logger=logger,
                policy="OR-MAGM",
                estimator_name="horus",
            )

            self.assertEqual(recovery_queue.length(), 1)

            recovered_task = recovery_queue.whole_list()[0]
            self.assertEqual(recovered_task.task_id, "oomtask")
            self.assertEqual(recovered_task.user_submit_time, "2026-04-21_12:00:00")
            self.assertEqual(recovered_task.recovery_count, 1)
            self.assertEqual(recovered_task.last_failure_reason, "oom")
            self.assertEqual(recovered_task.recovery_min_free_mib_override, 10 * 1024)
            self.assertFalse(recovered_task.recovery_force_full_gpu)

    @patch("recovery.manager._base_effective_min_free_mib_for_estimate_policy", return_value=15 * 1024)
    @patch("recovery.manager._recovery_total_mem_mib", return_value=40 * 1024)
    def test_estimate_oom_recovery_uses_next_capacity_bucket(
        self,
        _mock_total_mem,
        _mock_base_threshold,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            err_path = tmp_path / "err-2026-04-21_12:00:00-estoom.log"

            err_path.write_text(
                f"{tmp}+env+python train.py+{tmp}/good.rad+u+estoom+2026-04-21_12:00:00+0+0\n"
                "ResourceExhaustedError: OOM when allocating tensor with shape\n",
                encoding="utf-8",
            )

            handled_crashes = []
            recovery_queue = Tasks()
            recovery_lock = Lock()
            logger = Mock()

            recovery(
                dirs=[tmp],
                handled_crashes=handled_crashes,
                task_cls=Task,
                recovery_queue=recovery_queue,
                recovery_lock=recovery_lock,
                logger=logger,
                policy="EST-BF",
                estimator_name="horus",
            )

            self.assertEqual(recovery_queue.length(), 1)

            recovered_task = recovery_queue.whole_list()[0]
            self.assertEqual(recovered_task.task_id, "estoom")
            self.assertEqual(recovered_task.user_submit_time, "2026-04-21_12:00:00")
            self.assertEqual(recovered_task.recovery_count, 1)
            self.assertEqual(recovered_task.last_failure_reason, "oom")
            self.assertEqual(recovered_task.recovery_min_free_mib_override, 20 * 1024)
            self.assertFalse(recovered_task.recovery_force_full_gpu)

    @patch("recovery.manager._recovery_total_mem_mib", return_value=40 * 1024)
    def test_oom_recovery_marks_full_gpu_after_oblivious_ladder_exhaustion(
        self,
        _mock_total_mem,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            err_path = tmp_path / "err-2026-04-21_12:00:00-fullgpu.log"

            err_path.write_text(
                f"{tmp}+env+python train.py+{tmp}/good.rad+u+fullgpu+2026-04-21_12:00:00+3+0\n"
                "RuntimeError: CUDA out of memory\n",
                encoding="utf-8",
            )

            handled_crashes = []
            recovery_queue = Tasks()
            recovery_lock = Lock()
            logger = Mock()

            recovery(
                dirs=[tmp],
                handled_crashes=handled_crashes,
                task_cls=Task,
                recovery_queue=recovery_queue,
                recovery_lock=recovery_lock,
                logger=logger,
                policy="OR-MAGM",
                estimator_name="horus",
            )

            self.assertEqual(recovery_queue.length(), 1)

            recovered_task = recovery_queue.whole_list()[0]
            self.assertEqual(recovered_task.task_id, "fullgpu")
            self.assertEqual(recovered_task.recovery_count, 4)
            self.assertIsNone(recovered_task.recovery_min_free_mib_override)
            self.assertTrue(recovered_task.recovery_force_full_gpu)

    @patch("recovery.manager._base_effective_min_free_mib_for_estimate_policy", return_value=15 * 1024)
    @patch("recovery.manager._recovery_total_mem_mib", return_value=40 * 1024)
    def test_estimate_oom_recovery_marks_full_gpu_after_ladder_exhaustion(
        self,
        _mock_total_mem,
        _mock_base_threshold,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            err_path = tmp_path / "err-2026-04-21_12:00:00-estfullgpu.log"

            err_path.write_text(
                f"{tmp}+env+python train.py+{tmp}/good.rad+u+estfullgpu+2026-04-21_12:00:00+2+0\n"
                "ResourceExhaustedError: OOM when allocating tensor with shape\n",
                encoding="utf-8",
            )

            handled_crashes = []
            recovery_queue = Tasks()
            recovery_lock = Lock()
            logger = Mock()

            recovery(
                dirs=[tmp],
                handled_crashes=handled_crashes,
                task_cls=Task,
                recovery_queue=recovery_queue,
                recovery_lock=recovery_lock,
                logger=logger,
                policy="EST-BF",
                estimator_name="horus",
            )

            self.assertEqual(recovery_queue.length(), 1)

            recovered_task = recovery_queue.whole_list()[0]
            self.assertEqual(recovered_task.task_id, "estfullgpu")
            self.assertEqual(recovered_task.recovery_count, 3)
            self.assertIsNone(recovered_task.recovery_min_free_mib_override)
            self.assertTrue(recovered_task.recovery_force_full_gpu)
            
if __name__ == "__main__":
    unittest.main()