from __future__ import annotations

import os
from runtime.events import append_jsonl_event

def recovery(
    *,
    dirs,
    handled_crashes,
    task_cls,
    recovery_queue,
    recovery_lock,
    logger,
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

                tmp_dir = recovery_data[0]
                tmp_file = recovery_data[3]
                tmp_user = recovery_data[4]
                tmp_task_id = recovery_data[5][:-1]

                recovered_task = task_cls(tmp_user, tmp_dir, tmp_file)
                recovered_task.set_id(tmp_task_id)
                recovered_task.set_if_recovered()

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