from threading import Thread

from telemetry import monitor
from scheduler import run_scheduler, main_queue, lock
from runtime.submission_server import run_submission_server
import socket

if __name__ == "__main__":
    host = socket.gethostname()

    Thread(
        target=run_submission_server,
        kwargs={
            "main_queue": main_queue,
            "main_lock": lock,
            "host": host,
            "port": 5001,
        },
    ).start()

    Thread(target=run_scheduler).start()
    Thread(target=monitor.monitor_logger).start()
    Thread(target=monitor.top_system_logger).start()