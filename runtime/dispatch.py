from __future__ import annotations

from threading import Thread
from collections.abc import Iterable

from queueing.selection import dequeue_selected_job
from runtime import gpu_allocations
from runtime.dispatch_utils import format_gpu_identifiers, build_recovery_header
from runtime.events import append_jsonl_event

def dispatch_selected_job(
    *,
    selected,
    task_obj,
    user: str,
    dir: str,
    task: str,
    environment: str,
    command_to_execute: str,
    assigned_gpu_ids: Iterable,
    now: str,
    main_queue,
    recovery_queue,
    main_lock,
    recovery_lock,
    command_generator,
    command_executor,
    launch_and_get_pid,
    launch_task,
    async_resolve_and_update,
    logger,
    event_path: str,
    run_id: str,
    failed_host_free_mib_at_dispatch: int | None,
    profiled_gpu_util: float = 0.0,
    profiled_memory_mib: int = 0,
) -> int | None:
    gpu_ids_list = list(assigned_gpu_ids)

    task_obj.set_service_time(now)
    task_obj.set_status("dispatched")

    gpus_identifiers = format_gpu_identifiers(gpu_ids_list)
    command = command_generator(
        dir,
        gpus_identifiers,
        command_to_execute,
        now,
        task_obj,
        event_path,
        run_id,
    )

    dequeue_selected_job(selected, main_queue, recovery_queue, main_lock, recovery_lock)

    to_write = build_recovery_header(
        dir,
        environment,
        command_to_execute,
        task,
        user,
        task_obj.task_id,
        task_obj.user_submit_time,
        task_obj.recovery_count,
        task_obj.recovery_force_full_gpu,
        failed_host_free_mib_at_dispatch,
        now,
    )

    logger.info(f"dispatched {task_obj.task_id} - {task_obj.task} - {gpus_identifiers}")
    append_jsonl_event(
        event_path=event_path,
        record={
            "event": "dispatched",
            "timestamp": now,
            "task_id": task_obj.task_id,
            "task": task_obj.task,
            "task_file": task,
            "user": user,
            "assigned_gpu_ids": gpu_ids_list,
            "cuda_visible_devices": gpus_identifiers,
            "workdir": dir,
            "recovered": task_obj.recovered,
            "recovery_count": task_obj.recovery_count,
            "recovery_min_free_mib_override": task_obj.recovery_min_free_mib_override,
            "recovery_force_full_gpu": task_obj.recovery_force_full_gpu,
            "failure_reason": task_obj.last_failure_reason,
            "run_id": run_id,
            "failed_host_free_mib_at_dispatch": failed_host_free_mib_at_dispatch,
        },
    )

    command_executor(to_write)
    pid = launch_and_get_pid(command)

    if pid is None:
        with recovery_lock if task_obj.recovered else main_lock:
            if task_obj.recovered:
                recovery_queue.put_it_back(task_obj)
            else:
                main_queue.put_it_back(task_obj)

        append_jsonl_event(
            event_path=event_path,
            record={
                "event": "launch_failed",
                "timestamp": now,
                "task_id": task_obj.task_id,
                "task": task_obj.task,
                "task_file": task,
                "user": user,
                "assigned_gpu_ids": gpu_ids_list,
                "cuda_visible_devices": gpus_identifiers,
                "workdir": dir,
                "reason": "pid_capture_failed",
                "recovered": task_obj.recovered,
                "recovery_count": task_obj.recovery_count,
                "recovery_min_free_mib_override": task_obj.recovery_min_free_mib_override,
                "recovery_force_full_gpu": task_obj.recovery_force_full_gpu,
                "failure_reason": task_obj.last_failure_reason,
                "run_id": run_id,
            },
        )
        logger.error(f"Failed to capture PID for {task_obj.task_id}; task requeued")
        return None

    for gpu_uuid in gpu_ids_list:
        launch_task(
            gpu_uuid,
            pid,
            task_id=str(task_obj.task_id),
            event_path=event_path,
        )

    gpu_allocations.register_allocation(
        task_id=str(task_obj.task_id),
        task_path=task,
        launcher_pid=int(pid),
        assigned_gpu_ids=gpu_ids_list,
        profiled_gpu_util=float(profiled_gpu_util or 0.0),
        profiled_memory_mib=int(profiled_memory_mib or 0),
        metadata={
            "run_id": run_id,
            "user": user,
            "workdir": dir,
            "recovered": bool(task_obj.recovered),
            "recovery_count": int(task_obj.recovery_count),
        },
    )


    append_jsonl_event(
        event_path=event_path,
        record={
            "event": "launched",
            "timestamp": now,
            "task_id": task_obj.task_id,
            "task": task_obj.task,
            "task_file": task,
            "user": user,
            "pid": pid,
            "assigned_gpu_ids": gpu_ids_list,
            "cuda_visible_devices": gpus_identifiers,
            "workdir": dir,
            "run_id": run_id,
            "profiled_gpu_util": float(profiled_gpu_util or 0.0),
            "profiled_memory_mib": int(profiled_memory_mib or 0),
        },
    )

    Thread(
        target=async_resolve_and_update,
        args=(pid, gpu_ids_list),
        daemon=True,
    ).start()

    return pid