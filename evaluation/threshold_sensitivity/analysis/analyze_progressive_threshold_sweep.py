#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Analyze aggregated progressive threshold sweep results."
    )
    p.add_argument("--summary-csv", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--max-slowdown-budget", type=float, default=1.5)
    p.add_argument("--min-completion-fraction", type=float, default=1.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.summary_csv)

    numeric_cols = [
        "admission_fraction",
        "completion_fraction",
        "mean_throughput_gain",
        "median_throughput_gain",
        "mean_slowdown",
        "median_max_slowdown",
        "max_slowdown",
        "p95_slowdown_mean",
        "reject_retry_count",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    feasible = df[
        (df["completion_fraction"] >= float(args.min_completion_fraction))
        & (df["max_slowdown"] <= float(args.max_slowdown_budget))
    ].copy()

    if not feasible.empty:
        feasible["score"] = (
            feasible["mean_throughput_gain"]
            / feasible["max_slowdown"].clip(lower=1.0)
        )
        feasible = feasible.sort_values(
            ["score", "mean_throughput_gain"],
            ascending=[False, False],
        )

    all_ranked = df.copy()
    all_ranked["score"] = (
        all_ranked["mean_throughput_gain"]
        / all_ranked["max_slowdown"].clip(lower=1.0)
    )
    all_ranked = all_ranked.sort_values(
        ["completion_fraction", "score", "mean_throughput_gain"],
        ascending=[False, False, False],
    )

    all_ranked.to_csv(output_dir / "threshold_settings_ranked.csv", index=False)
    feasible.to_csv(output_dir / "threshold_settings_feasible.csv", index=False)

    top_cols = [
        "tau_smact",
        "tau_smocc",
        "tau_drama",
        "num_trials",
        "admission_fraction",
        "completion_fraction",
        "mean_throughput_gain",
        "max_slowdown",
        "p95_slowdown_mean",
        "reject_retry_count",
        "score",
    ]

    print("\nTop ranked settings:")
    print(all_ranked[top_cols].head(20).to_string(index=False))

    print(
        f"\nFeasible settings with max_slowdown <= {args.max_slowdown_budget} "
        f"and completion_fraction >= {args.min_completion_fraction}:"
    )
    if feasible.empty:
        print("None")
    else:
        print(feasible[top_cols].head(20).to_string(index=False))

    print(f"\nwrote {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())