from __future__ import annotations


def use_exclusive_first_admission(policy: str) -> bool:
    """
    Current default admission behavior.

    For now, all existing policies keep the same semantics:
    prefer exclusive placement when enough idle GPUs are available.
    """
    return True


def should_dispatch_exclusive_first(
    *,
    policy: str,
    idle_and_available,
    number_of_gpus_requested: int,
) -> bool:
    if not use_exclusive_first_admission(policy):
        return False

    return len(idle_and_available) >= number_of_gpus_requested