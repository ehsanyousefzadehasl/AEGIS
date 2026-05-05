#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_RISK_METRICS = ["smact_risk", "smocc_risk", "drama_risk"]

RISK_BASE_METRICS = ["smact", "smocc", "drama"]
RISK_COMPONENTS = ["mean", "median", "p95", "ewma", "risk"]

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

def require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"{description} is not a file: {path}")


def require_dir(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"{description} is not a directory: {path}")
    
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


def format_window_suffix(window_seconds: float) -> str:
    if float(window_seconds).is_integer():
        return f"w{int(window_seconds)}s"
    return f"w{str(window_seconds).replace('.', 'p')}s"


def split_risk_component_metric(metric: str) -> tuple[str | None, str | None]:
    for base_metric in RISK_BASE_METRICS:
        prefix = f"{base_metric}_"
        if metric.startswith(prefix):
            component = metric[len(prefix):]
            if component in RISK_COMPONENTS:
                return base_metric, component

    return None, None


def first_value_for_window(group: pd.DataFrame, window_seconds: float):
    values = group.loc[
        (group["summary_window_seconds"] - float(window_seconds)).abs() < 1e-9,
        "value",
    ]
    if values.empty:
        return None
    value = pd.to_numeric(values.iloc[0], errors="coerce")
    if pd.isna(value):
        return None
    return float(value)


def build_per_workload_risk_components(
    long_df: pd.DataFrame,
    *,
    decision_window: float,
    reference_window: float,
) -> pd.DataFrame:
    if long_df.empty:
        return pd.DataFrame()

    needed = {"metric", "summary_window_seconds", "value"}
    if not needed.issubset(long_df.columns):
        return pd.DataFrame()

    data = long_df.copy()
    parsed = data["metric"].astype(str).apply(split_risk_component_metric)
    data["base_metric"] = parsed.apply(lambda x: x[0])
    data["risk_component"] = parsed.apply(lambda x: x[1])

    data = data[
        data["base_metric"].notna()
        & data["risk_component"].notna()
    ].copy()

    if data.empty:
        return pd.DataFrame()

    data["summary_window_seconds"] = pd.to_numeric(
        data["summary_window_seconds"],
        errors="coerce",
    )
    data["value"] = pd.to_numeric(data["value"], errors="coerce")

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
        if c in data.columns
    ]

    decision_suffix = format_window_suffix(decision_window)
    reference_suffix = format_window_suffix(reference_window)

    rows = []
    group_cols = id_cols + ["base_metric"]

    for keys, group in data.groupby(group_cols, dropna=False, sort=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        row = dict(zip(group_cols, keys))

        for component in RISK_COMPONENTS:
            component_group = group[group["risk_component"] == component]

            decision_value = first_value_for_window(component_group, decision_window)
            reference_value = first_value_for_window(component_group, reference_window)

            row[f"{component}_{decision_suffix}"] = decision_value
            row[f"{component}_{reference_suffix}"] = reference_value

            if decision_value is not None and reference_value is not None:
                abs_error = abs(decision_value - reference_value)
                row[f"{component}_abs_error"] = abs_error
                row[f"{component}_relative_error"] = (
                    abs_error / abs(reference_value)
                    if abs(reference_value) > 1e-9
                    else None
                )
            else:
                row[f"{component}_abs_error"] = None
                row[f"{component}_relative_error"] = None

        rows.append(row)

    out = pd.DataFrame(rows)

    if "risk_abs_error" in out.columns:
        out["risk_abs_error"] = pd.to_numeric(out["risk_abs_error"], errors="coerce")
        out = out.sort_values(
            ["risk_abs_error", "base_metric"],
            ascending=[False, True],
            na_position="last",
        )

    return out


def build_risk_component_stability_summary(
    stability: pd.DataFrame,
    *,
    reference_window: float,
) -> pd.DataFrame:
    if stability.empty:
        return pd.DataFrame()

    required = {
        "metric",
        "summary_window_seconds",
        "reference_window_seconds",
        "n",
        "mean_abs_error",
        "median_abs_error",
        "p95_abs_error",
        "mean_abs_relative_error",
    }
    if not required.issubset(stability.columns):
        return pd.DataFrame()

    data = stability.copy()
    parsed = data["metric"].astype(str).apply(split_risk_component_metric)
    data["base_metric"] = parsed.apply(lambda x: x[0])
    data["risk_component"] = parsed.apply(lambda x: x[1])

    data = data[
        data["base_metric"].notna()
        & data["risk_component"].notna()
        & (
            pd.to_numeric(data["reference_window_seconds"], errors="coerce")
            == float(reference_window)
        )
    ].copy()

    if data.empty:
        return pd.DataFrame()

    data["summary_window_seconds"] = pd.to_numeric(
        data["summary_window_seconds"],
        errors="coerce",
    )

    component_order = {name: i for i, name in enumerate(RISK_COMPONENTS)}
    metric_order = {name: i for i, name in enumerate(RISK_BASE_METRICS)}

    data["metric_order"] = data["base_metric"].map(metric_order)
    data["component_order"] = data["risk_component"].map(component_order)

    return data.sort_values(
        ["metric_order", "component_order", "summary_window_seconds"]
    ).drop(columns=["metric_order", "component_order"])


def build_risk_component_stability_rollup(
    component_stability: pd.DataFrame,
) -> pd.DataFrame:
    if component_stability.empty:
        return pd.DataFrame()

    required = {
        "risk_component",
        "summary_window_seconds",
        "n",
        "mean_abs_error",
        "median_abs_error",
        "p95_abs_error",
        "mean_abs_relative_error",
    }
    if not required.issubset(component_stability.columns):
        return pd.DataFrame()

    data = component_stability.copy()
    data["n"] = pd.to_numeric(data["n"], errors="coerce").fillna(0)

    rows = []
    for (component, window), group in data.groupby(
        ["risk_component", "summary_window_seconds"],
        dropna=False,
        sort=False,
    ):
        weights = group["n"]
        total_n = int(weights.sum())

        row = {
            "risk_component": component,
            "summary_window_seconds": float(window),
            "total_n": total_n,
        }

        for col in [
            "mean_abs_error",
            "median_abs_error",
            "p95_abs_error",
            "mean_abs_relative_error",
        ]:
            values = pd.to_numeric(group[col], errors="coerce")
            valid = values.notna() & (weights > 0)

            if valid.any():
                row[f"weighted_{col}"] = float(
                    (values[valid] * weights[valid]).sum() / weights[valid].sum()
                )
            else:
                row[f"weighted_{col}"] = None

        rows.append(row)

    out = pd.DataFrame(rows)

    component_order = {name: i for i, name in enumerate(RISK_COMPONENTS)}
    out["component_order"] = out["risk_component"].map(component_order)

    return out.sort_values(
        ["component_order", "summary_window_seconds"]
    ).drop(columns=["component_order"])


def build_summary(
    *,
    stability: pd.DataFrame,
    long_df: pd.DataFrame,
    measurements: pd.DataFrame,
    reference_window: float,
    decision_window: float,
    top_k: int,
    per_workload_components: pd.DataFrame | None = None,
) -> str:
    lines: list[str] = []

    if per_workload_components is None:
        per_workload_components = build_per_workload_risk_components(
            long_df,
            decision_window=decision_window,
            reference_window=reference_window,
        )

    component_stability = build_risk_component_stability_summary(
        stability,
        reference_window=reference_window,
    )
    component_rollup = build_risk_component_stability_rollup(component_stability)

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

    decision_suffix = format_window_suffix(decision_window)
    reference_suffix = format_window_suffix(reference_window)

    lines.append("\n## Risk-component ablation\n")
    lines.append(
        "AEGIS risk is the equal-weight average of mean, median, p95, and EWMA. "
        "This section compares each component against the same reference window to show "
        "what each statistic contributes and whether the combined risk behaves as a balanced signal.\n"
    )

    lines.append("\n### Component stability rollup\n")
    lines.append(
        markdown_table(
            component_rollup,
            [
                "risk_component",
                "summary_window_seconds",
                "total_n",
                "weighted_mean_abs_error",
                "weighted_median_abs_error",
                "weighted_p95_abs_error",
                "weighted_mean_abs_relative_error",
            ],
            max_rows=100,
        )
    )

    lines.append("\n### Component stability by metric\n")
    lines.append(
        markdown_table(
            component_stability,
            [
                "base_metric",
                "risk_component",
                "summary_window_seconds",
                "reference_window_seconds",
                "n",
                "mean_abs_error",
                "median_abs_error",
                "p95_abs_error",
                "mean_abs_relative_error",
            ],
            max_rows=200,
        )
    )

    lines.append("\n## Per-workload risk-component breakdown\n")
    lines.append(
        "The risk score is the equal-weight average of mean, median, p95, and EWMA. "
        "This table keeps those components visible per workload so we can see when one "
        "component is stable while another differs between the decision and reference windows.\n"
    )

    lines.append(
        markdown_table(
            per_workload_components,
            [
                "task_path",
                "base_metric",
                f"mean_{decision_suffix}",
                f"mean_{reference_suffix}",
                f"median_{decision_suffix}",
                f"median_{reference_suffix}",
                f"p95_{decision_suffix}",
                f"p95_{reference_suffix}",
                f"ewma_{decision_suffix}",
                f"ewma_{reference_suffix}",
                f"risk_{decision_suffix}",
                f"risk_{reference_suffix}",
                "risk_abs_error",
                "risk_relative_error",
                "total_runtime_seconds",
                "ttfk_wait_seconds",
            ],
            max_rows=200,
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

    require_dir(analysis_dir, "window analysis directory")
    require_file(analysis_dir / "window_stability_summary.csv", "window stability summary CSV")
    require_file(analysis_dir / "window_metrics_long.csv", "window metrics long CSV")

    if args.measurements_csv:
        require_file(Path(args.measurements_csv), "live threshold measurements CSV")

    stability = read_csv_if_exists(analysis_dir / "window_stability_summary.csv")
    long_df = read_csv_if_exists(analysis_dir / "window_metrics_long.csv")
    measurements = read_csv_if_exists(Path(args.measurements_csv)) if args.measurements_csv else pd.DataFrame()

    per_workload_components = build_per_workload_risk_components(
        long_df,
        decision_window=float(args.decision_window),
        reference_window=float(args.reference_window),
    )

    component_stability = build_risk_component_stability_summary(
        stability,
        reference_window=float(args.reference_window),
    )
    component_rollup = build_risk_component_stability_rollup(component_stability)


    per_workload_components_path = analysis_dir / "per_workload_risk_components.csv"
    component_stability_path = analysis_dir / "risk_component_stability.csv"
    component_rollup_path = analysis_dir / "risk_component_stability_rollup.csv"
    per_workload_components.to_csv(per_workload_components_path, index=False)
    component_stability.to_csv(component_stability_path, index=False)
    component_rollup.to_csv(component_rollup_path, index=False)
    summary = build_summary(
        stability=stability,
        long_df=long_df,
        measurements=measurements,
        reference_window=float(args.reference_window),
        decision_window=float(args.decision_window),
        top_k=int(args.top_k),
        per_workload_components=per_workload_components,
    )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(summary, encoding="utf-8")

    print(f"wrote {output_md}")
    print(f"wrote {per_workload_components_path}")
    print(f"wrote {component_stability_path}")
    print(f"wrote {component_rollup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())