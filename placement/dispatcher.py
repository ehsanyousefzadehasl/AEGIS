from __future__ import annotations

from placement.strategies import execute_placement_strategy
from placement.profiles import policy_placement_strategy, policy_uses_dispatcher
from placement.inputs import (
    PlacementEstimate,
    resolve_legacy_peak_memory_policy_inputs,
)
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


def build_placement_request(
    *,
    policy: str,
    gpus_with_metrics,
    available_gpu_ids,
    number_of_gpus_requested: int,
    placement_estimate: PlacementEstimate | None,
    round_robin_generator=None,
    gpu_ids=None,
):
    gpu_memory_requirement, gpu_memory_estimation = (
        resolve_legacy_peak_memory_policy_inputs(
            placement_estimate=placement_estimate,
        )
    )

    return PlacementRequest(
        policy=policy,
        gpus_with_metrics=gpus_with_metrics,
        available_gpu_ids=available_gpu_ids,
        number_of_gpus_requested=number_of_gpus_requested,
        gpu_memory_requirement=gpu_memory_requirement,
        gpu_memory_estimation=gpu_memory_estimation,
        placement_estimate=placement_estimate,
        round_robin_generator=round_robin_generator,
        gpu_ids=gpu_ids,
    )


def dispatch_placement(request: PlacementRequest):
    strategy = policy_placement_strategy(request.policy)
    return execute_placement_strategy(strategy, request)



def is_dispatcher_policy(policy: str) -> bool:
    return policy_uses_dispatcher(policy)