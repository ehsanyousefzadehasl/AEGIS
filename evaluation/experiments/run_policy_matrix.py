#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
from pathlib import Path

import yaml
import copy

import time

DEFAULT_CONFIG = "config.yaml"
DEFAULT_RESULTS_DIR = "evaluation/experiments/results"

def count_trace_tasks(trace_csv: str | None) -> int:
    if not trace_csv:
        return 0

    with Path(trace_csv).open() as f:
        return max(0, sum(1 for _ in f) - 1)
    
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run AEGIS policy matrix experiments.")
    p.add_argument("--launch", action="store_true", help="Launch each run with CONFIG_PATH.")
    p.add_argument("--main", default="main.py", help="Scheduler entrypoint.")
    p.add_argument("--base-config", default=DEFAULT_CONFIG)
    p.add_argument("--results-dir", default=DEFAULT_RESULTS_DIR)
    p.add_argument("--experiment-name", required=True)
    p.add_argument("--policies", nargs="+", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--trace-csv", help="Optional trace CSV to submit after launching main.py.")
    p.add_argument("--delay-scale", type=float, default=1.0)
    p.add_argument("--startup-wait-s", type=float, default=10.0)
    p.add_argument("--eval-idle-exit-minutes", type=float, default=2.0)
    p.add_argument(
        "--run-timeout-minutes",
        type=float,
        default=240.0,
        help="Maximum time to wait for each launched policy run.",
    )
    p.add_argument(
        "--estimators",
        nargs="+",
        default=["horus"],
        help="Estimators to use for estimator-based policies.",
    )
    return p.parse_args()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False))

def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> int:
    with stdout_path.open("w") as out, stderr_path.open("w") as err:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdout=out,
            stderr=err,
            text=True,
        )
        return proc.wait()
    

def start_process(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[subprocess.Popen, object, object]:
    out = stdout_path.open("w")
    err = stderr_path.open("w")
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=out,
        stderr=err,
        text=True,
    )
    return proc, out, err


def policy_estimators(policy: str, requested_estimators: list[str]) -> list[str]:
    policies_without_estimator = {
        "exclusive",
        "LUCID",
        "oracle-FF",
        "oracle-BF",
        "oracle-MAGM",
        "oracle-LUG",
        "OR-RR",
        "OR-MAGM",
        "OR-LUG",
        "PROFILED-BF",
        "PROFILED-MAGM",
        "PROFILED-LUG",
    }

    if policy in policies_without_estimator:
        return ["None"]

    if policy == "HORUS":
        return ["horus"]

    return requested_estimators


def run_label_for(policy: str, estimator: str) -> str:
    if estimator == "None":
        return policy
    return f"{policy}__{estimator}"

def build_run_dir(results_dir: Path, experiment_name: str, policy: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_policy = policy.replace("/", "_")
    return results_dir / experiment_name / stamp / safe_policy


def main() -> int:
    args = parse_args()

    base_config_path = Path(args.base_config)
    base_config = load_yaml(base_config_path)

    for policy in args.policies:
        for estimator in policy_estimators(policy, args.estimators):
            run_label = run_label_for(policy, estimator)
            run_dir = build_run_dir(Path(args.results_dir), args.experiment_name, run_label)

        if args.dry_run:
            print(f"DRY {policy}: {run_dir}")
            continue

        run_dir.mkdir(parents=True, exist_ok=True)

        cfg = copy.deepcopy(base_config)
        cfg.setdefault("mapper", {})
        cfg["mapper"]["policy"] = policy
        cfg["mapper"]["estimator"] = estimator

        runtime_dir = run_dir / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        telemetry_dir = runtime_dir / "telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)

        cfg.setdefault("recovery", {})
        cfg["recovery"]["dir"] = str(runtime_dir.resolve())

        run_config_path = run_dir / "config.yaml"
        write_yaml(run_config_path, cfg)

        metadata = {
            "experiment_name": args.experiment_name,
            "policy": policy,
            "git_commit": git_commit(),
            "base_config": str(base_config_path),
            "run_dir": str(run_dir),
            "command": ["python", "main.py"],
            "trace_csv": args.trace_csv,
            "delay_scale": args.delay_scale,
            "startup_wait_s": args.startup_wait_s,
            "run_timeout_minutes": args.run_timeout_minutes,
            "eval_idle_exit_minutes": args.eval_idle_exit_minutes,
            "expected_tasks": count_trace_tasks(args.trace_csv) if args.trace_csv else 0,
            "estimator": estimator,
            "run_label": run_label,
        }
        (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        shutil.copy2(base_config_path, run_dir / "base_config.yaml")

        if args.launch:
            env = os.environ.copy()
            env["CONFIG_PATH"] = str(run_config_path.resolve())

            env["AEGIS_TELEMETRY_DIR"] = str(telemetry_dir.resolve())
            metadata["telemetry_dir"] = str(telemetry_dir.resolve())

            if args.trace_csv:
                expected_tasks = count_trace_tasks(args.trace_csv)
                env["AEGIS_EVAL_MODE"] = "1"
                env["AEGIS_EXPECTED_TASKS"] = str(expected_tasks)
                env["AEGIS_EVAL_IDLE_EXIT_MINUTES"] = str(args.eval_idle_exit_minutes)
                metadata["expected_tasks"] = expected_tasks
                metadata["eval_idle_exit_minutes"] = args.eval_idle_exit_minutes

            command = ["python", args.main]
            metadata["command"] = command
            metadata["config_path"] = str(run_config_path.resolve())
            (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

            proc, out_handle, err_handle = start_process(
                command,
                cwd=Path.cwd(),
                env=env,
                stdout_path=run_dir / "stdout.log",
                stderr_path=run_dir / "stderr.log",
            )

            metadata["pid"] = proc.pid
            metadata["trace_csv"] = args.trace_csv
            (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

            print(f"STARTED {policy}: pid={proc.pid} dir={run_dir}")

            try:
                if args.trace_csv:
                    time.sleep(args.startup_wait_s)

                    submit_cmd = [
                        "python",
                        "evaluation/experiments/submit_trace.py",
                        "--trace-csv",
                        args.trace_csv,
                        "--delay-scale",
                        str(args.delay_scale),
                    ]

                    submit_rc = run_command(
                        submit_cmd,
                        cwd=Path.cwd(),
                        env=os.environ.copy(),
                        stdout_path=run_dir / "submit_stdout.log",
                        stderr_path=run_dir / "submit_stderr.log",
                    )

                    metadata["submit_command"] = submit_cmd
                    metadata["submit_return_code"] = submit_rc
                    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

                    print(f"SUBMITTED {policy}: submit_return_code={submit_rc}")

                try:
                    return_code = proc.wait(timeout=args.run_timeout_minutes * 60.0)
                    timed_out = False
                except subprocess.TimeoutExpired:
                    timed_out = True
                    proc.terminate()
                    try:
                        return_code = proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        return_code = proc.wait()

                metadata["return_code"] = return_code

                metadata["timed_out"] = timed_out
                metadata["run_timeout_minutes"] = args.run_timeout_minutes

                (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

                print(f"DONE {policy}: return_code={return_code} dir={run_dir}")

            finally:
                out_handle.close()
                err_handle.close()

        else:
            print(f"READY {policy}: {run_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())