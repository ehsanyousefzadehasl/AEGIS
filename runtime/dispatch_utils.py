from __future__ import annotations

import os
import shlex

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
    log_dir: str | None = None,
) -> str:
    failed_host_free_mib_at_dispatch = (
        "" if failed_host_free_mib_at_dispatch is None else int(failed_host_free_mib_at_dispatch)
    )
    log_dir = dir if log_dir is None else log_dir
    os.makedirs(log_dir, exist_ok=True)
    err_log = os.path.join(log_dir, f"err-{now}-{task_id}.log")

    clean_command = " ".join(str(command_to_execute).split())

    header = (
        f"{dir}+{environment}+{clean_command}+{task}+{user}+{task_id}+"
        f"{user_submit_time}+{recovery_count}+{int(recovery_force_full_gpu)}+"
        f"{failed_host_free_mib_at_dispatch}"
    )

    return f"echo {shlex.quote(header)} > {shlex.quote(err_log)}"