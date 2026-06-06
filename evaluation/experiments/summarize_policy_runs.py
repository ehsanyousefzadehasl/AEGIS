#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from datetime import datetime
import pandas as pd

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize AEGIS policy experiment runs."
    )
    parser.add_argument(
        "--experiment-root",
        type=Path,
        required=True,
        help="Experiment directory containing timestamp/policy run folders.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory; defaults to <experiment-root>/analysis.",
    )
    return parser.parse_args()


def discover_run_dirs(experiment_root: Path) -> list[Path]:
    return sorted(
        metadata_path.parent
        for metadata_path in experiment_root.glob("*/*/metadata.json")
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_events(run_dir: Path) -> Iterable[dict]:
    event_files = sorted((run_dir / "runtime").glob("events-*.jsonl"))

    for event_file in event_files:
        with event_file.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"{event_file}:{line_number}: invalid JSON"
                    ) from exc


def parse_event_time(record: dict) -> datetime | None:
    emitted_at = record.get("emitted_at")
    if emitted_at:
        return datetime.fromisoformat(str(emitted_at))

    timestamp = record.get("timestamp")
    if timestamp:
        return datetime.strptime(str(timestamp), "%Y-%m-%d_%H:%M:%S")

    return None

def summarize_attempts(
    *,
    run_dir: Path,
    metadata: dict,
    events: list[dict],
) -> list[dict]:
    events_by_task: dict[str, list[tuple[datetime, dict]]] = {}

    for event in events:
        task_id = event.get("task_id")
        event_time = parse_event_time(event)

        if not task_id or event_time is None:
            continue

        events_by_task.setdefault(str(task_id), []).append(
            (event_time, event)
        )

    rows: list[dict] = []

    for task_id, task_events in events_by_task.items():
        task_events.sort(key=lambda item: item[0])

        pending_dispatches: list[tuple[datetime, dict]] = []
        active_attempt: dict | None = None
        previous_failure_at: datetime | None = None
        attempt_number = 0

        for event_time, event in task_events:
            event_name = event.get("event")

            if event_name == "dispatched":
                pending_dispatches.append((event_time, event))
                continue

            if event_name == "launched":
                attempt_number += 1

                dispatch_time = None
                dispatch_event = {}

                if pending_dispatches:
                    dispatch_time, dispatch_event = pending_dispatches.pop(0)

                recovery_queue_wait_s = None
                if (
                    previous_failure_at is not None
                    and dispatch_time is not None
                ):
                    recovery_queue_wait_s = (
                        dispatch_time - previous_failure_at
                    ).total_seconds()

                dispatch_to_launch_s = None
                if dispatch_time is not None:
                    dispatch_to_launch_s = (
                        event_time - dispatch_time
                    ).total_seconds()

                recovery_gap_s = None
                if previous_failure_at is not None:
                    recovery_gap_s = (
                        event_time - previous_failure_at
                    ).total_seconds()

                active_attempt = {
                    "experiment_name": metadata.get("experiment_name"),
                    "run_label": metadata.get("run_label", run_dir.name),
                    "policy": metadata.get("policy"),
                    "estimator": metadata.get("estimator"),
                    "trace_csv": metadata.get("trace_csv"),
                    "run_dir": str(run_dir),
                    "task_id": task_id,
                    "task_file": (
                        event.get("task_file")
                        or event.get("task")
                        or dispatch_event.get("task_file")
                        or dispatch_event.get("task")
                    ),
                    "attempt_number": attempt_number,
                    "recovered": bool(
                        dispatch_event.get("recovered", False)
                    ),
                    "recovery_count": int(
                        dispatch_event.get("recovery_count", 0) or 0
                    ),
                    "dispatch_at": dispatch_time,
                    "launch_at": event_time,
                    "terminal_at": None,
                    "terminal_event": None,
                    "attempt_runtime_s": None,
                    "recovery_queue_wait_s": recovery_queue_wait_s,
                    "dispatch_to_launch_s": dispatch_to_launch_s,
                    "recovery_gap_s": recovery_gap_s,
                    "assigned_gpu_ids": event.get(
                        "assigned_gpu_ids",
                        dispatch_event.get("assigned_gpu_ids"),
                    ),
                }
                continue

            if event_name in {"failed", "completed"}:
                if active_attempt is None:
                    continue

                active_attempt["terminal_at"] = event_time
                active_attempt["terminal_event"] = event_name
                active_attempt["attempt_runtime_s"] = (
                    event_time - active_attempt["launch_at"]
                ).total_seconds()

                rows.append(active_attempt)

                if event_name == "failed":
                    previous_failure_at = event_time
                else:
                    previous_failure_at = None

                active_attempt = None

        # Preserve an unfinished launched attempt for debugging.
        if active_attempt is not None:
            rows.append(active_attempt)

    return rows


def summarize_jobs(
    *,
    run_dir: Path,
    metadata: dict,
    events: list[dict],
    attempts: list[dict],
) -> list[dict]:
    tasks: dict[str, dict] = {}

    for event in events:
        task_id = event.get("task_id")
        event_name = event.get("event")
        event_time = parse_event_time(event)

        if not task_id or not event_name or event_time is None:
            continue

        task_id = str(task_id)
        task = tasks.setdefault(
            task_id,
            {
                "task_id": task_id,
                "task_file": None,
                "submitted": [],
                "dispatched": [],
                "launched": [],
                "failed": [],
                "completed": [],
                "recovery_stopped": [],
                "recovered_dispatches": [],
                "recovery_counts": [],
            },
        )

        task_file = event.get("task_file") or event.get("task")
        if task["task_file"] is None and task_file:
            task["task_file"] = str(task_file)

        if event_name in {
            "submitted",
            "dispatched",
            "launched",
            "failed",
            "completed",
            "recovery_stopped",
        }:
            task[event_name].append(event_time)

        if event_name == "dispatched":
            if bool(event.get("recovered", False)):
                task["recovered_dispatches"].append(event_time)

            recovery_count = event.get("recovery_count")
            if recovery_count is not None:
                task["recovery_counts"].append(int(recovery_count))

    rows = []

    for task in tasks.values():
        submitted_at = min(task["submitted"]) if task["submitted"] else None
        first_dispatched_at = (
            min(task["dispatched"]) if task["dispatched"] else None
        )
        first_launched_at = min(task["launched"]) if task["launched"] else None
        completed_at = max(task["completed"]) if task["completed"] else None

        final_successful_launch_at = None
        if completed_at is not None:
            eligible_launches = [
                ts for ts in task["launched"] if ts <= completed_at
            ]
            if eligible_launches:
                final_successful_launch_at = max(eligible_launches)

        waiting_s = None
        if submitted_at is not None and first_dispatched_at is not None:
            waiting_s = (
                first_dispatched_at - submitted_at
            ).total_seconds()

        jct_s = None
        if submitted_at is not None and completed_at is not None:
            jct_s = (completed_at - submitted_at).total_seconds()

        execution_span_s = None
        if first_launched_at is not None and completed_at is not None:
            execution_span_s = (
                completed_at - first_launched_at
            ).total_seconds()

        task_attempts = sorted(
            [
                attempt
                for attempt in attempts
                if attempt["task_id"] == task["task_id"]
            ],
            key=lambda attempt: attempt["attempt_number"],
        )

        completed_attempts = [
            attempt
            for attempt in task_attempts
            if attempt["terminal_event"] == "completed"
        ]
        failed_attempts = [
            attempt
            for attempt in task_attempts
            if attempt["terminal_event"] == "failed"
        ]

        successful_attempt = (
            completed_attempts[-1] if completed_attempts else None
        )

        successful_attempt_runtime_s = (
            successful_attempt["attempt_runtime_s"]
            if successful_attempt is not None
            else None
        )

        attempt_runtimes = [
            float(attempt["attempt_runtime_s"])
            for attempt in task_attempts
            if attempt["attempt_runtime_s"] is not None
        ]
        recovery_queue_waits = [
            float(attempt["recovery_queue_wait_s"])
            for attempt in task_attempts
            if attempt["recovery_queue_wait_s"] is not None
        ]
        recovery_gaps = [
            float(attempt["recovery_gap_s"])
            for attempt in task_attempts
            if attempt["recovery_gap_s"] is not None
        ]


        rows.append(
            {
                "experiment_name": metadata.get("experiment_name"),
                "run_label": metadata.get("run_label", run_dir.name),
                "policy": metadata.get("policy"),
                "estimator": metadata.get("estimator"),
                "trace_csv": metadata.get("trace_csv"),
                "run_dir": str(run_dir),
                "task_id": task["task_id"],
                "task_file": task["task_file"],
                "submitted_at": submitted_at,
                "first_dispatched_at": first_dispatched_at,
                "first_launched_at": first_launched_at,
                "final_successful_launch_at": final_successful_launch_at,
                "completed_at": completed_at,
                "initial_queue_wait_s": waiting_s,
                "jct_s": jct_s,
                "execution_span_s": execution_span_s,
                "successful_attempt_runtime_s": successful_attempt_runtime_s,
                "dispatch_count": len(task["dispatched"]),
                "launch_count": len(task["launched"]),
                "recovered_dispatch_count": len(
                    task["recovered_dispatches"]
                ),
                "maximum_recovery_count": max(
                    task["recovery_counts"],
                    default=0,
                ),
                "recovery_stopped_count": len(task["recovery_stopped"]),
                "completed_successfully": completed_at is not None,
                "attempt_count": len(task_attempts),
                "failed_attempt_count": len(failed_attempts),
                "recovered_attempt_count": sum(
                    bool(attempt["recovered"])
                    for attempt in task_attempts
                ),
                "total_attempt_runtime_s": sum(attempt_runtimes),
                "failed_attempt_runtime_s": sum(
                    float(attempt["attempt_runtime_s"])
                    for attempt in failed_attempts
                    if attempt["attempt_runtime_s"] is not None
                ),
                "total_recovery_queue_wait_s": sum(recovery_queue_waits),
                "max_recovery_queue_wait_s": (
                    max(recovery_queue_waits)
                    if recovery_queue_waits
                    else 0.0
                ),
                "total_recovery_gap_s": sum(recovery_gaps),
                "max_recovery_gap_s": (
                    max(recovery_gaps)
                    if recovery_gaps
                    else 0.0
                ),
            }
        )

    return rows


def main() -> int:
    args = parse_args()

    experiment_root = args.experiment_root.resolve()
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else experiment_root / "analysis"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = discover_run_dirs(experiment_root)

    print(f"Discovered {len(run_dirs)} policy runs")

    attempt_rows = []
    job_rows = []

    for run_dir in run_dirs:
        metadata = load_json(run_dir / "metadata.json")
        events = list(iter_events(run_dir))

        run_attempt_rows = summarize_attempts(
            run_dir=run_dir,
            metadata=metadata,
            events=events,
        )
        attempt_rows.extend(run_attempt_rows)

        rows = summarize_jobs(
            run_dir=run_dir,
            metadata=metadata,
            events=events,
            attempts=run_attempt_rows,
        )
        job_rows.extend(rows)

        print(
            metadata.get("run_label", run_dir.name),
            f"events={len(events)}",
            f"jobs={len(rows)}",
        )

    job_df = pd.DataFrame(job_rows)
    job_output = output_dir / "job_metrics.csv"
    job_df.to_csv(job_output, index=False)

    print(f"Wrote {len(job_df)} job rows to {job_output}")

    attempt_df = pd.DataFrame(attempt_rows)
    attempt_output = output_dir / "attempt_metrics.csv"
    attempt_df.to_csv(attempt_output, index=False)

    print(
        f"Wrote {len(attempt_df)} attempt rows to "
        f"{attempt_output}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())