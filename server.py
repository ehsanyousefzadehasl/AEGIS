import socket
import time
import datetime
from threading import Thread, Lock
import subprocess
import os
import logging

from typing import Set

import monitor
import rad_parser
from task_queue import Task, Tasks
from itertools import cycle, islice
from load_yaml import load_yaml
from job_spec import load_job_spec
from dispatch_utils import format_gpu_identifiers, build_recovery_header
from candidate_selection import build_candidate_gpus


# for getting the launched task PID
def launch_and_get_pid(cmd: str) -> int | None:
    p = subprocess.Popen(
        ["bash", "-lc", cmd],
        stdout=subprocess.PIPE,      # receives the echoed PID
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,   # <<< unique SID per launch
    )
    pid_line = p.stdout.readline().strip() if p.stdout else ""
    if p.stdout:
        p.stdout.close()            # don't wait; job keeps running
    try:
        return int(pid_line)
    except ValueError:
        return None
# ending the logic for getting PID


# --- add helpers (just above descendants) ---
def _proc_children_once(pid: int) -> list[int]:
    PROC_CHILDREN_HELPER = "/usr/bin/proc_children_helper"
    """Direct children via /proc (more reliable than pgrep)."""
    try:
        out = subprocess.check_output([PROC_CHILDREN_HELPER, str(pid)], text=True)
        return [int(x) for x in out.split() if x.isdigit()]
    except Exception:
        print("could not read children")
        return []


def _session_id(pid: int) -> str | None:
    """Return POSIX session id (SID) of a pid, or None."""
    try:
        out = subprocess.check_output(["ps", "-o", "sid=", "-p", str(pid)], text=True).strip()
        return out if out else None
    except subprocess.CalledProcessError:
        return None


def _pids_in_same_session(launcher_pid: int) -> Set[int]:
    """All PIDs that share the same SID as launcher (helps with MPS, fork/exec)."""
    sid = _session_id(launcher_pid)
    if not sid:
        return set()
    try:
        # List all pids with their sid, filter by sid
        out = subprocess.check_output(["ps", "-e", "-o", "pid=,sid="], text=True)
    except subprocess.CalledProcessError:
        return set()
    s = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == sid and parts[0].isdigit():
            s.add(int(parts[0]))
    return s


# --- replace descendants() with a proc-based, recursive walk + SID union ---
def descendants(pid: int) -> set[int]:
    """All descendants of pid (via /proc), plus same-session PIDs for MPS cases."""
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


# --- pid resolve logic: also accept same-session matches ---
def resolve_gpu_pid(launcher_pid: int, timeout=30, poll=0.5) -> int:
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


def _async_resolve_and_update(launcher_pid: int, gpu_uuids: list[str]) -> None:
    try:
        real_pid = resolve_gpu_pid(launcher_pid, timeout=1000, poll=0.5)
        print("resolved the PID, and will update the table")
        for u in gpu_uuids:
            gpus_state.at[u, "CPU_task_PID"] = int(real_pid)
            print("updated the validity table!", gpus_state)

            if monitor.is_in_pmon(str(real_pid)):
                print("oh! wait, I saw it here right after resolving!")
                mark_seen_now(u)

    except Exception as e:
        logging.exception("async resolve failed for %s: %s", launcher_pid, e)


def load_job_spec_safe(task_path: str, estimator_name: str):
    try:
        return load_job_spec(task_path, estimator_name)
    except Exception as e:
        logging.exception("Failed to load job spec from %s: %s", task_path, e)
        print(f"Failed to load job spec from {task_path}: {e}")
        return None


# logger for keeping track of submission, dispatch, and termination time
logging.basicConfig(
    filename='std.log',
    filemode='w',
    format='%(asctime)s %(message)s',
    datefmt='%d-%b-%y %H:%M:%S'
)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# loading mapping policy
cfg = load_yaml()

policy = cfg.get("mapper", {}).get("policy", "exclusive")
print("Configured mapping policy:", policy)

estimator = cfg.get("mapper", {}).get("estimator", "None")
print("Configured mapping estimator:", estimator)

recovery_dir = cfg.get("recovery", {}).get("dir", "/home/ehyo/rad-scheduler")
print("Configured recovery directory:", recovery_dir)

# locks for avoiding race condition
lock = Lock()
recover_lock = Lock()

# queues for submitted jobs
main_queue = Tasks()
recovery_queue = Tasks()

# ============= for having Round-Robin selection logic of GPUs ============
gpu_UUIDs = monitor.gpu_uuids()

GPU_IDs = []
for gpu in gpu_UUIDs:
    GPU_IDs.append(gpu)

round_robin_generator = cycle(GPU_IDs)


def select_ids(n):
    """
    Selects n IDs in a round-robin manner.
    Args:
        n (int): Number of IDs to select.
    Returns:
        list: List of selected IDs.
    """
    return list(islice(round_robin_generator, n))


# ============= End of Round Robin selection logic of GPUs =================

# keeps track of the handled crashes
handled_crashes = []

patience = cfg.get("monitor", {}).get("patience", "10")
monitoring_window_size = cfg.get("monitor", {}).get("window", "30")

import pandas as pd
gpus_state = pd.DataFrame(
    {
        "CPU_task_PID": pd.Series(dtype="str"),
        "validity":     pd.Series(dtype="boolean"),
        "gpu_seen_at":  pd.Series(dtype="float64"),
    },
)


def init_gpu_state(uuid_to_id: dict[str, str]) -> pd.DataFrame:
    idx = pd.Index(list(uuid_to_id.keys()), name="GPU_uuid", dtype="string")
    df = pd.DataFrame(index=idx)
    df["GPU_id"] = pd.Series([str(uuid_to_id[u]) for u in idx], index=idx, dtype="string")
    df["CPU_task_PID"] = pd.Series(pd.NA, index=idx, dtype="Int64")
    df["validity"] = pd.Series(True, index=idx, dtype="boolean")
    df["gpu_seen_at"] = pd.Series(pd.NA, index=idx, dtype="Float64")
    return df


#  ====== initialized GPUs ======
gpus_state = init_gpu_state(gpu_UUIDs)


def launch_task(gpu_uuid: str, pid: int) -> None:
    if gpu_uuid not in gpus_state.index:
        raise KeyError(f"Unknown GPU UUID: {gpu_uuid}")
    gpus_state.at[gpu_uuid, "CPU_task_PID"] = int(pid)
    gpus_state.at[gpu_uuid, "validity"] = False
    gpus_state.at[gpu_uuid, "gpu_seen_at"] = pd.NA


def mark_seen_now(gpu_uuid: str, now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    if pd.isna(gpus_state.at[gpu_uuid, "gpu_seen_at"]):
        gpus_state.at[gpu_uuid, "gpu_seen_at"] = float(now)


def update():
    now = time.monotonic()
    for gpu_uuid in gpus_state.index:
        pid_val = gpus_state.loc[gpu_uuid, "CPU_task_PID"]

        if pd.isna(pid_val):
            gpus_state.loc[gpu_uuid, "validity"] = True
            gpus_state.at[gpu_uuid, "CPU_task_PID"] = pd.NA
            gpus_state.at[gpu_uuid, "gpu_seen_at"] = pd.NA
            continue

        pid = str(pid_val)

        if not monitor.pid_on_system(pid):
            gpus_state.loc[gpu_uuid, "validity"] = True
            gpus_state.loc[gpu_uuid, "gpu_seen_at"] = pd.NA
            gpus_state.loc[gpu_uuid, "CPU_task_PID"] = pd.NA
            continue

        seen_at = gpus_state.at[gpu_uuid, "gpu_seen_at"]

        if pd.isna(seen_at) and monitor.is_in_pmon(pid):
            gpus_state.at[gpu_uuid, "gpu_seen_at"] = now
            seen_at = now

        if not pd.isna(seen_at) and (now - float(seen_at) > 30):
            gpus_state.at[gpu_uuid, "validity"] = True
            gpus_state.at[gpu_uuid, "CPU_task_PID"] = pd.NA
            gpus_state.at[gpu_uuid, "gpu_seen_at"] = pd.NA


def all_available_GPUs():
    return gpus_state.index[gpus_state["validity"].fillna(False)].tolist()


print("Initialized the gpus_state tracker: ", gpus_state)


# command generator function
def command_generator(dir, gpus_identifiers, command_to_execute, now, a):
    command = f"""cd {dir} ; \
                export CUDA_VISIBLE_DEVICES={gpus_identifiers} ; \
                exec 3>&1 ; \
                {{ time ( \
                    {{ \
                        conda run --no-capture-output -p /opt/miniconda3/envs/tf {command_to_execute} & pid=$! ; \
                        echo $pid >&3 ; \
                        wait $pid ; \
                        if [ $? -eq 0 ]; then \
                            echo 'Successful' >> {dir}/err-{now}-{a.task_id}.log ; \
                        else \
                            echo 'unsuccessful' >> {dir}/err-{now}-{a.task_id}.log ; \
                        fi ; \
                    }} 1> {dir}/out-{now}-{a.task_id}.log 2>> {dir}/err-{now}-{a.task_id}.log \
                ) ; }} 2> {dir}/time-{now}-{a.task_id}.et ; \
                exec 3>&-"""
    return command


# this function is responsible for implementing recovery method
def recovery(dirs=[globals()["recovery_dir"]]):
    """
    This is the function that checks error files and adds OOM found to the high-priority queue
    """
    list_of_files = []

    for base in dirs:
        for file in os.listdir(base):
            if file.startswith("err") and file.endswith(".log"):
                file = os.path.join(base, file)
                list_of_files.append(file)

    crashes = 0
    all_executions = 0
    for iterator in list_of_files:
        if iterator in handled_crashes:
            continue
        else:
            all_executions += 1
            file = open(f'{iterator}', 'r')
            Lines = file.readlines()

            for line in Lines:
                if "unsuccessful" in line or "OOM" in line or "Non-OK-status" in line or "RESOURCE_EXHAUSTED" in line:
                    crashes += 1

                    handled_crashes.append(iterator)
                    opener = open(f'{iterator}', 'r')
                    Lines = opener.readlines()

                    recovery_data = Lines[0].split('+')

                    tmp_dir = recovery_data[0]
                    tmp_file = recovery_data[3]
                    tmp_user = recovery_data[4]
                    tmp_task_id = recovery_data[5][:-1]

                    recovered_task = Task(tmp_user, tmp_dir, tmp_file)
                    recovered_task.set_id(tmp_task_id)

                    recovered_task.set_if_recovered()
                    with recover_lock:
                        recovery_queue.enqueue(recovered_task)
                    print("OOM FOUND: recovery queue is filled with the task that has problem: ", recovered_task, recovered_task._to_string())
                    print("length of the queue:", recovery_queue.length())
                    logging.info(f"Recovered: {recovered_task}")
                    break


def command_executor(command):
    subprocess.run(command, shell=True, check=True, executable='/bin/bash')
    pass


def server():
    host = socket.gethostname()
    port = 5001

    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((host, port))

    while True:
        server_socket.listen(10)
        while True:
            conn, address = server_socket.accept()
            print("Connection from: " + str(address))
            data = conn.recv(1024).decode()

            if not data:
                break
            message = "Got your task and queued it."

            conn.send(message.encode())

            user, dir, task = data.split('+')
            task = "/" + task[1:]

            print(user, dir, task)

            a = Task(user, dir, task)

            with lock:
                main_queue.enqueue(a)
                logging.info(f"queued {a.task_id} - {a.task}")

        conn.close()


def scheduler(policy=policy):
    estimator = globals()["estimator"]

    while True:
        time.sleep(1)

        recovery()
        update()

        print("updated the table: ", gpus_state)
        print(command_executor("nvidia-smi pmon -c 1"))

        if main_queue.length() != 0 or recovery_queue.length() != 0:
            idle_gpus_to_send_job = list()
            gpus_activeness = monitor.gpus_activeness()
            for gpu in gpus_activeness:
                if gpus_activeness[gpu] == 0:
                    idle_gpus_to_send_job.append(gpu)

            print("idle gpus: ", idle_gpus_to_send_job)
            print("available GPUs:", all_available_GPUs())

            idle_and_available = [g for g in idle_gpus_to_send_job if g in set(all_available_GPUs())]

            a = None
            main_queue_flag = None
            user, dir, task = None, None, None

            if recovery_queue.length() != 0:
                with recover_lock:
                    a = recovery_queue.check()
                user, dir, task = a.user, a.dir, a.task
                main_queue_flag = False
            else:
                with lock:
                    a = main_queue.check()
                user, dir, task = a.user, a.dir, a.task
                main_queue_flag = True

            spec = load_job_spec_safe(task, estimator)
            if spec is None:
                continue

            env_name = spec.env_name
            environment = spec.env_path
            command_to_execute = spec.command_to_execute
            number_of_GPUs_requested = spec.num_gpus_requested

            print("conda environment to activate: ", env_name, environment)

            now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

            if len(idle_and_available) >= number_of_GPUs_requested:
                assigned_gpus = idle_and_available[:number_of_GPUs_requested]

                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                if main_queue_flag is True:
                    main_queue.dequeue()
                else:
                    recovery_queue.dequeue()

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                logging.info(f"dispatched {a.task_id} - {a.task} - {gpus_identifiers}")

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus)),
                        daemon=True
                    ).start()

                print(gpus_state)
                continue

            elif policy == "oracle-FF" and main_queue.length() != 0 and recovery_queue.length() == 0:
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                gpu_memory_requirement = spec.gpu_memory_requirement_mib
                number_of_GPUs_requested = spec.num_gpus_requested

                if gpu_memory_requirement is None:
                    print(f"Could not parse GPU memory requirement for task {task}")
                    continue

                print("environment: ", env_name, environment)
                print("command to execute found: ", command_to_execute)
                print("memory requirement: ", gpu_memory_requirement)

                gpus_with_metrics = monitor.analyze_Gmetrics()

                candidate_gpus = build_candidate_gpus(
                    gpus_with_metrics=gpus_with_metrics,
                    min_free_mib=gpu_memory_requirement + 2048,
                    available_gpu_ids=all_available_GPUs(),
                    use_utilization_gate=True,
                )

                print("candidate & available GPUs:\n", candidate_gpus)

                if candidate_gpus.empty:
                    print("no candidate gpus at all!")
                    continue

                print("number of gpus requested: ", number_of_GPUs_requested)

                if len(candidate_gpus) < number_of_GPUs_requested:
                    print("Not enough GPUs to submit the task to!")
                    continue
                else:
                    print("The gpus that we can send the task to: \n", candidate_gpus)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                assigned_gpus = candidate_gpus.head(number_of_GPUs_requested)

                print("assigned GPUs: ", assigned_gpus)
                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus.index)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus.index:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus.index)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "Oracle-FF Collocated task on GPUs")
                continue

            elif (policy == "oracle-BF") and (main_queue.length() != 0) and (recovery_queue.length() == 0):
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                gpu_memory_requirement = spec.gpu_memory_requirement_mib
                number_of_GPUs_requested = spec.num_gpus_requested

                if gpu_memory_requirement is None:
                    print(f"Could not parse GPU memory requirement for task {task}")
                    continue

                print("environment: ", env_name, environment)
                print("command to execute found: ", command_to_execute)
                print("memory requirement: ", gpu_memory_requirement)

                gpus_with_metrics = monitor.analyze_Gmetrics()

                temp_ = gpus_with_metrics.loc[
                    gpus_with_metrics['GPU_mem_available'] >= (gpu_memory_requirement + 2048)
                ]

                candidate_gpus = temp_.copy()

                avail = set(all_available_GPUs())
                candidate_gpus = candidate_gpus.loc[candidate_gpus.index.isin(avail)].copy()

                print("candidate & available GPUs:\n", candidate_gpus)

                if candidate_gpus.empty:
                    print("no candidate gpus at all!")
                    continue

                print("number of gpus requested: ", number_of_GPUs_requested)

                if len(candidate_gpus) < number_of_GPUs_requested:
                    print("Not enough GPUs to submit the task to!")
                    continue
                else:
                    print("The gpus that we can send the task to: \n", candidate_gpus)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                sorted_ = candidate_gpus.sort_values(by="GPU_mem_available", ascending=True, kind="mergesort")
                assigned_gpus = sorted_.head(number_of_GPUs_requested)

                print("assigned GPUs: ", assigned_gpus)
                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus.index)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus.index:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus.index)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "Oracle-BF Collocated task on GPUs")
                continue

            elif policy == "oracle-MAGM" and (main_queue.length() != 0 and recovery_queue.length() == 0):
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                gpu_memory_requirement = spec.gpu_memory_requirement_mib
                number_of_GPUs_requested = spec.num_gpus_requested

                if gpu_memory_requirement is None:
                    print(f"Could not parse GPU memory requirement for task {task}")
                    continue

                print("this is what we want to parse and work on and collocate: ", task)
                print("conda environment to activate: ", env_name, environment)
                print("memory requirement: ", gpu_memory_requirement)

                gpus_with_metrics = monitor.analyze_Gmetrics()
                print(gpus_with_metrics)

                temp_ = gpus_with_metrics.loc[
                    gpus_with_metrics['GPU_mem_available'] >= (gpu_memory_requirement + 2048)
                ]

                candidate_gpus = temp_.copy()

                avail = set(all_available_GPUs())
                candidate_gpus = candidate_gpus.loc[candidate_gpus.index.isin(avail)].copy()

                print(gpus_state)
                print("candidate and available GPUs:\n", candidate_gpus)

                if candidate_gpus.empty:
                    print("no candidate gpus at all!")
                    continue

                print("number of gpus requested: ", number_of_GPUs_requested)

                if len(candidate_gpus) < number_of_GPUs_requested:
                    print("Not enough GPUs to submit the task to!")
                    continue
                else:
                    print("The gpus that we can send the task to: \n", candidate_gpus)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                sorted_ = candidate_gpus.sort_values(by="GPU_mem_available", ascending=False, kind="mergesort")
                assigned_gpus = sorted_.head(number_of_GPUs_requested)

                print("assigned GPUs: ", assigned_gpus)
                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus.index)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus.index:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus.index)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "Oracle-MAGM Collocated task on GPUs")
                continue

            elif policy == "oracle-LUG" and (main_queue.length() != 0 and recovery_queue.length() == 0):
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                gpu_memory_requirement = spec.gpu_memory_requirement_mib
                number_of_GPUs_requested = spec.num_gpus_requested

                if gpu_memory_requirement is None:
                    print(f"Could not parse GPU memory requirement for task {task}")
                    continue

                print("this is what we want to parse and work on and collocate: ", task)
                print("environment: ", env_name, environment)
                print("memory requirement: ", gpu_memory_requirement)

                gpus_with_metrics = monitor.analyze_Gmetrics()
                print(gpus_with_metrics)

                candidate_gpus = build_candidate_gpus(
                    gpus_with_metrics=gpus_with_metrics,
                    min_free_mib=gpu_memory_requirement + 2048,
                    available_gpu_ids=all_available_GPUs(),
                    use_utilization_gate=True,
                )

                print(gpus_state)
                print("candidate and available GPUs:\n", candidate_gpus)

                if candidate_gpus.empty:
                    print("no candidate gpus at all!")
                    continue

                print("number of gpus requested: ", number_of_GPUs_requested)

                if len(candidate_gpus) < number_of_GPUs_requested:
                    print("Not enough GPUs to submit the task to!")
                    continue
                else:
                    print("The gpus that we can send the task to: \n", candidate_gpus)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                sorted_ = candidate_gpus.sort_values(by="smact", ascending=True, kind="mergesort")
                assigned_gpus = sorted_.head(number_of_GPUs_requested)

                print("assigned GPUs: ", assigned_gpus)
                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus.index)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus.index:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus.index)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "Oracle-LUG Collocated task on GPUs")
                continue

            elif policy == "OR-RR" and (main_queue.length() != 0 and recovery_queue.length() == 0):
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                number_of_GPUs_requested = spec.num_gpus_requested

                print("this is what we want to parse and work on and collocate: ", task)
                print("conda environment to activate: ", env_name, environment)
                print("number of gpus requested: ", number_of_GPUs_requested)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                avail = set(all_available_GPUs())
                assigned_gpus = []

                print(gpus_state)
                print("available GPUs: ", avail)

                N = len(GPU_IDs)
                seen = set()

                while len(assigned_gpus) < number_of_GPUs_requested and len(seen) < N:
                    gid = next(round_robin_generator)
                    if gid in seen:
                        continue
                    seen.add(gid)
                    if gid in avail and gid not in assigned_gpus:
                        assigned_gpus.append(gid)

                if len(assigned_gpus) < number_of_GPUs_requested:
                    print("OR-RR: not enough available GPUs in this RR pass; skipping dispatch.")
                    continue

                print("assigned GPUs: ", assigned_gpus)

                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "Only Recovery - Round Robin Collocated!")
                continue

            elif policy == "OR-MAGM" and (main_queue.length() != 0 and recovery_queue.length() == 0):
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                number_of_GPUs_requested = spec.num_gpus_requested

                print("this is what we want collocate: ", task)
                print("environment: ", env_name, environment)

                gpus_with_metrics = monitor.analyze_Gmetrics()
                print(gpus_with_metrics)

                candidate_gpus = build_candidate_gpus(
                    gpus_with_metrics=gpus_with_metrics,
                    min_free_mib=5120,
                    available_gpu_ids=all_available_GPUs(),
                    use_utilization_gate=True,
                )

                print(gpus_state)
                print("candidate and available GPUs:\n", candidate_gpus)
                print("candidate GPUs:\n", candidate_gpus)

                if candidate_gpus.empty:
                    print("no candidate gpus at all!")
                    continue

                print("number of gpus requested: ", number_of_GPUs_requested)

                if len(candidate_gpus) < number_of_GPUs_requested:
                    print("Not enough GPUs to submit the task to!")
                    continue
                else:
                    print("The gpus that we can send the task to: \n", candidate_gpus)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                sorted_ = candidate_gpus.sort_values(by="GPU_mem_available", ascending=False, kind="mergesort")
                assigned_gpus = sorted_.head(number_of_GPUs_requested)

                print("assigned GPUs: ", assigned_gpus)
                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus.index)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus.index:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus.index)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "OR-MAGM (>= 5GB free) collocated task on GPUs.")
                continue

            elif policy == "OR-LUG" and (main_queue.length() != 0 and recovery_queue.length() == 0):
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                number_of_GPUs_requested = spec.num_gpus_requested

                print("this is what we want to parse and work on and collocate: ", task)
                print("environment: ", env_name, environment)

                gpus_with_metrics = monitor.analyze_Gmetrics()
                print(gpus_with_metrics)

                candidate_gpus = build_candidate_gpus(
                    gpus_with_metrics=gpus_with_metrics,
                    min_free_mib=5120,
                    available_gpu_ids=all_available_GPUs(),
                    use_utilization_gate=True,
                )

                print(gpus_state)
                print("candidate and available GPUs:\n", candidate_gpus)

                if candidate_gpus.empty:
                    print("No GPUs to submit job to!")
                    continue

                print("number of gpus requested: ", number_of_GPUs_requested)

                if len(candidate_gpus) < number_of_GPUs_requested:
                    print("Not enough GPUs to submit the task to!")
                    continue
                else:
                    print("The gpus that we can send the task to: \n", candidate_gpus)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                sorted_ = candidate_gpus.sort_values(by="smact", ascending=True, kind="mergesort")
                assigned_gpus = sorted_.head(number_of_GPUs_requested)

                print("assigned GPUs: ", assigned_gpus)
                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus.index)

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus.index:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus.index)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "OR-LUG collocated task on GPUs.")
                continue

            elif policy == "EST-MAGM" and (main_queue.length() != 0 and recovery_queue.length() == 0):
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                gpu_memory_estimation = spec.gpu_memory_estimate_mib
                number_of_GPUs_requested = spec.num_gpus_requested

                if gpu_memory_estimation is None:
                    print(f"Could not parse GPU memory estimate for task {task} using estimator {estimator}")
                    continue

                print("this is what we want to parse and work on and collocate: ", task)
                print("conda environment to activate: ", env_name, environment)
                print("memory estimation: ", gpu_memory_estimation)

                gpus_with_metrics = monitor.analyze_Gmetrics()
                print(gpus_with_metrics)

                candidate_gpus = build_candidate_gpus(
                    gpus_with_metrics=gpus_with_metrics,
                    min_free_mib=gpu_memory_estimation + 2048,
                    available_gpu_ids=all_available_GPUs(),
                    use_utilization_gate=True,
                )

                print(gpus_state)
                print("candidate and available GPUs:\n", candidate_gpus)

                if candidate_gpus.empty:
                    print("no candidate gpus at all!")
                    continue

                print("number of gpus requested: ", number_of_GPUs_requested)

                if len(candidate_gpus) < number_of_GPUs_requested:
                    print("Not enough GPUs to submit the task to!")
                    continue
                else:
                    print("The gpus that we can send the task to: \n", candidate_gpus)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                sorted_ = candidate_gpus.sort_values(by="GPU_mem_available", ascending=False, kind="mergesort")
                assigned_gpus = sorted_.head(number_of_GPUs_requested)

                print("assigned GPUs: ", assigned_gpus)
                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus.index)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus.index:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus.index)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "Oracle-MAGM Collocated task on GPUs")
                continue

            elif policy == "EST-LUG" and (main_queue.length() != 0 and recovery_queue.length() == 0):
                a = None
                user, dir, task = None, None, None
                main_queue_flag = None

                if recovery_queue.length() != 0:
                    with recover_lock:
                        a = recovery_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = False
                else:
                    with lock:
                        a = main_queue.check()
                    user, dir, task = a.user, a.dir, a.task
                    main_queue_flag = True

                spec = load_job_spec_safe(task, estimator)
                if spec is None:
                    continue

                env_name = spec.env_name
                environment = spec.env_path
                command_to_execute = spec.command_to_execute
                gpu_memory_estimation = spec.gpu_memory_estimate_mib
                number_of_GPUs_requested = spec.num_gpus_requested

                if gpu_memory_estimation is None:
                    print(f"Could not parse GPU memory estimate for task {task} using estimator {estimator}")
                    continue

                print("this is what we want to parse and work on and collocate: ", task)
                print("environment: ", env_name, environment)
                print("memory requirement: ", gpu_memory_estimation)

                gpus_with_metrics = monitor.analyze_Gmetrics()
                print(gpus_with_metrics)

                candidate_gpus = build_candidate_gpus(
                    gpus_with_metrics=gpus_with_metrics,
                    min_free_mib=gpu_memory_estimation + 2048,
                    available_gpu_ids=all_available_GPUs(),
                    use_utilization_gate=True,
                )

                print(gpus_state)
                print("candidate and available GPUs:\n", candidate_gpus)

                if candidate_gpus.empty:
                    print("no candidate gpus at all!")
                    continue

                print("number of gpus requested: ", number_of_GPUs_requested)

                if len(candidate_gpus) < number_of_GPUs_requested:
                    print("Not enough GPUs to submit the task to!")
                    continue
                else:
                    print("The gpus that we can send the task to: \n", candidate_gpus)

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                sorted_ = candidate_gpus.sort_values(by="smact", ascending=True, kind="mergesort")
                assigned_gpus = sorted_.head(number_of_GPUs_requested)

                print("assigned GPUs: ", assigned_gpus)
                a.set_service_time(now)
                a.set_status("dispatched")

                gpus_identifiers = format_gpu_identifiers(assigned_gpus.index)

                command = command_generator(dir, gpus_identifiers, command_to_execute, now, a)

                if main_queue_flag is True:
                    with lock:
                        main_queue.dequeue()
                else:
                    with recover_lock:
                        recovery_queue.dequeue()

                to_write = build_recovery_header(dir, environment, command_to_execute, task, user, a.task_id, now)

                logging.info(f"dispatched {a.task_id} - {gpus_identifiers}")

                Thread(target=command_executor, args=(to_write,)).start()
                pid = launch_and_get_pid(command)

                if pid is None:
                    logging.error(f"Failed to capture PID for {a.task_id}; leaving GPUs available")
                else:
                    for gpu_uuid in assigned_gpus.index:
                        launch_task(gpu_uuid, pid)

                    Thread(
                        target=_async_resolve_and_update,
                        args=(pid, list(assigned_gpus.index)),
                        daemon=True
                    ).start()

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, "EST-LUG Collocated task on GPUs")

            elif policy == "ml_predictor" and recovery_queue.length() == 0:
                a = None
                user, dir, file = None, None, None

                with lock:
                    a = main_queue.dequeue()
                    user, dir, file = a.user, a.dir, a.file
                    a.set_service_time(datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))
                    a.set_status("dispatched")

                command = f"cd {dir} ; cat {file}"
                ret = subprocess.run(command, capture_output=True, shell=True)
                commands = ret.stdout.decode()
                commands_to_execute = commands.split("\n")

                now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

                env_name = None
                for command in commands_to_execute:
                    if "activate" in command:
                        env_name = commands_to_execute[1].split("activate")[1].strip()
                        break
                if env_name is None:
                    env_name = "tf"

                environment = f"/home/{user}/.conda/envs/{env_name}"
                print(env_name, environment)

                command_to_execute = None
                for command in commands_to_execute:
                    if "python" in command:
                        command_to_execute = command
                        break
                if command_to_execute is None:
                    print("the command could not be found in the submitted job profile!")

                print("command to execute found: ", command_to_execute)

                cnn_features, fc_features, overhead = rad_parser.analyze_model_summary(
                    f"{dir}/{commands_to_execute[3]}",
                    commands_to_execute[4],
                    int(commands_to_execute[5])
                )

                global cnn_loaded_model
                global fc_loaded_model

                cnn_memory_predictor = cnn_loaded_model
                fc_memory_predictor = fc_loaded_model

                cnn_predicted_memory = cnn_memory_predictor.predict(cnn_features)
                fc_predicted_memory = fc_memory_predictor.predict(fc_features)

                print(cnn_predicted_memory, fc_predicted_memory, overhead)

                all_memory_estimation = cnn_predicted_memory[0] + fc_predicted_memory[0] + overhead

                time.sleep(61)
                gpus_with_metrics = monitor.Gmetrics
                temp_ = gpus_with_metrics.loc[gpus_with_metrics['GPU_mem_available'] > (all_memory_estimation)]
                candidate_gpus = temp_.loc[gpus_with_metrics['smact'] <= 0.8]

                sorted_ = candidate_gpus.sort_values(by="GPU_mem_available", ascending=False, kind="mergesort")

                print("gpus sorted:\n", sorted_)

                if candidate_gpus.empty:
                    print("No GPUs to submit job to!")
                    with lock:
                        main_queue.put_it_back(a)
                    continue
                else:
                    print("The gpus that we can send job to :) \n", candidate_gpus)
                    candidate_gpu_to_collocate_job = sorted_.index[0]
                    print("candidate GPU: ", candidate_gpu_to_collocate_job)

                logging.info(f"dispatched {a.task_id} - {candidate_gpu_to_collocate_job}")

                command = f"""cd {dir} ; . /opt/anaconda/etc/profile.d/conda.sh ; conda activate {environment} ; export CUDA_VISIBLE_DEVICES={candidate_gpu_to_collocate_job} ; {{ time {command_to_execute} 1> out-{user}-{now}-{file}-{a.task_id}.log 2>> err-{user}-{now}-{file}-{a.task_id}.log ; }} 2> time-{user}-{now}-{file}-{a.task_id}.et & pid=$!
                    wait $pid 
                    if [ $? -eq 0 ]; then
                        echo 'Successful' >> err-{user}-{now}-{file}-{a.task_id}.log
                    else
                        echo 'unsuccessful' >>  err-{user}-{now}-{file}-{a.task_id}.log
                    fi
                    """

                to_write = f'echo "{dir}+{environment}+{command_to_execute}+{file}+{user}+{a.task_id}" > err-{user}-{now}-{file}-{a.task_id}.log'

                Thread(target=command_executor, args=(to_write,)).start()
                Thread(target=command_executor, args=(command,)).start()

            timepoint = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            print(timepoint, "Number of tasks waiting in the queue: ", main_queue.length())
        else:
            pass


if __name__ == '__main__':
    Thread(target=server).start()
    Thread(target=scheduler).start()
    Thread(target=monitor.monitor_logger).start()
    Thread(target=monitor.top_system_logger).start()
