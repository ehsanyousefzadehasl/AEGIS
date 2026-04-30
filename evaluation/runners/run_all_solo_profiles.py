#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cmd(cmd: list[str]) -> None:
    print("\n>>>", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(REPO_ROOT))


def main() -> None:
    p = argparse.ArgumentParser(description="Run all solo profiling workloads.")
    p.add_argument("--gpu-1", default="0", help="CUDA_VISIBLE_DEVICES for 1-GPU specs")
    p.add_argument("--gpu-2", default="0,1", help="CUDA_VISIBLE_DEVICES for 2-GPU specs")
    p.add_argument("--skip-1gpu", action="store_true")
    p.add_argument("--skip-2gpu", action="store_true")
    args = p.parse_args()

    gen_specs_script = REPO_ROOT / "evaluation" / "runners" / "generate_solo_manifests.py"
    gen_profile_args_script = REPO_ROOT / "evaluation" / "runners" / "generate_profile_args_manifest.py"
    run_script = REPO_ROOT / "evaluation" / "runners" / "run_solo_profiles.py"

    manifests_dir = REPO_ROOT / "evaluation" / "profiling" / "solo" / "manifests"
    all_1gpu = manifests_dir / "all_specs_1gpu.txt"
    all_2gpu = manifests_dir / "all_specs_2gpu.txt"
    profile_1gpu = manifests_dir / "profile_args_1gpu.csv"
    profile_2gpu = manifests_dir / "profile_args_2gpu.csv"

    run_cmd([sys.executable, str(gen_specs_script)])
    run_cmd([sys.executable, str(gen_profile_args_script)])

    if not args.skip_1gpu:
        run_cmd([
            sys.executable,
            str(run_script),
            "--spec-list",
            str(all_1gpu),
            "--cuda-visible-devices",
            args.gpu_1,
            "--profile-manifest",
            str(profile_1gpu),
        ])

    if not args.skip_2gpu:
        run_cmd([
            sys.executable,
            str(run_script),
            "--spec-list",
            str(all_2gpu),
            "--cuda-visible-devices",
            args.gpu_2,
            "--profile-manifest",
            str(profile_2gpu),
        ])


if __name__ == "__main__":
    main()