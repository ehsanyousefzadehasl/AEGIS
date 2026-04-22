import time
import datetime
import logging

from telemetry import monitor
from telemetry.gpu_state import launch_task, update, all_available_GPUs
from queueing.task_queue import Task
from queueing.selection import peek_next_job
from workload.job_spec import load_job_spec
from runtime.state import lock, recover_lock, main_queue, recovery_queue
from runtime.dispatch import dispatch_selected_job
from runtime.pid_resolution import resolve_and_update_gpu_pid
from runtime.launcher import launch_and_get_pid, build_launch_command, command_executor
from runtime.bootstrap import configure_scheduler_logger, initialize_scheduler_runtime
from placement.dispatcher import (
    dispatch_policy_placement,
    resolve_policy_placement_estimate,
    validate_policy_placement,
)
from placement.profiles import policy_requires_gpu_metrics, policy_uses_dispatcher
from placement.admission import should_dispatch_exclusive_first
from recovery.manager import recovery


def load_job_spec_safe(task_path: str, estimator_name: str):
    try:
        return load_job_spec(task_path, estimator_name)
    except Exception as e:
        logging.exception("Failed to load job spec from %s: %s", task_path, e)
        print(f"Failed to load job spec from {task_path}: {e}")
        return None


logger = configure_scheduler_logger()

runtime_state = initialize_scheduler_runtime()

event_path = runtime_state.event_path
run_id = runtime_state.run_id

settings = runtime_state.settings

policy = settings.policy
print("Configured mapping policy:", policy)

estimator = settings.estimator
print("Configured mapping estimator:", estimator)

recovery_dir = settings.recovery_dir
print("Configured recovery directory:", recovery_dir)

gpu_UUIDs = runtime_state.gpu_uuids
GPU_IDs = runtime_state.gpu_ids
round_robin_generator = runtime_state.round_robin_generator
gpus_state = runtime_state.gpus_state
handled_crashes = runtime_state.handled_crashes

print("Initialized the gpus_state tracker: ", gpus_state)

patience = settings.patience
monitoring_window_size = settings.monitoring_window_size

def run_scheduler(policy=policy, estimator=estimator):

    while True:
        time.sleep(1)

        recovery(
            dirs=[recovery_dir],
            handled_crashes=handled_crashes,
            task_cls=Task,
            recovery_queue=recovery_queue,
            recovery_lock=recover_lock,
            logger=logger,
            policy=policy,
            estimator_name=estimator,
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

            placement_estimate = resolve_policy_placement_estimate(
                policy=policy,
                spec=spec,
                workdir=dir,
                estimator_name=estimator,
            )

            force_full_gpu_recovery = bool(a.recovery_force_full_gpu)
            
            if (
                force_full_gpu_recovery
                and len(idle_and_available) >= number_of_GPUs_requested
            ) or should_dispatch_exclusive_first(
                policy=policy,
                idle_and_available=idle_and_available,
                number_of_gpus_requested=number_of_GPUs_requested,
            ):
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
                    event_path=event_path,
                    run_id=run_id,
                )

                print(gpus_state)
                continue

            if (
                not force_full_gpu_recovery
                and policy_uses_dispatcher(policy)
                and (main_queue.length() != 0 and recovery_queue.length() == 0)
            ):
                missing_input_message = validate_policy_placement(
                    policy=policy,
                    task=task,
                    estimator_name=estimator,
                    placement_estimate=placement_estimate,
                )

                if missing_input_message is not None:
                    print(missing_input_message)
                    continue

                gpus_with_metrics = None
                if policy_requires_gpu_metrics(policy):
                    gpus_with_metrics = monitor.analyze_Gmetrics()
                    print(gpus_with_metrics)

                assigned_gpu_ids = dispatch_policy_placement(
                    policy=policy,
                    gpus_with_metrics=gpus_with_metrics,
                    available_gpu_ids=all_available_GPUs(),
                    number_of_gpus_requested=number_of_GPUs_requested,
                    recovery_min_free_mib_override=a.recovery_min_free_mib_override,
                    placement_estimate=placement_estimate,
                    round_robin_generator=round_robin_generator,
                    gpu_ids=GPU_IDs,
                )

                if assigned_gpu_ids is None:
                    print("Not enough GPUs to submit the task to!")
                    continue

                print("assigned GPUs: ", assigned_gpu_ids)

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
                    event_path=event_path,
                    run_id=run_id,
                )

                time_point = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                print(time_point, f"{policy} placed task on GPUs")
                continue

            timepoint = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            print(timepoint, "Number of tasks waiting in the queue: ", main_queue.length())
        else:
            pass