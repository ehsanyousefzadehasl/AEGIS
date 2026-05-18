#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Aggregate progressive threshold sweep outputs."
    )
    p.add_argument("--sweep-root", required=True)
    p.add_argument(
        "--output-csv",
        default=None,
        help="Default: <sweep-root>/threshold_sweep_summary.csv",
    )
    return p.parse_args()


def load_metadata(sweep_root: Path) -> dict:
    metadata_path = sweep_root / "sweep_metadata.json"
    if not metadata_path.exists():
        return {}
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    sweep_root = Path(args.sweep_root)
    output_csv = (
        Path(args.output_csv)
        if args.output_csv is not None
        else sweep_root / "threshold_sweep_summary.csv"
    )

    rows = []
    metadata = load_metadata(sweep_root)

    for summary_path in sorted(sweep_root.glob("*/progressive_trial_summary.csv")):
        run_dir = summary_path.parent
        df = pd.read_csv(summary_path)

        if df.empty:
            continue

        observations_path = run_dir / "admission_observations.csv"
        obs = pd.read_csv(observations_path) if observations_path.exists() else pd.DataFrame()

        for _, group in df.groupby(["tau_smact", "tau_smocc", "tau_drama"], dropna=False):
            tau_smact = group["tau_smact"].iloc[0]
            tau_smocc = group["tau_smocc"].iloc[0]
            tau_drama = group["tau_drama"].iloc[0]

            admitted = pd.to_numeric(group["admitted_workload_count"], errors="coerce")
            planned = pd.to_numeric(group["planned_workload_count"], errors="coerce")
            throughput = pd.to_numeric(group["throughput_gain"], errors="coerce")
            max_slowdown = pd.to_numeric(group["max_slowdown"], errors="coerce")
            mean_slowdown = pd.to_numeric(group["mean_slowdown"], errors="coerce")
            p95_slowdown = pd.to_numeric(group["p95_slowdown"], errors="coerce")

            reject_retry_count = 0
            started_count = 0
            finished_count = 0

            if not obs.empty:
                reject_retry_count = int((obs["decision"] == "reject_retry_later").sum())
                started_count = int(obs["candidate_started"].astype(str).str.lower().eq("true").sum())
                finished_count = int(obs["candidate_finished"].astype(str).str.lower().eq("true").sum())

            rows.append(
                {
                    "run_dir": str(run_dir),
                    "tau_smact": tau_smact,
                    "tau_smocc": tau_smocc,
                    "tau_drama": tau_drama,
                    "num_trials": len(group),
                    "planned_workload_count_sum": planned.sum(),
                    "admitted_workload_count_sum": admitted.sum(),
                    "admission_fraction": admitted.sum() / planned.sum() if planned.sum() else "",
                    "reject_retry_count": reject_retry_count,
                    "candidate_started_count": started_count,
                    "candidate_finished_count": finished_count,
                    "completion_fraction": finished_count / started_count if started_count else "",
                    "mean_throughput_gain": throughput.mean(),
                    "median_throughput_gain": throughput.median(),
                    "mean_slowdown": mean_slowdown.mean(),
                    "median_max_slowdown": max_slowdown.median(),
                    "max_slowdown": max_slowdown.max(),
                    "p95_slowdown_mean": p95_slowdown.mean(),
                    "manifest": metadata.get("plan_jsonl", ""),
                    "solo_runtime_csv": metadata.get("solo_runtime_csv", ""),
                }
            )

    out = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False)

    print(f"wrote {output_csv}")
    print(f"rows={len(out)}")

    if not out.empty:
        print(
            out[
                [
                    "tau_smact",
                    "tau_smocc",
                    "tau_drama",
                    "num_trials",
                    "admission_fraction",
                    "completion_fraction",
                    "mean_throughput_gain",
                    "max_slowdown",
                    "reject_retry_count",
                ]
            ].to_string(index=False)
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())