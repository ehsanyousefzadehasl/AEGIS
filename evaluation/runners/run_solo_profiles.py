#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workload.yaml_job_spec import load_yaml_job_spec


# Keep the currently-known-working DCGM list as default.
# You can later trim it with --dcgm-fields or skip it with --skip-dcgm.
DEFAULT_DCGM_FIELDS = "203,1001,1002,1003,1006,1007,1008,1004,204,1005,1009,1010,1011,1012,155,156"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run workload specs solo and collect runtime + monitoring logs."
    )

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--spec", type=str, help="Path to one workload spec YAML.")
    src.add_argument(
        "--spec-list",
        type=str,
        help="Text file with one spec path per line. Blank lines and # comments ignored.",
    )

    p.add_argument(
        "--profile-manifest",
        type=str,
        default=None,
        help=(
            "Optional CSV mapping spec paths to extra per-spec profiling args. "
            "Columns: spec_path,extra_profile_args"
        ),
    )

    p.add_argument("--repo-root", type=str, default=str(REPO_ROOT))
    p.add_argument(
        "--runs-root",
        type=str,
        default=str(REPO_ROOT / "evaluation" / "profiling" / "solo" / "runs"),
    )
    p.add_argument("--cuda-visible-devices", type=str, default="0")
    p.add_argument("--interval-sec", type=float, default=1.0)

    p.add_argument("--skip-smi", action="store_true")
    p.add_argument("--skip-dcgm", action="store_true")
    p.add_argument("--skip-pmon", action="store_true")
    p.add_argument("--skip-top", action="store_true")

    p.add_argument("--dcgm-fields", type=str, default=DEFAULT_DCGM_FIELDS)

    p.add_argument(
        "--global-extra-args",
        type=str,
        default="",
        help=(
            "Extra args appended to every command. Supports placeholders: "
            "{run_dir}, {artifacts_dir}, {summary_path}, {faketensor_path}, "
            "{output_dir}, {workload_id}"
        ),
    )
    return p.parse_args()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in "._-+" else "_" for c in s)


def ensure_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required binary not found in PATH: {name}")
    return path


def load_spec_paths(args: argparse.Namespace) -> list[Path]:
    if args.spec:
        return [resolve_maybe_relative(Path(args.spec), Path(args.repo_root))]

    out: list[Path] = []
    with open(args.spec_list, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            out.append(resolve_maybe_relative(Path(line), Path(args.repo_root)))
    return out


def resolve_maybe_relative(path: Path, base: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (base / path).resolve()


def load_profile_manifest(path: str | None, repo_root: Path) -> dict[str, str]:
    if not path:
        return {}

    manifest_path = resolve_maybe_relative(Path(path), repo_root)
    mapping: dict[str, str] = {}

    with open(manifest_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "spec_path" not in reader.fieldnames or "extra_profile_args" not in reader.fieldnames:
            raise ValueError(
                f"{manifest_path} must contain columns: spec_path,extra_profile_args"
            )
        for row in reader:
            spec_path = resolve_maybe_relative(Path(row["spec_path"]), repo_root)
            mapping[str(spec_path)] = (row.get("extra_profile_args") or "").strip()

    return mapping


def resolve_conda_prefix(conda_env: str) -> tuple[list[str], str]:
    env_text = str(conda_env).strip() or "tf"
    conda_exe = os.environ.get("CONDA_EXE", "conda")

    if "/" in env_text or env_text.startswith("."):
        return ([conda_exe, "run", "--no-capture-output", "-p", env_text], env_text)

    default_prefix = f"/opt/miniconda3/envs/{env_text}"
    if Path(default_prefix).exists():
        return (
            [conda_exe, "run", "--no-capture-output", "-p", default_prefix],
            default_prefix,
        )

    return ([conda_exe, "run", "--no-capture-output", "-n", env_text], env_text)


def format_extra_args(template: str, placeholders: dict[str, str]) -> list[str]:
    if not template.strip():
        return []
    rendered = template.format(**placeholders)
    return shlex.split(rendered)

def current_uuid_map_by_index() -> dict[int, str]:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,uuid",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        return {}

    mapping: dict[int, str] = {}
    for line in out.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            idx = int(parts[0])
        except ValueError:
            continue
        mapping[idx] = parts[1]
    return mapping


def build_run_context(
    spec_path: Path,
    runs_root: Path,
    profile_manifest_map: dict[str, str],
    global_extra_args: str,
) -> dict[str, Any]:
    data = load_yaml_job_spec(spec_path)

    version = data.get("version")
    job = data.get("job", {})
    resources = data.get("resources", {})
    estimates = data.get("estimates", {})
    profile = data.get("profile", {})
    online_estimation = data.get("online_estimation", {})

    if "command" not in job:
        raise ValueError(f"Spec missing job.command: {spec_path}")

    workload_id = safe_name(spec_path.stem)
    run_id = f"{now_str()}_{uuid.uuid4().hex[:8]}"

    run_dir = runs_root / workload_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    artifacts_dir = run_dir / "artifacts"
    summary_dir = artifacts_dir / "summary"
    faketensor_dir = artifacts_dir / "faketensor"
    output_dir = artifacts_dir / "outputs"

    summary_dir.mkdir(parents=True, exist_ok=True)
    faketensor_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = summary_dir / "summary.txt"
    faketensor_path = faketensor_dir / "faketensor.txt"

    placeholders = {
        "run_dir": str(run_dir),
        "artifacts_dir": str(artifacts_dir),
        "summary_path": str(summary_path),
        "faketensor_path": str(faketensor_path),
        "output_dir": str(output_dir),
        "workload_id": workload_id,
    }

    raw_command = str(job["command"]).strip()
    cmd_tokens = shlex.split(raw_command)

    per_spec_extra = profile_manifest_map.get(str(spec_path.resolve()), "")
    cmd_tokens += format_extra_args(global_extra_args, placeholders)
    cmd_tokens += format_extra_args(per_spec_extra, placeholders)

    conda_prefix, resolved_env = resolve_conda_prefix(str(job.get("conda_env", "tf")))

    return {
        "spec_path": str(spec_path),
        "version": version,
        "job": job,
        "resources": resources,
        "estimates": estimates,
        "profile": profile,
        "online_estimation": online_estimation,
        "workload_id": workload_id,
        "run_id": run_id,
        "run_dir": run_dir,
        "artifacts_dir": artifacts_dir,
        "summary_path": summary_path,
        "faketensor_path": faketensor_path,
        "output_dir": output_dir,
        "raw_command": raw_command,
        "command_tokens": cmd_tokens,
        "conda_prefix": conda_prefix,
        "resolved_env": resolved_env,
        "per_spec_extra_args": per_spec_extra,
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)


def append_index_row(index_csv: Path, row: dict[str, Any]) -> None:
    index_csv.parent.mkdir(parents=True, exist_ok=True)
    exists = index_csv.exists()
    with open(index_csv, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def monitor_nvidia_smi(
    stop_evt: threading.Event,
    log_path: Path,
    smi_path: str,
    interval: float,
) -> None:
    query = [
        "timestamp",
        "uuid",
        "utilization.gpu",
        "utilization.memory",
        "memory.used",
        "memory.free",
        "memory.total",
        "power.draw",
        "temperature.gpu",
    ]
    cmd = [
        smi_path,
        "--query-gpu=" + ",".join(query),
        "--format=csv,noheader,nounits",
    ]

    with open(log_path, "w", encoding="utf-8", buffering=1) as f:
        f.write(",".join(query) + "\n")
        while not stop_evt.is_set():
            try:
                out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", errors="replace")
            except subprocess.CalledProcessError as e:
                out = e.output.decode("utf-8", errors="replace")
            for line in out.strip().splitlines():
                if line.strip():
                    f.write(line.strip() + "\n")
            stop_evt.wait(interval)


def monitor_dcgm(
    stop_evt: threading.Event,
    log_path: Path,
    dcgmi_path: str,
    fields: str,
    interval: float,
) -> None:
    cmd = [dcgmi_path, "dmon", "-e", fields, "-c", "1"]

    with open(log_path, "w", encoding="utf-8", buffering=1) as f:
        f.write(f"# command: {' '.join(cmd)}\n")
        while not stop_evt.is_set():
            ts = datetime.now().isoformat()
            f.write(f"\n# timestamp: {ts}\n")
            try:
                out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", errors="replace")
            except subprocess.CalledProcessError as e:
                out = e.output.decode("utf-8", errors="replace")
            f.write(out.rstrip() + "\n")
            stop_evt.wait(interval)


def monitor_pmon(
    stop_evt: threading.Event,
    log_path: Path,
    smi_path: str,
    interval: float,
) -> None:
    cmd = [smi_path, "pmon", "-s", "um", "-c", "1"]

    with open(log_path, "w", encoding="utf-8", buffering=1) as f:
        f.write(f"# command: {' '.join(cmd)}\n")
        while not stop_evt.is_set():
            ts = datetime.now().isoformat()
            f.write(f"\n# timestamp: {ts}\n")
            try:
                out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", errors="replace")
            except subprocess.CalledProcessError as e:
                out = e.output.decode("utf-8", errors="replace")
            f.write(out.rstrip() + "\n")
            stop_evt.wait(interval)


def monitor_top(
    stop_evt: threading.Event,
    log_path: Path,
    pid: int,
    interval: float,
) -> None:
    with open(log_path, "w", encoding="utf-8", buffering=1) as f:
        while not stop_evt.is_set():
            ts = datetime.now().isoformat()
            f.write(f"\n# timestamp: {ts}\n")
            cmd = ["top", "-b", "-n", "1", "-p", str(pid), "-w", "512"]
            try:
                out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", errors="replace")
            except subprocess.CalledProcessError as e:
                out = e.output.decode("utf-8", errors="replace")
            f.write(out.rstrip() + "\n")
            stop_evt.wait(interval)


def start_monitors(
    args: argparse.Namespace,
    run_dir: Path,
    pid: int,
) -> tuple[threading.Event, list[threading.Thread]]:
    stop_evt = threading.Event()
    threads: list[threading.Thread] = []

    if not args.skip_smi:
        smi_path = ensure_binary("nvidia-smi")
        t = threading.Thread(
            target=monitor_nvidia_smi,
            args=(stop_evt, run_dir / "nvidia_smi.csv", smi_path, args.interval_sec),
            daemon=True,
        )
        t.start()
        threads.append(t)

    if not args.skip_dcgm:
        dcgmi_path = ensure_binary("dcgmi")
        t = threading.Thread(
            target=monitor_dcgm,
            args=(stop_evt, run_dir / "dcgm.log", dcgmi_path, args.dcgm_fields, args.interval_sec),
            daemon=True,
        )
        t.start()
        threads.append(t)

    if not args.skip_pmon:
        smi_path = ensure_binary("nvidia-smi")
        t = threading.Thread(
            target=monitor_pmon,
            args=(stop_evt, run_dir / "pmon.log", smi_path, args.interval_sec),
            daemon=True,
        )
        t.start()
        threads.append(t)

    if not args.skip_top:
        t = threading.Thread(
            target=monitor_top,
            args=(stop_evt, run_dir / "top.log", pid, args.interval_sec),
            daemon=True,
        )
        t.start()
        threads.append(t)

    return stop_evt, threads


def extract_faketensor_from_stdout(stdout_path: Path, faketensor_path: Path) -> None:
    if faketensor_path.exists() and faketensor_path.stat().st_size > 0:
        return
    if not stdout_path.exists():
        return

    matches: list[str] = []
    with open(stdout_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "faketensor" in line.lower():
                matches.append(line.rstrip())

    if matches:
        write_text(faketensor_path, "\n".join(matches) + "\n")


def run_one_spec(
    args: argparse.Namespace,
    spec_path: Path,
    runs_root: Path,
    profile_manifest_map: dict[str, str],
) -> int:
    ctx = build_run_context(spec_path, runs_root, profile_manifest_map, args.global_extra_args)
    run_dir: Path = ctx["run_dir"]

    command_tokens = ctx["conda_prefix"] + ctx["command_tokens"]
    cmd_text = " ".join(shlex.quote(x) for x in command_tokens)

    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    exitcode_path = run_dir / "exitcode.txt"
    time_path = run_dir / "time.json"

    write_text(run_dir / "command.txt", cmd_text + "\n")

    visible_gpu_indices = []
    for tok in str(args.cuda_visible_devices).split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            visible_gpu_indices.append(int(tok))
        except ValueError:
            pass

    uuid_map = current_uuid_map_by_index()
    assigned_gpu_uuids = [uuid_map[i] for i in visible_gpu_indices if i in uuid_map]

    meta = {
        "spec_path": ctx["spec_path"],
        "version": ctx["version"],
        "workload_id": ctx["workload_id"],
        "run_id": ctx["run_id"],
        "repo_root": str(Path(args.repo_root).resolve()),
        "assigned_gpu_indices": visible_gpu_indices,
        "assigned_gpu_uuids": assigned_gpu_uuids,
        "cuda_visible_devices": args.cuda_visible_devices,
        "resolved_env": ctx["resolved_env"],
        "raw_command": ctx["raw_command"],
        "per_spec_extra_args": ctx["per_spec_extra_args"],
        "final_command_tokens": command_tokens,
        "resources": ctx["resources"],
        "estimates": ctx["estimates"],
        "profile": ctx["profile"],
        "online_estimation": ctx["online_estimation"],
        "reserved_paths": {
            "artifacts_dir": str(ctx["artifacts_dir"]),
            "summary_path": str(ctx["summary_path"]),
            "faketensor_path": str(ctx["faketensor_path"]),
            "output_dir": str(ctx["output_dir"]),
        },
    }
    write_json(run_dir / "meta.json", meta)

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.cuda_visible_devices

    print(f"\n=== starting: {ctx['workload_id']}")
    print(f"    spec: {spec_path}")
    print(f"    run dir: {run_dir}")

    t0 = time.monotonic()
    wall_start = datetime.now().isoformat()

    with open(stdout_path, "w", encoding="utf-8", buffering=1) as out_f, open(
        stderr_path, "w", encoding="utf-8", buffering=1
    ) as err_f:
        proc = subprocess.Popen(
            command_tokens,
            cwd=str(Path(args.repo_root).resolve()),
            env=env,
            stdout=out_f,
            stderr=err_f,
            text=True,
        )

        stop_evt, threads = start_monitors(args, run_dir, proc.pid)

        try:
            rc = proc.wait()
        except KeyboardInterrupt:
            print("KeyboardInterrupt: terminating workload...")
            proc.terminate()
            try:
                rc = proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                rc = proc.wait()
        finally:
            stop_evt.set()
            for t in threads:
                t.join(timeout=5)

    t1 = time.monotonic()
    wall_finish = datetime.now().isoformat()
    elapsed = t1 - t0

    write_text(exitcode_path, f"{rc}\n")
    write_json(
        time_path,
        {
            "wall_start": wall_start,
            "wall_finish": wall_finish,
            "elapsed_seconds": elapsed,
            "exit_code": rc,
        },
    )

    extract_faketensor_from_stdout(stdout_path, ctx["faketensor_path"])

    append_index_row(
        runs_root / "index.csv",
        {
            "workload_id": ctx["workload_id"],
            "run_id": ctx["run_id"],
            "spec_path": ctx["spec_path"],
            "run_dir": str(run_dir),
            "cuda_visible_devices": args.cuda_visible_devices,
            "elapsed_seconds": f"{elapsed:.6f}",
            "exit_code": rc,
        },
    )

    status = "SUCCESS" if rc == 0 else f"FAIL ({rc})"
    print(f"=== finished: {ctx['workload_id']} -> {status}")
    return rc


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    runs_root = Path(args.runs_root).resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    spec_paths = load_spec_paths(args)
    profile_manifest_map = load_profile_manifest(args.profile_manifest, repo_root)

    failures = 0
    for spec_path in spec_paths:
        rc = run_one_spec(args, spec_path, runs_root, profile_manifest_map)
        if rc != 0:
            failures += 1

    print("\n========== SUMMARY ==========")
    print(f"total specs: {len(spec_paths)}")
    print(f"failures: {failures}")
    print(f"runs root: {runs_root}")


if __name__ == "__main__":
    main()