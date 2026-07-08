#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List


JOBS = {
    "resnet50_bs128_960": {
        "spec_name": "resnet50_imagenet_bs128_maxbatches960.yaml",
        "label": "ResNet50-bs128",
        "cmd": [
            "python",
            "evaluation/workloads/training/scripts/clean/resnet50_imagenet_train.py",
            "--max_batches",
            "960",
            "--batch_size",
            "128",
        ],
    },
    "vgg16_bs64_1200": {
        "spec_name": "vgg16_imagenet_bs64_maxbatches1200.yaml",
        "label": "VGG16-bs64",
        "cmd": [
            "python",
            "evaluation/workloads/training/scripts/clean/vgg16_imagenet_train.py",
            "--batch_size",
            "64",
            "--max_batches",
            "1200",
        ],
    },
    "xception_bs64_1200": {
        "spec_name": "xception_imagenet_bs64_maxbatches1200.yaml",
        "label": "Xception-bs64",
        "cmd": [
            "python",
            "evaluation/workloads/training/scripts/clean/xception_imagenet_train.py",
            "--max_batches",
            "1200",
            "--batch_size",
            "64",
        ],
    },
    "resnet50_bs32_3200": {
        "spec_name": "resnet50_imagenet_bs32_maxbatches3200.yaml",
        "label": "ResNet50-bs32",
        "cmd": [
            "python",
            "evaluation/workloads/training/scripts/clean/resnet50_imagenet_train.py",
            "--max_batches",
            "3200",
            "--batch_size",
            "32",
        ],
    },
}


CASES = {
    "mix2": ["resnet50_bs128_960", "vgg16_bs64_1200"],
    "mix3": ["resnet50_bs128_960", "vgg16_bs64_1200", "xception_bs64_1200"],
    "mix4": [
        "resnet50_bs128_960",
        "vgg16_bs64_1200",
        "xception_bs64_1200",
        "resnet50_bs32_3200",
    ],
}


def now_tag() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def command_string(cmd: List[str]) -> str:
    return " ".join(cmd)


def monitor_gpu(gpu: str, out_csv: Path, stop_event: threading.Event, interval_s: float) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp_s",
        "rel_s",
        "gpu",
        "memory_used_mib",
        "gpu_util_percent",
        "memory_util_percent",
    ]
    start = time.time()

    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        while not stop_event.is_set():
            t = time.time()
            try:
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        f"--id={gpu}",
                        "--query-gpu=memory.used,utilization.gpu,utilization.memory",
                        "--format=csv,noheader,nounits",
                    ],
                    check=False,
                    text=True,
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    parts = [x.strip() for x in result.stdout.strip().splitlines()[0].split(",")]
                    mem, gpu_util, mem_util = parts[:3]
                else:
                    mem = gpu_util = mem_util = ""
            except Exception:
                mem = gpu_util = mem_util = ""

            writer.writerow(
                {
                    "timestamp_s": f"{t:.6f}",
                    "rel_s": f"{t - start:.6f}",
                    "gpu": gpu,
                    "memory_used_mib": mem,
                    "gpu_util_percent": gpu_util,
                    "memory_util_percent": mem_util,
                }
            )
            f.flush()
            stop_event.wait(interval_s)


def launch_job(job_key: str, mode_dir: Path, gpu: str, idx: int) -> Dict:
    job = JOBS[job_key]
    log_path = mode_dir / f"job_{idx:02d}_{job_key}.log"

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    env["PYTHONUNBUFFERED"] = "1"

    log_f = log_path.open("w")
    start = time.time()
    proc = subprocess.Popen(
        job["cmd"],
        stdout=log_f,
        stderr=subprocess.STDOUT,
        env=env,
    )

    return {
        "idx": idx,
        "job_key": job_key,
        "label": job["label"],
        "spec_name": job["spec_name"],
        "command": command_string(job["cmd"]),
        "process": proc,
        "log_file_handle": log_f,
        "log_path": str(log_path),
        "start_time": start,
    }


def finish_job(record: Dict) -> Dict:
    proc = record.pop("process")
    log_f = record.pop("log_file_handle")
    return_code = proc.wait()
    end = time.time()
    log_f.close()

    record["end_time"] = end
    record["elapsed_seconds"] = end - record["start_time"]
    record["return_code"] = return_code
    return record


def write_jobs_csv(path: Path, rows: List[Dict]) -> None:
    fields = [
        "idx",
        "job_key",
        "label",
        "spec_name",
        "command",
        "return_code",
        "start_time",
        "end_time",
        "elapsed_seconds",
        "log_path",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def run_serial(case_name: str, job_keys: List[str], run_dir: Path, gpu: str, monitor_interval_s: float) -> List[Dict]:
    mode_dir = run_dir / case_name / "serial"
    mode_dir.mkdir(parents=True, exist_ok=True)

    stop = threading.Event()
    mon = threading.Thread(
        target=monitor_gpu,
        args=(gpu, mode_dir / "gpu_samples.csv", stop, monitor_interval_s),
        daemon=True,
    )
    mon.start()

    rows = []
    try:
        for idx, job_key in enumerate(job_keys):
            rec = launch_job(job_key, mode_dir, gpu, idx)
            rows.append(finish_job(rec))
    finally:
        stop.set()
        mon.join(timeout=5)

    write_jobs_csv(mode_dir / "jobs.csv", rows)
    return rows


def run_collocated(case_name: str, job_keys: List[str], run_dir: Path, gpu: str, monitor_interval_s: float) -> List[Dict]:
    mode_dir = run_dir / case_name / "collocated"
    mode_dir.mkdir(parents=True, exist_ok=True)

    stop = threading.Event()
    mon = threading.Thread(
        target=monitor_gpu,
        args=(gpu, mode_dir / "gpu_samples.csv", stop, monitor_interval_s),
        daemon=True,
    )
    mon.start()

    active = []
    try:
        for idx, job_key in enumerate(job_keys):
            active.append(launch_job(job_key, mode_dir, gpu, idx))
        rows = [finish_job(rec) for rec in active]
    finally:
        stop.set()
        mon.join(timeout=5)

    rows = sorted(rows, key=lambda r: r["idx"])
    write_jobs_csv(mode_dir / "jobs.csv", rows)
    return rows


def makespan(rows: List[Dict]) -> float:
    return max(r["end_time"] for r in rows) - min(r["start_time"] for r in rows)


def summarize_case(case_name: str, job_keys: List[str], serial_rows: List[Dict], colloc_rows: List[Dict], run_dir: Path) -> Dict:
    serial_by_key = {r["job_key"]: r for r in serial_rows}
    colloc_by_key = {r["job_key"]: r for r in colloc_rows}

    serial_makespan = makespan(serial_rows)
    colloc_makespan = makespan(colloc_rows)

    per_job = []
    slowdowns = []
    for job_key in job_keys:
        s = serial_by_key[job_key]["elapsed_seconds"]
        c = colloc_by_key[job_key]["elapsed_seconds"]
        slowdown = c / s if s > 0 else float("nan")
        slowdowns.append(slowdown)
        per_job.append(
            {
                "job_key": job_key,
                "label": JOBS[job_key]["label"],
                "serial_seconds": s,
                "collocated_seconds": c,
                "slowdown": slowdown,
                "serial_return_code": serial_by_key[job_key]["return_code"],
                "collocated_return_code": colloc_by_key[job_key]["return_code"],
            }
        )

    summary = {
        "case": case_name,
        "num_jobs": len(job_keys),
        "workload_mix": " + ".join(JOBS[k]["label"] for k in job_keys),
        "serial_makespan_seconds": serial_makespan,
        "collocated_makespan_seconds": colloc_makespan,
        "throughput_gain": serial_makespan / colloc_makespan if colloc_makespan > 0 else float("nan"),
        "mean_slowdown": sum(slowdowns) / len(slowdowns),
        "max_slowdown": max(slowdowns),
        "per_job": per_job,
    }

    out_dir = run_dir / case_name
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    with (out_dir / "per_job_summary.csv").open("w", newline="") as f:
        fields = [
            "job_key",
            "label",
            "serial_seconds",
            "collocated_seconds",
            "slowdown",
            "serial_return_code",
            "collocated_return_code",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in per_job:
            writer.writerow(row)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, help="Physical GPU id to use, e.g., 0")
    parser.add_argument(
        "--output-root",
        default="evaluation/threshold_sensitivity/results/motivation_unmanaged_collocation_v1",
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--monitor-interval-s", type=float, default=1.0)
    args = parser.parse_args()

    output_root = Path(args.output_root)
    run_dir = output_root / now_tag()
    run_dir.mkdir(parents=True, exist_ok=False)

    all_summaries = []

    for rep in range(args.repeats):
        rep_dir = run_dir / f"rep{rep + 1:02d}"
        rep_dir.mkdir(parents=True, exist_ok=True)

        for case_name, job_keys in CASES.items():
            print(f"=== rep {rep + 1}/{args.repeats}: {case_name} serial ===", flush=True)
            serial_rows = run_serial(case_name, job_keys, rep_dir, args.gpu, args.monitor_interval_s)

            print(f"=== rep {rep + 1}/{args.repeats}: {case_name} collocated ===", flush=True)
            colloc_rows = run_collocated(case_name, job_keys, rep_dir, args.gpu, args.monitor_interval_s)

            summary = summarize_case(case_name, job_keys, serial_rows, colloc_rows, rep_dir)
            summary["rep"] = rep + 1
            all_summaries.append(summary)

            print(
                f"{case_name}: gain={summary['throughput_gain']:.2f}x, "
                f"mean_slowdown={summary['mean_slowdown']:.2f}x, "
                f"max_slowdown={summary['max_slowdown']:.2f}x",
                flush=True,
            )

    with (run_dir / "aggregate_summary.csv").open("w", newline="") as f:
        fields = [
            "rep",
            "case",
            "num_jobs",
            "workload_mix",
            "serial_makespan_seconds",
            "collocated_makespan_seconds",
            "throughput_gain",
            "mean_slowdown",
            "max_slowdown",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in all_summaries:
            writer.writerow({k: s.get(k, "") for k in fields})

    with (run_dir / "metadata.json").open("w") as f:
        json.dump(
            {
                "gpu": args.gpu,
                "repeats": args.repeats,
                "cases": CASES,
                "jobs": JOBS,
                "created_at": now_tag(),
            },
            f,
            indent=2,
        )

    print(f"\nWrote: {run_dir}")
    print("Compact summary:")
    for s in all_summaries:
        print(
            f"{s['case']} | jobs={s['num_jobs']} | "
            f"gain={s['throughput_gain']:.2f}x | "
            f"mean_slowdown={s['mean_slowdown']:.2f}x | "
            f"max_slowdown={s['max_slowdown']:.2f}x"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
