#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and analyze all runs belonging to an "
            "AEGIS evaluation manifest."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Evaluation manifest used to launch the experiment.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help=(
            "Override the manifest results directory. By default, "
            "runner.results_dir from the manifest is used."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Analysis output directory. Defaults to "
            "<results-dir>/<experiment-name>_analysis."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "Regenerate per-policy summaries for completed runs. "
            "Running, failed, timed-out, and missing runs are skipped."
        ),
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")

    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")

    return data


def expected_experiment_root(
    *,
    results_dir: Path,
    experiment_name: str,
    trace_name: str,
    repetition: int,
    configuration_label: str,
) -> Path:
    directory_name = (
        f"{experiment_name}"
        f"__{trace_name}"
        f"__rep{repetition:02d}"
        f"__{configuration_label}"
    )
    return results_dir / directory_name


def discover_metadata_paths(
    experiment_root: Path,
) -> list[Path]:
    return sorted(
        experiment_root.glob("*/*/metadata.json")
    )


def classify_metadata(
    metadata: dict[str, Any],
) -> str:
    if metadata.get("timed_out") is True:
        return "timed_out"

    return_code = metadata.get("return_code")

    if return_code is None:
        return "running"

    try:
        return_code = int(return_code)
    except (TypeError, ValueError):
        return "invalid_metadata"

    if return_code == 0:
        return "complete"

    return "failed"


def choose_latest_metadata(
    metadata_paths: list[Path],
) -> Path | None:
    if not metadata_paths:
        return None

    return max(
        metadata_paths,
        key=lambda path: path.stat().st_mtime,
    )


def build_validation_rows(
    *,
    manifest: dict[str, Any],
    results_dir: Path,
) -> list[dict[str, Any]]:
    experiment_name = str(manifest["experiment_name"])
    repetitions = int(manifest.get("repetitions", 1))
    traces = manifest["traces"]
    configurations = manifest["configurations"]

    rows: list[dict[str, Any]] = []

    for repetition in range(1, repetitions + 1):
        for trace in traces:
            trace_name = str(trace["name"])
            trace_csv = str(trace["csv"])

            for configuration in configurations:
                configuration_label = str(
                    configuration["label"]
                )
                expected_policy = str(
                    configuration["policy"]
                )
                expected_estimator = str(
                    configuration.get("estimator", "None")
                )

                experiment_root = expected_experiment_root(
                    results_dir=results_dir,
                    experiment_name=experiment_name,
                    trace_name=trace_name,
                    repetition=repetition,
                    configuration_label=configuration_label,
                )

                metadata_paths = discover_metadata_paths(
                    experiment_root
                )
                metadata_path = choose_latest_metadata(
                    metadata_paths
                )

                row: dict[str, Any] = {
                    "experiment_name": experiment_name,
                    "trace_name": trace_name,
                    "trace_csv": trace_csv,
                    "repetition": repetition,
                    "configuration_label": configuration_label,
                    "expected_policy": expected_policy,
                    "expected_estimator": expected_estimator,
                    "experiment_root": str(experiment_root),
                    "discovered_run_count": len(metadata_paths),
                    "metadata_path": None,
                    "run_dir": None,
                    "run_label": None,
                    "actual_policy": None,
                    "actual_estimator": None,
                    "expected_tasks": None,
                    "submit_return_code": None,
                    "return_code": None,
                    "timed_out": None,
                    "git_commit": None,
                    "status": "missing",
                    "configuration_matches": False,
                }

                if metadata_path is None:
                    rows.append(row)
                    continue

                metadata = load_json(metadata_path)

                actual_policy = metadata.get("policy")
                actual_estimator = metadata.get(
                    "estimator",
                    "None",
                )

                configuration_matches = (
                    str(actual_policy) == expected_policy
                    and str(actual_estimator)
                    == expected_estimator
                    and str(metadata.get("trace_csv"))
                    == trace_csv
                )

                row.update(
                    {
                        "metadata_path": str(metadata_path),
                        "run_dir": metadata.get(
                            "run_dir",
                            str(metadata_path.parent),
                        ),
                        "run_label": metadata.get("run_label"),
                        "actual_policy": actual_policy,
                        "actual_estimator": actual_estimator,
                        "expected_tasks": metadata.get(
                            "expected_tasks"
                        ),
                        "submit_return_code": metadata.get(
                            "submit_return_code"
                        ),
                        "return_code": metadata.get(
                            "return_code"
                        ),
                        "timed_out": metadata.get(
                            "timed_out"
                        ),
                        "git_commit": metadata.get(
                            "git_commit"
                        ),
                        "status": classify_metadata(metadata),
                        "configuration_matches": (
                            configuration_matches
                        ),
                    }
                )

                rows.append(row)

    return rows



def refresh_completed_summaries(
    frame: pd.DataFrame,
) -> None:
    completed_roots = sorted(
        {
            Path(value)
            for value in frame.loc[
                frame["status"] == "complete",
                "experiment_root",
            ].dropna()
        }
    )

    if not completed_roots:
        print("\nNo completed runs are available to summarize.")
        return

    script = (
        Path(__file__).resolve().parent
        / "summarize_policy_runs.py"
    )

    print("\n===== Refreshing completed summaries =====")

    for experiment_root in completed_roots:
        print(f"Summarizing: {experiment_root}")

        subprocess.run(
            [
                sys.executable,
                str(script),
                "--experiment-root",
                str(experiment_root),
            ],
            check=True,
        )



def collect_completed_run_summaries(
    *,
    validation_frame: pd.DataFrame,
    output_dir: Path,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []

    completed = validation_frame[
        validation_frame["status"] == "complete"
    ]

    for record in completed.itertuples(index=False):
        experiment_root = Path(record.experiment_root)
        summary_path = (
            experiment_root
            / "analysis"
            / "run_summary.csv"
        )

        if not summary_path.is_file():
            raise FileNotFoundError(
                f"Missing summary for completed run: "
                f"{summary_path}"
            )

        summary = pd.read_csv(summary_path)

        if summary.empty:
            raise ValueError(
                f"{summary_path}: summary is empty"
            )

        summary = summary.copy()
        summary.insert(0, "trace_name", record.trace_name)
        summary.insert(1, "repetition", record.repetition)
        summary.insert(
            2,
            "configuration_label",
            record.configuration_label,
        )

        rows.append(summary)

    if rows:
        combined = pd.concat(
            rows,
            ignore_index=True,
        )
    else:
        combined = pd.DataFrame()

    output_path = output_dir / "all_run_summaries.csv"
    combined.to_csv(output_path, index=False)

    print(f"Wrote: {output_path}")

    return combined


def print_status_summary(frame: pd.DataFrame) -> None:
    print("\n===== Evaluation status =====")

    summary = (
        frame.groupby(
            ["trace_name", "status"],
            dropna=False,
        )
        .size()
        .unstack(fill_value=0)
    )

    print(summary.to_string())

    mismatches = frame[
        (frame["status"] != "missing")
        & (~frame["configuration_matches"])
    ]

    if not mismatches.empty:
        print("\nWARNING: configuration mismatches detected:")
        print(
            mismatches[
                [
                    "trace_name",
                    "configuration_label",
                    "expected_policy",
                    "actual_policy",
                    "expected_estimator",
                    "actual_estimator",
                    "trace_csv",
                ]
            ].to_string(index=False)
        )


def main() -> int:
    args = parse_args()
    manifest = load_yaml(args.manifest)

    experiment_name = str(manifest["experiment_name"])

    manifest_results_dir = Path(
        manifest.get("runner", {}).get(
            "results_dir",
            "evaluation/experiments/results",
        )
    )

    results_dir = (
        args.results_dir
        if args.results_dir is not None
        else manifest_results_dir
    )

    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else results_dir / f"{experiment_name}_analysis"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    rows = build_validation_rows(
        manifest=manifest,
        results_dir=results_dir,
    )

    frame = pd.DataFrame(rows).sort_values(
        [
            "trace_name",
            "repetition",
            "configuration_label",
        ]
    )

    output_path = output_dir / "validation_report.csv"
    frame.to_csv(output_path, index=False)

    print_status_summary(frame)

    if args.refresh:
        refresh_completed_summaries(frame)

    collect_completed_run_summaries(
        validation_frame=frame,
        output_dir=output_dir,
    )

    print(f"\nWrote: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
