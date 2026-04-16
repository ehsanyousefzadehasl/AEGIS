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