#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path


def _read_events(event_path: str) -> list[dict]:
    path = Path(event_path)
    if not path.exists():
        return []

    events = []
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def wait_for_eval_completion(
    *,
    event_path: str,
    expected_tasks: int,
    idle_exit_minutes: float,
    poll_s: float = 5.0,
) -> None:
    idle_started_at = None

    while True:
        events = _read_events(event_path)

        submitted = {
            str(e.get("task_id"))
            for e in events
            if e.get("event") == "submitted"
        }

        completed = {
            str(e.get("task_id"))
            for e in events
            if e.get("event") == "completed"
        }

        failed = {
            str(e.get("task_id"))
            for e in events
            if e.get("event") == "failed"
        }


        done = len(submitted) >= expected_tasks and len(completed) >= expected_tasks

        if done:
            if idle_started_at is None:
                idle_started_at = time.time()

            idle_s = time.time() - idle_started_at
            if idle_s >= idle_exit_minutes * 60.0:
                print(
                    "[eval] expected tasks reached; exiting "
                    f"submitted={len(submitted)} completed={len(completed)} failed={len(failed)}"
                )
                os._exit(0)
        else:
            idle_started_at = None

        time.sleep(poll_s)