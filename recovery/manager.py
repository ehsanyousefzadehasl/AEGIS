from __future__ import annotations

import os
import math

from runtime.events import append_jsonl_event

from placement.inputs import (
    resolve_peak_memory_estimation_from_estimate,
    resolve_placement_estimate,
)
from placement.profiles import policy_estimate_source
from workload.job_spec import load_job_spec
from telemetry.monitor import gpu_mem_total

def _capacity_recovery_buckets_mib(total_mem_mib: int) -> tuple[int, int, int]:
    return (
        math.ceil(total_mem_mib * 0.25),
        math.ceil(total_mem_mib * 0.50),
        math.ceil(total_mem_mib * 0.75),
    )

def _recovery_total_mem_mib() -> int | None:
    totals = gpu_mem_total()
    if not totals:
        return None
    return max(int(v) for v in totals.values())


def _recovery_min_free_mib_override(
    recovery_count: int,
    total_mem_mib: int,
) -> int | None:
    if recovery_count <= 0:
        return None

    buckets = _capacity_recovery_buckets_mib(total_mem_mib)

    if recovery_count == 1:
        return buckets[0]
    if recovery_count == 2:
        return buckets[1]
    if recovery_count == 3:
        return buckets[2]
    return None

def _next_estimator_recovery_min_free_mib(
    failed_effective_min_free_mib: int,
    total_mem_mib: int,
) -> int | None:
    for bucket_mib in _capacity_recovery_buckets_mib(total_mem_mib):
        if failed_effective_min_free_mib < bucket_mib:
            return bucket_mib
    return None

def _estimator_recovery_min_free_mib_override(
    base_effective_min_free_mib: int,
    recovery_count: int,
    total_mem_mib: int,
) -> int | None:
    failed_threshold = base_effective_min_free_mib
    override = None

    for _ in range(recovery_count):
        override = _next_estimator_recovery_min_free_mib(
            failed_threshold,
            total_mem_mib,
        )
        if override is None:
            return None
        failed_threshold = override

    return override

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

        for line in lines:
            if (
                "unsuccessful" in line
                or "OOM" in line
                or "Non-OK-status" in line
                or "RESOURCE_EXHAUSTED" in line
            ):
                crashes += 1
                handled_crashes.append(iterator)

                with open(iterator, "r") as opener:
                    lines = opener.readlines()

                recovery_data = lines[0].split("+")

                tmp_user_submit_time = recovery_data[6] if len(recovery_data) > 6 else None
                tmp_recovery_count = int(recovery_data[7]) if len(recovery_data) > 7 else 0
                tmp_recovery_force_full_gpu = bool(int(recovery_data[8])) if len(recovery_data) > 8 else False

                tmp_dir = recovery_data[0]
                tmp_file = recovery_data[3]
                tmp_user = recovery_data[4]
                tmp_task_id = recovery_data[5][:-1]

                if tmp_recovery_force_full_gpu:
                    handled_crashes.append(iterator)
                    append_jsonl_event(
                        event_path=f"{tmp_dir}/events.jsonl",
                        record={
                            "event": "recovery_stopped",
                            "task_id": tmp_task_id,
                            "task_file": tmp_file,
                            "user": tmp_user,
                            "workdir": tmp_dir,
                            "error_log": iterator,
                            "reason": "failed_after_full_gpu_fallback",
                        },
                    )
                    logger.warning(
                        f"Recovery stopped for task {tmp_task_id}: task already failed after full-GPU fallback"
                    )
                    break

                recovered_task = task_cls(tmp_user, tmp_dir, tmp_file)
                recovered_task.set_id(tmp_task_id)

                if tmp_user_submit_time is not None:
                    recovered_task.set_user_submit_time(tmp_user_submit_time)

                recovered_task.set_recovery_count(tmp_recovery_count)
                recovered_task.increment_recovery_count()
                recovered_task.set_if_recovered()
                recovered_task.set_last_failure_reason("oom")

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
                        total_mem_mib = _recovery_total_mem_mib()
                        if total_mem_mib is not None:
                            recovery_override = _estimator_recovery_min_free_mib_override(
                                base_effective_min_free_mib=base_effective_min_free_mib,
                                recovery_count=recovered_task.recovery_count,
                                total_mem_mib=total_mem_mib,
                            )
                        else:
                            recovery_override = None

                        force_full_gpu = recovery_override is None
                    else:
                        total_mem_mib = _recovery_total_mem_mib()
                        if total_mem_mib is not None:
                            recovery_override = _recovery_min_free_mib_override(
                                recovered_task.recovery_count,
                                total_mem_mib,
                            )
                        else:
                            recovery_override = None

                        force_full_gpu = recovery_override is None and recovered_task.recovery_count >= 4

                recovered_task.set_recovery_min_free_mib_override(recovery_override)
                recovered_task.set_recovery_force_full_gpu(force_full_gpu)

                with recovery_lock:
                    recovery_queue.enqueue(recovered_task)

                append_jsonl_event(
                    event_path=f"{tmp_dir}/events.jsonl",
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
                    },
                )

                print(
                    "OOM FOUND: recovery queue is filled with the task that has problem: ",
                    recovered_task,
                    recovered_task._to_string(),
                )
                print("length of the queue:", recovery_queue.length())
                logger.info(f"Recovered: {recovered_task}")
                break

    return crashes, all_executions