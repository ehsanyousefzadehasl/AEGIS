from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


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


def summarize_events(root: Path) -> Counter:
    counts = Counter()
    for record in iter_event_records(root):
        counts[record.get("event", "unknown")] += 1
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
    counts = summarize_events(root)

    if not counts:
        print("No structured events found.")
        return

    for event_name in sorted(counts):
        print(f"{event_name}: {counts[event_name]}")


if __name__ == "__main__":
    main()