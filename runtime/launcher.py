from __future__ import annotations

import os
import subprocess


def launch_and_get_pid(cmd: str) -> int | None:
    p = subprocess.Popen(
        ["bash", "-lc", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    pid_line = p.stdout.readline().strip() if p.stdout else ""
    if p.stdout:
        p.stdout.close()
    try:
        return int(pid_line)
    except ValueError:
        return None


def build_launch_command(dir, gpus_identifiers, command_to_execute, now, task_obj):
    command = f"""cd {dir} ; \
                export CUDA_VISIBLE_DEVICES={gpus_identifiers} ; \
                exec 3>&1 ; \
                {{ time ( \
                    {{ \
                        conda run --no-capture-output -p /opt/miniconda3/envs/tf {command_to_execute} & pid=$! ; \
                        echo $pid >&3 ; \
                        wait $pid ; \
                        if [ $? -eq 0 ]; then \
                            echo 'Successful' >> {dir}/err-{now}-{task_obj.task_id}.log ; \
                        else \
                            echo 'unsuccessful' >> {dir}/err-{now}-{task_obj.task_id}.log ; \
                        fi ; \
                    }} 1> {dir}/out-{now}-{task_obj.task_id}.log 2>> {dir}/err-{now}-{task_obj.task_id}.log \
                ) ; }} 2> {dir}/time-{now}-{task_obj.task_id}.et ; \
                exec 3>&-"""
    return command


def command_executor(command):
    subprocess.run(command, shell=True, check=True, executable="/bin/bash")