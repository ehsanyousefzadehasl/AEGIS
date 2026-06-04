from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
import uuid

from dataclasses import dataclass
from itertools import cycle

from config.settings import SchedulerSettings, load_scheduler_settings
from telemetry import monitor
from telemetry.gpu_state import init_gpu_state


@dataclass(frozen=True)
class SchedulerRuntime:
    settings: SchedulerSettings
    gpu_uuids: object
    gpu_ids: list[str]
    round_robin_generator: object
    gpus_state: object
    handled_crashes: list[str]
    run_id: str
    event_path: str

def configure_scheduler_logger():
    settings = load_scheduler_settings()
    recovery_dir = Path(settings.recovery_dir)
    recovery_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=str(recovery_dir / "std.log"),
        filemode="w",
        format="%(asctime)s %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
    )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    return logger


def initialize_scheduler_runtime() -> SchedulerRuntime:
    settings = load_scheduler_settings()

    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    recovery_dir = Path(settings.recovery_dir)
    recovery_dir.mkdir(parents=True, exist_ok=True)
    event_path = str(recovery_dir / f"events-{run_id}.jsonl")

    gpu_uuids = monitor.gpu_uuids()
    gpu_ids = list(gpu_uuids)
    round_robin_generator = cycle(gpu_ids)
    gpus_state = init_gpu_state(gpu_uuids)

    handled_crashes: list[str] = []

    return SchedulerRuntime(
        settings=settings,
        gpu_uuids=gpu_uuids,
        gpu_ids=gpu_ids,
        round_robin_generator=round_robin_generator,
        gpus_state=gpus_state,
        handled_crashes=handled_crashes,
        run_id=run_id,
        event_path=event_path,
    )