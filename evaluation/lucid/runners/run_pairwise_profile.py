#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import time
import uuid
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_MANIFEST = "evaluation/lucid/manifests/lucid_pairwise_manifest.csv"
DEFAULT_OUTPUT_DIR = "evaluation/lucid/results/pairwise_runs"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run one Lucid pairwise profiling trial without using the AEGIS scheduler."
    )
    p.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--gpu-id", required=True)
    p.add_argument("--row-index", type=int, default=None)
    p.add_argument("--pair-id", default=None)
    p.add_argument("--conda-prefix", default="")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def load_job_command(spec_path: str) -> tuple[str, str]:
    p = Path(spec_path)
    data = yaml.safe_load(p.read_text())

    job = data.get("job", {})
    command = job.get("command")
    conda_env = job.get("conda_env", "")

    if not command:
        raise ValueError(f"Missing job.command in {p}")

    return str(command), str(conda_env)


def select_manifest_row(df: pd.DataFrame, *, row_index: int | None, pair_id: str | None) -> pd.Series:
    if pair_id is not None:
        matches = df.loc[df["pair_id"] == pair_id]
        if matches.empty:
            raise ValueError(f"No manifest row found for pair_id={pair_id}")
        if len(matches) > 1:
            raise ValueError(f"Multiple manifest rows found for pair_id={pair_id}")
        return matches.iloc[0]

    if row_index is None:
        raise ValueError("Pass either --row-index or --pair-id")

    if row_index < 0 or row_index >= len(df):
        raise IndexError(f"row-index {row_index} out of range for manifest with {len(df)} rows")

    return df.iloc[row_index]


def build_shell_command(command: str, *, conda_env: str, conda_prefix: str) -> str:
    if conda_prefix:
        return f"source {conda_prefix}/etc/profile.d/conda.sh && conda activate {conda_env} && {command}"

    if conda_env:
        return f"conda run -n {conda_env} {command}"

    return command


def launch(
    *,
    command: str,
    conda_env: str,
    conda_prefix: str,
    gpu_id: str,
    out_log: Path,
    err_log: Path,
) -> subprocess.Popen:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    shell_command = build_shell_command(
        command,
        conda_env=conda_env,
        conda_prefix=conda_prefix,
    )

    out_f = out_log.open("w", encoding="utf-8")
    err_f = err_log.open("w", encoding="utf-8")

    return subprocess.Popen(
        shell_command,
        shell=True,
        executable="/bin/bash",
        stdout=out_f,
        stderr=err_f,
        env=env,
        preexec_fn=os.setsid,
    )


def terminate_process_tree(proc: subprocess.Popen, *, grace_s: float = 10.0) -> None:
    if proc.poll() is not None:
        return

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.time() + grace_s
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.2)

    if proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def append_index_row(index_path: Path, row: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    exists = index_path.exists()

    with index_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> int:
    args = parse_args()

    manifest = pd.read_csv(args.manifest)
    row = select_manifest_row(
        manifest,
        row_index=args.row_index,
        pair_id=args.pair_id,
    )

    spec_a = str(row["spec_a"])
    spec_b = str(row["spec_b"])
    command_a, conda_a = load_job_command(spec_a)
    command_b, conda_b = load_job_command(spec_b)

    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    pair_id = str(row["pair_id"])

    run_dir = Path(args.output_dir) / pair_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    out_a = run_dir / "out_a.log"
    err_a = run_dir / "err_a.log"
    out_b = run_dir / "out_b.log"
    err_b = run_dir / "err_b.log"
    metadata_path = run_dir / "metadata.json"

    metadata = {
        "run_id": run_id,
        "pair_id": pair_id,
        "gpu_id": str(args.gpu_id),
        "spec_a": spec_a,
        "spec_b": spec_b,
        "command_a": command_a,
        "command_b": command_b,
        "conda_env_a": conda_a,
        "conda_env_b": conda_b,
        "out_a": str(out_a),
        "err_a": str(err_a),
        "out_b": str(out_b),
        "err_b": str(err_b),
        "dry_run": bool(args.dry_run),
    }

    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if args.dry_run:
        print(json.dumps(metadata, indent=2))
        return 0

    started_at = time.time()
    proc_a = launch(
        command=command_a,
        conda_env=conda_a,
        conda_prefix=args.conda_prefix,
        gpu_id=str(args.gpu_id),
        out_log=out_a,
        err_log=err_a,
    )
    proc_b = launch(
        command=command_b,
        conda_env=conda_b,
        conda_prefix=args.conda_prefix,
        gpu_id=str(args.gpu_id),
        out_log=out_b,
        err_log=err_b,
    )

    try:
        return_a = proc_a.wait()
        return_b = proc_b.wait()
    except KeyboardInterrupt:
        terminate_process_tree(proc_a)
        terminate_process_tree(proc_b)
        raise

    finished_at = time.time()

    index_row = {
        "run_id": run_id,
        "pair_id": pair_id,
        "gpu_id": str(args.gpu_id),
        "spec_a": spec_a,
        "spec_b": spec_b,
        "return_code_a": return_a,
        "return_code_b": return_b,
        "elapsed_seconds": f"{finished_at - started_at:.3f}",
        "run_dir": str(run_dir),
        "metadata_path": str(metadata_path),
        "out_a": str(out_a),
        "err_a": str(err_a),
        "out_b": str(out_b),
        "err_b": str(err_b),
    }

    append_index_row(Path(args.output_dir) / "index.csv", index_row)

    print(json.dumps(index_row, indent=2))
    return 0 if return_a == 0 and return_b == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())