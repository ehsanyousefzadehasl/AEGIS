from __future__ import annotations


def should_dispatch_exclusive_first(
    *,
    idle_and_available,
    number_of_gpus_requested: int,
) -> bool:
    return len(idle_and_available) >= number_of_gpus_requested