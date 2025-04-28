import socket
import threading
import uuid
import json
from typing import Any

import unreal

from commands.commands import Commands
from commands.utils import Responses

UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55558


class Runner:
    """
    This class is responsible for executing commands on the main thread.
    """

    _return_registry = {}

    @classmethod
    def run_on_main_thread(cls, message: str, task_id: str):
        try:
            command = json.loads(message)
            function_name = command.get("type")
            arguments = command.get("params", {})
            function = getattr(Commands, function_name, None)
            cls._return_registry[task_id] = function(**arguments)
        except Exception as e:
            unreal.log_warning(repr(e))
            cls._return_registry[task_id] = Responses.create_error_response(repr(e))

    @classmethod
    def run(cls, message: str) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        python_code = f"Runner.run_on_main_thread('''{message}''', '{task_id}')"
        unreal.PythonExtension.launch_script_on_game_thread(python_code)
        while task_id not in cls._return_registry:
            threading.Event().wait(0.01)

        return cls._return_registry.pop(task_id)


class MCPServer:
    """
    A simple socket server to handle Unreal Engine commands.
    This server listens for incoming connections and executes functions
    """

    def __init__(self, host=UNREAL_HOST, port=UNREAL_PORT, buffer_size=65536):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.server_socket = None
        self.running = False

    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Recommended defaults for long-lived, low-latency RPC socket
        self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Optional tuning if expecting big payloads:
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_RCVBUF, self.buffer_size
        )
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_SNDBUF, self.buffer_size
        )

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        unreal.log(f"Socket server started on {self.host}:{self.port}")
        threading.Thread(target=self.accept_connections, daemon=True).start()

    def accept_connections(self):
        while self.running:
            client_socket, addr = self.server_socket.accept()
            unreal.log(f"Accepted connection from {addr}")
            threading.Thread(
                target=self.handle_client, args=(client_socket,), daemon=True
            ).start()

    def handle_client(self, client_socket: socket.socket):
        try:
            message = client_socket.recv(self.buffer_size)
            if not message:
                return  # Client disconnected

            # Execute the Unreal function
            result = Runner.run(message.decode("utf-8"))

            client_socket.sendall(json.dumps(result).encode("utf-8"))

        except Exception as e:
            unreal.log_error(f"Error in client loop: {repr(e)}")
            client_socket.sendall(json.dumps({"error": repr(e)}).encode("utf-8"))
        finally:
            client_socket.close()
