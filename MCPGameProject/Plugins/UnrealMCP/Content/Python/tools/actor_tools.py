"""
Actor Tools for Unreal MCP.

This module provides tools for creating, manipulating, and inspecting actors in Unreal Engine.
"""

import logging
from .editor_tools import (
    import_file_if_required,
)
import unreal
from os.path import join

from typing import Dict, List, Any, Literal
from mcp.server.fastmcp import FastMCP, Context

from runner import GameThreadRunner
from .utils.responses import Responses

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


def import_and_spawn_glb_to_actor(
    glb_path: str,
    actor_name: str,
    destination_path: str = "/Game/ImportedAssets",
) -> unreal.StaticMeshActor:
    """
    Imports a GLB file into Unreal as a StaticMesh asset.

    Args:
        glb_path (str): Absolute path to the .glb file.
        actor_name (str): Name of the actor to spawn. Always give a meaningful name to the actor (e.g Tree_01).
        destination_path (str): Unreal content browser path to import to (default: "/Game/ImportedAssets").

    Returns:
        str: Returns true if import was successful.
    """
    source_data = unreal.InterchangeManager.create_source_data(glb_path)

    current_level = unreal.LevelEditorSubsystem().get_current_level()

    import_asset_parameters = unreal.ImportAssetParameters(
        is_automated=True,  # Run without UI
        import_level=current_level,  # Specify which level to import into
        replace_existing=True,  # Replace existing assets if needed
        destination_name=unreal.Paths.get_base_filename(
            glb_path
        ),  # Use filename as base name
    )

    # Get the GLB-specific pipeline
    interchange_manager = unreal.InterchangeManager.get_interchange_manager_scripted()

    all_actors_names_before_import = [
        x.get_name() for x in unreal.EditorActorSubsystem().get_all_level_actors()
    ]

    success = interchange_manager.import_scene(
        destination_path, source_data, import_asset_parameters
    )

    if not success:
        print("Failed to import GLB file.")
        return Responses.create_error_response("Failed to import GLB file.")

    # Find all matching StaticMeshActors in the scene
    actors_to_merge = []
    all_actors = unreal.EditorActorSubsystem().get_all_level_actors()

    for actor in all_actors:
        if (
            isinstance(actor, unreal.StaticMeshActor)
            and actor.get_name() not in all_actors_names_before_import
        ):
            actors_to_merge.append(actor)

    if not actors_to_merge:
        print("No matching StaticMeshActors found in the scene.")
        return Responses.create_error_response(
            "No matching StaticMeshActors found in the scene."
        )

    meshMergeOptions = unreal.MergeStaticMeshActorsOptions(
        destroy_source_actors=True,
        new_actor_label=actor_name,
        rename_components_from_source=True,
        spawn_merged_actor=True,
        base_package_name=join(
            destination_path, unreal.Paths.get_base_filename(glb_path)
        ),
    )

    static_mesh_editor_subsystem = unreal.get_editor_subsystem(
        unreal.StaticMeshEditorSubsystem
    )

    merged_actor = static_mesh_editor_subsystem.merge_static_mesh_actors(
        actors_to_merge, meshMergeOptions
    )

    if not merged_actor:
        print("Failed to merge static meshes.")
        return Responses.create_error_response("Failed to merge static meshes.")

    for actor in all_actors:
        if actor.get_name() not in all_actors_names_before_import:
            unreal.EditorLevelLibrary.destroy_actor(actor)

    return merged_actor


def register_actor_tools(mcp: FastMCP):
    """Register actor tools with the MCP server."""

    # @mcp.tool()
    # @GameThreadRunner.run_on_main_thread
    # def move_actor_pivot_to_bottom(path_name: str):
    #     """Move the pivot of the actor to the bottom of the mesh.

    #     Args:
    #         path_name: The path of the actor to move the pivot of.
    #     """
    #     # Get the actor reference
    #     actor = unreal.EditorLevelLibrary.get_actor_reference(path_name)
    #     if not actor:
    #         return {"success": False, "error": f"Actor not found: {path_name}"}

    #     # Ensure it's a StaticMeshActor
    #     if not isinstance(actor, unreal.StaticMeshActor):
    #         return {
    #             "success": False,
    #             "error": f"Actor is not a StaticMeshActor: {path_name}",
    #         }

    #     # Get the static mesh component
    #     static_mesh_component = actor.static_mesh_component
    #     if not static_mesh_component:
    #         return {
    #             "success": False,
    #             "error": f"No static mesh component found for actor: {path_name}",
    #         }

    #     # Get bounds in local space to avoid issues with world transforms
    #     origin, extent = static_mesh_component.get_local_bounds()
    #     unreal.log(f"Local Origin: {origin}, Local Extent: {extent}")

    #     # Calculate the new location to place the pivot at the bottom
    #     current_location = actor.get_actor_location()
    #     new_location = current_location + unreal.Vector(0, 0, extent.z)
    #     actor.set_actor_location(new_location, False, False)

    #     # Log and return success
    #     unreal.log(f"Moved pivot of {path_name} to bottom: {new_location}")
    #     return {
    #         "success": True,
    #         "message": f"Moved pivot of {path_name} to bottom: {new_location}",
    #     }

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def import_and_spawn_glb(
        ctx: Context,
        glb_path: str,
        name: str,
        destination_path: str = "/Game/Imported",
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0],
        scale: List[float] = [1.0, 1.0, 1.0],
    ) -> Dict[str, Any]:
        """Imports a GLB file and spawns it as a StaticMeshActor.
        Use this instead of spawn_static_mesh_actor for .GLB files.
        """
        merged_actor = import_and_spawn_glb_to_actor(
            actor_name=name, glb_path=glb_path, destination_path=destination_path
        )
        if not merged_actor:
            return Responses.create_error_response(
                "Failed to import and spawn GLB file."
            )
        # Set transform

        merged_actor.set_actor_location(
            new_location=unreal.Vector(*location), sweep=False, teleport=True
        )

        merged_actor.set_actor_rotation(
            new_rotation=unreal.Rotator(*rotation), teleport_physics=True
        )

        merged_actor.set_actor_scale3d(unreal.Vector(*scale))

        return Responses.create_success_response(get_actor_info(merged_actor))

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def spawn_static_mesh_actor(
        ctx: Context,
        asset_path: str,
        name: str | None = None,
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0],
        scale: List[float] = [1.0, 1.0, 1.0],
    ) -> Dict[str, Any]:
        """Creates a StaticMeshActor using a built-in primitive shape.

        Args:
            asset_path (str): The path to the static mesh asset. The path can either be a path to a primative shape ("/Engine/BasicShapes/Cube", "/Engine/BasicShapes/Sphere", "/Engine/BasicShapes/Cone", "/Engine/BasicShapes/Cylinder", "/Engine/BasicShapes/Plane") or the path to a Staitc Mesh Actor.
            name (str | None): Optional name for the actor.
            location (List[float]): The location to spawn the actor at.
            rotation (List[float]): The rotation of the actor. The Rotation is specified as pitch (around Y axis), roll (around X axis), yaw (around Z axis) in degrees.
            scale (List[float]): The scale of the actor.
        Returns:
            Dict[str, Any]: A dictionary containing the success status and actor info.
        """
        asset_path = import_file_if_required(asset_path)

        static_mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not static_mesh:
            raise RuntimeError(f"Failed to load mesh asset for at {asset_path}")

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

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def get_actor_info_by_path_name(
        ctx: Context,
        path_name: str,
    ) -> Dict[str, Any]:
        """Returns detailed info about an actor by its path name."""
        actor = unreal.EditorLevelLibrary.get_actor_reference(path_name)
        if not actor:
            return {"success": False, "error": "Actor not found"}

        return {"success": True, "actor_info": get_actor_info(actor)}
