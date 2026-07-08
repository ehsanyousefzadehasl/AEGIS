#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import subprocess
import time
from pathlib import Path

import yaml


def load_command(spec_path: Path) -> str:
    spec = yaml.safe_load(spec_path.read_text())
    return spec["job"]["command"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--gpu-id", default="0")
    parser.add_argument("--spec", action="append", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = [Path(s) for s in args.spec]
    rows = []

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)

    procs = []

    global_start = time.time()

    for idx, spec_path in enumerate(specs):
        command = load_command(spec_path)
        log_path = output_dir / f"job_{idx:02d}_{spec_path.stem}.log"

        log_f = log_path.open("w")
        start_time = time.time()

        print(f"[launch] {idx}: {spec_path.name}", flush=True)
        print(f"         {command}", flush=True)

        proc = subprocess.Popen(
            shlex.split(command),
            cwd=Path.cwd(),
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            text=True,
        )

        procs.append({
            "idx": idx,
            "spec_path": str(spec_path),
            "spec_name": spec_path.name,
            "command": command,
            "process": proc,
            "log_file": log_f,
            "log_path": str(log_path),
            "start_time": start_time,
        })

    for item in procs:
        proc = item["process"]
        return_code = proc.wait()
        end_time = time.time()
        item["log_file"].close()

        rows.append({
            "idx": item["idx"],
            "spec_name": item["spec_name"],
            "spec_path": item["spec_path"],
            "command": item["command"],
            "return_code": return_code,
            "start_time": item["start_time"],
            "end_time": end_time,
            "elapsed_seconds": end_time - item["start_time"],
            "log_path": item["log_path"],
        })

        print(
            f"[done] {item['idx']}: {item['spec_name']} "
            f"return_code={return_code} elapsed={end_time - item['start_time']:.2f}s",
            flush=True,
        )

    global_end = time.time()

    summary = {
        "gpu_id": args.gpu_id,
        "num_jobs": len(specs),
        "global_start_time": global_start,
        "global_end_time": global_end,
        "makespan_seconds": global_end - global_start,
        "specs": [str(p) for p in specs],
    }

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    with (output_dir / "jobs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print()
    print("[summary]")
    print(json.dumps(summary, indent=2))
    print(f"wrote {output_dir / 'jobs.csv'}")
    print(f"wrote {output_dir / 'summary.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
