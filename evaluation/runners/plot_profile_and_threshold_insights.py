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

PROFILE_COMPONENT_STATS = [
    ("mean", "Mean"),
    ("median", "Median"),
    ("p95", "P95"),
    ("ewma", "EWMA"),
    ("aegis_profile_risk", "combined risk"),
]

PROFILE_COMPONENT_METRICS = [
    ("smact", "SMACT"),
    ("smocc", "SMOCC"),
    ("drama", "DRAMA"),
]


PROFILE_TOP_MISMATCH_STATS = [
    ("aegis_profile_risk", "combined risk", "profile_top_mismatches"),
    ("mean", "Mean", "profile_top_mismatches_mean"),
    ("median", "Median", "profile_top_mismatches_median"),
    ("p95", "P95", "profile_top_mismatches_p95"),
    ("ewma", "EWMA", "profile_top_mismatches_ewma"),
]


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
    p.add_argument(
        "--heatmap-components",
        default="risk,mean,median,p95,ewma",
        help="Comma-separated components for per-workload heatmaps.",
    )
    p.add_argument("--skip-profile-plots", action="store_true")
    p.add_argument("--skip-threshold-plots", action="store_true")
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

def build_profile_component_error_frame(comparison: pd.DataFrame) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()

    required = {
        "metric",
        "stat",
        "workload_id",
        "source_gpu_count",
        "gpu_label",
        "relative_error_200s_vs_full",
        "abs_error_200s_vs_full",
    }
    if not required.issubset(comparison.columns):
        return pd.DataFrame()

    stats = {name for name, _ in PROFILE_COMPONENT_STATS}
    metrics = {name for name, _ in PROFILE_COMPONENT_METRICS}

    df = comparison[
        comparison["metric"].isin(metrics)
        & comparison["stat"].isin(stats)
    ].copy()

    if df.empty:
        return pd.DataFrame()

    df["relative_error_200s_vs_full"] = pd.to_numeric(
        df["relative_error_200s_vs_full"],
        errors="coerce",
    )
    df["relative_error_percent"] = df["relative_error_200s_vs_full"] * 100.0

    return df.dropna(subset=["relative_error_percent"])


def prepare_profile_mismatches(
    comparison: pd.DataFrame,
    *,
    stat_name: str,
) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()

    required = {
        "metric",
        "stat",
        "relative_error_200s_vs_full",
        "value_200s",
        "value_full",
    }
    if not required.issubset(comparison.columns):
        return pd.DataFrame()

    out = comparison[
        comparison["metric"].isin(PROFILE_METRICS)
        & (comparison["stat"] == stat_name)
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

def plot_profile_component_boxplots(
    comparison: pd.DataFrame,
    output_dir: Path,
    formats: list[str],
) -> list[Path]:
    df = build_profile_component_error_frame(comparison)
    if df.empty:
        return []

    title_fontsize = 16
    label_fontsize = 14
    tick_fontsize = 12

    metric_order = [name for name, _ in PROFILE_COMPONENT_METRICS]
    metric_labels = {name: label for name, label in PROFILE_COMPONENT_METRICS}

    fig, axes = plt.subplots(
        len(metric_order),
        1,
        figsize=(7.4, 9.0),
        sharex=True,
    )
    if len(metric_order) == 1:
        axes = [axes]

    for ax, metric_name in zip(axes, metric_order):
        metric_df = df[df["metric"] == metric_name].copy()

        series_list = []
        labels = []

        for stat_name, stat_label in PROFILE_COMPONENT_STATS:
            vals = metric_df.loc[
                metric_df["stat"] == stat_name,
                "relative_error_percent",
            ].dropna()

            if vals.empty:
                continue

            series_list.append(vals.to_list())
            labels.append(stat_label)

        if not series_list:
            ax.set_yticks([])
            continue

        ax.boxplot(
            series_list,
            labels=labels,
            vert=False,
            showmeans=True,
            widths=0.55,
        )

        ax.text(
            0.98,
            0.90,
            metric_labels[metric_name],
            transform=ax.transAxes,
            fontsize=title_fontsize,
            fontweight="bold",
            va="top",
            ha="right",
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "white",
                "edgecolor": "0.8",
                "alpha": 0.9,
            },
        )

        ax.tick_params(axis="x", labelsize=tick_fontsize)
        ax.tick_params(axis="y", labelsize=tick_fontsize)
        ax.grid(True, axis="x", alpha=0.3)

    axes[-1].set_xlabel("200s-vs-full relative error (%)", fontsize=label_fontsize)

    fig.tight_layout(h_pad=1.2)

    return save_figure(
        fig,
        output_dir,
        "profile_200s_vs_full_component_boxplots",
        formats,
    )

def prepare_profile_score_mismatches(comparison: pd.DataFrame) -> pd.DataFrame:
    return prepare_profile_mismatches(
        comparison,
        stat_name="aegis_profile_risk",
    )


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


def plot_profile_top_mismatches_for_stat(
    comparison: pd.DataFrame,
    output_dir: Path,
    formats: list[str],
    top_k: int,
    *,
    stat_name: str,
    stat_label: str,
    stem: str,
) -> list[Path]:
    data = prepare_profile_mismatches(
        comparison,
        stat_name=stat_name,
    )
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
    ax.set_title(f"Largest fixed-profile mismatches ({stat_label})")
    ax.grid(True, axis="x", alpha=0.3)

    return save_figure(fig, output_dir, stem, formats)


def plot_profile_top_mismatches(
    comparison: pd.DataFrame,
    output_dir: Path,
    formats: list[str],
    top_k: int,
) -> list[Path]:
    return plot_profile_top_mismatches_for_stat(
        comparison,
        output_dir,
        formats,
        top_k,
        stat_name="aegis_profile_risk",
        stat_label="Combined risk",
        stem="profile_top_mismatches",
    )

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
    formats: Sequence[str],
    *,
    reference_window: float,
    decision_window: float | None = None,
) -> list[Path]:
    data = prepare_window_stability(stability, reference_window)

    if data.empty:
        raise ValueError(
            "No window-stability rows after filtering. "
            f"input columns={list(stability.columns)}"
        )

    fig, ax = plt.subplots(figsize=(6.4, 3.0))

    # The CSV stores one row per metric/statistic/window. We plot the most
    # paper-relevant pressure summaries with distinct markers and line styles.
    preferred_metrics = [
        ("smact_risk", "SMACT pressure", "s", "--", "#1F77B4"),
        ("smocc_risk", "SMOCC pressure", "^", "-.", "#2CA02C"),
        ("drama_risk", "DRAMA pressure", "D", ":", "#9467BD"),
    ]

    available = set(data["metric"].astype(str).tolist())

    plotted = False

    for metric, label, marker, linestyle, color in preferred_metrics:
        if metric not in available:
            continue

        metric_rows = data[data["metric"].astype(str) == metric].copy()
        metric_rows = metric_rows.sort_values("summary_window_seconds")

        ax.plot(
            metric_rows["summary_window_seconds"],
            metric_rows["mean_abs_error"],
            marker=marker,
            linestyle=linestyle,
            linewidth=2.2,
            markersize=5.8,
            color=color,
            label=label,
        )
        plotted = True

    # Fallback: if the exact preferred metric names are not available, plot the
    # first four *_mean metrics so the artifact still regenerates.
    if not plotted:
        fallback_metrics = [
            m for m in sorted(available)
            if str(m).endswith("_risk")
        ][:4]

        style_cycle = [
            ("o", "-", "#0072B2"),
            ("s", "--", "#D55E00"),
            ("^", "-.", "#009E73"),
            ("D", ":", "#CC79A7"),
        ]

        for idx, metric in enumerate(fallback_metrics):
            marker, linestyle, color = style_cycle[idx % len(style_cycle)]
            metric_rows = data[data["metric"].astype(str) == metric].copy()
            metric_rows = metric_rows.sort_values("summary_window_seconds")
            ax.plot(
                metric_rows["summary_window_seconds"],
                metric_rows["mean_abs_error"],
                marker=marker,
                linestyle=linestyle,
                linewidth=2.2,
                markersize=5.8,
                color=color,
                label=str(metric).replace("_", " "),
            )
            plotted = True

    if not plotted:
        raise ValueError(
            "No usable metrics found for window-stability plot. "
            f"available metrics={sorted(available)}"
        )

    ax.set_xlabel("Activity-anchored window (s)", fontsize=13)
    ax.set_ylabel("Mean absolute error", fontsize=13)

    # Show the first evaluated window after 0 s, but avoid crowding the
    # early-axis labels. The 10 s point remains plotted but is not labeled.
    evaluated_windows = sorted(
        pd.to_numeric(data["summary_window_seconds"], errors="coerce")
        .dropna()
        .unique()
        .tolist()
    )
    tick_values = [0.0, 5.0, 20.0, 30.0, 60.0, 120.0, 200.0]
    tick_values = [v for v in tick_values if v <= max(evaluated_windows)]
    ax.set_xticks(tick_values)
    ax.set_xticklabels(
        [str(int(v)) if float(v).is_integer() else f"{v:g}" for v in tick_values],
        fontsize=11,
    )
    ax.set_xlim(left=0.0, right=max(evaluated_windows) * 1.03)

    ax.grid(True, axis="both", linestyle=":", alpha=0.30)

    selected_window = 30.0
    ax.axvline(
        selected_window,
        color="#444444",
        linestyle="--",
        linewidth=1.6,
        alpha=0.85,
        label="Selected 30 s",
        zorder=1,
    )

    ax.tick_params(axis="both", labelsize=12, width=1.2)

    for spine in ax.spines.values():
        spine.set_linewidth(1.2)

    ax.legend(
        loc="upper right",
        frameon=True,
        fontsize=10.0,
        borderpad=0.35,
        labelspacing=0.30,
        handlelength=2.2,
    )

    fig.subplots_adjust(top=0.95, right=0.98)

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

    label_fontsize = 15
    tick_fontsize = 13
    legend_fontsize = 12

    fig, ax = plt.subplots(figsize=(7.2, 4.4))

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
    ax.set_xlabel("Post-first-GPU-activity window (s)", fontsize=label_fontsize)
    ax.set_ylabel(f"Mean absolute error vs {reference_window:g}s", fontsize=label_fontsize)
    ax.tick_params(axis="both", labelsize=tick_fontsize)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=legend_fontsize)

    return save_figure(fig, output_dir, "risk_component_ablation_curve", formats)


def prepare_per_workload_heatmap(
    per_workload: pd.DataFrame,
    *,
    top_k: int,
    component: str,
) -> pd.DataFrame:
    if per_workload.empty:
        return pd.DataFrame()

    error_col = f"{component}_abs_error"

    required = {"task_path", "base_metric", error_col}
    if not required.issubset(per_workload.columns):
        return pd.DataFrame()

    data = per_workload.copy()
    data[error_col] = pd.to_numeric(data[error_col], errors="coerce")
    data["workload_label"] = data["task_path"].apply(lambda x: Path(str(x)).stem)

    pivot = data.pivot_table(
        index="workload_label",
        columns="base_metric",
        values=error_col,
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
    component: str,
) -> list[Path]:
    pivot = prepare_per_workload_heatmap(
        per_workload,
        top_k=top_k,
        component=component,
    )
    if pivot.empty:
        return []

    label_fontsize = 15
    tick_fontsize = 12
    cell_fontsize = 10
    colorbar_fontsize = 13

    values = pivot.astype(float).to_numpy()
    row_labels = [short_label(idx, 38) for idx in pivot.index]
    col_labels = [c.upper() for c in pivot.columns]

    fig_height = max(4.0, 0.35 * len(row_labels) + 1.5)
    fig, ax = plt.subplots(figsize=(7.2, fig_height + 0.6))
    image = ax.imshow(values, aspect="auto")

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)

    ax.set_xlabel("Metric", fontsize=label_fontsize)
    ax.set_ylabel("Workload", fontsize=label_fontsize)
    ax.tick_params(axis="x", labelsize=tick_fontsize)
    ax.tick_params(axis="y", labelsize=tick_fontsize)

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if pd.notna(values[i, j]):
                ax.text(
                    j,
                    i,
                    f"{values[i, j]:.3f}",
                    ha="center",
                    va="center",
                    fontsize=cell_fontsize,
                )

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Absolute error", fontsize=colorbar_fontsize)
    cbar.ax.tick_params(labelsize=tick_fontsize)

    return save_figure(
        fig,
        output_dir,
        f"per_workload_{component}_error_heatmap",
        formats,
    )


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

    heatmap_components = [
        item.strip()
        for item in str(args.heatmap_components).split(",")
        if item.strip()
    ]

    profile_comparison = read_csv_if_exists(args.profile_comparison)
    window_stability = read_csv_if_exists(args.window_stability)
    risk_component_rollup = read_csv_if_exists(args.risk_component_rollup)
    per_workload_components = read_csv_if_exists(args.per_workload_components)

    written: list[Path] = []

    if not args.skip_profile_plots:
        written.extend(plot_profile_mismatch_boxplot(profile_comparison, output_dir, formats))

        written.extend(
            plot_profile_component_boxplots(
                profile_comparison,
                output_dir,
                formats,
            )
        )

        written.extend(plot_profile_top_mismatches(profile_comparison, output_dir, formats, int(args.top_k)))

        for stat_name, stat_label, stem in PROFILE_TOP_MISMATCH_STATS[1:]:
            written.extend(
                plot_profile_top_mismatches_for_stat(
                    profile_comparison,
                    output_dir,
                    formats,
                    int(args.top_k),
                    stat_name=stat_name,
                    stat_label=stat_label,
                    stem=stem,
                )
            )

    if not args.skip_threshold_plots:
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

        for component in heatmap_components:
            written.extend(
                plot_per_workload_error_heatmap(
                    per_workload_components,
                    output_dir,
                    formats,
                    top_k=int(args.top_k),
                    decision_window=float(args.decision_window),
                    reference_window=float(args.reference_window),
                    component=component,
                )
            )

    inventory = write_inventory(output_dir, written)

    for path in written:
        print(f"wrote {path}")
    print(f"wrote {inventory}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())