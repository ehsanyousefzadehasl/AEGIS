#!/usr/bin/env python3
"""Build the AEGIS memory-estimator sensitivity report.

One command refreshes summaries, validates runs, generates CSV tables, bar
figures, old-style distribution figures, and the Markdown report.

Default command:
    python evaluation/experiments/analyze_estimator_sensitivity.py --refresh
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import yaml


METRICS = [
    "makespan_s",
    "mean_jct_s",
    "p50_jct_s",
    "p95_jct_s",
    "mean_queue_wait_s",
    "p95_queue_wait_s",
    "mean_execution_time_s",
    "p95_execution_time_s",
]

SUMMARY_ALIASES = {
    "makespan_s": ["makespan_s", "makespan"],
    "mean_jct_s": ["mean_jct_s", "jct_mean_s", "mean_jct"],
    "p50_jct_s": ["p50_jct_s", "jct_p50_s", "median_jct_s", "p50_jct", "median_jct"],
    "p95_jct_s": ["p95_jct_s", "jct_p95_s", "p95_jct"],
    "mean_queue_wait_s": [
        "mean_queue_wait_s",
        "total_queue_wait_mean_s",
        "initial_queue_wait_mean_s",
        "mean_queue_wait",
    ],
    "p95_queue_wait_s": [
        "p95_queue_wait_s",
        "total_queue_wait_p95_s",
        "initial_queue_wait_p95_s",
        "p95_queue_wait",
    ],
    "mean_execution_time_s": [
        "mean_execution_time_s",
        "total_execution_time_mean_s",
        "execution_span_mean_s",
        "mean_execution_span",
    ],
    "p95_execution_time_s": [
        "p95_execution_time_s",
        "total_execution_time_p95_s",
        "execution_span_p95_s",
        "p95_execution_span",
    ],
}

DEFAULT_SOLO_PROFILES = [
    Path("evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv"),
    Path("evaluation/profiling/solo/extracted/solo_profile_results_2gpu.csv"),
]

ESTIMATOR_ORDER = [
    "Exclusive",
    "AEGIS+PeakMem",
    "AEGIS+HorusMem",
    "AEGIS+FakeTensorMem",
    "AEGIS+GPUMemNet",
]


def sort_key(label: str) -> tuple[int, str]:
    try:
        return ESTIMATOR_ORDER.index(label), label
    except ValueError:
        return len(ESTIMATOR_ORDER), label


def geomean(values: pd.Series) -> float:
    clean = [
        float(value)
        for value in values.dropna()
        if float(value) > 0 and math.isfinite(float(value))
    ]
    if not clean:
        return float("nan")
    return math.exp(sum(math.log(value) for value in clean) / len(clean))


def count_events(root: Path) -> tuple[Counter, Path | None]:
    event_files = sorted(root.rglob("events*.jsonl"))
    if not event_files:
        return Counter(), None

    event_file = event_files[-1]
    counter: Counter[str] = Counter()

    with event_file.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            counter[event.get("event", "unknown")] += 1

    return counter, event_file


def find_latest_run_dir(root: Path) -> Path | None:
    metadata_files = sorted(root.glob("*/**/metadata.json"))
    if not metadata_files:
        return None
    return metadata_files[-1].parent


def read_run_summary(root: Path) -> dict[str, Any]:
    summary_path = root / "analysis" / "run_summary.csv"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"Missing {summary_path}. Run with --refresh first."
        )

    frame = pd.read_csv(summary_path)
    if frame.empty:
        raise ValueError(f"Empty summary file: {summary_path}")

    return frame.iloc[0].to_dict()


def first_available(row: dict[str, Any], candidates: list[str]) -> Any:
    for candidate in candidates:
        if candidate in row and not pd.isna(row[candidate]):
            return row[candidate]
    return float("nan")


def load_manifest(manifest_path: Path) -> list[tuple[str, dict[str, Any]]]:
    data = yaml.safe_load(manifest_path.read_text())

    items: list[tuple[str, dict[str, Any]]] = []
    for item in data.get("runs", []):
        items.append(("estimator", item))
    for item in data.get("baselines", []):
        items.append(("baseline", item))

    return items


def refresh_summaries(items: list[tuple[str, dict[str, Any]]]) -> None:
    for _, item in items:
        root = Path(item["root"])

        if not root.exists():
            print(f"SKIP missing root: {root}")
            continue

        print(f"Summarizing: {root}")
        subprocess.run(
            [
                "python",
                "evaluation/experiments/summarize_policy_runs.py",
                "--experiment-root",
                str(root),
            ],
            check=True,
        )


def build_tables(
    items: list[tuple[str, dict[str, Any]]],
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    validation_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for kind, item in items:
        trace = item["trace"]
        label = item["label"]
        estimator = item.get("estimator", "exclusive" if kind == "baseline" else "")
        root = Path(item["root"])

        counter: Counter[str] = Counter()
        event_file: Path | None = None
        run_dir: Path | None = None
        status = "missing"

        if root.exists():
            counter, event_file = count_events(root)
            run_dir = find_latest_run_dir(root)

            if counter["submitted"] > 0 and counter["submitted"] == counter["completed"]:
                status = "complete"
            elif counter["submitted"] > 0:
                status = "incomplete"
            else:
                status = "no_events"

        has_summary = (root / "analysis" / "run_summary.csv").exists()
        has_job_metrics = (root / "analysis" / "job_metrics.csv").exists()

        validation_rows.append(
            {
                "kind": kind,
                "trace": trace,
                "estimator": estimator,
                "label": label,
                "root": str(root),
                "run_dir": str(run_dir) if run_dir else "",
                "event_file": str(event_file) if event_file else "",
                "status": status,
                "has_summary": has_summary,
                "has_job_metrics": has_job_metrics,
                "submitted": int(counter["submitted"]),
                "dispatched": int(counter["dispatched"]),
                "launched": int(counter["launched"]),
                "completed": int(counter["completed"]),
                "failed": int(counter["failed"]),
                "recovered": int(counter["recovered"]),
            }
        )

        if status != "complete":
            continue

        if not has_summary:
            validation_rows[-1]["status"] = "needs_summary"
            continue

        run_summary = read_run_summary(root)

        row: dict[str, Any] = {
            "kind": kind,
            "trace": trace,
            "estimator": estimator,
            "label": label,
            "root": str(root),
            "run_dir": str(run_dir) if run_dir else "",
            "submitted": int(counter["submitted"]),
            "completed": int(counter["completed"]),
            "failed": int(counter["failed"]),
            "recovered": int(counter["recovered"]),
            "completion_rate": (
                float(counter["completed"]) / float(counter["submitted"])
                if counter["submitted"]
                else float("nan")
            ),
        }

        for metric in METRICS:
            row[metric] = first_available(run_summary, SUMMARY_ALIASES[metric])

        summary_rows.append(row)

    validation = pd.DataFrame(validation_rows)
    summary = pd.DataFrame(summary_rows)

    if summary.empty:
        aggregate = pd.DataFrame()
        return validation, summary, aggregate

    normalized = summary.copy()

    for trace, trace_frame in summary.groupby("trace"):
        baseline = trace_frame[
            (trace_frame["kind"] == "baseline") & (trace_frame["label"] == "Exclusive")
        ]
        if baseline.empty:
            continue

        baseline_row = baseline.iloc[0]
        for metric in METRICS:
            base_value = float(baseline_row.get(metric, float("nan")))
            if not math.isfinite(base_value) or base_value <= 0:
                continue

            mask = normalized["trace"] == trace
            normalized.loc[mask, f"normalized_{metric}"] = (
                normalized.loc[mask, metric].astype(float) / base_value
            )

    estimator_rows = normalized[normalized["kind"] == "estimator"].copy()
    aggregate_rows: list[dict[str, Any]] = []

    for label, group in sorted(
        estimator_rows.groupby("label"),
        key=lambda item: sort_key(str(item[0])),
    ):
        row = {
            "label": label,
            "trace_count": group["trace"].nunique(),
            "completion_rate_mean": group["completion_rate"].mean(),
            "failed_total": int(group["failed"].sum()),
            "recovered_total": int(group["recovered"].sum()),
        }

        for metric in METRICS:
            norm_col = f"normalized_{metric}"
            if norm_col in group.columns:
                row[f"geomean_{norm_col}"] = geomean(group[norm_col])

        aggregate_rows.append(row)

    aggregate = pd.DataFrame(aggregate_rows)

    return validation, normalized, aggregate


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()

    png_path = output_dir / f"{stem}.png"
    pdf_path = output_dir / f"{stem}.pdf"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)

    return png_path


def plot_bar_figures(summary: pd.DataFrame, output_dir: Path) -> list[Path]:
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    stale_stems = {
        "actual_makespan_by_estimator",
        "actual_mean_jct_by_estimator",
        "actual_p95_jct_by_estimator",
        "normalized_makespan_by_estimator",
        "normalized_mean_jct_by_estimator",
        "normalized_p95_jct_by_estimator",
    }

    for stale in figures_dir.glob("*"):
        if stale.is_file() and stale.suffix in {".png", ".pdf"} and stale.stem in stale_stems:
            stale.unlink()

    estimator_rows = summary[summary["kind"] == "estimator"].copy()
    if estimator_rows.empty:
        return []

    estimator_rows["label_order"] = estimator_rows["label"].map(lambda label: sort_key(str(label))[0])
    estimator_rows = estimator_rows.sort_values(["label_order", "label", "trace"])

    figure_paths: list[Path] = []

    def bar(metric: str, ylabel: str, stem: str) -> None:
        if metric not in estimator_rows.columns:
            return

        pivot = estimator_rows.pivot_table(
            index="label",
            columns="trace",
            values=metric,
            aggfunc="mean",
        )

        ordered_index = sorted(pivot.index, key=lambda label: sort_key(str(label)))
        pivot = pivot.loc[ordered_index]

        fig, axis = plt.subplots(figsize=(9.2, 4.8))
        pivot.plot(kind="bar", ax=axis, rot=25)

        axis.set_xlabel("AEGIS memory estimator")
        axis.set_ylabel(ylabel)
        axis.set_title(ylabel)
        axis.grid(True, axis="y", alpha=0.3)
        axis.legend(title="Trace")

        figure_paths.append(save_figure(fig, figures_dir, stem))

    bar("makespan_s", "Makespan (s)", "actual_makespan_by_estimator")
    bar("mean_jct_s", "Mean JCT (s)", "actual_mean_jct_by_estimator")
    bar("p95_jct_s", "P95 JCT (s)", "actual_p95_jct_by_estimator")

    bar("normalized_makespan_s", "Normalized makespan", "normalized_makespan_by_estimator")
    bar("normalized_mean_jct_s", "Normalized mean JCT", "normalized_mean_jct_by_estimator")
    bar("normalized_p95_jct_s", "Normalized P95 JCT", "normalized_p95_jct_by_estimator")

    return figure_paths


def run_distribution_plots(
    summary: pd.DataFrame,
    output_dir: Path,
    solo_profiles: list[Path],
) -> dict[str, list[Path]]:
    """Generate old-style distribution figures with plot_policy_distributions.py."""

    trace_outputs: dict[str, list[Path]] = {}

    if summary.empty:
        return trace_outputs

    complete_rows = summary[summary["has_job_metrics_for_plot"] == True].copy() if "has_job_metrics_for_plot" in summary.columns else summary.copy()

    existing_solo_profiles = [path for path in solo_profiles if path.exists()]

    for trace, trace_frame in complete_rows.groupby("trace", sort=True):
        trace_dir = output_dir / "traces" / str(trace)
        trace_dir.mkdir(parents=True, exist_ok=True)

        for stale in trace_dir.glob("*"):
            if stale.is_file() and stale.suffix in {".png", ".pdf", ".csv", ".md"}:
                stale.unlink()

        ordered = trace_frame.copy()
        ordered["label_order"] = ordered["label"].map(lambda label: sort_key(str(label))[0])
        ordered = ordered.sort_values(["label_order", "label"])

        job_metrics = [
            Path(row["root"]) / "analysis" / "job_metrics.csv"
            for _, row in ordered.iterrows()
            if (Path(row["root"]) / "analysis" / "job_metrics.csv").exists()
        ]

        if not job_metrics:
            continue

        command = [
            "python",
            "evaluation/experiments/plot_policy_distributions.py",
            "--job-metrics",
            *[str(path) for path in job_metrics],
            "--output-dir",
            str(trace_dir),
        ]

        if existing_solo_profiles:
            command.extend(
                [
                    "--solo-profiles",
                    *[str(path) for path in existing_solo_profiles],
                ]
            )

        print("Generating distribution figures:", " ".join(command))
        subprocess.run(command, check=True)

        figure_names = [
            "normalized_jct_ecdf.png",
            "jct_ecdf.png",
            "queue_wait_ecdf.png",
            "completion_curve.png",
        ]

        trace_outputs[str(trace)] = [
            trace_dir / name
            for name in figure_names
            if (trace_dir / name).exists()
        ]

    return trace_outputs



def unique_task_files_from_summary(summary: pd.DataFrame) -> list[Path]:
    """Return unique workload YAMLs seen in completed runs."""

    task_files: set[str] = set()

    if summary.empty or "root" not in summary.columns:
        return []

    for root_value in summary["root"].dropna().unique():
        job_metrics_path = Path(str(root_value)) / "analysis" / "job_metrics.csv"
        if not job_metrics_path.exists():
            continue

        frame = pd.read_csv(job_metrics_path)
        if "task_file" not in frame.columns:
            continue

        for task_file in frame["task_file"].dropna().unique():
            task_files.add(str(task_file))

    return [Path(value) for value in sorted(task_files)]


def analyze_memory_estimator_behavior(
    summary: pd.DataFrame,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, list[Path]]:
    """Compare YAML estimator values against measured profile peak memory.

    The reference is profile.peak_memory_mib from each workload YAML. This is
    measured solo peak memory used only to evaluate memory-estimation behavior.
    It is not a performance oracle.
    """

    rows: list[dict[str, Any]] = []
    task_files = unique_task_files_from_summary(summary)

    estimator_fields = [
        ("HorusMem", "horus_mib"),
        ("FakeTensorMem", "faketensor_mib"),
        ("GPUMemNet", "gpumemnet_mib"),
    ]

    for task_path in task_files:
        if not task_path.exists():
            continue

        data = yaml.safe_load(task_path.read_text()) or {}
        resources = data.get("resources", {}) or {}
        estimates = data.get("estimates", {}) or {}
        profile = data.get("profile", {}) or {}

        peak_memory_mib = pd.to_numeric(
            profile.get("peak_memory_mib"),
            errors="coerce",
        )

        if pd.isna(peak_memory_mib) or float(peak_memory_mib) <= 0:
            continue

        peak_memory_mib = float(peak_memory_mib)

        for estimator_name, yaml_field in estimator_fields:
            estimate_mib = pd.to_numeric(
                estimates.get(yaml_field),
                errors="coerce",
            )

            if pd.isna(estimate_mib):
                continue

            estimate_mib = float(estimate_mib)
            ratio = estimate_mib / peak_memory_mib
            error_mib = estimate_mib - peak_memory_mib

            rows.append(
                {
                    "task_file": task_path.as_posix(),
                    "workload": task_path.name,
                    "num_gpus": resources.get("num_gpus"),
                    "estimator": estimator_name,
                    "yaml_field": yaml_field,
                    "peak_memory_mib": peak_memory_mib,
                    "estimate_mib": estimate_mib,
                    "error_mib": error_mib,
                    "abs_error_mib": abs(error_mib),
                    "estimate_to_peak_ratio": ratio,
                    "underestimates": ratio < 1.0,
                    "severe_underestimates": ratio < 0.8,
                    "overestimates": ratio > 1.0,
                    "severe_overestimates": ratio > 1.5,
                    "extreme_overestimates": ratio > 2.0,
                }
            )

    detail = pd.DataFrame(rows)

    if detail.empty:
        empty_summary = pd.DataFrame()
        detail.to_csv(output_dir / "estimator_memory_error.csv", index=False)
        empty_summary.to_csv(
            output_dir / "estimator_memory_error_summary.csv",
            index=False,
        )
        return detail, empty_summary, []

    summary_rows: list[dict[str, Any]] = []

    for estimator, group in detail.groupby("estimator", sort=True):
        ratio = pd.to_numeric(
            group["estimate_to_peak_ratio"],
            errors="coerce",
        ).dropna()

        abs_error = pd.to_numeric(
            group["abs_error_mib"],
            errors="coerce",
        ).dropna()

        summary_rows.append(
            {
                "estimator": estimator,
                "task_count": int(len(group)),
                "mean_ratio": ratio.mean(),
                "median_ratio": ratio.median(),
                "p05_ratio": ratio.quantile(0.05),
                "p95_ratio": ratio.quantile(0.95),
                "mean_abs_error_mib": abs_error.mean(),
                "median_abs_error_mib": abs_error.median(),
                "underestimate_count": int(group["underestimates"].sum()),
                "severe_underestimate_count": int(group["severe_underestimates"].sum()),
                "overestimate_count": int(group["overestimates"].sum()),
                "severe_overestimate_count": int(group["severe_overestimates"].sum()),
                "extreme_overestimate_count": int(group["extreme_overestimates"].sum()),
            }
        )

    error_summary = pd.DataFrame(summary_rows)

    detail.to_csv(output_dir / "estimator_memory_error.csv", index=False)
    error_summary.to_csv(
        output_dir / "estimator_memory_error_summary.csv",
        index=False,
    )

    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    figure_paths: list[Path] = []

    estimator_order = ["HorusMem", "FakeTensorMem", "GPUMemNet"]
    ordered = detail.copy()
    ordered["estimator_order"] = ordered["estimator"].map(
        {name: index for index, name in enumerate(estimator_order)}
    )
    ordered = ordered.sort_values(["estimator_order", "estimator", "workload"])

    # Ratio boxplot.
    fig, axis = plt.subplots(figsize=(7.2, 4.6))
    box_data = [
        ordered.loc[
            ordered["estimator"] == estimator,
            "estimate_to_peak_ratio",
        ].dropna()
        for estimator in estimator_order
        if estimator in set(ordered["estimator"])
    ]
    box_labels = [
        estimator
        for estimator in estimator_order
        if estimator in set(ordered["estimator"])
    ]

    if box_data:
        axis.boxplot(box_data, labels=box_labels, showfliers=True)
        axis.axhline(1.0, linestyle="--", linewidth=1.0)
        axis.set_yscale("log")
        axis.set_ylabel("Estimate / measured peak memory")
        axis.set_title("Memory-estimate ratio by estimator")
        axis.grid(True, axis="y", alpha=0.3)
        figure_paths.append(
            save_figure(fig, figures_dir, "estimate_ratio_boxplot")
        )
    else:
        plt.close(fig)

    # Ratio ECDF.
    fig, axis = plt.subplots(figsize=(7.2, 4.6))
    for estimator in estimator_order:
        values = pd.to_numeric(
            ordered.loc[
                ordered["estimator"] == estimator,
                "estimate_to_peak_ratio",
            ],
            errors="coerce",
        ).dropna()
        values = values[values > 0]
        if values.empty:
            continue

        x = values.sort_values().to_numpy()
        y = [(index + 1) / len(x) for index in range(len(x))]
        axis.step(x, y, where="post", label=estimator)

    axis.axvline(1.0, linestyle="--", linewidth=1.0)
    axis.set_xscale("log")
    axis.set_xlabel("Estimate / measured peak memory")
    axis.set_ylabel("Fraction of workloads")
    axis.set_title("Memory-estimate ratio ECDF")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure_paths.append(
        save_figure(fig, figures_dir, "estimate_ratio_ecdf")
    )

    # Estimate-vs-peak scatter.
    fig, axis = plt.subplots(figsize=(6.6, 5.4))
    for estimator in estimator_order:
        group = ordered[ordered["estimator"] == estimator]
        if group.empty:
            continue

        axis.scatter(
            group["peak_memory_mib"],
            group["estimate_mib"],
            label=estimator,
            alpha=0.75,
        )

    max_value = max(
        float(ordered["peak_memory_mib"].max()),
        float(ordered["estimate_mib"].max()),
    )
    min_positive = min(
        float(ordered.loc[ordered["peak_memory_mib"] > 0, "peak_memory_mib"].min()),
        float(ordered.loc[ordered["estimate_mib"] > 0, "estimate_mib"].min()),
    )

    axis.plot(
        [min_positive, max_value],
        [min_positive, max_value],
        linestyle="--",
        linewidth=1.0,
        label="Estimate = measured peak",
    )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("Measured peak memory (MiB)")
    axis.set_ylabel("Estimated memory (MiB)")
    axis.set_title("Estimated vs measured peak memory")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure_paths.append(
        save_figure(fig, figures_dir, "estimate_vs_peak_memory")
    )

    return detail, error_summary, figure_paths


TRACE_ORDER = {
    "philly": 0,
    "saturn": 1,
    "venus": 2,
}

LABEL_ORDER = {
    "AEGIS+PeakMem": 0,
    "AEGIS+HorusMem": 1,
    "AEGIS+FakeTensorMem": 2,
    "AEGIS+GPUMemNet": 3,
    "Exclusive": 4,
}

KIND_ORDER = {
    "estimator": 0,
    "baseline": 1,
}


def sort_readable_table(df: pd.DataFrame) -> pd.DataFrame:
    """Sort result tables so rows from the same trace appear together."""

    if df.empty:
        return df

    out = df.copy()

    if "trace" in out.columns:
        out["_trace_order"] = out["trace"].map(TRACE_ORDER).fillna(999)
    else:
        out["_trace_order"] = 0

    if "kind" in out.columns:
        out["_kind_order"] = out["kind"].map(KIND_ORDER).fillna(999)
    else:
        out["_kind_order"] = 0

    if "label" in out.columns:
        out["_label_order"] = out["label"].map(LABEL_ORDER).fillna(999)
    else:
        out["_label_order"] = 0

    sort_cols = [
        col
        for col in [
            "_trace_order",
            "_kind_order",
            "_label_order",
            "trace",
            "label",
            "estimator",
        ]
        if col in out.columns
    ]

    out = out.sort_values(sort_cols, kind="stable")
    return out.drop(
        columns=[
            col
            for col in ["_trace_order", "_kind_order", "_label_order"]
            if col in out.columns
        ]
    )

def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "_No rows._\n"

    table = df[columns].copy()

    for col in table.columns:
        if pd.api.types.is_float_dtype(table[col]):
            table[col] = table[col].map(
                lambda value: "" if pd.isna(value) else f"{float(value):.3f}"
            )

    return table.to_markdown(index=False)


def write_report(
    *,
    manifest_path: Path,
    output_dir: Path,
    validation: pd.DataFrame,
    summary: pd.DataFrame,
    aggregate: pd.DataFrame,
    memory_error: pd.DataFrame,
    memory_error_summary: pd.DataFrame,
    memory_figures: list[Path],
    bar_figures: list[Path],
    trace_figures: dict[str, list[Path]],
) -> None:
    validation = sort_readable_table(validation)
    summary = sort_readable_table(summary)
    aggregate = sort_readable_table(aggregate)
    memory_error_summary = sort_readable_table(memory_error_summary)

    lines: list[str] = []

    lines.append("# AEGIS Memory-Estimator Sensitivity\n")
    lines.append(
        "This report compares AEGIS variants that use the same runtime pressure "
        "filter and placement policy while changing only the memory-feasibility "
        "input.\n"
    )
    lines.append(f"Manifest: `{manifest_path}`\n")

    lines.append("## Validation Status\n")
    lines.append(
        markdown_table(
            validation,
            [
                "kind",
                "trace",
                "label",
                "status",
                "has_summary",
                "has_job_metrics",
                "submitted",
                "completed",
                "failed",
                "recovered",
            ],
        )
    )
    lines.append("\n")

    incomplete = validation[validation["status"] != "complete"].copy()
    if not incomplete.empty:
        lines.append("## Incomplete, Missing, or Not-Yet-Summarized Runs\n")
        lines.append(
            "These runs are excluded from performance tables and figures until "
            "they are complete and summarized.\n"
        )
        lines.append(
            markdown_table(
                incomplete,
                [
                    "kind",
                    "trace",
                    "label",
                    "status",
                    "has_summary",
                    "has_job_metrics",
                    "submitted",
                    "completed",
                    "failed",
                    "recovered",
                ],
            )
        )
        lines.append("\n")

    if not memory_error_summary.empty:
        lines.append("## Memory-Estimation Behavior\n")
        lines.append(
            "This section compares each memory estimator against the measured "
            "solo-run peak memory recorded in the workload YAML profile. "
            "`AEGIS+PeakMem` is therefore a reference using measured peak memory "
            "for feasibility; it is not a performance oracle.\n"
        )

        memory_cols = [
            "estimator",
            "task_count",
            "mean_ratio",
            "median_ratio",
            "p05_ratio",
            "p95_ratio",
            "mean_abs_error_mib",
            "median_abs_error_mib",
            "underestimate_count",
            "severe_underestimate_count",
            "overestimate_count",
            "severe_overestimate_count",
            "extreme_overestimate_count",
        ]
        memory_cols = [
            col for col in memory_cols
            if col in memory_error_summary.columns
        ]
        lines.append(markdown_table(memory_error_summary, memory_cols))
        lines.append("\n")

        if memory_figures:
            lines.append("### Memory-Estimation Figures\n")
            for figure in memory_figures:
                rel = figure.relative_to(output_dir)
                title = figure.stem.replace("_", " ").title()
                lines.append(f"#### {title}\n")
                lines.append(f"![{title}]({rel})\n")
            lines.append("\n")

    estimator_summary = summary[summary["kind"] == "estimator"].copy()

    lines.append("## Actual End-to-End Performance\n")
    actual_cols = [
        "trace",
        "label",
        "completion_rate",
        "makespan_s",
        "mean_jct_s",
        "p95_jct_s",
        "mean_queue_wait_s",
        "p95_queue_wait_s",
        "mean_execution_time_s",
        "failed",
        "recovered",
    ]
    actual_cols = [col for col in actual_cols if col in estimator_summary.columns]
    lines.append(markdown_table(estimator_summary, actual_cols))
    lines.append("\n")

    lines.append("## Normalized End-to-End Performance\n")
    lines.append("Values are normalized to the Exclusive run from the same trace.\n")
    normalized_cols = [
        "trace",
        "label",
        "completion_rate",
        "normalized_makespan_s",
        "normalized_mean_jct_s",
        "normalized_p95_jct_s",
        "normalized_mean_queue_wait_s",
        "normalized_p95_queue_wait_s",
        "normalized_mean_execution_time_s",
        "failed",
        "recovered",
    ]
    normalized_cols = [col for col in normalized_cols if col in estimator_summary.columns]
    lines.append(markdown_table(estimator_summary, normalized_cols))
    lines.append("\n")

    lines.append("## Aggregate Across Completed Traces\n")
    if aggregate.empty:
        lines.append("_No aggregate rows._\n")
    else:
        lines.append("### Paper-facing estimator summary\n")
        lines.append(
            "All normalized values use Exclusive = 1.0 for each trace before "
            "taking the geometric mean across traces. Queue wait is total queue "
            "wait, including recovery queue wait.\n"
        )

        paper_cols = [
            "label",
            "completion_rate_mean",
            "failed_total",
            "recovered_total",
            "geomean_normalized_makespan_s",
            "geomean_normalized_mean_jct_s",
            "geomean_normalized_p95_jct_s",
            "geomean_normalized_mean_queue_wait_s",
            "geomean_normalized_p95_queue_wait_s",
        ]
        paper_cols = [
            col for col in paper_cols if col in aggregate.columns
        ]
        paper = aggregate[paper_cols].copy()
        paper = paper.rename(
            columns={
                "label": "Estimator",
                "completion_rate_mean": "Completion",
                "failed_total": "Failed attempts",
                "recovered_total": "Recovered attempts",
                "geomean_normalized_makespan_s": "Makespan / Exclusive",
                "geomean_normalized_mean_jct_s": "Mean JCT / Exclusive",
                "geomean_normalized_p95_jct_s": "P95 JCT / Exclusive",
                "geomean_normalized_mean_queue_wait_s": "Mean total wait / Exclusive",
                "geomean_normalized_p95_queue_wait_s": "P95 total wait / Exclusive",
            }
        )
        lines.append(paper.to_markdown(index=False, floatfmt=".3f"))
        lines.append("\n")

        lines.append("### Detailed aggregate summary\n")
        aggregate_cols = [
            "label",
            "trace_count",
            "completion_rate_mean",
            "geomean_normalized_makespan_s",
            "geomean_normalized_mean_jct_s",
            "geomean_normalized_p95_jct_s",
            "geomean_normalized_mean_queue_wait_s",
            "geomean_normalized_p95_queue_wait_s",
            "geomean_normalized_mean_execution_time_s",
            "failed_total",
            "recovered_total",
        ]
        aggregate_cols = [col for col in aggregate_cols if col in aggregate.columns]
        lines.append(markdown_table(aggregate, aggregate_cols))
        lines.append("\n")

    if bar_figures:
        lines.append("## Summary Figures\n")
        for figure in bar_figures:
            rel = figure.relative_to(output_dir)
            title = figure.stem.replace("_", " ").title()
            lines.append(f"### {title}\n")
            lines.append(f"![{title}]({rel})\n")
        lines.append("\n")

    if trace_figures:
        lines.append("## Per-Trace Distribution Figures\n")
        lines.append(
            "These distribution figures are generated by "
            "`plot_policy_distributions.py`, matching the main evaluation "
            "plotting pipeline.\n"
        )

        for trace in sorted(trace_figures):
            lines.append(f"### {trace}\n")
            for figure in trace_figures[trace]:
                rel = figure.relative_to(output_dir)
                title = figure.stem.replace("_", " ").title()
                lines.append(f"#### {title}\n")
                lines.append(f"![{title}]({rel})\n")
            lines.append("\n")

    report_path = output_dir / "estimator_sensitivity_report.md"
    report_path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evaluation/experiments/manifests/estimator_sensitivity_analysis.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evaluation/experiments/results/estimator_sensitivity_analysis"),
    )
    parser.add_argument(
        "--solo-profiles",
        type=Path,
        nargs="*",
        default=DEFAULT_SOLO_PROFILES,
        help="Solo profile CSVs used by plot_policy_distributions.py.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh per-run analysis summaries before building the report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    items = load_manifest(args.manifest)

    if args.refresh:
        refresh_summaries(items)

    validation, summary, aggregate = build_tables(items, output_dir)

    validation = sort_readable_table(validation)
    summary = sort_readable_table(summary)
    aggregate = sort_readable_table(aggregate)

    validation.to_csv(output_dir / "validation_report.csv", index=False)
    summary.to_csv(output_dir / "per_trace_estimator_summary.csv", index=False)
    aggregate.to_csv(output_dir / "aggregate_estimator_summary.csv", index=False)

    if not summary.empty:
        summary = summary.copy()
        summary["has_job_metrics_for_plot"] = summary["root"].map(
            lambda root: (Path(root) / "analysis" / "job_metrics.csv").exists()
        )

    memory_error, memory_error_summary, memory_figures = analyze_memory_estimator_behavior(
        summary=summary,
        output_dir=output_dir,
    )

    bar_figures = plot_bar_figures(summary, output_dir)
    trace_figures = run_distribution_plots(
        summary=summary,
        output_dir=output_dir,
        solo_profiles=args.solo_profiles,
    )

    write_report(
        manifest_path=args.manifest,
        output_dir=output_dir,
        validation=validation,
        summary=summary,
        aggregate=aggregate,
        memory_error=memory_error,
        memory_error_summary=memory_error_summary,
        memory_figures=memory_figures,
        bar_figures=bar_figures,
        trace_figures=trace_figures,
    )

    print(f"Wrote {output_dir}")
    print(f"validation rows: {len(validation)}")
    print(f"complete summary rows: {len(summary)}")
    print(f"aggregate rows: {len(aggregate)}")
    print(f"report: {output_dir / 'estimator_sensitivity_report.md'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
