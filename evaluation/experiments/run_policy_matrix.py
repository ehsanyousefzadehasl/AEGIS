#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
from email import policy
import json
import shutil
import subprocess
from pathlib import Path

import yaml


DEFAULT_CONFIG = "config.yaml"
DEFAULT_RESULTS_DIR = "evaluation/experiments/results"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run AEGIS policy matrix experiments.")
    p.add_argument("--base-config", default=DEFAULT_CONFIG)
    p.add_argument("--results-dir", default=DEFAULT_RESULTS_DIR)
    p.add_argument("--experiment-name", required=True)
    p.add_argument("--policies", nargs="+", required=True)
    p.add_argument("--dry-run", action="store_true")
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


def build_run_dir(results_dir: Path, experiment_name: str, policy: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_policy = policy.replace("/", "_")
    return results_dir / experiment_name / stamp / safe_policy


def main() -> int:
    args = parse_args()

    base_config_path = Path(args.base_config)
    base_config = load_yaml(base_config_path)

    for policy in args.policies:
        run_dir = build_run_dir(Path(args.results_dir), args.experiment_name, policy)

        if args.dry_run:
            print(f"DRY {policy}: {run_dir}")
            continue

        run_dir.mkdir(parents=True, exist_ok=True)

        cfg = dict(base_config)
        cfg.setdefault("mapper", {})
        cfg["mapper"]["policy"] = policy

        run_config_path = run_dir / "config.yaml"
        write_yaml(run_config_path, cfg)

        metadata = {
            "experiment_name": args.experiment_name,
            "policy": policy,
            "git_commit": git_commit(),
            "base_config": str(base_config_path),
            "run_dir": str(run_dir),
            "command": ["python", "main.py"],
        }
        (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        shutil.copy2(base_config_path, run_dir / "base_config.yaml")

        print(f"READY {policy}: {run_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())