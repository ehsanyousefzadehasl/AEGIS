from __future__ import annotations

from estimation.online_estimator import estimate_online_gpu_memory
from placement.profiles import get_policy_profile

def resolve_policy_inputs(
    *,
    policy: str,
    spec,
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