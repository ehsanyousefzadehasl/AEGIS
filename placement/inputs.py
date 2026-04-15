from __future__ import annotations

from estimation.online_estimator import estimate_online_gpu_memory


def resolve_policy_inputs(
    *,
    policy: str,
    spec,
    workdir: str,
    estimator_name: str,
):
    gpu_memory_requirement = None
    gpu_memory_estimation = None

    if policy.startswith("oracle-"):
        gpu_memory_requirement = spec.gpu_memory_requirement_mib

    elif policy.startswith("EST-"):
        gpu_memory_estimation = spec.gpu_memory_estimate_mib

    elif policy.startswith("ONLINE-EST-"):
        gpu_memory_estimation = estimate_online_gpu_memory(
            spec=spec,
            workdir=workdir,
            estimator_name=estimator_name,
        )

    return gpu_memory_requirement, gpu_memory_estimation