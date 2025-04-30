import json
import queue
import threading
import uuid
import unreal
from functools import wraps


class GameThreadRunner:
    """
    Execute commands on the game thread.
    """

    _main_thread_task_queue = queue.Queue()
    _return_registry = {}

    @classmethod
    def run_on_main_thread(cls, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if unreal.PythonExtension.is_in_game_thread():
                return func(*args, **kwargs)
            task_id = str(uuid.uuid4())
            cls._main_thread_task_queue.put((task_id, func, args, kwargs))
            while task_id not in cls._return_registry:
                threading.Event().wait(0.005)
            result = cls._return_registry.pop(task_id)
            if isinstance(result, Exception):
                raise result
            return result

        return wrapper

    @classmethod
    def run_cpp_command(cls, command, params):
        @cls.run_on_main_thread
        def run():
            params_json = json.dumps(params)
            bridge = unreal.get_editor_subsystem(unreal.UnrealMCPBridge)
            return bridge.execute_command_from_json(command, params_json)

        return run()

    @classmethod
    def tick_callback(cls, delta_seconds):
        while not cls._main_thread_task_queue.empty():
            task_id, func, args, kwargs = cls._main_thread_task_queue.get()
            try:
                cls._return_registry[task_id] = func(*args, **kwargs)
                unreal.log(f"Task {task_id} completed")
            except Exception as e:
                cls._return_registry[task_id] = e
                unreal.log_error(f"Main thread task error: {e}")
