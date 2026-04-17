from __future__ import annotations

from placement.strategies import execute_placement_strategy
from placement.profiles import get_policy_profile, policy_placement_strategy
from placement.inputs import PlacementEstimate
from dataclasses import dataclass


@dataclass(frozen=True)
class PlacementRequest:
    policy: str
    gpus_with_metrics: object
    available_gpu_ids: object
    number_of_gpus_requested: int
    # Legacy scalar inputs remain for existing policies; placement_estimate is the normalized path.
    gpu_memory_requirement: int | None = None
    gpu_memory_estimation: int | None = None
    placement_estimate: PlacementEstimate | None = None
    round_robin_generator: object | None = None
    gpu_ids: object | None = None

    
def dispatch_placement(request: PlacementRequest):
    strategy = policy_placement_strategy(request.policy)
    return execute_placement_strategy(strategy, request)



def is_dispatcher_policy(policy: str) -> bool:
    return get_policy_profile(policy).uses_dispatcher