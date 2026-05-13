#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_OUTPUT_ROOT = Path("evaluation/threshold_sensitivity/progressive_sweeps")


def parse_float_list(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def format_threshold(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run progressive threshold trials over a grid of threshold values."
    )
    p.add_argument("--plan-jsonl", required=True)
    p.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    p.add_argument("--workdir", default=".")
    p.add_argument("--solo-runtime-csv", required=True)

    p.add_argument("--tau-smact-values", default="0.70,0.75,0.80,0.85,0.90")
    p.add_argument("--tau-smocc-values", default="0.35,0.40,0.45,0.50")
    p.add_argument("--tau-drama-values", default="0.30,0.35,0.40,0.45")

    p.add_argument("--window-seconds", type=float, default=30.0)
    p.add_argument("--summary-windows", default="30")
    p.add_argument("--ttfk-timeout", type=float, default=300.0)
    p.add_argument("--window-timeout", type=float, default=300.0)
    p.add_argument("--poll-seconds", type=float, default=0.5)
    p.add_argument("--trial-timeout-seconds", type=float, default=7200.0)

    p.add_argument("--limit-trials", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    tau_smact_values = parse_float_list(args.tau_smact_values)
    tau_smocc_values = parse_float_list(args.tau_smocc_values)
    tau_drama_values = parse_float_list(args.tau_drama_values)

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    grid = list(itertools.product(tau_smact_values, tau_smocc_values, tau_drama_values))

    metadata = {
        "plan_jsonl": args.plan_jsonl,
        "solo_runtime_csv": args.solo_runtime_csv,
        "tau_smact_values": tau_smact_values,
        "tau_smocc_values": tau_smocc_values,
        "tau_drama_values": tau_drama_values,
        "num_threshold_settings": len(grid),
        "window_seconds": args.window_seconds,
        "trial_timeout_seconds": args.trial_timeout_seconds,
    }
    (output_root / "sweep_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    for tau_smact, tau_smocc, tau_drama in grid:
        run_name = (
            f"smact_{format_threshold(tau_smact)}_"
            f"smocc_{format_threshold(tau_smocc)}_"
            f"drama_{format_threshold(tau_drama)}"
        )
        output_dir = output_root / run_name

        cmd = [
            sys.executable,
            "evaluation/threshold_sensitivity/run_progressive_threshold_trials.py",
            "--plan-jsonl",
            args.plan_jsonl,
            "--output-dir",
            str(output_dir),
            "--workdir",
            args.workdir,
            "--execute-progressive-trial",
            "--cleanup-after-observation",
            "--window-seconds",
            str(args.window_seconds),
            "--summary-windows",
            args.summary_windows,
            "--ttfk-timeout",
            str(args.ttfk_timeout),
            "--window-timeout",
            str(args.window_timeout),
            "--poll-seconds",
            str(args.poll_seconds),
            "--trial-timeout-seconds",
            str(args.trial_timeout_seconds),
            "--solo-runtime-csv",
            args.solo_runtime_csv,
            "--tau-smact",
            str(tau_smact),
            "--tau-smocc",
            str(tau_smocc),
            "--tau-drama",
            str(tau_drama),
        ]

        if args.limit_trials is not None:
            cmd.extend(["--limit-trials", str(args.limit_trials)])

        print("\n==", run_name, flush=True)
        print(" ".join(cmd), flush=True)

        if args.dry_run:
            continue

        try:
            completed = subprocess.run(cmd, check=True)
            status = {
                "run_name": run_name,
                "tau_smact": tau_smact,
                "tau_smocc": tau_smocc,
                "tau_drama": tau_drama,
                "status": "completed",
                "return_code": completed.returncode,
            }
        except subprocess.CalledProcessError as e:
            status = {
                "run_name": run_name,
                "tau_smact": tau_smact,
                "tau_smocc": tau_smocc,
                "tau_drama": tau_drama,
                "status": "failed",
                "return_code": e.returncode,
                "cmd": e.cmd,
            }

            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "sweep_failure.json").write_text(
                json.dumps(status, indent=2, default=str),
                encoding="utf-8",
            )

            print(
                f"[warning] threshold setting failed, continuing: {run_name}",
                flush=True,
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "sweep_status.json").write_text(
            json.dumps(status, indent=2, default=str),
            encoding="utf-8",
        )

    print(f"\nwrote sweep outputs under {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())