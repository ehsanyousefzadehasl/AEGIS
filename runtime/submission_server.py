from __future__ import annotations

import logging
import socket

from queueing.task_queue import Task
from runtime.events import append_jsonl_event

def run_submission_server(
    *,
    main_queue,
    main_lock,
    host: str,
    port: int = 5001,
):
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

            user, dir, task = data.split("+")
            task = "/" + task[1:]

            print(user, dir, task)

            task_obj = Task(user, dir, task)

            with main_lock:
                main_queue.enqueue(task_obj)
                logging.info(f"queued {task_obj.task_id} - {task_obj.task}")
                
                append_jsonl_event(
                    event_path=f"{dir}/events.jsonl",
                    record={
                        "event": "submitted",
                        "task_id": str(task_obj.task_id),
                        "task": task_obj.task,
                        "task_file": task,
                        "user": user,
                        "workdir": dir,
                        "source": "submission_server",
                    },
                )

        conn.close()