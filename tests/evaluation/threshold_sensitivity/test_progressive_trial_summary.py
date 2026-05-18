import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.threshold_sensitivity.runners.run_progressive_threshold_trials import (
    build_trial_summary_from_rows,
)


def test_sequence_wall_time_includes_rejection_delay():
    trial = {
        "trial_id": "synthetic_rejection_delay",
        "gpu_id": 0,
        "cuda_visible_devices": "0",
        "job_sequence": ["job1.yaml", "job2.yaml"],
    }

    rows = [
        {
            "stage": 1,
            "decision": "launch_initial",
            "candidate_started": True,
            "candidate_finished": True,
            "candidate_started_at_monotonic": 100.0,
            "candidate_finished_at_monotonic": 300.0,
            "candidate_runtime_seconds": 200.0,
            "candidate_solo_runtime_seconds": 200.0,
        },
        {
            "stage": 2,
            "decision": "reject_retry_later",
            "candidate_started": False,
            "candidate_finished": False,
            "candidate_started_at_monotonic": "",
            "candidate_finished_at_monotonic": "",
            "candidate_runtime_seconds": "",
            "candidate_solo_runtime_seconds": 200.0,
        },
        {
            "stage": 2,
            "decision": "admit",
            "candidate_started": True,
            "candidate_finished": True,
            "candidate_started_at_monotonic": 320.0,
            "candidate_finished_at_monotonic": 520.0,
            "candidate_runtime_seconds": 200.0,
            "candidate_solo_runtime_seconds": 200.0,
        },
    ]

    summary = build_trial_summary_from_rows(
        trial=trial,
        rows=rows,
        tau_smact=0.5,
        tau_smocc=0.2,
        tau_drama=0.2,
        window_seconds=30.0,
    )

    assert summary["reject_retry_count"] == 1
    assert summary["solo_runtime_sum_seconds"] == 400.0
    assert summary["collocated_wall_time_seconds"] == 200.0
    assert summary["sequence_wall_time_seconds"] == 420.0
    assert summary["throughput_gain"] == 400.0 / 420.0


if __name__ == "__main__":
    test_sequence_wall_time_includes_rejection_delay()
    print("OK: progressive trial summary regression test passed")
