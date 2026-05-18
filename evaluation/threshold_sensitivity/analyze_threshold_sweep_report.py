#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_SWEEPS = {
    "normal_grid_fresh_solo": Path(
        "evaluation/threshold_sensitivity/results/phase1_short_grid_recomputed_fresh_solo"
    ),
    "low_threshold_grid": Path(
        "evaluation/threshold_sensitivity/results/phase1_short_low_threshold_grid"
    ),
}

RUN_NAME_RE = re.compile(r"smact_(\dp\d+)_smocc_(\dp\d+)_drama_(\dp\d+)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a Markdown + figures report for threshold-sensitivity sweeps."
    )
    p.add_argument(
        "--output-dir",
        default="evaluation/threshold_sensitivity/reports/phase1_short_threshold_analysis",
        help="Directory where report.md, tables, and figures are written.",
    )
    p.add_argument(
        "--sweep",
        action="append",
        default=None,
        help=(
            "Sweep entry as name=path. Can be repeated. "
            "Defaults to hard-coded phase1 short normal/low threshold sweeps."
        ),
    )
    return p.parse_args()


def parse_thresholds_from_run_dir(path: Path) -> tuple[float, float, float] | None:
    m = RUN_NAME_RE.fullmatch(path.name)
    if not m:
        return None
    return tuple(float(x.replace("p", ".")) for x in m.groups())


def load_sweep_summary(root: Path) -> pd.DataFrame:
    """Build the sweep summary by scanning all per-setting folders.

    We intentionally do not trust an existing threshold_sweep_summary.csv here,
    because users may add/resume extra threshold folders after that aggregate
    file was created.
    """
    rows = []

    for p in sorted(root.glob("smact_*/progressive_trial_summary.csv")):
        run_dir = p.parent
        sub = pd.read_csv(p)

        vals = parse_thresholds_from_run_dir(run_dir)
        if vals is not None:
            sub["tau_smact"], sub["tau_smocc"], sub["tau_drama"] = vals

        sub["run_dir"] = str(run_dir)
        rows.append(sub)

    if not rows:
        return pd.DataFrame()

    trial_df = pd.concat(rows, ignore_index=True)
    return aggregate_trial_rows(trial_df)


def aggregate_trial_rows(trial_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["tau_smact", "tau_smocc", "tau_drama"]

    for keys, g in trial_df.groupby(group_cols, dropna=False):
        throughput = pd.to_numeric(g.get("throughput_gain"), errors="coerce")
        max_slowdown = pd.to_numeric(g.get("max_slowdown"), errors="coerce")
        mean_slowdown = pd.to_numeric(g.get("mean_slowdown"), errors="coerce")

        planned = pd.to_numeric(g.get("planned_workload_count"), errors="coerce").sum()
        admitted = pd.to_numeric(g.get("admitted_workload_count"), errors="coerce").sum()

        rows.append(
            {
                "tau_smact": keys[0],
                "tau_smocc": keys[1],
                "tau_drama": keys[2],
                "num_trials": len(g),
                "planned_workload_count_sum": planned,
                "admitted_workload_count_sum": admitted,
                "admission_fraction": admitted / planned if planned else float("nan"),
                "completion_fraction": throughput.notna().mean(),
                "mean_throughput_gain": throughput.mean(),
                "median_throughput_gain": throughput.median(),
                "mean_slowdown": mean_slowdown.mean(),
                "median_max_slowdown": max_slowdown.median(),
                "max_slowdown": max_slowdown.max(),
                "p95_slowdown_mean": pd.to_numeric(g.get("p95_slowdown"), errors="coerce").mean()
                if "p95_slowdown" in g.columns
                else float("nan"),
                "reject_retry_count": int(
                    g.get("rejected_stage", pd.Series(dtype=object)).notna().sum()
                ),
            }
        )

    return pd.DataFrame(rows)


def load_observations(root: Path) -> pd.DataFrame:
    rows = []
    for p in sorted(root.glob("smact_*/admission_observations.csv")):
        sub = pd.read_csv(p)
        sub["run_dir"] = p.parent.name
        vals = parse_thresholds_from_run_dir(p.parent)
        if vals is not None:
            sub["tau_smact"], sub["tau_smocc"], sub["tau_drama"] = vals
        rows.append(sub)

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def describe_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    for col in columns:
        if col not in df.columns:
            continue
        x = pd.to_numeric(df[col], errors="coerce").dropna()
        if x.empty:
            continue
        d = x.describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95])
        rows.append(
            {
                "metric": col,
                "count": d.get("count"),
                "mean": d.get("mean"),
                "std": d.get("std"),
                "min": d.get("min"),
                "p25": d.get("25%"),
                "median": d.get("50%"),
                "p75": d.get("75%"),
                "p90": d.get("90%"),
                "p95": d.get("95%"),
                "max": d.get("max"),
            }
        )
    return pd.DataFrame(rows)


def save_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows._\n"

    show = df.head(max_rows).copy()
    for col in show.columns:
        if pd.api.types.is_float_dtype(show[col]):
            show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")

    return show.to_markdown(index=False)


def plot_tradeoff(df: pd.DataFrame, out: Path, title: str) -> Path | None:
    needed = {"max_slowdown", "mean_throughput_gain"}
    if not needed.issubset(df.columns):
        return None

    sub = df.dropna(subset=list(needed)).copy()
    if sub.empty:
        return None

    fig_path = out / "figures" / f"{safe_name(title)}_tradeoff.png"
    fig_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 5))
    plt.scatter(sub["max_slowdown"], sub["mean_throughput_gain"])

    for _, r in sub.sort_values("mean_throughput_gain", ascending=False).head(5).iterrows():
        label = f"{r.get('tau_smact', float('nan')):.2f}/{r.get('tau_smocc', float('nan')):.2f}/{r.get('tau_drama', float('nan')):.2f}"
        plt.annotate(label, (r["max_slowdown"], r["mean_throughput_gain"]), fontsize=8)

    plt.xlabel("Maximum slowdown")
    plt.ylabel("Mean throughput gain")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=200)
    plt.close()

    return fig_path


def plot_heatmaps(df: pd.DataFrame, out: Path, sweep_name: str) -> list[Path]:
    paths = []
    metrics = ["mean_throughput_gain", "max_slowdown", "reject_retry_count", "admission_fraction"]

    required = {"tau_smact", "tau_smocc", "tau_drama"}
    if not required.issubset(df.columns):
        return paths

    for metric in metrics:
        if metric not in df.columns:
            continue

        for tau_smact, sub in df.groupby("tau_smact"):
            pivot = sub.pivot_table(
                index="tau_smocc",
                columns="tau_drama",
                values=metric,
                aggfunc="mean",
            )

            if pivot.empty:
                continue

            smact_label = f"{float(tau_smact):.2f}".replace(".", "p")
            fig_path = (
                out
                / "figures"
                / f"{safe_name(sweep_name)}_{metric}_smact_{smact_label}.png"
            )
            fig_path.parent.mkdir(parents=True, exist_ok=True)

            plt.figure(figsize=(6, 4))
            im = plt.imshow(pivot.values, aspect="auto", origin="lower")
            plt.colorbar(im, label=metric)
            plt.xticks(range(len(pivot.columns)), [f"{x:.2f}" for x in pivot.columns])
            plt.yticks(range(len(pivot.index)), [f"{x:.2f}" for x in pivot.index])
            plt.xlabel("DRAMA threshold")
            plt.ylabel("SMOCC threshold")
            plt.title(f"{sweep_name}: {metric}, SMACT={float(tau_smact):.2f}")

            for i, smocc in enumerate(pivot.index):
                for j, drama in enumerate(pivot.columns):
                    val = pivot.loc[smocc, drama]
                    if pd.notna(val):
                        plt.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8)

            plt.tight_layout()
            plt.savefig(fig_path, dpi=200)
            plt.close()
            paths.append(fig_path)

    return paths


def safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in s)


def relative_link(path: Path, base: Path) -> str:
    return str(path.relative_to(base))


def main() -> int:
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    sweeps = DEFAULT_SWEEPS.copy()
    if args.sweep:
        sweeps = {}
        for item in args.sweep:
            if "=" not in item:
                raise ValueError(f"Invalid --sweep entry: {item}. Expected name=path.")
            name, path = item.split("=", 1)
            sweeps[name] = Path(path)

    report_parts = [
        "# Threshold Sensitivity Report\n",
        "This report summarizes threshold-sensitivity runs, including aggregate tables, rejection diagnostics, and figures.\n",
    ]

    for name, root in sweeps.items():
        report_parts.append(f"\n## Sweep: `{name}`\n")
        report_parts.append(f"Path: `{root}`\n")

        summary = load_sweep_summary(root)
        observations = load_observations(root)

        if summary.empty:
            report_parts.append("\n_No summary data found._\n")
            continue

        save_table(summary, out / "tables" / f"{safe_name(name)}_threshold_sweep_summary.csv")

        metric_desc = describe_numeric(
            summary,
            [
                "admission_fraction",
                "completion_fraction",
                "mean_throughput_gain",
                "mean_slowdown",
                "max_slowdown",
                "reject_retry_count",
            ],
        )
        save_table(metric_desc, out / "tables" / f"{safe_name(name)}_metric_describe.csv")

        report_parts.append("\n### Aggregate metric summary\n\n")
        report_parts.append(markdown_table(metric_desc, max_rows=50))

        ranked = summary.copy()
        if "mean_throughput_gain" in ranked.columns and "max_slowdown" in ranked.columns:
            ranked["score"] = pd.to_numeric(ranked["mean_throughput_gain"], errors="coerce") / pd.to_numeric(
                ranked["max_slowdown"], errors="coerce"
            ).clip(lower=1.0)
            ranked = ranked.sort_values(
                ["completion_fraction", "score", "mean_throughput_gain"],
                ascending=[False, False, False],
            )

        save_table(ranked, out / "tables" / f"{safe_name(name)}_ranked_settings.csv")

        report_parts.append("\n### Top ranked settings\n\n")
        cols = [
            "tau_smact",
            "tau_smocc",
            "tau_drama",
            "num_trials",
            "admission_fraction",
            "completion_fraction",
            "mean_throughput_gain",
            "mean_slowdown",
            "max_slowdown",
            "reject_retry_count",
            "score",
        ]
        cols = [c for c in cols if c in ranked.columns]
        report_parts.append(markdown_table(ranked[cols], max_rows=15))

        if not observations.empty:
            save_table(observations, out / "tables" / f"{safe_name(name)}_admission_observations.csv")

            rejected = observations[observations["candidate_started"] != True].copy()
            save_table(rejected, out / "tables" / f"{safe_name(name)}_rejected_rows.csv")

            report_parts.append("\n### Rejection diagnostics\n\n")
            report_parts.append(f"Rejected/delayed rows: **{len(rejected)}**\n\n")

            if not rejected.empty:
                reject_desc = describe_numeric(
                    rejected,
                    ["smact_risk", "smocc_risk", "drama_risk", "running_job_count_before"],
                )
                save_table(reject_desc, out / "tables" / f"{safe_name(name)}_rejected_metric_describe.csv")
                report_parts.append(markdown_table(reject_desc, max_rows=50))

                sample_cols = [
                    "run_dir",
                    "trial_id",
                    "stage",
                    "smact_risk",
                    "smocc_risk",
                    "drama_risk",
                    "running_job_count_before",
                    "running_job_count_after",
                    "candidate_started",
                ]
                sample_cols = [c for c in sample_cols if c in rejected.columns]
                report_parts.append("\n### Sample rejected/delayed rows\n\n")
                report_parts.append(markdown_table(rejected[sample_cols], max_rows=20))

        tradeoff = plot_tradeoff(summary, out, name)
        heatmaps = plot_heatmaps(summary, out, name)

        report_parts.append("\n### Figures\n\n")
        if tradeoff is not None:
            report_parts.append(f"![{name} tradeoff]({relative_link(tradeoff, out)})\n\n")

        for fig in heatmaps[:12]:
            report_parts.append(f"![{fig.stem}]({relative_link(fig, out)})\n\n")

    report_path = out / "report.md"
    report_path.write_text("\n".join(report_parts), encoding="utf-8")

    print(f"wrote report: {report_path}")
    print(f"wrote tables: {out / 'tables'}")
    print(f"wrote figures: {out / 'figures'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
