#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path("evaluation/threshold_sensitivity/progressive_threshold_trials")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validate and materialize progressive collocation threshold trial manifests."
    )
    p.add_argument("--manifest-csv", required=True)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return p.parse_args()


def split_job_sequence(text: str) -> list[str]:
    return [item.strip() for item in str(text).split(";") if item.strip()]


def read_manifest(path: Path) -> list[dict]:
    rows: list[dict] = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        required = {"trial_id", "gpu_id", "cuda_visible_devices", "job_sequence"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest missing required columns: {sorted(missing)}")

        for row in reader:
            trial_id = str(row["trial_id"]).strip()
            gpu_id = str(row["gpu_id"]).strip()
            cuda_visible_devices = str(row["cuda_visible_devices"]).strip()
            jobs = split_job_sequence(row["job_sequence"])

            if not trial_id:
                raise ValueError("Empty trial_id")
            if not gpu_id:
                raise ValueError(f"Trial {trial_id}: empty gpu_id")
            if not cuda_visible_devices:
                raise ValueError(f"Trial {trial_id}: empty cuda_visible_devices")
            if len(jobs) < 2:
                raise ValueError(
                    f"Trial {trial_id}: job_sequence must contain at least two specs"
                )

            missing_specs = [job for job in jobs if not Path(job).exists()]
            if missing_specs:
                raise FileNotFoundError(
                    f"Trial {trial_id}: missing spec files: {missing_specs}"
                )

            rows.append(
                {
                    "trial_id": trial_id,
                    "gpu_id": gpu_id,
                    "cuda_visible_devices": cuda_visible_devices,
                    "job_sequence": jobs,
                    "num_stages": len(jobs),
                }
            )

    return rows


def write_plan(rows: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_json = output_dir / "progressive_trial_plan.json"
    plan_jsonl = output_dir / "progressive_trial_plan.jsonl"

    plan_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    with plan_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    print(f"validated_trials={len(rows)}")
    print(f"wrote {plan_json}")
    print(f"wrote {plan_jsonl}")


def main() -> int:
    args = parse_args()

    manifest = Path(args.manifest_csv)
    output_dir = Path(args.output_dir)

    rows = read_manifest(manifest)
    write_plan(rows, output_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())