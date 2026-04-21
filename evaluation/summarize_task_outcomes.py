from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


TERMINAL_EVENTS = {"completed", "failed"}


def iter_event_records(root: Path):
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


def summarize_final_task_outcomes(root: Path) -> Counter:
    latest_terminal_by_task: dict[str, tuple[tuple[int, str], str]] = {}

    for seq, record in enumerate(iter_event_records(root)):
        event = record.get("event")
        task_id = record.get("task_id")

        if event not in TERMINAL_EVENTS or not task_id:
            continue

        emitted_at = record.get("emitted_at")
        timestamp = record.get("timestamp")

        if emitted_at:
            order_key = (2, str(emitted_at))
        elif timestamp:
            order_key = (1, str(timestamp))
        else:
            order_key = (0, f"{seq:012d}")

        prev = latest_terminal_by_task.get(str(task_id))
        if prev is None or order_key >= prev[0]:
            latest_terminal_by_task[str(task_id)] = (order_key, str(event))

    counts = Counter()
    for _, event in latest_terminal_by_task.values():
        counts[event] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Root directory to recursively search for events.jsonl files",
    )
    args = parser.parse_args()

    root = Path(args.root)
    counts = summarize_final_task_outcomes(root)

    if not counts:
        print("No terminal task outcomes found.")
        return

    for outcome in sorted(counts):
        print(f"{outcome}: {counts[outcome]}")


if __name__ == "__main__":
    main()