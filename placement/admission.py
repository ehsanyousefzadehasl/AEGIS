from __future__ import annotations

from placement.profiles import policy_is_exclusive_first

def use_exclusive_first_admission(policy: str) -> bool:
    return policy_is_exclusive_first(policy)


def should_dispatch_exclusive_first(
    *,
    policy: str,
    idle_and_available,
    number_of_gpus_requested: int,
) -> bool:
    if not use_exclusive_first_admission(policy):
        return False

    return len(idle_and_available) >= number_of_gpus_requested