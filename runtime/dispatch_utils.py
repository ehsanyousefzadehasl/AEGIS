from __future__ import annotations

from collections.abc import Iterable


def format_gpu_identifiers(gpu_ids: Iterable) -> str:
    return ",".join(str(gpu) for gpu in gpu_ids)


def build_recovery_header(
    dir: str,
    environment: str,
    command_to_execute: str,
    task: str,
    user: str,
    task_id: str,
    user_submit_time: str,
    recovery_count: int,
    now: str,
) -> str:
    return (
        f'echo "{dir}+{environment}+{command_to_execute}+{task}+{user}+{task_id}+{user_submit_time}+{recovery_count}" '
        f'> {dir}/err-{now}-{task_id}.log'
    )