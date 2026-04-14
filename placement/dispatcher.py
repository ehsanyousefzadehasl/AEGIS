from __future__ import annotations

from placement.policies import (
    select_oracle_ff,
    select_oracle_bf,
    select_oracle_magm,
    select_oracle_lug,
)


def dispatch_placement(
    *,
    policy: str,
    gpus_with_metrics,
    available_gpu_ids,
    number_of_gpus_requested: int,
    gpu_memory_requirement: int | None = None,
    gpu_memory_estimation: int | None = None,
):
    if policy == "oracle-FF":
        if gpu_memory_requirement is None:
            return None
        return select_oracle_ff(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_requirement=gpu_memory_requirement,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )
    
    if policy == "oracle-BF":
        if gpu_memory_requirement is None:
            return None
        return select_oracle_bf(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_requirement=gpu_memory_requirement,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )

    if policy == "oracle-MAGM":
        if gpu_memory_requirement is None:
            return None
        return select_oracle_magm(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_requirement=gpu_memory_requirement,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )

    if policy == "oracle-LUG":
        if gpu_memory_requirement is None:
            return None
        return select_oracle_lug(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_requirement=gpu_memory_requirement,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )

    return None