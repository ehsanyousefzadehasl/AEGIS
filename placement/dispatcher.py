from __future__ import annotations

from placement.policies import (
    select_oracle_ff,
    select_oracle_bf,
    select_oracle_magm,
    select_oracle_lug,
    select_or_rr,
    select_or_magm,
    select_or_lug,
    select_est_magm,
    select_est_lug,
)

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

    if strategy == "oracle_ff":
        if request.gpu_memory_requirement is None:
            return None
        return select_oracle_ff(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_requirement=request.gpu_memory_requirement,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )
    
    if strategy == "oracle_bf":
        if request.gpu_memory_requirement is None:
            return None
        return select_oracle_bf(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_requirement=request.gpu_memory_requirement,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if strategy == "oracle_magm":
        if request.gpu_memory_requirement is None:
            return None
        return select_oracle_magm(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_requirement=request.gpu_memory_requirement,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if strategy == "oracle_lug":
        if request.gpu_memory_requirement is None:
            return None
        return select_oracle_lug(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_requirement=request.gpu_memory_requirement,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )
    
    if strategy == "or_rr":
        if request.round_robin_generator is None or request.gpu_ids is None:
            return None
        return select_or_rr(
            round_robin_generator=request.round_robin_generator,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
            gpu_ids=request.gpu_ids,
        )
    
    if strategy == "or_magm":
        return select_or_magm(
            gpus_with_metrics=request.gpus_with_metrics,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if strategy == "or_lug":
        return select_or_lug(
            gpus_with_metrics=request.gpus_with_metrics,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if strategy == "est_magm":
        if request.gpu_memory_estimation is None:
            return None
        return select_est_magm(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_estimation=request.gpu_memory_estimation,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if strategy == "est_lug":
        if request.gpu_memory_estimation is None:
            return None
        return select_est_lug(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_estimation=request.gpu_memory_estimation,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if request.policy == "ONLINE-EST-MAGM":
        if request.gpu_memory_estimation is None:
            return None
        return select_est_magm(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_estimation=request.gpu_memory_estimation,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if request.policy == "ONLINE-EST-LUG":
        if request.gpu_memory_estimation is None:
            return None
        return select_est_lug(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_estimation=request.gpu_memory_estimation,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )
    return None



def is_dispatcher_policy(policy: str) -> bool:
    return get_policy_profile(policy).uses_dispatcher