from __future__ import annotations

from threading import Lock

from queueing.task_queue import Tasks


lock = Lock()
recover_lock = Lock()

main_queue = Tasks()
recovery_queue = Tasks()