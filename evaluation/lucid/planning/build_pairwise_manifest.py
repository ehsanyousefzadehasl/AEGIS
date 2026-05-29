#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from itertools import combinations_with_replacement
from pathlib import Path

import pandas as pd


DEFAULT_SPEC_DIR = "evaluation/workloads/training/specs/yaml_threshold_short"
DEFAULT_SOLO_PROFILE_CSV = "evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv"
DEFAULT_OUTPUT_CSV = "evaluation/lucid/manifests/lucid_pairwise_manifest.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build Lucid pairwise profiling manifest from bounded YAML specs and solo memory profiles."
    )
    p.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    p.add_argument("--solo-profile-csv", default=DEFAULT_SOLO_PROFILE_CSV)
    p.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    p.add_argument("--capacity-mib", type=float, default=40960.0)
    p.add_argument("--guard-mib", type=float, default=2048.0)
    p.add_argument(
        "--include-self-pairs",
        action="store_true",
        help="Include A+A pairs. Useful for Lucid Tiny/Tiny and same-workload characterization.",
    )
    return p.parse_args()


def normalize_spec(path: str) -> str:
    name = Path(str(path).strip()).name
    stem = Path(name).stem

    suffixes = [
        "_maxbatches1200",
        "_maxbatches600",
        "_maxbatches",
        "_maxsteps2000",
    ]

    for suffix in suffixes:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break

    if not stem.endswith("_1gpu"):
        stem = f"{stem}_1gpu"

    return f"{stem}.yaml"


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


def list_specs(spec_dir: str) -> list[Path]:
    root = Path(spec_dir)
    if not root.exists():
        raise FileNotFoundError(f"Spec directory does not exist: {root}")

    specs = sorted(
        [
            *root.glob("*maxbatches1200.yaml"),
            *root.glob("*maxsteps2000.yaml"),
        ]
    )
    
    if not specs:
        raise FileNotFoundError(f"No YAML specs found in: {root}")

    return specs


def main() -> int:
    args = parse_args()

    specs = list_specs(args.spec_dir)
    memory_lookup = load_memory_lookup(args.solo_profile_csv)

    print(f"Loaded {len(memory_lookup)} memory profiles")
    
    usable_capacity = float(args.capacity_mib) - float(args.guard_mib)
    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing_memory: list[str] = []
    workloads = []

    for spec in specs:
        spec_name = spec.name
        lookup_name = normalize_spec(spec_name)
        peak = memory_lookup.get(lookup_name)
        if peak is None:
            missing_memory.append(spec_name)
            continue

        workloads.append(
            {
                "spec_name": spec_name,
                "spec_path": str(spec),
                "peak_memory_mib": float(peak),
            }
        )

    if missing_memory:
        print("WARNING: missing memory profile for these specs; skipped:")
        for item in missing_memory:
            print(f"  {item}")

    pair_iter = (
        combinations_with_replacement(workloads, 2)
        if args.include_self_pairs
        else combinations_with_replacement(workloads, 2)
    )

    rows = []
    skipped_capacity = 0

    for a, b in pair_iter:
        if not args.include_self_pairs and a["spec_name"] == b["spec_name"]:
            continue

        total = float(a["peak_memory_mib"]) + float(b["peak_memory_mib"])

        if total > usable_capacity:
            skipped_capacity += 1
            continue

        pair_id = f"{Path(a['spec_name']).stem}__PLUS__{Path(b['spec_name']).stem}"

        rows.append(
            {
                "pair_id": pair_id,
                "spec_a": a["spec_path"],
                "spec_b": b["spec_path"],
                "spec_a_name": a["spec_name"],
                "spec_b_name": b["spec_name"],
                "mem_a_mib": f"{a['peak_memory_mib']:.3f}",
                "mem_b_mib": f"{b['peak_memory_mib']:.3f}",
                "total_mem_mib": f"{total:.3f}",
                "capacity_mib": f"{float(args.capacity_mib):.3f}",
                "guard_mib": f"{float(args.guard_mib):.3f}",
                "usable_capacity_mib": f"{usable_capacity:.3f}",
            }
        )

    fieldnames = [
        "pair_id",
        "spec_a",
        "spec_b",
        "spec_a_name",
        "spec_b_name",
        "mem_a_mib",
        "mem_b_mib",
        "total_mem_mib",
        "capacity_mib",
        "guard_mib",
        "usable_capacity_mib",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} Lucid pairwise candidates to {output_path}")
    print(f"Skipped {skipped_capacity} pairs exceeding usable capacity {usable_capacity:.0f} MiB")
    print(f"Skipped {len(missing_memory)} specs with missing memory profile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())