from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


@dataclass
class Timer:
    start: float | None = None
    end: float | None = None

    def start_now(self) -> None:
        self.start = time.perf_counter()
        self.end = None

    def stop_now(self) -> float:
        if self.start is None:
            raise RuntimeError("Timer was not started")
        self.end = time.perf_counter()
        return self.elapsed_seconds

    @property
    def elapsed_seconds(self) -> float:
        if self.start is None:
            raise RuntimeError("Timer was not started")
        end = self.end if self.end is not None else time.perf_counter()
        return end - self.start


@contextmanager
def timed_run() -> Iterator[Timer]:
    timer = Timer()
    timer.start_now()
    try:
        yield timer
    finally:
        timer.stop_now()