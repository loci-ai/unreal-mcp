import socket
import threading
import json
import unreal

from commands.commands import Commands

UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55558


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
            data = client_socket.recv(self.buffer_size)
            if not data:
                return  # Client disconnected

            message = json.loads(data.decode("utf-8"))
            function_name = message.get("type")
            arguments = message.get("params", {})

            # Execute the Unreal function
            result = self.execute_function(function_name, arguments)

            client_socket.sendall(json.dumps(result).encode("utf-8"))

        except Exception as e:
            unreal.log_error(f"Error in client loop: {repr(e)}")
            client_socket.sendall(json.dumps({"error": repr(e)}).encode("utf-8"))
        finally:
            client_socket.close()

    def execute_function(self, function_name, arguments):
        unreal.log(f"Executing function: {function_name} with arguments: {arguments}")
        try:
            func = getattr(Commands, function_name, None)
            if callable(func):
                return func(**arguments)
            else:
                return f"Function '{function_name}' not found."
        except Exception as e:
            return {"error": repr(e)}
