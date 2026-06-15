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

    generate_recovery_analysis(
        validation_frame=frame,
        output_dir=output_dir,
    )

    print(f"\nWrote: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
