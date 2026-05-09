#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path("evaluation/threshold_sensitivity/progressive_threshold_trials")


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


def main() -> int:
    args = parse_args()

    plan_path = Path(args.plan_jsonl)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trials = read_plan(plan_path)

    all_stages = []
    for trial in trials:
        all_stages.extend(describe_trial(trial))

    stage_plan_path = output_dir / "progressive_stage_plan.jsonl"
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