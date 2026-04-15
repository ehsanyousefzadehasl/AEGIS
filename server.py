import socket
import time
import datetime
from threading import Thread, Lock
import subprocess
import os
import logging
from itertools import cycle, islice


from telemetry import monitor
from telemetry.gpu_state import init_gpu_state, launch_task, update, all_available_GPUs
from queueing.task_queue import Task, Tasks
from queueing.selection import peek_next_job
from config.load_yaml import load_yaml
from workload.job_spec import load_job_spec
from runtime.dispatch import dispatch_selected_job
from runtime.pid_resolution import resolve_and_update_gpu_pid
from runtime.submission_server import run_submission_server
from runtime.launcher import launch_and_get_pid, build_launch_command, command_executor
from placement.dispatcher import dispatch_placement, is_dispatcher_policy
from placement.inputs import resolve_policy_inputs
from recovery.manager import recovery


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


#  ====== initialized GPUs ======
gpus_state = init_gpu_state(gpu_UUIDs)
print("Initialized the gpus_state tracker: ", gpus_state)


def server():
    host = socket.gethostname()
    run_submission_server(
        main_queue=main_queue,
        main_lock=lock,
        host=host,
        port=5001,
    )


def scheduler(policy=policy, estimator=estimator):

    while True:
        time.sleep(1)

        recovery(
            dirs=[recovery_dir],
            handled_crashes=handled_crashes,
            task_cls=Task,
            recovery_queue=recovery_queue,
            recovery_lock=recover_lock,
            logger=logger,
        )
        
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

            selected = peek_next_job(main_queue, recovery_queue, lock, recover_lock)
            if selected is None:
                continue

            a = selected.task_obj
            user, dir, task = selected.user, selected.dir, selected.task

            spec = load_job_spec_safe(task, estimator)
            if spec is None:
                continue

            env_name = spec.env_name
            environment = spec.env_path
            command_to_execute = spec.command_to_execute
            number_of_GPUs_requested = spec.num_gpus_requested

            print("conda environment to activate: ", env_name, environment)

            now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

            gpu_memory_requirement, gpu_memory_estimation = resolve_policy_inputs(
                policy=policy,
                spec=spec,
                workdir=dir,
                estimator_name=estimator,
            )

            if len(idle_and_available) >= number_of_GPUs_requested:
                assigned_gpus = idle_and_available[:number_of_GPUs_requested]

                dispatch_selected_job(
                    selected=selected,
                    task_obj=a,
                    user=user,
                    dir=dir,
                    task=task,
                    environment=environment,
                    command_to_execute=command_to_execute,
                    assigned_gpu_ids=assigned_gpus,
                    now=now,
                    main_queue=main_queue,
                    recovery_queue=recovery_queue,
                    main_lock=lock,
                    recovery_lock=recover_lock,
                    command_generator=build_launch_command,
                    command_executor=command_executor,
                    launch_and_get_pid=launch_and_get_pid,
                    launch_task=launch_task,
                    async_resolve_and_update=resolve_and_update_gpu_pid,
                    logger=logger,
                )

                print(gpus_state)
                continue

            if is_dispatcher_policy(policy) and (main_queue.length() != 0 and recovery_queue.length() == 0):
                if policy.startswith("oracle-") and gpu_memory_requirement is None:
                    print(f"Could not parse GPU memory requirement for task {task}")
                    continue

                if (policy.startswith("EST-") or policy.startswith("ONLINE-EST-")) and gpu_memory_estimation is None:
                    print(f"Could not parse GPU memory estimate for task {task} using estimator {estimator}")
                    continue

                gpus_with_metrics = None
                if policy != "OR-RR":
                    gpus_with_metrics = monitor.analyze_Gmetrics()
                    print(gpus_with_metrics)

                assigned_gpus = dispatch_placement(
                    policy=policy,
                    gpus_with_metrics=gpus_with_metrics,
                    available_gpu_ids=all_available_GPUs(),
                    number_of_gpus_requested=number_of_GPUs_requested,
                    gpu_memory_requirement=gpu_memory_requirement,
                    gpu_memory_estimation=gpu_memory_estimation,
                    round_robin_generator=round_robin_generator,
                    gpu_ids=GPU_IDs,
                )

                if assigned_gpus is None:
                    print("Not enough GPUs to submit the task to!")
                    continue

                print("assigned GPUs: ", assigned_gpus)

                assigned_gpu_ids = assigned_gpus if policy == "OR-RR" else assigned_gpus.index

                dispatch_selected_job(
                    selected=selected,
                    task_obj=a,
                    user=user,
                    dir=dir,
                    task=task,
                    environment=environment,
                    command_to_execute=command_to_execute,
                    assigned_gpu_ids=assigned_gpu_ids,
                    now=now,
                    main_queue=main_queue,
                    recovery_queue=recovery_queue,
                    main_lock=lock,
                    recovery_lock=recover_lock,
                    command_generator=build_launch_command,
                    command_executor=command_executor,
                    launch_and_get_pid=launch_and_get_pid,
                    launch_task=launch_task,
                    async_resolve_and_update=resolve_and_update_gpu_pid,
                    logger=logger,
                )

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, f"{policy} placed task on GPUs")
                continue

            timepoint = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            print(timepoint, "Number of tasks waiting in the queue: ", main_queue.length())
        else:
            pass


if __name__ == '__main__':
    Thread(target=server).start()
    Thread(target=scheduler).start()
    Thread(target=monitor.monitor_logger).start()
    Thread(target=monitor.top_system_logger).start()