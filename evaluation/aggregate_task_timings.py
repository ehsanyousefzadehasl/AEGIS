from __future__ import annotations

import argparse
from pathlib import Path

try:
    from evaluation.summarize_task_timings import summarize_task_timings
except ModuleNotFoundError:
    from summarize_task_timings import summarize_task_timings


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]

    rank = (len(values) - 1) * p
    lo = int(rank)
    hi = min(lo + 1, len(values) - 1)
    frac = rank - lo
    return values[lo] * (1 - frac) + values[hi] * frac


def fmt(value: float | None) -> str:
    return "NA" if value is None else f"{value:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Root directory to recursively search for events.jsonl files",
    )
    args = parser.parse_args()

    rows = summarize_task_timings(Path(args.root))
    if not rows:
        print("No task timing records found.")
        return

    completed = [r for r in rows if r["terminal_event"] == "completed"]
    failed = [r for r in rows if r["terminal_event"] == "failed"]
    terminal = [r for r in rows if r["terminal_event"] in {"completed", "failed"}]

    waiting = [r["waiting_s"] for r in rows if r["waiting_s"] is not None]
    jct = [r["jct_s"] for r in terminal if r["jct_s"] is not None]
    runtime = [r["runtime_s"] for r in terminal if r["runtime_s"] is not None]

    completion_ratio = None
    if terminal:
        completion_ratio = len(completed) / len(terminal)

    print(f"tasks_total: {len(rows)}")
    print(f"tasks_terminal: {len(terminal)}")
    print(f"tasks_completed: {len(completed)}")
    print(f"tasks_failed: {len(failed)}")
    print(f"completion_ratio: {fmt(completion_ratio)}")
    print(f"avg_waiting_s: {fmt(mean(waiting))}")
    print(f"avg_jct_s: {fmt(mean(jct))}")
    print(f"p95_jct_s: {fmt(percentile(jct, 0.95))}")
    print(f"avg_runtime_s: {fmt(mean(runtime))}")


if __name__ == "__main__":
    main()