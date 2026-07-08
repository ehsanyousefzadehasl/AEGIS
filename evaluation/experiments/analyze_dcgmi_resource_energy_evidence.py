#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


RAW_TO_DISPLAY = {
    "EST-MAGM__horus": "AEGIS+HorusMem",
    "HORUS__horus": "Horus",
    "LUCID": "Lucid",
    "OR-MAGM": "AEGIS-EstimatorFree",
    "exclusive": "Exclusive",
    "oracle-MAGM": "AEGIS+PeakMem",
    "aegis_magm_thresholded": "AEGIS-MAGM",
    "aegis_lug_thresholded": "AEGIS-LUG",
    "aegis_magm_no_thresholds": "MAGM no thresholds",
    "aegis_lug_no_thresholds": "LUG no thresholds",
}

DISPLAY_ORDER = [
    "Exclusive",
    "AEGIS-MAGM",
    "AEGIS-LUG",
    "MAGM no thresholds",
    "LUG no thresholds",
    "Horus",
    "Lucid",
    "AEGIS+HorusMem",
    "AEGIS+PeakMem",
    "AEGIS-EstimatorFree",
]

PAPER_POLICIES_FOR_TIMELINE = [
    "Exclusive",
    "AEGIS-MAGM",
    "AEGIS-LUG",
    "MAGM no thresholds",
    "LUG no thresholds",
    "AEGIS-EstimatorFree",
]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def policy_name(raw: str) -> str:
    return RAW_TO_DISPLAY.get(str(raw), str(raw))


def order_key(policy: str) -> tuple[int, str]:
    try:
        return (DISPLAY_ORDER.index(policy), policy)
    except ValueError:
        return (len(DISPLAY_ORDER), policy)


def load_run_keys(analysis_dir: Path) -> pd.DataFrame:
    rows = []
    for p in sorted((analysis_dir / "traces").glob("*/normalized_jct_values.csv")):
        trace = p.parent.name
        df = pd.read_csv(p)
        for row in df[["experiment_name", "run_label"]].drop_duplicates().itertuples(index=False):
            raw = str(row.run_label)
            rows.append({
                "trace": trace,
                "experiment_name": str(row.experiment_name),
                "raw_label": raw,
                "policy": policy_name(raw),
            })
    out = pd.DataFrame(rows).drop_duplicates()
    if out.empty:
        return out
    return out.sort_values(
        ["trace", "policy"],
        key=lambda s: s.map(lambda x: order_key(str(x))[0]) if s.name == "policy" else s,
    )


def find_dcgmi_csv(results_root: Path, experiment_name: str, raw_label: str) -> Path | None:
    candidates = sorted(results_root.rglob("runtime/telemetry/dcgmi_metrics.csv"))
    scored = []

    for p in candidates:
        s = str(p)
        score = 0
        if experiment_name in s:
            score += 100
        if f"/{raw_label}/" in s or f"\\{raw_label}\\" in s:
            score += 50
        if raw_label.lower() in s.lower():
            score += 20
        if "final_representative" in s:
            score += 5
        if score > 0:
            scored.append((score, len(s), p))

    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][2]


def event_times_from_json(obj: Any) -> list[float]:
    times = []

    def visit(x: Any, key: str = "") -> None:
        key_n = norm(key)
        if isinstance(x, dict):
            for k, v in x.items():
                visit(v, k)
        elif isinstance(x, list):
            for v in x:
                visit(v, key)
        elif isinstance(x, (int, float)):
            if any(t in key_n for t in ["wall", "time", "timestamp"]):
                v = float(x)
                if math.isfinite(v) and v > 0:
                    times.append(v)
        elif isinstance(x, str):
            if any(t in key_n for t in ["wall", "time", "timestamp", "date"]):
                dt = pd.to_datetime(pd.Series([x]), errors="coerce", utc=True)
                if dt.notna().iloc[0]:
                    times.append(float(dt.astype("int64").iloc[0]) / 1e9)
                else:
                    try:
                        v = float(x)
                        if math.isfinite(v) and v > 0:
                            times.append(v)
                    except Exception:
                        pass

    visit(obj)
    return times


def infer_event_window(run_dir: Path) -> tuple[float | None, float | None, str]:
    times = []

    for path in list(run_dir.rglob("*.jsonl")) + list(run_dir.rglob("events*.json")):
        if "runtime" not in str(path) and "event" not in norm(path.name):
            continue

        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue

        records = []
        if path.suffix == ".jsonl":
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        else:
            try:
                obj = json.loads(text)
                records = obj if isinstance(obj, list) else [obj]
            except Exception:
                pass

        for record in records:
            times.extend(event_times_from_json(record))

    unix_like = [t for t in times if t > 1_000_000_000]
    if unix_like:
        times = unix_like

    if not times:
        return None, None, "dcgmi_span"

    return min(times), max(times), "runtime_events"


def prepare_dcgmi(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    required = [
        "sample_wall_time",
        "gpu_uuid",
        "gpu_id",
        "free_gpu_memory",
        "gpu_utilization",
        "smact",
        "smocc",
        "drama",
        "power",
        "energy",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing required DCGMI columns: {missing}")

    df = df.copy()

    # Parse wall-clock timestamps robustly. Invalid parses become NaT; we drop
    # them before converting to seconds so pandas' internal NaT sentinel does
    # not appear as -9223372036 seconds.
    df["sample_wall_time_dt"] = pd.to_datetime(
        df["sample_wall_time"],
        errors="coerce",
        utc=True,
        format="mixed",
    )
    bad_time_rows = int(df["sample_wall_time_dt"].isna().sum())
    if bad_time_rows:
        print(f"[WARN] {path}: dropping {bad_time_rows} rows with invalid sample_wall_time")
    df = df.dropna(subset=["sample_wall_time_dt"]).copy()

    if df.empty:
        raise ValueError(f"{path}: no valid sample_wall_time rows after parsing")

    df["sample_wall_time_s"] = df["sample_wall_time_dt"].map(lambda x: x.timestamp())

    numeric_cols = [
        "free_gpu_memory",
        "gpu_utilization",
        "gract",
        "smact",
        "smocc",
        "drama",
        "memory_copy",
        "power",
        "energy",
        "gpu_id",
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # The file reports free memory in MiB. Convert to used memory by subtracting
    # from each GPU's maximum observed free memory in the run. This avoids
    # hardcoding 40 GiB and accounts for driver-reserved memory.
    free_baseline = df.groupby("gpu_uuid")["free_gpu_memory"].transform("max")
    df["used_gpu_memory_mib"] = free_baseline - df["free_gpu_memory"]
    df["used_gpu_memory_gb"] = df["used_gpu_memory_mib"] / 1024.0

    # Safety: tiny negative values can appear from noisy counters.
    df.loc[df["used_gpu_memory_gb"] < 0, "used_gpu_memory_gb"] = 0.0

    # Pressure metrics are already fractions in your sample: 0.173, 0.069, etc.
    # If a future file stores percentages, normalize them.
    for c in ["smact", "smocc", "drama", "gract"]:
        if c in df.columns:
            q95 = df[c].dropna().quantile(0.95)
            if pd.notna(q95) and q95 > 1.5:
                df[c] = df[c] / 100.0

    return df


def restrict_window(df: pd.DataFrame, start: float | None, end: float | None) -> tuple[pd.DataFrame, float, float, str]:
    if start is not None and end is not None:
        mask = (df["sample_wall_time_s"] >= start) & (df["sample_wall_time_s"] <= end)
        if mask.sum() > 10:
            return df.loc[mask].copy(), start, end, "runtime_events"

    start2 = float(df["sample_wall_time_s"].min())
    end2 = float(df["sample_wall_time_s"].max())
    return df.copy(), start2, end2, "dcgmi_span"


def format_unix_time(ts: float | None) -> str:
    if ts is None or pd.isna(ts) or not math.isfinite(float(ts)):
        return ""
    if float(ts) < 1_000_000_000:
        return str(ts)
    return pd.to_datetime(float(ts), unit="s", utc=True).isoformat()


def active_mask(df: pd.DataFrame) -> pd.Series:
    # A GPU sample is active if it shows non-idle training/resource activity.
    return (
        (df["used_gpu_memory_gb"].fillna(0) > 0.5)
        | (df["gpu_utilization"].fillna(0) > 0)
        | (df["smact"].fillna(0) > 0.02)
        | (df["smocc"].fillna(0) > 0.02)
        | (df["drama"].fillna(0) > 0.005)
        | (df["power"].fillna(0) > 80)
    )


def energy_by_gpu(dfw: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for gpu_uuid, part in dfw.groupby("gpu_uuid"):
        part = part.sort_values("sample_wall_time_s")
        energy = pd.to_numeric(part["energy"], errors="coerce")
        part = part.loc[energy.notna()].copy()
        part["energy"] = energy[energy.notna()]

        if len(part) < 2:
            continue

        first = part.iloc[0]
        last = part.iloc[-1]
        delta_mj = float(last["energy"]) - float(first["energy"])
        if delta_mj < 0:
            continue

        rows.append({
            "gpu_uuid": gpu_uuid,
            "gpu_id": first.get("gpu_id", ""),
            "start_time": first["sample_wall_time"],
            "end_time": last["sample_wall_time"],
            "energy_start_mj": float(first["energy"]),
            "energy_end_mj": float(last["energy"]),
            "energy_delta_mj": delta_mj,
            "energy_delta_j": delta_mj / 1000.0,
        })

    return pd.DataFrame(rows)


def summarize_one(trace: str, policy: str, raw_label: str, experiment_name: str, dcgmi_csv: Path) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    df = prepare_dcgmi(dcgmi_csv)
    run_dir = dcgmi_csv.parents[2]
    event_start, event_end, _ = infer_event_window(run_dir)
    dfw, start, end, window_source = restrict_window(df, event_start, event_end)

    active = dfw.loc[active_mask(dfw)].copy()
    energy_gpu = energy_by_gpu(dfw)
    total_energy_j = float(energy_gpu["energy_delta_j"].sum()) if not energy_gpu.empty else np.nan

    def mean_or_nan(frame: pd.DataFrame, col: str) -> float:
        if frame.empty or col not in frame:
            return np.nan
        v = pd.to_numeric(frame[col], errors="coerce").dropna()
        return float(v.mean()) if not v.empty else np.nan

    def p95_or_nan(frame: pd.DataFrame, col: str) -> float:
        if frame.empty or col not in frame:
            return np.nan
        v = pd.to_numeric(frame[col], errors="coerce").dropna()
        return float(v.quantile(0.95)) if not v.empty else np.nan

    def max_or_nan(frame: pd.DataFrame, col: str) -> float:
        if frame.empty or col not in frame:
            return np.nan
        v = pd.to_numeric(frame[col], errors="coerce").dropna()
        return float(v.max()) if not v.empty else np.nan

    # Active GPU-seconds: approximate by number of active samples. Since the
    # sampling interval is consistent, normalized comparisons are still useful.
    active_fraction = len(active) / len(dfw) if len(dfw) else np.nan

    summary = {
        "trace": trace,
        "policy": policy,
        "raw_label": raw_label,
        "experiment_name": experiment_name,
        "dcgmi_csv": str(dcgmi_csv),
        "window_source": window_source,
        "window_start_wall": format_unix_time(start),
        "window_end_wall": format_unix_time(end),
        "window_duration_s": end - start,
        "rows_in_window": len(dfw),
        "active_rows": len(active),
        "active_row_fraction": active_fraction,

        # Full trace-window averages: include idle samples.
        "used_gpu_memory_trace_mean_gb": mean_or_nan(dfw, "used_gpu_memory_gb"),
        "used_gpu_memory_trace_p95_gb": p95_or_nan(dfw, "used_gpu_memory_gb"),
        "gpu_utilization_trace_mean_pct": mean_or_nan(dfw, "gpu_utilization"),
        "smact_trace_mean": mean_or_nan(dfw, "smact"),
        "smocc_trace_mean": mean_or_nan(dfw, "smocc"),
        "drama_trace_mean": mean_or_nan(dfw, "drama"),
        "power_trace_mean_w": mean_or_nan(dfw, "power"),

        # Active-sample averages: better for explaining pressure while GPUs work.
        "used_gpu_memory_active_mean_gb": mean_or_nan(active, "used_gpu_memory_gb"),
        "used_gpu_memory_active_p95_gb": p95_or_nan(active, "used_gpu_memory_gb"),
        "used_gpu_memory_active_max_gb": max_or_nan(active, "used_gpu_memory_gb"),
        "gpu_utilization_active_mean_pct": mean_or_nan(active, "gpu_utilization"),
        "smact_active_mean": mean_or_nan(active, "smact"),
        "smocc_active_mean": mean_or_nan(active, "smocc"),
        "drama_active_mean": mean_or_nan(active, "drama"),
        "power_active_mean_w": mean_or_nan(active, "power"),

        # Energy-to-solution.
        "total_gpu_energy_j": total_energy_j,
        "energy_gpu_count": int(energy_gpu["gpu_uuid"].nunique()) if not energy_gpu.empty else 0,
    }

    energy_gpu.insert(0, "trace", trace)
    energy_gpu.insert(1, "policy", policy)
    energy_gpu.insert(2, "raw_label", raw_label)
    energy_gpu.insert(3, "experiment_name", experiment_name)

    # Downsample for plotting to keep figures light.
    timeline = dfw[[
        "sample_wall_time_s",
        "sample_wall_time",
        "gpu_id",
        "gpu_uuid",
        "used_gpu_memory_gb",
        "gpu_utilization",
        "smact",
        "smocc",
        "drama",
        "power",
    ]].copy()
    timeline["trace"] = trace
    timeline["policy"] = policy
    timeline["raw_label"] = raw_label
    timeline["time_from_start_min"] = (timeline["sample_wall_time_s"] - start) / 60.0

    return summary, energy_gpu, timeline


def normalize_to_exclusive(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    metrics = [
        "used_gpu_memory_active_mean_gb",
        "used_gpu_memory_active_p95_gb",
        "gpu_utilization_active_mean_pct",
        "smact_active_mean",
        "smocc_active_mean",
        "drama_active_mean",
        "power_active_mean_w",
        "total_gpu_energy_j",
    ]

    for m in metrics:
        out[f"{m}_vs_exclusive"] = np.nan

    for trace, part in out.groupby("trace"):
        base = part[part["policy"] == "Exclusive"]
        if base.empty:
            continue
        base = base.iloc[0]
        idx = out["trace"] == trace
        for m in metrics:
            b = base.get(m, np.nan)
            if pd.notna(b) and float(b) > 0:
                out.loc[idx, f"{m}_vs_exclusive"] = out.loc[idx, m] / float(b)

    return out


def plot_bars(summary: pd.DataFrame, metric: str, ylabel: str, output: Path, *, baseline_line: bool = False) -> None:
    traces = ["philly", "saturn", "venus"]
    policies = [p for p in DISPLAY_ORDER if p in set(summary["policy"])]

    x = np.arange(len(traces))
    width = min(0.12, 0.75 / max(len(policies), 1))

    fig, ax = plt.subplots(figsize=(12.5, 4.4))

    for i, policy in enumerate(policies):
        vals = []
        for trace in traces:
            part = summary[(summary["trace"] == trace) & (summary["policy"] == policy)]
            vals.append(float(part[metric].iloc[0]) if not part.empty and pd.notna(part[metric].iloc[0]) else np.nan)
        ax.bar(x + (i - (len(policies) - 1) / 2) * width, vals, width, label=policy)

    if baseline_line:
        ax.axhline(1.0, linestyle="--", linewidth=1.2)

    ax.set_xticks(x)
    ax.set_xticklabels([t.capitalize() for t in traces])
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.7)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.28), frameon=True)
    fig.tight_layout()

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output.with_suffix(".png"), bbox_inches="tight", dpi=300)
    plt.close(fig)


def plot_memory_timeline(timeline: pd.DataFrame, trace: str, output: Path) -> None:
    subset = timeline[
        (timeline["trace"] == trace)
        & (timeline["policy"].isin(PAPER_POLICIES_FOR_TIMELINE))
    ].copy()

    if subset.empty:
        return

    policies = [p for p in PAPER_POLICIES_FOR_TIMELINE if p in set(subset["policy"])]
    gpu_ids = sorted(subset["gpu_id"].dropna().unique())

    fig, axes = plt.subplots(
        len(policies),
        1,
        figsize=(12.8, 3.2 * len(policies)),
        sharex=False,
        sharey=True,
    )
    if len(policies) == 1:
        axes = [axes]

    for ax, policy in zip(axes, policies):
        part = subset[subset["policy"] == policy]
        for gpu_id in gpu_ids:
            g = part[part["gpu_id"] == gpu_id].sort_values("time_from_start_min")
            if g.empty:
                continue
            ax.plot(
                g["time_from_start_min"],
                g["used_gpu_memory_gb"],
                linewidth=1.8,
                label=f"GPU {int(gpu_id)}",
            )

        ax.set_title(f"{trace.capitalize()} — {policy}", fontsize=14)
        ax.set_ylabel("Used GPU memory (GiB)")
        ax.grid(True, linestyle=":", linewidth=0.7)
        ax.legend(ncol=min(3, len(gpu_ids)), loc="upper right", frameon=True)

    axes[-1].set_xlabel("Time from trace start (min)")

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output.with_suffix(".png"), bbox_inches="tight", dpi=300)
    plt.close(fig)


def fmt_pct_change(ratio: float | None, *, lower_is_better: bool = False) -> str:
    if ratio is None or pd.isna(ratio) or not math.isfinite(float(ratio)):
        return "n/a"
    ratio = float(ratio)
    change = (ratio - 1.0) * 100.0
    if lower_is_better:
        if change < 0:
            return f"{abs(change):.1f}% lower"
        if change > 0:
            return f"{change:.1f}% higher"
        return "unchanged"
    else:
        if change > 0:
            return f"{change:.1f}% higher"
        if change < 0:
            return f"{abs(change):.1f}% lower"
        return "unchanged"


def geomean_ratio(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna()
    x = x[x > 0]
    if x.empty:
        return np.nan
    return float(np.exp(np.log(x).mean()))


def takeaway_lines(summary: pd.DataFrame) -> list[str]:
    lines = []

    focus = "AEGIS-EstimatorFree"
    aegis = summary[summary["policy"] == focus].copy()
    if aegis.empty:
        return [f"- No `{focus}` rows found, so no focused takeaway could be computed."]

    energy_gm = geomean_ratio(aegis["total_gpu_energy_j_vs_exclusive"])
    mem_mean_gm = geomean_ratio(aegis["used_gpu_memory_active_mean_gb_vs_exclusive"])
    mem_p95_gm = geomean_ratio(aegis["used_gpu_memory_active_p95_gb_vs_exclusive"])
    util_gm = geomean_ratio(aegis["gpu_utilization_active_mean_pct_vs_exclusive"])
    smact_gm = geomean_ratio(aegis["smact_active_mean_vs_exclusive"])
    smocc_gm = geomean_ratio(aegis["smocc_active_mean_vs_exclusive"])
    drama_gm = geomean_ratio(aegis["drama_active_mean_vs_exclusive"])
    power_gm = geomean_ratio(aegis["power_active_mean_w_vs_exclusive"])

    lines.append(f"- Across traces, `{focus}` changes GPU energy-to-solution by **{fmt_pct_change(energy_gm, lower_is_better=True)}** relative to Exclusive on a geomean basis.")
    lines.append(f"- Active used GPU memory mean is **{fmt_pct_change(mem_mean_gm)}** than Exclusive on a geomean basis; active used memory p95 is **{fmt_pct_change(mem_p95_gm)}**.")
    lines.append(f"- Active GPU utilization is **{fmt_pct_change(util_gm)}** than Exclusive on a geomean basis.")
    lines.append(f"- Active pressure indicators increase by **{fmt_pct_change(smact_gm)}** for SMACT, **{fmt_pct_change(smocc_gm)}** for SMOCC, and **{fmt_pct_change(drama_gm)}** for DRAMA on a geomean basis.")
    lines.append(f"- Active power is **{fmt_pct_change(power_gm)}** than Exclusive on a geomean basis; this is why energy-to-solution is more informative than average power alone.")

    lines.append("")
    lines.append("Per-trace AEGIS-EstimatorFree vs Exclusive:")
    for row in aegis.sort_values("trace").itertuples(index=False):
        energy = getattr(row, "total_gpu_energy_j_vs_exclusive", np.nan)
        mem = getattr(row, "used_gpu_memory_active_mean_gb_vs_exclusive", np.nan)
        util = getattr(row, "gpu_utilization_active_mean_pct_vs_exclusive", np.nan)
        smact = getattr(row, "smact_active_mean_vs_exclusive", np.nan)
        trace = getattr(row, "trace")
        lines.append(
            f"- `{trace}`: energy-to-solution {fmt_pct_change(energy, lower_is_better=True)}, "
            f"active memory mean {fmt_pct_change(mem)}, "
            f"active GPU utilization {fmt_pct_change(util)}, "
            f"active SMACT {fmt_pct_change(smact)}."
        )

    return lines


def figure_links(output_dir: Path) -> list[str]:
    fig_dir = output_dir / "figures"
    if not fig_dir.exists():
        return []

    preferred = [
        "normalized_energy_to_solution.png",
        "normalized_active_memory_mean.png",
        "active_memory_mean_gb.png",
        "active_memory_p95_gb.png",
        "active_smact_mean.png",
        "active_smocc_mean.png",
        "active_drama_mean.png",
        "memory_timeline_exclusive_vs_aegis_philly.png",
        "memory_timeline_exclusive_vs_aegis_saturn.png",
        "memory_timeline_exclusive_vs_aegis_venus.png",
    ]

    existing = []
    for name in preferred:
        p = fig_dir / name
        if p.exists():
            existing.append(p)

    # Include any extra PNGs not listed above.
    seen = {p.name for p in existing}
    for p in sorted(fig_dir.glob("*.png")):
        if p.name not in seen:
            existing.append(p)

    lines = []
    for p in existing:
        rel = p.relative_to(output_dir)
        title = p.stem.replace("_", " ")
        lines.append(f"### {title}\n\n![{title}]({rel.as_posix()})\n")
    return lines


def write_md(summary: pd.DataFrame, output: Path) -> None:
    output_dir = output.parent

    cols = [
        "trace",
        "policy",
        "active_row_fraction",
        "used_gpu_memory_trace_mean_gb",
        "used_gpu_memory_active_mean_gb",
        "used_gpu_memory_active_p95_gb",
        "gpu_utilization_active_mean_pct",
        "smact_active_mean",
        "smocc_active_mean",
        "drama_active_mean",
        "power_active_mean_w",
        "total_gpu_energy_j",
        "total_gpu_energy_j_vs_exclusive",
        "window_source",
    ]
    table = summary[[c for c in cols if c in summary.columns]].copy()

    for c in table.columns:
        if pd.api.types.is_numeric_dtype(table[c]):
            table[c] = table[c].map(lambda v: "" if pd.isna(v) else f"{v:.4g}")

    norm_cols = [
        "trace",
        "policy",
        "used_gpu_memory_active_mean_gb_vs_exclusive",
        "used_gpu_memory_active_p95_gb_vs_exclusive",
        "gpu_utilization_active_mean_pct_vs_exclusive",
        "smact_active_mean_vs_exclusive",
        "smocc_active_mean_vs_exclusive",
        "drama_active_mean_vs_exclusive",
        "power_active_mean_w_vs_exclusive",
        "total_gpu_energy_j_vs_exclusive",
    ]
    norm_table = summary[[c for c in norm_cols if c in summary.columns]].copy()
    for c in norm_table.columns:
        if pd.api.types.is_numeric_dtype(norm_table[c]):
            norm_table[c] = norm_table[c].map(lambda v: "" if pd.isna(v) else f"{v:.4g}")

    text = []
    text.append("# DCGMI resource and energy evidence\n")
    text.append("This report is secondary evidence and is not part of the main performance pipeline.\n")

    text.append("## Method\n")
    text.append("Important correction: `dcgmi_metrics.csv` reports `free_gpu_memory`, so used memory is computed as:\n")
    text.append("```text")
    text.append("used_gpu_memory_gb = (max_free_gpu_memory_for_that_gpu - free_gpu_memory) / 1024")
    text.append("```\n")
    text.append("The trace-window memory mean includes idle samples. The active memory mean/p95 only includes samples where the GPU appears active.\n")
    text.append("Energy is computed from the cumulative `energy` counter:\n")
    text.append("```text")
    text.append("energy_delta_j = (energy_last - energy_first) / 1000")
    text.append("total_gpu_energy_j = sum energy_delta_j over GPUs")
    text.append("```\n")

    text.append("## Numeric takeaway\n")
    text.extend(takeaway_lines(summary))
    text.append("")

    text.append("## Absolute summary\n")
    text.append(table.to_markdown(index=False))
    text.append("")

    text.append("## Normalized to Exclusive\n")
    text.append("Values above 1 mean higher than Exclusive. For energy-to-solution, lower than 1 is better; for utilization/activity metrics, higher than 1 means more active GPU usage.\n")
    text.append(norm_table.to_markdown(index=False))
    text.append("")

    text.append("## Figures\n")
    figs = figure_links(output_dir)
    if figs:
        text.extend(figs)
    else:
        text.append("_No figures found. Run the script again to generate figures._\n")

    output.write_text("\n".join(text))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", type=Path, default=Path("evaluation/experiments/results/final_representative_evaluation_analysis"))
    parser.add_argument("--results-root", type=Path, default=Path("evaluation/experiments/results"))
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/experiments/results/final_representative_evaluation_analysis/dcgmi_resource_energy_evidence"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    keys = load_run_keys(args.analysis_dir)
    summaries = []
    energy_frames = []
    timeline_frames = []
    missing = []

    for row in keys.itertuples(index=False):
        dcgmi = find_dcgmi_csv(args.results_root, row.experiment_name, row.raw_label)
        if dcgmi is None:
            missing.append(row._asdict())
            print(f"[WARN] missing dcgmi_metrics.csv for {row.trace} {row.policy}")
            continue

        print(f"[INFO] {row.trace} / {row.policy}: {dcgmi}")
        summary, energy_gpu, timeline = summarize_one(
            row.trace,
            row.policy,
            row.raw_label,
            row.experiment_name,
            dcgmi,
        )
        summaries.append(summary)
        energy_frames.append(energy_gpu)
        timeline_frames.append(timeline)

    summary = pd.DataFrame(summaries)
    if not summary.empty:
        summary = normalize_to_exclusive(summary)
        summary = summary.sort_values(
            ["trace", "policy"],
            key=lambda s: s.map(lambda x: order_key(str(x))[0]) if s.name == "policy" else s,
        )

    energy = pd.concat(energy_frames, ignore_index=True) if energy_frames else pd.DataFrame()
    timeline = pd.concat(timeline_frames, ignore_index=True) if timeline_frames else pd.DataFrame()

    summary.to_csv(args.output_dir / "dcgmi_resource_energy_summary.csv", index=False)
    energy.to_csv(args.output_dir / "dcgmi_energy_by_gpu.csv", index=False)
    timeline.to_csv(args.output_dir / "dcgmi_timeline_samples.csv", index=False)
    pd.DataFrame(missing).to_csv(args.output_dir / "missing_dcgmi_runs.csv", index=False)

    if not summary.empty:
        plot_bars(
            summary,
            "total_gpu_energy_j_vs_exclusive",
            "Energy-to-solution / Exclusive",
            args.output_dir / "figures" / "normalized_energy_to_solution",
            baseline_line=True,
        )
        plot_bars(
            summary,
            "used_gpu_memory_active_mean_gb_vs_exclusive",
            "Active used GPU memory / Exclusive",
            args.output_dir / "figures" / "normalized_active_memory_mean",
            baseline_line=True,
        )

        plot_bars(
            summary,
            "smact_active_mean_vs_exclusive",
            "Active SMACT / Exclusive",
            args.output_dir / "figures" / "normalized_active_smact",
            baseline_line=True,
        )
        plot_bars(
            summary,
            "smocc_active_mean_vs_exclusive",
            "Active SMOCC / Exclusive",
            args.output_dir / "figures" / "normalized_active_smocc",
            baseline_line=True,
        )
        plot_bars(
            summary,
            "drama_active_mean_vs_exclusive",
            "Active DRAMA / Exclusive",
            args.output_dir / "figures" / "normalized_active_drama",
            baseline_line=True,
        )
        plot_bars(
            summary,
            "used_gpu_memory_active_mean_gb",
            "Active used GPU memory mean (GiB)",
            args.output_dir / "figures" / "active_memory_mean_gb",
        )
        plot_bars(
            summary,
            "used_gpu_memory_active_p95_gb",
            "Active used GPU memory p95 (GiB)",
            args.output_dir / "figures" / "active_memory_p95_gb",
        )
        plot_bars(
            summary,
            "smact_active_mean",
            "Active SMACT mean",
            args.output_dir / "figures" / "active_smact_mean",
        )
        plot_bars(
            summary,
            "smocc_active_mean",
            "Active SMOCC mean",
            args.output_dir / "figures" / "active_smocc_mean",
        )
        plot_bars(
            summary,
            "drama_active_mean",
            "Active DRAMA mean",
            args.output_dir / "figures" / "active_drama_mean",
        )

        if not timeline.empty:
            for trace in sorted(timeline["trace"].unique()):
                plot_memory_timeline(
                    timeline,
                    trace,
                    args.output_dir / "figures" / f"memory_timeline_exclusive_vs_aegis_{trace}",
                )

        write_md(summary, args.output_dir / "dcgmi_resource_energy_summary.md")

    print(f"[DONE] wrote outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
