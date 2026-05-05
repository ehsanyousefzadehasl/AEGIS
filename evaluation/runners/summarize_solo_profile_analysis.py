#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANALYSIS_DIR = REPO_ROOT / "evaluation" / "profiling" / "solo" / "analysis"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Create a compact markdown summary from solo profile analysis CSVs."
    )
    p.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR))
    p.add_argument("--output-md", default=None)
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
            out[col] = out[col].round(4)

    return out.to_markdown(index=False) + "\n"

def summarize_profile_score_components(comparison: pd.DataFrame) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()

    required = {
        "metric",
        "stat",
        "value_200s",
        "value_full",
        "abs_error_200s_vs_full",
    }
    if not required.issubset(comparison.columns):
        return pd.DataFrame()

    wanted_metrics = ["smact", "smocc", "drama"]
    wanted_stats = [
        "mean",
        "median",
        "mode",
        "max",
        "profile_stat_score",
        "p95",
        "ewma",
        "aegis_profile_risk",
    ]

    subset = comparison[
        comparison["metric"].isin(wanted_metrics)
        & comparison["stat"].isin(wanted_stats)
    ].copy()

    if subset.empty:
        return pd.DataFrame()

    for col in ["value_200s", "value_full", "abs_error_200s_vs_full"]:
        subset[col] = pd.to_numeric(subset[col], errors="coerce")

    if "relative_error_200s_vs_full" in subset.columns:
        subset["relative_error_200s_vs_full"] = pd.to_numeric(
            subset["relative_error_200s_vs_full"],
            errors="coerce",
        )

    grouped = (
        subset.groupby(["metric", "stat"], dropna=False)
        .agg(
            n=("abs_error_200s_vs_full", "count"),
            mean_200s=("value_200s", "mean"),
            mean_full=("value_full", "mean"),
            mean_abs_error=("abs_error_200s_vs_full", "mean"),
            median_abs_error=("abs_error_200s_vs_full", "median"),
            p95_abs_error=("abs_error_200s_vs_full", lambda x: x.quantile(0.95)),
            mean_relative_error=(
                "relative_error_200s_vs_full",
                "mean",
            )
            if "relative_error_200s_vs_full" in subset.columns
            else ("abs_error_200s_vs_full", "mean"),
        )
        .reset_index()
    )

    stat_order = {name: i for i, name in enumerate(wanted_stats)}
    metric_order = {name: i for i, name in enumerate(wanted_metrics)}
    grouped["metric_order"] = grouped["metric"].map(metric_order)
    grouped["stat_order"] = grouped["stat"].map(stat_order)

    grouped = grouped.sort_values(["metric_order", "stat_order"]).drop(
        columns=["metric_order", "stat_order"]
    )

    return grouped

def summarize_label_distribution(labels: pd.DataFrame) -> str:
    if labels.empty or "lucid_style_class_200s" not in labels.columns:
        return "_Lucid-style label data is missing._\n"

    counts = (
        labels["lucid_style_class_200s"]
        .value_counts(dropna=False)
        .rename_axis("lucid_style_class_200s")
        .reset_index(name="count")
    )
    return markdown_table(counts, ["lucid_style_class_200s", "count"], max_rows=len(counts))


def summarize_metric_mismatch(comparison: pd.DataFrame, metric: str, stat: str, top_k: int) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()

    required = {"metric", "stat", "relative_error_200s_vs_full"}
    if not required.issubset(comparison.columns):
        return pd.DataFrame()

    subset = comparison[
        (comparison["metric"] == metric)
        & (comparison["stat"] == stat)
    ].copy()

    if subset.empty:
        return subset

    subset["relative_error_200s_vs_full"] = pd.to_numeric(
        subset["relative_error_200s_vs_full"],
        errors="coerce",
    )

    return subset.sort_values("relative_error_200s_vs_full", ascending=False).head(top_k)


def build_summary(
    *,
    labels: pd.DataFrame,
    comparison: pd.DataFrame,
    characterization: pd.DataFrame,
    top_k: int,
    horus_inputs: pd.DataFrame | None = None,
) -> str:
    lines: list[str] = []

    if horus_inputs is None:
        horus_inputs = pd.DataFrame()

    lines.append("# Solo Profile Analysis Summary\n")
    lines.append("This summary is generated from extracted solo profiling results.\n")

    lines.append("## Lucid-style 200s profile labels\n")
    lines.append(summarize_label_distribution(labels))

    lines.append("\n## Top Lucid-style pressure workloads\n")
    if not labels.empty and "lucid_style_pressure_score_200s" in labels.columns:
        top_pressure = labels.copy()
        top_pressure["lucid_style_pressure_score_200s"] = pd.to_numeric(
            top_pressure["lucid_style_pressure_score_200s"],
            errors="coerce",
        )
        top_pressure = top_pressure.sort_values(
            "lucid_style_pressure_score_200s",
            ascending=False,
        )
        lines.append(
            markdown_table(
                top_pressure,
                [
                    "workload_id",
                    "source_gpu_count",
                    "gpu_label",
                    "lucid_style_pressure_score_200s",
                    "lucid_style_ss_200s",
                    "lucid_style_class_200s",
                ],
                top_k,
            )
        )
    else:
        lines.append("_Lucid-style pressure score data is missing._\n")

    lines.append("\n## Coarse resource labels\n")
    if not characterization.empty and "coarse_resource_label" in characterization.columns:
        counts = (
            characterization["coarse_resource_label"]
            .value_counts(dropna=False)
            .rename_axis("coarse_resource_label")
            .reset_index(name="count")
        )
        lines.append(markdown_table(counts, ["coarse_resource_label", "count"], len(counts)))
    else:
        lines.append("_Workload characterization data is missing._\n")

    lines.append("\n## Largest 200s-vs-full mismatches\n")

    mismatch_specs = [
        ("smact", "profile_stat_score", "SMACT profile stat score"),
        ("smocc", "profile_stat_score", "SMOCC profile stat score"),
        ("drama", "profile_stat_score", "DRAMA profile stat score"),
        ("gpu_memory_peak_mib", "peak", "GPU memory peak"),
    ]

    for metric, stat, title in mismatch_specs:
        lines.append(f"\n### {title}\n")
        subset = summarize_metric_mismatch(comparison, metric, stat, top_k)
        lines.append(
            markdown_table(
                subset,
                [
                    "workload_id",
                    "source_gpu_count",
                    "gpu_label",
                    "value_200s",
                    "value_full",
                    "abs_error_200s_vs_full",
                    "relative_error_200s_vs_full",
                ],
                top_k,
            )
        )

    lines.append("\n## Horus-like oracle utilization inputs\n")
    lines.append(
        "For a generous Horus-like analysis, `horus_oracle_util_full` uses the observed "
        "full-run mean GPU utilization (`gputl_mean_full`) as if utilization were predicted perfectly. "
        "`horus_profile_util_200s` keeps the first-200s profiled value for comparison.\n"
    )

    if not horus_inputs.empty and "horus_oracle_util_full" in horus_inputs.columns:
        top_horus = horus_inputs.copy()
        top_horus["horus_oracle_util_full"] = pd.to_numeric(
            top_horus["horus_oracle_util_full"],
            errors="coerce",
        )
        top_horus = top_horus.sort_values("horus_oracle_util_full", ascending=False)

        lines.append(
            markdown_table(
                top_horus,
                [
                    "workload_id",
                    "source_gpu_count",
                    "gpu_label",
                    "horus_oracle_util_full",
                    "horus_profile_util_200s",
                    "horus_oracle_util_median_full",
                    "horus_oracle_util_max_full",
                    "horus_oracle_memory_full_mib",
                    "horus_abs_error_200s_vs_full_util",
                    "horus_relative_error_200s_vs_full_util",
                ],
                top_k,
            )
        )
    else:
        lines.append("_Horus-like oracle input data is missing._\n")


    lines.append("\n## Profile score component breakdown\n")
    lines.append(
        "`profile_stat_score` is the equal-weight average of mean, median, mode, and max "
        "from the extracted solo-profile CSVs. It is not the AEGIS risk formula. "
        "`aegis_profile_risk` is only available when mean, median, p95, and EWMA are present.\n"
    )

    component_summary = summarize_profile_score_components(comparison)
    lines.append(
        markdown_table(
            component_summary,
            [
                "metric",
                "stat",
                "n",
                "mean_200s",
                "mean_full",
                "mean_abs_error",
                "median_abs_error",
                "p95_abs_error",
                "mean_relative_error",
            ],
            max_rows=100,
        )
    )


    lines.append("\n## Notes for paper analysis\n")
    lines.append(
        "- `lucid_style_class_200s` is a Lucid-style profile class, not an exact Lucid reproduction.\n"
        "- `profile_stat_score` uses equal weights over mean, median, mode, and max from extracted solo-profile CSVs.\n"
        "- `profile_stat_score` is per metric/GPU/window, not a workload-level AEGIS risk.\n"
        "- `aegis_profile_risk` should only be used when mean, median, p95, and EWMA are available.\n"
        "- For activity metrics on 2-GPU workloads, inspect `gpu_a` and `gpu_b` separately.\n"
        "- For memory footprint on 2-GPU workloads, use sum columns when reasoning about total memory demand.\n"
        "- Large 200s-vs-full mismatch indicates that a short profiling window may not represent the full run.\n"
    )
    if horus_inputs is None:
        horus_inputs = pd.DataFrame()

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    analysis_dir = Path(args.analysis_dir)
    output_md = Path(args.output_md) if args.output_md else analysis_dir / "solo_profile_summary.md"

    labels = read_csv_if_exists(analysis_dir / "lucid_style_profile_labels.csv")
    comparison = read_csv_if_exists(analysis_dir / "profile_200s_vs_full.csv")
    characterization = read_csv_if_exists(analysis_dir / "workload_characterization.csv")
    horus_inputs = read_csv_if_exists(analysis_dir / "horus_oracle_inputs.csv")

    summary = build_summary(
        labels=labels,
        comparison=comparison,
        characterization=characterization,
        horus_inputs=horus_inputs,
        top_k=int(args.top_k),
    )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(summary, encoding="utf-8")

    print(f"wrote {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())