#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_LABELS = "evaluation/lucid/results/lucid_final_labels.csv"
DEFAULT_MANIFEST = "evaluation/lucid/manifests/lucid_pairwise_manifest.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Annotate YAML specs with final Lucid labels.")
    p.add_argument("--labels-csv", default=DEFAULT_LABELS)
    p.add_argument("--manifest-csv", default=DEFAULT_MANIFEST)
    p.add_argument("--write", action="store_true", help="Actually modify YAML files. Default is dry-run.")
    return p.parse_args()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def dump_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False))

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

def main() -> int:
    args = parse_args()

    labels = pd.read_csv(args.labels_csv)
    manifest = pd.read_csv(args.manifest_csv)

    label_by_key = {
        str(row["spec_key"]): row
        for _, row in labels.iterrows()
    }

    spec_paths = sorted(
        set(manifest["spec_a"].dropna().astype(str))
        | set(manifest["spec_b"].dropna().astype(str))
    )

    updated = 0
    missing = []

    for spec_path_str in spec_paths:
        spec_path = Path(spec_path_str)
        data = load_yaml(spec_path)

        profile = data.setdefault("profile", {})
        spec_key = None

        # Match by exact spec_key using the same key already stored in final labels.
        # The final labels table already contains canonical keys for these manifest specs.
        for key in label_by_key:
            if key == Path(spec_path).name:
                spec_key = key
                break

        if spec_key is None:
            spec_key = canonical_spec_key(spec_path)

        if spec_key not in label_by_key:
            missing.append(str(spec_path))
            continue

        row = label_by_key[spec_key]

        profile["lucid_class"] = str(row["lucid_final_class"])
        profile["lucid_ss"] = int(row["lucid_final_ss"])
        profile["lucid_label_source"] = str(row["lucid_final_label_source"])

        if "lucid_mean_normalized_speed" in row and pd.notna(row["lucid_mean_normalized_speed"]):
            profile["lucid_mean_normalized_speed"] = float(row["lucid_mean_normalized_speed"])

        if "lucid_num_pair_observations" in row and pd.notna(row["lucid_num_pair_observations"]):
            profile["lucid_num_pair_observations"] = int(row["lucid_num_pair_observations"])

        print(
            f"{'WRITE' if args.write else 'DRY'} {spec_path.name}: "
            f"{profile['lucid_class']} ss={profile['lucid_ss']} "
            f"source={profile['lucid_label_source']}"
        )

        if args.write:
            dump_yaml(spec_path, data)

        updated += 1

    print(f"\nMatched specs: {updated}")
    print(f"Missing labels: {len(missing)}")
    for path in missing:
        print("MISSING", path)

    if missing:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())