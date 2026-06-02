#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = "evaluation/lucid/results/pairwise_results.csv"
DEFAULT_OUTPUT = "evaluation/lucid/results/lucid_labels.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Lucid Tiny/Medium/Jumbo labels from pairwise normalized speeds.")
    p.add_argument("--input-csv", default=DEFAULT_INPUT)
    p.add_argument("--output-csv", default=DEFAULT_OUTPUT)
    p.add_argument("--tiny-threshold", type=float, default=0.95)
    p.add_argument("--medium-threshold", type=float, default=0.85)
    p.add_argument("--min-partner-runtime-ratio", type=float, default=0.8)
    p.add_argument(
        "--observations-output-csv",
        default="evaluation/lucid/results/lucid_label_observations.csv",
    )
    p.add_argument("--min-valid-observations", type=int, default=5)
    return p.parse_args()


def classify(mean_speed: float, *, tiny_threshold: float, medium_threshold: float) -> tuple[str, int]:
    if mean_speed >= tiny_threshold:
        return "tiny", 0
    if mean_speed >= medium_threshold:
        return "medium", 1
    return "jumbo", 2


def main() -> int:
    args = parse_args()
    df = pd.read_csv(args.input_csv)

    observations = []

    for _, row in df.iterrows():
        pair_time_a = float(row["pair_time_a_s"])
        pair_time_b = float(row["pair_time_b_s"])

        partner_ratio_for_a = pair_time_b / pair_time_a if pair_time_a > 0 else 0.0
        partner_ratio_for_b = pair_time_a / pair_time_b if pair_time_b > 0 else 0.0

        observations.append(
            {
                "spec_key": row["spec_a_key"],
                "spec_path": row["spec_a"],
                "normalized_speed": row["normalized_speed_a"],
                "partner_spec_key": row["spec_b_key"],
                "pair_id": row["pair_id"],
                "pair_time_s": pair_time_a,
                "partner_pair_time_s": pair_time_b,
                "partner_runtime_ratio": partner_ratio_for_a,
                "valid_for_label": partner_ratio_for_a >= args.min_partner_runtime_ratio,
            }
        )

        observations.append(
            {
                "spec_key": row["spec_b_key"],
                "spec_path": row["spec_b"],
                "normalized_speed": row["normalized_speed_b"],
                "partner_spec_key": row["spec_a_key"],
                "pair_id": row["pair_id"],
                "pair_time_s": pair_time_b,
                "partner_pair_time_s": pair_time_a,
                "partner_runtime_ratio": partner_ratio_for_b,
                "valid_for_label": partner_ratio_for_b >= args.min_partner_runtime_ratio,
            }
        )

    obs = pd.DataFrame(observations)
    obs = obs.dropna(subset=["normalized_speed"])

    obs.to_csv(args.observations_output_csv, index=False)
    obs = obs[obs["valid_for_label"]].copy()

    rows = []
    for spec_key, group in obs.groupby("spec_key", sort=True):
        speeds = group["normalized_speed"].astype(float)
        mean_speed = float(speeds.mean())
        lucid_class, lucid_ss = classify(
            mean_speed,
            tiny_threshold=args.tiny_threshold,
            medium_threshold=args.medium_threshold,
        )

        label_source = (
            "measured_pairwise"
            if int(len(speeds)) >= args.min_valid_observations
            else "insufficient_pairwise"
        )

        rows.append(
            {
                "spec_key": spec_key,
                "representative_spec_path": group["spec_path"].iloc[0],
                "lucid_mean_normalized_speed": mean_speed,
                "lucid_std_normalized_speed": float(speeds.std(ddof=0)),
                "lucid_min_normalized_speed": float(speeds.min()),
                "lucid_max_normalized_speed": float(speeds.max()),
                "lucid_num_pair_observations": int(len(speeds)),
                "lucid_class": lucid_class,
                "lucid_ss": lucid_ss,
                "lucid_label_source": label_source,
                "lucid_label_usable": label_source == "measured_pairwise",
            }
        )

    out = pd.DataFrame(rows).sort_values("spec_key")
    output = Path(args.output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)

    print(f"Wrote {len(out)} Lucid labels to {output}")
    print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())