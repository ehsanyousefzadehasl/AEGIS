#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

ANALYZE_WINDOWS = REPO_ROOT / "evaluation" / "threshold_sensitivity" / "analyze_solo_windows.py"
SUMMARIZE_WINDOWS = REPO_ROOT / "evaluation" / "threshold_sensitivity" / "summarize_solo_windows.py"
PLOT_INSIGHTS = REPO_ROOT / "evaluation" / "runners" / "plot_profile_and_threshold_insights.py"

DEFAULT_PROFILE_COMPARISON = (
    REPO_ROOT / "evaluation" / "profiling" / "solo" / "analysis" / "profile_200s_vs_full.csv"
)
DEFAULT_SUMMARY_DIR = REPO_ROOT / "evaluation" / "threshold_sensitivity" / "summaries"
DEFAULT_FIGURE_ROOT = REPO_ROOT / "evaluation" / "figures"


def parse_window_list(value: str) -> list[float]:
    windows = []
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        window = float(item)
        if window <= 0:
            raise ValueError(f"Decision window must be positive: {window}")
        windows.append(window)

    if not windows:
        raise ValueError("At least one decision window is required.")

    return windows


def format_window_suffix(window_seconds: float) -> str:
    if float(window_seconds).is_integer():
        return f"w{int(window_seconds)}s"
    return f"w{str(window_seconds).replace('.', 'p')}s"


def run_command(cmd: list[str], *, dry_run: bool) -> None:
    print("\n" + " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate AEGIS threshold analysis CSVs, Markdown summaries, and figures."
    )
    p.add_argument("--suite-dir", required=True, help="Solo-run suite directory.")
    p.add_argument("--analysis-name", default="window_analysis", help="Output analysis subdirectory name.")
    p.add_argument("--reference-window", type=float, default=200.0)
    p.add_argument("--decision-windows", default="30,40,60")
    p.add_argument("--summary-dir", default=str(DEFAULT_SUMMARY_DIR))
    p.add_argument("--figure-root", default=str(DEFAULT_FIGURE_ROOT))
    p.add_argument("--profile-comparison", default=str(DEFAULT_PROFILE_COMPARISON))
    p.add_argument("--summary-prefix", default="window_analysis_summary_1gpu")
    p.add_argument("--figure-prefix", default="profile_threshold_insights_1gpu")
    p.add_argument("--top-k", type=int, default=12)
    p.add_argument("--formats", default="pdf,png")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    suite_dir = Path(args.suite_dir).resolve()
    measurements_csv = suite_dir / "live_threshold_measurements.csv"
    analysis_dir = suite_dir / args.analysis_name

    if not suite_dir.is_dir():
        raise NotADirectoryError(f"Suite directory does not exist: {suite_dir}")
    if not measurements_csv.is_file():
        raise FileNotFoundError(f"Missing measurements CSV: {measurements_csv}")

    decision_windows = parse_window_list(args.decision_windows)
    reference_window = float(args.reference_window)

    summary_dir = Path(args.summary_dir)
    figure_root = Path(args.figure_root)

    run_command(
        [
            sys.executable,
            str(ANALYZE_WINDOWS),
            "--measurements-csv",
            str(measurements_csv),
            "--output-dir",
            str(analysis_dir),
            "--reference-window",
            str(reference_window),
        ],
        dry_run=args.dry_run,
    )

    for decision_window in decision_windows:
        decision_suffix = format_window_suffix(decision_window)
        reference_suffix = format_window_suffix(reference_window)

        output_md = summary_dir / f"{args.summary_prefix}_{decision_suffix}_vs_{reference_suffix}.md"

        run_command(
            [
                sys.executable,
                str(SUMMARIZE_WINDOWS),
                "--analysis-dir",
                str(analysis_dir),
                "--measurements-csv",
                str(measurements_csv),
                "--output-md",
                str(output_md),
                "--reference-window",
                str(reference_window),
                "--decision-window",
                str(decision_window),
                "--top-k",
                str(args.top_k),
            ],
            dry_run=args.dry_run,
        )

        per_workload_components = (
            analysis_dir
            / f"per_workload_risk_components_{decision_suffix}_vs_{reference_suffix}.csv"
        )

        figure_dir = figure_root / f"{args.figure_prefix}_{decision_suffix}_vs_{reference_suffix}"

        run_command(
            [
                sys.executable,
                str(PLOT_INSIGHTS),
                "--profile-comparison",
                str(args.profile_comparison),
                "--window-stability",
                str(analysis_dir / "window_stability_summary.csv"),
                "--risk-component-rollup",
                str(analysis_dir / "risk_component_stability_rollup.csv"),
                "--per-workload-components",
                str(per_workload_components),
                "--output-dir",
                str(figure_dir),
                "--decision-window",
                str(decision_window),
                "--reference-window",
                str(reference_window),
                "--top-k",
                str(args.top_k),
                "--formats",
                str(args.formats),
            ],
            dry_run=args.dry_run,
        )

    print("\nGenerated threshold analysis artifacts.")
    print(f"analysis_dir={analysis_dir}")
    print(f"summary_dir={summary_dir}")
    print(f"figure_root={figure_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())