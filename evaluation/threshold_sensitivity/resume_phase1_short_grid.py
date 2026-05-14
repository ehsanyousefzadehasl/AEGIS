#!/usr/bin/env python3
from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path


OUTPUT_ROOT = Path("evaluation/threshold_sensitivity/results/phase1_short_grid")
PLAN_JSONL = "evaluation/threshold_sensitivity/manifests/phase1_short/progressive_trial_plan.jsonl"
SOLO_RUNTIME_CSV = (
    "evaluation/threshold_sensitivity/solo_runs/"
    "combined_1gpu_threshold_windows_with_llama_20260509_202117/"
    "live_threshold_measurements.csv"
)

TAU_SMACT_VALUES = [0.70, 0.75, 0.80, 0.85, 0.90]
TAU_SMOCC_VALUES = [0.35, 0.40, 0.45, 0.50]
TAU_DRAMA_VALUES = [0.30, 0.35, 0.40, 0.45]


def fmt(x: float) -> str:
    return f"{x:.2f}".replace(".", "p")


def has_completed_summary(output_dir: Path) -> bool:
    summary = output_dir / "progressive_trial_summary.csv"
    if not summary.exists() or summary.stat().st_size <= 100:
        return False

    text = summary.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
    # header + at least one trial row
    return len(text) >= 2


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    completed = 0
    attempted = 0
    failed = 0

    for tau_smact, tau_smocc, tau_drama in itertools.product(
        TAU_SMACT_VALUES,
        TAU_SMOCC_VALUES,
        TAU_DRAMA_VALUES,
    ):
        run_name = (
            f"smact_{fmt(tau_smact)}_"
            f"smocc_{fmt(tau_smocc)}_"
            f"drama_{fmt(tau_drama)}"
        )
        output_dir = OUTPUT_ROOT / run_name

        if has_completed_summary(output_dir):
            completed += 1
            print("[skip completed]", run_name, flush=True)
            continue

        attempted += 1
        print("\n== resume", run_name, flush=True)

        cmd = [
            sys.executable,
            "evaluation/threshold_sensitivity/run_progressive_threshold_trials.py",
            "--plan-jsonl", PLAN_JSONL,
            "--output-dir", str(output_dir),
            "--workdir", ".",
            "--execute-progressive-trial",
            "--cleanup-after-observation",
            "--window-seconds", "30.0",
            "--summary-windows", "30",
            "--ttfk-timeout", "300.0",
            "--window-timeout", "300.0",
            "--poll-seconds", "0.5",
            "--trial-timeout-seconds", "7200.0",
            "--solo-runtime-csv", SOLO_RUNTIME_CSV,
            "--tau-smact", str(tau_smact),
            "--tau-smocc", str(tau_smocc),
            "--tau-drama", str(tau_drama),
            "--limit-trials", "2",
        ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            failed += 1
            print(f"[failed] {run_name} return_code={e.returncode}", flush=True)
            continue

    print(
        f"\nresume complete: completed_skipped={completed} "
        f"attempted={attempted} failed={failed}",
        flush=True,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
