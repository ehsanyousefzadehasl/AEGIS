from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResourceProfile:
    peak_memory_mib: Optional[int] = None
    avg_smact: Optional[float] = None
    avg_smocc: Optional[float] = None
    avg_drama: Optional[float] = None
    class_label: Optional[str] = None
    profiling_duration_s: Optional[int] = None
    source: Optional[str] = None
    extra_metrics: Optional[dict[str, float]] = None


def get_resource_profile_metric(
    resource_profile: ResourceProfile | None,
    metric_name: str,
):
    if resource_profile is None:
        return None

    if hasattr(resource_profile, metric_name):
        return getattr(resource_profile, metric_name)

    extra_metrics = resource_profile.extra_metrics or {}
    return extra_metrics.get(metric_name)


def load_resource_profile(data: dict | None) -> ResourceProfile | None:
    if not data:
        return None

    return ResourceProfile(
        peak_memory_mib=None if data.get("peak_memory_mib") is None else int(float(data.get("peak_memory_mib"))),
        avg_smact=None if data.get("avg_smact") is None else float(data.get("avg_smact")),
        avg_smocc=None if data.get("avg_smocc") is None else float(data.get("avg_smocc")),
        avg_drama=None if data.get("avg_drama") is None else float(data.get("avg_drama")),
        class_label=data.get("class_label"),
        profiling_duration_s=None if data.get("profiling_duration_s") is None else int(float(data.get("profiling_duration_s"))),
        source=data.get("source"),
        extra_metrics=data.get("extra_metrics"),
    )