#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_PROFILE_COMPARISON = (
    REPO_ROOT / "evaluation" / "profiling" / "solo" / "analysis" / "profile_200s_vs_full.csv"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evaluation" / "figures" / "profile_threshold_insights"

PROFILE_METRICS = ["smact", "smocc", "drama"]
RISK_METRICS = ["smact_risk", "smocc_risk", "drama_risk"]
RISK_COMPONENTS = ["mean", "median", "p95", "ewma", "risk"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Plot profile-mismatch and threshold-window insight figures."
    )
    p.add_argument("--profile-comparison", default=str(DEFAULT_PROFILE_COMPARISON))
    p.add_argument("--window-stability", default=None)
    p.add_argument("--risk-component-rollup", default=None)
    p.add_argument("--per-workload-components", default=None)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--top-k", type=int, default=12)
    p.add_argument("--decision-window", type=float, default=30.0)
    p.add_argument("--reference-window", type=float, default=200.0)
    p.add_argument("--formats", default="pdf,png")
    return p.parse_args()


def read_csv_if_exists(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()

    path = Path(path)
    if not path.exists():
        print(f"missing input, skipping: {path}")
        return pd.DataFrame()

    return pd.read_csv(path)


def short_label(value: str, max_len: int = 42) -> str:
    value = str(value)
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def workload_label(row: pd.Series) -> str:
    if "workload_id" in row.index and pd.notna(row["workload_id"]):
        return str(row["workload_id"])

    if "task_path" in row.index and pd.notna(row["task_path"]):
        return Path(str(row["task_path"])).stem

    if "spec_path" in row.index and pd.notna(row["spec_path"]):
        return Path(str(row["spec_path"])).stem

    return str(row.name)


def save_figure(fig, output_dir: Path, stem: str, formats: list[str]) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for fmt in formats:
        fmt = fmt.strip().lower().lstrip(".")
        if not fmt:
            continue
        path = output_dir / f"{stem}.{fmt}"
        fig.savefig(path, bbox_inches="tight", dpi=200)
        written.append(path)

    plt.close(fig)
    return written


def prepare_profile_score_mismatches(comparison: pd.DataFrame) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()

    required = {"metric", "stat", "relative_error_200s_vs_full", "value_200s", "value_full"}
    if not required.issubset(comparison.columns):
        return pd.DataFrame()

    out = comparison[
        comparison["metric"].isin(PROFILE_METRICS)
        & (comparison["stat"] == "profile_stat_score")
    ].copy()

    if out.empty:
        return out

    out["relative_error_200s_vs_full"] = pd.to_numeric(
        out["relative_error_200s_vs_full"],
        errors="coerce",
    )
    out["relative_error_percent"] = out["relative_error_200s_vs_full"] * 100.0
    out["value_200s"] = pd.to_numeric(out["value_200s"], errors="coerce")
    out["value_full"] = pd.to_numeric(out["value_full"], errors="coerce")
    out["workload_label"] = out.apply(workload_label, axis=1)

    return out.dropna(subset=["relative_error_percent"])


def plot_profile_mismatch_boxplot(
    comparison: pd.DataFrame,
    output_dir: Path,
    formats: list[str],
) -> list[Path]:
    data = prepare_profile_score_mismatches(comparison)
    if data.empty:
        return []

    grouped = []
    labels = []

    for metric in PROFILE_METRICS:
        values = data.loc[data["metric"] == metric, "relative_error_percent"].dropna()
        if values.empty:
            continue
        grouped.append(values.to_list())
        labels.append(metric.upper())

    if not grouped:
        return []

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.boxplot(grouped, tick_labels=labels, showmeans=True)
    ax.set_ylabel("200s-vs-full relative error (%)")
    ax.set_xlabel("Metric")
    ax.set_title("Fixed 200s profile mismatch")
    ax.grid(True, axis="y", alpha=0.3)

    return save_figure(fig, output_dir, "profile_200s_vs_full_boxplot", formats)


def plot_profile_top_mismatches(
    comparison: pd.DataFrame,
    output_dir: Path,
    formats: list[str],
    top_k: int,
) -> list[Path]:
    data = prepare_profile_score_mismatches(comparison)
    if data.empty:
        return []

    top = data.sort_values("relative_error_percent", ascending=False).head(top_k).copy()
    top["label"] = top.apply(
        lambda row: f"{short_label(row['workload_label'], 34)} ({str(row['metric']).upper()})",
        axis=1,
    )

    fig_height = max(3.8, 0.35 * len(top) + 1.2)
    fig, ax = plt.subplots(figsize=(8.0, fig_height))
    ax.barh(top["label"], top["relative_error_percent"])
    ax.invert_yaxis()
    ax.set_xlabel("200s-vs-full relative error (%)")
    ax.set_title("Largest fixed-profile mismatches")
    ax.grid(True, axis="x", alpha=0.3)

    return save_figure(fig, output_dir, "profile_top_mismatches", formats)


def prepare_window_stability(stability: pd.DataFrame, reference_window: float) -> pd.DataFrame:
    if stability.empty:
        return pd.DataFrame()

    required = {
        "metric",
        "summary_window_seconds",
        "reference_window_seconds",
        "mean_abs_error",
    }
    if not required.issubset(stability.columns):
        return pd.DataFrame()

    out = stability[
        stability["metric"].isin(RISK_METRICS)
        & (
            pd.to_numeric(stability["reference_window_seconds"], errors="coerce")
            == float(reference_window)
        )
    ].copy()

    out["summary_window_seconds"] = pd.to_numeric(
        out["summary_window_seconds"],
        errors="coerce",
    )
    out["mean_abs_error"] = pd.to_numeric(out["mean_abs_error"], errors="coerce")

    return out.dropna(subset=["summary_window_seconds", "mean_abs_error"])


def plot_window_stability_curve(
    stability: pd.DataFrame,
    output_dir: Path,
    formats: list[str],
    reference_window: float,
    decision_window: float,
) -> list[Path]:
    data = prepare_window_stability(stability, reference_window)
    if data.empty:
        return []

    fig, ax = plt.subplots(figsize=(7.0, 3.8))

    for metric in RISK_METRICS:
        metric_data = data[data["metric"] == metric].sort_values("summary_window_seconds")
        metric_data = metric_data[metric_data["summary_window_seconds"] != float(reference_window)]
        if metric_data.empty:
            continue

        ax.plot(
            metric_data["summary_window_seconds"],
            metric_data["mean_abs_error"],
            marker="o",
            label=metric.replace("_risk", "").upper(),
        )

    ax.axvline(float(decision_window), linestyle="--", linewidth=1.2, label="decision window")
    ax.set_xlabel("Post-TTFK summary window (s)")
    ax.set_ylabel(f"Mean absolute error vs {reference_window:g}s")
    ax.set_title("TTFK-window stability")
    ax.grid(True, alpha=0.3)
    ax.legend()

    return save_figure(fig, output_dir, "threshold_window_stability_curve", formats)


def prepare_component_rollup(rollup: pd.DataFrame) -> pd.DataFrame:
    if rollup.empty:
        return pd.DataFrame()

    required = {
        "risk_component",
        "summary_window_seconds",
        "weighted_mean_abs_error",
    }
    if not required.issubset(rollup.columns):
        return pd.DataFrame()

    out = rollup[rollup["risk_component"].isin(RISK_COMPONENTS)].copy()
    out["summary_window_seconds"] = pd.to_numeric(
        out["summary_window_seconds"],
        errors="coerce",
    )
    out["weighted_mean_abs_error"] = pd.to_numeric(
        out["weighted_mean_abs_error"],
        errors="coerce",
    )

    return out.dropna(subset=["summary_window_seconds", "weighted_mean_abs_error"])


def plot_risk_component_ablation(
    rollup: pd.DataFrame,
    output_dir: Path,
    formats: list[str],
    reference_window: float,
    decision_window: float,
) -> list[Path]:
    data = prepare_component_rollup(rollup)
    if data.empty:
        return []

    fig, ax = plt.subplots(figsize=(7.0, 3.8))

    for component in RISK_COMPONENTS:
        component_data = data[data["risk_component"] == component].sort_values(
            "summary_window_seconds"
        )
        component_data = component_data[
            component_data["summary_window_seconds"] != float(reference_window)
        ]
        if component_data.empty:
            continue

        ax.plot(
            component_data["summary_window_seconds"],
            component_data["weighted_mean_abs_error"],
            marker="o",
            label=component,
        )

    ax.axvline(float(decision_window), linestyle="--", linewidth=1.2, label="decision window")
    ax.set_xlabel("Post-TTFK summary window (s)")
    ax.set_ylabel(f"Weighted mean absolute error vs {reference_window:g}s")
    ax.set_title("Risk-component ablation")
    ax.grid(True, alpha=0.3)
    ax.legend()

    return save_figure(fig, output_dir, "risk_component_ablation_curve", formats)


def prepare_per_workload_heatmap(
    per_workload: pd.DataFrame,
    *,
    top_k: int,
) -> pd.DataFrame:
    if per_workload.empty:
        return pd.DataFrame()

    required = {"task_path", "base_metric", "risk_abs_error"}
    if not required.issubset(per_workload.columns):
        return pd.DataFrame()

    data = per_workload.copy()
    data["risk_abs_error"] = pd.to_numeric(data["risk_abs_error"], errors="coerce")
    data["workload_label"] = data["task_path"].apply(lambda x: Path(str(x)).stem)

    pivot = data.pivot_table(
        index="workload_label",
        columns="base_metric",
        values="risk_abs_error",
        aggfunc="max",
    )

    if pivot.empty:
        return pivot

    for metric in PROFILE_METRICS:
        if metric not in pivot.columns:
            pivot[metric] = pd.NA

    pivot = pivot[PROFILE_METRICS]
    pivot["max_error"] = pivot.max(axis=1)
    pivot = pivot.sort_values("max_error", ascending=False).head(top_k)
    pivot = pivot.drop(columns=["max_error"])

    return pivot


def plot_per_workload_error_heatmap(
    per_workload: pd.DataFrame,
    output_dir: Path,
    formats: list[str],
    top_k: int,
    decision_window: float,
    reference_window: float,
) -> list[Path]:
    pivot = prepare_per_workload_heatmap(per_workload, top_k=top_k)
    if pivot.empty:
        return []

    values = pivot.astype(float).to_numpy()
    row_labels = [short_label(idx, 38) for idx in pivot.index]
    col_labels = [c.upper() for c in pivot.columns]

    fig_height = max(4.0, 0.35 * len(row_labels) + 1.5)
    fig, ax = plt.subplots(figsize=(6.5, fig_height))
    image = ax.imshow(values, aspect="auto")

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)

    ax.set_title(f"Per-workload risk error: {decision_window:g}s vs {reference_window:g}s")
    ax.set_xlabel("Metric")
    ax.set_ylabel("Workload")

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if pd.notna(values[i, j]):
                ax.text(j, i, f"{values[i, j]:.3f}", ha="center", va="center", fontsize=8)

    fig.colorbar(image, ax=ax, label="Absolute error")

    return save_figure(fig, output_dir, "per_workload_risk_error_heatmap", formats)


def write_inventory(output_dir: Path, written: list[Path]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "figure_inventory.md"

    lines = ["# Profile and Threshold Insight Figures\n"]
    for figure in written:
        lines.append(f"- `{figure.name}`")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir)
    formats = [item.strip() for item in str(args.formats).split(",") if item.strip()]

    profile_comparison = read_csv_if_exists(args.profile_comparison)
    window_stability = read_csv_if_exists(args.window_stability)
    risk_component_rollup = read_csv_if_exists(args.risk_component_rollup)
    per_workload_components = read_csv_if_exists(args.per_workload_components)

    written: list[Path] = []

    written.extend(plot_profile_mismatch_boxplot(profile_comparison, output_dir, formats))
    written.extend(plot_profile_top_mismatches(profile_comparison, output_dir, formats, int(args.top_k)))

    written.extend(
        plot_window_stability_curve(
            window_stability,
            output_dir,
            formats,
            reference_window=float(args.reference_window),
            decision_window=float(args.decision_window),
        )
    )

    written.extend(
        plot_risk_component_ablation(
            risk_component_rollup,
            output_dir,
            formats,
            reference_window=float(args.reference_window),
            decision_window=float(args.decision_window),
        )
    )

    written.extend(
        plot_per_workload_error_heatmap(
            per_workload_components,
            output_dir,
            formats,
            top_k=int(args.top_k),
            decision_window=float(args.decision_window),
            reference_window=float(args.reference_window),
        )
    )

    inventory = write_inventory(output_dir, written)

    for path in written:
        print(f"wrote {path}")
    print(f"wrote {inventory}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())