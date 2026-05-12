#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_PROFILE_CSV = "evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Update workload YAML specs with solo profiling metadata."
    )
    p.add_argument(
        "--profile-csv",
        action="append",
        default=None,
        help="Profiling CSV. Can be passed multiple times.",
    )
    p.add_argument(
        "--spec-root",
        default="evaluation/workloads/training/specs/yaml",
        help="Root directory containing workload YAML specs.",
    )
    p.add_argument(
        "--write",
        action="store_true",
        help="Actually modify YAML files. Without this, only prints planned changes.",
    )
    p.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak backup before modifying each YAML file.",
    )
    return p.parse_args()


def spec_name(path: str) -> str:
    return Path(str(path)).name


def load_profile_rows(profile_csv: str) -> dict[str, dict]:
    df = pd.read_csv(profile_csv)

    required = {"spec_path"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{profile_csv} missing required columns: {sorted(missing)}")

    has_1gpu_memory = {
        "gpu_memory_peak_200s_mib",
        "gpu_memory_peak_full_mib",
    }.issubset(df.columns)

    has_2gpu_memory = {
        "gpu_memory_peak_200s_mib_gpu_a",
        "gpu_memory_peak_200s_mib_gpu_b",
        "gpu_memory_peak_full_mib_gpu_a",
        "gpu_memory_peak_full_mib_gpu_b",
    }.issubset(df.columns)

    if not has_1gpu_memory and not has_2gpu_memory:
        raise ValueError(
            f"{profile_csv} does not look like a supported 1-GPU or 2-GPU profile CSV"
        )

    rows = {}
    for _, row in df.iterrows():
        rows[spec_name(row["spec_path"])] = row.to_dict()

    return rows


def set_nested(mapping: dict, keys: list[str], value) -> None:
    cur = mapping
    for key in keys[:-1]:
        if cur.get(key) is None:
            cur[key] = {}
        cur = cur[key]
    cur[keys[-1]] = value


def maybe_float(value):
    if pd.isna(value):
        return None
    return float(value)


def max_available(row: dict, keys: list[str]) -> float | None:
    values = []
    for key in keys:
        value = row.get(key)
        if value is None or pd.isna(value):
            continue
        values.append(float(value))
    if not values:
        return None
    return max(values)


def extract_profile_values(row: dict) -> dict:
    gpu_count = int(row.get("gpu_count", 1) or 1)

    if gpu_count > 1:
        peak_200s = max_available(
            row,
            [
                "gpu_memory_peak_200s_mib_gpu_a",
                "gpu_memory_peak_200s_mib_gpu_b",
            ],
        )
        peak_full = max_available(
            row,
            [
                "gpu_memory_peak_full_mib_gpu_a",
                "gpu_memory_peak_full_mib_gpu_b",
            ],
        )
        avg_smact = max_available(row, ["smact_mean_200s_gpu_a", "smact_mean_200s_gpu_b"])
        avg_smocc = max_available(row, ["smocc_mean_200s_gpu_a", "smocc_mean_200s_gpu_b"])
        avg_drama = max_available(row, ["drama_mean_200s_gpu_a", "drama_mean_200s_gpu_b"])
    else:
        peak_200s = maybe_float(row.get("gpu_memory_peak_200s_mib"))
        peak_full = maybe_float(row.get("gpu_memory_peak_full_mib"))
        avg_smact = maybe_float(row.get("smact_mean_200s"))
        avg_smocc = maybe_float(row.get("smocc_mean_200s"))
        avg_drama = maybe_float(row.get("drama_mean_200s"))

    return {
        "gpu_count": gpu_count,
        "peak_200s": peak_200s,
        "peak_full": peak_full,
        "avg_smact": avg_smact,
        "avg_smocc": avg_smocc,
        "avg_drama": avg_drama,
    }

def update_spec_data(data: dict, row: dict) -> dict:
    values = extract_profile_values(row)

    peak_200s = values["peak_200s"]
    peak_full = values["peak_full"]
    avg_smact = values["avg_smact"]
    avg_smocc = values["avg_smocc"]
    avg_drama = values["avg_drama"]
    requirement = maybe_float(row.get("gpu_memory_requirement_mib"))

    if peak_full is not None:
        set_nested(data, ["resources", "gpu_memory_requirement_mib"], int(round(peak_full)))

    if peak_200s is not None:
        set_nested(data, ["profile", "peak_memory_mib"], int(round(peak_200s)))

    set_nested(data, ["profile", "profiling_duration_s"], 200)
    set_nested(data, ["profile", "source"], "solo_profile_200s")

    if avg_smact is not None:
        set_nested(data, ["profile", "avg_smact"], float(avg_smact))
    if avg_smocc is not None:
        set_nested(data, ["profile", "avg_smocc"], float(avg_smocc))
    if avg_drama is not None:
        set_nested(data, ["profile", "avg_drama"], float(avg_drama))

    # Keep the original requirement if present for traceability.
    if requirement is not None:
        set_nested(
            data,
            ["profile", "extra_metrics", "original_gpu_memory_requirement_mib"],
            int(round(requirement)),
        )

    if peak_full is not None:
        set_nested(
            data,
            ["profile", "extra_metrics", "full_run_peak_memory_mib"],
            int(round(peak_full)),
        )

    return data


def main() -> int:
    args = parse_args()

    profile_csvs = args.profile_csv or [DEFAULT_PROFILE_CSV]

    profile_rows = {}
    for profile_csv in profile_csvs:
        profile_rows.update(load_profile_rows(profile_csv))

    spec_root = Path(args.spec_root)

    updated = 0
    missing = 0

    for spec_path in sorted(spec_root.glob("*.yaml")):
        row = profile_rows.get(spec_path.name)
        if row is None:
            missing += 1
            print(f"[missing profile] {spec_path}")
            continue

        with spec_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        new_data = update_spec_data(data, row)

        print(
            f"[update] {spec_path.name}: "
            f"resources.gpu_memory_requirement_mib={new_data.get('resources', {}).get('gpu_memory_requirement_mib')} "
            f"profile.peak_memory_mib={new_data.get('profile', {}).get('peak_memory_mib')}"
        )

        if args.write:
            if args.backup:
                shutil.copy2(spec_path, spec_path.with_suffix(spec_path.suffix + ".bak"))

            with spec_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(
                    new_data,
                    f,
                    sort_keys=False,
                    default_flow_style=False,
                )

        updated += 1

    print(f"\nupdated_candidates={updated}")
    print(f"missing_profiles={missing}")
    print("dry_run=True" if not args.write else "dry_run=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())