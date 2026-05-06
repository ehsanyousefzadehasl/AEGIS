#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = REPO_ROOT / "evaluation" / "profiling" / "solo" / "runs"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evaluation" / "profiling" / "solo" / "extracted"

TIME_RE = {
    "training_loop_time_s": re.compile(r"training_loop_time_s:\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE),
    "end_to_end_time_s": re.compile(r"end_to_end_time_s:\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE),
}

PROFILE_STATS = ["mean", "max", "median", "mode", "p95", "ewma"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract solo profiling results into CSV.")
    p.add_argument("--runs-root", type=str, default=str(DEFAULT_RUNS_ROOT))
    p.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--window-sec", type=float, default=200.0)
    return p.parse_args()


def safe_float(x: Any) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        if isinstance(x, float) and math.isnan(x):
            return None
        return float(x)
    s = str(x).strip()
    if not s or s.upper() == "N/A" or s.upper() == "[N/A]":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def safe_int(x: Any) -> int | None:
    v = safe_float(x)
    if v is None:
        return None
    return int(v)

def resolve_target_uuids(meta: dict[str, Any], uuid_map: dict[int, str]) -> list[str]:
    explicit = meta.get("assigned_gpu_uuids", [])
    if isinstance(explicit, list) and explicit:
        return [str(x).strip() for x in explicit if str(x).strip()]

    visible_devices = parse_visible_devices(meta)
    return [uuid_map[idx] for idx in visible_devices if idx in uuid_map]

def window_alpha(window_size: int) -> float:
    if window_size <= 0:
        return 0.5
    return 2.0 / (window_size + 1.0)

def first_mode_or_none(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    counts = Counter(s.tolist())
    top_count = max(counts.values())
    if top_count <= 1:
        return None
    mode_value = min(v for v, c in counts.items() if c == top_count)
    return float(mode_value)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def load_index_map(runs_root: Path) -> dict[str, dict[str, str]]:
    index_path = runs_root / "index.csv"
    if not index_path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    with open(index_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_dir = row.get("run_dir")
            if run_dir:
                out[str(Path(run_dir).resolve())] = row
    return out


def discover_run_dirs(runs_root: Path) -> list[Path]:
    run_dirs: list[Path] = []
    for workload_dir in sorted(runs_root.iterdir()):
        if not workload_dir.is_dir():
            continue
        for run_dir in sorted(workload_dir.iterdir()):
            if run_dir.is_dir():
                run_dirs.append(run_dir.resolve())
    return run_dirs


def current_uuid_map_by_index() -> dict[int, str]:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,uuid",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        return {}

    mapping: dict[int, str] = {}
    for line in out.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            idx = int(parts[0])
        except ValueError:
            continue
        mapping[idx] = parts[1]
    return mapping


def parse_visible_devices(meta: dict[str, Any]) -> list[int]:
    value = str(meta.get("cuda_visible_devices", "")).strip()
    if not value:
        return []
    out: list[int] = []
    for tok in value.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(int(tok))
        except ValueError:
            pass
    return out


def extract_times_from_stdout(stdout_text: str) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for key, pattern in TIME_RE.items():
        m = pattern.search(stdout_text)
        out[key] = float(m.group(1)) if m else None
    return out


def extract_faketensor_value(run_dir: Path, stdout_text: str) -> float | None:
    faketensor_file = run_dir / "artifacts" / "faketensor" / "faketensor.txt"
    text = read_text(faketensor_file)
    if not text:
        text = stdout_text

    candidates: list[float] = []
    for line in text.splitlines():
        if "faketensor" not in line.lower():
            continue
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", line)
        for n in nums:
            try:
                candidates.append(float(n))
            except ValueError:
                pass

    if not candidates:
        return None
    return candidates[-1]


def normalize_nvidia_smi_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename = {
        "timestamp": "timestamp",
        "uuid": "uuid",
        "utilization.gpu": "utilization_gpu",
        "utilization.memory": "utilization_memory",
        "memory.used": "memory_used",
        "memory.free": "memory_free",
        "memory.total": "memory_total",
        "power.draw": "power_draw",
        "temperature.gpu": "temperature_gpu",
    }
    df = df.rename(columns=rename)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in [
        "utilization_gpu",
        "utilization_memory",
        "memory_used",
        "memory_free",
        "memory_total",
        "power_draw",
        "temperature_gpu",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "uuid" in df.columns:
        df["uuid"] = df["uuid"].astype(str).str.strip()
    return df


def active_start_from_nvidia(df: pd.DataFrame) -> pd.Timestamp | None:
    if df.empty or "timestamp" not in df.columns or "memory_used" not in df.columns:
        return None
    active = df[df["memory_used"].fillna(0) > 0]
    if active.empty:
        return None
    return active["timestamp"].min()


def summarize_nvidia_memory(
    csv_path: Path,
    target_uuids_in_order: list[str],
    window_sec: float,
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    if not csv_path.exists() or not target_uuids_in_order:
        return out

    try:
        df = pd.read_csv(csv_path, skipinitialspace=True)
    except Exception:
        return out

    df = normalize_nvidia_smi_columns(df)
    if "uuid" not in df.columns or "memory_used" not in df.columns or "timestamp" not in df.columns:
        return out

    df = df[df["uuid"].isin(target_uuids_in_order)].copy()
    if df.empty:
        return out

    start_ts = active_start_from_nvidia(df)
    if start_ts is None:
        return out

    df_full = df[df["timestamp"] >= start_ts].copy()
    df_200 = df_full[df_full["timestamp"] < start_ts + pd.Timedelta(seconds=window_sec)].copy()

    if len(target_uuids_in_order) == 1:
        uuid = target_uuids_in_order[0]
        one_full = df_full[df_full["uuid"] == uuid]
        one_200 = df_200[df_200["uuid"] == uuid]

        out["gpu_memory_peak_full_mib"] = (
            safe_float(one_full["memory_used"].max()) if not one_full.empty else None
        )
        out["gpu_memory_peak_200s_mib"] = (
            safe_float(one_200["memory_used"].max()) if not one_200.empty else None
        )
        return out

    peaks_full: list[float | None] = []
    peaks_200: list[float | None] = []

    for pos, uuid in enumerate(target_uuids_in_order):
        suffix = f"_gpu_{chr(ord('a') + pos)}"
        one_full = df_full[df_full["uuid"] == uuid]
        one_200 = df_200[df_200["uuid"] == uuid]

        full_peak = safe_float(one_full["memory_used"].max()) if not one_full.empty else None
        win_peak = safe_float(one_200["memory_used"].max()) if not one_200.empty else None

        out[f"gpu_memory_peak_full_mib{suffix}"] = full_peak
        out[f"gpu_memory_peak_200s_mib{suffix}"] = win_peak

        peaks_full.append(full_peak)
        peaks_200.append(win_peak)

    out["gpu_memory_peak_full_mib_sum"] = (
        sum(v for v in peaks_full if v is not None) if any(v is not None for v in peaks_full) else None
    )
    out["gpu_memory_peak_200s_mib_sum"] = (
        sum(v for v in peaks_200 if v is not None) if any(v is not None for v in peaks_200) else None
    )

    return out

def energy_delta(series: pd.Series) -> tuple[float | None, float | None]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty or len(s) < 2:
        return None, None
    delta_mj = float(s.iloc[-1] - s.iloc[0])
    if delta_mj < 0:
        return None, None
    return delta_mj, delta_mj / 1000.0

def parse_dcgm_log(dcgm_path: Path) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    if not dcgm_path.exists():
        return pd.DataFrame()

    header_cols: list[str] | None = None
    current_ts: pd.Timestamp | None = None

    with open(dcgm_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("# timestamp:"):
                ts_text = stripped.split(":", 1)[1].strip()
                current_ts = pd.to_datetime(ts_text, errors="coerce")
                continue

            if stripped.startswith("#Entity"):
                header_cols = stripped.lstrip("#").split()
                continue

            if stripped.startswith("GPU ") and current_ts is not None and header_cols:
                parts = stripped.split()
                if len(parts) < 3:
                    continue

                try:
                    gpu_index = int(parts[1])
                except ValueError:
                    continue

                values = parts[2:]
                metric_cols = header_cols[1:]  # skip Entity
                if len(values) < len(metric_cols):
                    continue

                rec: dict[str, Any] = {"timestamp": current_ts, "gpu_index": gpu_index}
                for col, val in zip(metric_cols, values):
                    rec[col] = safe_float(val)
                records.append(rec)

    if not records:
        return pd.DataFrame()

    return pd.DataFrame.from_records(records)


def active_start_from_dcgm(df: pd.DataFrame, metrics: list[str]) -> pd.Timestamp | None:
    if df.empty or "timestamp" not in df.columns:
        return None
    keep = [m for m in metrics if m in df.columns]
    if not keep:
        return None

    active_mask = pd.Series(False, index=df.index)
    for m in keep:
        active_mask = active_mask | (pd.to_numeric(df[m], errors="coerce").fillna(0) > 0)

    active = df[active_mask]
    if active.empty:
        return None
    return active["timestamp"].min()


def summarize_one_metric(series: pd.Series) -> dict[str, float | None]:
    s = pd.to_numeric(series, errors="coerce").dropna()

    if s.empty:
        return {stat: None for stat in PROFILE_STATS}

    alpha = window_alpha(len(s))

    return {
        "mean": safe_float(s.mean()),
        "max": safe_float(s.max()),
        "median": safe_float(s.median()),
        "mode": first_mode_or_none(s),
        "p95": safe_float(s.quantile(0.95)),
        "ewma": safe_float(s.ewm(alpha=alpha, adjust=False).mean().iloc[-1]),
    }


def summarize_dcgm(
    dcgm_path: Path,
    target_gpu_indices_in_order: list[int],
    window_sec: float,
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    if not dcgm_path.exists() or not target_gpu_indices_in_order:
        return out

    df = parse_dcgm_log(dcgm_path)
    if df.empty:
        return out

    df = df[df["gpu_index"].isin(target_gpu_indices_in_order)].copy()
    if df.empty:
        return out

    start_ts = active_start_from_dcgm(df, metrics=["GPUTL", "SMACT", "SMOCC", "DRAMA"])
    if start_ts is None:
        return out

    df_full = df[df["timestamp"] >= start_ts].copy()
    df_200 = df_full[df_full["timestamp"] < start_ts + pd.Timedelta(seconds=window_sec)].copy()

    metric_cols = [
        c
        for c in df.columns
        if c not in {"timestamp", "gpu_index"} and pd.api.types.is_numeric_dtype(df[c])
    ]

    if len(target_gpu_indices_in_order) == 1:
        gpu_idx = target_gpu_indices_in_order[0]
        one_full = df_full[df_full["gpu_index"] == gpu_idx]
        one_200 = df_200[df_200["gpu_index"] == gpu_idx]

        for metric in metric_cols:
            metric_l = metric.lower()

            if metric_l == "totec":
                full_mj, full_j = energy_delta(one_full[metric]) if metric in one_full.columns else (None, None)
                out[f"{metric_l}_delta_mj"] = full_mj
                out[f"{metric_l}_delta_j"] = full_j
                continue

            stats_full = (
                summarize_one_metric(one_full[metric])
                if metric in one_full.columns
                else {}
            )
            stats_200 = (
                summarize_one_metric(one_200[metric])
                if metric in one_200.columns
                else {}
            )

            for stat_name in PROFILE_STATS:
                out[f"{metric_l}_{stat_name}_full"] = stats_full.get(stat_name)
                out[f"{metric_l}_{stat_name}_200s"] = stats_200.get(stat_name)

        return out

    for pos, gpu_idx in enumerate(target_gpu_indices_in_order):
        suffix = f"_gpu_{chr(ord('a') + pos)}"
        one_full = df_full[df_full["gpu_index"] == gpu_idx]
        one_200 = df_200[df_200["gpu_index"] == gpu_idx]

        for metric in metric_cols:
            metric_l = metric.lower()

            if metric_l == "totec":
                full_mj, full_j = energy_delta(one_full[metric]) if metric in one_full.columns else (None, None)
                out[f"{metric_l}_delta_mj{suffix}"] = full_mj
                out[f"{metric_l}_delta_j{suffix}"] = full_j
                continue

            stats_full = summarize_one_metric(one_full[metric]) if metric in one_full.columns else {}
            stats_200 = summarize_one_metric(one_200[metric]) if metric in one_200.columns else {}

            for stat_name in PROFILE_STATS:
                out[f"{metric_l}_{stat_name}_full{suffix}"] = stats_full.get(stat_name)
                out[f"{metric_l}_{stat_name}_200s{suffix}"] = stats_200.get(stat_name)

    return out


def build_common_row(
    run_dir: Path,
    index_map: dict[str, dict[str, str]],
    uuid_map: dict[int, str],
) -> dict[str, Any]:
    meta = read_json(run_dir / "meta.json")
    time_json = read_json(run_dir / "time.json")
    stdout_text = read_text(run_dir / "stdout.log")
    exitcode_text = read_text(run_dir / "exitcode.txt").strip()

    visible_devices = parse_visible_devices(meta)
    target_uuids = resolve_target_uuids(meta, uuid_map)

    times = extract_times_from_stdout(stdout_text)
    faketensor_est = extract_faketensor_value(run_dir, stdout_text)

    row: dict[str, Any] = {
        "workload_id": meta.get("workload_id"),
        "run_id": meta.get("run_id"),
        "spec_path": meta.get("spec_path"),
        "run_dir": str(run_dir),
        "gpu_count": len(visible_devices) if visible_devices else None,
        "cuda_visible_devices": meta.get("cuda_visible_devices"),
        "assigned_gpu_a_index": visible_devices[0] if len(visible_devices) >= 1 else None,
        "assigned_gpu_b_index": visible_devices[1] if len(visible_devices) >= 2 else None,
        "assigned_gpu_a_uuid": target_uuids[0] if len(target_uuids) >= 1 else None,
        "assigned_gpu_b_uuid": target_uuids[1] if len(target_uuids) >= 2 else None,
        "elapsed_seconds_index": safe_float(index_map.get(str(run_dir), {}).get("elapsed_seconds")),
        "elapsed_seconds_time_json": safe_float(time_json.get("elapsed_seconds")),
        "training_loop_time_s": times.get("training_loop_time_s"),
        "end_to_end_time_s": times.get("end_to_end_time_s"),
        "exit_code": safe_int(exitcode_text) if exitcode_text else safe_int(time_json.get("exit_code")),
        "gpu_memory_requirement_mib": meta.get("resources", {}).get("gpu_memory_requirement_mib"),
        "faketensor_estimate": faketensor_est,
        "summary_exists": (run_dir / "artifacts" / "summary" / "summary.txt").exists(),
        "summary_path": str(run_dir / "artifacts" / "summary" / "summary.txt"),
        "faketensor_path": str(run_dir / "artifacts" / "faketensor" / "faketensor.txt"),
    }

    row.update(
        summarize_nvidia_memory(
            run_dir / "nvidia_smi.csv",
            target_uuids_in_order=target_uuids,
            window_sec=200.0,  # replaced later by caller if needed
        )
    )

    return row


def extract_rows(
    runs_root: Path,
    window_sec: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    index_map = load_index_map(runs_root)
    uuid_map = current_uuid_map_by_index()

    rows_1gpu: list[dict[str, Any]] = []
    rows_2gpu: list[dict[str, Any]] = []

    for run_dir in discover_run_dirs(runs_root):
        meta = read_json(run_dir / "meta.json")
        visible_devices = parse_visible_devices(meta)
        target_uuids = resolve_target_uuids(meta, uuid_map)

        stdout_text = read_text(run_dir / "stdout.log")
        time_json = read_json(run_dir / "time.json")
        exitcode_text = read_text(run_dir / "exitcode.txt").strip()
        times = extract_times_from_stdout(stdout_text)
        faketensor_est = extract_faketensor_value(run_dir, stdout_text)

        row: dict[str, Any] = {
            "workload_id": meta.get("workload_id"),
            "run_id": meta.get("run_id"),
            "spec_path": meta.get("spec_path"),
            "run_dir": str(run_dir),
            "gpu_count": len(visible_devices) if visible_devices else None,
            "cuda_visible_devices": meta.get("cuda_visible_devices"),
            "assigned_gpu_a_index": visible_devices[0] if len(visible_devices) >= 1 else None,
            "assigned_gpu_b_index": visible_devices[1] if len(visible_devices) >= 2 else None,
            "assigned_gpu_a_uuid": target_uuids[0] if len(target_uuids) >= 1 else None,
            "assigned_gpu_b_uuid": target_uuids[1] if len(target_uuids) >= 2 else None,
            "elapsed_seconds_index": safe_float(index_map.get(str(run_dir), {}).get("elapsed_seconds")),
            "elapsed_seconds_time_json": safe_float(time_json.get("elapsed_seconds")),
            "training_loop_time_s": times.get("training_loop_time_s"),
            "end_to_end_time_s": times.get("end_to_end_time_s"),
            "exit_code": safe_int(exitcode_text) if exitcode_text else safe_int(time_json.get("exit_code")),
            "gpu_memory_requirement_mib": meta.get("resources", {}).get("gpu_memory_requirement_mib"),
            "faketensor_estimate": faketensor_est,
            "summary_exists": (run_dir / "artifacts" / "summary" / "summary.txt").exists(),
            "summary_path": str(run_dir / "artifacts" / "summary" / "summary.txt"),
            "faketensor_path": str(run_dir / "artifacts" / "faketensor" / "faketensor.txt"),
        }

        row.update(
            summarize_nvidia_memory(
                run_dir / "nvidia_smi.csv",
                target_uuids_in_order=target_uuids,
                window_sec=window_sec,
            )
        )
        row.update(
            summarize_dcgm(
                run_dir / "dcgm.log",
                target_gpu_indices_in_order=visible_devices,
                window_sec=window_sec,
            )
        )

        if len(visible_devices) == 2:
            rows_2gpu.append(row)
        else:
            rows_1gpu.append(row)

    return rows_1gpu, rows_2gpu


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        pd.DataFrame().to_csv(path, index=False)
        return

    # Stable column order: union of all keys, sorted after a preferred prefix
    preferred = [
        "workload_id",
        "run_id",
        "spec_path",
        "run_dir",
        "gpu_count",
        "cuda_visible_devices",
        "assigned_gpu_a_index",
        "assigned_gpu_b_index",
        "assigned_gpu_a_uuid",
        "assigned_gpu_b_uuid",
        "elapsed_seconds_index",
        "elapsed_seconds_time_json",
        "training_loop_time_s",
        "end_to_end_time_s",
        "exit_code",
        "gpu_memory_requirement_mib",
        "faketensor_estimate",
        "summary_exists",
        "summary_path",
        "faketensor_path",
    ]

    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())

    rest = sorted(k for k in all_keys if k not in preferred)
    cols = preferred + rest

    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols]
    df.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    runs_root = Path(args.runs_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows_1gpu, rows_2gpu = extract_rows(runs_root, args.window_sec)

    out_1 = output_dir / "solo_profile_results_1gpu.csv"
    out_2 = output_dir / "solo_profile_results_2gpu.csv"

    write_csv(out_1, rows_1gpu)
    write_csv(out_2, rows_2gpu)

    print(f"wrote {len(rows_1gpu)} rows to {out_1}")
    print(f"wrote {len(rows_2gpu)} rows to {out_2}")


if __name__ == "__main__":
    main()