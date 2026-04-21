from __future__ import annotations

import argparse
import json

from runtime.events import append_jsonl_event


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--record-json", required=True)
    args = parser.parse_args()

    record = json.loads(args.record_json)
    append_jsonl_event(
        event_path=args.event_path,
        record=record,
    )


if __name__ == "__main__":
    main()