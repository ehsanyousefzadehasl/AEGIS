#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Create decision-oriented threshold sweep tables and figures."
    )
    p.add_argument("--summary-csv", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--max-slowdown-budget", type=float, default=3.0)
    p.add_argument("--p95-slowdown-budget", type=float, default=2.5)
    return p.parse_args()


def parse_threshold_dir(name: str) -> dict[str, float]:
    m = re.match(
        r"smact_(\d+p\d+)_smocc_(\d+p\d+)_drama_(\d+p\d+)",
        name,
    )
    if not m:
        return {"tau_smact": float("nan"), "tau_smocc": float("nan"), "tau_drama": float("nan")}

    def f(x: str) -> float:
        return float(x.replace("p", "."))

    return {
        "tau_smact": f(m.group(1)),
        "tau_smocc": f(m.group(2)),
        "tau_drama": f(m.group(3)),
    }


def markdown_table(df: pd.DataFrame, path: Path, *, max_rows: int = 30) -> None:
    path.write_text(df.head(max_rows).to_markdown(index=False), encoding="utf-8")


def main() -> int:
    args = parse_args()

    out = Path(args.output_dir)
    tables = out / "tables"
    figs = out / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.summary_csv)

    numeric_cols = [
        "reject_retry_count",
        "solo_runtime_sum_seconds",
        "sequence_wall_time_seconds",
        "throughput_gain",
        "mean_slowdown",
        "max_slowdown",
        "failed_started_rows",
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    threshold_rows = []
    for threshold_dir, g in df.groupby("threshold_dir"):
        parsed = parse_threshold_dir(threshold_dir)

        completed_trials = int(
            (
                g["throughput_gain"].notna()
                & g["sequence_wall_time_seconds"].notna()
                & (g["failed_started_rows"].fillna(0) == 0)
            ).sum()
        )

        trial_count = len(g)
        completion_fraction = completed_trials / trial_count if trial_count else 0.0

        mean_throughput = g["throughput_gain"].mean()
        median_throughput = g["throughput_gain"].median()
        worst_slowdown = g["max_slowdown"].max()
        p95_slowdown = g["max_slowdown"].quantile(0.95)
        mean_slowdown = g["mean_slowdown"].mean()
        total_retries = int(g["reject_retry_count"].fillna(0).sum())
        failed_started = int(g["failed_started_rows"].fillna(0).sum())

        feasible = (
            completion_fraction == 1.0
            and failed_started == 0
            and worst_slowdown <= args.max_slowdown_budget
            and p95_slowdown <= args.p95_slowdown_budget
            
        )

        # Higher is better: throughput reward with slowdown penalty.
        # Retry count is diagnostic only; retries mean the gate is active.
        score = (
            mean_throughput / max(worst_slowdown, 1.0)
            if pd.notna(mean_throughput) and pd.notna(worst_slowdown)
            else float("nan")
        )

        threshold_rows.append({
            "threshold_dir": threshold_dir,
            **parsed,
            "trial_count": trial_count,
            "completion_fraction": completion_fraction,
            "failed_started_rows": failed_started,
            "mean_throughput_gain": mean_throughput,
            "median_throughput_gain": median_throughput,
            "mean_slowdown": mean_slowdown,
            "p95_max_slowdown": p95_slowdown,
            "worst_max_slowdown": worst_slowdown,
            "total_reject_retries": total_retries,
            "feasible": feasible,
            "score": score,
        })

    ranked = pd.DataFrame(threshold_rows).sort_values(
        ["feasible", "score", "mean_throughput_gain"],
        ascending=[False, False, False],
    )

    ranked_path = tables / "threshold_settings_ranked.csv"
    ranked.to_csv(ranked_path, index=False)
    markdown_table(ranked, tables / "threshold_settings_ranked.md")

    feasible = ranked[ranked["feasible"] == True].copy()
    feasible_path = tables / "threshold_settings_feasible.csv"
    feasible.to_csv(feasible_path, index=False)
    markdown_table(feasible, tables / "threshold_settings_feasible.md")

    per_trial = (
        df.groupby("trial_id")
        .agg(
            settings=("threshold_dir", "nunique"),
            best_throughput_gain=("throughput_gain", "max"),
            worst_throughput_gain=("throughput_gain", "min"),
            median_throughput_gain=("throughput_gain", "median"),
            best_max_slowdown=("max_slowdown", "min"),
            worst_max_slowdown=("max_slowdown", "max"),
            total_reject_retries=("reject_retry_count", "sum"),
        )
        .reset_index()
        .sort_values("worst_max_slowdown", ascending=False)
    )
    per_trial.to_csv(tables / "per_trial_sensitivity.csv", index=False)
    markdown_table(per_trial, tables / "per_trial_sensitivity.md")

    # Clean presentation figures.
    # We show direct metrics only: throughput, slowdown, and rejection diagnostics.
    # Thresholds are sorted numerically as SMACT, then SMOCC, then DRAMA.

    grid = ranked.sort_values(["tau_smact", "tau_smocc", "tau_drama"]).copy()
    grid["label"] = grid.apply(
        lambda r: f"{r['tau_smact']:.2f}/{r['tau_smocc']:.2f}/{r['tau_drama']:.2f}",
        axis=1,
    )
    grid["x"] = range(len(grid))

    def apply_all_threshold_xticks(ax, labels):
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=75, ha="right", fontsize=8)

    # Figure 1: full threshold grid, sorted by numeric threshold values.
    fig, ax1 = plt.subplots(figsize=(16, 6.5))
    ax2 = ax1.twinx()

    throughput_color = "tab:blue"
    slowdown_color = "tab:orange"

    ax1.plot(
        grid["x"],
        grid["mean_throughput_gain"],
        marker="o",
        linewidth=2.0,
        markersize=4.5,
        color=throughput_color,
        label="Mean throughput gain",
    )
    ax2.plot(
        grid["x"],
        grid["worst_max_slowdown"],
        marker="s",
        linewidth=1.8,
        markersize=4.2,
        linestyle="--",
        color=slowdown_color,
        label="Worst max slowdown",
    )
    ax2.axhline(
        args.max_slowdown_budget,
        linestyle=":",
        linewidth=1.4,
        color="tab:red",
        label=f"Slowdown budget ({args.max_slowdown_budget:g}×)",
    )

    apply_all_threshold_xticks(ax1, grid["label"].tolist())

    ax1.set_xlabel("Threshold setting: SMACT / SMOCC / DRAMA")
    ax1.set_ylabel("Mean throughput gain")
    ax2.set_ylabel("Worst max slowdown")
    ax1.tick_params(axis="y", labelcolor="black")
    ax2.tick_params(axis="y", labelcolor="black")
    ax1.grid(axis="y", linestyle=":", alpha=0.35)

    ax1.set_title("Threshold grid: throughput benefit vs. slowdown cost")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", frameon=True)

    fig.tight_layout()
    fig.savefig(figs / "threshold_grid_throughput_vs_slowdown.png", dpi=240)
    plt.close(fig)

    # Figure 2: per-sequence throughput and slowdown across the full sorted grid.
    per_seq = df.copy()
    order_map = {name: i for i, name in enumerate(grid["threshold_dir"])}
    per_seq["threshold_index"] = per_seq["threshold_dir"].map(order_map)

    trial_ids = list(per_seq["trial_id"].drop_duplicates())
    fig, axes = plt.subplots(
        nrows=len(trial_ids),
        ncols=1,
        figsize=(16, max(9, 2.6 * len(trial_ids))),
        sharex=True,
    )
    if len(trial_ids) == 1:
        axes = [axes]

    for ax, trial_id in zip(axes, trial_ids):
        g = per_seq[per_seq["trial_id"] == trial_id].sort_values("threshold_index")
        ax2 = ax.twinx()

        ax.plot(
            g["threshold_index"],
            g["throughput_gain"],
            marker="o",
            linewidth=1.8,
            markersize=4,
            color=throughput_color,
            label="Throughput gain",
        )
        ax2.plot(
            g["threshold_index"],
            g["max_slowdown"],
            marker="s",
            linestyle="--",
            linewidth=1.5,
            markersize=3.8,
            color=slowdown_color,
            label="Max slowdown",
        )
        ax2.axhline(
            args.max_slowdown_budget,
            linestyle=":",
            linewidth=1.1,
            color="tab:red",
            label=f"Budget ({args.max_slowdown_budget:g}×)",
        )

        ax.set_ylabel("Throughput")
        ax2.set_ylabel("Slowdown")
        ax.tick_params(axis="y")
        ax2.tick_params(axis="y")
        ax.grid(axis="y", linestyle=":", alpha=0.30)
        ax.set_title(trial_id, fontsize=10)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="upper right")

    axes[-1].set_xlabel("Threshold setting: SMACT / SMOCC / DRAMA")
    apply_all_threshold_xticks(axes[-1], grid["label"].tolist())

    fig.suptitle("Per-sequence threshold sensitivity", y=1.0, fontsize=14)
    fig.tight_layout()
    fig.savefig(figs / "per_sequence_throughput_and_slowdown.png", dpi=240)
    plt.close(fig)

    # Figure 3: rejection diagnostics. Retries are not penalized; they show gating activity.
    fig, ax = plt.subplots(figsize=(16, 5.8))
    ax.bar(grid["x"], grid["total_reject_retries"], color="tab:gray", alpha=0.85)
    apply_all_threshold_xticks(ax, grid["label"].tolist())
    ax.set_xlabel("Threshold setting: SMACT / SMOCC / DRAMA")
    ax.set_ylabel("Total reject retries")
    ax.set_title("Rejection diagnostics: threshold gate activity")
    ax.grid(axis="y", linestyle=":", alpha=0.35)
    fig.tight_layout()
    fig.savefig(figs / "rejection_diagnostics.png", dpi=240)
    plt.close(fig)

    report = out / "threshold_decision_report.md"
    best = ranked.iloc[0]

    report.write_text(
        "\n".join([
            "# Threshold sweep decision report",
            "",
            "## Recommended setting",
            "",
            f"- Thresholds: SMACT={best['tau_smact']:.2f}, SMOCC={best['tau_smocc']:.2f}, DRAMA={best['tau_drama']:.2f}",
            f"- Mean throughput gain: {best['mean_throughput_gain']:.3f}",
            f"- Worst max slowdown: {best['worst_max_slowdown']:.3f}",
            f"- P95 max slowdown: {best['p95_max_slowdown']:.3f}",
            f"- Total reject retries: {int(best['total_reject_retries'])}",
            f"- Feasible under selected budgets: {bool(best['feasible'])}",
            "",
            "## Selection rule",
            "",
            f"A setting is marked feasible if all trials complete, no started jobs fail, "
            f"worst max slowdown <= {args.max_slowdown_budget}, "
            f"and p95 max slowdown <= {args.p95_slowdown_budget}. "
            f"Reject retries are reported as diagnostics, not as a feasibility penalty.",
            "",
            "## Main files",
            "",
            "- `tables/threshold_settings_ranked.csv`",
            "- `tables/threshold_settings_feasible.csv`",
            "- `tables/per_trial_sensitivity.csv`",
            "- `figures/threshold_decision_scatter.png`\n- `figures/top_threshold_settings_score.png`\n- `figures/top_thresholds_throughput_vs_slowdown.png`",
        ]),
        encoding="utf-8",
    )

    print(f"wrote {ranked_path}")
    print(f"wrote {feasible_path}")
    print(f"wrote {report}")
    print(f"wrote {figs / 'threshold_grid_throughput_vs_slowdown.png'}")
    print(f"wrote {figs / 'per_sequence_throughput_and_slowdown.png'}")
    print(f"wrote {figs / 'rejection_diagnostics.png'}")
    print("\nTOP 10:")
    print(ranked.head(10).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
