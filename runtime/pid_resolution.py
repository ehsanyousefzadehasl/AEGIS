from __future__ import annotations

import logging
import subprocess
import time
from typing import Set

from telemetry import monitor
from telemetry import gpu_state


def _proc_children_once(pid: int) -> list[int]:
    proc_children_helper = "/usr/bin/proc_children_helper"
    try:
        out = subprocess.check_output([proc_children_helper, str(pid)], text=True)
        return [int(x) for x in out.split() if x.isdigit()]
    except Exception:
        print("could not read children")
        return []


def _session_id(pid: int) -> str | None:
    try:
        out = subprocess.check_output(
            ["ps", "-o", "sid=", "-p", str(pid)],
            text=True,
        ).strip()
        return out if out else None
    except subprocess.CalledProcessError:
        return None


def _pids_in_same_session(launcher_pid: int) -> Set[int]:
    sid = _session_id(launcher_pid)
    if not sid:
        return set()

    try:
        out = subprocess.check_output(["ps", "-e", "-o", "pid=,sid="], text=True)
    except subprocess.CalledProcessError:
        return set()

    same_session = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == sid and parts[0].isdigit():
            same_session.add(int(parts[0]))
    return same_session


def descendants(pid: int) -> set[int]:
    seen: Set[int] = set()
    frontier = [pid]

    while frontier:
        p = frontier.pop()
        if p in seen:
            continue
        seen.add(p)
        kids = _proc_children_once(p)
        frontier.extend(kids)

    return seen | _pids_in_same_session(pid)


def resolve_gpu_pid(launcher_pid: int, timeout: int = 30, poll: float = 0.5) -> int:
    deadline = time.time() + timeout
    sid_l = _session_id(launcher_pid)
    last_seen = None

    while time.time() < deadline:
        if not monitor.pid_on_system(str(launcher_pid)):
            return last_seen or launcher_pid

        cand = descendants(launcher_pid)
        if sid_l:
            cand |= _pids_in_same_session(launcher_pid)

        found = None
        for row in monitor.pmon_rows():
            cmd = row.get("cmd", "")

            if cmd in {"nvidia-cuda-mps", "nvidia-cuda-mps-control"}:
                continue

            pid_s = row.get("pid", "")
            if pid_s.isdigit():
                gpu_pid = int(pid_s)
                if gpu_pid in cand:
                    found = gpu_pid
                    break

        if found is not None:
            if last_seen == found:
                return found
            last_seen = found

        time.sleep(poll)

    return last_seen or launcher_pid


def resolve_and_update_gpu_pid(launcher_pid: int, gpu_uuids: list[str]) -> None:
    try:
        real_pid = resolve_gpu_pid(launcher_pid, timeout=1000, poll=0.5)
        print("resolved the PID, and will update the table")

        for gpu_uuid in gpu_uuids:
            gpu_state.gpus_state.at[gpu_uuid, "CPU_task_PID"] = int(real_pid)
            print("updated the validity table!", gpu_state.gpus_state)

            if monitor.is_in_pmon(str(real_pid)):
                print("oh! wait, I saw it here right after resolving!")
                gpu_state.mark_seen_now(gpu_uuid)

    except Exception as e:
        logging.exception("async resolve failed for %s: %s", launcher_pid, e)