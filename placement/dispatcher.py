from __future__ import annotations

from placement.strategies import execute_placement_strategy
from placement.profiles import policy_placement_strategy
from placement.inputs import (
    PlacementEstimate,
    get_missing_policy_input_message,
    resolve_placement_estimate,
)
from dataclasses import dataclass


@dataclass(frozen=True)
class _PlacementRequest:
    policy: str
    gpus_with_metrics: object
    available_gpu_ids: object
    number_of_gpus_requested: int
    recovery_min_free_mib_override: int | None = None
    placement_estimate: PlacementEstimate | None = None
    round_robin_generator: object | None = None
    gpu_ids: object | None = None


def _build_placement_request(
    *,
    policy: str,
    gpus_with_metrics,
    available_gpu_ids,
    number_of_gpus_requested: int,
    recovery_min_free_mib_override: int | None = None,
    placement_estimate: PlacementEstimate | None,
    round_robin_generator=None,
    gpu_ids=None,
):

    return _PlacementRequest(
        policy=policy,
        gpus_with_metrics=gpus_with_metrics,
        available_gpu_ids=available_gpu_ids,
        number_of_gpus_requested=number_of_gpus_requested,
        recovery_min_free_mib_override=recovery_min_free_mib_override,
        placement_estimate=placement_estimate,
        round_robin_generator=round_robin_generator,
        gpu_ids=gpu_ids,
    )


def _normalize_assigned_gpu_ids(strategy: str, assigned_gpus):
    if assigned_gpus is None:
        return None

    if strategy == "or_rr":
        return assigned_gpus

    return assigned_gpus.index

def dispatch_placement(request: _PlacementRequest):
    strategy = policy_placement_strategy(request.policy)
    assigned_gpus = execute_placement_strategy(strategy, request)
    return _normalize_assigned_gpu_ids(strategy, assigned_gpus)

def dispatch_policy_placement(
    *,
    policy: str,
    gpus_with_metrics,
    available_gpu_ids,
    number_of_gpus_requested: int,
    placement_estimate: PlacementEstimate | None,
    round_robin_generator=None,
    gpu_ids=None,
    recovery_min_free_mib_override=None,
):
    request = _build_placement_request(
        policy=policy,
        gpus_with_metrics=gpus_with_metrics,
        available_gpu_ids=available_gpu_ids,
        number_of_gpus_requested=number_of_gpus_requested,
        placement_estimate=placement_estimate,
        round_robin_generator=round_robin_generator,
        gpu_ids=gpu_ids,
        recovery_min_free_mib_override=recovery_min_free_mib_override,
    )
    return dispatch_placement(request)

def resolve_policy_placement_estimate(
    *,
    policy: str,
    spec,
    workdir: str,
    estimator_name: str,
) -> PlacementEstimate | None:
    return resolve_placement_estimate(
        policy=policy,
        spec=spec,
        workdir=workdir,
        estimator_name=estimator_name,
    )

def validate_policy_placement(
    *,
    policy: str,
    task: str,
    estimator_name: str,
    placement_estimate: PlacementEstimate | None,
) -> str | None:
    return get_missing_policy_input_message(
        policy=policy,
        task=task,
        estimator_name=estimator_name,
        placement_estimate=placement_estimate,
    )