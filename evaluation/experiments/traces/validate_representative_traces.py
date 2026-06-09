from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workload.job_spec import load_job_spec



TRACE_DIR = (
    REPO_ROOT
    / "evaluation"
    / "experiments"
    / "traces"
    / "representative"
)

EXPECTED = {
    "philly_seed42_60jobs.execution.csv": {
        1: 58,
        2: 2,
    },
    "saturn_seed42_60jobs.execution.csv": {
        1: 56,
        2: 4,
    },
    "venus_seed42_60jobs.execution.csv": {
        1: 57,
        2: 3,
    },
}


def read_declared_gpu_count(task_path: Path) -> int:
    with task_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError(
            f"{task_path}: YAML root must be a mapping"
        )

    resources = raw.get("resources")

    if not isinstance(resources, dict):
        raise ValueError(
            f"{task_path}: missing resources mapping"
        )

    num_gpus = resources.get("num_gpus")

    if num_gpus is None:
        raise ValueError(
            f"{task_path}: missing resources.num_gpus"
        )

    num_gpus = int(num_gpus)

    if num_gpus not in {1, 2}:
        raise ValueError(
            f"{task_path}: unsupported GPU count {num_gpus}"
        )

    return num_gpus


def validate_trace(
    trace_path: Path,
    expected_gpu_counts: dict[int, int],
) -> dict:
    trace = pd.read_csv(trace_path)

    expected_columns = [
        "submit_time_s",
        "task_path",
    ]

    if trace.columns.tolist() != expected_columns:
        raise ValueError(
            f"{trace_path}: expected columns "
            f"{expected_columns}, found "
            f"{trace.columns.tolist()}"
        )

    if len(trace) != 60:
        raise ValueError(
            f"{trace_path}: expected 60 jobs, "
            f"found {len(trace)}"
        )

    submit_times = pd.to_numeric(
        trace["submit_time_s"],
        errors="raise",
    )

    if submit_times.isna().any():
        raise ValueError(
            f"{trace_path}: submission times contain NaN"
        )

    if (submit_times < 0).any():
        raise ValueError(
            f"{trace_path}: submission times must be nonnegative"
        )

    if not submit_times.is_monotonic_increasing:
        raise ValueError(
            f"{trace_path}: submission times are not "
            "nondecreasing"
        )

    if float(submit_times.iloc[0]) != 0.0:
        raise ValueError(
            f"{trace_path}: first submission must be at 0 s"
        )

    gpu_counts: Counter[int] = Counter()
    missing_paths: list[str] = []
    absolute_paths: list[str] = []
    load_failures: list[str] = []

    for row_index, task_value in enumerate(
        trace["task_path"],
        start=1,
    ):
        task_text = str(task_value).strip()
        task_path = Path(task_text)

        if task_path.is_absolute():
            absolute_paths.append(task_text)
            continue

        resolved_path = REPO_ROOT / task_path

        if not resolved_path.is_file():
            missing_paths.append(task_text)
            continue

        gpu_count = read_declared_gpu_count(
            resolved_path
        )
        gpu_counts[gpu_count] += 1

        try:
            load_job_spec(
                str(resolved_path),
                estimator_name="horus",
            )
        except Exception as exc:
            load_failures.append(
                f"row {row_index}: {task_text}: "
                f"{type(exc).__name__}: {exc}"
            )

    if absolute_paths:
        raise ValueError(
            f"{trace_path}: absolute task paths found:\n"
            + "\n".join(absolute_paths)
        )

    if missing_paths:
        raise ValueError(
            f"{trace_path}: missing task files:\n"
            + "\n".join(missing_paths)
        )

    if load_failures:
        raise ValueError(
            f"{trace_path}: JobSpec loading failures:\n"
            + "\n".join(load_failures)
        )

    actual_gpu_counts = dict(
        sorted(gpu_counts.items())
    )

    if actual_gpu_counts != expected_gpu_counts:
        raise ValueError(
            f"{trace_path}: expected GPU counts "
            f"{expected_gpu_counts}, found "
            f"{actual_gpu_counts}"
        )

    return {
        "jobs": len(trace),
        "gpu_counts": actual_gpu_counts,
        "unique_workloads": int(
            trace["task_path"].nunique()
        ),
        "arrival_span_s": float(
            submit_times.iloc[-1]
        ),
    }


def main() -> None:
    for filename, expected_gpu_counts in (
        EXPECTED.items()
    ):
        path = TRACE_DIR / filename

        if not path.is_file():
            raise FileNotFoundError(
                f"Missing trace: {path}"
            )

        result = validate_trace(
            path,
            expected_gpu_counts,
        )

        print(f"\n=== {filename} ===")
        print("jobs:", result["jobs"])
        print("GPU counts:", result["gpu_counts"])
        print(
            "unique workloads:",
            result["unique_workloads"],
        )
        print(
            "arrival span (h):",
            f"{result['arrival_span_s'] / 3600:.2f}",
        )

    print(
        "\nRepresentative trace validation: OK"
    )


if __name__ == "__main__":
    main()
