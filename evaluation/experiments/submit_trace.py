#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import socket
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Submit a trace of task spec files to AEGIS.")
    p.add_argument("--trace-csv", required=True)
    p.add_argument("--host", default=socket.gethostname())
    p.add_argument("--port", type=int, default=5001)
    p.add_argument("--user", default=os.getenv("USER", "unknown"))
    p.add_argument("--workdir", default=str(Path.cwd()))
    p.add_argument("--delay-scale", type=float, default=1.0)
    return p.parse_args()


def send_task(*, host: str, port: int, user: str, workdir: str, task_path: str) -> str:
    task_abs = str(Path(task_path).resolve())
    message = f"{user}+{workdir}+{task_abs}"

    with socket.socket() as s:
        s.connect((host, port))
        s.send(message.encode())
        return s.recv(1024).decode()


def main() -> int:
    args = parse_args()

    with open(args.trace_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    last_submit_s = 0.0

    for i, row in enumerate(rows):
        submit_s = float(row.get("submit_time_s", 0.0))
        sleep_s = max(0.0, submit_s - last_submit_s) * args.delay_scale
        if sleep_s > 0:
            time.sleep(sleep_s)

        task_path = row["task_path"]
        response = send_task(
            host=args.host,
            port=args.port,
            user=args.user,
            workdir=args.workdir,
            task_path=task_path,
        )

        print(f"submitted {i}: {task_path} -> {response}")
        last_submit_s = submit_s

    return 0


if __name__ == "__main__":
    raise SystemExit(main())