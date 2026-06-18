from __future__ import annotations

from dataclasses import dataclass

from config.load_yaml import load_yaml
from placement.profiles import get_policy_profile, policy_requires_estimator


@dataclass(frozen=True)
class SchedulerSettings:
    policy: str
    estimator: str
    recovery_dir: str
    recovery_bucket_mode: str
    recovery_percentage_buckets: tuple[float, ...]
    recovery_fixed_bins_mib: tuple[int, ...]
    recovery_max_step_mib: int
    patience: str
    monitoring_window_size: str
    risk_smact_threshold: float
    risk_smocc_threshold: float
    risk_drama_threshold: float
    runtime_pressure_backend: str
    gpu_utilization_threshold: float


def load_scheduler_settings() -> SchedulerSettings:
    cfg = load_yaml()

    policy = cfg.get("mapper", {}).get("policy", "exclusive")
    get_policy_profile(policy)

    estimator = cfg.get("mapper", {}).get("estimator", "None")
    if policy_requires_estimator(policy) and estimator == "None":
        raise ValueError(f"Policy '{policy}' requires a configured estimator")

    recovery_cfg = cfg.get("recovery", {})

    recovery_bucket_mode = recovery_cfg.get(
        "bucket_mode",
        "percentage_buckets_with_max_step",
    )
    allowed_bucket_modes = {
        "fixed_bins",
        "percentage_buckets",
        "percentage_buckets_with_max_step",
    }
    if recovery_bucket_mode not in allowed_bucket_modes:
        raise ValueError(
            f"Unsupported recovery.bucket_mode '{recovery_bucket_mode}'. "
            f"Expected one of {sorted(allowed_bucket_modes)}"
        )

    recovery_percentage_buckets = tuple(
        float(x) for x in recovery_cfg.get("percentage_buckets", [0.25, 0.50, 0.75])
    )
    if not recovery_percentage_buckets:
        raise ValueError("recovery.percentage_buckets must not be empty")
    if any(x <= 0 or x >= 1 for x in recovery_percentage_buckets):
        raise ValueError("recovery.percentage_buckets values must be in (0, 1)")
    if list(recovery_percentage_buckets) != sorted(recovery_percentage_buckets):
        raise ValueError("recovery.percentage_buckets must be sorted ascending")

    recovery_fixed_bins_mib = tuple(
        int(x)
        for x in recovery_cfg.get(
            "fixed_bins_mib",
            [5120, 8192, 12288, 16384, 20480, 24576, 30720, 35840],
        )
    )
    if not recovery_fixed_bins_mib:
        raise ValueError("recovery.fixed_bins_mib must not be empty")
    if any(x <= 0 for x in recovery_fixed_bins_mib):
        raise ValueError("recovery.fixed_bins_mib values must be positive")
    if list(recovery_fixed_bins_mib) != sorted(recovery_fixed_bins_mib):
        raise ValueError("recovery.fixed_bins_mib must be sorted ascending")

    recovery_max_step_mib = int(recovery_cfg.get("max_step_mib", 8192))
    if recovery_max_step_mib <= 0:
        raise ValueError("recovery.max_step_mib must be positive")

    risk_cfg = cfg.get("risk", {})

    return SchedulerSettings(
        policy=policy,
        estimator=estimator,
        recovery_dir=recovery_cfg.get("dir", "/home/ehyo/rad-scheduler"),
        recovery_bucket_mode=recovery_bucket_mode,
        recovery_percentage_buckets=recovery_percentage_buckets,
        recovery_fixed_bins_mib=recovery_fixed_bins_mib,
        recovery_max_step_mib=recovery_max_step_mib,
        patience=cfg.get("monitor", {}).get("patience", "10"),
        monitoring_window_size=cfg.get("monitor", {}).get("window", "30"),

        risk_smact_threshold=float(risk_cfg.get("smact_threshold", 0.65)),
        risk_smocc_threshold=float(risk_cfg.get("smocc_threshold", 0.35)),
        risk_drama_threshold=float(risk_cfg.get("drama_threshold", 0.50)),
        runtime_pressure_backend=str(risk_cfg.get("runtime_pressure_backend", "dcgm")),
        gpu_utilization_threshold=float(risk_cfg.get("gpu_utilization_threshold", 70.0)),
    )