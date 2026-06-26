from dataclasses import dataclass
import pandas as pd


@dataclass
class RiskThresholds:
    smact: float = 0.65
    smocc: float = 0.35
    drama: float = 0.50
    gpu_utilization: float = 70.0
    runtime_pressure_backend: str = "dcgm"


def apply_memory_filter(
    gpus_with_metrics: pd.DataFrame,
    min_free_mib: int,
) -> pd.DataFrame:
    return gpus_with_metrics.loc[
        gpus_with_metrics["GPU_mem_available"] >= min_free_mib
    ].copy()


def apply_utilization_gate(
    candidate_gpus: pd.DataFrame,
    risk_thresholds: RiskThresholds,
    enabled: bool = True,
) -> pd.DataFrame:
    if not enabled:
        return candidate_gpus.copy()

    backend = str(
        getattr(risk_thresholds, "runtime_pressure_backend", "dcgm")
    ).lower()

    if backend in {"none", "memory_only", "memory-only"}:
        return candidate_gpus.copy()

    if backend in {"nvidia_smi", "nvidia-smi", "smi"}:
        if "gpu_utilization" not in candidate_gpus.columns:
            return candidate_gpus.copy()

        util = pd.to_numeric(
            candidate_gpus["gpu_utilization"],
            errors="coerce",
        )

        # Fail closed for the nvidia-smi backend: missing utilization means
        # the runtime pressure signal is unavailable, not that the GPU is idle.
        valid = util.notna()
        candidates = candidate_gpus.loc[valid].copy()
        util = util.loc[candidates.index]

        return candidates.loc[
            util < float(risk_thresholds.gpu_utilization)
        ].copy()

    temp_ = candidate_gpus
    return temp_.loc[
        ~(
            (temp_["smact"] >= risk_thresholds.smact)
            & (
                (temp_["smocc"] >= risk_thresholds.smocc)
                | (temp_["drama"] >= risk_thresholds.drama)
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
    risk_thresholds: RiskThresholds | None = None,
    use_utilization_gate: bool = True,
) -> pd.DataFrame:
    thresholds = risk_thresholds or RiskThresholds()
    candidates = apply_memory_filter(gpus_with_metrics, min_free_mib)
    candidates = apply_utilization_gate(
        candidates,
        risk_thresholds=thresholds,
        enabled=use_utilization_gate,
    )
    candidates = apply_availability_filter(candidates, available_gpu_ids)
    return candidates