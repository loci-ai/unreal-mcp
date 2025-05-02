"""
Actor Tools for Unreal MCP.

This module provides tools for creating, manipulating, and inspecting actors in Unreal Engine.
"""

import logging
import unreal

from typing import Dict, List, Any, Literal
from mcp.server.fastmcp import FastMCP, Context

from runner import GameThreadRunner
from .utils.terrain_generation import create_heightmap

logger = logging.getLogger("UnrealMCP")


def get_actor_info(actor: unreal.Actor) -> Dict[str, Any]:
    """Get detailed info about an actor, including its location, rotation, scale, and bounding box."""
    if isinstance(actor, unreal.StaticMeshActor):
        return get_static_mesh_actor_info(actor)
    else:
        return {
            "name": actor.get_name(),
            "path_name": actor.get_path_name().split(":")[-1],
            "label": actor.get_actor_label(),
            "location": [
                actor.get_actor_location().x,
                actor.get_actor_location().y,
                actor.get_actor_location().z,
            ],
            "rotation": [
                actor.get_actor_rotation().pitch,
                actor.get_actor_rotation().yaw,
                actor.get_actor_rotation().roll,
            ],
            "scale": [
                actor.get_actor_scale3d().x,
                actor.get_actor_scale3d().y,
                actor.get_actor_scale3d().z,
            ],
        }


def get_static_mesh_actor_info(actor: unreal.Actor) -> Dict[str, Any]:
    mesh_component = actor.static_mesh_component
    mesh = mesh_component.get_editor_property("static_mesh")

    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()

    # Bounding box info
    origin, box_extent = actor.get_actor_bounds(
        False
    )  # False = do not include children
    bbox_min = [
        origin.x - box_extent.x,
        origin.y - box_extent.y,
        origin.z - box_extent.z,
    ]
    bbox_max = [
        origin.x + box_extent.x,
        origin.y + box_extent.y,
        origin.z + box_extent.z,
    ]
    actor.get_actor_label()
    info = {
        "name": actor.get_name(),
        "path_name": actor.get_path_name().split(":")[-1],
        "label": actor.get_actor_label(),
        "mesh_name": mesh.get_name() if mesh else None,
        "mesh_path": mesh.get_path_name() if mesh else None,
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
        "scale": [scale.x, scale.y, scale.z],
        # "tags": actor.tags,
        "bounds": {
            "origin": [origin.x, origin.y, origin.z],
            "extent": [box_extent.x, box_extent.y, box_extent.z],
            "min": bbox_min,
            "max": bbox_max,
        },
    }

    return info


def register_actor_tools(mcp: FastMCP):
    """Register actor tools with the MCP server."""

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def create_primative_static_mesh_actor(
        ctx: Context,
        shape_type: Literal["cube", "sphere", "cone", "cylinder", "plane"],
        name: str | None = None,
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0],
        scale: List[float] = [1.0, 1.0, 1.0],
    ) -> Dict[str, Any]:
        """Creates a StaticMeshActor using a built-in primitive shape.
        The Rotation is specified as pitch (around Y axis), roll (around X axis), yaw (around Z axis) in degrees.
        """

        PRIMITIVE_MESH_PATHS = {
            "cube": "/Engine/BasicShapes/Cube.Cube",
            "sphere": "/Engine/BasicShapes/Sphere.Sphere",
            "cone": "/Engine/BasicShapes/Cone.Cone",
            "cylinder": "/Engine/BasicShapes/Cylinder.Cylinder",
            "plane": "/Engine/BasicShapes/Plane.Plane",
        }

        asset_path = PRIMITIVE_MESH_PATHS.get(shape_type)

        if not asset_path:
            raise ValueError(f"Unsupported primitive shape: {shape_type}")

        static_mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not static_mesh:
            raise RuntimeError(
                f"Failed to load mesh asset for '{shape_type}' at {asset_path}"
            )

        # Spawn a StaticMeshActor
        location = unreal.Vector(*location)
        rotation = unreal.Rotator(*rotation)
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor, location, rotation
        )

        # Set mesh and transform
        actor.static_mesh_component.set_static_mesh(static_mesh)
        actor.set_actor_scale3d(unreal.Vector(*scale))

        # Optionally rename
        if name:
            actor.set_actor_label(name)

        return {"success": True, "actor_info": get_actor_info(actor)}

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def delete_actor(
        ctx: Context,
        path_name: str,
    ) -> Dict[str, Any]:
        """Deletes an actor by path name."""
        actor = unreal.EditorLevelLibrary.get_actor_reference(path_name)
        if actor:
            unreal.EditorLevelLibrary.destroy_actor(actor)
            return {"success": True}
        else:
            return {"success": False, "error": "Actor not found"}

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def modify_actor(
        ctx: Context,
        path_name: str,
        location: List[float] | None = None,
        rotation: List[float] | None = None,
        scale: List[float] | None = None,
    ) -> Dict[str, Any]:
        """Modifies an actor's transform."""
        actor = unreal.EditorLevelLibrary.get_actor_reference(path_name)
        if not actor:
            return {"success": False, "error": "Actor not found"}

        if location:
            actor.set_actor_location(
                new_location=unreal.Vector(*location), sweep=False, teleport=True
            )
        if rotation:
            actor.set_actor_rotation(
                new_rotation=unreal.Rotator(*rotation), teleport_physics=True
            )
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))

        return {"success": True, "actor_info": get_actor_info(actor)}

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def get_all_static_mesh_actors_info() -> List[Dict[str, Any]]:
        """Returns detailed info about all StaticMeshActors in the current level, including bounding boxes."""

        actors = unreal.EditorActorSubsystem().get_all_level_actors()
        results = []
        logger.info("HI")

        for actor in actors:
            if not isinstance(actor, unreal.StaticMeshActor):
                continue

            results.append(get_actor_info(actor))

        return results

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def get_all_actors_info() -> List[Dict[str, Any]]:
        """Returns detailed info about all actors in the current level, including bounding boxes."""

        actors = unreal.EditorActorSubsystem().get_all_level_actors()
        results = []

        for actor in actors:
            results.append(get_actor_info(actor))

        return results
