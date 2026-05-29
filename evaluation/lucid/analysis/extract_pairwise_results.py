#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


DEFAULT_INDEX = "evaluation/lucid/results/pairwise_runs/index.csv"
DEFAULT_SOLO = "evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv"
DEFAULT_OUTPUT = "evaluation/lucid/results/pairwise_results.csv"

TRAIN_TIME_RE = re.compile(r"training_loop_time_s:\s*([0-9.]+)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract Lucid pairwise normalized speeds from run logs.")
    p.add_argument("--index-csv", default=DEFAULT_INDEX)
    p.add_argument("--solo-profile-csv", default=DEFAULT_SOLO)
    p.add_argument("--output-csv", default=DEFAULT_OUTPUT)
    return p.parse_args()


def canonical_spec_name(path: str) -> str:
    name = Path(str(path)).name
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


def parse_training_time(log_path: str) -> float | None:
    p = Path(str(log_path))
    if not p.exists():
        return None

    text = p.read_text(errors="replace")
    matches = TRAIN_TIME_RE.findall(text)
    if not matches:
        return None

    return float(matches[-1])


def load_solo_times(path: str) -> dict[str, float]:
    df = pd.read_csv(path)

    required = {"spec_path", "training_loop_time_s"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")

    out: dict[str, float] = {}
    for _, row in df.iterrows():
        spec = canonical_spec_name(row["spec_path"])
        val = row["training_loop_time_s"]
        if pd.isna(val):
            continue
        out[spec] = float(val)

    return out


def main() -> int:
    args = parse_args()

    index = pd.read_csv(args.index_csv)
    solo_times = load_solo_times(args.solo_profile_csv)

    finished = index.loc[index["status"] == "finished"].copy()

    rows = []
    for _, row in finished.iterrows():
        spec_a = str(row["spec_a"])
        spec_b = str(row["spec_b"])

        spec_a_key = canonical_spec_name(spec_a)
        spec_b_key = canonical_spec_name(spec_b)

        solo_a = solo_times.get(spec_a_key)
        solo_b = solo_times.get(spec_b_key)

        pair_a = parse_training_time(str(row["out_a"]))
        pair_b = parse_training_time(str(row["out_b"]))

        norm_a = solo_a / pair_a if solo_a and pair_a and pair_a > 0 else None
        norm_b = solo_b / pair_b if solo_b and pair_b and pair_b > 0 else None

        rows.append(
            {
                "run_id": row["run_id"],
                "pair_id": row["pair_id"],
                "spec_a": spec_a,
                "spec_b": spec_b,
                "spec_a_key": spec_a_key,
                "spec_b_key": spec_b_key,
                "solo_time_a_s": solo_a,
                "solo_time_b_s": solo_b,
                "pair_time_a_s": pair_a,
                "pair_time_b_s": pair_b,
                "normalized_speed_a": norm_a,
                "normalized_speed_b": norm_b,
                "return_code_a": row.get("return_code_a", ""),
                "return_code_b": row.get("return_code_b", ""),
                "run_dir": row.get("run_dir", ""),
            }
        )

    out = pd.DataFrame(rows)
    output = Path(args.output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)

    print(f"Wrote {len(out)} rows to {output}")
    if not out.empty:
        print(out.head().to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())