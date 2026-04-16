# job_spec.py
from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Optional

from workload.yaml_job_spec import load_yaml_job_spec

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
    online_summary_path: Optional[str]
    online_parser_arg_1: Optional[str]
    online_parser_arg_2: Optional[str]

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

def _string_at(lines: list[str], idx: int) -> Optional[str]:
    if idx < 0 or idx >= len(lines):
        return None
    value = lines[idx].strip()
    return value if value else None


def _load_yaml_format_job_spec(task_path: str, estimator_name: str) -> JobSpec:
    data = load_yaml_job_spec(task_path)

    job = data.get("job", {})
    resources = data.get("resources", {})
    estimates = data.get("estimates", {})
    online_estimation = data.get("online_estimation", {})

    env_name = job.get("conda_env", "tf")
    env_path = f"/opt/miniconda3/envs/{env_name}"
    command_to_execute = job["command"]

    num_gpus_requested = resources.get("num_gpus")
    if num_gpus_requested is None:
        raise ValueError(f"Could not parse requested GPU count from {task_path}")

    gpu_memory_requirement_mib = resources.get("gpu_memory_requirement_mib")

    estimate_key_map = {
        "None": None,
        "horus": "horus_mib",
        "faketensor": "faketensor_mib",
        "GPUMemNet": "gpumemnet_mib",
    }

    estimate_key = estimate_key_map.get(estimator_name)
    gpu_memory_estimate_mib = None if estimate_key is None else estimates.get(estimate_key)

    raw_lines = [
        f"# YAML job spec: {task_path}",
        f"conda activate {env_name}",
        command_to_execute,
        str(online_estimation.get("summary_path", "")),
        str(online_estimation.get("parser_arg_1", "")),
        str(online_estimation.get("parser_arg_2", "")),
        "",
        str(num_gpus_requested),
        "" if gpu_memory_requirement_mib is None else str(gpu_memory_requirement_mib),
        "" if estimates.get("horus_mib") is None else str(estimates.get("horus_mib")),
        "" if estimates.get("faketensor_mib") is None else str(estimates.get("faketensor_mib")),
        "" if estimates.get("gpumemnet_mib") is None else str(estimates.get("gpumemnet_mib")),
    ]

    return JobSpec(
        task_path=task_path,
        raw_lines=raw_lines,
        env_name=env_name,
        env_path=env_path,
        command_to_execute=command_to_execute,
        num_gpus_requested=int(num_gpus_requested),
        gpu_memory_requirement_mib=None if gpu_memory_requirement_mib is None else int(float(gpu_memory_requirement_mib)),
        gpu_memory_estimate_mib=None if gpu_memory_estimate_mib is None else int(float(gpu_memory_estimate_mib)),
        online_summary_path=online_estimation.get("summary_path"),
        online_parser_arg_1=None if online_estimation.get("parser_arg_1") is None else str(online_estimation.get("parser_arg_1")),
        online_parser_arg_2=None if online_estimation.get("parser_arg_2") is None else str(online_estimation.get("parser_arg_2")),
    )


def load_job_spec(task_path: str, estimator_name: str) -> JobSpec:
    if task_path.endswith(".yaml") or task_path.endswith(".yml"):
        return _load_yaml_format_job_spec(task_path, estimator_name)
    
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
        online_summary_path=_string_at(lines, 3),
        online_parser_arg_1=_string_at(lines, 4),
        online_parser_arg_2=_string_at(lines, 5),
    )