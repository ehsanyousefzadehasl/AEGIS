#!/usr/bin/env python3
from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path

import pandas as pd


OUTPUT_ROOT = Path("evaluation/threshold_sensitivity/results/threshold_sweep_v1_fixed_grid")
PLAN_JSONL = "evaluation/threshold_sensitivity/manifests/threshold_sweep_v1_fixed/progressive_trial_plan.jsonl"
SOLO_RUNTIME_CSV = "evaluation/threshold_sensitivity/manifests/threshold_sweep_v1_solo_runtimes.csv"

# Start with a smaller, meaningful grid. We can expand later.
TAU_SMACT_VALUES = [0.95, 1.0]
TAU_SMOCC_VALUES = [0.95, 1.0]
TAU_DRAMA_VALUES = [0.95, 1.0]

EXPECTED_TRIALS = 5


def fmt(x: float) -> str:
    return f"{x:.2f}".replace(".", "p")


def has_completed_summary(output_dir: Path) -> bool:
    summary = output_dir / "progressive_trial_summary.csv"
    observations = output_dir / "admission_observations.csv"

    if not summary.exists() or not observations.exists():
        return False

    try:
        df = pd.read_csv(summary)
    except Exception:
        return False

    if len(df) != EXPECTED_TRIALS:
        return False

    required = [
        "trial_id",
        "planned_workload_count",
        "admitted_workload_count",
        "reject_retry_count",
        "solo_runtime_sum_seconds",
        "sequence_wall_time_seconds",
        "throughput_gain",
    ]

    return all(c in df.columns for c in required)


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
        print("\n== run", run_name, flush=True)

        cmd = [
            sys.executable,
            "evaluation/threshold_sensitivity/runners/run_progressive_threshold_trials.py",
            "--plan-jsonl", PLAN_JSONL,
            "--output-dir", str(output_dir),
            "--workdir", ".",
            "--execute-progressive-trial",
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
        ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            failed += 1
            print(f"[failed] {run_name} return_code={e.returncode}", flush=True)
            continue

    print(
        f"\nsweep complete: completed_skipped={completed} "
        f"attempted={attempted} failed={failed}",
        flush=True,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
