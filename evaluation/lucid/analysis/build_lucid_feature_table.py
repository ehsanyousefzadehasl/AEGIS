#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_SPEC_DIR = "evaluation/workloads/training/specs/yaml_threshold_short"
DEFAULT_LABELS = "evaluation/lucid/results/lucid_labels.csv"
DEFAULT_OUTPUT = "evaluation/lucid/results/lucid_feature_table.csv"

FEATURE_COLUMNS_LUCID_FAITHFUL = [
    "peak_memory_mib",
    "memory_fraction",
    "horus_gpu_util_mean",
    "avg_drama",
    "amp_enabled",
]

FEATURE_COLUMNS_EXTENDED = [
    *FEATURE_COLUMNS_LUCID_FAITHFUL,
    "avg_smact",
    "avg_smocc",
    "horus_gpu_util_p95",
    "horus_gpu_util_max",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build feature table for Lucid-style classifier.")
    p.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    p.add_argument("--labels-csv", default=DEFAULT_LABELS)
    p.add_argument("--output-csv", default=DEFAULT_OUTPUT)
    p.add_argument("--gpu-capacity-mib", type=float, default=40960)
    p.add_argument(
        "--manifest-csv",
        default="evaluation/lucid/manifests/lucid_pairwise_manifest.csv",
    )
    return p.parse_args()


def canonical_spec_key(path: str | Path) -> str:
    name = Path(path).name
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


def command_has_amp(command: str) -> int:
    tokens = str(command).split()
    return int("--amp" in tokens)


def profile_value(profile: dict, key: str, default=None):
    value = profile.get(key, default)
    return value


def build_row(spec_path: Path, *, gpu_capacity_mib: float) -> dict:
    data = yaml.safe_load(spec_path.read_text())
    profile = data.get("profile", {}) or {}
    job = data.get("job", {}) or {}
    command = str(job.get("command", ""))

    peak_memory_mib = profile_value(profile, "peak_memory_mib")

    row = {
        "spec_name": spec_path.name,
        "spec_path": str(spec_path),
        "spec_key": canonical_spec_key(spec_path),
        "peak_memory_mib": peak_memory_mib,
        "memory_fraction": None if peak_memory_mib is None else float(peak_memory_mib) / float(gpu_capacity_mib),
        "horus_gpu_util_mean": profile_value(profile, "horus_gpu_util_mean"),
        "horus_gpu_util_p95": profile_value(profile, "horus_gpu_util_p95"),
        "horus_gpu_util_max": profile_value(profile, "horus_gpu_util_max"),
        "avg_smact": profile_value(profile, "avg_smact"),
        "avg_smocc": profile_value(profile, "avg_smocc"),
        "avg_drama": profile_value(profile, "avg_drama"),
        "amp_enabled": command_has_amp(command),
    }
    return row


def main() -> int:
    args = parse_args()

    manifest = pd.read_csv(args.manifest_csv)
    spec_paths = sorted(
        set(manifest["spec_a"].dropna().astype(str))
        | set(manifest["spec_b"].dropna().astype(str))
    )

    rows = [
        build_row(Path(p), gpu_capacity_mib=args.gpu_capacity_mib)
        for p in spec_paths
    ]

    features = pd.DataFrame(rows)

    labels = pd.read_csv(args.labels_csv)
    labels = labels.sort_values(
        ["lucid_label_usable", "lucid_num_pair_observations"],
        ascending=[False, False],
    ).drop_duplicates("spec_key", keep="first")
    
    out = features.merge(labels, on="spec_key", how="left", suffixes=("", "_label"))

    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_csv, index=False)

    print(f"Wrote {len(out)} rows to {args.output_csv}")
    print("Lucid-faithful features:", FEATURE_COLUMNS_LUCID_FAITHFUL)
    print("Extended features:", FEATURE_COLUMNS_EXTENDED)
    print(out[["spec_key", "lucid_label_source", "lucid_label_usable", "lucid_class", "lucid_ss"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())