import unreal
import inspect
import textwrap
import threading
import uuid
import json
from typing import Any


class Responses:
    @staticmethod
    def create_success_response(data: dict[str, Any] = {}) -> dict[str, Any]:
        """
        Create a success response for the command.
        """
        return {"success": True, **data}

    @staticmethod
    def create_error_response(message: str) -> dict[str, Any]:
        """
        Create an error response for the command.
        """
        return {"success": False, "error": message}

    @staticmethod
    def _vector_to_list(vector: unreal.Vector) -> list[float]:
        """
        Convert an Unreal Vector to a list of floats.
        """
        return [vector.x, vector.y, vector.z]

    @staticmethod
    def _rotator_to_list(rotator: unreal.Rotator) -> list[float]:
        """
        Convert an Unreal Rotator to a list of floats.
        """
        return [rotator.pitch, rotator.yaw, rotator.roll]

    @staticmethod
    def actor_to_json(actor: unreal.Actor) -> dict[str, Any]:
        """
        Convert an Unreal actor to a JSON-compatible dictionary.
        """
        return {
            "name": actor.get_actor_label(),
            "class": actor.get_class().get_name(),
            "location": Responses._vector_to_list(actor.get_actor_location()),
            "rotation": Responses._rotator_to_list(actor.get_actor_rotation()),
            "scale": Responses._vector_to_list(actor.get_actor_scale3d()),
        }


# Registry to store return values
_return_registry = {}


def run_on_main_thread(func):
    def wrapper(*args, **kwargs):
        task_id = str(uuid.uuid4())
        args_json = json.dumps(args)
        kwargs_json = json.dumps(kwargs)

        # Extract and dedent the function's source code
        source_lines = inspect.getsourcelines(func)[0]
        while source_lines[0].lstrip().startswith("@"):
            source_lines.pop(0)
        func_def = textwrap.dedent("".join(source_lines))

        # Build the code to execute
        python_code = f"""
import json
import unreal
from typing import Any
from commands.utils import _return_registry, Responses
{func_def}
args = json.loads('''{args_json}''')
kwargs = json.loads('''{kwargs_json}''')
try:
    _return_registry['{task_id}'] = {func.__name__}(*args, **kwargs)
except Exception as e:
    unreal.log_warning(f"Error in function {func.__name__}:" + repr(e))
    _return_registry['{task_id}'] = Responses.create_error_response(repr(e))
"""
        # Dedent the entire code block to ensure proper formatting
        python_code = python_code

        unreal.log("--- Executing Python Code ---")
        unreal.log(python_code)
        unreal.log("-----------------------------")

        # Execute the code on the main thread
        unreal.PythonExtension.launch_script_on_game_thread(python_code)

        # Wait for the result
        while task_id not in _return_registry:
            threading.Event().wait(0.01)

        return _return_registry.pop(task_id)

    return wrapper
