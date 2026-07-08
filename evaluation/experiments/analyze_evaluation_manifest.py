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


POLICY_DISPLAY_NAMES = {
    "exclusive": "Exclusive",
    "oracle-MAGM": "AEGIS + ProfiledPeakMem",
    "OR-MAGM": "AEGIS - EstimatorFree",
    "EST-MAGM__horus": "AEGIS + AnalyticalMemEst",
    "HORUS__horus": "Horus",
    "LUCID": "Lucid",
    "PROFILED-MAGM": "Profiled-MFM",
}


POLICY_DISPLAY_ORDER = {
    "Exclusive": 0,
    "AEGIS + ProfiledPeakMem": 1,
    "AEGIS - EstimatorFree": 2,
    "AEGIS + AnalyticalMemEst": 3,
    "Horus": 4,
    "Lucid": 5,
    "Profiled-MFM": 6,
}


def policy_display_name(run_label: object) -> str:
    raw = str(run_label)
    display_names = {
        **POLICY_DISPLAY_NAMES,
        "aegis_magm_thresholded": "AEGIS-MAGM",
        "aegis_lug_thresholded": "AEGIS-LUG",
        "aegis_magm_no_thresholds": "AEGIS-MAGM no thresholds",
        "aegis_lug_no_thresholds": "AEGIS-LUG no thresholds",
    }
    return display_names.get(raw, raw.replace("MAGM", "MFM"))


def policy_sort_order(run_label: object) -> int:
    raw = str(run_label)
    explicit_order = {
        "exclusive": 0,
        "aegis_magm_thresholded": 1,
        "aegis_lug_thresholded": 2,
        "aegis_magm_no_thresholds": 3,
        "aegis_lug_no_thresholds": 4,
    }
    if raw in explicit_order:
        return explicit_order[raw]
    display = policy_display_name(run_label)
    return POLICY_DISPLAY_ORDER.get(display, 100)



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
        if "run_label" in summary.columns:
            summary["run_label"] = record.configuration_label

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
        trace_output_dir = (
            output_dir
            / "traces"
            / str(trace_name)
        )
        trace_output_dir.mkdir(parents=True, exist_ok=True)

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

            jobs = pd.read_csv(path).copy()
            jobs["configuration_label"] = record.configuration_label
            jobs["run_label"] = record.configuration_label

            relabeled_path = (
                trace_output_dir
                / f"job_metrics__{record.configuration_label}.csv"
            )
            jobs.to_csv(relabeled_path, index=False)
            job_metric_paths.append(relabeled_path)


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
            if "run_label" in summary.columns:
                summary["run_label"] = record.configuration_label
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
            "total_queue_wait_mean_s",
            "total_queue_wait_p50_s",
            "total_queue_wait_p95_s",
            "jct_mean_s",
            "jct_p50_s",
            "jct_p95_s",
            "total_execution_time_mean_s",
            "execution_span_p50_s",
            "total_execution_time_p95_s",
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
            "total_queue_wait_mean_s",
            "total_queue_wait_p50_s",
            "total_queue_wait_p95_s",
            "jct_mean_s",
            "jct_p50_s",
            "jct_p95_s",
            "total_execution_time_mean_s",
            "execution_span_p50_s",
            "total_execution_time_p95_s",
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
            "total_queue_wait_mean_s",
            "total_queue_wait_mean_s_vs_exclusive",
            "total_queue_wait_p95_s",
            "total_queue_wait_p95_s_vs_exclusive",
            "jct_mean_s",
            "jct_mean_s_vs_exclusive",
            "jct_p95_s",
            "jct_p95_s_vs_exclusive",
            "total_execution_time_mean_s",
            "total_execution_time_mean_s_vs_exclusive",
            "total_execution_time_p95_s",
            "total_execution_time_p95_s_vs_exclusive",
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
            mean_column="total_queue_wait_mean_s",
            tail_column="total_queue_wait_p95_s",
            mean_label="Mean wait",
            tail_label="P95 wait",
            y_label="Initial queue wait (seconds)",
            output_dir=trace_output,
            output_stem="total_queue_wait_comparison",
        )

        plot_grouped_metric_bars(
            frame=performance,
            mean_column="total_execution_time_mean_s",
            tail_column="total_execution_time_p95_s",
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
    prepared = frame.copy()
    prepared["policy_display"] = prepared["run_label"].map(
        policy_display_name
    )
    prepared["_order"] = prepared["run_label"].map(
        policy_sort_order
    )

    return prepared.sort_values(
        ["_order", "policy_display", "run_label"]
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
        prepared["policy_display"],
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
        prepared["policy_display"],
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


CROSS_TRACE_METRICS = [
    (
        "makespan_s_vs_exclusive",
        "Normalized makespan",
        "normalized_makespan_by_trace",
    ),
    (
        "jct_mean_s_vs_exclusive",
        "Normalized mean JCT",
        "normalized_mean_jct_by_trace",
    ),
    (
        "jct_p95_s_vs_exclusive",
        "Normalized P95 JCT",
        "normalized_p95_jct_by_trace",
    ),
    (
        "total_queue_wait_mean_s_vs_exclusive",
        "Normalized mean total queue wait",
        "normalized_mean_total_queue_wait_by_trace",
    ),
    (
        "total_queue_wait_p95_s_vs_exclusive",
        "Normalized P95 total queue wait",
        "normalized_p95_total_queue_wait_by_trace",
    ),
    (
        "total_execution_time_mean_s_vs_exclusive",
        "Normalized mean total execution time",
        "normalized_mean_total_execution_time_by_trace",
    ),
    (
        "total_execution_time_p95_s_vs_exclusive",
        "Normalized P95 total execution time",
        "normalized_p95_total_execution_time_by_trace",
    ),
]


def build_cross_trace_metric_table(
    *,
    combined: pd.DataFrame,
    value_column: str,
) -> pd.DataFrame:
    pivot = combined.pivot_table(
        index="run_label",
        columns="trace_name",
        values=value_column,
        aggfunc="first",
    )

    pivot = pivot.reset_index()

    trace_columns = [
        column
        for column in pivot.columns
        if column != "run_label"
    ]

    pivot["geomean"] = pivot[trace_columns].apply(
        lambda row: geometric_mean(row),
        axis=1,
    )

    return _ordered_policy_frame(pivot).drop(
        columns=["_order"],
        errors="ignore",
    )


def generate_cross_trace_analysis(
    *,
    validation_frame: pd.DataFrame,
    output_dir: Path,
) -> None:
    completed = validation_frame[
        validation_frame["status"] == "complete"
    ]

    completed_trace_names = sorted(
        completed["trace_name"].dropna().unique()
    )

    frames: list[pd.DataFrame] = []

    for trace_name in completed_trace_names:
        summary_path = (
            output_dir
            / "traces"
            / str(trace_name)
            / "normalized_performance_summary.csv"
        )

        if not summary_path.is_file():
            continue

        frame = pd.read_csv(summary_path).copy()
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

    trace_count = int(
        combined["trace_name"].nunique()
    )

    if trace_count < 2:
        print(
            "\nCross-trace aggregation skipped: "
            f"only {trace_count} trace is complete."
        )
        return

    tables_dir = output_dir / "cross_trace_tables"
    figures_dir = output_dir / "figures"

    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    aggregate_rows = []

    for value_column, label, output_stem in CROSS_TRACE_METRICS:
        table = build_cross_trace_metric_table(
            combined=combined,
            value_column=value_column,
        )

        table_path = tables_dir / f"{output_stem}.csv"
        table.to_csv(table_path, index=False)

        plot_cross_trace_metric(
            table=table,
            metric_label=label,
            output_dir=figures_dir,
            output_stem=output_stem,
        )

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

        for value_column, _, _ in CROSS_TRACE_METRICS:
            row[
                f"{value_column}_geomean"
            ] = geometric_mean(
                group[value_column]
            )

        makespan_ratio = row[
            "makespan_s_vs_exclusive_geomean"
        ]

        row[
            "makespan_reduction_percent_from_geomean"
        ] = (
            (1.0 - makespan_ratio) * 100.0
            if np.isfinite(makespan_ratio)
            else np.nan
        )

        aggregate_rows.append(row)

    aggregate = pd.DataFrame(aggregate_rows)

    aggregate = _ordered_policy_frame(
        aggregate
    ).drop(
        columns=["_order"],
        errors="ignore",
    )

    aggregate_path = (
        output_dir
        / "aggregate_policy_summary.csv"
    )
    aggregate.to_csv(aggregate_path, index=False)

    print(
        "\nWrote cross-trace analysis:"
        f"\n  {combined_path}"
        f"\n  {aggregate_path}"
        f"\n  {tables_dir}"
    )


def plot_cross_trace_metric(
    *,
    table: pd.DataFrame,
    metric_label: str,
    output_dir: Path,
    output_stem: str,
) -> None:
    prepared = table.copy()
    prepared["policy_display"] = prepared["run_label"].map(
        policy_display_name
    )
    prepared["_order"] = prepared["run_label"].map(
        policy_sort_order
    )
    prepared = prepared.sort_values(
        ["_order", "policy_display", "run_label"]
    )

    value_columns = [
        column
        for column in prepared.columns
        if column not in {"run_label", "policy_display", "_order"}
    ]

    x = np.arange(len(prepared))
    total_width = 0.82
    width = total_width / max(
        len(value_columns),
        1,
    )

    figure, axis = plt.subplots(
        figsize=(
            max(8.4, len(prepared) * 1.45),
            5.3,
        )
    )

    color_cycle = [
        "#0072B2",  # blue
        "#E69F00",  # orange
        "#009E73",  # bluish green
        "#D55E00",  # vermillion
        "#CC79A7",  # reddish purple
        "#56B4E9",  # sky blue
    ]
    hatch_cycle = [
        "",
        "//",
        "\\\\",
        "xx",
        "..",
        "--",
    ]

    for index, column in enumerate(value_columns):
        offset = (
            index
            - (len(value_columns) - 1) / 2
        ) * width

        label = (
            "GeoMean"
            if column == "geomean"
            else str(column).capitalize()
        )

        axis.bar(
            x + offset,
            prepared[column],
            width,
            label=label,
            color=color_cycle[index % len(color_cycle)],
            edgecolor="black",
            linewidth=0.9,
            hatch=hatch_cycle[index % len(hatch_cycle)],
        )

    axis.axhline(
        1.0,
        linestyle="--",
        linewidth=1.6,
        color="black",
        label="Exclusive baseline",
    )

    axis.set_xticks(x)
    axis.set_xticklabels(
        prepared["policy_display"],
        rotation=25,
        ha="right",
        fontsize=13,
    )
    axis.set_ylabel(metric_label, fontsize=15)
    axis.set_xlabel("Policy", fontsize=15)
    axis.set_ylim(bottom=0)
    axis.tick_params(axis="y", labelsize=13, width=1.3)
    axis.tick_params(axis="x", width=1.3)
    axis.grid(True, axis="y", alpha=0.30, linestyle=":")

    for spine in axis.spines.values():
        spine.set_linewidth(1.3)

    axis.legend(
        fontsize=11,
        frameon=True,
        ncols=min(len(value_columns) + 1, 4),
        loc="upper center",
        bbox_to_anchor=(0.5, 1.24),
    )

    figure.subplots_adjust(top=0.78)

    save_figure(
        figure,
        output_dir,
        output_stem,
    )



def plot_queue_execution_tradeoff(
    *,
    output_dir: Path,
) -> None:
    tables_dir = output_dir / "cross_trace_tables"
    figures_dir = output_dir / "figures"

    queue_mean_path = tables_dir / "normalized_mean_total_queue_wait_by_trace.csv"
    queue_p95_path = tables_dir / "normalized_p95_total_queue_wait_by_trace.csv"
    execution_mean_path = (
        tables_dir / "normalized_mean_total_execution_time_by_trace.csv"
    )
    execution_p95_path = (
        tables_dir / "normalized_p95_total_execution_time_by_trace.csv"
    )

    required_paths = [
        queue_mean_path,
        queue_p95_path,
        execution_mean_path,
        execution_p95_path,
    ]
    missing_paths = [
        path
        for path in required_paths
        if not path.is_file()
    ]
    if missing_paths:
        print(
            "Skipping queue/execution trade-off figure; "
            "missing required tables: "
            + ", ".join(str(path) for path in missing_paths)
        )
        return

    def load_geomean(
        csv_path: Path,
        value_name: str,
    ) -> pd.DataFrame:
        frame = pd.read_csv(csv_path)
        required_columns = {
            "run_label",
            "policy_display",
            "geomean",
        }
        missing_columns = required_columns - set(frame.columns)
        if missing_columns:
            raise ValueError(
                f"{csv_path}: missing columns "
                f"{sorted(missing_columns)}"
            )

        return frame[
            [
                "run_label",
                "policy_display",
                "geomean",
            ]
        ].rename(
            columns={
                "geomean": value_name,
            }
        )

    def merge_mean_and_p95(
        *,
        mean_path: Path,
        p95_path: Path,
    ) -> pd.DataFrame:
        mean_frame = load_geomean(mean_path, "Mean")
        p95_frame = load_geomean(p95_path, "p95")

        merged = mean_frame.merge(
            p95_frame[
                [
                    "run_label",
                    "p95",
                ]
            ],
            on="run_label",
            how="inner",
        )
        merged["_order"] = merged["policy_display"].map(
            POLICY_DISPLAY_ORDER
        ).fillna(100)

        return merged.sort_values(
            [
                "_order",
                "policy_display",
                "run_label",
            ]
        )

    queue_frame = merge_mean_and_p95(
        mean_path=queue_mean_path,
        p95_path=queue_p95_path,
    )
    execution_frame = merge_mean_and_p95(
        mean_path=execution_mean_path,
        p95_path=execution_p95_path,
    )

    figure, axes = plt.subplots(
        1,
        2,
        figsize=(13.5, 5.2),
        sharey=False,
    )

    bar_specs = [
        ("Mean", "#0072B2", ""),
        ("p95", "#D55E00", "//"),
    ]

    def draw_panel(
        *,
        axis: plt.Axes,
        frame: pd.DataFrame,
        title: str,
        y_label: str,
    ) -> None:
        x = np.arange(len(frame))
        width = 0.36

        for index, (column, color, hatch) in enumerate(bar_specs):
            offset = (
                index
                - (len(bar_specs) - 1) / 2
            ) * width

            axis.bar(
                x + offset,
                frame[column],
                width,
                label=column,
                color=color,
                edgecolor="black",
                linewidth=0.9,
                hatch=hatch,
            )

        axis.axhline(
            1.0,
            linestyle="--",
            linewidth=1.5,
            color="black",
            label="Exclusive baseline",
        )

        axis.set_title(title, fontsize=16)
        axis.set_ylabel(y_label, fontsize=15)
        axis.set_xticks(x)
        axis.set_xticklabels(
            frame["policy_display"],
            rotation=28,
            ha="right",
            fontsize=11,
        )
        axis.set_ylim(bottom=0)
        axis.grid(
            True,
            axis="y",
            linestyle=":",
            alpha=0.30,
        )
        axis.tick_params(
            axis="both",
            width=1.3,
            labelsize=12,
        )

        for spine in axis.spines.values():
            spine.set_linewidth(1.3)

    draw_panel(
        axis=axes[0],
        frame=queue_frame,
        title="Total queue time",
        y_label="Normalized total queue time",
    )
    draw_panel(
        axis=axes[1],
        frame=execution_frame,
        title="Execution span",
        y_label="Normalized total execution time",
    )

    handles, labels = axes[1].get_legend_handles_labels()
    unique = dict(zip(labels, handles))

    figure.legend(
        unique.values(),
        unique.keys(),
        loc="upper center",
        ncols=3,
        frameon=True,
        bbox_to_anchor=(0.5, 1.04),
        fontsize=12,
    )

    figure.tight_layout(rect=(0, 0, 1, 0.96))

    save_figure(
        figure,
        figures_dir,
        "normalized_total_queue_execution_tradeoff",
    )


def plot_cross_trace_mean_with_p95_markers(
    *,
    output_dir: Path,
    mean_stem: str,
    p95_stem: str,
    output_stem: str,
    y_label: str,
) -> None:
    tables_dir = output_dir / "cross_trace_tables"
    figures_dir = output_dir / "figures"

    mean_path = tables_dir / f"{mean_stem}.csv"
    p95_path = tables_dir / f"{p95_stem}.csv"

    missing_paths = [
        path
        for path in [mean_path, p95_path]
        if not path.is_file()
    ]
    if missing_paths:
        print(
            f"Skipping {output_stem}; missing required tables: "
            + ", ".join(str(path) for path in missing_paths)
        )
        return

    mean_table = pd.read_csv(mean_path).copy()
    p95_table = pd.read_csv(p95_path).copy()

    if "policy_display" not in mean_table.columns:
        mean_table["policy_display"] = mean_table["run_label"].map(
            policy_display_name
        )
    if "policy_display" not in p95_table.columns:
        p95_table["policy_display"] = p95_table["run_label"].map(
            policy_display_name
        )

    mean_table["_order"] = mean_table["policy_display"].map(
        POLICY_DISPLAY_ORDER
    ).fillna(100)

    mean_table = mean_table.sort_values(
        [
            "_order",
            "policy_display",
            "run_label",
        ]
    )

    p95_lookup = p95_table.set_index("run_label")

    value_columns = [
        column
        for column in mean_table.columns
        if column not in {
            "run_label",
            "policy_display",
            "_order",
        }
    ]

    x = np.arange(len(mean_table))
    total_width = 0.82
    width = total_width / max(
        len(value_columns),
        1,
    )

    figure, axis = plt.subplots(
        figsize=(
            max(8.4, len(mean_table) * 1.45),
            5.4,
        )
    )

    color_cycle = [
        "#0072B2",  # blue
        "#E69F00",  # orange
        "#009E73",  # bluish green
        "#D55E00",  # vermillion
        "#CC79A7",  # reddish purple
        "#56B4E9",  # sky blue
    ]
    hatch_cycle = [
        "",
        "//",
        "\\\\",
        "xx",
        "..",
        "--",
    ]

    for index, column in enumerate(value_columns):
        offset = (
            index
            - (len(value_columns) - 1) / 2
        ) * width

        label = (
            "GeoMean"
            if column == "geomean"
            else str(column).capitalize()
        )

        bar_x = x + offset
        mean_values = mean_table[column].to_numpy(dtype=float)

        axis.bar(
            bar_x,
            mean_values,
            width,
            label=f"{label} mean",
            color=color_cycle[index % len(color_cycle)],
            edgecolor="black",
            linewidth=0.9,
            hatch=hatch_cycle[index % len(hatch_cycle)],
        )

        p95_values = []
        for run_label in mean_table["run_label"]:
            if run_label not in p95_lookup.index:
                p95_values.append(np.nan)
            else:
                p95_values.append(
                    float(p95_lookup.loc[run_label, column])
                )

        axis.scatter(
            bar_x,
            p95_values,
            marker="D",
            s=42,
            color="black",
            edgecolor="white",
            linewidth=0.7,
            zorder=5,
            label="p95" if index == 0 else None,
        )

    axis.axhline(
        1.0,
        linestyle="--",
        linewidth=1.6,
        color="black",
        label="Exclusive baseline",
    )

    axis.set_xticks(x)
    axis.set_xticklabels(
        mean_table["policy_display"],
        rotation=25,
        ha="right",
        fontsize=13,
    )
    axis.set_ylabel(y_label, fontsize=15)
    axis.set_xlabel("Policy", fontsize=15)
    axis.set_ylim(bottom=0)
    axis.tick_params(axis="y", labelsize=13, width=1.3)
    axis.tick_params(axis="x", width=1.3)
    axis.grid(True, axis="y", alpha=0.30, linestyle=":")

    for spine in axis.spines.values():
        spine.set_linewidth(1.3)

    axis.legend(
        fontsize=11,
        frameon=True,
        ncols=3,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.24),
    )

    figure.subplots_adjust(top=0.78)

    save_figure(
        figure,
        figures_dir,
        output_stem,
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
            if "run_label" in frame.columns:
                frame["run_label"] = record.configuration_label
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

    prepared["policy_display"] = prepared["run_label"].map(
        policy_display_name
    )
    prepared["_order"] = prepared["run_label"].map(
        policy_sort_order
    )
    prepared = prepared.sort_values(
        ["_order", "policy_display", "run_label"]
    )

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
        prepared["policy_display"],
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

    lines.extend(
        [
            "",
            "## Cross-trace comparison",
            "",
        ]
    )

    completed_trace_count = int(
        validation_frame.loc[
            validation_frame["status"] == "complete",
            "trace_name",
        ].nunique()
    )

    if completed_trace_count < 2:
        lines.extend(
            [
                (
                    "Cross-trace aggregation is not shown because "
                    f"only {completed_trace_count} trace is complete."
                ),
                "",
                (
                    "See the trace-specific raw and normalized "
                    "results below."
                ),
            ]
        )
    else:
        lines.extend(
            [
                (
                    "Each table reports every completed trace "
                    "separately. GeoMean summarizes normalized "
                    "ratios across traces; lower is better."
                ),
                "",
            ]
        )

        table_specs = [
            (
                "Normalized makespan",
                "normalized_makespan_by_trace.csv",
            ),
            (
                "Normalized mean JCT",
                "normalized_mean_jct_by_trace.csv",
            ),
            (
                "Normalized P95 JCT",
                "normalized_p95_jct_by_trace.csv",
            ),
            (
                "Normalized mean total queue wait",
                "normalized_mean_total_queue_wait_by_trace.csv",
            ),
            (
                "Normalized P95 total queue wait",
                "normalized_p95_total_queue_wait_by_trace.csv",
            ),
            (
                "Normalized mean total execution time",
                "normalized_mean_total_execution_time_by_trace.csv",
            ),
            (
                "Normalized P95 total execution time",
                "normalized_p95_total_execution_time_by_trace.csv",
            ),
        ]

        for title, filename in table_specs:
            table_path = (
                output_dir
                / "cross_trace_tables"
                / filename
            )

            if not table_path.is_file():
                continue

            table = pd.read_csv(table_path)
            table_display = table.copy()
            if "run_label" in table_display.columns:
                table_display["run_label"] = table_display[
                    "run_label"
                ].map(policy_display_name)

            rename = {
                "run_label": "Policy",
                "geomean": "GeoMean",
            }

            for column in table.columns:
                if column not in rename:
                    rename[column] = str(column).capitalize()

            lines.extend(
                [
                    f"### {title}",
                    "",
                    markdown_table(
                        table_display,
                        columns=list(table_display.columns),
                        rename=rename,
                    ),
                    "",
                ]
            )

            figure_path = (
                output_dir
                / "figures"
                / filename.replace(".csv", ".png")
            )

            if figure_path.is_file():
                lines.extend(
                    [
                        f"![{title}]"
                        f"({relative_markdown_path(target=figure_path, report_dir=output_dir)})",
                        "",
                    ]
                )

    lines.extend(
        [
            "",
            "## Cross-trace queue and execution-time summary",
            "",
            "Total queue time is initial queue wait plus recovery queue wait. "
            "Total execution time is the sum of all attempt runtimes, including failed attempts before recovery.",
            "",
        ]
    )

    marker_figures = [
        (
            output_dir / "figures" / "normalized_jct_mean_bars_p95_markers_by_trace.png",
            "Normalized JCT with P95 markers",
        ),
        (
            output_dir / "figures" / "normalized_total_queue_wait_mean_bars_p95_markers_by_trace.png",
            "Normalized total queue wait with P95 markers",
        ),
        (
            output_dir / "figures" / "normalized_total_execution_time_mean_bars_p95_markers_by_trace.png",
            "Normalized total execution time with P95 markers",
        ),
    ]

    for figure_path, title in marker_figures:
        if figure_path.is_file():
            lines.extend(
                [
                    f"![{title}]"
                    f"({relative_markdown_path(target=figure_path, report_dir=output_dir)})",
                    "",
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
        performance_display = performance.copy()
        if "run_label" in performance_display.columns:
            performance_display["run_label"] = performance_display[
                "run_label"
            ].map(policy_display_name)

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
                performance_display,
                columns=[
                    "run_label",
                    "completion_fraction",
                    "makespan_s",
                    "total_queue_wait_mean_s",
                    "total_queue_wait_p95_s",
                    "jct_mean_s",
                    "jct_p95_s",
                    "total_execution_time_mean_s",
                    "total_execution_time_p95_s",
                    "successful_attempt_runtime_mean_s",
                    "failed_attempt_count",
                    "recovered_attempt_count",
                ],
                rename={
                    "run_label": "Policy",
                    "completion_fraction": "Completion",
                    "makespan_s": "Makespan (s)",
                    "total_queue_wait_mean_s": "Mean total wait (s)",
                    "total_queue_wait_p95_s": "P95 total wait (s)",
                    "jct_mean_s": "Mean JCT (s)",
                    "jct_p95_s": "P95 JCT (s)",
                    "total_execution_time_mean_s": (
                        "Mean total execution time (s)"
                    ),
                    "total_execution_time_p95_s": (
                        "P95 total execution time (s)"
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
            normalized_display = normalized.copy()
            if "run_label" in normalized_display.columns:
                normalized_display["run_label"] = normalized_display[
                    "run_label"
                ].map(policy_display_name)

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
                    normalized_display,
                    columns=[
                        "run_label",
                        "makespan_s_vs_exclusive",
                        "makespan_reduction_percent",
                        "jct_mean_s_vs_exclusive",
                        "jct_p95_s_vs_exclusive",
                        "total_queue_wait_mean_s_vs_exclusive",
                        "total_queue_wait_p95_s_vs_exclusive",
                        "total_execution_time_mean_s_vs_exclusive",
                        "total_execution_time_p95_s_vs_exclusive",
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
                        "total_queue_wait_mean_s_vs_exclusive": (
                            "Mean wait / Exclusive"
                        ),
                        "total_queue_wait_p95_s_vs_exclusive": (
                            "P95 wait / Exclusive"
                        ),
                        "total_execution_time_mean_s_vs_exclusive": (
                            "Mean total execution time / Exclusive"
                        ),
                        "total_execution_time_p95_s_vs_exclusive": (
                            "P95 total execution time / Exclusive"
                        ),
                    },
                )
            )

        figures = [
            (
                "Normalized makespan by policy",
                trace_dir / "makespan_comparison.png",
            ),
            (
                "Job completion time by policy",
                trace_dir / "jct_comparison.png",
            ),
            (
                "Queueing time by policy",
                trace_dir / "total_queue_wait_comparison.png",
            ),
            (
                "Execution time by policy",
                trace_dir / "execution_time_comparison.png",
            ),
            (
                "Per-job normalized JCT distribution",
                trace_dir / "normalized_jct_ecdf.png",
            ),
            (
                "Trace completion progress",
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
            recovery_display = recovery.copy()
            if "run_label" in recovery_display.columns:
                recovery_display["run_label"] = recovery_display[
                    "run_label"
                ].map(policy_display_name)

            lines.extend(
                [
                    "",
                    "### Recovery cost",
                    "",
                ]
            )

            lines.append(
                markdown_table(
                    recovery_display,
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

    plot_cross_trace_mean_with_p95_markers(
        output_dir=output_dir,
        mean_stem="normalized_mean_jct_by_trace",
        p95_stem="normalized_p95_jct_by_trace",
        output_stem="normalized_jct_mean_bars_p95_markers_by_trace",
        y_label="Normalized JCT",
    )

    plot_cross_trace_mean_with_p95_markers(
        output_dir=output_dir,
        mean_stem="normalized_mean_total_queue_wait_by_trace",
        p95_stem="normalized_p95_total_queue_wait_by_trace",
        output_stem="normalized_total_queue_wait_mean_bars_p95_markers_by_trace",
        y_label="Normalized total queue wait",
    )

    plot_cross_trace_mean_with_p95_markers(
        output_dir=output_dir,
        mean_stem="normalized_mean_total_execution_time_by_trace",
        p95_stem="normalized_p95_total_execution_time_by_trace",
        output_stem="normalized_total_execution_time_mean_bars_p95_markers_by_trace",
        y_label="Normalized total execution time",
    )

    plot_queue_execution_tradeoff(
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
