#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter


DISPLAY_ORDER = [
    "AEGIS+AnalyticalMemEst",
    "Horus",
    "Lucid",
    "AEGIS-EstimatorFree",
    "Exclusive",
    "AEGIS+PeakMem",
]

# Exact mapping from raw run labels in normalized_jct_values.csv to paper names.
LABEL_ALIASES = {
    "EST-MAGM__horus": "AEGIS+AnalyticalMemEst",
    "HORUS__horus": "Horus",
    "LUCID": "Lucid",
    "OR-MAGM": "AEGIS-EstimatorFree",
    "exclusive": "Exclusive",
    "oracle-MAGM": "AEGIS+PeakMem",
}

# Draw secondary/baseline curves first; draw AEGIS-EstimatorFree last so it stays visible.
DRAW_ORDER = [
    "Exclusive",
    "Horus",
    "Lucid",
    "AEGIS+AnalyticalMemEst",
    "AEGIS+PeakMem",
    "AEGIS-EstimatorFree",
]

# Simple, distinct styles. No markers and no artificial smoothing.
LINE_STYLES = {
    "AEGIS+AnalyticalMemEst": dict(linestyle=":", linewidth=2.5, zorder=4),
    "Horus": dict(linestyle=(0, (5, 2)), linewidth=2.4, zorder=3),
    "Lucid": dict(linestyle="-.", linewidth=2.4, zorder=3),
    "AEGIS-EstimatorFree": dict(linestyle="-", linewidth=3.0, zorder=8),
    "Exclusive": dict(linestyle=(0, (3, 2)), linewidth=2.4, zorder=2),
    "AEGIS+PeakMem": dict(linestyle=(0, (8, 2, 2, 2)), linewidth=2.4, zorder=5),
}

def display_label(raw: object) -> str:
    raw_s = str(raw)
    return LABEL_ALIASES.get(raw_s, raw_s)


def order_key(label: str, order: list[str]) -> tuple[int, str]:
    try:
        return (order.index(label), label)
    except ValueError:
        return (len(order), label)


def ecdf(values: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(pd.to_numeric(values, errors="raise").to_numpy(dtype=float))
    y = np.arange(1, len(x) + 1, dtype=float) / len(x) * 100.0
    return x, y


def plot_panel(ax, csv_path: Path, trace_label: str, *, x_min: float, x_max: float):
    df = pd.read_csv(csv_path)
    df["display_label"] = df["run_label"].map(display_label)

    labels = sorted(df["display_label"].dropna().unique(), key=lambda x: order_key(x, DRAW_ORDER))

    handles_by_label = {}
    for label in labels:
        part = df[df["display_label"] == label]
        x, y = ecdf(part["normalized_jct"])

        style = LINE_STYLES.get(label, dict(linestyle="-", linewidth=2.6, zorder=1))
        line, = ax.plot(
            x,
            y,
            label=label,
            marker=None,
            solid_capstyle="round",
            dash_capstyle="round",
            **style,
        )
        handles_by_label[label] = line

    ax.set_xscale("log")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, 100)

    ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0,)))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    ax.xaxis.set_minor_formatter(NullFormatter())

    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.grid(True, which="major", axis="both", linestyle=":", linewidth=0.7, alpha=0.55)
    ax.grid(True, which="minor", axis="x", linestyle=":", linewidth=0.4, alpha=0.25)

    ax.set_title(trace_label, fontsize=18, pad=7)
    ax.tick_params(axis="both", labelsize=15)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    return handles_by_label


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=Path("evaluation/experiments/results/final_representative_evaluation_analysis"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evaluation/experiments/results/final_representative_evaluation_analysis/figures"),
    )
    parser.add_argument("--output-stem", default="paper_normalized_jct_cdf_traces")
    parser.add_argument("--x-min", type=float, default=0.8)
    parser.add_argument("--x-max", type=float, default=300.0)
    args = parser.parse_args()

    traces = [
        ("philly", "Philly"),
        ("saturn", "Saturn"),
        ("venus", "Venus"),
    ]

    plt.rcParams.update({
        "font.size": 16,
        "axes.labelsize": 19,
        "axes.titlesize": 20,
        "xtick.labelsize": 16,
        "ytick.labelsize": 16,
        "legend.fontsize": 15,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(18.0, 6.1),
        sharey=True,
    )

    all_handles = {}
    for ax, (trace_key, trace_label) in zip(axes, traces):
        csv_path = args.analysis_dir / "traces" / trace_key / "normalized_jct_values.csv"
        handles = plot_panel(ax, csv_path, trace_label, x_min=args.x_min, x_max=args.x_max)
        all_handles.update(handles)

    axes[0].set_ylabel("Fraction of jobs (%)")
    for ax in axes[1:]:
        ax.tick_params(axis="y", labelleft=True)

    fig.supxlabel("Normalized JCT (JCT / solo runtime)", fontsize=19, y=0.075)

    legend_labels = [x for x in DISPLAY_ORDER if x in all_handles]
    legend_handles = [all_handles[x] for x in legend_labels]

    # Two-row legend avoids names sitting on top of each other.
    fig.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=3,
        frameon=True,
        fancybox=True,
        columnspacing=2.0,
        handlelength=3.2,
        borderpad=0.45,
        labelspacing=0.55,
    )

    fig.tight_layout(rect=(0.0, 0.04, 1.0, 0.85))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for ext in ["pdf", "png"]:
        out = args.output_dir / f"{args.output_stem}.{ext}"
        fig.savefig(out, bbox_inches="tight", dpi=300)
        print(out)

    plt.close(fig)


if __name__ == "__main__":
    main()
