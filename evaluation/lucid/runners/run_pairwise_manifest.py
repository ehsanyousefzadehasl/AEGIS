#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


DEFAULT_MANIFEST = "evaluation/lucid/manifests/lucid_pairwise_manifest.csv"
DEFAULT_OUTPUT_DIR = "evaluation/lucid/results/pairwise_runs"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Lucid pairwise profiling manifest with resume support.")
    p.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--gpu-id", required=True)
    p.add_argument("--timeout-s", type=float, default=None)
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--conda-prefix", default="")
    p.add_argument("--rerun-timeouts", action="store_true")
    return p.parse_args()


def completed_pair_ids(index_path: Path, *, rerun_timeouts: bool) -> set[str]:
    if not index_path.exists():
        return set()

    df = pd.read_csv(index_path)
    if df.empty or "pair_id" not in df.columns or "status" not in df.columns:
        return set()

    done_statuses = {"finished"}
    if not rerun_timeouts:
        done_statuses.add("timeout")

    done = df.loc[df["status"].isin(done_statuses), "pair_id"]
    return set(done.dropna().astype(str))


def main() -> int:
    args = parse_args()

    manifest = pd.read_csv(args.manifest)
    index_path = Path(args.output_dir) / "index.csv"
    done = completed_pair_ids(index_path, rerun_timeouts=args.rerun_timeouts)

    launched = 0

    for row_index, row in manifest.iloc[args.start_index :].iterrows():
        pair_id = str(row["pair_id"])

        if pair_id in done:
            print(f"SKIP row={row_index} pair_id={pair_id}")
            continue

        if args.limit is not None and launched >= args.limit:
            break

        cmd = [
            sys.executable,
            "evaluation/lucid/runners/run_pairwise_profile.py",
            "--manifest",
            args.manifest,
            "--output-dir",
            args.output_dir,
            "--row-index",
            str(row_index),
            "--gpu-id",
            str(args.gpu_id),
        ]

        if args.timeout_s is not None:
            cmd.extend(["--timeout-s", str(args.timeout_s)])

        if args.conda_prefix:
            cmd.extend(["--conda-prefix", args.conda_prefix])

        print(f"RUN row={row_index} pair_id={pair_id}")
        result = subprocess.run(cmd, check=False)
        launched += 1

        if result.returncode != 0:
            print(f"WARNING: row={row_index} pair_id={pair_id} exited with {result.returncode}")

    print(f"Launched {launched} Lucid pairwise trials")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())