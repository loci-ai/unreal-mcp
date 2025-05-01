# @mcp.tool()
# def create_terrain(
#     ctx: Context,
#     name: str,
#     base_scale: float = 250.0,
#     base_octaves: int = 3,
#     base_persistence: float = 0.4,
#     base_lacunarity: float = 2.0,
#     plateau_scale: float = 120.0,
#     plateau_octaves: int = 4,
#     plateau_threshold: float = 0.6,
#     plateau_height: float = 0.8,
#     plateau_softness: float = 0.15,
#     plateau_flatness: float = 3.0,
#     plateau_top_variation: float = 0.05,
#     terracing_steps: int = 0,
#     erosion_scale: float = 60.0,
#     erosion_strength: float = 0.05,
#     enable_mesa: bool = False,
#     seed: int = 42,
# ):
#     """Create a new terrain actor in the current level.
#     Note: Does not delete existing terrain actors.
#     Args:
#         ctx: The MCP context
#         name: The name to give the new terrain actor (must be unique)
#         base_scale: Scale for the base terrain noise (higher = lower frequency)
#         base_octaves: Number of octaves for the base terrain noise
#         base_persistence: Persistence for the base terrain noise
#         base_lacunarity: Lacunarity for the base terrain noise
#         plateau_scale: Scale for the plateau noise (higher = lower frequency)
#         plateau_octaves: Number of octaves for the plateau noise
#         plateau_threshold: Threshold for plateau generation
#         plateau_height: Height of the plateaus
#         plateau_softness: Softness of the plateau edges
#         plateau_flatness: Flatness of the plateau tops
#         plateau_top_variation: Variation on the plateau tops
#         erosion_strength: Strength of the erosion effect
#         erosion_scale: Scale for the erosion noise (higher = lower frequency)
#         enable_mesa: True - big abrupt plateaus, False - plateaus blend into terrain
#         terracing_steps: Number of steps for terracing (0 disables terracing)
#         seed: Seed for the perlin noise generation

#     Returns:
#         Dict containing the created actor's properties
#     """

#     unreal.log("In create_terrain")
#     heightmap_path = create_heightmap(
#         width=1009,
#         height=1009,
#         base_scale=base_scale,
#         base_octaves=base_octaves,
#         base_persistence=base_persistence,
#         base_lacunarity=base_lacunarity,
#         plateau_scale=plateau_scale,
#         plateau_octaves=plateau_octaves,
#         plateau_threshold=plateau_threshold,
#         plateau_height=plateau_height,
#         plateau_softness=plateau_softness,
#         plateau_flatness=plateau_flatness,
#         plateau_top_variation=plateau_top_variation,
#         terracing_steps=terracing_steps,
#         erosion_scale=erosion_scale,
#         erosion_strength=erosion_strength,
#         enable_mesa=enable_mesa,
#         seed=seed,
#     )

#     params = {"heightmap_path": heightmap_path, "name": name}
#     response = GameThreadRunner.run_cpp_command("create_terrain", params)
#     return response or {}
