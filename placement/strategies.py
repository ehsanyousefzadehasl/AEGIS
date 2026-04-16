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

def _get_peak_memory_mib_from_estimate(request):
    if request.placement_estimate is None:
        return None
    if request.placement_estimate.resource_profile is None:
        return None
    return request.placement_estimate.resource_profile.peak_memory_mib

def execute_placement_strategy(strategy: str, request):
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
        gpu_memory_estimation = request.gpu_memory_estimation
        if gpu_memory_estimation is None:
            gpu_memory_estimation = _get_peak_memory_mib_from_estimate(request)
        if gpu_memory_estimation is None:
            return None
        
        return select_est_magm(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_estimation=gpu_memory_estimation,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    if strategy == "est_lug":
        gpu_memory_estimation = request.gpu_memory_estimation
        if gpu_memory_estimation is None:
            gpu_memory_estimation = _get_peak_memory_mib_from_estimate(request)
        if gpu_memory_estimation is None:
            return None
        
        return select_est_lug(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_estimation=gpu_memory_estimation,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    return None