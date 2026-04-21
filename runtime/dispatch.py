from __future__ import annotations

from threading import Thread
from collections.abc import Iterable

from queueing.selection import dequeue_selected_job
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
) -> int | None:
    gpu_ids_list = list(assigned_gpu_ids)

    task_obj.set_service_time(now)
    task_obj.set_status("dispatched")

    gpus_identifiers = format_gpu_identifiers(gpu_ids_list)
    command = command_generator(dir, gpus_identifiers, command_to_execute, now, task_obj)

    dequeue_selected_job(selected, main_queue, recovery_queue, main_lock, recovery_lock)

    to_write = build_recovery_header(
        dir,
        environment,
        command_to_execute,
        task,
        user,
        task_obj.task_id,
        task_obj.user_submit_time,
        now,
    )

    logger.info(f"dispatched {task_obj.task_id} - {task_obj.task} - {gpus_identifiers}")
    append_jsonl_event(
        event_path=f"{dir}/events.jsonl",
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
        },
    )

    Thread(target=command_executor, args=(to_write,)).start()
    pid = launch_and_get_pid(command)

    if pid is None:
        append_jsonl_event(
            event_path=f"{dir}/events.jsonl",
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
            },
        )
        logger.error(f"Failed to capture PID for {task_obj.task_id}; leaving GPUs available")
        return None

    for gpu_uuid in gpu_ids_list:
        launch_task(
            gpu_uuid,
            pid,
            task_id=str(task_obj.task_id),
            event_path=f"{dir}/events.jsonl",
        )
    
    append_jsonl_event(
        event_path=f"{dir}/events.jsonl",
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
        },
    )

    Thread(
        target=async_resolve_and_update,
        args=(pid, gpu_ids_list),
        daemon=True,
    ).start()

    return pid