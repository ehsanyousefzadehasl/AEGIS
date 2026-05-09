#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import csv

DEFAULT_OUTPUT_DIR = Path("evaluation/threshold_sensitivity/progressive_threshold_trials")

OBSERVATION_COLUMNS = [
    "trial_id",
    "stage",
    "gpu_id",
    "cuda_visible_devices",
    "running_jobs_before_stage",
    "candidate_job",
    "is_initial_job",
    "decision",
    "decision_reason",
    "smact_risk",
    "smocc_risk",
    "drama_risk",
    "running_job_count_before",
    "running_job_count_after",
    "candidate_started",
    "candidate_finished",
    "candidate_return_code",
    "candidate_runtime_seconds",
    "candidate_solo_runtime_seconds",
    "max_slowdown",
]

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run progressive collocation threshold trials."
    )
    p.add_argument(
        "--plan-jsonl",
        required=True,
        help="JSONL plan produced by plan_progressive_threshold_trials.py.",
    )
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned stages without launching workloads.",
    )
    p.add_argument("--tau-smact", type=float, default=0.80)
    p.add_argument("--tau-smocc", type=float, default=0.45)
    p.add_argument("--tau-drama", type=float, default=0.40)

    p.add_argument("--window-seconds", type=float, default=30.0)
    p.add_argument(
        "--summary-windows",
        default="5,10,20,30,40,60,120,200",
        help="Comma-separated summary windows to collect for each admission point.",
    )

    p.add_argument(
        "--solo-runtime-csv",
        default=None,
        help="Optional CSV with solo runtimes used to compute slowdown.",
    )

    return p.parse_args()


def read_plan(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def describe_trial(trial: dict) -> list[dict]:
    jobs = trial["job_sequence"]
    stages = []

    for stage_idx, candidate in enumerate(jobs, start=1):
        running_jobs = jobs[: stage_idx - 1]

        stages.append(
            {
                "trial_id": trial["trial_id"],
                "stage": stage_idx,
                "gpu_id": trial["gpu_id"],
                "cuda_visible_devices": trial["cuda_visible_devices"],
                "running_jobs_before_stage": running_jobs,
                "candidate_job": candidate,
                "is_initial_job": stage_idx == 1,
            }
        )

    return stages

def initialize_observations_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OBSERVATION_COLUMNS)
        writer.writeheader()


def dry_run_observation(stage: dict) -> dict:
    running_jobs = stage["running_jobs_before_stage"]
    return {
        "trial_id": stage["trial_id"],
        "stage": stage["stage"],
        "gpu_id": stage["gpu_id"],
        "cuda_visible_devices": stage["cuda_visible_devices"],
        "running_jobs_before_stage": ";".join(running_jobs),
        "candidate_job": stage["candidate_job"],
        "is_initial_job": stage["is_initial_job"],
        "decision": "dry_run",
        "decision_reason": "planned_only",
        "smact_risk": "",
        "smocc_risk": "",
        "drama_risk": "",
        "running_job_count_before": len(running_jobs),
        "running_job_count_after": len(running_jobs),
        "candidate_started": False,
        "candidate_finished": False,
        "candidate_return_code": "",
        "candidate_runtime_seconds": "",
        "candidate_solo_runtime_seconds": "",
        "max_slowdown": "",
    }


def append_observations(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OBSERVATION_COLUMNS)
        for row in rows:
            writer.writerow(row)

def should_reject_gpu(
    *,
    smact_risk: float,
    smocc_risk: float,
    drama_risk: float,
    tau_smact: float,
    tau_smocc: float,
    tau_drama: float,
) -> bool:
    return (
        smact_risk >= tau_smact
        and (
            smocc_risk >= tau_smocc
            or drama_risk >= tau_drama
        )
    )

def parse_summary_windows(text: str) -> list[float]:
    windows = []
    for item in str(text).split(","):
        item = item.strip()
        if item:
            windows.append(float(item))
    return windows

def normalize_spec_path(path: str) -> str:
    return str(Path(path)).strip()


def load_solo_runtime_lookup(path: str | None) -> dict[str, float]:
    if path is None:
        return {}

    import pandas as pd

    df = pd.read_csv(path)
    candidates = [
        "task_path",
        "spec_path",
        "job_spec",
        "workload_spec",
    ]
    path_col = next((c for c in candidates if c in df.columns), None)

    runtime_candidates = [
        "total_runtime_seconds",
        "end_to_end_time_s",
        "end_to_end_time_seconds",
        "training_loop_time_s",
        "runtime_seconds",
    ]
    runtime_col = next((c for c in runtime_candidates if c in df.columns), None)

    if path_col is None or runtime_col is None:
        raise ValueError(
            f"Could not find spec/runtime columns in {path}. "
            f"Columns={list(df.columns)}"
        )

    lookup: dict[str, float] = {}
    for _, row in df.iterrows():
        spec = normalize_spec_path(str(row[path_col]))
        try:
            runtime = float(row[runtime_col])
        except Exception:
            continue
        lookup[spec] = runtime
        lookup[Path(spec).name] = runtime
        lookup[Path(spec).stem] = runtime

    return lookup


def lookup_solo_runtime(
    lookup: dict[str, float],
    spec_path: str,
) -> float | None:
    keys = [
        normalize_spec_path(spec_path),
        Path(spec_path).name,
        Path(spec_path).stem,
    ]
    for key in keys:
        if key in lookup:
            return lookup[key]
    return None


def main() -> int:
    args = parse_args()

    plan_path = Path(args.plan_jsonl)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trials = read_plan(plan_path)

    solo_runtime_lookup = load_solo_runtime_lookup(args.solo_runtime_csv)

    metadata = {
        "plan_jsonl": str(plan_path),
        "tau_smact": args.tau_smact,
        "tau_smocc": args.tau_smocc,
        "tau_drama": args.tau_drama,
        "rule": "reject if smact_risk >= tau_smact and (smocc_risk >= tau_smocc or drama_risk >= tau_drama)",
        "window_seconds": args.window_seconds,
        "summary_windows": parse_summary_windows(args.summary_windows),
        "solo_runtime_csv": args.solo_runtime_csv,
        "solo_runtime_entries": len(solo_runtime_lookup),
    }

    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"wrote {metadata_path}")


    all_stages = []
    for trial in trials:
        all_stages.extend(describe_trial(trial))

    stage_plan_path = output_dir / "progressive_stage_plan.jsonl"

    observations_csv = output_dir / "admission_observations.csv"
    initialize_observations_csv(observations_csv)

    if args.dry_run:
        append_observations(
            observations_csv,
            [dry_run_observation(stage) for stage in all_stages],
        )
        print(f"wrote {observations_csv}")

    with stage_plan_path.open("w", encoding="utf-8") as f:
        for stage in all_stages:
            f.write(json.dumps(stage, sort_keys=True) + "\n")

    print(f"trials={len(trials)}")
    print(f"stages={len(all_stages)}")
    print(f"wrote {stage_plan_path}")

    if args.dry_run:
        print("\nDRY RUN: planned stages")
        for stage in all_stages:
            running = stage["running_jobs_before_stage"]
            running_text = ", ".join(Path(x).stem for x in running) if running else "<none>"
            candidate = Path(stage["candidate_job"]).stem
            print(
                f"[{stage['trial_id']} stage={stage['stage']}] "
                f"running={running_text} -> candidate={candidate} "
                f"gpu_id={stage['gpu_id']} visible={stage['cuda_visible_devices']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())