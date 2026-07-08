#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RUN_RE = re.compile(r"smact_(\d+p\d+)_smocc_(\d+p\d+)_drama_(\d+p\d+)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "One-stop analyzer for progressive threshold sweeps. "
            "Reads a sweep root, combines per-trial summaries, ranks thresholds, "
            "and writes report tables + figures."
        )
    )
    p.add_argument("--sweep-root", required=True, help="Directory containing smact_*/ progressive run folders.")
    p.add_argument("--output-dir", required=True, help="Directory where report/tables/figures are written.")
    p.add_argument("--max-slowdown-budget", type=float, default=2.0)
    p.add_argument("--p95-slowdown-budget", type=float, default=2.0)
    p.add_argument("--min-completion-fraction", type=float, default=1.0)
    return p.parse_args()


def parse_threshold_dir(run_dir: Path) -> tuple[float, float, float]:
    m = RUN_RE.fullmatch(run_dir.name)
    if not m:
        return (float("nan"), float("nan"), float("nan"))
    return tuple(float(x.replace("p", ".")) for x in m.groups())


def to_num(s: pd.Series | None, default: float = 0.0) -> pd.Series:
    if s is None:
        return pd.Series(dtype="float64")
    return pd.to_numeric(s, errors="coerce").fillna(default)


def safe_bool_true(s: pd.Series | None) -> pd.Series:
    if s is None:
        return pd.Series(dtype="bool")
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def load_metadata(sweep_root: Path) -> dict:
    p = sweep_root / "sweep_metadata.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_trials(sweep_root: Path) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []

    for summary_path in sorted(sweep_root.glob("smact_*/progressive_trial_summary.csv")):
        run_dir = summary_path.parent
        sub = pd.read_csv(summary_path)
        if sub.empty:
            continue

        tau_smact, tau_smocc, tau_drama = parse_threshold_dir(run_dir)
        sub["run_dir"] = str(run_dir)
        sub["threshold_dir"] = run_dir.name

        for col, val in {
            "tau_smact": tau_smact,
            "tau_smocc": tau_smocc,
            "tau_drama": tau_drama,
        }.items():
            if col not in sub.columns or sub[col].isna().all():
                sub[col] = val

        if "failed_started_rows" not in sub.columns:
            sub["failed_started_rows"] = 0

        if "reject_retry_count" not in sub.columns:
            obs_path = run_dir / "admission_observations.csv"
            if obs_path.exists():
                obs = pd.read_csv(obs_path)
                if "decision" in obs.columns:
                    sub["reject_retry_count"] = int((obs["decision"] == "reject_retry_later").sum())
                elif "rejected_stage" in obs.columns:
                    sub["reject_retry_count"] = int(obs["rejected_stage"].notna().sum())
                else:
                    sub["reject_retry_count"] = 0
            else:
                sub["reject_retry_count"] = 0

        rows.append(sub)

    if not rows:
        return pd.DataFrame()

    trials = pd.concat(rows, ignore_index=True)

    for c in [
        "tau_smact",
        "tau_smocc",
        "tau_drama",
        "planned_workload_count",
        "admitted_workload_count",
        "reject_retry_count",
        "sequence_wall_time_seconds",
        "throughput_gain",
        "mean_slowdown",
        "max_slowdown",
        "p95_slowdown",
        "failed_started_rows",
        "solo_runtime_sum_seconds",
    ]:
        if c in trials.columns:
            trials[c] = pd.to_numeric(trials[c], errors="coerce")

    if "trial_id" not in trials.columns:
        trials["trial_id"] = trials.groupby("threshold_dir").cumcount().map(lambda i: f"trial_{i:03d}")

    return trials


def aggregate_thresholds(trials: pd.DataFrame, metadata: dict) -> pd.DataFrame:
    rows = []

    for threshold_dir, g in trials.groupby("threshold_dir", dropna=False):
        tau_smact = to_num(g.get("tau_smact")).iloc[0] if "tau_smact" in g else float("nan")
        tau_smocc = to_num(g.get("tau_smocc")).iloc[0] if "tau_smocc" in g else float("nan")
        tau_drama = to_num(g.get("tau_drama")).iloc[0] if "tau_drama" in g else float("nan")

        planned = to_num(g.get("planned_workload_count"))
        admitted = to_num(g.get("admitted_workload_count"))
        throughput = pd.to_numeric(g.get("throughput_gain"), errors="coerce")
        max_slowdown = pd.to_numeric(g.get("max_slowdown"), errors="coerce")
        mean_slowdown = pd.to_numeric(g.get("mean_slowdown"), errors="coerce")
        p95_slowdown = pd.to_numeric(g.get("p95_slowdown"), errors="coerce") if "p95_slowdown" in g else max_slowdown
        failed = to_num(g.get("failed_started_rows"))
        retries = to_num(g.get("reject_retry_count"))

        completed = throughput.notna() & max_slowdown.notna() & (failed.fillna(0) == 0)
        num_trials = len(g)
        completion_fraction = float(completed.mean()) if num_trials else 0.0

        worst = max_slowdown.max()
        p95 = max_slowdown.quantile(0.95)
        mean_t = throughput.mean()
        score = mean_t / max(worst, 1.0) if pd.notna(mean_t) and pd.notna(worst) else float("nan")

        rows.append(
            {
                "threshold_dir": threshold_dir,
                "run_dir": g["run_dir"].iloc[0] if "run_dir" in g else "",
                "tau_smact": tau_smact,
                "tau_smocc": tau_smocc,
                "tau_drama": tau_drama,
                "num_trials": num_trials,
                "planned_workload_count_sum": planned.sum(),
                "admitted_workload_count_sum": admitted.sum(),
                "admission_fraction": admitted.sum() / planned.sum() if planned.sum() else float("nan"),
                "completion_fraction": completion_fraction,
                "mean_throughput_gain": mean_t,
                "median_throughput_gain": throughput.median(),
                "mean_slowdown": mean_slowdown.mean(),
                "median_max_slowdown": max_slowdown.median(),
                "max_slowdown": worst,
                "p95_max_slowdown": p95,
                "p95_slowdown_mean": p95_slowdown.mean(),
                "failed_started_rows": int(failed.sum()),
                "reject_retry_count": int(retries.sum()),
                "score": score,
                "manifest": metadata.get("plan_jsonl", ""),
                "solo_runtime_csv": metadata.get("solo_runtime_csv", ""),
            }
        )

    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame, path: Path, max_rows: int = 30) -> None:
    show = df.head(max_rows).copy()
    for c in show.columns:
        if pd.api.types.is_float_dtype(show[c]):
            show[c] = show[c].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    path.write_text(show.to_markdown(index=False), encoding="utf-8")


def add_labels(grid: pd.DataFrame) -> pd.DataFrame:
    grid = grid.sort_values(["tau_smact", "tau_smocc", "tau_drama"]).copy()
    grid["x"] = range(len(grid))
    grid["label"] = grid.apply(
        lambda r: f"{r['tau_smact']:.2f}/{r['tau_smocc']:.2f}/{r['tau_drama']:.2f}",
        axis=1,
    )
    return grid


def set_threshold_xticks(ax, labels: list[str]) -> None:
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=75, ha="right", fontsize=8)


def plot_grid(ranked: pd.DataFrame, figs: Path, max_slowdown_budget: float) -> Path:
    grid = add_labels(ranked)
    fig_path = figs / "threshold_grid_throughput_vs_slowdown.png"

    fig, ax1 = plt.subplots(figsize=(16, 6.5))
    ax2 = ax1.twinx()

    ax1.plot(
        grid["x"],
        grid["mean_throughput_gain"],
        marker="o",
        linewidth=2.0,
        markersize=4.5,
        label="Mean throughput gain",
    )
    ax2.plot(
        grid["x"],
        grid["max_slowdown"],
        marker="s",
        linewidth=1.8,
        markersize=4.2,
        linestyle="--",
        label="Worst max slowdown",
    )
    ax2.axhline(
        max_slowdown_budget,
        linestyle=":",
        linewidth=1.4,
        label=f"Slowdown budget ({max_slowdown_budget:g}×)",
    )

    ax1.set_ylim(bottom=0)
    ax2.set_ylim(bottom=0)

    set_threshold_xticks(ax1, grid["label"].tolist())
    ax1.set_xlabel("Threshold setting: SMACT / SMOCC / DRAMA")
    ax1.set_ylabel("Mean throughput gain")
    ax2.set_ylabel("Worst max slowdown")
    ax1.grid(axis="y", linestyle=":", alpha=0.35)
    ax1.set_title("Threshold grid: throughput benefit vs. slowdown cost")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", frameon=True)

    fig.tight_layout()
    fig.savefig(fig_path, dpi=240)
    plt.close(fig)

    return fig_path


def plot_per_sequence(
    trials: pd.DataFrame,
    ranked: pd.DataFrame,
    figs: Path,
    max_slowdown_budget: float,
) -> Path | None:
    needed = {"threshold_dir", "trial_id", "throughput_gain", "max_slowdown"}
    if not needed.issubset(trials.columns):
        return None

    grid = add_labels(ranked)
    order_map = {name: i for i, name in enumerate(grid["threshold_dir"])}
    label_map = {i: label for i, label in enumerate(grid["label"])}

    per_seq = trials.copy()
    per_seq["threshold_index"] = per_seq["threshold_dir"].map(order_map)
    per_seq = per_seq.dropna(subset=["threshold_index"])
    per_seq["threshold_index"] = per_seq["threshold_index"].astype(int)

    trial_ids = list(per_seq["trial_id"].drop_duplicates())
    if not trial_ids:
        return None

    fig_path = figs / "per_sequence_throughput_and_slowdown.png"

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
            label="Throughput gain",
        )
        ax2.plot(
            g["threshold_index"],
            g["max_slowdown"],
            marker="s",
            linestyle="--",
            linewidth=1.5,
            markersize=3.8,
            label="Max slowdown",
        )
        ax2.axhline(
            max_slowdown_budget,
            linestyle=":",
            linewidth=1.1,
            label=f"Budget ({max_slowdown_budget:g}×)",
        )

        ax.set_ylim(bottom=0)
        ax2.set_ylim(bottom=0)

        ax.set_ylabel("Throughput")
        ax2.set_ylabel("Slowdown")
        ax.grid(axis="y", linestyle=":", alpha=0.30)
        ax.set_title(str(trial_id), fontsize=10)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="upper right")

    axes[-1].set_xlabel("Threshold setting: SMACT / SMOCC / DRAMA")
    set_threshold_xticks(axes[-1], [label_map[i] for i in range(len(grid))])

    fig.suptitle("Per-sequence threshold sensitivity", y=1.0, fontsize=14)
    fig.tight_layout()
    fig.savefig(fig_path, dpi=240)
    plt.close(fig)

    return fig_path


def plot_rejections(ranked: pd.DataFrame, figs: Path) -> Path:
    grid = add_labels(ranked)
    fig_path = figs / "rejection_diagnostics.png"

    fig, ax = plt.subplots(figsize=(16, 5.8))
    ax.bar(grid["x"], grid["reject_retry_count"])
    set_threshold_xticks(ax, grid["label"].tolist())
    ax.set_xlabel("Threshold setting: SMACT / SMOCC / DRAMA")
    ax.set_ylabel("Total admission deferrals")
    ax.set_title("Admission-control diagnostics: deferred placement attempts")
    ax.grid(axis="y", linestyle=":", alpha=0.35)

    fig.tight_layout()
    fig.savefig(fig_path, dpi=240)
    plt.close(fig)

    return fig_path


def pick_threshold_row(summary: pd.DataFrame, tau: tuple[float, float, float]) -> pd.Series | None:
    smact, smocc, drama = tau
    m = (
        summary["tau_smact"].round(4).eq(smact)
        & summary["tau_smocc"].round(4).eq(smocc)
        & summary["tau_drama"].round(4).eq(drama)
    )
    if not m.any():
        return None
    return summary[m].iloc[0]


def plot_paper_threshold_tradeoff(summary: pd.DataFrame, figs: Path) -> Path | None:
    """Create the main paper threshold trade-off figure.

    The figure uses representative operating points rather than the full grid,
    so it remains readable in the paper while showing the trend from strict
    admission to near-admit-all behavior.
    """
    selected = [
        ("Strict", (0.10, 0.05, 0.10)),
        ("Conservative", (0.50, 0.20, 0.40)),
        ("Selected", (0.65, 0.35, 0.50)),
        ("Permissive", (0.80, 0.65, 0.60)),
        ("Very permissive", (0.95, 0.95, 0.95)),
        ("Admit-all", (1.00, 1.00, 1.00)),
    ]

    rows = []
    for name, tau in selected:
        r = pick_threshold_row(summary, tau)
        if r is None:
            print(f"warning: missing threshold setting {name}: {tau}")
            continue

        rows.append(
            {
                "name": name,
                "label": f"{tau[0]:.2f}/{tau[1]:.2f}/{tau[2]:.2f}",
                "mean_throughput_gain": float(r["mean_throughput_gain"]),
                "max_slowdown": float(r["max_slowdown"]),
                "mean_slowdown": float(r["mean_slowdown"]),
                "reject_retry_count": int(r["reject_retry_count"]),
            }
        )

    if len(rows) < 2:
        return None

    paper = pd.DataFrame(rows)
    x = range(len(paper))

    fig_path = figs / "paper_threshold_tradeoff_with_deferrals.png"

    fig, (ax_top, ax_bottom) = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(9.2, 6.2),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.0]},
    )

    ax_slow = ax_top.twinx()

    throughput_color = "#0072B2"  # blue, color-blind friendly
    mean_slowdown_color = "#009E73"  # bluish green, color-blind friendly
    worst_slowdown_color = "#D55E00"  # vermillion, color-blind friendly
    selected_color = "#000000"
    bar_color = "#B0B0B0"

    ax_top.plot(
        x,
        paper["mean_throughput_gain"],
        marker="o",
        linestyle="-",
        linewidth=3.0,
        markersize=8.0,
        color=throughput_color,
        label="Mean throughput gain",
    )
    ax_slow.plot(
        x,
        paper["mean_slowdown"],
        marker="^",
        linestyle="-.",
        linewidth=3.0,
        markersize=7.5,
        color=mean_slowdown_color,
        label="Mean slowdown",
    )
    ax_slow.plot(
        x,
        paper["max_slowdown"],
        marker="s",
        linestyle="--",
        linewidth=3.0,
        markersize=7.5,
        color=worst_slowdown_color,
        label="Worst slowdown",
    )

    selected_idx = paper.index[paper["name"] == "Selected"].tolist()
    if selected_idx:
        sx = selected_idx[0]
        ax_top.axvline(sx, linestyle=":", linewidth=2.2, color=selected_color)
        ax_bottom.axvline(sx, linestyle=":", linewidth=2.2, color=selected_color)

    ax_top.set_ylabel("Throughput gain", fontsize=15)
    ax_slow.set_ylabel("Slowdown", fontsize=15)
    ax_top.set_ylim(bottom=0)
    ax_slow.set_ylim(bottom=0)
    ax_top.grid(axis="y", linestyle=":", alpha=0.35)

    lines1, labels1 = ax_top.get_legend_handles_labels()
    lines2, labels2 = ax_slow.get_legend_handles_labels()
    ax_top.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True, fontsize=13)

    ax_bottom.bar(x, paper["reject_retry_count"], color=bar_color, edgecolor="black", linewidth=1.0)
    ax_bottom.set_ylabel("Admission\ndeferrals", fontsize=15)
    ax_bottom.set_ylim(bottom=0)
    ax_bottom.grid(axis="y", linestyle=":", alpha=0.35)

    ax_bottom.set_xticks(list(x))
    ax_bottom.set_xticklabels(
        [f"{n}\n({l})" for n, l in zip(paper["name"], paper["label"])],
        rotation=30,
        ha="right",
        fontsize=13,
    )

    # ax_top.set_title("Admission-threshold trade-off", fontsize=16)
    ax_top.tick_params(axis="both", labelsize=13, width=1.4)
    ax_slow.tick_params(axis="y", labelsize=13, width=1.4)
    ax_bottom.tick_params(axis="both", labelsize=13, width=1.4)
    for ax in (ax_top, ax_slow, ax_bottom):
        for spine in ax.spines.values():
            spine.set_linewidth(1.4)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.33)
    fig.savefig(fig_path, dpi=300)
    fig.savefig(fig_path.with_suffix(".pdf"))
    plt.close(fig)

    return fig_path




def plot_paper_threshold_slowdown_tails(summary: pd.DataFrame, figs: Path) -> Path | None:
    """Create companion paper threshold figure with throughput and slowdown tails.

    This uses the same representative threshold settings as
    plot_paper_threshold_tradeoff(), so the figures are directly comparable.
    It keeps throughput gain in the top panel and adds P95 slowdown alongside
    mean and worst slowdown.
    """
    selected = [
        ("Strict", (0.10, 0.05, 0.10)),
        ("Conservative", (0.50, 0.20, 0.40)),
        ("Selected", (0.65, 0.35, 0.50)),
        ("Permissive", (0.80, 0.65, 0.60)),
        ("Very permissive", (0.95, 0.95, 0.95)),
        ("Admit-all", (1.00, 1.00, 1.00)),
    ]

    rows = []
    for name, tau in selected:
        r = pick_threshold_row(summary, tau)
        if r is None:
            print(f"warning: missing threshold setting {name}: {tau}")
            continue

        rows.append(
            {
                "name": name,
                "label": f"{tau[0]:.2f}/{tau[1]:.2f}/{tau[2]:.2f}",
                "mean_throughput_gain": float(r["mean_throughput_gain"]),
                "mean_slowdown": float(r["mean_slowdown"]),
                "p95_slowdown": float(r["p95_slowdown_mean"]),
                "max_slowdown": float(r["max_slowdown"]),
                "reject_retry_count": int(r["reject_retry_count"]),
            }
        )

    if len(rows) < 2:
        return None

    paper = pd.DataFrame(rows)
    x = range(len(paper))

    fig_path = figs / "paper_threshold_tradeoff_tails_with_deferrals.png"

    fig, (ax_top, ax_bottom) = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(9.2, 6.2),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.0]},
    )

    ax_slow = ax_top.twinx()

    throughput_color = "#0072B2"      # blue, color-blind friendly
    mean_slowdown_color = "#009E73"   # bluish green, color-blind friendly
    p95_slowdown_color = "#CC79A7"    # reddish purple, color-blind friendly
    worst_slowdown_color = "#D55E00"  # vermillion, color-blind friendly
    selected_color = "#000000"
    bar_color = "#B0B0B0"

    ax_top.plot(
        x,
        paper["mean_throughput_gain"],
        marker="o",
        linestyle="-",
        linewidth=3.0,
        markersize=8.0,
        color=throughput_color,
        label="Mean throughput gain",
    )
    ax_slow.plot(
        x,
        paper["mean_slowdown"],
        marker="^",
        linestyle="-.",
        linewidth=3.0,
        markersize=7.5,
        color=mean_slowdown_color,
        label="Mean slowdown",
    )
    ax_slow.plot(
        x,
        paper["p95_slowdown"],
        marker="D",
        linestyle=":",
        linewidth=3.0,
        markersize=7.0,
        color=p95_slowdown_color,
        label="P95 slowdown",
    )
    ax_slow.plot(
        x,
        paper["max_slowdown"],
        marker="s",
        linestyle="--",
        linewidth=3.0,
        markersize=7.5,
        color=worst_slowdown_color,
        label="Worst slowdown",
    )

    selected_idx = paper.index[paper["name"] == "Selected"].tolist()
    if selected_idx:
        sx = selected_idx[0]
        ax_top.axvline(sx, linestyle=":", linewidth=2.2, color=selected_color)
        ax_bottom.axvline(sx, linestyle=":", linewidth=2.2, color=selected_color)

    ax_top.set_ylabel("Throughput gain", fontsize=15)
    ax_slow.set_ylabel("Slowdown", fontsize=15)
    ax_top.set_ylim(bottom=0)
    ax_slow.set_ylim(bottom=0)
    ax_top.grid(axis="y", linestyle=":", alpha=0.35)

    lines1, labels1 = ax_top.get_legend_handles_labels()
    lines2, labels2 = ax_slow.get_legend_handles_labels()
    ax_top.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True, fontsize=13)

    ax_bottom.bar(x, paper["reject_retry_count"], color=bar_color, edgecolor="black", linewidth=1.0)
    ax_bottom.set_ylabel("Placement\\ndeferrals", fontsize=15)
    ax_bottom.set_ylim(bottom=0)
    ax_bottom.grid(axis="y", linestyle=":", alpha=0.35)

    ax_bottom.set_xticks(list(x))
    ax_bottom.set_xticklabels(
        [f"{n}\n({l})" for n, l in zip(paper["name"], paper["label"])],
        rotation=30,
        ha="right",
        fontsize=13,
    )

    ax_top.tick_params(axis="both", labelsize=13, width=1.4)
    ax_slow.tick_params(axis="y", labelsize=13, width=1.4)
    ax_bottom.tick_params(axis="both", labelsize=13, width=1.4)
    for ax in (ax_top, ax_slow, ax_bottom):
        for spine in ax.spines.values():
            spine.set_linewidth(1.4)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.33)
    fig.savefig(fig_path, dpi=300)
    fig.savefig(fig_path.with_suffix(".pdf"))
    plt.close(fig)

    return fig_path


def main() -> int:

    args = parse_args()

    sweep_root = Path(args.sweep_root)
    out = Path(args.output_dir)
    tables = out / "tables"
    figs = out / "figures"

    tables.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)

    metadata = load_metadata(sweep_root)

    trials = load_trials(sweep_root)
    if trials.empty:
        raise SystemExit(f"No progressive_trial_summary.csv files found under {sweep_root}/smact_*/")

    trials_path = tables / "threshold_sweep_trials_combined.csv"
    trials.to_csv(trials_path, index=False)

    summary = aggregate_thresholds(trials, metadata)
    summary_path = tables / "threshold_sweep_summary.csv"
    summary.to_csv(summary_path, index=False)

    ranked = summary.copy()
    ranked["feasible"] = (
        (ranked["completion_fraction"] >= args.min_completion_fraction)
        & (ranked["failed_started_rows"] == 0)
        & (ranked["max_slowdown"] <= args.max_slowdown_budget)
        & (ranked["p95_max_slowdown"] <= args.p95_slowdown_budget)
    )
    ranked = ranked.sort_values(
        ["feasible", "score", "mean_throughput_gain"],
        ascending=[False, False, False],
    )

    ranked_path = tables / "threshold_settings_ranked.csv"
    ranked.to_csv(ranked_path, index=False)
    markdown_table(ranked, tables / "threshold_settings_ranked.md")

    feasible = ranked[ranked["feasible"]].copy()
    feasible_path = tables / "threshold_settings_feasible.csv"
    feasible.to_csv(feasible_path, index=False)
    markdown_table(feasible, tables / "threshold_settings_feasible.md")

    per_trial = (
        trials.groupby("trial_id")
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

    grid_fig = plot_grid(ranked, figs, args.max_slowdown_budget)
    seq_fig = plot_per_sequence(trials, ranked, figs, args.max_slowdown_budget)
    rej_fig = plot_rejections(ranked, figs)
    paper_fig = plot_paper_threshold_tradeoff(summary, figs)
    paper_tail_fig = plot_paper_threshold_slowdown_tails(summary, figs)

    best = ranked.iloc[0]
    report_lines = [
        "# Threshold sweep report",
        "",
        f"Sweep root: `{sweep_root}`",
        "",
        "## Recommended setting",
        "",
        f"- Thresholds: SMACT={best['tau_smact']:.2f}, SMOCC={best['tau_smocc']:.2f}, DRAMA={best['tau_drama']:.2f}",
        f"- Mean throughput gain: {best['mean_throughput_gain']:.3f}",
        f"- Worst max slowdown: {best['max_slowdown']:.3f}",
        f"- P95 max slowdown: {best['p95_max_slowdown']:.3f}",
        f"- Total admission deferrals: {int(best['reject_retry_count'])}",
        f"- Feasible under selected budgets: {bool(best['feasible'])}",
        "",
        "## Selection rule",
        "",
        f"Feasible means completion_fraction >= {args.min_completion_fraction}, no started-job failures, "
        f"max_slowdown <= {args.max_slowdown_budget}, and p95_max_slowdown <= {args.p95_slowdown_budget}.",
        "",
        "## Main files",
        "",
        "- `tables/threshold_sweep_trials_combined.csv`",
        "- `tables/threshold_sweep_summary.csv`",
        "- `tables/threshold_settings_ranked.csv`",
        "- `tables/threshold_settings_feasible.csv`",
        "- `tables/per_trial_sensitivity.csv`",
        "- `figures/threshold_grid_throughput_vs_slowdown.png`",
        "- `figures/rejection_diagnostics.png`",
    ]

    if seq_fig is not None:
        report_lines.append("- `figures/per_sequence_throughput_and_slowdown.png`")

    if paper_fig is not None:
        report_lines.append("- `figures/paper_threshold_tradeoff_with_deferrals.png`")

    if paper_tail_fig is not None:
        report_lines.append("- `figures/paper_threshold_tradeoff_tails_with_deferrals.png`")

    (out / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"wrote {trials_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {ranked_path}")
    print(f"wrote {feasible_path}")
    print(f"wrote {grid_fig}")

    if seq_fig is not None:
        print(f"wrote {seq_fig}")

    print(f"wrote {rej_fig}")

    if paper_fig is not None:
        print(f"wrote {paper_fig}")

    if paper_tail_fig is not None:
        print(f"wrote {paper_tail_fig}")

    print(f"wrote {out / 'report.md'}")

    print("\nTOP 10:")
    cols = [
        "tau_smact",
        "tau_smocc",
        "tau_drama",
        "num_trials",
        "completion_fraction",
        "mean_throughput_gain",
        "max_slowdown",
        "p95_max_slowdown",
        "reject_retry_count",
        "feasible",
        "score",
    ]
    print(ranked[cols].head(10).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())