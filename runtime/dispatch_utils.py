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
    recovery_force_full_gpu: bool,
    failed_host_free_mib_at_dispatch: int | None,
    now: str,
) -> str:
    failed_host_free_mib_at_dispatch = (
        "" if failed_host_free_mib_at_dispatch is None else int(failed_host_free_mib_at_dispatch)
    )
    return (
        f'echo "{dir}+{environment}+{command_to_execute}+{task}+{user}+{task_id}+{user_submit_time}+{recovery_count}+{int(recovery_force_full_gpu)}+{failed_host_free_mib_at_dispatch}" '
        f'> {dir}/err-{now}-{task_id}.log'
    )