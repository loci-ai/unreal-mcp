"""
Placement Tools for Unreal MCP.

This module provides tools for placing different actors in Unreal Engine.
"""

import logging
import random
from typing import List, Optional
from mcp.server.fastmcp import FastMCP, Context

from .utils.asset_placement import generate_tree_locations, generate_rock_locations

# Get logger
logger = logging.getLogger("UnrealMCP")


def register_placement_tools(mcp: FastMCP):
    """Register placement tools with the MCP server."""

    @mcp.tool()
    def place_actor(
        ctx: Context,
        asset_path: str,
        name: str,
        location: List[float],
        rotation: Optional[float] = None,
        scale: Optional[float] = None,
    ):
        """Place an actor in the level. The mesh used will first be scaled
         down to unit cube, and then scaled up to the specified scale.
        The landscape size is assumed to be 1009x1009 with . An appropriate scale
        for a tree could be around 0.5, while a rock could be around 0.3.
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
        from unreal_mcp_server import get_unreal_connection, UNREAL_PYTHON_PORT

        try:
            unreal = get_unreal_connection(port=UNREAL_PYTHON_PORT)
            params = {
                "asset_path": asset_path,
                "name": name,
                "location": location,
            }
            if rotation is not None:
                params["rotation"] = rotation
            if scale is not None:
                params["scale"] = scale
            response = unreal.send_command(
                "place_actor", params, port=UNREAL_PYTHON_PORT
            )
            return response or {}

        except Exception as e:
            logger.error(f"Error placing actor: {e}")
            return {}

    @mcp.tool()
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
        could be around 0.3. Uses line trace to adjust the Z coordinate of the
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

        from unreal_mcp_server import get_unreal_connection, UNREAL_PYTHON_PORT

        try:
            unreal = get_unreal_connection(port=UNREAL_PYTHON_PORT)
            params = {
                "asset_path": asset_path,
                "prefix_name": prefix_name,
                "locations": locations,
            }
            if rotations is not None:
                params["rotations"] = rotations
            if scales is not None:
                params["scales"] = scales
            response = unreal.send_command(
                "place_multiple_actors", params, port=UNREAL_PYTHON_PORT
            )
            return response or {}

        except Exception as e:
            logger.error(f"Error placing multiple actors: {e}")
            return {}

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

        from unreal_mcp_server import get_unreal_connection, UNREAL_PYTHON_PORT

        try:
            unreal = get_unreal_connection(port=UNREAL_PYTHON_PORT)
            locations = generate_tree_locations(num_assets)
            rotations = [random.uniform(0, 360) for _ in range(len(locations))]
            scales = [random.uniform(0.4, 0.6) for _ in range(len(locations))]
            params = {
                "asset_path": asset_path,
                "prefix_name": prefix_name,
                "locations": locations,
                "rotations": rotations,
                "scales": scales,
            }
            response = unreal.send_command(
                "place_multiple_actors", params, port=UNREAL_PYTHON_PORT
            )
            return response or {}

        except Exception as e:
            logger.error(f"Error placing tree actors: {e}")
            return {}

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

        from unreal_mcp_server import get_unreal_connection, UNREAL_PYTHON_PORT

        try:
            unreal = get_unreal_connection(port=UNREAL_PYTHON_PORT)
            locations = generate_rock_locations(num_assets)
            rotations = [random.uniform(0.0, 360.0) for _ in range(len(locations))]
            scales = [random.uniform(0.25, 0.4) for _ in range(len(locations))]

            params = {
                "asset_path": asset_path,
                "prefix_name": prefix_name,
                "locations": locations,
                "rotations": rotations,
                "scales": scales,
            }
            response = unreal.send_command(
                "place_multiple_actors", params, port=UNREAL_PYTHON_PORT
            )
            return response or {}

        except Exception as e:
            logger.error(f"Error placing rock actors: {e}")
            return {}
