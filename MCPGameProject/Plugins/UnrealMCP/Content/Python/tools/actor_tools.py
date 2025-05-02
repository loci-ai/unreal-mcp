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
        erosion_scale: float = 60.0,
        erosion_strength: float = 0.05,
        mountain_height_multiplier: float = 1.0,  # New parameter
        seed: int = 42,
    ):
        """Create a new terrain actor in the current level.
        Note: Does not delete existing terrain actors.

        Generates a 2D procedural terrain heightmap using Perlin and Simplex noise.

        This function produces terrain suitable for various biome types, such as mountains,
        hills, or desert basins, depending on the input parameters. The terrain is composed
        of a base layer of smooth or rugged elevation and optional micro-detail added via
        erosion noise.

        --------
        Example usage:
        - Mountainous terrain:
            create_terrain(base_scale=100.0, base_octaves=5, mountain_height_multiplier=2.0)

        - Rolling desert hills:
            create_terrain(base_scale=400.0, base_octaves=2, erosion_strength=0.02)

        Parameters
        ----------
        name : str
            Name of the terrain actor to create.
        base_scale : float
            Controls the size of the base terrain features. Lower values zoom in (larger, sharper features),
            higher values zoom out (smoother terrain).
        base_octaves : int
            Number of noise layers (octaves) used to build the base terrain.
            More octaves add finer detail.
        base_persistence : float
            Controls how much each successive octave contributes to the overall shape.
            Lower values (e.g., 0.3–0.4) create smoother terrain; higher values make it rougher.
        base_lacunarity : float
            Controls how quickly frequency increases per octave. Values >2 make terrain more jagged
        erosion_scale : float
            Scale of the additional erosion noise that breaks up uniformity.
        erosion_strength : float
            How strongly erosion noise influences the final terrain.
            Small values (0.01–0.05) give subtle variation.
        mountain_height_multiplier : float
            Multiplies the base elevation to exaggerate peaks and valleys.
            - Set to 1.0 for default elevation.
            - Set to 2.0 or more for tall mountains.
            - Use <1.0 for flatter terrain like deserts.
        seed : int
            Random seed for the noise used in terrain generation.

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
            erosion_scale=erosion_scale,
            erosion_strength=erosion_strength,
            mountain_height_multiplier=mountain_height_multiplier,
            seed=seed,
        )

        params = {"heightmap_path": heightmap_path, "name": name}

        @GameThreadRunner.run_on_main_thread
        def delete_existing_terrain():
            actors = unreal.EditorLevelLibrary.get_all_level_actors()

            for actor in actors:
                if isinstance(
                    actor, (unreal.Landscape, unreal.LandscapeStreamingProxy)
                ):
                    unreal.EditorLevelLibrary.destroy_actor(actor)

        delete_existing_terrain()

        response = GameThreadRunner.run_cpp_command("create_terrain", params)
        return response or {}
