#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


WINDOW_COL_RE = re.compile(r"^(?P<metric>.+)_w(?P<window>\d+(?:p\d+)?)s$")

DEFAULT_METRICS = [
    "smact_mean",
    "smact_median",
    "smact_p95",
    "smact_ewma",
    "smact_risk",
    "smocc_mean",
    "smocc_median",
    "smocc_p95",
    "smocc_ewma",
    "smocc_risk",
    "drama_mean",
    "drama_median",
    "drama_p95",
    "drama_ewma",
    "drama_risk",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Analyze solo threshold summary windows from live_threshold_measurements.csv."
    )
    p.add_argument("--measurements-csv", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--reference-window", type=float, default=200.0)
    p.add_argument(
        "--metrics",
        default=",".join(DEFAULT_METRICS),
        help="Comma-separated metrics to analyze.",
    )
    return p.parse_args()


def format_window_suffix(window_seconds: float) -> str:
    if float(window_seconds).is_integer():
        return f"w{int(window_seconds)}s"
    return f"w{str(window_seconds).replace('.', 'p')}s"


def parse_window_from_suffix(value: str) -> float:
    return float(value.replace("p", "."))


def discover_window_columns(df: pd.DataFrame, metrics: list[str]) -> dict[float, dict[str, str]]:
    wanted = set(metrics)
    discovered: dict[float, dict[str, str]] = {}

    for column in df.columns:
        match = WINDOW_COL_RE.match(column)
        if not match:
            continue

        metric = match.group("metric")
        if metric not in wanted:
            continue

        window = parse_window_from_suffix(match.group("window"))
        discovered.setdefault(window, {})[metric] = column

    return dict(sorted(discovered.items()))


def build_long_window_metrics(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    window_columns = discover_window_columns(df, metrics)

    id_columns = [
        c
        for c in [
            "run_id",
            "task_id",
            "task_path",
            "finish_status",
            "return_code",
            "window_seconds",
            "summary_windows_collected",
            "total_runtime_seconds",
            "ttfk_wait_seconds",
        ]
        if c in df.columns
    ]

    rows = []
    for row_idx, row in df.iterrows():
        base = {c: row.get(c) for c in id_columns}
        base["row_index"] = row_idx

        for window_seconds, metric_to_column in window_columns.items():
            for metric, column in metric_to_column.items():
                rows.append(
                    {
                        **base,
                        "summary_window_seconds": float(window_seconds),
                        "metric": metric,
                        "value": pd.to_numeric(row.get(column), errors="coerce"),
                    }
                )

    return pd.DataFrame(rows)


def summarize_stability(
    long_df: pd.DataFrame,
    *,
    reference_window: float,
) -> pd.DataFrame:
    if long_df.empty:
        return pd.DataFrame(
            columns=[
                "metric",
                "summary_window_seconds",
                "reference_window_seconds",
                "n",
                "mean_abs_error",
                "median_abs_error",
                "p95_abs_error",
                "mean_abs_relative_error",
            ]
        )

    pivot = long_df.pivot_table(
        index=["row_index", "metric"],
        columns="summary_window_seconds",
        values="value",
        aggfunc="first",
    )

    if reference_window not in pivot.columns:
        raise ValueError(
            f"Reference window {reference_window:g}s not found in measurement columns. "
            f"Available windows: {sorted(pivot.columns.tolist())}"
        )

    rows = []
    for metric in sorted(long_df["metric"].dropna().unique()):
        metric_pivot = pivot.xs(metric, level="metric")
        reference = pd.to_numeric(metric_pivot[reference_window], errors="coerce")

        for window in sorted(pivot.columns):
            values = pd.to_numeric(metric_pivot[window], errors="coerce")
            error = (values - reference).abs()

            denom = reference.abs()
            rel_error = error / denom.where(denom > 1e-9)

            rows.append(
                {
                    "metric": metric,
                    "summary_window_seconds": float(window),
                    "reference_window_seconds": float(reference_window),
                    "n": int(error.notna().sum()),
                    "mean_abs_error": float(error.mean()) if error.notna().any() else None,
                    "median_abs_error": float(error.median()) if error.notna().any() else None,
                    "p95_abs_error": float(error.quantile(0.95)) if error.notna().any() else None,
                    "mean_abs_relative_error": float(rel_error.mean()) if rel_error.notna().any() else None,
                }
            )

    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()

    measurements_csv = Path(args.measurements_csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]
    df = pd.read_csv(measurements_csv)

    long_df = build_long_window_metrics(df, metrics)
    summary_df = summarize_stability(
        long_df,
        reference_window=float(args.reference_window),
    )

    long_path = output_dir / "window_metrics_long.csv"
    summary_path = output_dir / "window_stability_summary.csv"

    long_df.to_csv(long_path, index=False)
    summary_df.to_csv(summary_path, index=False)

    print(f"wrote {long_path}")
    print(f"wrote {summary_path}")
    print(f"rows_long={len(long_df)}")
    print(f"rows_summary={len(summary_df)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())