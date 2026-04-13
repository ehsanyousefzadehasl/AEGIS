from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Optional

from .task_queue import Task, Tasks


@dataclass(frozen=True)
class SelectedJob:
    task_obj: Task
    from_recovery_queue: bool

    @property
    def user(self) -> str:
        return self.task_obj.user

    @property
    def dir(self) -> str:
        return self.task_obj.dir

    @property
    def task(self) -> str:
        return self.task_obj.task


def peek_next_job(
    main_queue: Tasks,
    recovery_queue: Tasks,
    main_lock: Lock,
    recovery_lock: Lock,
) -> Optional[SelectedJob]:
    if recovery_queue.length() != 0:
        with recovery_lock:
            task_obj = recovery_queue.check()
        return SelectedJob(task_obj=task_obj, from_recovery_queue=True)

    if main_queue.length() != 0:
        with main_lock:
            task_obj = main_queue.check()
        return SelectedJob(task_obj=task_obj, from_recovery_queue=False)

    return None


def dequeue_selected_job(
    selected: SelectedJob,
    main_queue: Tasks,
    recovery_queue: Tasks,
    main_lock: Lock,
    recovery_lock: Lock,
) -> None:
    if selected.from_recovery_queue:
        with recovery_lock:
            recovery_queue.dequeue()
    else:
        with main_lock:
            main_queue.dequeue()