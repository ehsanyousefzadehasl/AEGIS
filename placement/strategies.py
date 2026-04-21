from __future__ import annotations

from placement.inputs import (
    resolve_peak_memory_estimation_from_estimate,
    resolve_peak_memory_requirement_from_estimate,
)

from placement.policies import (
    select_oracle_ff,
    select_oracle_bf,
    select_oracle_magm,
    select_oracle_lug,
    select_or_rr,
    select_or_magm,
    select_or_lug,
    select_est_bf,
    select_est_magm,
    select_est_lug,
)

def _resolve_gpu_memory_requirement(request):
    return resolve_peak_memory_requirement_from_estimate(
        placement_estimate=request.placement_estimate,
    )

def _resolve_gpu_memory_estimation(request):
    return resolve_peak_memory_estimation_from_estimate(
        policy=request.policy,
        placement_estimate=request.placement_estimate,
    )

def _execute_oracle_selector(selector, request):
    gpu_memory_requirement = _resolve_gpu_memory_requirement(request)
    if gpu_memory_requirement is None:
        return None

    return selector(
        gpus_with_metrics=request.gpus_with_metrics,
        gpu_memory_requirement=gpu_memory_requirement,
        available_gpu_ids=request.available_gpu_ids,
        number_of_gpus_requested=request.number_of_gpus_requested,
    )


def _execute_or_selector(selector, request):
    return selector(
        gpus_with_metrics=request.gpus_with_metrics,
        available_gpu_ids=request.available_gpu_ids,
        number_of_gpus_requested=request.number_of_gpus_requested,
        recovery_min_free_mib_override=request.recovery_min_free_mib_override,
    )


def _execute_est_selector(selector, request):
    gpu_memory_estimation = _resolve_gpu_memory_estimation(request)
    if gpu_memory_estimation is None:
        return None

    return selector(
        gpus_with_metrics=request.gpus_with_metrics,
        gpu_memory_estimation=gpu_memory_estimation,
        available_gpu_ids=request.available_gpu_ids,
        number_of_gpus_requested=request.number_of_gpus_requested,
    )

def _execute_or_rr_selector(selector, request):
    if request.round_robin_generator is None or request.gpu_ids is None:
        return None

    return selector(
        round_robin_generator=request.round_robin_generator,
        available_gpu_ids=request.available_gpu_ids,
        number_of_gpus_requested=request.number_of_gpus_requested,
        gpu_ids=request.gpu_ids,
    )


_STRATEGY_REGISTRY = {
    "oracle_ff": (_execute_oracle_selector, select_oracle_ff),
    "oracle_bf": (_execute_oracle_selector, select_oracle_bf),
    "oracle_magm": (_execute_oracle_selector, select_oracle_magm),
    "oracle_lug": (_execute_oracle_selector, select_oracle_lug),
    "or_rr": (_execute_or_rr_selector, select_or_rr),
    "or_magm": (_execute_or_selector, select_or_magm),
    "or_lug": (_execute_or_selector, select_or_lug),
    "est_bf": (_execute_est_selector, select_est_bf),
    "est_magm": (_execute_est_selector, select_est_magm),
    "est_lug": (_execute_est_selector, select_est_lug),
}


def execute_placement_strategy(strategy: str, request):
    entry = _STRATEGY_REGISTRY.get(strategy)
    if entry is None:
        return None

    executor, selector = entry
    return executor(selector, request)