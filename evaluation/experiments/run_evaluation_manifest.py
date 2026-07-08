#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an AEGIS evaluation manifest."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--launch",
        action="store_true",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError("Manifest root must be a mapping")

    return raw


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)

    experiment = str(manifest["experiment_name"])
    repetitions = int(manifest.get("repetitions", 1))
    common = manifest.get("runner", {})
    traces = manifest["traces"]
    configurations = manifest["configurations"]

    if repetitions <= 0:
        raise ValueError("repetitions must be positive")

    for repetition in range(1, repetitions + 1):
        for trace in traces:
            trace_name = str(trace["name"])
            trace_csv = str(trace["csv"])

            if not Path(trace_csv).is_file():
                raise FileNotFoundError(trace_csv)

            for configuration in configurations:
                label = str(configuration["label"])
                policy = str(configuration["policy"])
                estimator = str(
                    configuration.get("estimator", "None")
                )

                run_name = (
                    f"{experiment}__{trace_name}"
                    f"__rep{repetition:02d}__{label}"
                )

                command = [
                    "python",
                    "evaluation/experiments/run_policy_matrix.py",
                    "--experiment-name",
                    run_name,
                    "--policies",
                    policy,
                    "--estimators",
                    estimator,
                    "--trace-csv",
                    trace_csv,
                    "--base-config",
                    str(common.get("base_config", "config.yaml")),
                    "--results-dir",
                    str(
                        common.get(
                            "results_dir",
                            "evaluation/experiments/results",
                        )
                    ),
                    "--delay-scale",
                    str(common.get("delay_scale", 1.0)),
                    "--startup-wait-s",
                    str(common.get("startup_wait_s", 10.0)),
                    "--eval-idle-exit-minutes",
                    str(
                        common.get(
                            "eval_idle_exit_minutes",
                            2.0,
                        )
                    ),
                    "--run-timeout-minutes",
                    str(
                        common.get(
                            "run_timeout_minutes",
                            240.0,
                        )
                    ),
                ]

                if "risk_smact_threshold" in configuration:
                    command.extend([
                        "--risk-smact-threshold",
                        str(configuration["risk_smact_threshold"]),
                    ])
                if "risk_smocc_threshold" in configuration:
                    command.extend([
                        "--risk-smocc-threshold",
                        str(configuration["risk_smocc_threshold"]),
                    ])
                if "risk_drama_threshold" in configuration:
                    command.extend([
                        "--risk-drama-threshold",
                        str(configuration["risk_drama_threshold"]),
                    ])

                if args.launch:
                    command.append("--launch")
                else:
                    command.append("--dry-run")

                print(
                    f"\n[{repetition}/{repetitions}] "
                    f"{trace_name} / {label}"
                )
                print(" ".join(command))

                result = subprocess.run(command)

                if result.returncode != 0:
                    raise RuntimeError(
                        f"Run failed with code "
                        f"{result.returncode}: {run_name}"
                    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())