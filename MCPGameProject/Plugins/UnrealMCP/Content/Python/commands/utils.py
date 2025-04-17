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
