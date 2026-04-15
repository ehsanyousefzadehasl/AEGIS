from threading import Thread

from telemetry import monitor
from server import run_ingress, run_scheduler


if __name__ == "__main__":
    Thread(target=run_ingress).start()
    Thread(target=run_scheduler).start()
    Thread(target=monitor.monitor_logger).start()
    Thread(target=monitor.top_system_logger).start()