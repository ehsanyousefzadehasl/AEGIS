from __future__ import annotations

import pandas as pd

from placement.candidate_selection import build_candidate_gpus


def select_oracle_bf(
    *,
    gpus_with_metrics: pd.DataFrame,
    gpu_memory_requirement: int,
    available_gpu_ids,
    number_of_gpus_requested: int,
):
    candidate_gpus = gpus_with_metrics.loc[
        gpus_with_metrics["GPU_mem_available"] >= (gpu_memory_requirement + 2048)
    ].copy()

    avail = set(available_gpu_ids)
    candidate_gpus = candidate_gpus.loc[candidate_gpus.index.isin(avail)].copy()

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
):
    candidate_gpus = gpus_with_metrics.loc[
        gpus_with_metrics["GPU_mem_available"] >= (gpu_memory_requirement + 2048)
    ].copy()

    avail = set(available_gpu_ids)
    candidate_gpus = candidate_gpus.loc[candidate_gpus.index.isin(avail)].copy()

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
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_requirement + 2048,
        available_gpu_ids=available_gpu_ids,
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
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=5120,
        available_gpu_ids=available_gpu_ids,
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
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=5120,
        available_gpu_ids=available_gpu_ids,
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
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_estimation + 2048,
        available_gpu_ids=available_gpu_ids,
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
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_estimation + 2048,
        available_gpu_ids=available_gpu_ids,
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
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_estimation + 2048,
        available_gpu_ids=available_gpu_ids,
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
):
    candidate_gpus = build_candidate_gpus(
        gpus_with_metrics=gpus_with_metrics,
        min_free_mib=gpu_memory_requirement + 2048,
        available_gpu_ids=available_gpu_ids,
        use_utilization_gate=True,
    )

    if candidate_gpus.empty or len(candidate_gpus) < number_of_gpus_requested:
        return None

    return candidate_gpus.head(number_of_gpus_requested)