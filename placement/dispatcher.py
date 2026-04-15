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
    if request.policy == "oracle-FF":
        if request.gpu_memory_requirement is None:
            return None
        return select_oracle_ff(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_requirement=request.gpu_memory_requirement,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )
    
    if request.policy == "oracle-BF":
        if request.gpu_memory_requirement is None:
            return None
        return select_oracle_bf(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_requirement=request.gpu_memory_requirement,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if request.policy == "oracle-MAGM":
        if request.gpu_memory_requirement is None:
            return None
        return select_oracle_magm(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_requirement=request.gpu_memory_requirement,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if request.policy == "oracle-LUG":
        if request.gpu_memory_requirement is None:
            return None
        return select_oracle_lug(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_requirement=request.gpu_memory_requirement,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )
    
    if request.policy == "OR-RR":
        if request.round_robin_generator is None or request.gpu_ids is None:
            return None
        return select_or_rr(
            round_robin_generator=request.round_robin_generator,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
            gpu_ids=request.gpu_ids,
        )
    
    if request.policy == "OR-MAGM":
        return select_or_magm(
            gpus_with_metrics=request.gpus_with_metrics,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if request.policy == "OR-LUG":
        return select_or_lug(
            gpus_with_metrics=request.gpus_with_metrics,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if request.policy == "EST-MAGM":
        if request.gpu_memory_estimation is None:
            return None
        return select_est_magm(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_estimation=request.gpu_memory_estimation,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if request.policy == "EST-LUG":
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
    return policy in {
        "oracle-FF",
        "oracle-BF",
        "oracle-MAGM",
        "oracle-LUG",
        "OR-RR",
        "OR-MAGM",
        "OR-LUG",
        "EST-MAGM",
        "EST-LUG",
        "ONLINE-EST-MAGM",
        "ONLINE-EST-LUG",
    }