from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path


TERMINAL_EVENTS = {"completed", "failed"}


def iter_event_records(root: Path) -> Iterable[dict]:
    for event_file in root.rglob("events.jsonl"):
        with event_file.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{event_file}:{line_no}: invalid json: {e}") from e
                record["_event_file"] = str(event_file)
                yield record


def parse_event_time(record: dict) -> datetime | None:
    emitted_at = record.get("emitted_at")
    if emitted_at:
        return datetime.fromisoformat(str(emitted_at))

    timestamp = record.get("timestamp")
    if timestamp:
        return datetime.strptime(str(timestamp), "%Y-%m-%d_%H:%M:%S")

    return None


def summarize_task_timings(root: Path) -> list[dict]:
    tasks: dict[str, dict] = {}

    for record in iter_event_records(root):
        task_id = record.get("task_id")
        event = record.get("event")
        ts = parse_event_time(record)

        if not task_id or not event or ts is None:
            continue

        task_id = str(task_id)
        info = tasks.setdefault(
            task_id,
            {
                "task_id": task_id,
                "task_file": record.get("task_file"),
                "submitted_at": None,
                "first_dispatched_at": None,
                "first_launched_at": None,
                "terminal_at": None,
                "terminal_event": None,
            },
        )

        if info["task_file"] is None:
            info["task_file"] = record.get("task_file")

        if event == "submitted":
            if info["submitted_at"] is None or ts < info["submitted_at"]:
                info["submitted_at"] = ts

        elif event == "dispatched":
            if info["first_dispatched_at"] is None or ts < info["first_dispatched_at"]:
                info["first_dispatched_at"] = ts

        elif event == "launched":
            if info["first_launched_at"] is None or ts < info["first_launched_at"]:
                info["first_launched_at"] = ts

        elif event in TERMINAL_EVENTS:
            if info["terminal_at"] is None or ts >= info["terminal_at"]:
                info["terminal_at"] = ts
                info["terminal_event"] = event

    rows = []
    for info in tasks.values():
        submitted_at = info["submitted_at"]
        first_dispatched_at = info["first_dispatched_at"]
        first_launched_at = info["first_launched_at"]
        terminal_at = info["terminal_at"]

        waiting_s = None
        if submitted_at is not None and first_dispatched_at is not None:
            waiting_s = (first_dispatched_at - submitted_at).total_seconds()

        jct_s = None
        if submitted_at is not None and terminal_at is not None:
            jct_s = (terminal_at - submitted_at).total_seconds()

        runtime_s = None
        if first_launched_at is not None and terminal_at is not None:
            runtime_s = (terminal_at - first_launched_at).total_seconds()

        rows.append(
            {
                "task_id": info["task_id"],
                "task_file": info["task_file"],
                "terminal_event": info["terminal_event"],
                "waiting_s": waiting_s,
                "jct_s": jct_s,
                "runtime_s": runtime_s,
            }
        )

    return sorted(rows, key=lambda r: r["task_id"])


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

    for row in rows:
        print(json.dumps(row, sort_keys=True, default=str))


if __name__ == "__main__":
    main()