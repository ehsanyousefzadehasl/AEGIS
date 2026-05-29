#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import signal
import subprocess
import time
import uuid
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_MANIFEST = "evaluation/lucid/manifests/lucid_pairwise_manifest.csv"
DEFAULT_OUTPUT_DIR = "evaluation/lucid/results/solo_runs"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run bounded Lucid solo baselines from unique pairwise manifest specs.")
    p.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--gpu-id", required=True)
    p.add_argument("--timeout-s", type=float, default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--conda-prefix", default="")
    return p.parse_args()


def load_job_command(spec_path: str) -> tuple[str, str]:
    data = yaml.safe_load(Path(spec_path).read_text())
    job = data.get("job", {})
    return str(job["command"]), str(job.get("conda_env", ""))


def build_shell_command(command: str, *, conda_env: str, conda_prefix: str) -> str:
    if conda_prefix:
        return f"source {conda_prefix}/etc/profile.d/conda.sh && conda activate {conda_env} && {command}"
    if conda_env:
        return f"conda run -n {conda_env} {command}"
    return command


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


def completed_specs(index_path: Path) -> set[str]:
    if not index_path.exists():
        return set()
    df = pd.read_csv(index_path)
    if df.empty or "status" not in df.columns:
        return set()
    return set(df.loc[df["status"] == "finished", "spec_path"].dropna().astype(str))


def unique_specs_from_manifest(manifest_path: str) -> list[str]:
    df = pd.read_csv(manifest_path)
    specs = sorted(set(df["spec_a"].dropna().astype(str)) | set(df["spec_b"].dropna().astype(str)))
    return specs


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir)
    index_path = output_dir / "index.csv"
    done = completed_specs(index_path)

    launched = 0
    for spec_path in unique_specs_from_manifest(args.manifest):
        if spec_path in done:
            print(f"SKIP {spec_path}")
            continue

        if args.limit is not None and launched >= args.limit:
            break

        command, conda_env = load_job_command(spec_path)
        run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        spec_stem = Path(spec_path).stem
        run_dir = output_dir / spec_stem / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        out_log = run_dir / "out.log"
        err_log = run_dir / "err.log"

        started_at = time.time()
        row_base = {
            "run_id": run_id,
            "spec_path": spec_path,
            "spec_name": Path(spec_path).name,
            "status": "started",
            "gpu_id": str(args.gpu_id),
            "return_code": "",
            "elapsed_seconds": "",
            "run_dir": str(run_dir),
            "out_log": str(out_log),
            "err_log": str(err_log),
        }
        append_index_row(index_path, row_base)

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)

        shell_command = build_shell_command(
            command,
            conda_env=conda_env,
            conda_prefix=args.conda_prefix,
        )

        print(f"RUN {spec_path}")
        with out_log.open("w", encoding="utf-8") as out_f, err_log.open("w", encoding="utf-8") as err_f:
            proc = subprocess.Popen(
                shell_command,
                shell=True,
                executable="/bin/bash",
                stdout=out_f,
                stderr=err_f,
                env=env,
                preexec_fn=os.setsid,
            )

            timed_out = False
            try:
                if args.timeout_s is None:
                    return_code = proc.wait()
                else:
                    deadline = time.time() + float(args.timeout_s)
                    while time.time() < deadline:
                        if proc.poll() is not None:
                            break
                        time.sleep(1.0)

                    if proc.poll() is None:
                        timed_out = True
                        terminate_process_tree(proc)

                    return_code = proc.poll()
            except KeyboardInterrupt:
                terminate_process_tree(proc)
                finished_at = time.time()
                interrupted = dict(row_base)
                interrupted.update(
                    {
                        "status": "interrupted",
                        "return_code": proc.poll(),
                        "elapsed_seconds": f"{finished_at - started_at:.3f}",
                    }
                )
                append_index_row(index_path, interrupted)
                raise

        finished_at = time.time()
        finished = dict(row_base)
        finished.update(
            {
                "status": "timeout" if timed_out else "finished",
                "return_code": return_code,
                "elapsed_seconds": f"{finished_at - started_at:.3f}",
            }
        )
        append_index_row(index_path, finished)

        launched += 1

    print(f"Launched {launched} Lucid solo trials")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())