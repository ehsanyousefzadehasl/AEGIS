# job_spec.py
from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Optional


ESTIMATOR_INDEX = {
    "None": None,
    "horus": 9,
    "faketensor": 10,
    "GPUMemNet": 11,
}


@dataclass
class JobSpec:
    task_path: str
    raw_lines: list[str]
    env_name: str
    env_path: str
    command_to_execute: str
    num_gpus_requested: int
    gpu_memory_requirement_mib: Optional[int]
    gpu_memory_estimate_mib: Optional[int]


def _read_task_lines(task_path: str) -> list[str]:
    ret = subprocess.run(
        f"cat {task_path}",
        capture_output=True,
        shell=True,
        text=True,
    )
    if ret.returncode != 0:
        raise RuntimeError(f"Failed to read task file: {task_path}")
    return ret.stdout.splitlines()


def _extract_env_name(lines: list[str]) -> str:
    for line in lines:
        if "activate" in line:
            return line.split("activate", 1)[1].strip()
    return "tf"


def _extract_python_command(lines: list[str]) -> str:
    for line in lines:
        if "python" in line:
            return line
    raise ValueError("Could not find python command in task profile")


def _safe_int_at(lines: list[str], idx: int) -> Optional[int]:
    if idx < 0 or idx >= len(lines):
        return None
    value = lines[idx].strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def load_job_spec(task_path: str, estimator_name: str) -> JobSpec:
    lines = _read_task_lines(task_path)

    env_name = _extract_env_name(lines)
    env_path = f"/opt/miniconda3/envs/{env_name}"
    command_to_execute = _extract_python_command(lines)

    num_gpus_requested = _safe_int_at(lines, 7)
    if num_gpus_requested is None:
        raise ValueError(f"Could not parse requested GPU count from {task_path}")

    gpu_memory_requirement_mib = _safe_int_at(lines, 8)

    est_idx = ESTIMATOR_INDEX.get(estimator_name, None)
    gpu_memory_estimate_mib = None if est_idx is None else _safe_int_at(lines, est_idx)

    return JobSpec(
        task_path=task_path,
        raw_lines=lines,
        env_name=env_name,
        env_path=env_path,
        command_to_execute=command_to_execute,
        num_gpus_requested=num_gpus_requested,
        gpu_memory_requirement_mib=gpu_memory_requirement_mib,
        gpu_memory_estimate_mib=gpu_memory_estimate_mib,
    )