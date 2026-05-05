#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_RISK_METRICS = ["smact_risk", "smocc_risk", "drama_risk"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Create a compact markdown summary for threshold window analysis."
    )
    p.add_argument("--analysis-dir", required=True, help="Directory containing window_stability_summary.csv.")
    p.add_argument("--measurements-csv", default=None, help="Optional live_threshold_measurements.csv.")
    p.add_argument("--output-md", default=None)
    p.add_argument("--reference-window", type=float, default=200.0)
    p.add_argument("--decision-window", type=float, default=30.0)
    p.add_argument("--top-k", type=int, default=10)
    return p.parse_args()


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int) -> str:
    if df.empty:
        return "_No data available._\n"

    cols = [c for c in columns if c in df.columns]
    if not cols:
        return "_Requested columns are missing._\n"

    out = df[cols].head(max_rows).copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].round(5)

    return out.to_markdown(index=False) + "\n"


def summarize_stability_table(
    summary: pd.DataFrame,
    *,
    metrics: list[str],
    reference_window: float,
) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()

    out = summary[
        (summary["metric"].isin(metrics))
        & (summary["reference_window_seconds"] == float(reference_window))
    ].copy()

    out["summary_window_seconds"] = pd.to_numeric(out["summary_window_seconds"], errors="coerce")
    return out.sort_values(["metric", "summary_window_seconds"])


def build_top_decision_window_mismatches(
    long_df: pd.DataFrame,
    *,
    metrics: list[str],
    decision_window: float,
    reference_window: float,
    top_k: int,
) -> pd.DataFrame:
    if long_df.empty:
        return pd.DataFrame()

    needed = {"row_index", "metric", "summary_window_seconds", "value"}
    if not needed.issubset(long_df.columns):
        return pd.DataFrame()

    id_cols = [
        c
        for c in [
            "row_index",
            "run_id",
            "task_path",
            "finish_status",
            "return_code",
            "total_runtime_seconds",
            "ttfk_wait_seconds",
        ]
        if c in long_df.columns
    ]

    rows = []

    for metric in metrics:
        metric_df = long_df[long_df["metric"] == metric].copy()
        if metric_df.empty:
            continue

        pivot = metric_df.pivot_table(
            index=id_cols,
            columns="summary_window_seconds",
            values="value",
            aggfunc="first",
        ).reset_index()

        if decision_window not in pivot.columns or reference_window not in pivot.columns:
            continue

        pivot["metric"] = metric
        pivot["decision_window_seconds"] = float(decision_window)
        pivot["reference_window_seconds"] = float(reference_window)
        pivot["value_decision"] = pd.to_numeric(pivot[decision_window], errors="coerce")
        pivot["value_reference"] = pd.to_numeric(pivot[reference_window], errors="coerce")
        pivot["abs_error"] = (pivot["value_decision"] - pivot["value_reference"]).abs()

        denom = pivot["value_reference"].abs()
        pivot["relative_error"] = pivot["abs_error"] / denom.where(denom > 1e-9)

        rows.append(pivot)

    if not rows:
        return pd.DataFrame()

    out = pd.concat(rows, ignore_index=True)
    out["abs_error"] = pd.to_numeric(out["abs_error"], errors="coerce")
    return out.sort_values("abs_error", ascending=False).head(top_k)


def build_summary(
    *,
    stability: pd.DataFrame,
    long_df: pd.DataFrame,
    measurements: pd.DataFrame,
    reference_window: float,
    decision_window: float,
    top_k: int,
) -> str:
    lines: list[str] = []

    lines.append("# Threshold Window Analysis Summary\n")
    lines.append(
        "This summary compares shorter TTFK-anchored monitoring windows against "
        f"a {reference_window:g}s reference window.\n"
    )

    lines.append("## Measurement coverage\n")
    if measurements.empty:
        lines.append("_Measurement CSV not provided or missing._\n")
    else:
        lines.append(f"- measurement rows: `{len(measurements)}`\n")
        if "summary_windows_collected" in measurements.columns:
            counts = (
                measurements["summary_windows_collected"]
                .value_counts(dropna=False)
                .rename_axis("summary_windows_collected")
                .reset_index(name="count")
            )
            lines.append(markdown_table(counts, ["summary_windows_collected", "count"], max_rows=20))

    lines.append("\n## Stability versus reference window\n")
    table = summarize_stability_table(
        stability,
        metrics=DEFAULT_RISK_METRICS,
        reference_window=reference_window,
    )
    lines.append(
        markdown_table(
            table,
            [
                "metric",
                "summary_window_seconds",
                "reference_window_seconds",
                "n",
                "mean_abs_error",
                "median_abs_error",
                "p95_abs_error",
                "mean_abs_relative_error",
            ],
            max_rows=100,
        )
    )

    lines.append(f"\n## Largest {decision_window:g}s-vs-{reference_window:g}s mismatches\n")
    mismatches = build_top_decision_window_mismatches(
        long_df,
        metrics=DEFAULT_RISK_METRICS,
        decision_window=decision_window,
        reference_window=reference_window,
        top_k=top_k,
    )
    lines.append(
        markdown_table(
            mismatches,
            [
                "metric",
                "task_path",
                "value_decision",
                "value_reference",
                "abs_error",
                "relative_error",
                "total_runtime_seconds",
                "ttfk_wait_seconds",
            ],
            max_rows=top_k,
        )
    )

    lines.append("\n## Notes\n")
    lines.append(
        "- The unsuffixed live-runner metric columns correspond to the decision window.\n"
        "- Suffixed columns such as `smact_risk_w30s` and `smact_risk_w200s` correspond to explicit summary windows.\n"
        "- Large error at 30s means the 30s decision window does not match the 200s reference for that workload/metric.\n"
        "- This file is generated from `window_stability_summary.csv` and `window_metrics_long.csv`.\n"
    )

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    analysis_dir = Path(args.analysis_dir)
    output_md = Path(args.output_md) if args.output_md else analysis_dir / "window_analysis_summary.md"

    stability = read_csv_if_exists(analysis_dir / "window_stability_summary.csv")
    long_df = read_csv_if_exists(analysis_dir / "window_metrics_long.csv")
    measurements = read_csv_if_exists(Path(args.measurements_csv)) if args.measurements_csv else pd.DataFrame()

    summary = build_summary(
        stability=stability,
        long_df=long_df,
        measurements=measurements,
        reference_window=float(args.reference_window),
        decision_window=float(args.decision_window),
        top_k=int(args.top_k),
    )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(summary, encoding="utf-8")

    print(f"wrote {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())