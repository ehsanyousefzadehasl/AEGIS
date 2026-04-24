from __future__ import annotations

import time
import pandas as pd

from telemetry import monitor


POST_TTFK_WINDOW_SEC = 30.0


gpus_state = pd.DataFrame(
    {
        "CPU_task_PID": pd.Series(dtype="str"),
        "task_id": pd.Series(dtype="string"),
        "event_path": pd.Series(dtype="string"),
        "validity": pd.Series(dtype="boolean"),
        "gpu_seen_at": pd.Series(dtype="float64"),
        "window_seconds": pd.Series(dtype="float64"),
    },
)


def init_gpu_state(uuid_to_id: dict[str, str]) -> pd.DataFrame:
    global gpus_state

    idx = pd.Index(list(uuid_to_id.keys()), name="GPU_uuid", dtype="string")
    df = pd.DataFrame(index=idx)
    df["GPU_id"] = pd.Series([str(uuid_to_id[u]) for u in idx], index=idx, dtype="string")
    df["CPU_task_PID"] = pd.Series(pd.NA, index=idx, dtype="Int64")
    df["task_id"] = pd.Series(pd.NA, index=idx, dtype="string")
    df["event_path"] = pd.Series(pd.NA, index=idx, dtype="string")
    df["validity"] = pd.Series(True, index=idx, dtype="boolean")
    df["gpu_seen_at"] = pd.Series(pd.NA, index=idx, dtype="Float64")
    df["window_seconds"] = pd.Series(float(POST_TTFK_WINDOW_SEC), index=idx, dtype="Float64")

    gpus_state = df
    return gpus_state


def clear_tracking(gpu_uuid: str) -> None:
    gpus_state.at[gpu_uuid, "CPU_task_PID"] = pd.NA
    gpus_state.at[gpu_uuid, "task_id"] = pd.NA
    gpus_state.at[gpu_uuid, "event_path"] = pd.NA
    gpus_state.at[gpu_uuid, "gpu_seen_at"] = pd.NA
    gpus_state.at[gpu_uuid, "window_seconds"] = float(POST_TTFK_WINDOW_SEC)


def launch_task(
    gpu_uuid: str,
    pid: int,
    *,
    task_id: str | None = None,
    event_path: str | None = None,
    window_seconds: float = POST_TTFK_WINDOW_SEC,
) -> None:
    if gpu_uuid not in gpus_state.index:
        raise KeyError(f"Unknown GPU UUID: {gpu_uuid}")
    gpus_state.at[gpu_uuid, "CPU_task_PID"] = int(pid)
    gpus_state.at[gpu_uuid, "task_id"] = pd.NA if task_id is None else str(task_id)
    gpus_state.at[gpu_uuid, "event_path"] = pd.NA if event_path is None else str(event_path)
    gpus_state.at[gpu_uuid, "validity"] = False
    gpus_state.at[gpu_uuid, "gpu_seen_at"] = pd.NA
    gpus_state.at[gpu_uuid, "window_seconds"] = float(window_seconds)


def mark_seen_now(gpu_uuid: str, now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    if pd.isna(gpus_state.at[gpu_uuid, "gpu_seen_at"]):
        gpus_state.at[gpu_uuid, "gpu_seen_at"] = float(now)


def window_ready(gpu_uuid: str, now: float | None = None) -> bool:
    now = time.monotonic() if now is None else now
    seen_at = gpus_state.at[gpu_uuid, "gpu_seen_at"]
    if pd.isna(seen_at):
        return False
    window_seconds = float(gpus_state.at[gpu_uuid, "window_seconds"])
    return (now - float(seen_at)) >= window_seconds


def update() -> None:
    now = time.monotonic()

    for gpu_uuid in gpus_state.index:
        pid_val = gpus_state.loc[gpu_uuid, "CPU_task_PID"]

        if pd.isna(pid_val):
            gpus_state.at[gpu_uuid, "validity"] = True
            clear_tracking(gpu_uuid)
            continue

        pid = str(pid_val)

        if not monitor.pid_on_system(pid):
            gpus_state.at[gpu_uuid, "validity"] = True
            clear_tracking(gpu_uuid)
            continue

        seen_at = gpus_state.at[gpu_uuid, "gpu_seen_at"]

        if pd.isna(seen_at) and monitor.is_in_pmon(pid):
            gpus_state.at[gpu_uuid, "gpu_seen_at"] = now
            seen_at = now

        if pd.isna(seen_at):
            gpus_state.at[gpu_uuid, "validity"] = False
            continue

        if window_ready(gpu_uuid, now=now):
            gpus_state.at[gpu_uuid, "validity"] = True
        else:
            gpus_state.at[gpu_uuid, "validity"] = False


def all_available_GPUs():
    return gpus_state.index[gpus_state["validity"].fillna(False)].tolist()