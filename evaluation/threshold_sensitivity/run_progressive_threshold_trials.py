#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import csv
import datetime as dt

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import subprocess

import time

import os
import uuid
from threading import Thread

from queueing.task_queue import Task
from runtime.launcher import build_launch_command, launch_and_get_pid
from runtime.pid_resolution import resolve_and_update_gpu_pid
from telemetry import gpu_state, monitor
from workload.job_spec import load_job_spec

from evaluation.threshold_sensitivity.live_threshold_runner import (
    collect_summary_windows,
    parse_summary_windows,
    resolve_gpu_selection,
    start_monitor_thread,
    wait_for_ttfk,
)

DEFAULT_OUTPUT_DIR = Path("evaluation/threshold_sensitivity/progressive_threshold_trials")

OBSERVATION_COLUMNS = [
    "trial_id",
    "stage",
    "gpu_id",
    "cuda_visible_devices",
    "running_jobs_before_stage",
    "next_workload",
    "is_initial_job",
    "decision",
    "decision_reason",
    "smact_risk",
    "smocc_risk",
    "drama_risk",
    "running_job_count_before",
    "running_job_count_after",
    "candidate_started",
    "candidate_finished",
    "candidate_return_code",
    "candidate_runtime_seconds",
    "candidate_solo_runtime_seconds",
    "max_slowdown",
]

TRIAL_SUMMARY_COLUMNS = [
    "trial_id",
    "gpu_id",
    "cuda_visible_devices",
    "tau_smact",
    "tau_smocc",
    "tau_drama",
    "window_seconds",
    "planned_workload_count",
    "admitted_workload_count",
    "rejected_stage",
    "rejection_reason",
    "solo_runtime_sum_seconds",
    "collocated_wall_time_seconds",
    "throughput_gain",
    "mean_slowdown",
    "max_slowdown",
    "p95_slowdown",
]

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run progressive collocation threshold trials."
    )
    p.add_argument(
        "--plan-jsonl",
        required=True,
        help="JSONL plan produced by plan_progressive_threshold_trials.py.",
    )
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned stages without launching workloads.",
    )
    p.add_argument("--tau-smact", type=float, default=0.80)
    p.add_argument("--tau-smocc", type=float, default=0.45)
    p.add_argument("--tau-drama", type=float, default=0.40)

    p.add_argument("--window-seconds", type=float, default=30.0)
    p.add_argument(
        "--summary-windows",
        default="5,10,20,30,40,60,120,200",
        help="Comma-separated summary windows to collect for each admission point.",
    )

    p.add_argument(
        "--solo-runtime-csv",
        default=None,
        help="Optional CSV with solo runtimes used to compute slowdown.",
    )

    p.add_argument(
        "--execute-initial-only",
        action="store_true",
        help="Launch only the first job of each trial and record runtime.",
    )

    p.add_argument("--workdir", default=".")
    p.add_argument(
        "--job-timeout-seconds",
        type=float,
        default=None,
        help="Optional timeout for each launched job.",
    )

    p.add_argument(
        "--limit-trials",
        type=int,
        default=None,
        help="Limit number of trials to run/read from the plan.",
    )

    p.add_argument(
        "--observe-initial-and-decide-next",
        action="store_true",
        help="Launch the first job, collect the risk window, and record the admission decision for the next job without launching it.",
    )
    p.add_argument("--ttfk-timeout", type=float, default=300.0)
    p.add_argument("--window-timeout", type=float, default=900.0)
    p.add_argument("--poll-seconds", type=float, default=0.5)

    p.add_argument(
        "--cleanup-after-observation",
        action="store_true",
        help="Terminate the initial job after recording the admission decision.",
    )

    p.add_argument(
        "--execute-progressive-skeleton",
        action="store_true",
        help="Materialize the progressive admission sequence without launching workloads.",
    )

    p.add_argument(
        "--execute-progressive-trial",
        action="store_true",
        help="Execute the full progressive admission sequence for each trial.",
    )

    p.add_argument(
        "--trial-timeout-seconds",
        type=float,
        default=None,
        help="Optional timeout for waiting for all admitted workloads in a progressive trial.",
    )

    return p.parse_args()


def read_plan(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def describe_trial(trial: dict) -> list[dict]:
    jobs = trial["job_sequence"]
    stages = []

    for stage_idx, candidate in enumerate(jobs, start=1):
        running_jobs = jobs[: stage_idx - 1]

        stages.append(
            {
                "trial_id": trial["trial_id"],
                "stage": stage_idx,
                "gpu_id": trial["gpu_id"],
                "cuda_visible_devices": trial["cuda_visible_devices"],
                "running_jobs_before_stage": running_jobs,
                "next_workload": candidate,
                "is_initial_job": stage_idx == 1,
                "mock_smact_risk": trial.get("mock_smact_risk", ""),
                "mock_smocc_risk": trial.get("mock_smocc_risk", ""),
                "mock_drama_risk": trial.get("mock_drama_risk", ""),
            }
        )

    return stages

def initialize_observations_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OBSERVATION_COLUMNS)
        writer.writeheader()


def dry_run_observation(
    stage: dict,
    *,
    tau_smact: float,
    tau_smocc: float,
    tau_drama: float,
    solo_runtime_lookup: dict[str, float],
) -> dict:
    running_jobs = stage["running_jobs_before_stage"]

    smact = stage.get("mock_smact_risk", "")
    smocc = stage.get("mock_smocc_risk", "")
    drama = stage.get("mock_drama_risk", "")

    decision = "dry_run"
    reason = "planned_only"
    smact_f = ""
    smocc_f = ""
    drama_f = ""

    if smact != "" and smocc != "" and drama != "":
        smact_f = float(smact)
        smocc_f = float(smocc)
        drama_f = float(drama)

        reject = should_reject_gpu(
            smact_risk=smact_f,
            smocc_risk=smocc_f,
            drama_risk=drama_f,
            tau_smact=tau_smact,
            tau_smocc=tau_smocc,
            tau_drama=tau_drama,
        )

        decision = "reject" if reject else "admit"
        reason = "mock_threshold_rule"

    candidate_solo_runtime = lookup_solo_runtime(
        solo_runtime_lookup,
        stage["next_workload"],
    )

    return {
        "trial_id": stage["trial_id"],
        "stage": stage["stage"],
        "gpu_id": stage["gpu_id"],
        "cuda_visible_devices": stage["cuda_visible_devices"],
        "running_jobs_before_stage": ";".join(running_jobs),
        "next_workload": stage["next_workload"],
        "is_initial_job": stage["is_initial_job"],
        "decision": decision,
        "decision_reason": reason,
        "smact_risk": smact_f,
        "smocc_risk": smocc_f,
        "drama_risk": drama_f,
        "running_job_count_before": len(running_jobs),
        "running_job_count_after": len(running_jobs),
        "candidate_started": False,
        "candidate_finished": False,
        "candidate_return_code": "",
        "candidate_runtime_seconds": "",
        "candidate_solo_runtime_seconds": "" if candidate_solo_runtime is None else candidate_solo_runtime,
        "max_slowdown": "",
    }


def append_observations(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OBSERVATION_COLUMNS)
        for row in rows:
            writer.writerow(row)

def should_reject_gpu(
    *,
    smact_risk: float,
    smocc_risk: float,
    drama_risk: float,
    tau_smact: float,
    tau_smocc: float,
    tau_drama: float,
) -> bool:
    return (
        smact_risk >= tau_smact
        and (
            smocc_risk >= tau_smocc
            or drama_risk >= tau_drama
        )
    )

def parse_summary_window_list(text: str) -> list[float]:
    windows = []
    for item in str(text).split(","):
        item = item.strip()
        if item:
            windows.append(float(item))
    return windows

def normalize_spec_path(path: str) -> str:
    return str(Path(path)).strip()


def load_solo_runtime_lookup(path: str | None) -> dict[str, float]:
    if path is None:
        return {}

    import pandas as pd

    df = pd.read_csv(path)
    candidates = [
        "task_path",
        "spec_path",
        "job_spec",
        "workload_spec",
    ]
    path_col = next((c for c in candidates if c in df.columns), None)

    runtime_candidates = [
        "total_runtime_seconds",
        "end_to_end_time_s",
        "end_to_end_time_seconds",
        "training_loop_time_s",
        "runtime_seconds",
    ]
    runtime_col = next((c for c in runtime_candidates if c in df.columns), None)

    if path_col is None or runtime_col is None:
        raise ValueError(
            f"Could not find spec/runtime columns in {path}. "
            f"Columns={list(df.columns)}"
        )

    lookup: dict[str, float] = {}
    for _, row in df.iterrows():
        spec = normalize_spec_path(str(row[path_col]))
        try:
            runtime = float(row[runtime_col])
        except Exception:
            continue
        lookup[spec] = runtime
        lookup[Path(spec).name] = runtime
        lookup[Path(spec).stem] = runtime

    return lookup


def lookup_solo_runtime(
    lookup: dict[str, float],
    spec_path: str,
) -> float | None:
    keys = [
        normalize_spec_path(spec_path),
        Path(spec_path).name,
        Path(spec_path).stem,
    ]
    for key in keys:
        if key in lookup:
            return lookup[key]
    return None

def load_job_command(spec_path: str) -> str:
    import yaml

    with Path(spec_path).open("r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    command = spec.get("job", {}).get("command")
    if not command:
        raise ValueError(f"No job.command found in {spec_path}")

    return str(command)

def execute_candidate_job(
    *,
    spec_path: str,
    workdir: Path,
    cuda_visible_devices: str,
    timeout_seconds: float | None,
    output_dir: Path,
    trial_id: str,
    stage: int,
) -> dict:
    command = load_job_command(spec_path)

    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(spec_path).stem
    stdout_path = logs_dir / f"{trial_id}_stage{stage}_{safe_name}.out.log"
    stderr_path = logs_dir / f"{trial_id}_stage{stage}_{safe_name}.err.log"

    env = dict(**__import__("os").environ)
    env["CUDA_VISIBLE_DEVICES"] = str(cuda_visible_devices)

    started_at = dt.datetime.now().isoformat()
    t0 = time.monotonic()

    timed_out = False

    with stdout_path.open("w", encoding="utf-8") as stdout_f, stderr_path.open(
        "w",
        encoding="utf-8",
    ) as stderr_f:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                cwd=str(workdir),
                env=env,
                stdout=stdout_f,
                stderr=stderr_f,
                timeout=timeout_seconds,
            )
            return_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            return_code = 124
            stderr_f.write(
                f"\n[progressive-runner] job timed out after {timeout_seconds} seconds\n"
            )

    runtime_s = time.monotonic() - t0
    finished_at = dt.datetime.now().isoformat()

    return {
        "return_code": return_code,
        "runtime_seconds": runtime_s,
        "timed_out": timed_out,
        "started_at": started_at,
        "finished_at": finished_at,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }

def terminate_process_tree(pid: int, *, grace_seconds: float = 10.0) -> None:
    import os
    import signal
    import subprocess
    import time

    if pid <= 0:
        return

    try:
        subprocess.run(
            ["pkill", "-TERM", "-P", str(pid)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception as exc:
        print(f"[warning] failed to send SIGTERM to pid={pid}: {exc}")

    deadline = time.time() + grace_seconds
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.25)

    try:
        subprocess.run(
            ["pkill", "-KILL", "-P", str(pid)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except Exception as exc:
        print(f"[warning] failed to send SIGKILL to pid={pid}: {exc}")


def observe_initial_and_decide_next(
    *,
    trial: dict,
    output_dir: Path,
    workdir: Path,
    window_seconds: float,
    summary_windows_text: str,
    tau_smact: float,
    tau_smocc: float,
    tau_drama: float,
    ttfk_timeout: float,
    window_timeout: float,
    poll_seconds: float,
    cleanup_after_observation: bool,
) -> list[dict]:
    jobs = trial["job_sequence"]
    if len(jobs) < 2:
        return []

    initial_spec = jobs[0]
    next_spec = jobs[1]
    gpu_id = str(trial["gpu_id"])
    cuda_visible_devices = str(trial["cuda_visible_devices"])

    run_id = f"{trial['trial_id']}_stage1_{uuid.uuid4().hex[:8]}"
    events_dir = output_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    event_path = str(events_dir / f"{run_id}.jsonl")

    job_spec = load_job_spec(initial_spec, estimator_name=None)
    
    task_obj = Task(
        user="progressive-threshold",
        dir=str(workdir),
        task=initial_spec,
    )
    task_obj.set_id(run_id)

    uuid_to_id = monitor.gpu_uuids()
    gpu_state.init_gpu_state(uuid_to_id)

    selection_args = argparse.Namespace(gpu_id=gpu_id, gpu_uuid=None)
    gpu_uuid, gpu_id = resolve_gpu_selection(selection_args, uuid_to_id)

    monitor_window_seconds = max(parse_summary_windows(summary_windows_text, window_seconds))
    start_monitor_thread(monitor_window_seconds)

    now_str = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    command = build_launch_command(
        str(workdir),
        gpu_id,
        job_spec.command_to_execute,
        now_str,
        task_obj,
        event_path,
        run_id,
        cuda_visible_devices=cuda_visible_devices,
    )

    t_launch = time.monotonic()
    launcher_pid = launch_and_get_pid(command)
    if launcher_pid is None:
        raise RuntimeError("Failed to capture launcher PID")

    gpu_state.launch_task(
        gpu_uuid,
        launcher_pid,
        task_id=str(task_obj.task_id),
        event_path=event_path,
        window_seconds=float(window_seconds),
    )

    Thread(
        target=resolve_and_update_gpu_pid,
        args=(launcher_pid, [gpu_uuid]),
        daemon=True,
    ).start()

    ttfk_seen_at, tracked_pid_after_ttfk = wait_for_ttfk(
        gpu_uuid,
        timeout_s=ttfk_timeout,
        poll_s=poll_seconds,
    )

    summary_windows = parse_summary_windows(summary_windows_text, window_seconds)
    summary_metrics_by_window, summary_ready_times, tracked_pid_after_window = collect_summary_windows(
        gpu_uuid=gpu_uuid,
        ttfk_seen_at=ttfk_seen_at,
        tracked_pid=tracked_pid_after_ttfk,
        windows=summary_windows,
        timeout_s=window_timeout,
        poll_s=poll_seconds,
    )

    decision_window = float(window_seconds)
    if decision_window not in summary_metrics_by_window:
        raise RuntimeError(f"Decision window not collected: {decision_window}s")

    metrics = summary_metrics_by_window[decision_window]

    smact_risk = float(metrics.get("smact_risk"))
    smocc_risk = float(metrics.get("smocc_risk"))
    drama_risk = float(metrics.get("drama_risk"))

    reject = should_reject_gpu(
        smact_risk=smact_risk,
        smocc_risk=smocc_risk,
        drama_risk=drama_risk,
        tau_smact=tau_smact,
        tau_smocc=tau_smocc,
        tau_drama=tau_drama,
    )

    decision = "reject" if reject else "admit"
    reason = "threshold_rule"

    if cleanup_after_observation:
        terminate_process_tree(int(tracked_pid_after_window))
        terminate_process_tree(int(launcher_pid))
        gpu_state.clear_tracking(gpu_uuid)

    return [
        {
            "trial_id": trial["trial_id"],
            "stage": 2,
            "gpu_id": gpu_id,
            "cuda_visible_devices": cuda_visible_devices,
            "running_jobs_before_stage": initial_spec,
            "next_workload": next_spec,
            "is_initial_job": False,
            "decision": decision,
            "decision_reason": reason,
            "smact_risk": smact_risk,
            "smocc_risk": smocc_risk,
            "drama_risk": drama_risk,
            "running_job_count_before": 1,
            "running_job_count_after": 1 if reject else 2,
            "candidate_started": False,
            "candidate_finished": False,
            "candidate_return_code": "",
            "candidate_runtime_seconds": "",
            "candidate_solo_runtime_seconds": "",
            "max_slowdown": "",
        }
    ]

def launch_tracked_workload(
    *,
    spec_path: str,
    trial_id: str,
    stage: int,
    output_dir: Path,
    workdir: Path,
    gpu_id: str,
    cuda_visible_devices: str,
    window_seconds: float,
) -> dict:
    run_id = f"{trial_id}_stage{stage}_{uuid.uuid4().hex[:8]}"

    events_dir = output_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    event_path = str(events_dir / f"{run_id}.jsonl")

    job_spec = load_job_spec(spec_path, estimator_name=None)

    task_obj = Task(
        user="progressive-threshold",
        dir=str(workdir),
        task=spec_path,
    )
    task_obj.set_id(run_id)

    uuid_to_id = monitor.gpu_uuids()
    gpu_state.init_gpu_state(uuid_to_id)

    selection_args = argparse.Namespace(gpu_id=str(gpu_id), gpu_uuid=None)
    gpu_uuid, resolved_gpu_id = resolve_gpu_selection(selection_args, uuid_to_id)

    now_str = dt.datetime.now().strftime("%Y%m%d-%H%M%S")

    command = build_launch_command(
        str(workdir),
        resolved_gpu_id,
        job_spec.command_to_execute,
        now_str,
        task_obj,
        event_path,
        run_id,
        cuda_visible_devices=cuda_visible_devices,
    )

    started_monotonic = time.monotonic()
    started_wall_time = dt.datetime.now().isoformat()

    launcher_pid = launch_and_get_pid(command)
    if launcher_pid is None:
        raise RuntimeError(f"Failed to capture launcher PID for {spec_path}")

    gpu_state.launch_task(
        gpu_uuid,
        launcher_pid,
        task_id=str(task_obj.task_id),
        event_path=event_path,
        window_seconds=float(window_seconds),
    )

    Thread(
        target=resolve_and_update_gpu_pid,
        args=(launcher_pid, [gpu_uuid]),
        daemon=True,
    ).start()

    return {
        "run_id": run_id,
        "spec_path": spec_path,
        "gpu_uuid": gpu_uuid,
        "gpu_id": resolved_gpu_id,
        "cuda_visible_devices": cuda_visible_devices,
        "launcher_pid": int(launcher_pid),
        "event_path": event_path,
        "num_gpus_requested": int(job_spec.num_gpus_requested),
        "stage": int(stage),
        "started_monotonic": float(started_monotonic),
        "started_wall_time": started_wall_time,
    }

def execute_progressive_trial(
    *,
    trial: dict,
) -> list[dict]:
    jobs = trial["job_sequence"]
    if not jobs:
        return []

    rows = []
    running_workloads: list[str] = []

    for stage_idx, next_workload in enumerate(jobs, start=1):
        if stage_idx == 1:
            rows.append(
                {
                    "trial_id": trial["trial_id"],
                    "stage": stage_idx,
                    "gpu_id": trial["gpu_id"],
                    "cuda_visible_devices": trial["cuda_visible_devices"],
                    "running_jobs_before_stage": "",
                    "next_workload": next_workload,
                    "is_initial_job": True,
                    "decision": "launch_initial",
                    "decision_reason": "first_workload_in_sequence",
                    "smact_risk": "",
                    "smocc_risk": "",
                    "drama_risk": "",
                    "running_job_count_before": 0,
                    "running_job_count_after": 1,
                    "candidate_started": False,
                    "candidate_finished": False,
                    "candidate_return_code": "",
                    "candidate_runtime_seconds": "",
                    "candidate_solo_runtime_seconds": "",
                    "max_slowdown": "",
                }
            )
            running_workloads.append(next_workload)
            continue

        rows.append(
            {
                "trial_id": trial["trial_id"],
                "stage": stage_idx,
                "gpu_id": trial["gpu_id"],
                "cuda_visible_devices": trial["cuda_visible_devices"],
                "running_jobs_before_stage": ";".join(running_workloads),
                "next_workload": next_workload,
                "is_initial_job": False,
                "decision": "planned_progressive_stage",
                "decision_reason": "skeleton_only",
                "smact_risk": "",
                "smocc_risk": "",
                "drama_risk": "",
                "running_job_count_before": len(running_workloads),
                "running_job_count_after": len(running_workloads) + 1,
                "candidate_started": False,
                "candidate_finished": False,
                "candidate_return_code": "",
                "candidate_runtime_seconds": "",
                "candidate_solo_runtime_seconds": "",
                "max_slowdown": "",
            }
        )

        running_workloads.append(next_workload)

    return rows

def observe_risk_window_for_running_set(
    *,
    gpu_uuid: str,
    tracked_pid: int,
    window_seconds: float,
    summary_windows_text: str,
    ttfk_timeout: float,
    window_timeout: float,
    poll_seconds: float,
) -> dict:
    summary_windows = parse_summary_windows(summary_windows_text, window_seconds)
    monitor_window_seconds = max(summary_windows)

    start_monitor_thread(monitor_window_seconds)

    ttfk_seen_at, tracked_pid_after_ttfk = wait_for_ttfk(
        gpu_uuid,
        timeout_s=ttfk_timeout,
        poll_s=poll_seconds,
    )

    summary_metrics_by_window, summary_ready_times, tracked_pid_after_window = collect_summary_windows(
        gpu_uuid=gpu_uuid,
        ttfk_seen_at=ttfk_seen_at,
        tracked_pid=tracked_pid_after_ttfk,
        windows=summary_windows,
        timeout_s=window_timeout,
        poll_s=poll_seconds,
    )

    decision_window = float(window_seconds)
    if decision_window not in summary_metrics_by_window:
        raise RuntimeError(f"Decision window not collected: {decision_window}s")

    metrics = summary_metrics_by_window[decision_window]

    return {
        "smact_risk": float(metrics["smact_risk"]),
        "smocc_risk": float(metrics["smocc_risk"]),
        "drama_risk": float(metrics["drama_risk"]),
        "ttfk_seen_at": float(ttfk_seen_at),
        "tracked_pid_after_ttfk": int(tracked_pid_after_ttfk),
        "tracked_pid_after_window": int(tracked_pid_after_window),
        "summary_ready_seconds": float(summary_ready_times[decision_window]),
    }

def terminate_workload_by_spec(spec_path: str) -> None:
    command = load_job_command(spec_path)
    parts = command.split()

    patterns = [command]

    for part in parts:
        if part.endswith(".py"):
            patterns.append(part)
            patterns.append(Path(part).name)

    # Also use the workload spec stem as a fallback.
    patterns.append(Path(spec_path).stem)

    for pattern in dict.fromkeys(patterns):
        subprocess.run(
            ["pkill", "-TERM", "-f", pattern],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    time.sleep(2.0)

    for pattern in dict.fromkeys(patterns):
        subprocess.run(
            ["pkill", "-KILL", "-f", pattern],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

def read_terminal_event_for_run(event_path: str, run_id: str) -> dict | None:
    path = Path(event_path)
    if not path.exists():
        return None

    terminal = None
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if record.get("run_id") != run_id:
                continue
            if record.get("event") in {"completed", "failed"}:
                terminal = record

    return terminal


def wait_for_launched_workloads(
    running_processes: list[dict],
    *,
    poll_seconds: float,
    timeout_seconds: float | None,
) -> dict[int, dict]:
    deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
    remaining = {int(proc["stage"]): proc for proc in running_processes}
    results: dict[int, dict] = {}

    while remaining:
        now = time.monotonic()

        print(
            f"[progressive-runner] waiting for {len(remaining)} workload(s): "
            f"{sorted(remaining.keys())}",
            flush=True,
        )

        if deadline is not None and now >= deadline:
            for stage, proc in list(remaining.items()):
                results[stage] = {
                    "finished": False,
                    "return_code": 124,
                    "runtime_seconds": now - float(proc["started_monotonic"]),
                    "finish_status": "timeout",
                }
            break

        for stage, proc in list(remaining.items()):
            launcher_pid = str(proc["launcher_pid"])

            if monitor.pid_on_system(launcher_pid):
                continue

            terminal_event = read_terminal_event_for_run(
                proc["event_path"],
                proc["run_id"],
            )

            return_code = ""
            finish_status = "unknown"

            if terminal_event is not None:
                finish_status = str(terminal_event.get("event", "unknown"))
                if terminal_event.get("return_code") is not None:
                    return_code = int(terminal_event["return_code"])

            finished_at = time.monotonic()
            results[stage] = {
                "finished": return_code == 0 if return_code != "" else True,
                "return_code": return_code,
                "runtime_seconds": finished_at - float(proc["started_monotonic"]),
                "finish_status": finish_status,
            }
            remaining.pop(stage)

        if remaining:
            time.sleep(max(float(poll_seconds), 5.0))

    return results

def execute_progressive_trial_real(
    *,
    trial: dict,
    output_dir: Path,
    workdir: Path,
    window_seconds: float,
    summary_windows_text: str,
    tau_smact: float,
    tau_smocc: float,
    tau_drama: float,
    ttfk_timeout: float,
    window_timeout: float,
    poll_seconds: float,
    cleanup_after_observation: bool,
    trial_timeout_seconds: float | None,
    solo_runtime_lookup: dict[str, float],
) -> list[dict]:
    jobs = trial["job_sequence"]
    if not jobs:
        return []

    rows = []
    running_workloads: list[str] = []
    running_processes: list[dict] = []

    gpu_id = str(trial["gpu_id"])
    cuda_visible_devices = str(trial["cuda_visible_devices"])

    try:
        for stage_idx, next_workload in enumerate(jobs, start=1):
            if stage_idx == 1:
                launched = launch_tracked_workload(
                    spec_path=next_workload,
                    trial_id=trial["trial_id"],
                    stage=stage_idx,
                    output_dir=output_dir,
                    workdir=workdir,
                    gpu_id=gpu_id,
                    cuda_visible_devices=cuda_visible_devices,
                    window_seconds=window_seconds,
                )

                running_processes.append(launched)
                running_workloads.append(next_workload)

                solo_runtime = lookup_solo_runtime(solo_runtime_lookup, next_workload)

                rows.append(
                    {
                        "trial_id": trial["trial_id"],
                        "stage": stage_idx,
                        "gpu_id": launched["gpu_id"],
                        "cuda_visible_devices": cuda_visible_devices,
                        "running_jobs_before_stage": "",
                        "next_workload": next_workload,
                        "is_initial_job": True,
                        "decision": "launch_initial",
                        "decision_reason": "first_workload_in_sequence",
                        "smact_risk": "",
                        "smocc_risk": "",
                        "drama_risk": "",
                        "running_job_count_before": 0,
                        "running_job_count_after": 1,
                        "candidate_started": True,
                        "candidate_finished": False,
                        "candidate_return_code": "",
                        "candidate_runtime_seconds": "",
                        "candidate_solo_runtime_seconds": "" if solo_runtime is None else solo_runtime,
                        "max_slowdown": "",
                    }
                )
                continue

            observed = observe_risk_window_for_running_set(
                gpu_uuid=running_processes[-1]["gpu_uuid"],
                tracked_pid=running_processes[-1]["launcher_pid"],
                window_seconds=window_seconds,
                summary_windows_text=summary_windows_text,
                ttfk_timeout=ttfk_timeout,
                window_timeout=window_timeout,
                poll_seconds=poll_seconds,
            )

            running_processes[-1]["tracked_pid_after_window"] = observed["tracked_pid_after_window"]
            running_processes[-1]["tracked_pid_after_ttfk"] = observed["tracked_pid_after_ttfk"]

            reject = should_reject_gpu(
                smact_risk=observed["smact_risk"],
                smocc_risk=observed["smocc_risk"],
                drama_risk=observed["drama_risk"],
                tau_smact=tau_smact,
                tau_smocc=tau_smocc,
                tau_drama=tau_drama,
            )

            decision = "reject" if reject else "admit"

            started = False
            if not reject:
                launched = launch_tracked_workload(
                    spec_path=next_workload,
                    trial_id=trial["trial_id"],
                    stage=stage_idx,
                    output_dir=output_dir,
                    workdir=workdir,
                    gpu_id=gpu_id,
                    cuda_visible_devices=cuda_visible_devices,
                    window_seconds=window_seconds,
                )
                running_processes.append(launched)
                running_workloads.append(next_workload)
                started = True

            solo_runtime = lookup_solo_runtime(solo_runtime_lookup, next_workload)
            
            rows.append(
                {
                    "trial_id": trial["trial_id"],
                    "stage": stage_idx,
                    "gpu_id": gpu_id,
                    "cuda_visible_devices": cuda_visible_devices,
                    "running_jobs_before_stage": ";".join(running_workloads[:-1] if started else running_workloads),
                    "next_workload": next_workload,
                    "is_initial_job": False,
                    "decision": decision,
                    "decision_reason": "threshold_rule",
                    "smact_risk": observed["smact_risk"],
                    "smocc_risk": observed["smocc_risk"],
                    "drama_risk": observed["drama_risk"],
                    "running_job_count_before": len(running_workloads) - 1 if started else len(running_workloads),
                    "running_job_count_after": len(running_workloads),
                    "candidate_started": started,
                    "candidate_finished": False,
                    "candidate_return_code": "",
                    "candidate_runtime_seconds": "",
                    "candidate_solo_runtime_seconds": "" if solo_runtime is None else solo_runtime,
                    "max_slowdown": "",
                }
            )

            print(
                f"[{trial['trial_id']} stage={stage_idx}] "
                f"decision={decision} "
                f"smact={observed['smact_risk']:.3f} "
                f"smocc={observed['smocc_risk']:.3f} "
                f"drama={observed['drama_risk']:.3f}"
            )

            if reject:
                break

        finish_results = wait_for_launched_workloads(
            running_processes,
            poll_seconds=poll_seconds,
            timeout_seconds=trial_timeout_seconds,
        )

        for row in rows:
            stage = int(row["stage"])
            if stage not in finish_results:
                continue

            result = finish_results[stage]
            row["candidate_finished"] = result["finished"]
            row["candidate_return_code"] = result["return_code"]

            row["candidate_runtime_seconds"] = result["runtime_seconds"]

            solo_runtime = row.get("candidate_solo_runtime_seconds", "")
            if (
                row.get("candidate_finished") is True
                and solo_runtime != ""
                and result["runtime_seconds"] != ""
            ):
                row["max_slowdown"] = float(result["runtime_seconds"]) / float(solo_runtime)
            else:
                row["max_slowdown"] = ""

    finally:
        if cleanup_after_observation:
            for proc in reversed(running_processes):
                if proc.get("tracked_pid_after_window") is not None:
                    terminate_process_tree(int(proc["tracked_pid_after_window"]))
                if proc.get("tracked_pid_after_ttfk") is not None:
                    terminate_process_tree(int(proc["tracked_pid_after_ttfk"]))

                terminate_process_tree(int(proc["launcher_pid"]))
                terminate_workload_by_spec(proc["spec_path"])

            for proc in running_processes:
                gpu_state.clear_tracking(proc["gpu_uuid"])

    return rows

def initialize_trial_summary_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAL_SUMMARY_COLUMNS)
        writer.writeheader()


def append_trial_summaries(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAL_SUMMARY_COLUMNS)
        for row in rows:
            writer.writerow(row)


def build_trial_summary_from_rows(
    *,
    trial: dict,
    rows: list[dict],
    tau_smact: float,
    tau_smocc: float,
    tau_drama: float,
    window_seconds: float,
) -> dict:
    rejected_rows = [r for r in rows if r.get("decision") == "reject"]
    rejected_stage = rejected_rows[0]["stage"] if rejected_rows else ""

    admitted_count = sum(
        1
        for r in rows
        if r.get("decision") in {"launch_initial", "admit", "initial_only"}
    )

    finished_rows = [
        r for r in rows
        if r.get("candidate_started") is True
        and r.get("candidate_finished") is True
    ]

    solo_runtimes = []
    collocated_runtimes = []
    slowdowns = []

    for r in finished_rows:
        solo = r.get("candidate_solo_runtime_seconds", "")
        runtime = r.get("candidate_runtime_seconds", "")

        if solo == "" or runtime == "":
            continue

        solo = float(solo)
        runtime = float(runtime)

        solo_runtimes.append(solo)
        collocated_runtimes.append(runtime)
        slowdowns.append(runtime / solo)

        r["max_slowdown"] = runtime / solo
        
    if len(finished_rows) == admitted_count and slowdowns:
        solo_runtime_sum = sum(solo_runtimes)
        collocated_wall_time = max(collocated_runtimes)
        throughput_gain = solo_runtime_sum / collocated_wall_time
        mean_slowdown = sum(slowdowns) / len(slowdowns)
        max_slowdown = max(slowdowns)
        p95_slowdown = sorted(slowdowns)[int(0.95 * (len(slowdowns) - 1))]
    else:
        solo_runtime_sum = ""
        collocated_wall_time = ""
        throughput_gain = ""
        mean_slowdown = ""
        max_slowdown = ""
        p95_slowdown = ""

    return {
        "trial_id": trial["trial_id"],
        "gpu_id": trial["gpu_id"],
        "cuda_visible_devices": trial["cuda_visible_devices"],
        "tau_smact": tau_smact,
        "tau_smocc": tau_smocc,
        "tau_drama": tau_drama,
        "window_seconds": window_seconds,
        "planned_workload_count": len(trial["job_sequence"]),
        "admitted_workload_count": admitted_count,
        "rejected_stage": rejected_stage,
        "rejection_reason": "threshold_rule" if rejected_rows else "",
        "solo_runtime_sum_seconds": solo_runtime_sum,
        "collocated_wall_time_seconds": collocated_wall_time,
        "throughput_gain": throughput_gain,
        "mean_slowdown": mean_slowdown,
        "max_slowdown": max_slowdown,
        "p95_slowdown": p95_slowdown,
    }


def main() -> int:
    args = parse_args()

    plan_path = Path(args.plan_jsonl)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trials = read_plan(plan_path)

    if args.limit_trials is not None:
        trials = trials[: args.limit_trials]

    solo_runtime_lookup = load_solo_runtime_lookup(args.solo_runtime_csv)

    metadata = {
        "plan_jsonl": str(plan_path),
        "tau_smact": args.tau_smact,
        "tau_smocc": args.tau_smocc,
        "tau_drama": args.tau_drama,
        "rule": "reject if smact_risk >= tau_smact and (smocc_risk >= tau_smocc or drama_risk >= tau_drama)",
        "window_seconds": args.window_seconds,
        "summary_windows": parse_summary_window_list(args.summary_windows),
        "solo_runtime_csv": args.solo_runtime_csv,
        "solo_runtime_entries": len(solo_runtime_lookup),
    }

    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"wrote {metadata_path}")

    

    all_stages = []
    for trial in trials:
        all_stages.extend(describe_trial(trial))

    stage_plan_path = output_dir / "progressive_stage_plan.jsonl"

    observations_csv = output_dir / "admission_observations.csv"
    initialize_observations_csv(observations_csv)

    trial_summary_csv = output_dir / "progressive_trial_summary.csv"
    initialize_trial_summary_csv(trial_summary_csv)

    if args.execute_initial_only:
        rows = []
        workdir = Path(args.workdir).resolve()

        for stage in all_stages:
            if not stage["is_initial_job"]:
                continue

            result = execute_candidate_job(
                spec_path=stage["next_workload"],
                workdir=workdir,
                cuda_visible_devices=stage["cuda_visible_devices"],
                timeout_seconds=args.job_timeout_seconds,
                output_dir=output_dir,
                trial_id=stage["trial_id"],
                stage=int(stage["stage"]),
            )

            running_jobs = stage["running_jobs_before_stage"]
            candidate_solo_runtime = lookup_solo_runtime(
                solo_runtime_lookup,
                stage["next_workload"],
            )

            rows.append(
                {
                    "trial_id": stage["trial_id"],
                    "stage": stage["stage"],
                    "gpu_id": stage["gpu_id"],
                    "cuda_visible_devices": stage["cuda_visible_devices"],
                    "running_jobs_before_stage": ";".join(running_jobs),
                    "next_workload": stage["next_workload"],
                    "is_initial_job": stage["is_initial_job"],
                    "decision": "initial_only",
                    "decision_reason": "initial_job_execution_test",
                    "smact_risk": "",
                    "smocc_risk": "",
                    "drama_risk": "",
                    "running_job_count_before": len(running_jobs),
                    "running_job_count_after": 1,
                    "candidate_started": True,
                    "candidate_finished": result["return_code"] == 0 and not result["timed_out"],
                    "candidate_return_code": result["return_code"],
                    "candidate_runtime_seconds": result["runtime_seconds"],
                    "candidate_solo_runtime_seconds": "" if candidate_solo_runtime is None else candidate_solo_runtime,
                    "max_slowdown": "",
                }
            )

            print(
                f"[{stage['trial_id']}] initial job finished "
                f"rc={result['return_code']} timed_out={result['timed_out']} "
                f"runtime={result['runtime_seconds']:.2f}s"
            )

        append_observations(observations_csv, rows)
        print(f"wrote {observations_csv}")

    if args.observe_initial_and_decide_next:
        rows = []
        workdir = Path(args.workdir).resolve()

        for trial in trials:
            rows.extend(
                observe_initial_and_decide_next(
                    trial=trial,
                    output_dir=output_dir,
                    workdir=workdir,
                    window_seconds=float(args.window_seconds),
                    summary_windows_text=args.summary_windows,
                    tau_smact=float(args.tau_smact),
                    tau_smocc=float(args.tau_smocc),
                    tau_drama=float(args.tau_drama),
                    ttfk_timeout=float(args.ttfk_timeout),
                    window_timeout=float(args.window_timeout),
                    poll_seconds=float(args.poll_seconds),
                    cleanup_after_observation=args.cleanup_after_observation,
                )
            )

        append_observations(observations_csv, rows)
        print(f"wrote {observations_csv}")

    if args.execute_progressive_skeleton:
        rows = []
        summaries = []

        for trial in trials:
            trial_rows = execute_progressive_trial(trial=trial)
            rows.extend(trial_rows)
            summaries.append(
                build_trial_summary_from_rows(
                    trial=trial,
                    rows=trial_rows,
                    tau_smact=float(args.tau_smact),
                    tau_smocc=float(args.tau_smocc),
                    tau_drama=float(args.tau_drama),
                    window_seconds=float(args.window_seconds),
                )
            )

        append_observations(observations_csv, rows)
        append_trial_summaries(trial_summary_csv, summaries)
        print(f"wrote {observations_csv}")
        print(f"wrote {trial_summary_csv}")

    if args.dry_run:
        append_observations(
            observations_csv,
            [
                dry_run_observation(
                    stage,
                    tau_smact=args.tau_smact,
                    tau_smocc=args.tau_smocc,
                    tau_drama=args.tau_drama,
                    solo_runtime_lookup=solo_runtime_lookup,
                )
                for stage in all_stages
            ]
        )
        print(f"wrote {observations_csv}")

    with stage_plan_path.open("w", encoding="utf-8") as f:
        for stage in all_stages:
            f.write(json.dumps(stage, sort_keys=True) + "\n")

    if args.execute_progressive_trial:
        rows = []
        summaries = []
        workdir = Path(args.workdir).resolve()

        for trial in trials:
            trial_rows = execute_progressive_trial_real(
                trial=trial,
                output_dir=output_dir,
                workdir=workdir,
                window_seconds=float(args.window_seconds),
                summary_windows_text=args.summary_windows,
                tau_smact=float(args.tau_smact),
                tau_smocc=float(args.tau_smocc),
                tau_drama=float(args.tau_drama),
                ttfk_timeout=float(args.ttfk_timeout),
                window_timeout=float(args.window_timeout),
                poll_seconds=float(args.poll_seconds),
                cleanup_after_observation=args.cleanup_after_observation,
                trial_timeout_seconds=args.trial_timeout_seconds,
                solo_runtime_lookup=solo_runtime_lookup,
            )
            rows.extend(trial_rows)
            summaries.append(
                build_trial_summary_from_rows(
                    trial=trial,
                    rows=trial_rows,
                    tau_smact=float(args.tau_smact),
                    tau_smocc=float(args.tau_smocc),
                    tau_drama=float(args.tau_drama),
                    window_seconds=float(args.window_seconds),
                )
            )

        append_observations(observations_csv, rows)
        append_trial_summaries(trial_summary_csv, summaries)
        print(f"wrote {observations_csv}")
        print(f"wrote {trial_summary_csv}")

    print(f"trials={len(trials)}")
    print(f"stages={len(all_stages)}")
    print(f"wrote {stage_plan_path}")

    if args.dry_run:
        print("\nDRY RUN: planned stages")
        for stage in all_stages:
            running = stage["running_jobs_before_stage"]
            running_text = ", ".join(Path(x).stem for x in running) if running else "<none>"
            next_workload = Path(stage["next_workload"]).stem
            print(
                f"[{stage['trial_id']} stage={stage['stage']}] "
                f"running={running_text} -> next_workload={next_workload} "
                f"gpu_id={stage['gpu_id']} visible={stage['cuda_visible_devices']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())