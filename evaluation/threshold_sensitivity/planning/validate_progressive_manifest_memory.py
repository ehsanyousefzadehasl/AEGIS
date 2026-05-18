#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd


DEFAULT_MEMORY_CSV = "evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validate cumulative GPU memory peaks in a progressive threshold manifest."
    )
    p.add_argument("--manifest-csv", required=True)
    p.add_argument("--memory-csv", default=DEFAULT_MEMORY_CSV)
    p.add_argument("--capacity-mib", type=float, default=40960.0)
    p.add_argument("--guard-mib", type=float, default=2048.0)
    return p.parse_args()


def normalize_spec(path: str) -> str:
    return Path(str(path).strip()).name


def load_memory_lookup(path: str) -> dict[str, float]:
    df = pd.read_csv(path)

    required = {"spec_path", "gpu_memory_peak_full_mib"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")

    lookup: dict[str, float] = {}
    for _, row in df.iterrows():
        spec_name = normalize_spec(row["spec_path"])
        peak = row["gpu_memory_peak_full_mib"]
        if pd.isna(peak):
            continue
        lookup[spec_name] = float(peak)

    return lookup


def main() -> int:
    args = parse_args()
    memory_lookup = load_memory_lookup(args.memory_csv)

    usable_capacity = float(args.capacity_mib) - float(args.guard_mib)
    bad_rows = []

    with Path(args.manifest_csv).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            trial_id = row["trial_id"]
            jobs = [x.strip() for x in row["job_sequence"].split(";") if x.strip()]

            cumulative = 0.0
            print(f"\n== {trial_id}")

            for idx, job in enumerate(jobs, start=1):
                spec_name = normalize_spec(job)
                peak = memory_lookup.get(spec_name)

                if peak is None:
                    bad_rows.append((trial_id, idx, spec_name, "missing_memory"))
                    print(f"  stage {idx}: {spec_name}: MISSING")
                    continue

                cumulative += peak
                status = "OK" if cumulative <= usable_capacity else "EXCEEDS"
                print(
                    f"  stage {idx}: {spec_name}: "
                    f"peak={peak:.0f} MiB cumulative={cumulative:.0f} MiB "
                    f"usable={usable_capacity:.0f} MiB [{status}]"
                )

                if cumulative > usable_capacity:
                    bad_rows.append((trial_id, idx, spec_name, "exceeds_capacity"))

    if bad_rows:
        print("\nFAILED memory validation:")
        for item in bad_rows:
            print("  ", item)
        return 1

    print("\nAll trials passed cumulative-memory validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())