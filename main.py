from threading import Thread

from telemetry import monitor
from scheduler import run_scheduler, runtime_state
from runtime.state import main_queue, lock
from runtime.submission_server import run_submission_server
import socket

import os
from evaluation.experiments.eval_watcher import wait_for_eval_completion


if __name__ == "__main__":
    host = socket.gethostname()

    Thread(
        target=run_submission_server,
        kwargs={
            "main_queue": main_queue,
            "main_lock": lock,
            "host": host,
            "port": 5001,
            "event_path": runtime_state.event_path,
            "run_id": runtime_state.run_id,
        },
    ).start()

    Thread(target=run_scheduler).start()
    Thread(target=monitor.monitor_logger).start()
    Thread(target=monitor.top_system_logger).start()

    if os.getenv("AEGIS_EVAL_MODE") == "1":
        Thread(
            target=wait_for_eval_completion,
            kwargs={
                "event_path": runtime_state.event_path,
                "expected_tasks": int(os.getenv("AEGIS_EXPECTED_TASKS", "0")),
                "idle_exit_minutes": float(os.getenv("AEGIS_EVAL_IDLE_EXIT_MINUTES", "2")),
            },
            daemon=True,
        ).start()