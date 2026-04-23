from __future__ import annotations

import os
import math
import re

from runtime.events import append_jsonl_event

from placement.inputs import (
    resolve_peak_memory_estimation_from_estimate,
    resolve_placement_estimate,
)
from placement.profiles import policy_estimate_source
from workload.job_spec import load_job_spec
from telemetry.monitor import gpu_mem_total

def _normalize_bucket_list_mib(buckets: list[int], total_mem_mib: int) -> tuple[int, ...]:
    cleaned = sorted({int(x) for x in buckets if int(x) > 0 and int(x) < total_mem_mib})
    return tuple(cleaned)


def _expand_bins_with_max_step(buckets: tuple[int, ...], max_step_mib: int) -> tuple[int, ...]:
    if not buckets:
        return ()

    expanded: list[int] = [buckets[0]]
    for target in buckets[1:]:
        current = expanded[-1]
        while target - current > max_step_mib:
            current += max_step_mib
            expanded.append(current)
        if expanded[-1] != target:
            expanded.append(target)

    return tuple(expanded)


def _capacity_recovery_buckets_mib(
    total_mem_mib: int,
    bucket_mode: str,
    percentage_buckets: tuple[float, ...],
    fixed_bins_mib: tuple[int, ...],
    max_step_mib: int,
) -> tuple[int, ...]:
    if bucket_mode == "fixed_bins":
        return _normalize_bucket_list_mib(list(fixed_bins_mib), total_mem_mib)

    percentage_based = _normalize_bucket_list_mib(
        [math.ceil(total_mem_mib * frac) for frac in percentage_buckets],
        total_mem_mib,
    )

    if bucket_mode == "percentage_buckets":
        return percentage_based

    if bucket_mode == "percentage_buckets_with_max_step":
        return _expand_bins_with_max_step(percentage_based, max_step_mib)

    raise ValueError(f"Unsupported recovery bucket mode: {bucket_mode}")

def _recovery_total_mem_mib() -> int | None:
    totals = gpu_mem_total()
    if not totals:
        return None
    return max(int(v) for v in totals.values())

def _next_estimator_recovery_min_free_mib(
    failed_effective_min_free_mib: int,
    total_mem_mib: int,
    bucket_mode: str,
    percentage_buckets: tuple[float, ...],
    fixed_bins_mib: tuple[int, ...],
    max_step_mib: int,
) -> int | None:
    for bucket_mib in _capacity_recovery_buckets_mib(
        total_mem_mib,
        bucket_mode,
        percentage_buckets,
        fixed_bins_mib,
        max_step_mib,
    ):
        if failed_effective_min_free_mib < bucket_mib:
            return bucket_mib
    return None

def _next_capacity_bucket_above(
    failed_effective_min_free_mib: int,
    total_mem_mib: int,
    bucket_mode: str,
    percentage_buckets: tuple[float, ...],
    fixed_bins_mib: tuple[int, ...],
    max_step_mib: int,
) -> int | None:
    for bucket_mib in _capacity_recovery_buckets_mib(
        total_mem_mib,
        bucket_mode,
        percentage_buckets,
        fixed_bins_mib,
        max_step_mib,
    ):
        if failed_effective_min_free_mib < bucket_mib:
            return bucket_mib
    return None

def _base_effective_min_free_mib_for_estimate_policy(
    *,
    policy: str,
    task_path: str,
    workdir: str,
    estimator_name: str,
) -> int | None:
    estimate_source = policy_estimate_source(policy)
    if estimate_source not in {"task_file_estimate", "online_estimate", "profiled_metadata"}:
        return None

    spec = load_job_spec(task_path, estimator_name)
    placement_estimate = resolve_placement_estimate(
        spec=spec,
        policy=policy,
        workdir=workdir,
        estimator_name=estimator_name,
    )

    gpu_memory_estimation = resolve_peak_memory_estimation_from_estimate(
        policy=policy,
        placement_estimate=placement_estimate,
    )
    if gpu_memory_estimation is None:
        return None

    return int(gpu_memory_estimation) + 2048

def _classify_recovery_failure(lines: list[str]) -> str | None:
    # Ignore the recovery header line. It may contain task ids / paths with
    # accidental substrings such as "oom".
    text = "\n".join(lines[1:])
    text_lower = text.lower()

    # OOM-like failures from frameworks
    if (
        "resourceexhaustederror" in text_lower
        or "resource_exhausted" in text_lower
        or "cuda out of memory" in text_lower
        or "out of memory" in text_lower
        or "outofmemoryerror" in text_lower
        or re.search(r"\boom\b", text_lower) is not None
    ):
        return "oom"

    # Generic failures: do not trigger memory-escalation recovery
    if "non-ok-status" in text_lower:
        return "non_ok_status"

    if "error conda.cli.main_run:execute" in text_lower:
        return "conda_run_failed"

    if "unsuccessful" in text_lower:
        return "nonzero_exit"

    return None

def recovery(
    *,
    dirs,
    handled_crashes,
    task_cls,
    recovery_queue,
    recovery_lock,
    logger,
    policy: str,
    estimator_name: str,
    event_path: str,
    run_id: str,
    recovery_bucket_mode: str,
    recovery_percentage_buckets: tuple[float, ...],
    recovery_fixed_bins_mib: tuple[int, ...],
    recovery_max_step_mib: int,
):
    """
    Scan error logs and enqueue failed jobs for recovery.
    Keeps the current behavior unchanged.
    """
    list_of_files = []

    print("======>", dirs)
    for base in dirs:
        for file in os.listdir(base):
            if file.startswith("err") and file.endswith(".log"):
                file = os.path.join(base, file)
                list_of_files.append(file)

    print("these are the error files that I found in the recovery dir: ", list_of_files)

    crashes = 0
    all_executions = 0

    for iterator in list_of_files:
        if iterator in handled_crashes:
            continue

        all_executions += 1

        with open(iterator, "r") as file:
            lines = file.readlines()

        failure_reason = _classify_recovery_failure(lines)
        if failure_reason is None:
            continue

        crashes += 1
        handled_crashes.append(iterator)

        recovery_data = lines[0].strip().split("+")

        tmp_user_submit_time = recovery_data[6] if len(recovery_data) > 6 else None
        tmp_recovery_count = int(recovery_data[7]) if len(recovery_data) > 7 else 0
        tmp_recovery_force_full_gpu = bool(int(recovery_data[8])) if len(recovery_data) > 8 else False
        tmp_failed_host_free_mib_at_dispatch = (
            int(recovery_data[9]) if len(recovery_data) > 9 and recovery_data[9] != "" else None
        )

        tmp_dir = recovery_data[0]
        tmp_file = recovery_data[3]
        tmp_user = recovery_data[4]
        tmp_task_id = recovery_data[5]

        if failure_reason != "oom":
            append_jsonl_event(
                event_path=event_path,
                record={
                    "event": "recovery_stopped",
                    "task_id": tmp_task_id,
                    "task_file": tmp_file,
                    "user": tmp_user,
                    "workdir": tmp_dir,
                    "error_log": iterator,
                    "reason": failure_reason,
                    "recovery_count": tmp_recovery_count,
                    "recovery_force_full_gpu": tmp_recovery_force_full_gpu,
                    "failure_reason": failure_reason,
                    "run_id": run_id,
                },
            )
            logger.warning(
                f"Recovery skipped for task {tmp_task_id}: non-OOM failure ({failure_reason})"
            )
            continue
        
        if tmp_recovery_force_full_gpu:
            append_jsonl_event(
                event_path=event_path,
                record={
                    "event": "recovery_stopped",
                    "task_id": tmp_task_id,
                    "task_file": tmp_file,
                    "user": tmp_user,
                    "workdir": tmp_dir,
                    "error_log": iterator,
                    "reason": "failed_after_full_gpu_fallback",
                    "recovery_count": tmp_recovery_count,
                    "recovery_force_full_gpu": tmp_recovery_force_full_gpu,
                    "failure_reason": "oom",
                    "run_id": run_id,
                },
            )
            logger.warning(
                f"Recovery stopped for task {tmp_task_id}: task already failed after full-GPU fallback"
            )
            continue

        recovered_task = task_cls(tmp_user, tmp_dir, tmp_file)
        recovered_task.set_id(tmp_task_id)

        if tmp_user_submit_time is not None:
            recovered_task.set_user_submit_time(tmp_user_submit_time)

        recovered_task.set_recovery_count(tmp_recovery_count)
        recovered_task.increment_recovery_count()
        recovered_task.set_if_recovered()
        recovered_task.set_last_failure_reason(failure_reason)

        estimate_source = policy_estimate_source(policy)

        recovery_override = None
        force_full_gpu = False

        if estimate_source in {"task_file_estimate", "online_estimate", "profiled_metadata"}:
            base_effective_min_free_mib = _base_effective_min_free_mib_for_estimate_policy(
                policy=policy,
                task_path=tmp_file,
                workdir=tmp_dir,
                estimator_name=estimator_name,
            )
            if base_effective_min_free_mib is not None:
                failed_effective_min_free_mib = base_effective_min_free_mib
                if tmp_failed_host_free_mib_at_dispatch is not None:
                    failed_effective_min_free_mib = max(
                        failed_effective_min_free_mib,
                        tmp_failed_host_free_mib_at_dispatch,
                    )

                total_mem_mib = _recovery_total_mem_mib()
                if total_mem_mib is not None:
                    recovery_override = _next_estimator_recovery_min_free_mib(
                        failed_effective_min_free_mib,
                        total_mem_mib,
                        recovery_bucket_mode,
                        recovery_percentage_buckets,
                        recovery_fixed_bins_mib,
                        recovery_max_step_mib,
                    )
                else:
                    recovery_override = None

                force_full_gpu = recovery_override is None
            else:
                force_full_gpu = True
        else:
            total_mem_mib = _recovery_total_mem_mib()
            if total_mem_mib is not None:
                failed_effective_min_free_mib = 5 * 1024
                if tmp_failed_host_free_mib_at_dispatch is not None:
                    failed_effective_min_free_mib = max(
                        failed_effective_min_free_mib,
                        tmp_failed_host_free_mib_at_dispatch,
                    )

                recovery_override = _next_capacity_bucket_above(
                    failed_effective_min_free_mib,
                    total_mem_mib,
                )
            else:
                recovery_override = None

            force_full_gpu = recovery_override is None

        recovered_task.set_recovery_min_free_mib_override(recovery_override)
        recovered_task.set_recovery_force_full_gpu(force_full_gpu)

        with recovery_lock:
            recovery_queue.enqueue(recovered_task)

        append_jsonl_event(
            event_path=event_path,
            record={
                "event": "recovered",
                "task_id": tmp_task_id,
                "task_file": tmp_file,
                "user": tmp_user,
                "workdir": tmp_dir,
                "error_log": iterator,
                "recovery_queue_length": recovery_queue.length(),
                "recovery_count": recovered_task.recovery_count,
                "recovery_min_free_mib_override": recovered_task.recovery_min_free_mib_override,
                "recovery_force_full_gpu": recovered_task.recovery_force_full_gpu,
                "failure_reason": recovered_task.last_failure_reason,
                "run_id": run_id,
                "failed_host_free_mib_at_dispatch": tmp_failed_host_free_mib_at_dispatch,
            },
        )

        print(
            "OOM FOUND: recovery queue is filled with the task that has problem: ",
            recovered_task,
            recovered_task._to_string(),
        )
        print("length of the queue:", recovery_queue.length())
        logger.info(f"Recovered: {recovered_task}")

    return crashes, all_executions