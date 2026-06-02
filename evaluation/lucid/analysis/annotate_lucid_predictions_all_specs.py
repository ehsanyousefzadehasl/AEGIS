#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_PREDICTIONS = "evaluation/lucid/results/lucid_predictions_all_specs_with_tiny_safeguard.csv"
DEFAULT_SPEC_DIR = "evaluation/workloads/training/specs/yaml"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Annotate full workload YAML specs with Lucid predicted labels.")
    p.add_argument("--predictions-csv", default=DEFAULT_PREDICTIONS)
    p.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    p.add_argument("--write", action="store_true", help="Actually modify YAML files. Default is dry-run.")
    return p.parse_args()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def dump_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def main() -> int:
    args = parse_args()

    predictions = pd.read_csv(args.predictions_csv)

    required = {
        "spec_name",
        "lucid_final_class",
        "lucid_final_ss",
        "lucid_final_source",
    }
    missing_cols = sorted(required - set(predictions.columns))
    if missing_cols:
        raise ValueError(f"Missing required columns in predictions CSV: {missing_cols}")

    pred_by_name = {
        str(row["spec_name"]): row
        for _, row in predictions.iterrows()
    }

    spec_paths = sorted(Path(args.spec_dir).glob("*.yaml"))

    updated = 0
    missing = []

    for spec_path in spec_paths:
        row = pred_by_name.get(spec_path.name)
        if row is None:
            missing.append(spec_path.name)
            continue

        data = load_yaml(spec_path)
        profile = data.setdefault("profile", {})

        profile["lucid_class"] = str(row["lucid_final_class"])
        profile["lucid_ss"] = int(row["lucid_final_ss"])
        profile["lucid_label_source"] = str(row["lucid_final_source"])

        if "lucid_pred_class" in row and pd.notna(row["lucid_pred_class"]):
            profile["lucid_classifier_class"] = str(row["lucid_pred_class"])
        if "lucid_pred_ss" in row and pd.notna(row["lucid_pred_ss"]):
            profile["lucid_classifier_ss"] = int(row["lucid_pred_ss"])

        for col in [
            "lucid_pred_proba_ss0",
            "lucid_pred_proba_ss1",
            "lucid_pred_proba_ss2",
        ]:
            if col in row and pd.notna(row[col]):
                profile[col] = float(row[col])

        print(
            f"{'WRITE' if args.write else 'DRY'} {spec_path.name}: "
            f"{profile['lucid_class']} ss={profile['lucid_ss']} "
            f"source={profile['lucid_label_source']}"
        )

        if args.write:
            dump_yaml(spec_path, data)

        updated += 1

    print(f"\nMatched specs: {updated}")
    print(f"Missing predictions: {len(missing)}")
    for name in missing:
        print("MISSING", name)

    if missing:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())