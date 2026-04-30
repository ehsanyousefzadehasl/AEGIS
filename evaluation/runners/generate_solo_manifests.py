#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = REPO_ROOT / "evaluation" / "workloads" / "training" / "specs" / "yaml"
MANIFEST_DIR = REPO_ROOT / "evaluation" / "profiling" / "solo" / "manifests"


def write_text_manifest(path: Path, items: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in sorted(items):
            f.write(str(item.relative_to(REPO_ROOT)) + "\n")


def profile_args_for_spec(spec_path: Path) -> str:
    return "--print_model_summary --summary_output {summary_path} --print_faketensor_estimate"


def write_profile_args_csv(path: Path, items: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["spec_path", "extra_profile_args"])
        writer.writeheader()
        for item in sorted(items):
            writer.writerow(
                {
                    "spec_path": str(item.relative_to(REPO_ROOT)),
                    "extra_profile_args": profile_args_for_spec(item),
                }
            )


def main() -> None:
    all_specs = sorted(SPECS_DIR.glob("*.yaml"))
    specs_1gpu = [p for p in all_specs if p.name.endswith("_1gpu.yaml")]
    specs_2gpu = [p for p in all_specs if p.name.endswith("_2gpu.yaml")]

    write_text_manifest(MANIFEST_DIR / "all_specs.txt", all_specs)
    write_text_manifest(MANIFEST_DIR / "all_specs_1gpu.txt", specs_1gpu)
    write_text_manifest(MANIFEST_DIR / "all_specs_2gpu.txt", specs_2gpu)
    write_profile_args_csv(MANIFEST_DIR / "profile_args.csv", all_specs)

    print(f"wrote {len(all_specs)} specs to {MANIFEST_DIR / 'all_specs.txt'}")
    print(f"wrote {len(specs_1gpu)} specs to {MANIFEST_DIR / 'all_specs_1gpu.txt'}")
    print(f"wrote {len(specs_2gpu)} specs to {MANIFEST_DIR / 'all_specs_2gpu.txt'}")
    print(f"wrote profiling args to {MANIFEST_DIR / 'profile_args.csv'}")


if __name__ == "__main__":
    main()