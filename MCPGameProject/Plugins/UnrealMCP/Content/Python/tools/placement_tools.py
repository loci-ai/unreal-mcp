"""
Placement Tools for Unreal MCP.

This module provides tools for placing different actors in Unreal Engine.
"""

import random
import unreal

from typing import List, Optional
from mcp.server.fastmcp import FastMCP, Context

from runner import GameThreadRunner
from .utils.asset_placement import generate_tree_locations, generate_rock_locations
from .utils.responses import Responses


def register_placement_tools(mcp: FastMCP):
    """Register placement tools with the MCP server."""

    @GameThreadRunner.run_on_main_thread
    def move_actor_pivot_to_bottom(actor):
        origin, extent = actor.get_actor_bounds(False)
        current_loc = actor.get_actor_location()
        unreal.log(
            f"Origin: {(origin.x, origin.y, origin.z)}, Extent: {(extent.x, extent.y, extent.z)}"
        )
        new_loc = unreal.Vector(current_loc.x, current_loc.y, current_loc.z + extent.z)
        actor.set_actor_location(new_loc, False, False)

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def place_actor(
        ctx: Context,
        asset_path: str,
        name: str,
        location: List[float],
        rotation: Optional[float] = 0,
        scale: Optional[float] = 1,
    ):
        """Place an actor in the level. The mesh used will first be scaled
         down to unit cube, and then scaled up to the specified scale.
        The landscape size is assumed to be 1009x1009 with . An appropriate scale
        for a tree could be around 0.5, while a rock could be around 0.2.
        Uses line trace to adjust the Z coordinate of the actor to the landscape.
        Args:
            ctx: The MCP context
            asset_path: The folder path to the imported asset to use
            name: The name to give the new actor (must be unique)
            location: The [x, y, z] world location to spawn at
            rotation [Optional]: The z axis rotation in degrees
            scale [Optional]: The [s] scale to apply (uniformly applied to all axes)

        Returns:
            Dict containing the created actor's properties
        """

        is_folder = unreal.EditorAssetLibrary.does_directory_exist(asset_path)
        mesh_asset = None

        if is_folder:
            assets = unreal.EditorAssetLibrary.list_assets(asset_path, recursive=True)
            for asset in assets:
                loaded = unreal.EditorAssetLibrary.load_asset(asset)
                if isinstance(loaded, (unreal.StaticMesh, unreal.SkeletalMesh)):
                    mesh_asset = loaded
                    asset_path = asset  # update the path for the returned info
                    break
            if not mesh_asset:
                raise ValueError(f"No valid mesh asset found in folder: {asset_path}")
        else:
            # Assume it's a direct path to an asset
            mesh_asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if not isinstance(mesh_asset, (unreal.StaticMesh, unreal.SkeletalMesh)):
                raise TypeError(
                    f"Asset is not a StaticMesh or SkeletalMesh: {asset_path}"
                )

        # Determine the actor class
        if isinstance(mesh_asset, unreal.StaticMesh):
            actor_class = unreal.StaticMeshActor
        elif isinstance(mesh_asset, unreal.SkeletalMesh):
            actor_class = unreal.SkeletalMeshActor
        else:
            raise TypeError("Unsupported mesh type.")

        bounds = mesh_asset.get_bounding_box()
        max_dim = max(
            bounds.max.x - bounds.min.x,
            bounds.max.y - bounds.min.y,
            bounds.max.z - bounds.min.z,
        )
        scale = scale / max_dim * 10.0

        loc_v = unreal.Vector(*location)
        rot_v = unreal.Rotator(0.0, 0.0, rotation)
        scale_v = unreal.Vector(scale, scale, scale)

        hit_result = unreal.SystemLibrary.line_trace_single(
            unreal.EditorLevelLibrary.get_editor_world(),
            start=unreal.Vector(location[0], location[1], 2000),
            end=unreal.Vector(location[0], location[1], -2000),
            trace_channel=unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,  # Visibility
            trace_complex=False,
            actors_to_ignore=[],
            draw_debug_type=unreal.DrawDebugTrace.NONE,
            ignore_self=True,
        )
        if hit_result:
            hit_result = hit_result.to_tuple()
            loc_v = hit_result[4]

        # Spawn actor in the world
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class, loc_v, rot_v
        )
        if not actor:
            raise RuntimeError("Failed to spawn actor.")

        actor.set_actor_label(name)
        actor.set_actor_scale3d(scale_v)

        # Set the mesh on the actor
        if isinstance(actor, unreal.StaticMeshActor):
            actor.static_mesh_component.set_static_mesh(mesh_asset)
        elif isinstance(actor, unreal.SkeletalMeshActor):
            actor.skeletal_mesh_component.set_skeletal_mesh(mesh_asset)

        # Move the pivot to the bottom of the actor
        move_actor_pivot_to_bottom(actor)

        return Responses.actor_to_json(actor)

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def place_multiple_actors(
        ctx: Context,
        asset_path: str,
        prefix_name: str,
        locations: List[List[float]],
        rotations: Optional[List[float]] = None,
        scales: Optional[List[float]] = None,
    ):
        """
        Place multiple actors in the level. Number of actors to place
        is equal to the number of locations and rotations provided.
        Asset path is a folder which can contain multiple assets.
        For each location, a random asset from the folder is selected.
        So the same asset can be used multiple times (like trees in a forest).
        Landscape size is assumed to be 1009x1009. Any mesh used will first
        be scaled down to unit cube, and then scaled up to the specified scale.
        An appropriate scale for a tree could be around 0.5, while a rock
        could be around 0.2. Uses line trace to adjust the Z coordinate of the
        actors to the landscape.
        The final number of actors placed may be less than the number of locations
        provided, if a collision may occur with an existing actor.
        Args:
            asset_path: Folder path to the imported assets to use
            prefix: Prefix to add to the actor names
            locations: List of [x, y, z] world locations to spawn at
            rotations: [Optional] List of z axis rotations in degrees
            scales: [Optional] List of [s] scales to apply (uniformly applied to all axes)
        Returns:
            Success/error response
        """

        mesh_assets = []
        rotations = rotations or [0.0] * len(locations)
        scales = scales or [1.0] * len(locations)

        is_folder = unreal.EditorAssetLibrary.does_directory_exist(asset_path)
        if is_folder:
            assets = unreal.EditorAssetLibrary.list_assets(asset_path, recursive=True)
            for asset in assets:
                loaded = unreal.EditorAssetLibrary.load_asset(asset)
                if isinstance(loaded, (unreal.StaticMesh, unreal.SkeletalMesh)):
                    mesh_assets.append(loaded)
        else:
            # Assume it's a direct path to an asset
            loaded = unreal.EditorAssetLibrary.load_asset(asset_path)
            if isinstance(loaded, (unreal.StaticMesh, unreal.SkeletalMesh)):
                mesh_assets.append(loaded)

        if not mesh_assets:
            raise ValueError("No valid mesh assets found in provided paths.")

        unreal.log(f"{len(locations)}")
        unreal.log(f"{len(rotations)}")
        unreal.log(f"{len(scales)}")

        placed_actors = 0

        for i, (loc, rot, scale) in enumerate(zip(locations, rotations, scales)):
            mesh_asset = random.choice(mesh_assets)
            bounds = mesh_asset.get_bounding_box()
            max_dim = max(
                bounds.max.x - bounds.min.x,
                bounds.max.y - bounds.min.y,
                bounds.max.z - bounds.min.z,
            )
            scale_ = scale / max_dim * 10.0
            loc_v = unreal.Vector(*loc)
            rot_v = unreal.Rotator(0.0, 0.0, rot)
            scale_v = unreal.Vector(scale_, scale_, scale_)

            hit_results = unreal.SystemLibrary.line_trace_multi(
                unreal.EditorLevelLibrary.get_editor_world(),
                start=unreal.Vector(loc[0], loc[1], 2000),
                end=unreal.Vector(loc[0], loc[1], -2000),
                trace_channel=unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,  # Visibility
                trace_complex=False,
                actors_to_ignore=[],
                draw_debug_type=unreal.DrawDebugTrace.NONE,
                ignore_self=True,
            )
            if not hit_results or any(
                [
                    h.to_tuple()[9].get_class().get_name() != "Landscape"
                    for h in hit_results
                ]
            ):
                continue
            else:
                hit_result = hit_results[0].to_tuple()
                loc_v = hit_result[4]

            # Determine the actor class
            if isinstance(mesh_asset, unreal.StaticMesh):
                actor_class = unreal.StaticMeshActor
            elif isinstance(mesh_asset, unreal.SkeletalMesh):
                actor_class = unreal.SkeletalMeshActor
            else:
                raise TypeError("Unsupported mesh type.")

            # Spawn actor in the world
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                actor_class, loc_v, rot_v
            )
            if not actor:
                raise RuntimeError("Failed to spawn actor.")
            actor.set_actor_label(f"{prefix_name}_{i}")

            actor.set_actor_scale3d(scale_v)

            # Set the mesh on the actor
            if isinstance(actor, unreal.StaticMeshActor):
                actor.static_mesh_component.set_static_mesh(mesh_asset)
            elif isinstance(actor, unreal.SkeletalMeshActor):
                actor.skeletal_mesh_component.set_skeletal_mesh(mesh_asset)

            # Move the pivot to the bottom of the actor
            move_actor_pivot_to_bottom(actor)

            placed_actors += 1

        return Responses.create_success_response(
            {"message": f"Placed {placed_actors} actors with prefix: {prefix_name}"}
        )

    @mcp.tool()
    def place_tree_actors(
        ctx: Context,
        asset_path: str,
        prefix_name: str,
        num_assets: int = 500,
    ):
        """
        Place tree actors in the level. Asset path is a folder which can
        contain multiple assets. Locations are generated using a poisson
        disk sampling algorithm. Calls place_multiple_actors
        after generating the locations.
        The final number of actors placed may be less than num_assets
        if a collision may occur with an existing actor.
        Args:
            asset_path: Folder path to the imported assets to use
            prefix: Prefix to add to the actor names
            num_assets (int): Number of asset positions to generate.
        Returns:
            Success/error response
        """

        locations = generate_tree_locations(num_assets)
        rotations = [random.uniform(0, 360) for _ in range(len(locations))]
        scales = [random.uniform(0.4, 0.6) for _ in range(len(locations))]
        return place_multiple_actors(
            ctx,
            asset_path=asset_path,
            prefix_name=prefix_name,
            locations=locations,
            rotations=rotations,
            scales=scales,
        )

    @mcp.tool()
    def place_rock_actors(
        ctx: Context,
        asset_path: str,
        prefix_name: str,
        num_assets: int = 300,
    ):
        """
        Place rock actors in the level. Asset path is a folder which can
        contain multiple assets. Locations are generated using a poisson
        disk sampling algorithm. Calls place_multiple_actors after
        generating the locations.
        The final number of actors placed may be less than num_assets
        if a collision may occur with an existing actor.
        Args:
            asset_path: Folder path to the imported assets to use
            prefix: Prefix to add to the actor names
            num_assets (int): Number of asset positions to generate.
        Returns:
            Success/error response
        """

        locations = generate_rock_locations(num_assets)
        rotations = [random.uniform(0.0, 360.0) for _ in range(len(locations))]
        scales = [random.uniform(0.15, 0.25) for _ in range(len(locations))]
        return place_multiple_actors(
            ctx,
            asset_path=asset_path,
            prefix_name=prefix_name,
            locations=locations,
            rotations=rotations,
            scales=scales,
        )
