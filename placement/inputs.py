from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from estimation.online_estimator import estimate_online_gpu_memory
from placement.profiles import (
    get_policy_profile,
    policy_estimate_source,
    policy_required_profile_metrics,
)
from workload.job_spec import JobSpec
from workload.resource_profile import (
    ResourceProfile,
    resolve_required_profile_metrics,
)

@dataclass(frozen=True)
class PlacementEstimate:
    source: str
    resource_profile: ResourceProfile | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def resolve_placement_estimate(
    *,
    spec: JobSpec,
    policy: str,
    workdir: str,
    estimator_name: str,
) -> PlacementEstimate | None:
    estimate_source = policy_estimate_source(policy)

    if estimate_source == "oracle":
        return PlacementEstimate(
            source="oracle_requirement",
            resource_profile=ResourceProfile(
                peak_memory_mib=spec.gpu_memory_requirement_mib,
                source="task_file_requirement",
            ) if spec.gpu_memory_requirement_mib is not None else None,
        )

    if estimate_source == "task_file_estimate":
        return PlacementEstimate(
            source="task_file_estimate",
            resource_profile=ResourceProfile(
                peak_memory_mib=spec.gpu_memory_estimate_mib,
                source="task_file_estimate",
            ) if spec.gpu_memory_estimate_mib is not None else None,
        )

    if estimate_source == "online_estimate":
        online_estimate_mib = estimate_online_gpu_memory(
            spec=spec,
            workdir=workdir,
            estimator_name=estimator_name,
        )
        return PlacementEstimate(
            source="online_estimate",
            resource_profile=ResourceProfile(
                peak_memory_mib=online_estimate_mib,
                source="online_estimate",
            ) if online_estimate_mib is not None else None,
        )
    
    if estimate_source == "profiled_metadata":
        return PlacementEstimate(
            source="profiled_metadata",
            resource_profile=spec.resource_profile,
        )
    
    return None


def resolve_policy_inputs(
    *,
    policy: str,
    spec: JobSpec,
    workdir: str,
    estimator_name: str,
):
    estimate = resolve_placement_estimate(
        spec=spec,
        policy=policy,
        workdir=workdir,
        estimator_name=estimator_name,
    )

    gpu_memory_requirement = None
    gpu_memory_estimation = None

    if estimate is None or estimate.resource_profile is None:
        return gpu_memory_requirement, gpu_memory_estimation

    peak_memory_mib = estimate.resource_profile.peak_memory_mib

    estimate_source = policy_estimate_source(policy)
    if estimate_source == "oracle":
        gpu_memory_requirement = peak_memory_mib
    elif estimate_source in {"task_file_estimate", "online_estimate"}:
        gpu_memory_estimation = peak_memory_mib

    return gpu_memory_requirement, gpu_memory_estimation


def get_missing_policy_input_message(
    *,
    policy: str,
    spec: JobSpec,
    task: str,
    estimator_name: str,
    gpu_memory_requirement,
    gpu_memory_estimation,
) -> str | None:
    profile = get_policy_profile(policy)

    if profile.estimate_source == "oracle" and gpu_memory_requirement is None:
        return f"Could not parse GPU memory requirement for task {task}"

    if profile.estimate_source in {"task_file_estimate", "online_estimate"} and gpu_memory_estimation is None:
        return f"Could not parse GPU memory estimate for task {task} using estimator {estimator_name}"

    if profile.estimate_source == "profiled_metadata":
        required_metrics = resolve_required_profile_metrics(
            spec.resource_profile,
            policy_required_profile_metrics(policy),
        )
        if required_metrics is None:
            return f"Could not resolve required profiled metrics for task {task}"
    
    return None