from __future__ import annotations

from placement.profiles import get_policy_profile


def use_exclusive_first_admission(policy: str) -> bool:
    return get_policy_profile(policy).exclusive_first


def should_dispatch_exclusive_first(
    *,
    policy: str,
    idle_and_available,
    number_of_gpus_requested: int,
) -> bool:
    if not use_exclusive_first_admission(policy):
        return False

    return len(idle_and_available) >= number_of_gpus_requested