"""
Actor Tools for Unreal MCP.

This module provides tools for creating, manipulating, and inspecting actors in Unreal Engine.
"""

import unreal

from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP, Context

from runner import GameThreadRunner
from .utils.terrain_generation import create_heightmap


def register_actor_tools(mcp: FastMCP):
    """Register actor tools with the MCP server."""

    @mcp.tool()
    def get_actors_in_level(ctx: Context) -> List[Dict[str, Any]]:
        response = GameThreadRunner.run_cpp_command("get_actors_in_level", {})
        return response or {}

    @mcp.tool()
    def find_actors_by_name(ctx: Context, pattern: str) -> List[str]:
        response = GameThreadRunner.run_cpp_command(
            "find_actors_by_name", {"pattern": pattern}
        )
        return response or {}

    @mcp.tool()
    def create_actor(
        ctx: Context,
        name: str,
        type: str,
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0],
        scale: List[float] = [1.0, 1.0, 1.0],
    ) -> Dict[str, Any]:
        """Create a new actor in the current level.

        Args:
            ctx: The MCP context
            name: The name to give the new actor (must be unique)
            type: The type of actor to create (e.g. StaticMeshActor, PointLight)
            location: The [x, y, z] world location to spawn at
            rotation: The [pitch, yaw, roll] rotation in degrees
            scale: The [x, y, z] scale to apply. The

        Returns:
            Dict containing the created actor's properties
        """
        params = {
            "name": name,
            "type": type.upper(),  # Make sure type is uppercase
            "location": location,
            "rotation": rotation,
            "scale": scale,
        }

        # Validate location, rotation, and scale formats
        for param_name in ["location", "rotation", "scale"]:
            param_value = params[param_name]
            if not isinstance(param_value, list) or len(param_value) != 3:
                unreal.log_warning(
                    f"Invalid {param_name} format: {param_value}. Must be a list of 3 float values."
                )
                raise ValueError(
                    f"Invalid {param_name} format. Must be a list of 3 float values."
                )
            # Ensure all values are float
            params[param_name] = [float(val) for val in param_value]

        unreal.log(f"Creating actor '{name}' of type '{type}' with params: {params}")
        response = GameThreadRunner.run_cpp_command("create_actor", params)
        return response or {}

    @mcp.tool()
    def delete_actor(ctx: Context, name: str) -> Dict[str, Any]:
        """Delete an actor by name."""
        response = GameThreadRunner.run_cpp_command("delete_actor", {"name": name})
        return response or {}

    @mcp.tool()
    def set_actor_transform(
        ctx: Context,
        name: str,
        location: List[float] = None,
        rotation: List[float] = None,
        scale: List[float] = None,
    ) -> Dict[str, Any]:
        """Set the transform of an actor."""
        params = {"name": name}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale

        response = GameThreadRunner.run_cpp_command("set_actor_transform", params)
        return response or {}

    @mcp.tool()
    def get_actor_properties(ctx: Context, name: str) -> Dict[str, Any]:
        """Get all properties of an actor."""
        response = GameThreadRunner.run_cpp_command(
            "get_actor_properties", {"name": name}
        )
        return response or {}

    @mcp.tool()
    def create_terrain(
        ctx: Context,
        name: str,
        base_scale: float = 250.0,
        base_octaves: int = 3,
        base_persistence: float = 0.4,
        base_lacunarity: float = 2.0,
        plateau_scale: float = 120.0,
        plateau_octaves: int = 4,
        plateau_threshold: float = 0.6,
        plateau_height: float = 0.8,
        plateau_softness: float = 0.15,
        plateau_flatness: float = 3.0,
        plateau_top_variation: float = 0.05,
        terracing_steps: int = 0,
        erosion_scale: float = 60.0,
        erosion_strength: float = 0.05,
        enable_mesa: bool = False,
        seed: int = 42,
    ):
        """Create a new terrain actor in the current level.
        Note: Does not delete existing terrain actors.
        Args:
            ctx: The MCP context
            name: The name to give the new terrain actor (must be unique)
            base_scale: Scale for the base terrain noise (higher = lower frequency)
            base_octaves: Number of octaves for the base terrain noise
            base_persistence: Persistence for the base terrain noise
            base_lacunarity: Lacunarity for the base terrain noise
            plateau_scale: Scale for the plateau noise (higher = lower frequency)
            plateau_octaves: Number of octaves for the plateau noise
            plateau_threshold: Threshold for plateau generation
            plateau_height: Height of the plateaus
            plateau_softness: Softness of the plateau edges
            plateau_flatness: Flatness of the plateau tops
            plateau_top_variation: Variation on the plateau tops
            erosion_strength: Strength of the erosion effect
            erosion_scale: Scale for the erosion noise (higher = lower frequency)
            enable_mesa: True - big abrupt plateaus, False - plateaus blend into terrain
            terracing_steps: Number of steps for terracing (0 disables terracing)
            seed: Seed for the perlin noise generation

        Returns:
            Dict containing the created actor's properties
        """

        unreal.log("In create_terrain")
        heightmap_path = create_heightmap(
            width=1009,
            height=1009,
            base_scale=base_scale,
            base_octaves=base_octaves,
            base_persistence=base_persistence,
            base_lacunarity=base_lacunarity,
            plateau_scale=plateau_scale,
            plateau_octaves=plateau_octaves,
            plateau_threshold=plateau_threshold,
            plateau_height=plateau_height,
            plateau_softness=plateau_softness,
            plateau_flatness=plateau_flatness,
            plateau_top_variation=plateau_top_variation,
            terracing_steps=terracing_steps,
            erosion_scale=erosion_scale,
            erosion_strength=erosion_strength,
            enable_mesa=enable_mesa,
            seed=seed,
        )

        params = {"heightmap_path": heightmap_path, "name": name}
        response = GameThreadRunner.run_cpp_command("create_terrain", params)
        return response or {}
