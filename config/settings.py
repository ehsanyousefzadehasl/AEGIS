from __future__ import annotations

from dataclasses import dataclass

from config.load_yaml import load_yaml
from placement.profiles import get_policy_profile, policy_requires_estimator


@dataclass(frozen=True)
class SchedulerSettings:
    policy: str
    estimator: str
    recovery_dir: str
    patience: str
    monitoring_window_size: str


def load_scheduler_settings() -> SchedulerSettings:
    cfg = load_yaml()

    policy = cfg.get("mapper", {}).get("policy", "exclusive")
    get_policy_profile(policy)

    estimator = cfg.get("mapper", {}).get("estimator", "None")
    if policy_requires_estimator(policy) and estimator == "None":
        raise ValueError(f"Policy '{policy}' requires a configured estimator")

    return SchedulerSettings(
        policy=policy,
        estimator=estimator,
        recovery_dir=cfg.get("recovery", {}).get("dir", "/home/ehyo/rad-scheduler"),
        patience=cfg.get("monitor", {}).get("patience", "10"),
        monitoring_window_size=cfg.get("monitor", {}).get("window", "30"),
    )