from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from telemetry import monitor


@dataclass(frozen=True)
class AllocationRecord:
    task_id: str
    task_path: str
    launcher_pid: int
    assigned_gpu_ids: tuple[str, ...]
    profiled_gpu_util: float = 0.0
    profiled_memory_mib: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


_allocations_by_task: dict[str, AllocationRecord] = {}


def register_allocation(
    *,
    task_id: str,
    task_path: str,
    launcher_pid: int,
    assigned_gpu_ids,
    profiled_gpu_util: float = 0.0,
    profiled_memory_mib: int = 0,
    metadata: dict[str, Any] | None = None,
) -> None:
    _allocations_by_task[str(task_id)] = AllocationRecord(
        task_id=str(task_id),
        task_path=str(task_path),
        launcher_pid=int(launcher_pid),
        assigned_gpu_ids=tuple(str(g) for g in assigned_gpu_ids),
        profiled_gpu_util=float(profiled_gpu_util or 0.0),
        profiled_memory_mib=int(profiled_memory_mib or 0),
        metadata={} if metadata is None else dict(metadata),
    )


def remove_allocation(task_id: str) -> None:
    _allocations_by_task.pop(str(task_id), None)


def reconcile_allocations() -> None:
    stale_task_ids = [
        task_id
        for task_id, record in _allocations_by_task.items()
        if not monitor.pid_on_system(str(record.launcher_pid))
    ]

    for task_id in stale_task_ids:
        remove_allocation(task_id)


def allocations_for_gpu(gpu_id: str) -> list[AllocationRecord]:
    gid = str(gpu_id)
    return [
        record
        for record in _allocations_by_task.values()
        if gid in record.assigned_gpu_ids
    ]


def reserved_profiled_gpu_util_by_gpu() -> dict[str, float]:
    out: dict[str, float] = {}
    for record in _allocations_by_task.values():
        for gpu_id in record.assigned_gpu_ids:
            out[gpu_id] = out.get(gpu_id, 0.0) + float(record.profiled_gpu_util)
    return out


def snapshot() -> dict[str, dict[str, Any]]:
    return {
        task_id: {
            "task_path": record.task_path,
            "launcher_pid": record.launcher_pid,
            "assigned_gpu_ids": list(record.assigned_gpu_ids),
            "profiled_gpu_util": record.profiled_gpu_util,
            "profiled_memory_mib": record.profiled_memory_mib,
            "metadata": record.metadata,
        }
        for task_id, record in _allocations_by_task.items()
    }