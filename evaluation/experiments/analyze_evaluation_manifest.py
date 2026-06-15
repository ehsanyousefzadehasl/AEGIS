#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and analyze all runs belonging to an "
            "AEGIS evaluation manifest."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Evaluation manifest used to launch the experiment.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help=(
            "Override the manifest results directory. By default, "
            "runner.results_dir from the manifest is used."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Analysis output directory. Defaults to "
            "<results-dir>/<experiment-name>_analysis."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "Regenerate per-policy summaries for completed runs. "
            "Running, failed, timed-out, and missing runs are skipped."
        ),
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")

    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")

    return data


def expected_experiment_root(
    *,
    results_dir: Path,
    experiment_name: str,
    trace_name: str,
    repetition: int,
    configuration_label: str,
) -> Path:
    directory_name = (
        f"{experiment_name}"
        f"__{trace_name}"
        f"__rep{repetition:02d}"
        f"__{configuration_label}"
    )
    return results_dir / directory_name


def discover_metadata_paths(
    experiment_root: Path,
) -> list[Path]:
    return sorted(
        experiment_root.glob("*/*/metadata.json")
    )


def classify_metadata(
    metadata: dict[str, Any],
) -> str:
    if metadata.get("timed_out") is True:
        return "timed_out"

    return_code = metadata.get("return_code")

    if return_code is None:
        return "running"

    try:
        return_code = int(return_code)
    except (TypeError, ValueError):
        return "invalid_metadata"

    if return_code == 0:
        return "complete"

    return "failed"


def choose_latest_metadata(
    metadata_paths: list[Path],
) -> Path | None:
    if not metadata_paths:
        return None

    return max(
        metadata_paths,
        key=lambda path: path.stat().st_mtime,
    )


def build_validation_rows(
    *,
    manifest: dict[str, Any],
    results_dir: Path,
) -> list[dict[str, Any]]:
    experiment_name = str(manifest["experiment_name"])
    repetitions = int(manifest.get("repetitions", 1))
    traces = manifest["traces"]
    configurations = manifest["configurations"]

    rows: list[dict[str, Any]] = []

    for repetition in range(1, repetitions + 1):
        for trace in traces:
            trace_name = str(trace["name"])
            trace_csv = str(trace["csv"])

            for configuration in configurations:
                configuration_label = str(
                    configuration["label"]
                )
                expected_policy = str(
                    configuration["policy"]
                )
                expected_estimator = str(
                    configuration.get("estimator", "None")
                )

                experiment_root = expected_experiment_root(
                    results_dir=results_dir,
                    experiment_name=experiment_name,
                    trace_name=trace_name,
                    repetition=repetition,
                    configuration_label=configuration_label,
                )

                metadata_paths = discover_metadata_paths(
                    experiment_root
                )
                metadata_path = choose_latest_metadata(
                    metadata_paths
                )

                row: dict[str, Any] = {
                    "experiment_name": experiment_name,
                    "trace_name": trace_name,
                    "trace_csv": trace_csv,
                    "repetition": repetition,
                    "configuration_label": configuration_label,
                    "expected_policy": expected_policy,
                    "expected_estimator": expected_estimator,
                    "experiment_root": str(experiment_root),
                    "discovered_run_count": len(metadata_paths),
                    "metadata_path": None,
                    "run_dir": None,
                    "run_label": None,
                    "actual_policy": None,
                    "actual_estimator": None,
                    "expected_tasks": None,
                    "submit_return_code": None,
                    "return_code": None,
                    "timed_out": None,
                    "git_commit": None,
                    "status": "missing",
                    "configuration_matches": False,
                }

                if metadata_path is None:
                    rows.append(row)
                    continue

                metadata = load_json(metadata_path)

                actual_policy = metadata.get("policy")
                actual_estimator = metadata.get(
                    "estimator",
                    "None",
                )

                configuration_matches = (
                    str(actual_policy) == expected_policy
                    and str(actual_estimator)
                    == expected_estimator
                    and str(metadata.get("trace_csv"))
                    == trace_csv
                )

                row.update(
                    {
                        "metadata_path": str(metadata_path),
                        "run_dir": metadata.get(
                            "run_dir",
                            str(metadata_path.parent),
                        ),
                        "run_label": metadata.get("run_label"),
                        "actual_policy": actual_policy,
                        "actual_estimator": actual_estimator,
                        "expected_tasks": metadata.get(
                            "expected_tasks"
                        ),
                        "submit_return_code": metadata.get(
                            "submit_return_code"
                        ),
                        "return_code": metadata.get(
                            "return_code"
                        ),
                        "timed_out": metadata.get(
                            "timed_out"
                        ),
                        "git_commit": metadata.get(
                            "git_commit"
                        ),
                        "status": classify_metadata(metadata),
                        "configuration_matches": (
                            configuration_matches
                        ),
                    }
                )

                rows.append(row)

    return rows



def refresh_completed_summaries(
    frame: pd.DataFrame,
) -> None:
    completed_roots = sorted(
        {
            Path(value)
            for value in frame.loc[
                frame["status"] == "complete",
                "experiment_root",
            ].dropna()
        }
    )

    if not completed_roots:
        print("\nNo completed runs are available to summarize.")
        return

    script = (
        Path(__file__).resolve().parent
        / "summarize_policy_runs.py"
    )

    print("\n===== Refreshing completed summaries =====")

    for experiment_root in completed_roots:
        print(f"Summarizing: {experiment_root}")

        subprocess.run(
            [
                sys.executable,
                str(script),
                "--experiment-root",
                str(experiment_root),
            ],
            check=True,
        )



def collect_completed_run_summaries(
    *,
    validation_frame: pd.DataFrame,
    output_dir: Path,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []

    completed = validation_frame[
        validation_frame["status"] == "complete"
    ]

    for record in completed.itertuples(index=False):
        experiment_root = Path(record.experiment_root)
        summary_path = (
            experiment_root
            / "analysis"
            / "run_summary.csv"
        )

        if not summary_path.is_file():
            raise FileNotFoundError(
                f"Missing summary for completed run: "
                f"{summary_path}"
            )

        summary = pd.read_csv(summary_path)

        if summary.empty:
            raise ValueError(
                f"{summary_path}: summary is empty"
            )

        summary = summary.copy()
        summary.insert(0, "trace_name", record.trace_name)
        summary.insert(1, "repetition", record.repetition)
        summary.insert(
            2,
            "configuration_label",
            record.configuration_label,
        )

        rows.append(summary)

    if rows:
        combined = pd.concat(
            rows,
            ignore_index=True,
        )
    else:
        combined = pd.DataFrame()

    output_path = output_dir / "all_run_summaries.csv"
    combined.to_csv(output_path, index=False)

    print(f"Wrote: {output_path}")

    return combined



def generate_per_trace_comparisons(
    *,
    validation_frame: pd.DataFrame,
    output_dir: Path,
) -> None:
    completed = validation_frame[
        validation_frame["status"] == "complete"
    ]

    if completed.empty:
        print("\nNo completed runs are available for plotting.")
        return

    plot_script = (
        Path(__file__).resolve().parent
        / "plot_policy_distributions.py"
    )

    solo_profiles = [
        Path(
            "evaluation/profiling/solo/extracted/"
            "solo_profile_results_1gpu.csv"
        ),
        Path(
            "evaluation/profiling/solo/extracted/"
            "solo_profile_results_2gpu.csv"
        ),
    ]

    for solo_path in solo_profiles:
        if not solo_path.is_file():
            raise FileNotFoundError(solo_path)

    print("\n===== Generating per-trace comparisons =====")

    for trace_name, group in completed.groupby(
        "trace_name",
        sort=True,
    ):
        job_metric_paths: list[Path] = []

        for record in group.itertuples(index=False):
            path = (
                Path(record.experiment_root)
                / "analysis"
                / "job_metrics.csv"
            )

            if not path.is_file():
                raise FileNotFoundError(
                    f"Missing job metrics for completed run: {path}"
                )

            job_metric_paths.append(path)

        trace_output_dir = (
            output_dir
            / "traces"
            / str(trace_name)
        )

        command = [
            sys.executable,
            str(plot_script),
            "--job-metrics",
            *[str(path) for path in job_metric_paths],
            "--solo-profiles",
            *[str(path) for path in solo_profiles],
            "--output-dir",
            str(trace_output_dir),
        ]

        print(
            f"Plotting {trace_name}: "
            f"{len(job_metric_paths)} completed policies"
        )

        subprocess.run(
            command,
            check=True,
        )



def save_figure(
    figure: plt.Figure,
    output_dir: Path,
    stem: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()

    for suffix in ["pdf", "png"]:
        figure.savefig(
            output_dir / f"{stem}.{suffix}",
            dpi=300,
            bbox_inches="tight",
        )

    plt.close(figure)



def generate_per_trace_performance_tables(
    *,
    validation_frame: pd.DataFrame,
    output_dir: Path,
) -> None:
    completed = validation_frame[
        validation_frame["status"] == "complete"
    ]

    print("\n===== Generating performance tables and figures =====")

    for trace_name, group in completed.groupby(
        "trace_name",
        sort=True,
    ):
        frames: list[pd.DataFrame] = []

        for record in group.itertuples(index=False):
            summary_path = (
                Path(record.experiment_root)
                / "analysis"
                / "run_summary.csv"
            )

            if not summary_path.is_file():
                raise FileNotFoundError(summary_path)

            summary = pd.read_csv(summary_path).copy()

            if summary.empty:
                raise ValueError(
                    f"{summary_path}: summary is empty"
                )

            summary.insert(
                0,
                "configuration_label",
                record.configuration_label,
            )
            frames.append(summary)

        performance = pd.concat(
            frames,
            ignore_index=True,
        )

        trace_output = (
            output_dir
            / "traces"
            / str(trace_name)
        )
        trace_output.mkdir(parents=True, exist_ok=True)

        metric_columns = [
            "makespan_s",
            "initial_queue_wait_mean_s",
            "initial_queue_wait_p50_s",
            "initial_queue_wait_p95_s",
            "jct_mean_s",
            "jct_p50_s",
            "jct_p95_s",
            "execution_span_mean_s",
            "execution_span_p50_s",
            "execution_span_p95_s",
            "successful_attempt_runtime_mean_s",
            "successful_attempt_runtime_p50_s",
            "successful_attempt_runtime_p95_s",
        ]

        for column in metric_columns:
            performance[column] = pd.to_numeric(
                performance[column],
                errors="coerce",
            )

        table_columns = [
            "configuration_label",
            "run_label",
            "policy",
            "estimator",
            "submitted_job_count",
            "completed_job_count",
            "incomplete_job_count",
            "completion_fraction",
            "makespan_s",
            "initial_queue_wait_mean_s",
            "initial_queue_wait_p50_s",
            "initial_queue_wait_p95_s",
            "jct_mean_s",
            "jct_p50_s",
            "jct_p95_s",
            "execution_span_mean_s",
            "execution_span_p50_s",
            "execution_span_p95_s",
            "successful_attempt_runtime_mean_s",
            "successful_attempt_runtime_p50_s",
            "successful_attempt_runtime_p95_s",
            "failed_attempt_count",
            "recovered_attempt_count",
            "recovery_stopped_job_count",
            "total_failed_attempt_runtime_s",
            "total_recovery_queue_wait_s",
        ]

        performance[table_columns].to_csv(
            trace_output / "performance_summary.csv",
            index=False,
        )

        exclusive = performance[
            performance["run_label"] == "exclusive"
        ]

        if len(exclusive) != 1:
            print(
                f"{trace_name}: expected exactly one Exclusive "
                f"run, found {len(exclusive)}; skipping normalization"
            )
            continue

        normalized = performance.copy()

        for column in metric_columns:
            baseline = float(exclusive.iloc[0][column])

            normalized[f"{column}_vs_exclusive"] = (
                normalized[column] / baseline
                if np.isfinite(baseline) and baseline > 0
                else np.nan
            )

        normalized["makespan_reduction_percent"] = (
            1.0
            - normalized["makespan_s_vs_exclusive"]
        ) * 100.0

        normalized_columns = [
            "configuration_label",
            "run_label",
            "completion_fraction",
            "makespan_s",
            "makespan_s_vs_exclusive",
            "makespan_reduction_percent",
            "initial_queue_wait_mean_s",
            "initial_queue_wait_mean_s_vs_exclusive",
            "initial_queue_wait_p95_s",
            "initial_queue_wait_p95_s_vs_exclusive",
            "jct_mean_s",
            "jct_mean_s_vs_exclusive",
            "jct_p95_s",
            "jct_p95_s_vs_exclusive",
            "execution_span_mean_s",
            "execution_span_mean_s_vs_exclusive",
            "execution_span_p95_s",
            "execution_span_p95_s_vs_exclusive",
            "successful_attempt_runtime_mean_s",
            "successful_attempt_runtime_mean_s_vs_exclusive",
            "failed_attempt_count",
            "recovered_attempt_count",
        ]

        normalized[normalized_columns].to_csv(
            trace_output
            / "normalized_performance_summary.csv",
            index=False,
        )

        plot_single_metric_bars(
            frame=performance,
            value_column="makespan_s",
            y_label="Makespan (seconds)",
            output_dir=trace_output,
            output_stem="makespan_comparison",
        )

        plot_grouped_metric_bars(
            frame=performance,
            mean_column="jct_mean_s",
            tail_column="jct_p95_s",
            mean_label="Mean JCT",
            tail_label="P95 JCT",
            y_label="Job completion time (seconds)",
            output_dir=trace_output,
            output_stem="jct_comparison",
        )

        plot_grouped_metric_bars(
            frame=performance,
            mean_column="initial_queue_wait_mean_s",
            tail_column="initial_queue_wait_p95_s",
            mean_label="Mean wait",
            tail_label="P95 wait",
            y_label="Initial queue wait (seconds)",
            output_dir=trace_output,
            output_stem="queue_wait_comparison",
        )

        plot_grouped_metric_bars(
            frame=performance,
            mean_column="execution_span_mean_s",
            tail_column="execution_span_p95_s",
            mean_label="Mean execution span",
            tail_label="P95 execution span",
            y_label="Execution span (seconds)",
            output_dir=trace_output,
            output_stem="execution_time_comparison",
        )

        print(
            f"{trace_name}: wrote performance tables and figures "
            f"for {len(performance)} policies"
        )


def _ordered_policy_frame(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    order = {
        "exclusive": 0,
        "OR-MAGM": 1,
        "EST-MAGM__horus": 2,
        "HORUS__horus": 3,
        "LUCID": 4,
        "oracle-MAGM": 5,
    }

    prepared = frame.copy()
    prepared["_order"] = (
        prepared["run_label"]
        .map(order)
        .fillna(len(order))
    )

    return prepared.sort_values(
        ["_order", "run_label"]
    )


def plot_single_metric_bars(
    *,
    frame: pd.DataFrame,
    value_column: str,
    y_label: str,
    output_dir: Path,
    output_stem: str,
) -> None:
    prepared = _ordered_policy_frame(frame)

    figure, axis = plt.subplots(figsize=(7.2, 4.4))

    x = np.arange(len(prepared))
    values = prepared[value_column].to_numpy(dtype=float)

    axis.bar(x, values)
    axis.set_xticks(x)
    axis.set_xticklabels(
        prepared["run_label"],
        rotation=20,
        ha="right",
    )
    axis.set_ylabel(y_label)
    axis.set_xlabel("Policy")
    axis.set_ylim(bottom=0)
    axis.grid(True, axis="y", alpha=0.3)

    save_figure(
        figure,
        output_dir,
        output_stem,
    )


def plot_grouped_metric_bars(
    *,
    frame: pd.DataFrame,
    mean_column: str,
    tail_column: str,
    mean_label: str,
    tail_label: str,
    y_label: str,
    output_dir: Path,
    output_stem: str,
) -> None:
    prepared = _ordered_policy_frame(frame)

    x = np.arange(len(prepared))
    width = 0.36

    figure, axis = plt.subplots(figsize=(7.2, 4.4))

    axis.bar(
        x - width / 2,
        prepared[mean_column],
        width,
        label=mean_label,
    )
    axis.bar(
        x + width / 2,
        prepared[tail_column],
        width,
        label=tail_label,
    )

    axis.set_xticks(x)
    axis.set_xticklabels(
        prepared["run_label"],
        rotation=20,
        ha="right",
    )
    axis.set_ylabel(y_label)
    axis.set_xlabel("Policy")
    axis.set_ylim(bottom=0)
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend()

    save_figure(
        figure,
        output_dir,
        output_stem,
    )



def geometric_mean(values: pd.Series) -> float:
    numeric = pd.to_numeric(
        values,
        errors="coerce",
    ).dropna()

    numeric = numeric[
        np.isfinite(numeric) & (numeric > 0)
    ]

    if numeric.empty:
        return np.nan

    return float(
        np.exp(np.log(numeric.to_numpy(dtype=float)).mean())
    )


def generate_cross_trace_analysis(
    *,
    validation_frame: pd.DataFrame,
    output_dir: Path,
) -> None:
    completed = validation_frame[
        validation_frame["status"] == "complete"
    ]

    available_traces = sorted(
        completed["trace_name"].dropna().unique()
    )

    frames: list[pd.DataFrame] = []

    for trace_name in available_traces:
        path = (
            output_dir
            / "traces"
            / str(trace_name)
            / "normalized_performance_summary.csv"
        )

        if not path.is_file():
            print(
                f"{trace_name}: normalized performance table "
                "is unavailable; skipping cross-trace inclusion"
            )
            continue

        frame = pd.read_csv(path).copy()
        frame.insert(0, "trace_name", trace_name)
        frames.append(frame)

    if not frames:
        print(
            "\nNo normalized trace summaries are available "
            "for cross-trace analysis."
        )
        return

    combined = pd.concat(
        frames,
        ignore_index=True,
    )

    combined_path = (
        output_dir
        / "all_trace_normalized_summary.csv"
    )
    combined.to_csv(combined_path, index=False)

    ratio_columns = [
        "makespan_s_vs_exclusive",
        "jct_mean_s_vs_exclusive",
        "jct_p95_s_vs_exclusive",
        "initial_queue_wait_mean_s_vs_exclusive",
        "initial_queue_wait_p95_s_vs_exclusive",
        "execution_span_mean_s_vs_exclusive",
        "execution_span_p95_s_vs_exclusive",
        "successful_attempt_runtime_mean_s_vs_exclusive",
    ]

    aggregate_rows = []

    for run_label, group in combined.groupby(
        "run_label",
        sort=True,
    ):
        row = {
            "run_label": run_label,
            "trace_count": int(
                group["trace_name"].nunique()
            ),
            "completion_fraction_mean": float(
                pd.to_numeric(
                    group["completion_fraction"],
                    errors="coerce",
                ).mean()
            ),
        }

        for column in ratio_columns:
            if column in group.columns:
                row[
                    f"{column}_geomean"
                ] = geometric_mean(group[column])

        makespan_ratio = row.get(
            "makespan_s_vs_exclusive_geomean",
            np.nan,
        )

        row[
            "makespan_reduction_percent_from_geomean"
        ] = (
            (1.0 - makespan_ratio) * 100.0
            if np.isfinite(makespan_ratio)
            else np.nan
        )

        aggregate_rows.append(row)

    aggregate = pd.DataFrame(aggregate_rows)

    aggregate_path = (
        output_dir
        / "aggregate_policy_summary.csv"
    )
    aggregate.to_csv(aggregate_path, index=False)

    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    plot_cross_trace_grouped_bars(
        frame=combined,
        value_columns=[
            (
                "makespan_s_vs_exclusive",
                "Normalized makespan",
            ),
        ],
        y_label="Relative to Exclusive",
        output_dir=figures_dir,
        output_stem="normalized_makespan_by_trace",
    )

    plot_cross_trace_grouped_bars(
        frame=combined,
        value_columns=[
            (
                "jct_mean_s_vs_exclusive",
                "Mean JCT",
            ),
            (
                "jct_p95_s_vs_exclusive",
                "P95 JCT",
            ),
        ],
        y_label="Relative to Exclusive",
        output_dir=figures_dir,
        output_stem="normalized_jct_by_trace",
    )

    plot_cross_trace_grouped_bars(
        frame=combined,
        value_columns=[
            (
                "initial_queue_wait_mean_s_vs_exclusive",
                "Mean wait",
            ),
            (
                "initial_queue_wait_p95_s_vs_exclusive",
                "P95 wait",
            ),
        ],
        y_label="Relative to Exclusive",
        output_dir=figures_dir,
        output_stem="normalized_queue_wait_by_trace",
    )

    plot_cross_trace_grouped_bars(
        frame=combined,
        value_columns=[
            (
                "execution_span_mean_s_vs_exclusive",
                "Mean execution span",
            ),
            (
                "execution_span_p95_s_vs_exclusive",
                "P95 execution span",
            ),
        ],
        y_label="Relative to Exclusive",
        output_dir=figures_dir,
        output_stem="normalized_execution_span_by_trace",
    )

    plot_aggregate_policy_performance(
        aggregate=aggregate,
        output_dir=figures_dir,
    )

    print(
        "\nWrote cross-trace analysis:"
        f"\n  {combined_path}"
        f"\n  {aggregate_path}"
    )


def plot_cross_trace_grouped_bars(
    *,
    frame: pd.DataFrame,
    value_columns: list[tuple[str, str]],
    y_label: str,
    output_dir: Path,
    output_stem: str,
) -> None:
    traces = sorted(
        frame["trace_name"].astype(str).unique()
    )

    policies = list(
        _ordered_policy_frame(frame)[
            "run_label"
        ].drop_duplicates()
    )

    combinations = [
        (trace_name, column, label)
        for trace_name in traces
        for column, label in value_columns
    ]

    x = np.arange(len(policies))
    total_width = 0.8
    width = total_width / max(len(combinations), 1)

    figure, axis = plt.subplots(
        figsize=(max(7.2, len(policies) * 1.25), 4.6)
    )

    for index, (
        trace_name,
        value_column,
        metric_label,
    ) in enumerate(combinations):
        values = []

        for policy in policies:
            match = frame[
                (frame["trace_name"].astype(str) == trace_name)
                & (frame["run_label"] == policy)
            ]

            values.append(
                float(match.iloc[0][value_column])
                if len(match) == 1
                else np.nan
            )

        offset = (
            index
            - (len(combinations) - 1) / 2
        ) * width

        label = (
            trace_name
            if len(value_columns) == 1
            else f"{trace_name}: {metric_label}"
        )

        axis.bar(
            x + offset,
            values,
            width,
            label=label,
        )

    axis.axhline(
        1.0,
        linestyle="--",
        linewidth=1.0,
        label="Exclusive baseline",
    )
    axis.set_xticks(x)
    axis.set_xticklabels(
        policies,
        rotation=20,
        ha="right",
    )
    axis.set_ylabel(y_label)
    axis.set_xlabel("Policy")
    axis.set_ylim(bottom=0)
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend()

    save_figure(
        figure,
        output_dir,
        output_stem,
    )


def plot_aggregate_policy_performance(
    *,
    aggregate: pd.DataFrame,
    output_dir: Path,
) -> None:
    prepared = _ordered_policy_frame(aggregate)

    metrics = [
        (
            "makespan_s_vs_exclusive_geomean",
            "Makespan",
        ),
        (
            "jct_mean_s_vs_exclusive_geomean",
            "Mean JCT",
        ),
        (
            "initial_queue_wait_mean_s_vs_exclusive_geomean",
            "Mean wait",
        ),
    ]

    metrics = [
        item
        for item in metrics
        if item[0] in prepared.columns
    ]

    x = np.arange(len(prepared))
    total_width = 0.8
    width = total_width / max(len(metrics), 1)

    figure, axis = plt.subplots(
        figsize=(max(7.2, len(prepared) * 1.25), 4.6)
    )

    for index, (column, label) in enumerate(metrics):
        offset = (
            index
            - (len(metrics) - 1) / 2
        ) * width

        axis.bar(
            x + offset,
            prepared[column],
            width,
            label=label,
        )

    axis.axhline(
        1.0,
        linestyle="--",
        linewidth=1.0,
        label="Exclusive baseline",
    )
    axis.set_xticks(x)
    axis.set_xticklabels(
        prepared["run_label"],
        rotation=20,
        ha="right",
    )
    axis.set_ylabel("Geometric mean relative to Exclusive")
    axis.set_xlabel("Policy")
    axis.set_ylim(bottom=0)
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend()

    save_figure(
        figure,
        output_dir,
        "aggregate_policy_performance",
    )


def generate_recovery_analysis(
    *,
    validation_frame: pd.DataFrame,
    output_dir: Path,
) -> None:
    completed = validation_frame[
        validation_frame["status"] == "complete"
    ]

    print("\n===== Generating recovery analysis =====")

    for trace_name, group in completed.groupby(
        "trace_name",
        sort=True,
    ):
        frames: list[pd.DataFrame] = []

        for record in group.itertuples(index=False):
            job_metrics_path = (
                Path(record.experiment_root)
                / "analysis"
                / "job_metrics.csv"
            )

            if not job_metrics_path.is_file():
                raise FileNotFoundError(job_metrics_path)

            frame = pd.read_csv(job_metrics_path).copy()
            frame.insert(0, "trace_name", trace_name)
            frame.insert(
                1,
                "configuration_label",
                record.configuration_label,
            )
            frames.append(frame)

        jobs = pd.concat(frames, ignore_index=True)

        numeric_columns = [
            "failed_attempt_count",
            "recovered_attempt_count",
            "recovery_stopped_count",
            "failed_attempt_runtime_s",
            "total_recovery_queue_wait_s",
            "max_recovery_queue_wait_s",
            "total_recovery_gap_s",
            "max_recovery_gap_s",
            "successful_attempt_runtime_s",
            "jct_s",
        ]

        for column in numeric_columns:
            jobs[column] = pd.to_numeric(
                jobs[column],
                errors="coerce",
            ).fillna(0.0)

        recovered = jobs[
            jobs["recovered_attempt_count"] > 0
        ].copy()

        recovered["workload"] = recovered[
            "task_file"
        ].map(lambda value: Path(str(value)).name)

        recovered["recovery_overhead_s"] = (
            recovered["failed_attempt_runtime_s"]
            + recovered["total_recovery_gap_s"]
        )

        detail_columns = [
            "trace_name",
            "configuration_label",
            "run_label",
            "task_id",
            "task_file",
            "workload",
            "failed_attempt_count",
            "recovered_attempt_count",
            "recovery_stopped_count",
            "failed_attempt_runtime_s",
            "total_recovery_queue_wait_s",
            "max_recovery_queue_wait_s",
            "total_recovery_gap_s",
            "max_recovery_gap_s",
            "successful_attempt_runtime_s",
            "recovery_overhead_s",
            "jct_s",
        ]

        trace_output = (
            output_dir
            / "traces"
            / str(trace_name)
            / "recovery"
        )
        trace_output.mkdir(parents=True, exist_ok=True)

        recovered[detail_columns].to_csv(
            trace_output / "recovery_job_details.csv",
            index=False,
        )

        summary_rows = []

        for run_label, policy_jobs in jobs.groupby(
            "run_label",
            sort=True,
        ):
            policy_recovered = policy_jobs[
                policy_jobs["recovered_attempt_count"] > 0
            ]

            recovered_count = len(policy_recovered)

            queue_wait = policy_recovered[
                "total_recovery_queue_wait_s"
            ]
            recovery_gap = policy_recovered[
                "total_recovery_gap_s"
            ]
            lost_runtime = policy_recovered[
                "failed_attempt_runtime_s"
            ]

            summary_rows.append(
                {
                    "trace_name": trace_name,
                    "run_label": run_label,
                    "submitted_job_count": len(policy_jobs),
                    "jobs_with_failed_attempts": int(
                        (
                            policy_jobs["failed_attempt_count"] > 0
                        ).sum()
                    ),
                    "recovered_job_count": recovered_count,
                    "recovery_stopped_job_count": int(
                        (
                            policy_jobs["recovery_stopped_count"] > 0
                        ).sum()
                    ),
                    "failed_attempt_count": int(
                        policy_jobs[
                            "failed_attempt_count"
                        ].sum()
                    ),
                    "recovered_attempt_count": int(
                        policy_jobs[
                            "recovered_attempt_count"
                        ].sum()
                    ),
                    "recovery_queue_wait_mean_s": (
                        float(queue_wait.mean())
                        if recovered_count
                        else 0.0
                    ),
                    "recovery_queue_wait_p95_s": (
                        float(queue_wait.quantile(0.95))
                        if recovered_count
                        else 0.0
                    ),
                    "recovery_queue_wait_max_s": (
                        float(queue_wait.max())
                        if recovered_count
                        else 0.0
                    ),
                    "recovery_gap_mean_s": (
                        float(recovery_gap.mean())
                        if recovered_count
                        else 0.0
                    ),
                    "recovery_gap_p95_s": (
                        float(recovery_gap.quantile(0.95))
                        if recovered_count
                        else 0.0
                    ),
                    "total_failed_runtime_s": float(
                        lost_runtime.sum()
                    ),
                    "total_recovery_queue_wait_s": float(
                        queue_wait.sum()
                    ),
                    "total_recovery_gap_s": float(
                        recovery_gap.sum()
                    ),
                    "total_recovery_overhead_s": float(
                        (
                            lost_runtime
                            + recovery_gap
                        ).sum()
                    ),
                }
            )

        summary = pd.DataFrame(summary_rows)

        summary.to_csv(
            trace_output / "recovery_policy_summary.csv",
            index=False,
        )

        if recovered.empty:
            print(
                f"{trace_name}: no recovered jobs; "
                "wrote empty recovery tables"
            )
            continue

        plot_recovered_job_costs(
            recovered=recovered,
            output_dir=trace_output,
        )

        plot_policy_recovery_costs(
            summary=summary,
            output_dir=trace_output,
        )

        print(
            f"{trace_name}: analyzed "
            f"{len(recovered)} recovered jobs"
        )


def plot_recovered_job_costs(
    *,
    recovered: pd.DataFrame,
    output_dir: Path,
) -> None:
    prepared = recovered.sort_values(
        [
            "run_label",
            "recovery_overhead_s",
        ],
        ascending=[True, False],
    ).copy()

    prepared["label"] = (
        prepared["run_label"].astype(str)
        + " | "
        + prepared["workload"].astype(str)
    )

    figure_height = max(
        4.2,
        0.35 * len(prepared) + 1.5,
    )

    figure, axis = plt.subplots(
        figsize=(8.0, figure_height)
    )

    y = np.arange(len(prepared))

    failed = prepared[
        "failed_attempt_runtime_s"
    ].to_numpy(dtype=float)
    gap = prepared[
        "total_recovery_gap_s"
    ].to_numpy(dtype=float)
    successful = prepared[
        "successful_attempt_runtime_s"
    ].to_numpy(dtype=float)

    axis.barh(
        y,
        failed,
        label="Failed-attempt runtime",
    )
    axis.barh(
        y,
        gap,
        left=failed,
        label="Failure-to-relaunch gap",
    )
    axis.barh(
        y,
        successful,
        left=failed + gap,
        label="Successful rerun runtime",
    )

    axis.set_yticks(y)
    axis.set_yticklabels(prepared["label"])
    axis.invert_yaxis()
    axis.set_xlabel("Time (seconds)")
    axis.set_ylabel("Recovered job")
    axis.grid(True, axis="x", alpha=0.3)
    axis.legend()

    save_figure(
        figure,
        output_dir,
        "recovered_job_cost_breakdown",
    )


def plot_policy_recovery_costs(
    *,
    summary: pd.DataFrame,
    output_dir: Path,
) -> None:
    prepared = summary[
        summary["recovered_job_count"] > 0
    ].copy()

    if prepared.empty:
        return

    prepared = prepared.sort_values("run_label")

    x = np.arange(len(prepared))
    width = 0.36

    figure, axis = plt.subplots(figsize=(7.2, 4.4))

    axis.bar(
        x - width / 2,
        prepared["total_failed_runtime_s"],
        width,
        label="Failed-attempt runtime",
    )
    axis.bar(
        x + width / 2,
        prepared["total_recovery_gap_s"],
        width,
        label="Failure-to-relaunch gap",
    )

    axis.set_xticks(x)
    axis.set_xticklabels(
        prepared["run_label"],
        rotation=20,
        ha="right",
    )
    axis.set_ylabel("Total time (seconds)")
    axis.set_xlabel("Policy")
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend()

    save_figure(
        figure,
        output_dir,
        "policy_recovery_cost",
    )



def markdown_table(
    frame: pd.DataFrame,
    *,
    columns: list[str],
    rename: dict[str, str] | None = None,
    decimals: int = 3,
) -> str:
    available = [
        column for column in columns
        if column in frame.columns
    ]

    if not available:
        return "_No data available._"

    table = frame[available].copy()

    if rename:
        table = table.rename(columns=rename)

    for column in table.columns:
        if pd.api.types.is_numeric_dtype(table[column]):
            table[column] = table[column].map(
                lambda value: (
                    ""
                    if pd.isna(value)
                    else f"{float(value):.{decimals}f}"
                )
            )

    return table.to_markdown(index=False)


def relative_markdown_path(
    *,
    target: Path,
    report_dir: Path,
) -> str:
    return target.relative_to(report_dir).as_posix()


def generate_markdown_report(
    *,
    validation_frame: pd.DataFrame,
    output_dir: Path,
) -> None:
    report_path = output_dir / "report.md"
    lines: list[str] = []

    lines.extend(
        [
            "# Final Representative Evaluation",
            "",
            "This report is generated automatically by "
            "`analyze_evaluation_manifest.py`.",
            "",
            "## Evaluation status",
            "",
        ]
    )

    status = (
        validation_frame.groupby(
            ["trace_name", "status"],
            dropna=False,
        )
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    lines.append(
        markdown_table(
            status,
            columns=list(status.columns),
            decimals=0,
        )
    )

    lines.extend(["", "## Aggregate cross-trace comparison", ""])

    aggregate_path = (
        output_dir / "aggregate_policy_summary.csv"
    )

    if aggregate_path.is_file():
        aggregate = pd.read_csv(aggregate_path)

        lines.append(
            markdown_table(
                aggregate,
                columns=[
                    "run_label",
                    "trace_count",
                    "completion_fraction_mean",
                    "makespan_s_vs_exclusive_geomean",
                    "makespan_reduction_percent_from_geomean",
                    "jct_mean_s_vs_exclusive_geomean",
                    "jct_p95_s_vs_exclusive_geomean",
                    "initial_queue_wait_mean_s_vs_exclusive_geomean",
                    "initial_queue_wait_p95_s_vs_exclusive_geomean",
                    "execution_span_mean_s_vs_exclusive_geomean",
                ],
                rename={
                    "run_label": "Policy",
                    "trace_count": "Traces",
                    "completion_fraction_mean": "Completion",
                    "makespan_s_vs_exclusive_geomean": (
                        "Makespan / Exclusive"
                    ),
                    "makespan_reduction_percent_from_geomean": (
                        "Makespan reduction (%)"
                    ),
                    "jct_mean_s_vs_exclusive_geomean": (
                        "Mean JCT / Exclusive"
                    ),
                    "jct_p95_s_vs_exclusive_geomean": (
                        "P95 JCT / Exclusive"
                    ),
                    "initial_queue_wait_mean_s_vs_exclusive_geomean": (
                        "Mean wait / Exclusive"
                    ),
                    "initial_queue_wait_p95_s_vs_exclusive_geomean": (
                        "P95 wait / Exclusive"
                    ),
                    "execution_span_mean_s_vs_exclusive_geomean": (
                        "Execution span / Exclusive"
                    ),
                },
            )
        )
    else:
        lines.append("_Aggregate results are not available yet._")

    aggregate_figure = (
        output_dir
        / "figures"
        / "aggregate_policy_performance.png"
    )

    if aggregate_figure.is_file():
        lines.extend(
            [
                "",
                "![Aggregate policy performance]"
                f"({relative_markdown_path(target=aggregate_figure, report_dir=output_dir)})",
            ]
        )

    completed_traces = sorted(
        validation_frame.loc[
            validation_frame["status"] == "complete",
            "trace_name",
        ].dropna().unique()
    )

    for trace_name in completed_traces:
        trace_dir = output_dir / "traces" / str(trace_name)

        performance_path = (
            trace_dir / "performance_summary.csv"
        )

        if not performance_path.is_file():
            continue

        performance = pd.read_csv(performance_path)

        lines.extend(
            [
                "",
                "---",
                "",
                f"## Trace: {trace_name}",
                "",
                "Results below contain only runs from this trace.",
                "",
                "### Raw performance summary",
                "",
            ]
        )

        lines.append(
            markdown_table(
                performance,
                columns=[
                    "run_label",
                    "completion_fraction",
                    "makespan_s",
                    "initial_queue_wait_mean_s",
                    "initial_queue_wait_p95_s",
                    "jct_mean_s",
                    "jct_p95_s",
                    "execution_span_mean_s",
                    "execution_span_p95_s",
                    "successful_attempt_runtime_mean_s",
                    "failed_attempt_count",
                    "recovered_attempt_count",
                ],
                rename={
                    "run_label": "Policy",
                    "completion_fraction": "Completion",
                    "makespan_s": "Makespan (s)",
                    "initial_queue_wait_mean_s": "Mean wait (s)",
                    "initial_queue_wait_p95_s": "P95 wait (s)",
                    "jct_mean_s": "Mean JCT (s)",
                    "jct_p95_s": "P95 JCT (s)",
                    "execution_span_mean_s": (
                        "Mean execution span (s)"
                    ),
                    "execution_span_p95_s": (
                        "P95 execution span (s)"
                    ),
                    "successful_attempt_runtime_mean_s": (
                        "Mean successful runtime (s)"
                    ),
                    "failed_attempt_count": "Failed attempts",
                    "recovered_attempt_count": (
                        "Recovered attempts"
                    ),
                },
            )
        )

        normalized_path = (
            trace_dir
            / "normalized_performance_summary.csv"
        )

        if normalized_path.is_file():
            normalized = pd.read_csv(normalized_path)

            lines.extend(
                [
                    "",
                    "### Normalized performance summary",
                    "",
                    "All ratios use Exclusive = 1.0 for this trace. "
                    "Lower is better.",
                    "",
                ]
            )

            lines.append(
                markdown_table(
                    normalized,
                    columns=[
                        "run_label",
                        "makespan_s_vs_exclusive",
                        "makespan_reduction_percent",
                        "jct_mean_s_vs_exclusive",
                        "jct_p95_s_vs_exclusive",
                        "initial_queue_wait_mean_s_vs_exclusive",
                        "initial_queue_wait_p95_s_vs_exclusive",
                        "execution_span_mean_s_vs_exclusive",
                        "execution_span_p95_s_vs_exclusive",
                    ],
                    rename={
                        "run_label": "Policy",
                        "makespan_s_vs_exclusive": (
                            "Makespan / Exclusive"
                        ),
                        "makespan_reduction_percent": (
                            "Makespan reduction (%)"
                        ),
                        "jct_mean_s_vs_exclusive": (
                            "Mean JCT / Exclusive"
                        ),
                        "jct_p95_s_vs_exclusive": (
                            "P95 JCT / Exclusive"
                        ),
                        "initial_queue_wait_mean_s_vs_exclusive": (
                            "Mean wait / Exclusive"
                        ),
                        "initial_queue_wait_p95_s_vs_exclusive": (
                            "P95 wait / Exclusive"
                        ),
                        "execution_span_mean_s_vs_exclusive": (
                            "Mean execution span / Exclusive"
                        ),
                        "execution_span_p95_s_vs_exclusive": (
                            "P95 execution span / Exclusive"
                        ),
                    },
                )
            )

        figures = [
            (
                "Makespan",
                trace_dir / "makespan_comparison.png",
            ),
            (
                "Job completion time",
                trace_dir / "jct_comparison.png",
            ),
            (
                "Initial queue wait",
                trace_dir / "queue_wait_comparison.png",
            ),
            (
                "Execution span",
                trace_dir / "execution_time_comparison.png",
            ),
            (
                "Normalized JCT ECDF",
                trace_dir / "normalized_jct_ecdf.png",
            ),
            (
                "Completion progress",
                trace_dir / "completion_progress.png",
            ),
        ]

        for title, figure_path in figures:
            if figure_path.is_file():
                lines.extend(
                    [
                        "",
                        f"### {title}",
                        "",
                        f"![{title}]"
                        f"({relative_markdown_path(target=figure_path, report_dir=output_dir)})",
                    ]
                )

        recovery_summary_path = (
            trace_dir
            / "recovery"
            / "recovery_policy_summary.csv"
        )

        if recovery_summary_path.is_file():
            recovery = pd.read_csv(
                recovery_summary_path
            )

            lines.extend(
                [
                    "",
                    "### Recovery cost",
                    "",
                ]
            )

            lines.append(
                markdown_table(
                    recovery,
                    columns=[
                        "run_label",
                        "jobs_with_failed_attempts",
                        "recovered_job_count",
                        "recovery_stopped_job_count",
                        "failed_attempt_count",
                        "recovery_queue_wait_mean_s",
                        "recovery_queue_wait_p95_s",
                        "recovery_queue_wait_max_s",
                        "total_failed_runtime_s",
                        "total_recovery_gap_s",
                        "total_recovery_overhead_s",
                    ],
                    rename={
                        "run_label": "Policy",
                        "jobs_with_failed_attempts": (
                            "Jobs with failures"
                        ),
                        "recovered_job_count": "Recovered jobs",
                        "recovery_stopped_job_count": (
                            "Recovery stopped"
                        ),
                        "failed_attempt_count": (
                            "Failed attempts"
                        ),
                        "recovery_queue_wait_mean_s": (
                            "Mean recovery wait (s)"
                        ),
                        "recovery_queue_wait_p95_s": (
                            "P95 recovery wait (s)"
                        ),
                        "recovery_queue_wait_max_s": (
                            "Max recovery wait (s)"
                        ),
                        "total_failed_runtime_s": (
                            "Lost runtime (s)"
                        ),
                        "total_recovery_gap_s": (
                            "Failure-to-relaunch gap (s)"
                        ),
                        "total_recovery_overhead_s": (
                            "Total recovery overhead (s)"
                        ),
                    },
                )
            )

            recovery_figures = [
                (
                    "Recovered-job cost breakdown",
                    trace_dir
                    / "recovery"
                    / "recovered_job_cost_breakdown.png",
                ),
                (
                    "Policy recovery cost",
                    trace_dir
                    / "recovery"
                    / "policy_recovery_cost.png",
                ),
            ]

            for title, figure_path in recovery_figures:
                if figure_path.is_file():
                    lines.extend(
                        [
                            "",
                            f"#### {title}",
                            "",
                            f"![{title}]"
                            f"({relative_markdown_path(target=figure_path, report_dir=output_dir)})",
                        ]
                    )

    incomplete = validation_frame[
        validation_frame["status"] != "complete"
    ]

    if not incomplete.empty:
        lines.extend(
            [
                "",
                "## Pending or unsuccessful runs",
                "",
            ]
        )

        lines.append(
            markdown_table(
                incomplete,
                columns=[
                    "trace_name",
                    "configuration_label",
                    "status",
                    "return_code",
                    "timed_out",
                ],
                rename={
                    "trace_name": "Trace",
                    "configuration_label": "Configuration",
                    "status": "Status",
                    "return_code": "Return code",
                    "timed_out": "Timed out",
                },
            )
        )

    report_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote: {report_path}")


def print_status_summary(frame: pd.DataFrame) -> None:
    print("\n===== Evaluation status =====")

    summary = (
        frame.groupby(
            ["trace_name", "status"],
            dropna=False,
        )
        .size()
        .unstack(fill_value=0)
    )

    print(summary.to_string())

    mismatches = frame[
        (frame["status"] != "missing")
        & (~frame["configuration_matches"])
    ]

    if not mismatches.empty:
        print("\nWARNING: configuration mismatches detected:")
        print(
            mismatches[
                [
                    "trace_name",
                    "configuration_label",
                    "expected_policy",
                    "actual_policy",
                    "expected_estimator",
                    "actual_estimator",
                    "trace_csv",
                ]
            ].to_string(index=False)
        )


def main() -> int:
    args = parse_args()
    manifest = load_yaml(args.manifest)

    experiment_name = str(manifest["experiment_name"])

    manifest_results_dir = Path(
        manifest.get("runner", {}).get(
            "results_dir",
            "evaluation/experiments/results",
        )
    )

    results_dir = (
        args.results_dir
        if args.results_dir is not None
        else manifest_results_dir
    )

    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else results_dir / f"{experiment_name}_analysis"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    rows = build_validation_rows(
        manifest=manifest,
        results_dir=results_dir,
    )

    frame = pd.DataFrame(rows).sort_values(
        [
            "trace_name",
            "repetition",
            "configuration_label",
        ]
    )

    output_path = output_dir / "validation_report.csv"
    frame.to_csv(output_path, index=False)

    print_status_summary(frame)

    if args.refresh:
        refresh_completed_summaries(frame)

    collect_completed_run_summaries(
        validation_frame=frame,
        output_dir=output_dir,
    )

    generate_per_trace_comparisons(
        validation_frame=frame,
        output_dir=output_dir,
    )

    generate_per_trace_performance_tables(
        validation_frame=frame,
        output_dir=output_dir,
    )

    generate_cross_trace_analysis(
        validation_frame=frame,
        output_dir=output_dir,
    )

    generate_recovery_analysis(
        validation_frame=frame,
        output_dir=output_dir,
    )

    generate_markdown_report(
        validation_frame=frame,
        output_dir=output_dir,
    )

    print(f"\nWrote: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
