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


def dispatch_placement(
    *,
    policy: str,
    gpus_with_metrics,
    available_gpu_ids,
    number_of_gpus_requested: int,
    gpu_memory_requirement: int | None = None,
    gpu_memory_estimation: int | None = None,
    round_robin_generator=None,
    gpu_ids=None,
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
    
    if policy == "OR-RR":
        if round_robin_generator is None or gpu_ids is None:
            return None
        return select_or_rr(
            round_robin_generator=round_robin_generator,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
            gpu_ids=gpu_ids,
        )
    
    if policy == "OR-MAGM":
        return select_or_magm(
            gpus_with_metrics=gpus_with_metrics,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )

    if policy == "OR-LUG":
        return select_or_lug(
            gpus_with_metrics=gpus_with_metrics,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )

    if policy == "EST-MAGM":
        if gpu_memory_estimation is None:
            return None
        return select_est_magm(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_estimation=gpu_memory_estimation,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )

    if policy == "EST-LUG":
        if gpu_memory_estimation is None:
            return None
        return select_est_lug(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_estimation=gpu_memory_estimation,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )

    if policy == "ONLINE-EST-MAGM":
        if gpu_memory_estimation is None:
            return None
        return select_est_magm(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_estimation=gpu_memory_estimation,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
        )

    if policy == "ONLINE-EST-LUG":
        if gpu_memory_estimation is None:
            return None
        return select_est_lug(
            gpus_with_metrics=gpus_with_metrics,
            gpu_memory_estimation=gpu_memory_estimation,
            available_gpu_ids=available_gpu_ids,
            number_of_gpus_requested=number_of_gpus_requested,
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