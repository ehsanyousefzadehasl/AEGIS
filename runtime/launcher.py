from __future__ import annotations

import os
import json
import shlex
import subprocess
import sys
import time

PID_SENTINEL = "__PID__:"

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

def build_event_cli_command(event_path: str, record: dict) -> str:
    return (
        f"{shlex.quote(sys.executable)} -m runtime.event_cli "
        f"--event-path {shlex.quote(event_path)} "
        f"--record-json {shlex.quote(json.dumps(record, sort_keys=True, default=str))}"
    )

def build_launch_command(
    dir,
    gpus_identifiers,
    command_to_execute,
    now,
    task_obj,
    event_path,
    run_id,
):
    completed_event_cmd = build_event_cli_command(
        event_path,
        {
            "event": "completed",
            "task_id": str(task_obj.task_id),
            "task": task_obj.task,
            "workdir": dir,
            "cuda_visible_devices": gpus_identifiers,
            "run_id": run_id,
        },
    )

    failed_event_cmd = build_event_cli_command(
        event_path,
        {
            "event": "failed",
            "task_id": str(task_obj.task_id),
            "task": task_obj.task,
            "workdir": dir,
            "cuda_visible_devices": gpus_identifiers,
            "run_id": run_id,
        },
    )

    clean_command = " ".join(str(command_to_execute).split())

    out_log = f"{dir}/out-{now}-{task_obj.task_id}.log"
    err_log = f"{dir}/err-{now}-{task_obj.task_id}.log"
    time_log = f"{dir}/time-{now}-{task_obj.task_id}.et"

    command = (
        f"cd {shlex.quote(dir)} ; "
        f"export CUDA_VISIBLE_DEVICES={shlex.quote(str(gpus_identifiers))} ; "
        f"exec 3>&1 ; "
        f"{{ time ( "
        f"{{ "
        f"conda run --no-capture-output -p /opt/miniconda3/envs/tf {clean_command} & pid=$! ; "
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