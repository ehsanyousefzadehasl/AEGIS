#!/usr/bin/env python3
"""Analyze AEGIS memory-estimator sensitivity runs.

This script is intentionally analysis-only. It reads a small manifest that
points to existing run roots under evaluation/experiments/results and writes a
separate Markdown/CSV report. It tolerates missing or incomplete runs so the
report can be regenerated while longer traces are still running.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


METRICS = [
    "makespan_s",
    "mean_jct_s",
    "p50_jct_s",
    "p95_jct_s",
    "mean_queue_wait_s",
    "p95_queue_wait_s",
    "mean_execution_span_s",
    "p95_execution_span_s",
]


def geomean(values: pd.Series) -> float:
    clean = [
        float(v)
        for v in values.dropna()
        if float(v) > 0.0 and math.isfinite(float(v))
    ]
    if not clean:
        return float("nan")
    return math.exp(sum(math.log(v) for v in clean) / len(clean))


def find_latest_run_dir(root: Path) -> Path | None:
    metadata_files = sorted(root.glob("*/**/metadata.json"))
    if not metadata_files:
        return None
    return metadata_files[-1].parent


def count_events(root: Path) -> tuple[Counter, Path | None]:
    events = sorted(root.rglob("events*.jsonl"))
    if not events:
        return Counter(), None

    event_file = events[-1]
    counter: Counter[str] = Counter()

    with event_file.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            counter[event.get("event", "unknown")] += 1

    return counter, event_file


def read_run_summary(run_dir: Path) -> dict[str, Any]:
    summary_path = run_dir.parent.parent / "analysis" / "run_summary.csv"
    if not summary_path.exists():
        # Some layouts may put analysis directly under the experiment root.
        summary_path = run_dir.parents[1] / "analysis" / "run_summary.csv"

    if not summary_path.exists():
        raise FileNotFoundError(f"Could not find run_summary.csv for {run_dir}")

    df = pd.read_csv(summary_path)
    if df.empty:
        raise ValueError(f"Empty run summary: {summary_path}")

    return df.iloc[0].to_dict()


def summarize_manifest(
    manifest_path: Path,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = yaml.safe_load(manifest_path.read_text())

    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []

    items: list[tuple[str, dict[str, Any]]] = []
    for item in data.get("runs", []):
        items.append(("estimator", item))
    for item in data.get("baselines", []):
        items.append(("baseline", item))

    for kind, item in items:
        trace = item["trace"]
        label = item["label"]
        estimator = item.get("estimator", "exclusive" if kind == "baseline" else "")
        root = Path(item["root"])

        counter: Counter[str] = Counter()
        event_file: Path | None = None
        run_dir: Path | None = None
        status = "missing"

        if root.exists():
            counter, event_file = count_events(root)
            run_dir = find_latest_run_dir(root)

            if counter["submitted"] > 0 and counter["submitted"] == counter["completed"]:
                status = "complete"
            elif counter["submitted"] > 0:
                status = "incomplete"
            else:
                status = "no_events"

        validation_rows.append(
            {
                "kind": kind,
                "trace": trace,
                "estimator": estimator,
                "label": label,
                "root": str(root),
                "run_dir": str(run_dir) if run_dir else "",
                "event_file": str(event_file) if event_file else "",
                "status": status,
                "submitted": int(counter["submitted"]),
                "dispatched": int(counter["dispatched"]),
                "launched": int(counter["launched"]),
                "completed": int(counter["completed"]),
                "failed": int(counter["failed"]),
                "recovered": int(counter["recovered"]),
            }
        )

        if status != "complete" or run_dir is None:
            continue

        summary = read_run_summary(run_dir)

        row = {
            "kind": kind,
            "trace": trace,
            "estimator": estimator,
            "label": label,
            "root": str(root),
            "run_dir": str(run_dir),
            "submitted": int(counter["submitted"]),
            "completed": int(counter["completed"]),
            "failed": int(counter["failed"]),
            "recovered": int(counter["recovered"]),
            "completion_rate": (
                float(counter["completed"]) / float(counter["submitted"])
                if counter["submitted"]
                else float("nan")
            ),
        }

        # Keep only metrics that exist in the current run summary.
        # Existing AEGIS summaries sometimes use names without the _s suffix.
        aliases = {
            "makespan_s": ["makespan_s", "makespan"],
            "mean_jct_s": ["mean_jct_s", "jct_mean_s", "mean_jct"],
            "p50_jct_s": [
                "p50_jct_s",
                "jct_p50_s",
                "median_jct_s",
                "p50_jct",
                "median_jct",
            ],
            "p95_jct_s": ["p95_jct_s", "jct_p95_s", "p95_jct"],
            "mean_queue_wait_s": [
                "mean_queue_wait_s",
                "initial_queue_wait_mean_s",
                "mean_queue_wait",
            ],
            "p95_queue_wait_s": [
                "p95_queue_wait_s",
                "initial_queue_wait_p95_s",
                "p95_queue_wait",
            ],
            "mean_execution_span_s": [
                "mean_execution_span_s",
                "execution_span_mean_s",
                "mean_execution_span",
            ],
            "p95_execution_span_s": [
                "p95_execution_span_s",
                "execution_span_p95_s",
                "p95_execution_span",
            ],
        }

        for canonical, candidates in aliases.items():
            row[canonical] = float("nan")
            for candidate in candidates:
                if candidate in summary and not pd.isna(summary[candidate]):
                    row[canonical] = summary[candidate]
                    break

        rows.append(row)

    validation = pd.DataFrame(validation_rows)
    summary = pd.DataFrame(rows)

    if summary.empty:
        validation.to_csv(output_dir / "validation_report.csv", index=False)
        return validation, summary, pd.DataFrame()

    # Normalize against Exclusive within each trace.
    normalized = summary.copy()

    for trace, trace_df in summary.groupby("trace"):
        baseline = trace_df[
            (trace_df["kind"] == "baseline") & (trace_df["label"] == "Exclusive")
        ]
        if baseline.empty:
            continue

        baseline_row = baseline.iloc[0]
        for metric in METRICS:
            if metric not in normalized.columns:
                continue
            base_value = float(baseline_row.get(metric, float("nan")))
            if not math.isfinite(base_value) or base_value <= 0:
                continue
            mask = normalized["trace"] == trace
            normalized.loc[mask, f"normalized_{metric}"] = (
                normalized.loc[mask, metric].astype(float) / base_value
            )

    # Aggregate only complete rows. Keep trace_count explicit because the report is incremental.
    estimator_rows = normalized[normalized["kind"] == "estimator"].copy()
    aggregate_rows: list[dict[str, Any]] = []

    for label, group in estimator_rows.groupby("label", sort=True):
        row = {
            "label": label,
            "trace_count": group["trace"].nunique(),
            "completion_rate_mean": group["completion_rate"].mean(),
            "failed_total": int(group["failed"].sum()),
            "recovered_total": int(group["recovered"].sum()),
        }
        for metric in METRICS:
            norm_col = f"normalized_{metric}"
            if norm_col in group.columns:
                row[f"geomean_{norm_col}"] = geomean(group[norm_col])
        aggregate_rows.append(row)

    aggregate = pd.DataFrame(aggregate_rows)

    validation.to_csv(output_dir / "validation_report.csv", index=False)
    normalized.to_csv(output_dir / "per_trace_estimator_summary.csv", index=False)
    aggregate.to_csv(output_dir / "aggregate_estimator_summary.csv", index=False)

    write_report(
        manifest_path=manifest_path,
        output_dir=output_dir,
        validation=validation,
        summary=normalized,
        aggregate=aggregate,
    )

    return validation, normalized, aggregate


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "_No rows._\n"

    table = df[columns].copy()
    for col in table.columns:
        if pd.api.types.is_float_dtype(table[col]):
            table[col] = table[col].map(
                lambda x: "" if pd.isna(x) else f"{float(x):.3f}"
            )

    return table.to_markdown(index=False)


def write_report(
    *,
    manifest_path: Path,
    output_dir: Path,
    validation: pd.DataFrame,
    summary: pd.DataFrame,
    aggregate: pd.DataFrame,
) -> None:
    complete = validation[validation["status"] == "complete"]
    incomplete = validation[validation["status"] != "complete"]

    lines: list[str] = []
    lines.append("# AEGIS Memory-Estimator Sensitivity\n")
    lines.append(
        "This report compares AEGIS variants that keep the same runtime "
        "pressure filter and placement policy while changing only the "
        "memory-feasibility input.\n"
    )
    lines.append(f"Manifest: `{manifest_path}`\n")
    lines.append("## Validation Status\n")
    lines.append(
        markdown_table(
            validation,
            [
                "kind",
                "trace",
                "label",
                "status",
                "submitted",
                "completed",
                "failed",
                "recovered",
            ],
        )
    )
    lines.append("\n")

    if not incomplete.empty:
        lines.append("## Incomplete or Missing Runs\n")
        lines.append(
            "These runs are listed in the analysis manifest but are excluded "
            "from performance summaries until they complete.\n"
        )
        lines.append(
            markdown_table(
                incomplete,
                [
                    "kind",
                    "trace",
                    "label",
                    "status",
                    "submitted",
                    "completed",
                    "failed",
                    "recovered",
                ],
            )
        )
        lines.append("\n")

    lines.append("## Per-Trace End-to-End Performance\n")
    estimator_summary = summary[summary["kind"] == "estimator"].copy()
    if estimator_summary.empty:
        lines.append("_No complete estimator runs found._\n")
    else:
        display_cols = [
            "trace",
            "label",
            "completion_rate",
            "normalized_makespan_s",
            "normalized_mean_jct_s",
            "normalized_p95_jct_s",
            "normalized_mean_queue_wait_s",
            "normalized_mean_execution_span_s",
            "failed",
            "recovered",
        ]
        display_cols = [c for c in display_cols if c in estimator_summary.columns]
        lines.append(markdown_table(estimator_summary, display_cols))
        lines.append("\n")

    lines.append("## Aggregate Across Completed Traces\n")
    if aggregate.empty:
        lines.append("_No aggregate rows._\n")
    else:
        display_cols = [
            "label",
            "trace_count",
            "completion_rate_mean",
            "geomean_normalized_makespan_s",
            "geomean_normalized_mean_jct_s",
            "geomean_normalized_p95_jct_s",
            "geomean_normalized_mean_queue_wait_s",
            "geomean_normalized_mean_execution_span_s",
            "failed_total",
            "recovered_total",
        ]
        display_cols = [c for c in display_cols if c in aggregate.columns]
        lines.append(markdown_table(aggregate, display_cols))
        lines.append("\n")

    lines.append("## Initial Takeaways\n")
    lines.append(
        "- Underestimation can surface as failed/recovered attempts, while "
        "overestimation can reduce collocation opportunities and increase queueing.\n"
    )
    lines.append(
        "- Because the report is incremental, compare aggregate rows using "
        "`trace_count`; not every estimator has completed on every trace yet.\n"
    )
    lines.append(
        "- The estimator with the best raw memory accuracy is not necessarily "
        "the estimator with the best system-level trade-off, because memory "
        "estimates affect feasibility, placement trajectory, queueing, "
        "interference, and recovery.\n"
    )

    report_path = output_dir / "estimator_sensitivity_report.md"
    report_path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evaluation/experiments/manifests/estimator_sensitivity_analysis.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evaluation/experiments/results/estimator_sensitivity_analysis"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validation, summary, aggregate = summarize_manifest(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
    )

    print(f"Wrote {args.output_dir}")
    print(f"validation rows: {len(validation)}")
    print(f"complete summary rows: {len(summary)}")
    print(f"aggregate rows: {len(aggregate)}")


if __name__ == "__main__":
    main()
