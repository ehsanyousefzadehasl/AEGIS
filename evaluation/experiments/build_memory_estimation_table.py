#!/usr/bin/env python3
"""Build the paper table for memory-feasibility strategy effects.

The script reads the output of analyze_evaluation_manifest.py and produces:
  - a CSV table for inspection,
  - a LaTeX table for the paper,
  - a Markdown report snippet.

It intentionally uses paper-facing memory-mode names while preserving raw
run labels in the analysis inputs.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd


MEMORY_MODE_NAMES = {
    "OR-MAGM": "Estimator-free",
    "oracle-MAGM": "PeakMem",
    "EST-MAGM__horus": "HorusMem",
    "EST-MAGM__faketensor": "FakeTensor",
    "EST-MAGM__gpumemnet": "GPUMemNet",
}

MEMORY_MODE_ORDER = {
    "Estimator-free": 0,
    "PeakMem": 1,
    "HorusMem": 2,
    "FakeTensor": 3,
    "GPUMemNet": 4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a paper-ready memory-estimation/recovery table from "
            "final representative evaluation analysis outputs."
        )
    )
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=Path(
            "evaluation/experiments/results/"
            "final_representative_evaluation_analysis"
        ),
        help=(
            "Directory produced by analyze_evaluation_manifest.py. "
            "Default: final_representative_evaluation_analysis."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory for generated artifacts. Defaults to "
            "<analysis-dir>/paper_tables."
        ),
    )
    return parser.parse_args()


def memory_mode_from_row(row: pd.Series) -> str | None:
    run_label = str(row.get("run_label", ""))
    configuration = str(row.get("configuration_label", "")).lower()
    estimator = str(row.get("estimator", "")).lower()

    if run_label in MEMORY_MODE_NAMES:
        return MEMORY_MODE_NAMES[run_label]

    if "faketensor" in configuration or "faketensor" in estimator:
        return "FakeTensor"

    if "gpumemnet" in configuration or "gpumemnet" in estimator:
        return "GPUMemNet"

    return None


def read_required_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path)


def build_table(analysis_dir: Path) -> pd.DataFrame:
    aggregate = read_required_csv(analysis_dir / "aggregate_policy_summary.csv")
    runs = read_required_csv(analysis_dir / "all_run_summaries.csv")

    aggregate = aggregate.copy()
    aggregate["memory_mode"] = aggregate.apply(memory_mode_from_row, axis=1)
    aggregate = aggregate.dropna(subset=["memory_mode"])

    runs = runs.copy()
    runs["memory_mode"] = runs.apply(memory_mode_from_row, axis=1)
    runs = runs.dropna(subset=["memory_mode"])

    recovery = (
        runs.groupby("memory_mode", as_index=False)
        .agg(
            trace_count=("trace_name", "nunique"),
            failed_attempts=("failed_attempt_count", "sum"),
            recovered_attempts=("recovered_attempt_count", "sum"),
            recovery_stopped=("recovery_stopped_job_count", "sum"),
            total_failed_runtime_s=("total_failed_attempt_runtime_s", "sum"),
            total_recovery_queue_wait_s=(
                "total_recovery_queue_wait_s",
                "sum",
            ),
        )
    )

    table = aggregate.merge(recovery, on="memory_mode", how="left")

    table["mean_failed_runtime_s"] = table.apply(
        lambda row: (
            row["total_failed_runtime_s"] / row["failed_attempts"]
            if (
                pd.notna(row.get("failed_attempts"))
                and row["failed_attempts"] > 0
            )
            else 0.0
        ),
        axis=1,
    )

    table["_order"] = table["memory_mode"].map(MEMORY_MODE_ORDER)
    table = table.sort_values(["_order", "memory_mode"])

    return table


def format_table(table: pd.DataFrame) -> pd.DataFrame:
    selected = table[
        [
            "memory_mode",
            "makespan_s_vs_exclusive_geomean",
            "initial_queue_wait_mean_s_vs_exclusive_geomean",
            "execution_span_mean_s_vs_exclusive_geomean",
            "failed_attempts",
            "recovered_attempts",
            "mean_failed_runtime_s",
        ]
    ].copy()

    selected.columns = [
        "Memory mode",
        "Makespan",
        "Mean queue",
        "Mean exec.",
        "OOMs",
        "Recovered",
        "Mean failed-attempt time",
    ]

    formatted = selected.copy()

    for column in ["Makespan", "Mean queue", "Mean exec."]:
        formatted[column] = formatted[column].map(lambda value: f"{value:.3f}")

    for column in ["OOMs", "Recovered"]:
        formatted[column] = formatted[column].fillna(0).astype(int)

    formatted["Mean failed-attempt time"] = formatted["Mean failed-attempt time"].map(
        lambda value: f"{value:.1f}s"
    )

    return formatted


def latex_table(formatted: pd.DataFrame) -> str:
    rows = []
    rows.append(r"\begin{table}[t]")
    rows.append(r"\centering")
    rows.append(r"\small")
    rows.append(
        r"\caption{"
        r"Effect of memory-feasibility strategy on admission and recovery "
        r"behavior. Makespan, mean queue time, and mean execution time are "
        r"geometric means normalized to Exclusive across traces. OOMs and "
        r"recovered attempts are totals across traces. Mean failed-attempt time reports "
        r"the average runtime of failed attempts before recovery. Failed "
        r"attempts and recovery overhead are included in the end-to-end "
        r"metrics."
        r"}"
    )
    rows.append(r"\label{tab:eval-memory-estimation}")
    rows.append(r"\begin{tabular}{lcccccc}")
    rows.append(r"\toprule")
    rows.append(
        r"Memory mode & Makespan & Mean queue & Mean exec. & "
        r"OOMs & Recovered & Failed runtime \\"
    )
    rows.append(r"\midrule")

    for row in formatted.itertuples(index=False):
        rows.append(
            f"{row[0]} & {row[1]} & {row[2]} & {row[3]} & "
            f"{row[4]} & {row[5]} & {row[6]} \\\\"
        )

    rows.append(r"\bottomrule")
    rows.append(r"\end{tabular}")
    rows.append(r"\end{table}")

    return "\n".join(rows) + "\n"


def markdown_report(formatted: pd.DataFrame) -> str:
    lines = [
        "# Memory-feasibility strategy table",
        "",
        (
            "Makespan, mean queue time, and mean execution time are geometric "
            "means normalized to Exclusive across traces. OOMs and recovered "
            "attempts are totals across traces. Mean failed-attempt time is the mean "
            "time spent in failed attempts before recovery."
        ),
        "",
        formatted.to_markdown(index=False),
        "",
        "## LaTeX label",
        "",
        "`tab:eval-memory-estimation`",
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    analysis_dir = args.analysis_dir
    output_dir = args.output_dir or analysis_dir / "paper_tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    table = build_table(analysis_dir)
    formatted = format_table(table)

    raw_csv = output_dir / "memory_estimation_table_raw.csv"
    formatted_csv = output_dir / "memory_estimation_table.csv"
    latex_path = output_dir / "memory_estimation_table.tex"
    markdown_path = output_dir / "memory_estimation_table.md"

    table.to_csv(raw_csv, index=False)
    formatted.to_csv(formatted_csv, index=False)
    latex_path.write_text(latex_table(formatted))
    markdown_path.write_text(markdown_report(formatted))

    print("Generated memory-feasibility table artifacts:")
    print(f"  raw csv:       {raw_csv}")
    print(f"  formatted csv: {formatted_csv}")
    print(f"  latex:         {latex_path}")
    print(f"  markdown:      {markdown_path}")
    print()
    print(formatted.to_markdown(index=False))

    missing_modes = [
        mode
        for mode in MEMORY_MODE_ORDER
        if mode not in set(formatted["Memory mode"])
    ]

    if missing_modes:
        print()
        print(
            "Note: these memory modes were not found in the current analysis: "
            + ", ".join(missing_modes)
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
