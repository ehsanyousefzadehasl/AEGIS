from __future__ import annotations

from workload.resource_profile import get_resource_profile_metric

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

def _get_required_profile_metrics(request):
    profile = get_policy_profile(request.policy)
    metrics: dict[str, object] = {}

    for metric_name in profile.required_profile_metrics:
        value = _get_profile_metric(request, metric_name)
        if value is None:
            return None
        metrics[metric_name] = value

    return metrics

def _get_profile_metric(request, metric_name: str):
    if request.placement_estimate is None:
        return None
    return get_resource_profile_metric(
        request.placement_estimate.resource_profile,
        metric_name,
    )


def _get_peak_memory_mib_from_estimate(request):
    return _get_profile_metric(request, "peak_memory_mib")

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
            required_profile_metrics = _get_required_profile_metrics(request)
            if required_profile_metrics is not None:
                gpu_memory_estimation = required_profile_metrics.get("peak_memory_mib")

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
            required_profile_metrics = _get_required_profile_metrics(request)
            if required_profile_metrics is not None:
                gpu_memory_estimation = required_profile_metrics.get("peak_memory_mib")

        if gpu_memory_estimation is None:
            return None
        
        return select_est_lug(
            gpus_with_metrics=request.gpus_with_metrics,
            gpu_memory_estimation=gpu_memory_estimation,
            available_gpu_ids=request.available_gpu_ids,
            number_of_gpus_requested=request.number_of_gpus_requested,
        )

    return None