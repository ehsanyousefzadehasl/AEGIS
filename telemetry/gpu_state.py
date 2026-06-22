from __future__ import annotations

import subprocess
import time
import pandas as pd

from telemetry import monitor


POST_TTFK_WINDOW_SEC = 30.0

# Pascal GTX 1080 Ti GPUs on the legacy Zeus server. Under MPS, CUDA client
# processes may be hidden behind nvidia-cuda-mps-server in nvidia-smi/pmon.
# For these GPUs, first GPU activity is detected using a stable device-memory
# increase rather than client PID visibility.
LEGACY_GTX_GPU_UUIDS = {
    "GPU-1c6317b1-1524-facb-b296-af9236965e45",
    "GPU-323af678-54fb-3c08-ae09-02f5f27c6ed6",
    "GPU-f9167b1e-3128-ca9e-6851-91863ac9987e",
    "GPU-341c9e18-417a-7e7c-3eec-c0a83d472ac0",
}

MEMORY_ACTIVITY_DELTA_MIB = 64.0


gpus_state = pd.DataFrame(
    {
        "CPU_task_PID": pd.Series(dtype="str"),
        "task_id": pd.Series(dtype="string"),
        "event_path": pd.Series(dtype="string"),
        "validity": pd.Series(dtype="boolean"),
        "gpu_seen_at": pd.Series(dtype="float64"),
        "window_seconds": pd.Series(dtype="float64"),
        "activity_backend": pd.Series(dtype="string"),
        "dispatch_memory_used_mib": pd.Series(dtype="float64"),
        "activity_memory_delta_mib": pd.Series(dtype="float64"),
    },
)


def memory_used_mib_by_uuid() -> dict[str, float]:
    """Return current memory.used per GPU UUID using nvidia-smi.

    This is intentionally device-level rather than process-level, because on
    pre-Volta/Pascal MPS the CUDA client process may be hidden behind the MPS
    server process.
    """
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=uuid,memory.used",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return {}

    usage: dict[str, float] = {}
    for line in out.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        uuid, memory_mib = parts
        try:
            usage[uuid] = float(memory_mib)
        except ValueError:
            continue
    return usage


def memory_used_mib(gpu_uuid: str) -> float | None:
    return memory_used_mib_by_uuid().get(str(gpu_uuid))


def activity_backend_for_gpu(gpu_uuid: str) -> str:
    return "memory_delta" if str(gpu_uuid) in LEGACY_GTX_GPU_UUIDS else "pid"


def memory_activity_detected(gpu_uuid: str, current_memory: float | None = None) -> bool:
    if current_memory is None:
        current_memory = memory_used_mib(gpu_uuid)
    if current_memory is None:
        return False

    baseline = gpus_state.at[gpu_uuid, "dispatch_memory_used_mib"]
    if pd.isna(baseline):
        baseline = 0.0

    delta = gpus_state.at[gpu_uuid, "activity_memory_delta_mib"]
    if pd.isna(delta):
        delta = float(MEMORY_ACTIVITY_DELTA_MIB)

    return float(current_memory) >= float(baseline) + float(delta)


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
    df["activity_backend"] = pd.Series(
        [activity_backend_for_gpu(u) for u in idx],
        index=idx,
        dtype="string",
    )
    df["dispatch_memory_used_mib"] = pd.Series(pd.NA, index=idx, dtype="Float64")
    df["activity_memory_delta_mib"] = pd.Series(
        float(MEMORY_ACTIVITY_DELTA_MIB),
        index=idx,
        dtype="Float64",
    )

    gpus_state = df
    return gpus_state


def clear_tracking(gpu_uuid: str) -> None:
    gpus_state.at[gpu_uuid, "CPU_task_PID"] = pd.NA
    gpus_state.at[gpu_uuid, "task_id"] = pd.NA
    gpus_state.at[gpu_uuid, "event_path"] = pd.NA
    gpus_state.at[gpu_uuid, "gpu_seen_at"] = pd.NA
    gpus_state.at[gpu_uuid, "window_seconds"] = float(POST_TTFK_WINDOW_SEC)
    gpus_state.at[gpu_uuid, "dispatch_memory_used_mib"] = pd.NA


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

    dispatch_memory = memory_used_mib(gpu_uuid)
    if dispatch_memory is None:
        dispatch_memory = 0.0

    gpus_state.at[gpu_uuid, "CPU_task_PID"] = int(pid)
    gpus_state.at[gpu_uuid, "task_id"] = pd.NA if task_id is None else str(task_id)
    gpus_state.at[gpu_uuid, "event_path"] = pd.NA if event_path is None else str(event_path)
    gpus_state.at[gpu_uuid, "validity"] = False
    gpus_state.at[gpu_uuid, "gpu_seen_at"] = pd.NA
    gpus_state.at[gpu_uuid, "window_seconds"] = float(window_seconds)
    gpus_state.at[gpu_uuid, "activity_backend"] = activity_backend_for_gpu(gpu_uuid)
    gpus_state.at[gpu_uuid, "dispatch_memory_used_mib"] = float(dispatch_memory)
    gpus_state.at[gpu_uuid, "activity_memory_delta_mib"] = float(MEMORY_ACTIVITY_DELTA_MIB)


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

    memory_by_uuid = memory_used_mib_by_uuid()

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

        activity_backend = gpus_state.at[gpu_uuid, "activity_backend"]

        if (
            pd.isna(seen_at)
            and activity_backend == "memory_delta"
            and memory_activity_detected(
                gpu_uuid,
                current_memory=memory_by_uuid.get(str(gpu_uuid)),
            )
        ):
            gpus_state.at[gpu_uuid, "gpu_seen_at"] = now
            seen_at = now

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