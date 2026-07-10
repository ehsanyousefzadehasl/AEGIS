from __future__ import annotations

from pathlib import Path
import math
import shutil

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SOURCE_DIR = Path("evaluation/experiments/results/legacy_zeus_multitrace_memory_vs_fixed_smi_analysis")
OUT_DIR = Path("evaluation/experiments/results/legacy_zeus_multitrace_memory_vs_fixed_smi_analysis_polished")
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "cross_trace_tables"

POLICY_ORDER = [
    "exclusive",
    "memory_only_interference",
    "fixed_smi80",
    "fixed_smi70",
    "fixed_smi60",
    "fixed_smi50",
    "horus_baseline",
    "lucid_baseline",
]

POLICY_DISPLAY = {
    "exclusive": "Exclusive",
    "memory_only_interference": "Memory-only",
    "fixed_smi80": "AEGIS-SMI80",
    "fixed_smi70": "AEGIS-SMI70",
    "fixed_smi60": "AEGIS-SMI60",
    "fixed_smi50": "AEGIS-SMI50",
    "horus_baseline": "Horus",
    "lucid_baseline": "Lucid",
}

TRACE_DISPLAY = {
    "philly_legacy": "Philly-legacy",
    "saturn_legacy": "Saturn-legacy",
    "venus_gapfix600": "Venus-gapfix600",
}

TRACE_ORDER = [
    "philly_legacy",
    "saturn_legacy",
    "venus_gapfix600",
]


def ensure_dirs() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame | None]:
    runs = pd.read_csv(SOURCE_DIR / "all_run_summaries.csv")

    # The legacy combined analyzer may not emit all_job_metrics.csv.
    # Reconstruct job metrics from every wrapper-level analysis/job_metrics.csv.
    jobs_path = SOURCE_DIR / "all_job_metrics.csv"
    if jobs_path.exists():
        jobs = pd.read_csv(jobs_path)
        return runs, jobs

    results_root = SOURCE_DIR.parent
    experiment_prefix = "legacy_zeus_multitrace_memory_vs_fixed_smi"
    job_frames = []

    for job_path in sorted(results_root.glob(f"{experiment_prefix}__*__rep01__*/analysis/job_metrics.csv")):
        wrapper = job_path.parents[1]
        wrapper_name = wrapper.name

        if "__rep01__" not in wrapper_name:
            print("skipping unexpected wrapper name:", wrapper_name)
            continue

        prefix, configuration_label = wrapper_name.split("__rep01__", 1)
        configuration_label = configuration_label.strip("_")

        # prefix looks like:
        # legacy_zeus_multitrace_memory_vs_fixed_smi__venus_gapfix600
        trace_name = prefix.replace(f"{experiment_prefix}__", "")

        frame = pd.read_csv(job_path)

        # Preserve existing columns where present, otherwise inject metadata.
        frame["trace_name"] = frame.get("trace_name", trace_name)
        frame["configuration_label"] = frame.get("configuration_label", configuration_label)
        frame["experiment_name"] = frame.get("experiment_name", experiment_prefix)
        frame["run_dir"] = frame.get("run_dir", str(wrapper))
        frame["job_metrics_path"] = str(job_path)

        # Align with run summary metadata when possible.
        hit = runs[
            runs["trace_name"].astype(str).eq(str(trace_name))
            & runs["configuration_label"].astype(str).eq(str(configuration_label))
        ]
        if not hit.empty:
            row = hit.iloc[0]
            for col in ["repetition", "run_label", "policy", "estimator"]:
                frame[col] = row.get(col)

        job_frames.append(frame)

    if not job_frames:
        print("could not reconstruct job metrics; no wrapper analysis/job_metrics.csv files found")
        return runs, None

    jobs = pd.concat(job_frames, ignore_index=True, sort=False)
    print("reconstructed job metrics:", len(jobs), "rows from", len(job_frames), "files")
    return runs, jobs


def add_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["policy_key"] = out["configuration_label"].astype(str)
    out["policy_display"] = out["policy_key"].map(POLICY_DISPLAY).fillna(out["policy_key"])
    out["policy_order"] = out["policy_key"].map({p: i for i, p in enumerate(POLICY_ORDER)}).fillna(999)
    out["trace_display"] = out["trace_name"].map(TRACE_DISPLAY).fillna(out["trace_name"])
    out["trace_order"] = out["trace_name"].map({t: i for i, t in enumerate(TRACE_ORDER)}).fillna(999)
    return out


def derive_safe_metric_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Legacy analyzer may only have initial queue wait and execution span.
    # Main-server analyzer later used total queue/execution time.
    # For the legacy postprocessor, use total columns if present; otherwise fall back.
    if "total_queue_wait_mean_s" not in out.columns:
        out["total_queue_wait_mean_s"] = out.get("initial_queue_wait_mean_s", np.nan)
    if "total_queue_wait_p95_s" not in out.columns:
        out["total_queue_wait_p95_s"] = out.get("initial_queue_wait_p95_s", np.nan)

    if "total_execution_time_mean_s" not in out.columns:
        out["total_execution_time_mean_s"] = out.get("execution_span_mean_s", np.nan)
    if "total_execution_time_p95_s" not in out.columns:
        out["total_execution_time_p95_s"] = out.get("execution_span_p95_s", np.nan)

    return out


def normalize_by_exclusive(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    out = df.copy()
    for trace, sub in out.groupby("trace_name"):
        base_rows = sub[sub["policy_key"].eq("exclusive")]
        if base_rows.empty:
            continue
        base = base_rows.iloc[0]
        idx = out["trace_name"].eq(trace)
        for metric in metrics:
            if metric not in out.columns:
                continue
            denom = base.get(metric, np.nan)
            norm_col = f"{metric}_vs_exclusive"
            if pd.notna(denom) and float(denom) != 0.0:
                out.loc[idx, norm_col] = pd.to_numeric(out.loc[idx, metric], errors="coerce") / float(denom)
            else:
                out.loc[idx, norm_col] = np.nan
    return out


def geomean(values: pd.Series) -> float:
    vals = pd.to_numeric(values, errors="coerce")
    vals = vals[(vals > 0) & vals.notna()]
    if vals.empty:
        return float("nan")
    return float(np.exp(np.log(vals).mean()))


def write_cross_trace_table(df: pd.DataFrame, norm_col: str, stem: str) -> pd.DataFrame:
    rows = []
    for policy in POLICY_ORDER:
        sub = df[df["policy_key"].eq(policy)]
        if sub.empty:
            continue
        row = {
            "policy": POLICY_DISPLAY.get(policy, policy),
            "geomean": geomean(sub[norm_col]),
        }
        for trace in TRACE_ORDER:
            hit = sub[sub["trace_name"].eq(trace)]
            row[TRACE_DISPLAY.get(trace, trace)] = float(hit[norm_col].iloc[0]) if not hit.empty else np.nan
        rows.append(row)

    table = pd.DataFrame(rows)
    table.to_csv(TABLE_DIR / f"{stem}.csv", index=False)
    return table


def plot_cross_trace_bars(table: pd.DataFrame, stem: str, title: str, ylabel: str) -> None:
    if table.empty:
        return

    policies = table["policy"].tolist()
    trace_cols = [TRACE_DISPLAY[t] for t in TRACE_ORDER if TRACE_DISPLAY[t] in table.columns]

    value_cols = trace_cols.copy()
    if "geomean" in table.columns:
        table = table.copy()
        table["Geomean"] = pd.to_numeric(table["geomean"], errors="coerce")
        value_cols.append("Geomean")

    x = np.arange(len(policies))
    width = 0.82 / max(1, len(value_cols))

    fig, ax = plt.subplots(figsize=(max(10.0, len(policies) * 0.95), 5.4))

    colors = ["#0072B2", "#E69F00", "#009E73", "#000000"]
    hatches = ["", "//", "\\\\", "xx"]

    for i, col in enumerate(value_cols):
        offset = (i - (len(value_cols) - 1) / 2) * width
        ax.bar(
            x + offset,
            pd.to_numeric(table[col], errors="coerce"),
            width,
            label=col,
            color=colors[i % len(colors)],
            edgecolor="black",
            linewidth=0.8,
            hatch=hatches[i % len(hatches)],
            zorder=2,
        )

    ax.axhline(
        1.0,
        linestyle="--",
        linewidth=1.4,
        color="black",
        label="Exclusive baseline",
        zorder=1,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(policies, rotation=25, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", linestyle=":", linewidth=0.8, alpha=0.7, zorder=0)
    ax.legend(ncol=3, frameon=False)
    fig.tight_layout()

    fig.savefig(FIG_DIR / f"{stem}.png", dpi=220)
    fig.savefig(FIG_DIR / f"{stem}.pdf")
    plt.close(fig)

def plot_mean_p95_markers(df: pd.DataFrame, mean_norm: str, p95_norm: str, stem: str, title: str, ylabel: str) -> None:
    rows = []
    for policy in POLICY_ORDER:
        sub = df[df["policy_key"].eq(policy)]
        if sub.empty:
            continue
        rows.append({
            "policy": POLICY_DISPLAY.get(policy, policy),
            "mean_geomean": geomean(sub[mean_norm]),
            "p95_geomean": geomean(sub[p95_norm]),
        })

    table = pd.DataFrame(rows)
    table.to_csv(TABLE_DIR / f"{stem}.csv", index=False)
    if table.empty:
        return

    x = np.arange(len(table))
    fig, ax = plt.subplots(figsize=(max(8.5, len(table) * 0.85), 4.8))

    ax.bar(
        x,
        table["mean_geomean"],
        label="Mean",
        color="#0072B2",
        edgecolor="black",
        linewidth=0.8,
    )
    ax.scatter(
        x,
        table["p95_geomean"],
        marker="D",
        s=58,
        color="#D55E00",
        edgecolor="black",
        linewidth=0.7,
        label="P95",
        zorder=3,
    )

    ax.axhline(1.0, linestyle="--", linewidth=1.4, color="black", label="Exclusive baseline")
    ax.set_xticks(x)
    ax.set_xticklabels(table["policy"], rotation=25, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", linestyle=":", linewidth=0.8, alpha=0.7)
    ax.legend(ncol=3, frameon=False)
    fig.tight_layout()

    fig.savefig(FIG_DIR / f"{stem}.png", dpi=220)
    fig.savefig(FIG_DIR / f"{stem}.pdf")
    plt.close(fig)


def plot_queue_execution_tradeoff(df: pd.DataFrame) -> None:
    rows = []
    for policy in POLICY_ORDER:
        if policy == "exclusive":
            continue
        sub = df[df["policy_key"].eq(policy)]
        if sub.empty:
            continue
        rows.append({
            "policy": POLICY_DISPLAY.get(policy, policy),
            "queue": geomean(sub["total_queue_wait_mean_s_vs_exclusive"]),
            "execution": geomean(sub["total_execution_time_mean_s_vs_exclusive"]),
            "jct": geomean(sub["jct_mean_s_vs_exclusive"]),
        })

    table = pd.DataFrame(rows)
    table.to_csv(TABLE_DIR / "normalized_queue_execution_tradeoff.csv", index=False)
    if table.empty:
        return

    fig, ax = plt.subplots(figsize=(6.8, 5.2))

    colors = ["#E69F00", "#0072B2", "#56B4E9", "#009E73", "#D55E00", "#CC79A7", "#999999"]
    for i, row in table.iterrows():
        ax.scatter(
            row["queue"],
            row["execution"],
            s=95,
            color=colors[i % len(colors)],
            edgecolor="black",
            linewidth=0.8,
            label=row["policy"],
        )
        ax.annotate(
            row["policy"],
            (row["queue"], row["execution"]),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=8,
        )

    ax.axvline(1.0, linestyle="--", linewidth=1.2, color="black")
    ax.axhline(1.0, linestyle="--", linewidth=1.2, color="black")
    ax.set_xlabel("Normalized mean queue wait")
    ax.set_ylabel("Normalized mean execution time")
    ax.set_title("Cross-trace queue/execution trade-off")
    ax.grid(linestyle=":", linewidth=0.8, alpha=0.7)
    fig.tight_layout()

    fig.savefig(FIG_DIR / "normalized_queue_execution_tradeoff.png", dpi=220)
    fig.savefig(FIG_DIR / "normalized_queue_execution_tradeoff.pdf")
    plt.close(fig)


def markdown_table(df: pd.DataFrame, float_digits: int = 3) -> str:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].map(lambda x: "" if pd.isna(x) else f"{x:.{float_digits}f}")
    return out.to_markdown(index=False)


def build_geomean_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metric_map = [
        ("makespan_s_vs_exclusive", "makespan"),
        ("jct_mean_s_vs_exclusive", "mean_jct"),
        ("jct_p95_s_vs_exclusive", "p95_jct"),
        ("total_queue_wait_mean_s_vs_exclusive", "mean_queue_wait"),
        ("total_queue_wait_p95_s_vs_exclusive", "p95_queue_wait"),
        ("total_execution_time_mean_s_vs_exclusive", "mean_execution_time"),
        ("total_execution_time_p95_s_vs_exclusive", "p95_execution_time"),
    ]

    for policy in POLICY_ORDER:
        sub = df[df["policy_key"].eq(policy)]
        if sub.empty:
            continue

        row = {
            "policy": POLICY_DISPLAY.get(policy, policy),
        }
        for source_col, out_col in metric_map:
            row[out_col] = geomean(sub[source_col]) if source_col in sub.columns else np.nan

        rows.append(row)

    out = pd.DataFrame(rows)

    # Useful discussion columns: lower is better for normalized time metrics.
    if "makespan" in out.columns:
        out["makespan_reduction_%"] = (1.0 - out["makespan"]) * 100.0
    if "mean_jct" in out.columns:
        out["mean_jct_reduction_%"] = (1.0 - out["mean_jct"]) * 100.0
    if "mean_execution_time" in out.columns:
        out["mean_execution_overhead_%"] = (out["mean_execution_time"] - 1.0) * 100.0

    ordered = [
        "policy",
        "makespan",
        "makespan_reduction_%",
        "mean_jct",
        "mean_jct_reduction_%",
        "p95_jct",
        "mean_queue_wait",
        "p95_queue_wait",
        "mean_execution_time",
        "mean_execution_overhead_%",
        "p95_execution_time",
    ]
    out = out[[c for c in ordered if c in out.columns]]
    out.to_csv(OUT_DIR / "geomean_policy_summary.csv", index=False)
    return out



def _pick_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _ecdf_xy(values: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    vals = pd.to_numeric(values, errors="coerce")
    vals = vals[np.isfinite(vals)]
    vals = vals[vals >= 0]
    vals = np.sort(vals.to_numpy())
    if len(vals) == 0:
        return vals, vals
    y = np.arange(1, len(vals) + 1) / len(vals)
    return vals, y


def plot_ecdf_by_trace(jobs: pd.DataFrame | None, metric_col: str, stem: str, title: str, xlabel: str) -> None:
    if jobs is None or jobs.empty or metric_col not in jobs.columns:
        print(f"Skipping {stem}: missing {metric_col}")
        return

    jobs = add_display_columns(jobs)
    for trace in TRACE_ORDER:
        sub_trace = jobs[jobs["trace_name"].eq(trace)]
        if sub_trace.empty:
            continue

        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        for policy in POLICY_ORDER:
            sub = sub_trace[sub_trace["policy_key"].eq(policy)]
            if sub.empty:
                continue
            x, y = _ecdf_xy(sub[metric_col])
            if len(x) == 0:
                continue
            ax.step(x, y, where="post", label=POLICY_DISPLAY.get(policy, policy), linewidth=1.8)

        ax.set_xlabel(xlabel)
        ax.set_ylabel("Fraction of jobs")
        ax.set_title(f"{TRACE_DISPLAY.get(trace, trace)}: {title}")
        ax.grid(linestyle=":", linewidth=0.8, alpha=0.7)
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()

        out_stem = f"{stem}_{trace}"
        fig.savefig(FIG_DIR / f"{out_stem}.png", dpi=220)
        fig.savefig(FIG_DIR / f"{out_stem}.pdf")
        plt.close(fig)


def plot_completion_progress_by_trace(jobs: pd.DataFrame | None) -> None:
    if jobs is None or jobs.empty:
        print("Skipping completion progress: no job metrics")
        return

    jobs = add_display_columns(jobs)

    # Try common completion/end-time columns from analyzer variants.
    end_col = _pick_column(jobs, [
        "completed_at",
        "completion_time_s",
        "completed_at_s",
        "end_time_s",
        "job_end_time_s",
        "jct_end_s",
        "finish_time_s",
        "successful_attempt_end_s",
    ])

    # If absolute completion timestamp is unavailable, approximate with submission + JCT.
    submit_col = _pick_column(jobs, [
        "submitted_at",
        "submit_time_s",
        "submitted_at_s",
        "arrival_time_s",
        "job_submit_time_s",
    ])
    jct_col = _pick_column(jobs, [
        "jct_s",
        "job_completion_time_s",
        "completion_latency_s",
    ])

    if end_col is None and submit_col is not None and jct_col is not None:
        jobs = jobs.copy()
        jobs["_derived_completion_time_s"] = (
            pd.to_numeric(jobs[submit_col], errors="coerce")
            + pd.to_numeric(jobs[jct_col], errors="coerce")
        )
        end_col = "_derived_completion_time_s"

    if end_col is None:
        print("Skipping completion progress: no completion/end time column found")
        print("available job columns:", ", ".join(jobs.columns))
        return

    for trace in TRACE_ORDER:
        sub_trace = jobs[jobs["trace_name"].eq(trace)]
        if sub_trace.empty:
            continue

        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        for policy in POLICY_ORDER:
            sub = sub_trace[sub_trace["policy_key"].eq(policy)]
            if sub.empty:
                continue
            x = pd.to_numeric(sub[end_col], errors="coerce")
            x = x[np.isfinite(x)]
            x = np.sort(x.to_numpy())
            if len(x) == 0:
                continue
            x = x - np.nanmin(x)
            y = np.arange(1, len(x) + 1)
            ax.step(x / 3600.0, y, where="post", label=POLICY_DISPLAY.get(policy, policy), linewidth=1.8)

        ax.set_xlabel("Elapsed time since first completion (hours)")
        ax.set_ylabel("Completed jobs")
        ax.set_title(f"{TRACE_DISPLAY.get(trace, trace)}: completion progress")
        ax.grid(linestyle=":", linewidth=0.8, alpha=0.7)
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()

        out_stem = f"completion_progress_{trace}"
        fig.savefig(FIG_DIR / f"{out_stem}.png", dpi=220)
        fig.savefig(FIG_DIR / f"{out_stem}.pdf")
        plt.close(fig)


def generate_distribution_figures(jobs: pd.DataFrame | None) -> None:
    if jobs is None or jobs.empty:
        print("Skipping distribution figures: no job metrics")
        return

    jct_col = _pick_column(jobs, ["jct_s", "job_completion_time_s", "completion_latency_s"])
    queue_col = _pick_column(jobs, [
        "initial_queue_wait_s",
        "queue_wait_s",
        "total_queue_wait_s",
        "job_queue_wait_s",
    ])
    exec_col = _pick_column(jobs, [
        "execution_span_s",
        "total_execution_time_s",
        "successful_attempt_runtime_s",
        "runtime_s",
    ])

    if jct_col:
        plot_ecdf_by_trace(jobs, jct_col, "jct_ecdf", "JCT ECDF", "Job completion time (s)")
    else:
        print("No JCT column found for ECDF")

    if queue_col:
        plot_ecdf_by_trace(jobs, queue_col, "queue_wait_ecdf", "queue-wait ECDF", "Queue wait (s)")
    else:
        print("No queue-wait column found for ECDF")

    if exec_col:
        plot_ecdf_by_trace(jobs, exec_col, "execution_time_ecdf", "execution-time ECDF", "Execution time (s)")
    else:
        print("No execution-time column found for ECDF")

    plot_completion_progress_by_trace(jobs)

def write_report(df: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> None:
    lines = []

    lines.append("# Legacy RTX-2080Ti Evaluation\n")
    lines.append("This polished report is generated from the completed legacy Zeus analysis outputs. It does not modify the original analyzer outputs.\n")

    lines.append("## Evaluation status\n")
    status = (
        df.groupby("trace_name")
        .agg(
            configurations=("configuration_label", "nunique"),
            min_completion_fraction=("completion_fraction", "min"),
            failed_attempts=("failed_attempt_count", "sum"),
            recovered_attempts=("recovered_attempt_count", "sum"),
        )
        .reset_index()
    )
    status["trace"] = status["trace_name"].map(TRACE_DISPLAY).fillna(status["trace_name"])
    status = status[["trace", "configurations", "min_completion_fraction", "failed_attempts", "recovered_attempts"]]
    lines.append(markdown_table(status, 3))
    lines.append("")

    lines.append("## Trace note\n")
    lines.append(
        "The Venus legacy replay uses `venus_gapfix600`, a minimally adjusted variant of the Venus-derived trace. "
        "The original trace contained one idle interval of approximately 5.87 hours; only that interval was replaced by a 600-second gap. "
        "Job order and all other inter-arrival gaps are preserved. This avoids spending hours testing the replay harness idle path rather than scheduling behavior.\n"
    )

    lines.append("## Cross-trace geomean summary\n")
    geomean_summary = build_geomean_summary(df)
    lines.append(
        "All values are geometric means across traces and are normalized to Exclusive. "
        "Values below 1.0 are better for time metrics. The percentage columns report reduction relative to Exclusive; "
        "execution overhead is positive when co-location slows execution.\n"
    )
    lines.append(markdown_table(geomean_summary, 3))
    lines.append("")

    lines.append("## Cross-trace comparison\n")
    metric_sections = [
        ("Normalized makespan", "normalized_makespan_by_trace", "figures/normalized_makespan_by_trace.png"),
        ("Normalized mean JCT", "normalized_mean_jct_by_trace", "figures/normalized_mean_jct_by_trace.png"),
        ("Normalized P95 JCT", "normalized_p95_jct_by_trace", "figures/normalized_p95_jct_by_trace.png"),
        ("Normalized mean queue wait", "normalized_mean_queue_wait_by_trace", "figures/normalized_mean_queue_wait_by_trace.png"),
        ("Normalized P95 queue wait", "normalized_p95_queue_wait_by_trace", "figures/normalized_p95_queue_wait_by_trace.png"),
        ("Normalized mean execution time", "normalized_mean_execution_time_by_trace", "figures/normalized_mean_execution_time_by_trace.png"),
        ("Normalized P95 execution time", "normalized_p95_execution_time_by_trace", "figures/normalized_p95_execution_time_by_trace.png"),
    ]

    for title, stem, fig in metric_sections:
        table = tables.get(stem)
        if table is None:
            continue
        lines.append(f"### {title}\n")
        lines.append(f"![{title}]({fig})\n")
        lines.append(markdown_table(table, 3))
        lines.append("")

    lines.append("## Cross-trace mean/P95 summaries\n")
    marker_figs = [
        ("JCT mean bars with P95 markers", "figures/normalized_jct_mean_bars_p95_markers_by_trace.png"),
        ("Queue-wait mean bars with P95 markers", "figures/normalized_queue_wait_mean_bars_p95_markers_by_trace.png"),
        ("Execution-time mean bars with P95 markers", "figures/normalized_execution_time_mean_bars_p95_markers_by_trace.png"),
    ]
    for title, fig in marker_figs:
        lines.append(f"### {title}\n")
        lines.append(f"![{title}]({fig})\n")

    lines.append("### Queue/execution trade-off\n")
    lines.append("![Queue/execution trade-off](figures/normalized_queue_execution_tradeoff.png)\n")

    lines.append("## Per-trace distribution figures\n")
    distribution_specs = [
        ("JCT ECDF", "jct_ecdf"),
        ("Queue-wait ECDF", "queue_wait_ecdf"),
        ("Execution-time ECDF", "execution_time_ecdf"),
        ("Completion progress", "completion_progress"),
    ]
    for trace in TRACE_ORDER:
        trace_title = TRACE_DISPLAY.get(trace, trace)
        lines.append(f"### {trace_title}\n")
        added = 0
        for title, stem in distribution_specs:
            candidates = sorted((FIG_DIR).glob(f"{stem}*{trace}*.png"))
            if not candidates:
                candidates = sorted((FIG_DIR).glob(f"*{stem}*{trace}*.png"))
            for candidate in candidates[:1]:
                rel = candidate.relative_to(OUT_DIR)
                lines.append(f"#### {title}\n")
                lines.append(f"![{trace_title} {title}]({rel.as_posix()})\n")
                added += 1
        if added == 0:
            lines.append("_No distribution figures were generated for this trace._\n")

    lines.append("## Per-trace raw summaries\n")
    raw_cols = [
        "trace_display",
        "policy_display",
        "makespan_s",
        "jct_mean_s",
        "jct_p95_s",
        "total_queue_wait_mean_s",
        "total_queue_wait_p95_s",
        "total_execution_time_mean_s",
        "total_execution_time_p95_s",
        "failed_attempt_count",
        "recovered_attempt_count",
    ]

    for trace in TRACE_ORDER:
        sub = df[df["trace_name"].eq(trace)].sort_values("policy_order")
        if sub.empty:
            continue
        lines.append(f"### {TRACE_DISPLAY.get(trace, trace)}\n")
        table = sub[[c for c in raw_cols if c in sub.columns]].copy()
        table = table.rename(columns={
            "trace_display": "trace",
            "policy_display": "policy",
            "makespan_s": "makespan_s",
            "jct_mean_s": "mean_jct_s",
            "jct_p95_s": "p95_jct_s",
            "total_queue_wait_mean_s": "mean_queue_wait_s",
            "total_queue_wait_p95_s": "p95_queue_wait_s",
            "total_execution_time_mean_s": "mean_execution_s",
            "total_execution_time_p95_s": "p95_execution_s",
            "failed_attempt_count": "failed_attempts",
            "recovered_attempt_count": "recovered_attempts",
        })
        lines.append(markdown_table(table, 2))
        lines.append("")

    (OUT_DIR / "report_polished.md").write_text("\n".join(lines))


def main() -> None:
    ensure_dirs()

    runs, jobs = read_inputs()
    if jobs is not None:
        jobs.to_csv(OUT_DIR / "all_job_metrics_polished.csv", index=False)
    df = add_display_columns(runs)
    df = derive_safe_metric_columns(df)

    metrics = [
        "makespan_s",
        "jct_mean_s",
        "jct_p95_s",
        "total_queue_wait_mean_s",
        "total_queue_wait_p95_s",
        "total_execution_time_mean_s",
        "total_execution_time_p95_s",
    ]
    df = normalize_by_exclusive(df, metrics)
    df = df.sort_values(["trace_order", "policy_order"])

    df.to_csv(OUT_DIR / "all_run_summaries_polished.csv", index=False)

    metric_specs = [
        ("makespan_s_vs_exclusive", "normalized_makespan_by_trace", "Normalized makespan", "Normalized to Exclusive"),
        ("jct_mean_s_vs_exclusive", "normalized_mean_jct_by_trace", "Normalized mean JCT", "Normalized to Exclusive"),
        ("jct_p95_s_vs_exclusive", "normalized_p95_jct_by_trace", "Normalized P95 JCT", "Normalized to Exclusive"),
        ("total_queue_wait_mean_s_vs_exclusive", "normalized_mean_queue_wait_by_trace", "Normalized mean queue wait", "Normalized to Exclusive"),
        ("total_queue_wait_p95_s_vs_exclusive", "normalized_p95_queue_wait_by_trace", "Normalized P95 queue wait", "Normalized to Exclusive"),
        ("total_execution_time_mean_s_vs_exclusive", "normalized_mean_execution_time_by_trace", "Normalized mean execution time", "Normalized to Exclusive"),
        ("total_execution_time_p95_s_vs_exclusive", "normalized_p95_execution_time_by_trace", "Normalized P95 execution time", "Normalized to Exclusive"),
    ]

    tables = {}
    for norm_col, stem, title, ylabel in metric_specs:
        table = write_cross_trace_table(df, norm_col, stem)
        tables[stem] = table
        plot_cross_trace_bars(table, stem, title, ylabel)

    plot_mean_p95_markers(
        df,
        "jct_mean_s_vs_exclusive",
        "jct_p95_s_vs_exclusive",
        "normalized_jct_mean_bars_p95_markers_by_trace",
        "Cross-trace JCT summary",
        "Geomean normalized to Exclusive",
    )
    plot_mean_p95_markers(
        df,
        "total_queue_wait_mean_s_vs_exclusive",
        "total_queue_wait_p95_s_vs_exclusive",
        "normalized_queue_wait_mean_bars_p95_markers_by_trace",
        "Cross-trace queue-wait summary",
        "Geomean normalized to Exclusive",
    )
    plot_mean_p95_markers(
        df,
        "total_execution_time_mean_s_vs_exclusive",
        "total_execution_time_p95_s_vs_exclusive",
        "normalized_execution_time_mean_bars_p95_markers_by_trace",
        "Cross-trace execution-time summary",
        "Geomean normalized to Exclusive",
    )

    plot_queue_execution_tradeoff(df)
    generate_distribution_figures(jobs)
    write_report(df, tables)

    print("wrote:", OUT_DIR / "report_polished.md")
    print("figures:", FIG_DIR)
    print("tables:", TABLE_DIR)


if __name__ == "__main__":
    main()
