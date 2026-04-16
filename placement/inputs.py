from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from estimation.online_estimator import estimate_online_gpu_memory
from placement.profiles import get_policy_profile
from workload.job_spec import JobSpec
from workload.resource_profile import ResourceProfile


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
    profile = get_policy_profile(policy)

    if profile.estimate_source == "oracle":
        return PlacementEstimate(
            source="oracle_requirement",
            resource_profile=ResourceProfile(
                peak_memory_mib=spec.gpu_memory_requirement_mib,
                source="task_file_requirement",
            ) if spec.gpu_memory_requirement_mib is not None else None,
        )

    if profile.estimate_source == "task_file_estimate":
        return PlacementEstimate(
            source="task_file_estimate",
            resource_profile=ResourceProfile(
                peak_memory_mib=spec.gpu_memory_estimate_mib,
                source="task_file_estimate",
            ) if spec.gpu_memory_estimate_mib is not None else None,
        )

    if profile.estimate_source == "online_estimate":
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

    return None


def resolve_policy_inputs(
    *,
    policy: str,
    spec: JobSpec,
    workdir: str,
    estimator_name: str,
):
    gpu_memory_requirement = None
    gpu_memory_estimation = None

    profile = get_policy_profile(policy)

    if profile.estimate_source == "oracle":
        gpu_memory_requirement = spec.gpu_memory_requirement_mib

    elif profile.estimate_source == "task_file_estimate":
        gpu_memory_estimation = spec.gpu_memory_estimate_mib

    elif profile.estimate_source == "online_estimate":
        gpu_memory_estimation = estimate_online_gpu_memory(
            spec=spec,
            workdir=workdir,
            estimator_name=estimator_name,
        )

    return gpu_memory_requirement, gpu_memory_estimation


def get_missing_policy_input_message(
    *,
    policy: str,
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

    return None