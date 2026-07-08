#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


RAW_TO_DISPLAY = {
    "EST-MAGM__horus": "AEGIS+HorusMem",
    "HORUS__horus": "Horus",
    "LUCID": "Lucid",
    "OR-MAGM": "AEGIS-EstimatorFree",
    "exclusive": "Exclusive",
    "oracle-MAGM": "AEGIS+PeakMem",
}

DISPLAY_ORDER = [
    "Exclusive",
    "Horus",
    "Lucid",
    "AEGIS+HorusMem",
    "AEGIS+PeakMem",
    "AEGIS-EstimatorFree",
]

METRIC_PATTERNS = {
    "gpu_memory": [
        "memory",
        "fb_used",
        "fbused",
        "gpu_memory",
        "used_gpu_memory",
        "mem_used",
    ],
    "smact": ["smact", "sm_active", "sm_active_pct"],
    "smocc": ["smocc", "sm_occupancy", "sm_occ"],
    "drama": ["drama", "dram_active", "dram_active_pct"],
    "power": ["power", "pwr", "power_usage"],
    "energy": [
        "total_energy",
        "energy_consumption",
        "energy",
        "totec",
        "DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION",
    ],
}

TIME_PATTERNS = [
    "timestamp",
    "time",
    "datetime",
    "date",
    "wall_time",
    "walltime",
    "ts",
]

GPU_PATTERNS = [
    "gpu",
    "gpu_id",
    "device",
    "device_id",
    "gpu_index",
    "index",
]


@dataclass(frozen=True)
class RunKey:
    trace: str
    raw_label: str
    policy: str
    experiment_name: str


@dataclass
class TelemetryFrame:
    path: Path
    frame: pd.DataFrame
    time_col: str | None
    gpu_col: str | None
    metric_cols: dict[str, list[str]]


def norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def display_policy(raw: str) -> str:
    return RAW_TO_DISPLAY.get(raw, raw)


def order_key(policy: str) -> tuple[int, str]:
    try:
        return (DISPLAY_ORDER.index(policy), policy)
    except ValueError:
        return (len(DISPLAY_ORDER), policy)


def read_run_keys(analysis_dir: Path) -> list[RunKey]:
    keys: dict[tuple[str, str, str], RunKey] = {}

    for csv_path in sorted((analysis_dir / "traces").glob("*/normalized_jct_values.csv")):
        trace = csv_path.parent.name
        frame = pd.read_csv(csv_path)

        required = {"experiment_name", "run_label"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{csv_path}: missing columns {sorted(missing)}")

        for row in frame[["experiment_name", "run_label"]].drop_duplicates().itertuples(index=False):
            experiment_name = str(row.experiment_name)
            raw_label = str(row.run_label)
            policy = display_policy(raw_label)
            keys[(trace, raw_label, experiment_name)] = RunKey(
                trace=trace,
                raw_label=raw_label,
                policy=policy,
                experiment_name=experiment_name,
            )

    return sorted(keys.values(), key=lambda k: (k.trace, order_key(k.policy), k.experiment_name))


def find_run_dir(runs_root: Path, experiment_name: str, raw_label: str) -> Path | None:
    candidates = [
        runs_root / experiment_name,
        runs_root / experiment_name / raw_label,
        runs_root / experiment_name / raw_label.upper(),
        runs_root / experiment_name / raw_label.lower(),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    matches = [p for p in runs_root.rglob(experiment_name) if p.is_dir()]
    if len(matches) == 1:
        return matches[0]

    if matches:
        # Prefer a directory with runtime/task logs, if there are several.
        ranked = sorted(
            matches,
            key=lambda p: (
                not (p / "runtime").exists(),
                len(str(p)),
            ),
        )
        return ranked[0]

    return None


def maybe_parse_time(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        values = pd.to_numeric(series, errors="coerce")
        # If it looks like unix seconds, keep seconds. If monotonic/sample index,
        # it still works for ordering but not absolute event alignment.
        return values.astype(float)

    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    if parsed.notna().any():
        return parsed.astype("int64") / 1e9

    return pd.to_numeric(series, errors="coerce").astype(float)


def find_time_col(frame: pd.DataFrame) -> str | None:
    columns = list(frame.columns)
    scored: list[tuple[int, str]] = []
    for col in columns:
        n = norm_name(col)
        for i, pattern in enumerate(TIME_PATTERNS):
            if pattern in n:
                scored.append((i, col))
                break
    if scored:
        return sorted(scored)[0][1]
    return None


def find_gpu_col(frame: pd.DataFrame) -> str | None:
    columns = list(frame.columns)
    for col in columns:
        n = norm_name(col)
        if n in {"gpu", "gpu_id", "gpu_index", "device", "device_id", "index"}:
            return col
    for col in columns:
        n = norm_name(col)
        if any(pattern == n or pattern in n for pattern in GPU_PATTERNS):
            # Avoid picking metric columns such as gpu_memory.
            if "memory" not in n and "util" not in n:
                return col
    return None


def numeric_metric_columns(frame: pd.DataFrame) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {k: [] for k in METRIC_PATTERNS}

    for col in frame.columns:
        n = norm_name(col)
        numeric = pd.to_numeric(frame[col], errors="coerce")
        if numeric.notna().sum() == 0:
            continue

        for metric, patterns in METRIC_PATTERNS.items():
            if any(norm_name(p) in n for p in patterns):
                out[metric].append(col)

    # Remove energy from power if a column matched both.
    for col in list(out["power"]):
        n = norm_name(col)
        if "energy" in n or "totec" in n:
            out["power"].remove(col)

    return out


def looks_like_telemetry_csv(path: Path) -> bool:
    name = norm_name(path.name)
    return any(
        token in name
        for token in [
            "dcgm",
            "dmon",
            "nvidia",
            "telemetry",
            "monitor",
            "gpu",
            "metrics",
            "samples",
        ]
    )


def load_telemetry_frames(run_dir: Path) -> list[TelemetryFrame]:
    frames: list[TelemetryFrame] = []

    for path in sorted(run_dir.rglob("*.csv")):
        if "analysis" in path.parts[-4:] or "summary" in path.name.lower():
            pass

        if not looks_like_telemetry_csv(path):
            # Still inspect small-ish CSVs because telemetry filenames may vary.
            pass

        try:
            frame = pd.read_csv(path, nrows=5)
        except Exception:
            continue

        metric_cols = numeric_metric_columns(frame)
        if not any(metric_cols.values()):
            continue

        # Re-read full file only after it looks useful.
        try:
            full = pd.read_csv(path)
        except Exception:
            continue

        metric_cols = numeric_metric_columns(full)
        if not any(metric_cols.values()):
            continue

        frames.append(
            TelemetryFrame(
                path=path,
                frame=full,
                time_col=find_time_col(full),
                gpu_col=find_gpu_col(full),
                metric_cols=metric_cols,
            )
        )

    return frames


def event_time_candidates(obj: dict[str, Any]) -> list[float]:
    candidates: list[float] = []

    def visit(value: Any, key: str = "") -> None:
        key_n = norm_name(key)
        if isinstance(value, dict):
            for k, v in value.items():
                visit(v, k)
        elif isinstance(value, (int, float)):
            if any(token in key_n for token in ["time", "timestamp", "wall"]):
                v = float(value)
                # Keep plausible unix seconds or monotonic seconds.
                if math.isfinite(v) and v > 0:
                    candidates.append(v)
        elif isinstance(value, str):
            if any(token in key_n for token in ["time", "timestamp", "wall", "date"]):
                parsed = pd.to_datetime(pd.Series([value]), errors="coerce", utc=True)
                if parsed.notna().iloc[0]:
                    candidates.append(float(parsed.astype("int64").iloc[0]) / 1e9)
                else:
                    try:
                        v = float(value)
                        if math.isfinite(v) and v > 0:
                            candidates.append(v)
                    except Exception:
                        pass

    visit(obj)
    return candidates


def infer_window_from_events(run_dir: Path) -> tuple[float | None, float | None, str]:
    event_paths = sorted(run_dir.rglob("*.jsonl"))
    event_paths += sorted(run_dir.rglob("events*.json"))

    times: list[float] = []

    for path in event_paths:
        name = norm_name(path.name)
        if "event" not in name and "runtime" not in str(path):
            continue

        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue

        if path.suffix == ".jsonl":
            lines = text.splitlines()
            records = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
        else:
            try:
                data = json.loads(text)
            except Exception:
                continue
            records = data if isinstance(data, list) else [data]

        for record in records:
            if isinstance(record, dict):
                # We intentionally use all runtime event times. This usually gives
                # first scheduling/task event to last completion event. The report
                # records the source as inferred, so we can audit it later.
                times.extend(event_time_candidates(record))

    if not times:
        return None, None, "telemetry_minmax"

    # Remove obviously monotonic tiny times if mixed with unix timestamps.
    unix_like = [t for t in times if t > 1_000_000_000]
    if unix_like:
        times = unix_like

    return min(times), max(times), "events_inferred"


def frame_time_series(tf: TelemetryFrame) -> pd.Series | None:
    if tf.time_col is None:
        return None
    values = maybe_parse_time(tf.frame[tf.time_col])
    if values.notna().sum() == 0:
        return None
    return values


def restrict_window(tf: TelemetryFrame, start: float | None, end: float | None) -> pd.DataFrame:
    frame = tf.frame.copy()
    times = frame_time_series(tf)

    if times is None or start is None or end is None:
        return frame

    # If telemetry looks like unix time but event window is unix time, align.
    # If telemetry is sample index, this filter may drop everything; fall back.
    mask = (times >= start) & (times <= end)
    if mask.sum() > 5:
        return frame.loc[mask].copy()

    return frame


def summarize_numeric(values: pd.Series) -> dict[str, float]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {}
    return {
        "mean": float(numeric.mean()),
        "p50": float(numeric.quantile(0.50)),
        "p95": float(numeric.quantile(0.95)),
        "max": float(numeric.max()),
    }


def convert_memory_to_gb(value: float, column_name: str) -> float:
    n = norm_name(column_name)
    if "mib" in n or "mb" in n:
        return value / 1024.0
    if "kib" in n or "kb" in n:
        return value / (1024.0 * 1024.0)
    if "byte" in n or value > 1e6:
        return value / (1024.0 ** 3)
    # Assume already GiB/GB if values are small.
    return value


def convert_energy_to_j(value: float, column_name: str) -> float:
    n = norm_name(column_name)
    if "mj" in n or "millij" in n:
        return value / 1000.0
    if "kj" in n:
        return value * 1000.0
    # DCGM total energy is often in millijoules in some exports, but names vary.
    # Keep as J unless the name strongly says mJ. Ratios are still meaningful.
    return value


def energy_delta_for_frame(tf: TelemetryFrame, start: float | None, end: float | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    energy_cols = tf.metric_cols.get("energy", [])
    if not energy_cols:
        return rows

    times = frame_time_series(tf)
    frame = tf.frame.copy()

    if times is None:
        return rows

    frame["_time_s"] = times
    frame = frame.dropna(subset=["_time_s"])
    if frame.empty:
        return rows

    if start is None:
        start = float(frame["_time_s"].min())
    if end is None:
        end = float(frame["_time_s"].max())

    gpu_col = tf.gpu_col
    groups: list[tuple[str, pd.DataFrame]]
    if gpu_col and gpu_col in frame.columns:
        groups = [(str(g), part.copy()) for g, part in frame.groupby(gpu_col)]
    else:
        groups = [("all", frame)]

    for gpu_id, part in groups:
        part = part.sort_values("_time_s")
        for col in energy_cols:
            numeric = pd.to_numeric(part[col], errors="coerce")
            valid = part.loc[numeric.notna(), ["_time_s"]].copy()
            valid[col] = numeric[numeric.notna()]
            if len(valid) < 2:
                continue

            before_start = valid.iloc[(valid["_time_s"] - start).abs().argmin()]
            before_end = valid.iloc[(valid["_time_s"] - end).abs().argmin()]
            delta_raw = float(before_end[col]) - float(before_start[col])

            if not math.isfinite(delta_raw) or delta_raw < 0:
                continue

            rows.append(
                {
                    "telemetry_file": str(tf.path),
                    "gpu_id": gpu_id,
                    "energy_column": col,
                    "energy_start_raw": float(before_start[col]),
                    "energy_end_raw": float(before_end[col]),
                    "energy_delta_raw": delta_raw,
                    "energy_delta_j": convert_energy_to_j(delta_raw, col),
                    "start_sample_time_s": float(before_start["_time_s"]),
                    "end_sample_time_s": float(before_end["_time_s"]),
                }
            )

    return rows


def summarize_run(run_key: RunKey, run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    frames = load_telemetry_frames(run_dir)
    start, end, window_source = infer_window_from_events(run_dir)

    summary: dict[str, Any] = {
        "trace": run_key.trace,
        "raw_label": run_key.raw_label,
        "policy": run_key.policy,
        "experiment_name": run_key.experiment_name,
        "run_dir": str(run_dir),
        "window_source": window_source,
        "window_start_s": start,
        "window_end_s": end,
        "window_duration_s": (end - start) if start is not None and end is not None else np.nan,
        "telemetry_file_count": len(frames),
    }

    metric_details: list[dict[str, Any]] = []
    energy_details: list[dict[str, Any]] = []

    metric_values: dict[str, list[tuple[str, pd.Series]]] = {k: [] for k in ["gpu_memory", "smact", "smocc", "drama", "power"]}

    for tf in frames:
        restricted = restrict_window(tf, start, end)

        for metric in metric_values:
            for col in tf.metric_cols.get(metric, []):
                series = pd.to_numeric(restricted[col], errors="coerce")
                if series.notna().sum() == 0:
                    continue

                if metric == "gpu_memory":
                    series = series.map(lambda v: convert_memory_to_gb(float(v), col) if pd.notna(v) else np.nan)

                metric_values[metric].append((f"{tf.path}:{col}", series))

                stats = summarize_numeric(series)
                for stat, value in stats.items():
                    metric_details.append(
                        {
                            "trace": run_key.trace,
                            "policy": run_key.policy,
                            "raw_label": run_key.raw_label,
                            "experiment_name": run_key.experiment_name,
                            "telemetry_file": str(tf.path),
                            "metric": metric,
                            "column": col,
                            "stat": stat,
                            "value": value,
                        }
                    )

        energy_rows = energy_delta_for_frame(tf, start, end)
        for row in energy_rows:
            row.update(
                {
                    "trace": run_key.trace,
                    "policy": run_key.policy,
                    "raw_label": run_key.raw_label,
                    "experiment_name": run_key.experiment_name,
                    "run_dir": str(run_dir),
                }
            )
            energy_details.append(row)

    for metric, items in metric_values.items():
        if not items:
            continue

        concat = pd.concat([series for _, series in items], ignore_index=True)
        stats = summarize_numeric(concat)

        unit_suffix = "_gb" if metric == "gpu_memory" else ""
        for stat, value in stats.items():
            summary[f"{metric}_{stat}{unit_suffix}"] = value

    if energy_details:
        # Avoid double-counting if multiple energy columns appear in one file.
        # Prefer the column with largest number of per-GPU rows.
        energy_frame = pd.DataFrame(energy_details)
        group_counts = (
            energy_frame.groupby(["telemetry_file", "energy_column"])
            .size()
            .sort_values(ascending=False)
        )
        best_file, best_col = group_counts.index[0]
        chosen = energy_frame[
            (energy_frame["telemetry_file"] == best_file)
            & (energy_frame["energy_column"] == best_col)
        ]
        summary["energy_source_file"] = str(best_file)
        summary["energy_source_column"] = str(best_col)
        summary["total_gpu_energy_j"] = float(chosen["energy_delta_j"].sum())
        summary["energy_gpu_count"] = int(chosen["gpu_id"].nunique())
    else:
        summary["energy_source_file"] = ""
        summary["energy_source_column"] = ""
        summary["total_gpu_energy_j"] = np.nan
        summary["energy_gpu_count"] = 0

    return summary, metric_details, energy_details


def add_normalized_energy(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    out["normalized_energy_vs_exclusive"] = np.nan

    for trace, part in out.groupby("trace"):
        exclusive = part[part["policy"] == "Exclusive"]["total_gpu_energy_j"].dropna()
        if exclusive.empty:
            continue
        base = float(exclusive.iloc[0])
        if base <= 0:
            continue
        idx = out["trace"] == trace
        out.loc[idx, "normalized_energy_vs_exclusive"] = out.loc[idx, "total_gpu_energy_j"] / base

    return out


def write_markdown(summary: pd.DataFrame, output_path: Path) -> None:
    columns = [
        "trace",
        "policy",
        "window_duration_s",
        "gpu_memory_mean_gb",
        "gpu_memory_p95_gb",
        "smact_mean",
        "smocc_mean",
        "drama_mean",
        "power_mean",
        "total_gpu_energy_j",
        "normalized_energy_vs_exclusive",
        "telemetry_file_count",
        "energy_gpu_count",
        "window_source",
    ]
    existing = [c for c in columns if c in summary.columns]
    table = summary[existing].copy()

    for col in table.columns:
        if pd.api.types.is_numeric_dtype(table[col]):
            table[col] = table[col].map(lambda v: "" if pd.isna(v) else f"{v:.4g}")

    text = []
    text.append("# Resource and Energy Evidence\n")
    text.append(
        "This report is generated as secondary evidence. It summarizes GPU telemetry "
        "over inferred trace windows and computes GPU energy-to-solution when "
        "cumulative energy counters are available.\n"
    )
    text.append(
        "Energy is computed per GPU as the difference between the cumulative energy "
        "counter near the inferred trace end and start, then summed across GPUs. "
        "Normalized energy is relative to Exclusive within each trace.\n"
    )
    text.append(table.to_markdown(index=False))
    text.append("\n\n## Notes\n")
    text.append("- Check `window_source`: `events_inferred` is preferred; `telemetry_minmax` means the script used the telemetry file span.\n")
    text.append("- Check `energy_source_column` in the CSV to verify the DCGMI energy counter and unit.\n")
    text.append("- Use energy-to-solution, not average power alone, for paper claims.\n")

    output_path.write_text("\n".join(text))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=Path("evaluation/experiments/results/final_representative_evaluation_analysis"),
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("evaluation/experiments/results"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evaluation/experiments/results/final_representative_evaluation_analysis/resource_energy_evidence"),
    )
    args = parser.parse_args()

    keys = read_run_keys(args.analysis_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []
    metric_details: list[dict[str, Any]] = []
    energy_details: list[dict[str, Any]] = []
    missing_runs: list[dict[str, str]] = []

    for key in keys:
        run_dir = find_run_dir(args.runs_root, key.experiment_name, key.raw_label)
        if run_dir is None:
            missing_runs.append(
                {
                    "trace": key.trace,
                    "policy": key.policy,
                    "raw_label": key.raw_label,
                    "experiment_name": key.experiment_name,
                }
            )
            continue

        print(f"[INFO] {key.trace} / {key.policy}: {run_dir}")
        summary, metric_rows, energy_rows = summarize_run(key, run_dir)
        summaries.append(summary)
        metric_details.extend(metric_rows)
        energy_details.extend(energy_rows)

    summary_frame = pd.DataFrame(summaries)
    if not summary_frame.empty:
        summary_frame = add_normalized_energy(summary_frame)
        summary_frame = summary_frame.sort_values(
            by=["trace", "policy"],
            key=lambda s: s.map(lambda x: order_key(str(x))[0]) if s.name == "policy" else s,
        )

    summary_path = args.output_dir / "resource_energy_summary.csv"
    details_path = args.output_dir / "resource_metric_details.csv"
    energy_path = args.output_dir / "resource_energy_by_gpu.csv"
    missing_path = args.output_dir / "missing_runs.csv"
    report_path = args.output_dir / "resource_energy_summary.md"

    summary_frame.to_csv(summary_path, index=False)
    pd.DataFrame(metric_details).to_csv(details_path, index=False)
    pd.DataFrame(energy_details).to_csv(energy_path, index=False)
    pd.DataFrame(missing_runs).to_csv(missing_path, index=False)

    if not summary_frame.empty:
        write_markdown(summary_frame, report_path)

    print(f"[DONE] wrote {summary_path}")
    print(f"[DONE] wrote {details_path}")
    print(f"[DONE] wrote {energy_path}")
    print(f"[DONE] wrote {missing_path}")
    if report_path.exists():
        print(f"[DONE] wrote {report_path}")


if __name__ == "__main__":
    main()
