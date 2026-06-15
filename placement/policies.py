from __future__ import annotations

import pandas as pd

GPU_MEMORY_GUARD_MIB = 512

from placement.candidate_selection import RiskThresholds, build_candidate_gpus
from runtime import gpu_allocations

def select_oracle_bf(
    *,
    gpus_with_metrics: pd.DataFrame,
    gpu_memory_requirement: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
    risk_thresholds: RiskThresholds | None = None,
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_requirement + GPU_MEMORY_GUARD_MIB,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    sorted_ = candidate_gpus.sort_values(
        by="GPU_mem_available",
        ascending=True,
        kind="mergesort",
    )
    return sorted_.head(number_of_gpus_requested)


def select_oracle_magm(
    *,
    gpus_with_metrics: pd.DataFrame,
    gpu_memory_requirement: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
    risk_thresholds: RiskThresholds | None = None,
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_requirement + GPU_MEMORY_GUARD_MIB,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    sorted_ = candidate_gpus.sort_values(
        by="GPU_mem_available",
        ascending=False,
        kind="mergesort",
    )
    return sorted_.head(number_of_gpus_requested)


def select_oracle_lug(
    *,
    gpus_with_metrics: pd.DataFrame,
    gpu_memory_requirement: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
    risk_thresholds: RiskThresholds | None = None,
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_requirement + GPU_MEMORY_GUARD_MIB,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    sorted_ = candidate_gpus.sort_values(
        by="smact",
        ascending=True,
        kind="mergesort",
    )
    return sorted_.head(number_of_gpus_requested)



def select_or_magm(
    *,
    gpus_with_metrics: pd.DataFrame,
    available_gpu_ids,
    number_of_gpus_requested: int,
    recovery_min_free_mib_override: int | None = None,
    risk_thresholds: RiskThresholds | None = None,
):
    min_free_mib = 5120
    if recovery_min_free_mib_override is not None:
        min_free_mib = max(min_free_mib, recovery_min_free_mib_override)

    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=min_free_mib,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    sorted_ = candidate_gpus.sort_values(
        by="GPU_mem_available",
        ascending=False,
        kind="mergesort",
    )
    return sorted_.head(number_of_gpus_requested)


def select_or_lug(
    *,
    gpus_with_metrics: pd.DataFrame,
    available_gpu_ids,
    number_of_gpus_requested: int,
    recovery_min_free_mib_override: int | None = None,
    risk_thresholds: RiskThresholds | None = None,
):
    min_free_mib = 5120
    if recovery_min_free_mib_override is not None:
        min_free_mib = max(min_free_mib, recovery_min_free_mib_override)

    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=min_free_mib,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    sorted_ = candidate_gpus.sort_values(
        by="smact",
        ascending=True,
        kind="mergesort",
    )
    return sorted_.head(number_of_gpus_requested)


def select_est_magm(
    *,
    gpus_with_metrics: pd.DataFrame,
    gpu_memory_estimation: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
    risk_thresholds: RiskThresholds | None = None,
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_estimation + GPU_MEMORY_GUARD_MIB,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    sorted_ = candidate_gpus.sort_values(
        by="GPU_mem_available",
        ascending=False,
        kind="mergesort",
    )
    return sorted_.head(number_of_gpus_requested)

def select_est_bf(
    *,
    gpus_with_metrics: pd.DataFrame,
    gpu_memory_estimation: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
    risk_thresholds: RiskThresholds | None = None,
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_estimation + GPU_MEMORY_GUARD_MIB,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    sorted_ = candidate_gpus.sort_values(
        by="GPU_mem_available",
        ascending=True,
        kind="mergesort",
    )
    return sorted_.head(number_of_gpus_requested)


def select_est_lug(
    *,
    gpus_with_metrics: pd.DataFrame,
    gpu_memory_estimation: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
    risk_thresholds: RiskThresholds | None = None,
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_estimation + GPU_MEMORY_GUARD_MIB,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    sorted_ = candidate_gpus.sort_values(
        by="smact",
        ascending=True,
        kind="mergesort",
    )
    return sorted_.head(number_of_gpus_requested)

def select_horus(
    *,
    gpu_memory_estimation: int,
    candidate_horus_gpu_util: float,
    available_gpu_ids,
    number_of_gpus_requested: int,
    utilization_budget: float = 100.0,
):
    del gpu_memory_estimation

    reserved = gpu_allocations.reserved_profiled_gpu_util_by_gpu()

    rows = []
    for gpu_id in available_gpu_ids:
        reserved_util = float(reserved.get(str(gpu_id), 0.0))
        projected_util = reserved_util + float(candidate_horus_gpu_util)

        if projected_util <= float(utilization_budget):
            rows.append(
                {
                    "gpu_id": str(gpu_id),
                    "horus_reserved_gpu_util": reserved_util,
                    "horus_projected_gpu_util": projected_util,
                }
            )

    candidate_gpus = pd.DataFrame(rows)

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    candidate_gpus = candidate_gpus.set_index("gpu_id")

    return candidate_gpus.sort_values(
        by="horus_projected_gpu_util",
        ascending=True,
        kind="mergesort",
    ).head(number_of_gpus_requested)


def select_lucid(
    *,
    peak_memory_mib: int,
    lucid_ss: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
    gpu_memory_capacity_mib: int = 40960,
    memory_guard_mib: int = GPU_MEMORY_GUARD_MIB,
    gss_capacity: int = 2,
    max_jobs_per_gpu: int = 2,
):
    usable_memory_mib = int(gpu_memory_capacity_mib) - int(memory_guard_mib)

    rows = []
    for gpu_id in available_gpu_ids:
        gid = str(gpu_id)
        allocations = gpu_allocations.allocations_for_gpu(gid)

        current_job_count = len(allocations)
        reserved_memory_mib = sum(int(a.profiled_memory_mib or 0) for a in allocations)
        
        reserved_lucid_ss = sum(int(a.lucid_ss or 0) for a in allocations)

        projected_job_count = current_job_count + 1
        projected_memory_mib = reserved_memory_mib + int(peak_memory_mib)
        projected_lucid_ss = reserved_lucid_ss + int(lucid_ss)

        if projected_job_count > int(max_jobs_per_gpu):
            continue
        if projected_lucid_ss > int(gss_capacity):
            continue
        if projected_memory_mib > usable_memory_mib:
            continue

        rows.append(
            {
                "gpu_id": gid,
                "lucid_reserved_memory_mib": reserved_memory_mib,
                "lucid_projected_memory_mib": projected_memory_mib,
                "lucid_reserved_ss": reserved_lucid_ss,
                "lucid_projected_ss": projected_lucid_ss,
                "lucid_current_job_count": current_job_count,
                "lucid_projected_job_count": projected_job_count,
            }
        )

    if not rows or len(rows) < number_of_gpus_requested:
        return None

    candidate_gpus = pd.DataFrame(rows).set_index("gpu_id")

    return candidate_gpus.sort_values(
        by=["lucid_projected_ss", "lucid_projected_memory_mib"],
        ascending=[True, True],
        kind="mergesort",
    ).head(number_of_gpus_requested)


def select_or_rr(
    *,
    round_robin_generator,
    available_gpu_ids,
    number_of_gpus_requested: int,
    gpu_ids,
):
    avail = set(available_gpu_ids)
    assigned_gpus = []

    n = len(gpu_ids)
    seen = set()

    while len(assigned_gpus) < number_of_gpus_requested and len(seen) < n:
        gid = next(round_robin_generator)
        if gid in seen:
            continue
        seen.add(gid)
        if gid in avail and gid not in assigned_gpus:
            assigned_gpus.append(gid)

    if len(assigned_gpus) < number_of_gpus_requested:
        return None

    return assigned_gpus


def select_oracle_ff(
    *,
    gpus_with_metrics: pd.DataFrame,
    gpu_memory_requirement: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
    risk_thresholds: RiskThresholds | None = None,
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_requirement + GPU_MEMORY_GUARD_MIB,
        available_gpu_ids=available_gpu_ids,
        risk_thresholds=risk_thresholds,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    return candidate_gpus.head(number_of_gpus_requested)