from dataclasses import dataclass
import pandas as pd


@dataclass
class RiskThresholds:
    smact: float = 0.80
    smocc: float = 0.45
    drama: float = 0.40


def apply_memory_filter(
    gpus_with_metrics: pd.DataFrame,
    min_free_mib: int,
) -> pd.DataFrame:
    return gpus_with_metrics.loc[
        gpus_with_metrics["GPU_mem_available"] >= min_free_mib
    ].copy()


def apply_utilization_gate(
    candidate_gpus: pd.DataFrame,
    thresholds: RiskThresholds,
    enabled: bool = True,
) -> pd.DataFrame:
    if not enabled:
        return candidate_gpus.copy()

    temp_ = candidate_gpus
    return temp_.loc[
        ~(
            (temp_["smact"] >= thresholds.smact)
            & (
                (temp_["smocc"] >= thresholds.smocc)
                | (temp_["drama"] >= thresholds.drama)
            )
        )
    ].copy()


def apply_availability_filter(
    candidate_gpus: pd.DataFrame,
    available_gpu_ids,
) -> pd.DataFrame:
    avail = set(available_gpu_ids)
    return candidate_gpus.loc[candidate_gpus.index.isin(avail)].copy()


def build_candidate_gpus(
    gpus_with_metrics: pd.DataFrame,
    min_free_mib: int,
    available_gpu_ids,
    thresholds: RiskThresholds | None = None,
    use_utilization_gate: bool = True,
) -> pd.DataFrame:
    thresholds = thresholds or RiskThresholds()
    candidates = apply_memory_filter(gpus_with_metrics, min_free_mib)
    candidates = apply_utilization_gate(
        candidates,
        thresholds=thresholds,
        enabled=use_utilization_gate,
    )
    candidates = apply_availability_filter(candidates, available_gpu_ids)
    return candidates