from __future__ import annotations

from placement.strategies import execute_placement_strategy
from placement.profiles import get_policy_profile
from dataclasses import dataclass


@dataclass(frozen=True)
class PlacementRequest:
    policy: str
    gpus_with_metrics: object
    available_gpu_ids: object
    number_of_gpus_requested: int
    gpu_memory_requirement: int | None = None
    gpu_memory_estimation: int | None = None
    round_robin_generator: object | None = None
    gpu_ids: object | None = None


    
def dispatch_placement(request: PlacementRequest):
    profile = get_policy_profile(request.policy)
    strategy = profile.placement_strategy
    return execute_placement_strategy(strategy, request)



def is_dispatcher_policy(policy: str) -> bool:
    return get_policy_profile(policy).uses_dispatcher