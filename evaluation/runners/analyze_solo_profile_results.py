#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_1GPU = (
    REPO_ROOT
    / "evaluation"
    / "profiling"
    / "solo"
    / "extracted"
    / "solo_profile_results_1gpu.csv"
)

DEFAULT_INPUT_2GPU = (
    REPO_ROOT
    / "evaluation"
    / "profiling"
    / "solo"
    / "extracted"
    / "solo_profile_results_2gpu.csv"
)

DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "evaluation"
    / "profiling"
    / "solo"
    / "analysis"
)

GENERIC_PROFILE_RE = re.compile(
    r"^(?P<metric>.+)_(?P<stat>max|mean|median|mode|p95|ewma)_(?P<window>200s|full)$"
)

MEMORY_PROFILE_RE = re.compile(
    r"^gpu_memory_peak_(?P<window>200s|full)_mib$"
)

ENERGY_RE = re.compile(
    r"^(?P<metric>totec_delta_j|totec_delta_mj)$"
)

METADATA_COLUMNS = [
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

PROFILE_STAT_SCORE_STATS = ["mean", "median", "mode", "max"]
AEGIS_PROFILE_RISK_STATS = ["mean", "median", "p95", "ewma"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Analyze extracted solo profile results from evaluation/profiling/solo/extracted."
    )
    p.add_argument("--input-1gpu", default=str(DEFAULT_INPUT_1GPU))
    p.add_argument("--input-2gpu", default=str(DEFAULT_INPUT_2GPU))
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--compute-threshold", type=float, default=50.0)
    p.add_argument("--memory-threshold", type=float, default=30.0)
    return p.parse_args()


def split_gpu_suffix(column: str, default_gpu_label: str) -> tuple[str, str]:
    for suffix, label in [
        ("_gpu_a", "gpu_a"),
        ("_gpu_b", "gpu_b"),
        ("_sum", "sum"),
    ]:
        if column.endswith(suffix):
            return column[: -len(suffix)], label

    return column, default_gpu_label


def parse_profile_column(column: str, default_gpu_label: str) -> dict | None:
    base, gpu_label = split_gpu_suffix(column, default_gpu_label)

    memory_match = MEMORY_PROFILE_RE.match(base)
    if memory_match:
        return {
            "gpu_label": gpu_label,
            "window": memory_match.group("window"),
            "metric": "gpu_memory_peak_mib",
            "stat": "peak",
        }

    generic_match = GENERIC_PROFILE_RE.match(base)
    if generic_match:
        return {
            "gpu_label": gpu_label,
            "window": generic_match.group("window"),
            "metric": generic_match.group("metric"),
            "stat": generic_match.group("stat"),
        }

    energy_match = ENERGY_RE.match(base)
    if energy_match:
        return {
            "gpu_label": gpu_label,
            "window": "full",
            "metric": energy_match.group("metric"),
            "stat": "delta",
        }

    return None


def metadata_from_row(row: pd.Series) -> dict:
    return {column: row.get(column) for column in METADATA_COLUMNS if column in row.index}


def normalize_profile_dataframe(df: pd.DataFrame, *, gpu_count: int) -> pd.DataFrame:
    rows = []
    default_gpu_label = "single" if gpu_count == 1 else "unknown"

    for _, row in df.iterrows():
        metadata = metadata_from_row(row)
        metadata["source_gpu_count"] = gpu_count

        for column in df.columns:
            parsed = parse_profile_column(column, default_gpu_label)
            if parsed is None:
                continue

            value = pd.to_numeric(row.get(column), errors="coerce")
            if pd.isna(value):
                continue

            rows.append(
                {
                    **metadata,
                    "gpu_label": parsed["gpu_label"],
                    "window": parsed["window"],
                    "metric": parsed["metric"],
                    "stat": parsed["stat"],
                    "value": float(value),
                    "source_column": column,
                }
            )

    return pd.DataFrame(rows)


def add_equal_weight_profile_scores(long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived per-metric, per-GPU, per-window profile scores.

    profile_stat_score:
        Equal-weight score over mean, median, mode, and max.
        This matches the statistics available in older extracted solo-profile CSVs.
        It is not the AEGIS risk formula.

    aegis_profile_risk:
        Equal-weight score over mean, median, p95, and EWMA.
        This is only computed when p95 and ewma are available in the input data.
    """
    if long_df.empty:
        return long_df

    group_cols = [
        "workload_id",
        "run_id",
        "spec_path",
        "source_gpu_count",
        "gpu_label",
        "window",
        "metric",
    ]

    derived_rows = []

    grouped = long_df.groupby(group_cols, dropna=False, sort=False)

    def build_score_row(group: pd.DataFrame, required_stats: list[str], score_name: str) -> dict | None:
        stats = set(group["stat"].dropna().astype(str))
        if not set(required_stats).issubset(stats):
            return None

        values = {}
        for stat in required_stats:
            stat_values = group.loc[group["stat"] == stat, "value"]
            if stat_values.empty:
                return None
            values[stat] = float(stat_values.iloc[0])

        base = group.iloc[0].to_dict()
        base["stat"] = score_name
        base["value"] = sum(values.values()) / len(required_stats)
        base["source_column"] = f"computed_equal_weight_{'_'.join(required_stats)}"
        return base

    for _, group in grouped:
        profile_stat_score = build_score_row(
            group,
            PROFILE_STAT_SCORE_STATS,
            "profile_stat_score",
        )
        if profile_stat_score is not None:
            derived_rows.append(profile_stat_score)

        aegis_profile_risk = build_score_row(
            group,
            AEGIS_PROFILE_RISK_STATS,
            "aegis_profile_risk",
        )
        if aegis_profile_risk is not None:
            derived_rows.append(aegis_profile_risk)

    if not derived_rows:
        return long_df

    return pd.concat([long_df, pd.DataFrame(derived_rows)], ignore_index=True)



def build_200s_vs_full(long_df: pd.DataFrame) -> pd.DataFrame:
    if long_df.empty:
        return pd.DataFrame()

    id_cols = [
        c
        for c in [
            "workload_id",
            "run_id",
            "spec_path",
            "source_gpu_count",
            "gpu_label",
            "metric",
            "stat",
        ]
        if c in long_df.columns
    ]

    subset = long_df[long_df["window"].isin(["200s", "full"])].copy()
    pivot = subset.pivot_table(
        index=id_cols,
        columns="window",
        values="value",
        aggfunc="first",
    ).reset_index()

    if "200s" not in pivot.columns:
        pivot["200s"] = pd.NA
    if "full" not in pivot.columns:
        pivot["full"] = pd.NA

    pivot = pivot.rename(columns={"200s": "value_200s", "full": "value_full"})
    pivot["abs_error_200s_vs_full"] = (pivot["value_200s"] - pivot["value_full"]).abs()

    denom = pivot["value_full"].abs()
    pivot["relative_error_200s_vs_full"] = (
        pivot["abs_error_200s_vs_full"] / denom.where(denom > 1e-9)
    )

    return pivot


def classify_workload(row: pd.Series, compute_threshold: float, memory_threshold: float) -> str:
    smact = row.get(
        "smact_aegis_profile_risk_full",
        row.get("smact_profile_stat_score_full", row.get("smact_mean_full")),
    )
    drama = row.get(
        "drama_aegis_profile_risk_full",
        row.get("drama_profile_stat_score_full", row.get("drama_mean_full")),
    )

    if pd.isna(smact) or pd.isna(drama):
        return "unknown"

    if smact >= compute_threshold and drama >= memory_threshold:
        return "mixed_high_compute_memory"
    if smact >= compute_threshold:
        return "compute_heavy"
    if drama >= memory_threshold:
        return "memory_heavy"
    if smact < compute_threshold / 2 and drama < memory_threshold / 2:
        return "light"
    return "moderate"


def build_workload_characterization(
    long_df: pd.DataFrame,
    *,
    compute_threshold: float,
    memory_threshold: float,
) -> pd.DataFrame:
    if long_df.empty:
        return pd.DataFrame()

    wanted = long_df[
        (
            (long_df["window"] == "full")
            & (
                long_df["stat"].isin(
                    [
                        "mean",
                        "median",
                        "max",
                        "mode",
                        "p95",
                        "ewma",
                        "profile_stat_score",
                        "aegis_profile_risk",
                        "peak",
                    ]
                )
            )
            & (long_df["metric"].isin(["smact", "smocc", "drama", "gpu_memory_peak_mib"]))
            & (long_df["gpu_label"] != "sum")
        )
    ].copy()

    if wanted.empty:
        return pd.DataFrame()

    wanted["feature"] = wanted["metric"] + "_" + wanted["stat"] + "_full"

    id_cols = [
        c
        for c in [
            "workload_id",
            "run_id",
            "spec_path",
            "source_gpu_count",
            "gpu_label",
            "training_loop_time_s",
            "end_to_end_time_s",
            "exit_code",
            "gpu_memory_requirement_mib",
            "faketensor_estimate",
        ]
        if c in wanted.columns
    ]

    out = wanted.pivot_table(
        index=id_cols,
        columns="feature",
        values="value",
        aggfunc="first",
    ).reset_index()

    out["coarse_resource_label"] = out.apply(
        lambda row: classify_workload(row, compute_threshold, memory_threshold),
        axis=1,
    )

    return out


def build_lucid_style_profile_labels(long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build Lucid-style Tiny/Medium/Jumbo labels from 200s solo profile data.

    This is not an exact reproduction of Lucid's model. It uses the same high-level
    idea of assigning Tiny/Medium/Jumbo sharing classes from profiling signals.

    We use equal-weight profile_stat_score rows for smact/smocc/drama and peak memory.
    The final pressure score is the maximum normalized pressure across dimensions.
    """
    if long_df.empty:
        return pd.DataFrame()

    wanted = long_df[
        (
            (long_df["window"] == "200s")
            & (
                (
                    long_df["metric"].isin(["smact", "smocc", "drama"])
                    & (long_df["stat"] == "profile_stat_score")
                )
                | (
                    (long_df["metric"] == "gpu_memory_peak_mib")
                    & (long_df["stat"] == "peak")
                )
            )
            & (long_df["gpu_label"] != "sum")
        )
    ].copy()

    if wanted.empty:
        return pd.DataFrame()

    wanted["feature"] = wanted["metric"] + "_" + wanted["stat"] + "_200s"

    id_cols = [
        c
        for c in [
            "workload_id",
            "run_id",
            "spec_path",
            "source_gpu_count",
            "gpu_label",
            "training_loop_time_s",
            "end_to_end_time_s",
            "exit_code",
            "gpu_memory_requirement_mib",
            "faketensor_estimate",
        ]
        if c in wanted.columns
    ]

    out = wanted.pivot_table(
        index=id_cols,
        columns="feature",
        values="value",
        aggfunc="first",
    ).reset_index()

    pressure_features = [
        c
        for c in [
            "smact_profile_stat_score_200s",
            "smocc_profile_stat_score_200s",
            "drama_profile_stat_score_200s",
            "gpu_memory_peak_mib_peak_200s",
        ]
        if c in out.columns
    ]

    if not pressure_features:
        out["lucid_style_pressure_score_200s"] = pd.NA
        out["lucid_style_ss_200s"] = pd.NA
        out["lucid_style_class_200s"] = "unknown"
        return out

    for feature in pressure_features:
        values = pd.to_numeric(out[feature], errors="coerce")
        max_value = values.max(skipna=True)

        if pd.isna(max_value) or max_value <= 0:
            out[f"{feature}_normalized"] = 0.0
        else:
            out[f"{feature}_normalized"] = values / max_value

    normalized_features = [f"{feature}_normalized" for feature in pressure_features]
    out["lucid_style_pressure_score_200s"] = out[normalized_features].max(axis=1)

    low_cut = out["lucid_style_pressure_score_200s"].quantile(1 / 3)
    high_cut = out["lucid_style_pressure_score_200s"].quantile(2 / 3)

    def assign_label(score):
        if pd.isna(score):
            return pd.NA, "unknown"
        if score <= low_cut:
            return 0, "Tiny"
        if score <= high_cut:
            return 1, "Medium"
        return 2, "Jumbo"

    labels = out["lucid_style_pressure_score_200s"].apply(assign_label)
    out["lucid_style_ss_200s"] = labels.apply(lambda x: x[0])
    out["lucid_style_class_200s"] = labels.apply(lambda x: x[1])

    return out


def build_horus_oracle_inputs(long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build Horus-friendly utilization inputs from extracted solo profiles.

    The main generous value is horus_oracle_util_full = gputl_mean_full,
    which treats Horus as if it predicted full-run mean GPU utilization perfectly.

    We also keep 200s, median, and max variants for sensitivity checks.
    """
    if long_df.empty:
        return pd.DataFrame()

    wanted = long_df[
        (
            (
                (long_df["metric"] == "gputl")
                & (long_df["stat"].isin(["mean", "median", "max"]))
                & (long_df["window"].isin(["200s", "full"]))
            )
            |
            (
                (long_df["metric"] == "gpu_memory_peak_mib")
                & (long_df["stat"] == "peak")
                & (long_df["window"].isin(["200s", "full"]))
            )
        )
        & (long_df["gpu_label"] != "sum")
    ].copy()

    if wanted.empty:
        return pd.DataFrame()

    wanted["feature"] = wanted["metric"] + "_" + wanted["stat"] + "_" + wanted["window"]

    id_cols = [
        c
        for c in [
            "workload_id",
            "run_id",
            "spec_path",
            "source_gpu_count",
            "gpu_label",
            "training_loop_time_s",
            "end_to_end_time_s",
            "exit_code",
            "gpu_memory_requirement_mib",
            "faketensor_estimate",
        ]
        if c in wanted.columns
    ]

    out = wanted.pivot_table(
        index=id_cols,
        columns="feature",
        values="value",
        aggfunc="first",
    ).reset_index()

    required_features = [
        "gputl_mean_full",
        "gputl_mean_200s",
        "gputl_median_full",
        "gputl_median_200s",
        "gputl_max_full",
        "gputl_max_200s",
        "gpu_memory_peak_mib_peak_full",
        "gpu_memory_peak_mib_peak_200s",
    ]

    for feature in required_features:
        if feature not in out.columns:
            out[feature] = pd.NA

    out["horus_oracle_util_full"] = out["gputl_mean_full"]
    out["horus_profile_util_200s"] = out["gputl_mean_200s"]
    out["horus_oracle_util_median_full"] = out["gputl_median_full"]
    out["horus_profile_util_median_200s"] = out["gputl_median_200s"]
    out["horus_oracle_util_max_full"] = out["gputl_max_full"]
    out["horus_profile_util_max_200s"] = out["gputl_max_200s"]
    out["horus_oracle_memory_full_mib"] = out["gpu_memory_peak_mib_peak_full"]
    out["horus_profile_memory_200s_mib"] = out["gpu_memory_peak_mib_peak_200s"]
    out["horus_oracle_util_source"] = "gputl_mean_full"

    out["horus_abs_error_200s_vs_full_util"] = (
        pd.to_numeric(out["horus_profile_util_200s"], errors="coerce")
        - pd.to_numeric(out["horus_oracle_util_full"], errors="coerce")
    ).abs()

    denom = pd.to_numeric(out["horus_oracle_util_full"], errors="coerce").abs()
    out["horus_relative_error_200s_vs_full_util"] = (
        out["horus_abs_error_200s_vs_full_util"] / denom.where(denom > 1e-9)
    )

    return out

def read_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"missing input, skipping: {path}")
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> int:
    args = parse_args()

    input_1gpu = Path(args.input_1gpu)
    input_2gpu = Path(args.input_2gpu)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df_1gpu = read_if_exists(input_1gpu)
    df_2gpu = read_if_exists(input_2gpu)

    long_parts = []
    if not df_1gpu.empty:
        long_parts.append(normalize_profile_dataframe(df_1gpu, gpu_count=1))
    if not df_2gpu.empty:
        long_parts.append(normalize_profile_dataframe(df_2gpu, gpu_count=2))

    long_df = pd.concat(long_parts, ignore_index=True) if long_parts else pd.DataFrame()
    long_df = add_equal_weight_profile_scores(long_df)

    comparison_df = build_200s_vs_full(long_df)
    characterization_df = build_workload_characterization(
        long_df,
        compute_threshold=float(args.compute_threshold),
        memory_threshold=float(args.memory_threshold),
    )
    lucid_style_labels_df = build_lucid_style_profile_labels(long_df)
    horus_oracle_inputs_df = build_horus_oracle_inputs(long_df)

    long_path = output_dir / "solo_profiles_long.csv"
    comparison_path = output_dir / "profile_200s_vs_full.csv"
    characterization_path = output_dir / "workload_characterization.csv"
    lucid_style_labels_path = output_dir / "lucid_style_profile_labels.csv"
    horus_oracle_inputs_path = output_dir / "horus_oracle_inputs.csv"

    long_df.to_csv(long_path, index=False)
    comparison_df.to_csv(comparison_path, index=False)
    characterization_df.to_csv(characterization_path, index=False)
    lucid_style_labels_df.to_csv(lucid_style_labels_path, index=False)
    horus_oracle_inputs_df.to_csv(horus_oracle_inputs_path, index=False)

    print(f"wrote {long_path}")
    print(f"wrote {comparison_path}")
    print(f"wrote {characterization_path}")
    print(f"wrote {lucid_style_labels_path}")
    print(f"wrote {horus_oracle_inputs_path}")
    print(f"rows_long={len(long_df)}")
    print(f"rows_comparison={len(comparison_df)}")
    print(f"rows_characterization={len(characterization_df)}")
    print(f"rows_lucid_style_labels={len(lucid_style_labels_df)}")
    print(f"rows_horus_oracle_inputs={len(horus_oracle_inputs_df)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())