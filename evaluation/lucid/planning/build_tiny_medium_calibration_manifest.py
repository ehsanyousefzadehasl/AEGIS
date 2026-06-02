#!/usr/bin/env python3
from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import pandas as pd


DEFAULT_OUTPUT = "evaluation/lucid/manifests/lucid_tiny_medium_calibration_manifest.csv"

SPEC_PATHS = [
    # Existing good-duration CIFAR specs.
    "evaluation/workloads/training/specs/yaml/mobilenet_cifar100_bs128_20e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml/mobilenet_cifar100_bs64_20e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml/resnet18_cifar100_bs64_20e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml/resnet34_cifar100_bs128_20e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml/resnet34_cifar100_bs64_20e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml/efficientnet_cifar100_bs128_20e_1gpu.yaml",

    # New shortened calibration specs.
    "evaluation/workloads/training/specs/yaml_lucid_calibration/efficientnet_cifar100_bs32_10e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml_lucid_calibration/efficientnet_cifar100_bs32_12e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml_lucid_calibration/efficientnet_cifar100_bs64_25e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml_lucid_calibration/mobilenet_cifar100_bs32_15e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml_lucid_calibration/resnet18_cifar100_bs32_25e_1gpu.yaml",
    "evaluation/workloads/training/specs/yaml_lucid_calibration/resnet34_cifar100_bs32_15e_1gpu.yaml",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Lucid Tiny/Medium calibration pairwise manifest.")
    p.add_argument("--output-csv", default=DEFAULT_OUTPUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    paths = [Path(p) for p in SPEC_PATHS]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing calibration specs: {missing}")

    rows = []
    for spec_a, spec_b in combinations(paths, 2):
        pair_id = f"{spec_a.stem}__PLUS__{spec_b.stem}"
        rows.append(
            {
                "pair_id": pair_id,
                "spec_a": str(spec_a),
                "spec_b": str(spec_b),
                "spec_a_name": spec_a.name,
                "spec_b_name": spec_b.name,
            }
        )

    out = pd.DataFrame(rows).sort_values("pair_id")
    output = Path(args.output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)

    print(f"num specs: {len(paths)}")
    print(f"num pairs: {len(out)}")
    print(f"wrote: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())