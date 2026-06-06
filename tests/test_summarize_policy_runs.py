from datetime import datetime, timezone
from pathlib import Path
import unittest

from datetime import datetime, timedelta, timezone

from evaluation.experiments.summarize_policy_runs import (
    summarize_attempts,
    summarize_jobs,
    summarize_run,
)


class SummarizePolicyRunsTests(unittest.TestCase):
    def test_recovered_job_metrics(self) -> None:
        # Replace numeric timestamps with valid ISO timestamps.
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)

        def make_event(name: str, seconds: int, **fields) -> dict:
            return {
                "event": name,
                "task_id": "task-1",
                "task_file": "workload.yaml",
                "emitted_at": (base + timedelta(seconds=seconds)).isoformat(),
                **fields,
            }

        events = [
            make_event("submitted", 0),
            make_event(
                "dispatched",
                10,
                recovered=False,
                recovery_count=0,
                assigned_gpu_ids=["GPU-0"],
            ),
            make_event(
                "launched",
                12,
                assigned_gpu_ids=["GPU-0"],
            ),
            make_event("failed", 52),
            make_event(
                "dispatched",
                72,
                recovered=True,
                recovery_count=1,
                assigned_gpu_ids=["GPU-1"],
            ),
            make_event(
                "launched",
                75,
                assigned_gpu_ids=["GPU-1"],
            ),
            make_event("completed", 155),
        ]

        metadata = {
            "experiment_name": "synthetic",
            "run_label": "AEGIS",
            "policy": "EST-MAGM",
            "estimator": "GPUMemNet",
            "trace_csv": "synthetic.csv",
        }
        run_dir = Path("/tmp/synthetic-run")

        attempts = summarize_attempts(
            run_dir=run_dir,
            metadata=metadata,
            events=events,
        )
        jobs = summarize_jobs(
            run_dir=run_dir,
            metadata=metadata,
            events=events,
            attempts=attempts,
        )


        run = summarize_run(
            run_dir=run_dir,
            metadata=metadata,
            jobs=jobs,
            attempts=attempts,
        )


        self.assertEqual(len(attempts), 2)
        self.assertEqual(len(jobs), 1)

        first, second = attempts
        job = jobs[0]

        self.assertEqual(first["attempt_number"], 1)
        self.assertFalse(first["recovered"])
        self.assertEqual(first["terminal_event"], "failed")
        self.assertAlmostEqual(first["attempt_runtime_s"], 40.0)

        self.assertEqual(second["attempt_number"], 2)
        self.assertTrue(second["recovered"])
        self.assertEqual(second["terminal_event"], "completed")
        self.assertAlmostEqual(second["attempt_runtime_s"], 80.0)
        self.assertAlmostEqual(second["recovery_queue_wait_s"], 20.0)
        self.assertAlmostEqual(second["dispatch_to_launch_s"], 3.0)
        self.assertAlmostEqual(second["recovery_gap_s"], 23.0)

        self.assertAlmostEqual(job["initial_queue_wait_s"], 10.0)
        self.assertAlmostEqual(job["jct_s"], 155.0)
        self.assertAlmostEqual(job["execution_span_s"], 143.0)
        self.assertAlmostEqual(
            job["successful_attempt_runtime_s"], 80.0
        )
        self.assertEqual(job["attempt_count"], 2)
        self.assertEqual(job["failed_attempt_count"], 1)
        self.assertEqual(job["recovered_attempt_count"], 1)
        self.assertAlmostEqual(job["total_attempt_runtime_s"], 120.0)
        self.assertAlmostEqual(job["failed_attempt_runtime_s"], 40.0)
        self.assertAlmostEqual(
            job["total_recovery_queue_wait_s"], 20.0
        )
        self.assertAlmostEqual(job["total_recovery_gap_s"], 23.0)
        self.assertEqual(job["maximum_recovery_count"], 1)
        self.assertTrue(job["completed_successfully"])


        self.assertEqual(run["submitted_job_count"], 1)
        self.assertEqual(run["completed_job_count"], 1)
        self.assertEqual(run["incomplete_job_count"], 0)
        self.assertAlmostEqual(run["completion_fraction"], 1.0)

        self.assertEqual(run["total_attempt_count"], 2)
        self.assertEqual(run["failed_attempt_count"], 1)
        self.assertEqual(run["recovered_attempt_count"], 1)

        self.assertAlmostEqual(run["makespan_s"], 155.0)
        self.assertAlmostEqual(run["total_recovery_queue_wait_s"], 20.0)
        self.assertAlmostEqual(run["total_failed_attempt_runtime_s"], 40.0)

        # Only one job exists, so every percentile equals that job's value.
        for suffix in ["mean_s", "p50_s", "p95_s", "p99_s"]:
            self.assertAlmostEqual(run[f"initial_queue_wait_{suffix}"], 10.0)
            self.assertAlmostEqual(run[f"jct_{suffix}"], 155.0)
            self.assertAlmostEqual(run[f"execution_span_{suffix}"], 143.0)
            self.assertAlmostEqual(
                run[f"successful_attempt_runtime_{suffix}"],
                80.0,
            )
            self.assertAlmostEqual(
                run[f"recovery_queue_wait_{suffix}"],
                20.0,
            )
            self.assertAlmostEqual(
                run[f"recovery_gap_{suffix}"],
                23.0,
            )


if __name__ == "__main__":
    unittest.main()