from __future__ import annotations

import os
import json
import shlex
import subprocess
import sys
import time

PID_SENTINEL = "__PID__:"

LEGACY_RTX_GPU_UUIDS = {
    "GPU-ea93b842-ff46-a040-3e86-9292c61a6654",
    "GPU-2bd2c45d-9e92-653b-8ea2-406dc6ad138f",
    "GPU-3b3c2291-7688-7cd4-ec0a-cdb638dd10e7",
    "GPU-a4f5bfcd-5a1a-e006-fcb4-cc25d681f4ea",
}

LEGACY_GTX_GPU_UUIDS = {
    "GPU-1c6317b1-1524-facb-b296-af9236965e45",
    "GPU-323af678-54fb-3c08-ae09-02f5f27c6ed6",
    "GPU-f9167b1e-3128-ca9e-6851-91863ac9987e",
    "GPU-341c9e18-417a-7e7c-3eec-c0a83d472ac0",
}


def legacy_mps_dirs_for_cuda_visible_devices(cuda_visible_devices: object) -> tuple[str | None, str | None]:
    """Return generation-specific MPS pipe/log dirs for Zeus legacy GPUs.

    Pascal GTX 1080 Ti clients are hidden behind the MPS server in nvidia-smi,
    and mixed RTX/GTX MPS daemons caused attachment/visibility issues. We use
    separate MPS daemons per generation and choose the pipe from the assigned
    GPU UUID.
    """
    devices = str(cuda_visible_devices)
    assigned = [part.strip() for part in devices.split(",") if part.strip()]

    if not assigned:
        return None, None

    if all(gpu in LEGACY_GTX_GPU_UUIDS for gpu in assigned):
        return "/tmp/nvidia-mps-gtx", "/tmp/nvidia-log-gtx"

    if all(gpu in LEGACY_RTX_GPU_UUIDS for gpu in assigned):
        return "/tmp/nvidia-mps-rtx", "/tmp/nvidia-log-rtx"

    # Mixed-generation multi-GPU jobs are intentionally not supported in this
    # legacy MPS setup. Keep the caller's environment unchanged.
    return None, None


def mps_env_exports(cuda_visible_devices: object) -> str:
    pipe_dir, log_dir = legacy_mps_dirs_for_cuda_visible_devices(cuda_visible_devices)
    if pipe_dir is None or log_dir is None:
        return ""
    return (
        f"export CUDA_MPS_PIPE_DIRECTORY={shlex.quote(pipe_dir)} ; "
        f"export CUDA_MPS_LOG_DIRECTORY={shlex.quote(log_dir)} ; "
    )

def launch_and_get_pid(cmd: str, timeout_s: float = 10.0) -> int | None:
    p = subprocess.Popen(
        ["bash", "-lc", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )

    debug_lines = []
    deadline = time.time() + timeout_s

    try:
        while time.time() < deadline:
            if p.stdout is None:
                break

            line = p.stdout.readline()
            if not line:
                if p.poll() is not None:
                    break
                time.sleep(0.1)
                continue

            s = line.strip()

            if s.startswith(PID_SENTINEL):
                pid_text = s[len(PID_SENTINEL):].strip()
                try:
                    return int(pid_text)
                except ValueError:
                    debug_lines.append(s)
                    break

            debug_lines.append(s)

        print(f"[launcher] PID capture failed. Initial stdout lines: {debug_lines[:10]}")
        return None

    finally:
        if p.stdout:
            p.stdout.close()

def build_event_cli_command(
    event_path: str,
    record: dict,
    return_code_var: str | None = None,
) -> str:
    command = (
        f"{shlex.quote(sys.executable)} -m runtime.event_cli "
        f"--event-path {shlex.quote(event_path)} "
        f"--record-json {shlex.quote(json.dumps(record, sort_keys=True, default=str))}"
    )

    if return_code_var is not None:
        command += f' --return-code "${return_code_var}"'

    return command

def build_launch_command(
    dir,
    gpus_identifiers,
    command_to_execute,
    now,
    task_obj,
    event_path,
    run_id,
    cuda_visible_devices=None,
    log_dir=None,
):
    cuda_visible_devices = (
        gpus_identifiers if cuda_visible_devices is None else cuda_visible_devices
    )

    completed_event_cmd = build_event_cli_command(
        event_path,
        {
            "event": "completed",
            "task_id": str(task_obj.task_id),
            "task": task_obj.task,
            "workdir": dir,
            "cuda_visible_devices": cuda_visible_devices,
            "run_id": run_id,
        },
        return_code_var="rc",
    )

    failed_event_cmd = build_event_cli_command(
        event_path,
        {
            "event": "failed",
            "task_id": str(task_obj.task_id),
            "task": task_obj.task,
            "workdir": dir,
            "cuda_visible_devices": cuda_visible_devices,
            "run_id": run_id,
        },
        return_code_var="rc",
    )

    clean_command = " ".join(str(command_to_execute).split())

    log_dir = dir if log_dir is None else log_dir
    os.makedirs(log_dir, exist_ok=True)
    
    out_log = f"{log_dir}/out-{now}-{task_obj.task_id}.log"
    err_log = f"{log_dir}/err-{now}-{task_obj.task_id}.log"
    time_log = f"{log_dir}/time-{now}-{task_obj.task_id}.et"

    command = (
        f"cd {shlex.quote(dir)} ; "
        f"export CUDA_VISIBLE_DEVICES={shlex.quote(str(cuda_visible_devices))} ; "
        f"{mps_env_exports(cuda_visible_devices)}"
        f"exec 3>&1 ; "
        f"{{ time ( "
        f"{{ "
        f"conda run --no-capture-output -p /home/eyousefzadeh/miniconda3/envs/tf {clean_command} & pid=$! ; "
        f"echo '__PID__:'\"$pid\" >&3 ; "
        f"wait $pid ; rc=$? ; "
        f"if [ $rc -eq 0 ]; then "
        f"echo 'Successful' >> {shlex.quote(err_log)} ; "
        f"{completed_event_cmd} ; "
        f"else "
        f"echo 'unsuccessful' >> {shlex.quote(err_log)} ; "
        f"{failed_event_cmd} ; "
        f"fi ; "
        f"}} 1> {shlex.quote(out_log)} 2>> {shlex.quote(err_log)} "
        f") ; }} 2> {shlex.quote(time_log)} ; "
        f"exec 3>&-"
    )
    return command


def command_executor(command):
    subprocess.run(command, shell=True, check=True, executable="/bin/bash")