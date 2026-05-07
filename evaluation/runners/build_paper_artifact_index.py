#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import os

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_OUTPUT_DIR = REPO_ROOT / "evaluation" / "paper_artifacts"
DEFAULT_FIGURES_DIR = REPO_ROOT / "evaluation" / "figures"

PROFILE_METRICS = ["smact", "smocc", "drama"]
PROFILE_STATS = ["mean", "median", "p95", "ewma", "aegis_profile_risk"]
RISK_METRICS = ["smact_risk", "smocc_risk", "drama_risk"]
DECISION_WINDOWS = [30, 40, 60, 120]
REFERENCE_WINDOW = 200


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build a curated paper-artifact index from existing evaluation outputs."
    )
    p.add_argument("--suite-dir", default=None)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--figures-dir", default=str(DEFAULT_FIGURES_DIR))
    return p.parse_args()


def latest_suite_dir() -> Path:
    root = REPO_ROOT / "evaluation" / "threshold_sensitivity" / "solo_runs"
    candidates = sorted(root.glob("solo_1gpu_threshold_windows_*"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No solo threshold suites found under {root}")
    return candidates[-1]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"missing, skipping: {path}")
        return pd.DataFrame()
    return pd.read_csv(path)


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int = 200) -> str:
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


def build_anchor_comparison(output_dir: Path) -> pd.DataFrame:
    anchors = {
        "launch": REPO_ROOT / "evaluation" / "profiling" / "solo" / "analysis_launch_anchor" / "profile_200s_vs_full.csv",
        "first_memory": REPO_ROOT / "evaluation" / "profiling" / "solo" / "analysis_first_memory_anchor" / "profile_200s_vs_full.csv",
        "activity_filtered": REPO_ROOT / "evaluation" / "profiling" / "solo" / "analysis" / "profile_200s_vs_full.csv",
    }

    frames = []
    for anchor, path in anchors.items():
        df = read_csv(path)
        if df.empty:
            continue
        df["anchor"] = anchor
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df[df["metric"].isin(PROFILE_METRICS) & df["stat"].isin(PROFILE_STATS)].copy()
    df["relative_error_200s_vs_full"] = pd.to_numeric(
        df["relative_error_200s_vs_full"], errors="coerce"
    )

    rows = []
    for (stat, anchor), group in df.groupby(["stat", "anchor"], sort=False):
        rel = group["relative_error_200s_vs_full"].dropna() * 100.0
        rows.append(
            {
                "stat": stat,
                "anchor": anchor,
                "n": int(len(rel)),
                "median_relative_error_percent": rel.median(),
                "p90_relative_error_percent": rel.quantile(0.90),
                "p95_relative_error_percent": rel.quantile(0.95),
                "max_relative_error_percent": rel.max(),
            }
        )

    summary = pd.DataFrame(rows)

    stat_order = {name: i for i, name in enumerate(PROFILE_STATS)}
    anchor_order = {"launch": 0, "first_memory": 1, "activity_filtered": 2}
    summary["stat_order"] = summary["stat"].map(stat_order)
    summary["anchor_order"] = summary["anchor"].map(anchor_order)
    summary = summary.sort_values(["stat_order", "anchor_order"]).drop(
        columns=["stat_order", "anchor_order"]
    )

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "solo_profile_anchor_comparison.csv"
    md_path = tables_dir / "solo_profile_anchor_comparison.md"

    summary.to_csv(csv_path, index=False)

    md = ["# Solo Profile Anchor Comparison\n"]
    md.append(
        "This table compares 200s-vs-full profile mismatch under three anchors: "
        "`launch`, `first_memory`, and `activity_filtered`.\n"
    )
    md.append(
        markdown_table(
            summary,
            [
                "stat",
                "anchor",
                "n",
                "median_relative_error_percent",
                "p90_relative_error_percent",
                "p95_relative_error_percent",
                "max_relative_error_percent",
            ],
            max_rows=200,
        )
    )
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    return summary


def build_first_gpu_activity_window_summary(suite_dir: Path, output_dir: Path) -> pd.DataFrame:
    analysis_dir = suite_dir / "window_analysis"
    stability = read_csv(analysis_dir / "window_stability_summary.csv")
    if stability.empty:
        return pd.DataFrame()

    data = stability[
        stability["metric"].isin(RISK_METRICS)
        & (pd.to_numeric(stability["reference_window_seconds"], errors="coerce") == float(REFERENCE_WINDOW))
    ].copy()

    if data.empty:
        return pd.DataFrame()

    for col in [
        "summary_window_seconds",
        "n",
        "mean_abs_error",
        "median_abs_error",
        "p95_abs_error",
        "mean_abs_relative_error",
    ]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    rows = []
    for window, group in data.groupby("summary_window_seconds", sort=True):
        weights = group["n"].fillna(0)
        row = {
            "summary_window_seconds": float(window),
            "total_n": int(weights.sum()),
        }

        for col in ["mean_abs_error", "median_abs_error", "p95_abs_error", "mean_abs_relative_error"]:
            valid = group[col].notna() & (weights > 0)
            if valid.any():
                row[f"weighted_{col}"] = float(
                    (group.loc[valid, col] * weights.loc[valid]).sum() / weights.loc[valid].sum()
                )
            else:
                row[f"weighted_{col}"] = None

        rows.append(row)

    summary = pd.DataFrame(rows)

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "first_gpu_activity_window_stability.csv"
    md_path = tables_dir / "first_gpu_activity_window_stability.md"

    summary.to_csv(csv_path, index=False)

    md = ["# First-Observed-GPU-Activity Window Stability\n"]
    md.append(
        "This table summarizes how shorter first-observed-GPU-activity windows compare "
        f"against the {REFERENCE_WINDOW}s reference window for `smact_risk`, `smocc_risk`, and `drama_risk`.\n"
    )
    md.append(
        markdown_table(
            summary,
            [
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
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    return summary


def build_risk_component_ablation_summary(suite_dir: Path, output_dir: Path) -> pd.DataFrame:
    path = suite_dir / "window_analysis" / "risk_component_stability_rollup.csv"
    df = read_csv(path)
    if df.empty:
        return pd.DataFrame()

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "risk_component_ablation_rollup.csv"
    md_path = tables_dir / "risk_component_ablation_rollup.md"

    df.to_csv(csv_path, index=False)

    md = ["# Risk Component Ablation Rollup\n"]
    md.append(
        "This table compares the stability of `mean`, `median`, `p95`, `ewma`, and the combined `risk` "
        f"against the {REFERENCE_WINDOW}s reference window.\n"
    )
    md.append(
        markdown_table(
            df,
            [
                "risk_component",
                "summary_window_seconds",
                "total_n",
                "weighted_mean_abs_error",
                "weighted_median_abs_error",
                "weighted_p95_abs_error",
                "weighted_mean_abs_relative_error",
            ],
            max_rows=200,
        )
    )
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    return df


def build_figure_index(figures_dir: Path, output_dir: Path) -> None:
    figure_md = output_dir / "figure_index.md"

    lines = ["# Figure Index\n"]
    lines.append("## First-observed-GPU-activity threshold-window figures\n")

    for window in DECISION_WINDOWS:
        fig_dir = figures_dir / f"profile_threshold_insights_1gpu_w{window}s_vs_w{REFERENCE_WINDOW}s"
        lines.append(f"\n### {window}s vs {REFERENCE_WINDOW}s\n")
        if not fig_dir.exists():
            lines.append(f"_Missing: `{fig_dir}`_\n")
            continue

        for path in sorted(fig_dir.glob("*.pdf")):
            lines.append(f"- `{path.relative_to(REPO_ROOT)}`")

    lines.append("\n## First-memory anchored solo-profile figures\n")
    first_memory_dir = figures_dir / "profile_insights_first_memory_anchor_w200s_vs_full"
    if first_memory_dir.exists():
        for path in sorted(first_memory_dir.glob("*.pdf")):
            lines.append(f"- `{path.relative_to(REPO_ROOT)}`")
    else:
        lines.append(f"_Missing: `{first_memory_dir}`_")

    figure_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {figure_md}")


def md_image(path: Path, output_dir: Path, title: str) -> str:
    if not path.exists():
        return f"_Missing: `{path.relative_to(REPO_ROOT)}`_\n"

    rel = os.path.relpath(path, start=output_dir)
    return f"**{title}**\n\n![{title}]({rel})\n"


def build_figure_gallery(figures_dir: Path, output_dir: Path) -> None:
    gallery_md = output_dir / "figure_gallery.md"

    lines = ["# Figure Gallery\n"]
    lines.append(
        "This gallery embeds selected PNG figures for quick visual inspection. "
        "See `figure_index.md` for the complete file list.\n"
    )

    solo_sections = {
        "Launch anchored solo profile: 200s vs full": figures_dir / "solo_profile_launch_w200s_vs_full",
        "First-memory anchored solo profile: 200s vs full": figures_dir / "solo_profile_first_memory_w200s_vs_full",
        "Activity-filtered solo profile: 200s vs full": figures_dir / "solo_profile_activity_filtered_w200s_vs_full",
    }

    solo_figures = [
        ("profile_200s_vs_full_boxplot.png", "AEGIS risk 200s-vs-full boxplot"),
        ("profile_200s_vs_full_component_boxplots.png", "Component 200s-vs-full boxplots"),
        ("profile_top_mismatches.png", "Top AEGIS-risk profile mismatches"),
        ("profile_top_mismatches_mean.png", "Top mean profile mismatches"),
        ("profile_top_mismatches_p95.png", "Top p95 profile mismatches"),
        ("profile_top_mismatches_ewma.png", "Top EWMA profile mismatches"),
    ]

    lines.append("\n## Solo-profile anchor figures\n")
    for section_title, folder in solo_sections.items():
        lines.append(f"\n### {section_title}\n")
        lines.append(f"Folder: `{folder.relative_to(REPO_ROOT)}`\n")

        for filename, title in solo_figures:
            lines.append(md_image(folder / filename, output_dir, title))

    threshold_figures = [
        ("threshold_window_stability_curve.png", "Window stability curve"),
        ("risk_component_ablation_curve.png", "Risk component ablation curve"),
        ("per_workload_risk_error_heatmap.png", "Per-workload AEGIS-risk error heatmap"),
        ("per_workload_mean_error_heatmap.png", "Per-workload mean error heatmap"),
        ("per_workload_p95_error_heatmap.png", "Per-workload p95 error heatmap"),
        ("per_workload_ewma_error_heatmap.png", "Per-workload EWMA error heatmap"),
    ]

    lines.append("\n## First-observed-GPU-activity threshold-window figures\n")
    for window in DECISION_WINDOWS:
        folder = figures_dir / f"first_gpu_activity_windows_w{window}s_vs_w{REFERENCE_WINDOW}s"
        lines.append(f"\n### {window}s vs {REFERENCE_WINDOW}s\n")
        lines.append(f"Folder: `{folder.relative_to(REPO_ROOT)}`\n")

        for filename, title in threshold_figures:
            lines.append(md_image(folder / filename, output_dir, title))

    gallery_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {gallery_md}")

def build_memory_safety_summary(output_dir: Path) -> pd.DataFrame:
    sources = {
        "launch": REPO_ROOT / "evaluation" / "profiling" / "solo" / "extracted_launch_anchor" / "solo_profile_results_1gpu.csv",
        "first_memory": REPO_ROOT / "evaluation" / "profiling" / "solo" / "extracted_first_memory_anchor" / "solo_profile_results_1gpu.csv",
        "activity_filtered": REPO_ROOT / "evaluation" / "profiling" / "solo" / "extracted" / "solo_profile_results_1gpu.csv",
    }

    rows = []

    for anchor, path in sources.items():
        df = read_csv(path)
        if df.empty:
            continue

        required = {
            "gpu_memory_peak_200s_mib",
            "gpu_memory_peak_full_mib",
            "gpu_memory_requirement_mib",
        }
        if not required.issubset(df.columns):
            continue

        data = df.copy()
        data["gpu_memory_peak_200s_mib"] = pd.to_numeric(
            data["gpu_memory_peak_200s_mib"], errors="coerce"
        )
        data["gpu_memory_peak_full_mib"] = pd.to_numeric(
            data["gpu_memory_peak_full_mib"], errors="coerce"
        )
        data["gpu_memory_requirement_mib"] = pd.to_numeric(
            data["gpu_memory_requirement_mib"], errors="coerce"
        )

        valid = data.dropna(
            subset=["gpu_memory_peak_200s_mib", "gpu_memory_peak_full_mib"]
        ).copy()

        if valid.empty:
            continue

        underestimate = (
            valid["gpu_memory_peak_full_mib"] - valid["gpu_memory_peak_200s_mib"]
        )
        under_positive = underestimate[underestimate > 0]

        requirement_valid = valid.dropna(subset=["gpu_memory_requirement_mib"]).copy()
        requirement_under = (
            requirement_valid["gpu_memory_requirement_mib"]
            - requirement_valid["gpu_memory_peak_200s_mib"]
        )
        requirement_under_positive = requirement_under[requirement_under > 0]

        rows.append(
            {
                "anchor": anchor,
                "n": int(len(valid)),
                "underestimates_full_peak_count": int(len(under_positive)),
                "underestimates_full_peak_rate": (
                    float(len(under_positive) / len(valid)) if len(valid) else None
                ),
                "median_full_peak_underestimate_mib": (
                    float(under_positive.median()) if not under_positive.empty else 0.0
                ),
                "p95_full_peak_underestimate_mib": (
                    float(under_positive.quantile(0.95)) if not under_positive.empty else 0.0
                ),
                "max_full_peak_underestimate_mib": (
                    float(under_positive.max()) if not under_positive.empty else 0.0
                ),
                "n_with_requirement": int(len(requirement_valid)),
                "window_peak_below_requirement_count": int(len(requirement_under_positive)),
                "window_peak_below_requirement_rate": (
                    float(len(requirement_under_positive) / len(requirement_valid))
                    if len(requirement_valid)
                    else None
                ),
                "median_requirement_gap_mib": (
                    float(requirement_under_positive.median())
                    if not requirement_under_positive.empty
                    else 0.0
                ),
                "max_requirement_gap_mib": (
                    float(requirement_under_positive.max())
                    if not requirement_under_positive.empty
                    else 0.0
                ),
            }
        )

    summary = pd.DataFrame(rows)

    if summary.empty:
        return summary

    anchor_order = {"launch": 0, "first_memory": 1, "activity_filtered": 2}
    summary["anchor_order"] = summary["anchor"].map(anchor_order)
    summary = summary.sort_values("anchor_order").drop(columns=["anchor_order"])

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "memory_safety_summary.csv"
    md_path = tables_dir / "memory_safety_summary.md"

    summary.to_csv(csv_path, index=False)

    md = ["# Memory Safety Summary\n"]
    md.append(
        "This table compares the 200s-window observed GPU memory peak against the full-run "
        "observed peak and the workload memory requirement. Memory is a hard constraint for "
        "collocation, so underestimating peak memory can lead to unsafe placements.\n"
    )
    md.append(
        markdown_table(
            summary,
            [
                "anchor",
                "n",
                "underestimates_full_peak_count",
                "underestimates_full_peak_rate",
                "median_full_peak_underestimate_mib",
                "p95_full_peak_underestimate_mib",
                "max_full_peak_underestimate_mib",
                "n_with_requirement",
                "window_peak_below_requirement_count",
                "window_peak_below_requirement_rate",
                "median_requirement_gap_mib",
                "max_requirement_gap_mib",
            ],
            max_rows=50,
        )
    )
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")

    return summary


def build_claims_and_evidence(
    output_dir: Path,
    anchor_summary: pd.DataFrame,
    window_summary: pd.DataFrame,
    component_summary: pd.DataFrame,
) -> None:
    path = output_dir / "claims_and_evidence.md"
    lines = ["# Claims and Evidence\n"]

    lines.append("## Claim 1: Fixed profile windows can be unrepresentative\n")
    lines.append(
        "Evidence: `tables/solo_profile_anchor_comparison.md` and profile mismatch figures. "
        "Use this to discuss launch, first-memory, and activity-filtered anchoring.\n"
    )

    if not anchor_summary.empty:
        risk_rows = anchor_summary[anchor_summary["stat"] == "aegis_profile_risk"]
        lines.append(markdown_table(
            risk_rows,
            [
                "anchor",
                "n",
                "median_relative_error_percent",
                "p90_relative_error_percent",
                "p95_relative_error_percent",
                "max_relative_error_percent",
            ],
            max_rows=20,
        ))

    lines.append("\n## Claim 2: First-observed-GPU-activity windows stabilize quickly\n")
    lines.append(
        "Evidence: `tables/first_gpu_activity_window_stability.md`, "
        "`threshold_window_stability_curve.pdf`, and per-workload heatmaps.\n"
    )

    if not window_summary.empty:
        selected = window_summary[
            window_summary["summary_window_seconds"].isin([30.0, 40.0, 60.0, 120.0])
        ]
        lines.append(markdown_table(
            selected,
            [
                "summary_window_seconds",
                "total_n",
                "weighted_mean_abs_error",
                "weighted_p95_abs_error",
                "weighted_mean_abs_relative_error",
            ],
            max_rows=20,
        ))

    lines.append("\n## Claim 3: AEGIS risk is a balanced score, not simply the lowest-error component\n")
    lines.append(
        "Evidence: `tables/risk_component_ablation_rollup.md` and `risk_component_ablation_curve.pdf`. "
        "The paper should explain that mean, median, p95, and EWMA capture complementary behavior.\n"
    )

    if not component_summary.empty:
        selected = component_summary[
            component_summary["summary_window_seconds"].isin([30.0, 40.0, 60.0])
        ]
        lines.append(markdown_table(
            selected,
            [
                "risk_component",
                "summary_window_seconds",
                "total_n",
                "weighted_mean_abs_error",
                "weighted_p95_abs_error",
            ],
            max_rows=100,
        ))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def build_readme(output_dir: Path, suite_dir: Path) -> None:
    path = output_dir / "README.md"

    text = f"""# AEGIS Paper Artifacts

This folder is a curated index for paper-writing. It does not replace the raw experiment outputs; it points to the stable analysis tables and figures.

## Source locations

### Solo profile anchor analyses

- Activity-filtered solo profile analysis: `evaluation/profiling/solo/analysis/`
- First-memory anchored solo profile analysis: `evaluation/profiling/solo/analysis_first_memory_anchor/`
- Launch anchored solo profile analysis: `evaluation/profiling/solo/analysis_launch_anchor/`

### First-observed-GPU-activity threshold-window analysis

- Suite directory: `{suite_dir.relative_to(REPO_ROOT)}`
- Window analysis: `{(suite_dir / "window_analysis").relative_to(REPO_ROOT)}`
- Summaries: `evaluation/threshold_sensitivity/summaries/`
- Figures: `evaluation/figures/profile_threshold_insights_1gpu_w{{30,40,60,120}}s_vs_w200s/`

## Curated files

- `claims_and_evidence.md`: paper-facing claims and where the evidence lives.
- `figure_index.md`: figure paths grouped by experiment.
- `tables/solo_profile_anchor_comparison.md`: launch vs first-memory vs activity-filtered comparison.
- `tables/first_gpu_activity_window_stability.md`: stability of shorter windows vs 200s.
- `tables/risk_component_ablation_rollup.md`: mean/median/p95/EWMA/risk ablation.
- `tables/memory_safety_summary.md`: 200s-window memory peak vs full-run peak and workload memory requirement.
- `figure_gallery.md`: visual gallery of selected generated figures.

## Terminology note

The current threshold-window pipeline uses a first-observed-GPU-activity anchor. Some internal CSV columns may still use legacy names such as `ttfk_wait_seconds`; interpret those as wait time until the job is first observed as active on GPU, not as exact CUDA-kernel-launch instrumentation.
"""

    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    args = parse_args()

    suite_dir = Path(args.suite_dir).resolve() if args.suite_dir else latest_suite_dir()
    output_dir = Path(args.output_dir)
    figures_dir = Path(args.figures_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    anchor_summary = build_anchor_comparison(output_dir)
    window_summary = build_first_gpu_activity_window_summary(suite_dir, output_dir)
    component_summary = build_risk_component_ablation_summary(suite_dir, output_dir)

    memory_summary = build_memory_safety_summary(output_dir)

    build_figure_index(figures_dir, output_dir)

    build_figure_gallery(figures_dir, output_dir)

    build_claims_and_evidence(
        output_dir,
        anchor_summary,
        window_summary,
        component_summary,
    )

    build_readme(output_dir, suite_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())