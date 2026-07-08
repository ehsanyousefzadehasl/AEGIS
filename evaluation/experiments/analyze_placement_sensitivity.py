from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import pandas as pd
import matplotlib.pyplot as plt


RESULTS_DIR = Path("evaluation/experiments/results")
OUT_DIR = RESULTS_DIR / "placement_sensitivity_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FINAL_ANALYSIS = RESULTS_DIR / "final_representative_evaluation_analysis" / "all_run_summaries.csv"

POLICY_LABELS = {
    "exclusive": "Exclusive",
    "OR-MAGM": "Memory-aware greedy",
    "OR-LUG": "Least-utilized GPU",
    "OR-RR": "Round-robin",
}

POLICY_ORDER = {
    "exclusive": 0,
    "OR-RR": 1,
    "OR-LUG": 2,
    "OR-MAGM": 3,
}

TRACE_ORDER = {
    "philly": 0,
    "venus": 1,
    "saturn": 2,
}


def _latest_policy_run_dir(parent: Path) -> Path | None:
    if not parent.exists():
        return None
    candidates = []
    for policy_dir in parent.glob("*"):
        if policy_dir.is_dir():
            candidates.append(policy_dir)
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]


def _summarize_single_run(run_dir: Path) -> pd.DataFrame | None:
    """
    Use the existing summarizer to avoid duplicating run parsing logic.
    """
    tmp = OUT_DIR / "_tmp_single_summary.csv"
    if tmp.exists():
        tmp.unlink()

    cmd = [
        sys.executable,
        "evaluation/experiments/summarize_policy_runs.py",
        "--run-dir",
        str(run_dir),
        "--output-csv",
        str(tmp),
    ]

    try:
        subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"[skip] summarizer failed for {run_dir}")
        print(e.stderr[-1000:])
        return None

    if not tmp.exists():
        print(f"[skip] no summary produced for {run_dir}")
        return None

    df = pd.read_csv(tmp)
    tmp.unlink(missing_ok=True)

    if df.empty:
        print(f"[skip] empty summary for {run_dir}")
        return None

    return df


def _load_existing_exclusive_and_magm() -> pd.DataFrame:
    if not FINAL_ANALYSIS.exists():
        print(f"[warn] missing {FINAL_ANALYSIS}")
        return pd.DataFrame()

    df = pd.read_csv(FINAL_ANALYSIS)

    keep = df[
        df["policy"].isin(["exclusive", "OR-MAGM"])
        & df["estimator"].isna()
    ].copy()

    # Keep only the original final representative evaluation rows.
    keep = keep[
        keep["experiment_name"].astype(str).str.contains(
            "final_representative_evaluation__",
            regex=False,
            na=False,
        )
    ].copy()

    return keep


def _load_new_or_rr_lug() -> pd.DataFrame:
    rows = []

    for parent in sorted(RESULTS_DIR.glob("final_representative_evaluation_or_placement_sensitivity__*")):
        run_dir = _latest_policy_run_dir(parent)
        if run_dir is None:
            print(f"[skip] no policy dir under {parent}")
            continue

        df = _summarize_single_run(run_dir)
        if df is None or df.empty:
            continue

        rows.append(df)

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def _extract_trace_name(row) -> str:
    if "trace_name" in row and pd.notna(row["trace_name"]):
        return str(row["trace_name"])

    exp = str(row.get("experiment_name", ""))
    m = re.search(r"__(philly|venus|saturn)__", exp)
    if m:
        return m.group(1)

    trace_csv = str(row.get("trace_csv", ""))
    m = re.search(r"(philly|venus|saturn)_seed", trace_csv)
    if m:
        return m.group(1)

    return "unknown"


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()

    if "trace_name" not in out.columns:
        out["trace_name"] = out.apply(_extract_trace_name, axis=1)
    else:
        out["trace_name"] = out.apply(_extract_trace_name, axis=1)

    out["policy_label"] = out["policy"].map(POLICY_LABELS).fillna(out["policy"])
    out["policy_order"] = out["policy"].map(POLICY_ORDER).fillna(999).astype(int)
    out["trace_order"] = out["trace_name"].map(TRACE_ORDER).fillna(999).astype(int)

    # Standardize metric names.
    if "makespan_seconds" in out.columns and "makespan_s" not in out.columns:
        out["makespan_s"] = out["makespan_seconds"]

    return out


def _add_exclusive_normalization(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    exclusive = (
        out[out["policy"] == "exclusive"]
        .set_index("trace_name")["makespan_s"]
        .to_dict()
    )

    out["exclusive_makespan_s"] = out["trace_name"].map(exclusive)
    out["makespan_gain_vs_exclusive"] = out["exclusive_makespan_s"] / out["makespan_s"]
    out["normalized_makespan_vs_exclusive"] = out["makespan_s"] / out["exclusive_makespan_s"]

    return out


def _save_bar(df: pd.DataFrame, metric: str, ylabel: str, title: str, out_path: Path):
    plot = df.copy()
    plot = plot.sort_values(["trace_order", "policy_order"])

    traces = [t for t in ["philly", "venus", "saturn"] if t in set(plot["trace_name"])]
    policies = [p for p in ["exclusive", "OR-RR", "OR-LUG", "OR-MAGM"] if p in set(plot["policy"])]

    x = range(len(traces))
    width = 0.18

    plt.figure(figsize=(7.2, 3.6))

    offsets = {
        "exclusive": -1.5 * width,
        "OR-RR": -0.5 * width,
        "OR-LUG": 0.5 * width,
        "OR-MAGM": 1.5 * width,
    }

    for policy in policies:
        vals = []
        for trace in traces:
            r = plot[(plot["trace_name"] == trace) & (plot["policy"] == policy)]
            vals.append(float(r[metric].iloc[0]) if not r.empty and pd.notna(r[metric].iloc[0]) else float("nan"))

        plt.bar(
            [i + offsets.get(policy, 0) for i in x],
            vals,
            width,
            label=POLICY_LABELS.get(policy, policy),
        )

    plt.xticks(list(x), traces)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(axis="y", linestyle=":", linewidth=0.7)
    plt.legend(frameon=False, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=240)
    plt.close()


def _markdown_table(df: pd.DataFrame, cols: list[str]) -> str:
    small = df[cols].copy()
    for c in small.columns:
        if pd.api.types.is_float_dtype(small[c]):
            small[c] = small[c].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
    return small.to_markdown(index=False)


def main():
    existing = _load_existing_exclusive_and_magm()
    new = _load_new_or_rr_lug()

    all_df = pd.concat([existing, new], ignore_index=True)
    all_df = _normalize(all_df)

    if all_df.empty:
        raise SystemExit("No rows found.")

    # Keep only the fair estimator-free placement comparison.
    all_df = all_df[
        all_df["policy"].isin(["exclusive", "OR-MAGM", "OR-LUG", "OR-RR"])
    ].copy()

    all_df = _add_exclusive_normalization(all_df)

    all_df = all_df.sort_values(["trace_order", "policy_order"])

    all_path = OUT_DIR / "all_placement_run_summaries.csv"
    all_df.to_csv(all_path, index=False)

    cols = [
        "trace_name",
        "policy",
        "policy_label",
        "makespan_s",
        "normalized_makespan_vs_exclusive",
        "makespan_gain_vs_exclusive",
        "completion_fraction",
        "completed_job_count",
        "incomplete_job_count",
        "total_attempt_count",
        "failed_attempt_count",
        "recovered_attempt_count",
        "risk_smact_threshold",
        "risk_smocc_threshold",
        "risk_drama_threshold",
        "run_dir",
    ]
    cols = [c for c in cols if c in all_df.columns]

    clean = all_df[cols].copy()
    clean_path = OUT_DIR / "placement_policy_comparison.csv"
    clean.to_csv(clean_path, index=False)

    fig_gain = OUT_DIR / "fig_placement_makespan_gain_vs_exclusive.png"
    fig_norm = OUT_DIR / "fig_placement_normalized_makespan.png"
    fig_fail = OUT_DIR / "fig_placement_failed_attempts.png"

    _save_bar(
        all_df,
        "makespan_gain_vs_exclusive",
        "Makespan gain vs exclusive",
        "Estimator-free placement sensitivity",
        fig_gain,
    )

    _save_bar(
        all_df,
        "normalized_makespan_vs_exclusive",
        "Normalized makespan",
        "Makespan normalized to exclusive baseline",
        fig_norm,
    )

    if "failed_attempt_count" in all_df.columns:
        _save_bar(
            all_df,
            "failed_attempt_count",
            "Failed attempts",
            "Recovery pressure under placement policies",
            fig_fail,
        )

    table_cols = [
        "trace_name",
        "policy_label",
        "makespan_s",
        "makespan_gain_vs_exclusive",
        "completion_fraction",
        "failed_attempt_count",
        "recovered_attempt_count",
    ]
    table_cols = [c for c in table_cols if c in clean.columns]

    md = f"""# Placement Sensitivity Evidence

This report compares estimator-free placement policies on the same representative traces.

## Scope

Policies included:

- **Exclusive**: no collocation baseline.
- **Round-robin**: estimator-free cyclic placement. This policy does not use pressure-based eligibility filtering and relies on recovery if placement is harmful.
- **Least-utilized GPU**: estimator-free placement using the least-utilized eligible GPU.
- **Memory-aware greedy**: estimator-free greedy placement using available memory among eligible GPUs.

This is a placement-policy sensitivity analysis, not an estimator comparison.

## Makespan gain versus exclusive

![Placement makespan gain]({fig_gain.name})

## Normalized makespan

![Placement normalized makespan]({fig_norm.name})

## Recovery pressure

![Placement failed attempts]({fig_fail.name})

## Summary table

{_markdown_table(clean, table_cols)}

Generated files:

- `{all_path}`
- `{clean_path}`
- `{fig_gain}`
- `{fig_norm}`
- `{fig_fail}`
"""

    report_path = OUT_DIR / "placement_sensitivity_report.md"
    report_path.write_text(md)

    print("wrote", all_path)
    print("wrote", clean_path)
    print("wrote", report_path)
    print("wrote", fig_gain)
    print("wrote", fig_norm)
    print("wrote", fig_fail)
    print()
    print(clean[table_cols].to_string(index=False))


if __name__ == "__main__":
    main()
