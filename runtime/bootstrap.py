from __future__ import annotations

import logging
from itertools import cycle

from config.settings import load_scheduler_settings
from telemetry import monitor
from telemetry.gpu_state import init_gpu_state


def configure_scheduler_logger():
    logging.basicConfig(
        filename="std.log",
        filemode="w",
        format="%(asctime)s %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
    )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    return logger


def initialize_scheduler_runtime():
    settings = load_scheduler_settings()

    gpu_uuids = monitor.gpu_uuids()
    gpu_ids = list(gpu_uuids)
    round_robin_generator = cycle(gpu_ids)
    gpus_state = init_gpu_state(gpu_uuids)

    handled_crashes: list[str] = []

    return {
        "settings": settings,
        "gpu_uuids": gpu_uuids,
        "gpu_ids": gpu_ids,
        "round_robin_generator": round_robin_generator,
        "gpus_state": gpus_state,
        "handled_crashes": handled_crashes,
    }