#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = REPO_ROOT / "evaluation" / "threshold_sensitivity" / "solo_runs"
LIVE_RUNNER = REPO_ROOT / "evaluation" / "threshold_sensitivity" / "live_threshold_runner.py"
DEFAULT_SUMMARY_WINDOWS = "5,10,20,30,40,60,120,200"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run threshold solo baselines from one workload spec or a manifest."
    )

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--spec", type=str, help="Path to one workload spec.")
    src.add_argument("--spec-list", type=str, help="Text file with one workload spec per line.")

    p.add_argument("--workdir", type=str, default=str(REPO_ROOT))
    p.add_argument("--runs-root", type=str, default=str(DEFAULT_RUNS_ROOT))
    p.add_argument("--suite-id", type=str, default=None)

    p.add_argument("--limit", type=int, default=None, help="Optional max number of specs to run.")

    p.add_argument("--gpu-id", type=str, default=None)
    p.add_argument("--gpu-uuid", type=str, default=None)

    p.add_argument(
        "--cuda-visible-devices",
        type=str,
        default=None,
        help="CUDA_VISIBLE_DEVICES value for launched workloads. Defaults to --gpu-id.",
    )

    p.add_argument("--user", default="threshold-exp")
    p.add_argument("--estimator", default="None")
    p.add_argument("--window-seconds", type=float, default=30.0)

    p.add_argument(
        "--summary-windows",
        default=DEFAULT_SUMMARY_WINDOWS,
        help=f"Comma-separated post-first-GPU-activity summary windows. Default: {DEFAULT_SUMMARY_WINDOWS}",
    )

    p.add_argument("--ttfk-timeout", type=float, default=300.0)
    p.add_argument("--window-timeout", type=float, default=900.0)
    p.add_argument("--finish-timeout", type=float, default=0.0)
    p.add_argument("--poll-seconds", type=float, default=0.5)

    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Write commands.jsonl but do not launch workloads.",
    )
    return p.parse_args()


def safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "._-+" else "_" for c in value)


def resolve_maybe_relative(path: Path, base: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (base / path).resolve()


def load_spec_paths(args: argparse.Namespace, repo_root: Path) -> list[Path]:
    if args.spec:
        return [resolve_maybe_relative(Path(args.spec), repo_root)]

    manifest = resolve_maybe_relative(Path(args.spec_list), repo_root)
    specs: list[Path] = []

    with manifest.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            specs.append(resolve_maybe_relative(Path(line), repo_root))

    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be positive.")
        specs = specs[: args.limit]

    return specs


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True, default=str) + "\n")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)


def build_live_runner_command(
    *,
    spec_path: Path,
    workdir: Path,
    run_id: str,
    event_path: Path,
    output_csv: Path,
    index_csv: Path,
    args: argparse.Namespace,
) -> list[str]:
    cmd = [
        sys.executable,
        str(LIVE_RUNNER),
        "--task",
        str(spec_path),
        "--workdir",
        str(workdir),
        "--user",
        args.user,
        "--estimator",
        args.estimator,
        "--window-seconds",
        str(args.window_seconds),
        "--summary-windows",
        args.summary_windows,
        "--ttfk-timeout",
        str(args.ttfk_timeout),
        "--window-timeout",
        str(args.window_timeout),
        "--finish-timeout",
        str(args.finish_timeout),
        "--poll-seconds",
        str(args.poll_seconds),
        "--event-path",
        str(event_path),
        "--output-csv",
        str(output_csv),
        "--index-csv",
        str(index_csv),
        "--run-id",
        run_id,
    ]

    if args.gpu_uuid is not None:
        cmd.extend(["--gpu-uuid", args.gpu_uuid])
        
    if args.gpu_id is not None:
        cmd.extend(["--gpu-id", args.gpu_id])

    if args.cuda_visible_devices is not None:
        cmd.extend(["--cuda-visible-devices", args.cuda_visible_devices])

    return cmd


def main() -> int:
    args = parse_args()

    if args.gpu_id is not None and args.gpu_uuid is not None:
        raise ValueError("Use only one of --gpu-id or --gpu-uuid.")

    repo_root = REPO_ROOT.resolve()
    workdir = resolve_maybe_relative(Path(args.workdir), repo_root)

    suite_id = args.suite_id or dt.datetime.now().strftime("solo_%Y-%m-%d_%H-%M-%S")
    suite_dir = resolve_maybe_relative(Path(args.runs_root), repo_root) / safe_name(suite_id)
    events_dir = suite_dir / "events"

    index_csv = suite_dir / "index.csv"
    output_csv = suite_dir / "live_threshold_measurements.csv"
    commands_jsonl = suite_dir / "commands.jsonl"
    metadata_json = suite_dir / "metadata.json"

    spec_paths = load_spec_paths(args, repo_root)

    write_json(
        metadata_json,
        {
            "suite_id": suite_id,
            "created_at": dt.datetime.now().isoformat(),
            "repo_root": str(repo_root),
            "workdir": str(workdir),
            "runs_root": str(resolve_maybe_relative(Path(args.runs_root), repo_root)),
            "suite_dir": str(suite_dir),
            "index_csv": str(index_csv),
            "output_csv": str(output_csv),
            "commands_jsonl": str(commands_jsonl),
            "num_specs": len(spec_paths),
            "gpu_id": args.gpu_id,
            "gpu_uuid": args.gpu_uuid,
            "window_seconds": args.window_seconds,
            "summary_windows": args.summary_windows,
            "limit": args.limit,
            "ttfk_timeout": args.ttfk_timeout,
            "window_timeout": args.window_timeout,
            "finish_timeout": args.finish_timeout,
            "poll_seconds": args.poll_seconds,
            "dry_run": args.dry_run,
        },
    )

    failures = 0

    for i, spec_path in enumerate(spec_paths, start=1):
        workload_name = safe_name(spec_path.stem)
        run_id = f"solo_{i:04d}_{workload_name}_{uuid.uuid4().hex[:8]}"
        event_path = events_dir / f"{run_id}.jsonl"

        cmd = build_live_runner_command(
            spec_path=spec_path,
            workdir=workdir,
            run_id=run_id,
            event_path=event_path,
            output_csv=output_csv,
            index_csv=index_csv,
            args=args,
        )

        append_jsonl(
            commands_jsonl,
            {
                "event": "threshold_solo_command_prepared",
                "timestamp": dt.datetime.now().isoformat(),
                "run_id": run_id,
                "spec_path": str(spec_path),
                "event_path": str(event_path),
                "window_seconds": args.window_seconds,
                "summary_windows": args.summary_windows,
                "command": cmd,
                "dry_run": args.dry_run,
            },
        )

        print(f"\n[{i}/{len(spec_paths)}] {spec_path}")
        print(" ".join(cmd))

        if args.dry_run:
            continue

        result = subprocess.run(cmd, cwd=str(repo_root), check=False)

        append_jsonl(
            commands_jsonl,
            {
                "event": "threshold_solo_command_finished",
                "timestamp": dt.datetime.now().isoformat(),
                "run_id": run_id,
                "spec_path": str(spec_path),
                "window_seconds": args.window_seconds,
                "summary_windows": args.summary_windows,
                "return_code": result.returncode,
            },
        )

        if result.returncode != 0:
            failures += 1

    print("\n========== THRESHOLD SOLO SUMMARY ==========")
    print(f"suite_dir={suite_dir}")
    print(f"index_csv={index_csv}")
    print(f"output_csv={output_csv}")
    print(f"commands_jsonl={commands_jsonl}")
    print(f"total_specs={len(spec_paths)}")
    print(f"window_seconds={args.window_seconds}")
    print(f"summary_windows={args.summary_windows}")
    print(f"runner_failures={failures}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())