import unreal

from typing import Dict, Any
from mcp.server.fastmcp import FastMCP, Context

from runner import GameThreadRunner
from .utils.responses import Responses


def register_pcg_tools(mcp: FastMCP):
    """Register PCG tools with the MCP server."""

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def scatter_mesh(
        ctx: Context,
        asset_path: str,
        actor_name: str,
        actor_location: list[float] = [504.0, 504.0],
        actor_box_extents: list[float] = [504.0, 504.0],
        points_per_sq_meter: float = 10.0,
        min_scale: float = 0.8,
        max_scale: float = 1.2,
        min_rotation: float = 0.0,
        max_rotation: float = 360.0,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """Scatter meshes in the landscape using the PCG system.
           Note: This will not delete any existing PCG actors.
           Use delete_actor to remove any existing PCG actors if needed.
           If you want to modify an existing PCG actor, use the same name
           as the actor.
           Landscape location is 0,0,0 and size is 1009x1009. (about 10x10 sqmt)

        Args:
            ctx: The MCP context
            asset_path: The folder path to the imported asset to use
            asset_path: This is either a path to a mesh or to a folder
                that can contain one or more meshes. If folder then all
                meshes in the folder will be used for scattering. Each
                scatter point will randomly select one of the meshes in the folder.
            actor_location: [x, y] location of the PCG collision box in the world.
                By default it is at (504, 504) which means the center of the box
                is at the center of the landscape. z will always be 0.
            actor_box_extents: [x, y] box extents of the PCG collision box in the world.
                By default it is (504, 504) which means the box is 1008x1008
                and covers the entire landscape. z will always be 504.
            points_per_sq_meter: The point density for the PCG surface sampler.
                Recommended between 1.0 (very sparse) to 100.0 (very dense)
                (default: 10.0).
            min_scale: Min scale for the mesh (default: 0.8)
            max_scale: Max scale for the mesh (default: 1.2)
                Each point is scaled randomly between min_scale and max_scale
                Meshes are scaled to a 10cmx10cm box first and then scaled by the
                given scales, so for a tree ~1.0 is good, rock might be 0.5 etc.
            min_rotation: Min z rotation for the mesh (default: 0.0)
            max_rotation: Max z rotation for the mesh (default: 360.0)
                Each point is rotated randomly between min_rotation and max_rotation
            seed: The random seed to use for scattering
        Returns:
            The PCG actor's properties
        """

        mesh_assets: list[unreal.StaticMesh] = []
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

        dims = []
        for mesh in mesh_assets:
            box = mesh.get_bounding_box()
            size = box.max - box.min
            unreal.log(f"Mesh Size: {size.x}, {size.y}, {size.z}")
            dims.append(max(size.x, size.y, size.z))
        scale = sum(dims) / len(dims)

        blueprint_class = unreal.load_class(
            None, "/UnrealMCP/Widgets/BP_PCGScatter.BP_PCGScatter_C"
        )
        if not blueprint_class:
            return {
                "success": False,
                "error": "Blueprint class BP_PCGScatter not found.",
            }

        all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
        actor = next((a for a in all_actors if a.get_actor_label() == actor_name), None)

        location = unreal.Vector(actor_location[0], actor_location[1], 0)
        if not actor:
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                blueprint_class, location
            )
            actor.set_actor_label(actor_name)
        else:
            actor.set_actor_location(location, False, False)
        box_component = actor.get_component_by_class(unreal.BoxComponent)
        assert box_component is not None, "BoxComponent not found in actor."
        box_component.set_box_extent(
            unreal.Vector(actor_box_extents[0], actor_box_extents[1], 504)
        )

        # --- Set exposed PCG variables ---
        actor.set_editor_property("PointDensity", points_per_sq_meter)
        min_scale = min_scale / scale * 10.0
        actor.set_editor_property(
            "MinScale", unreal.Vector(min_scale, min_scale, min_scale)
        )
        max_scale = max_scale / scale * 10.0
        actor.set_editor_property(
            "MaxScale", unreal.Vector(max_scale, max_scale, max_scale)
        )
        actor.set_editor_property("MinRotation", unreal.Rotator(0.0, 0.0, min_rotation))
        actor.set_editor_property("MaxRotation", unreal.Rotator(0.0, 0.0, max_rotation))
        actor.set_editor_property("Seed", seed)
        actor.set_editor_property("Meshes", mesh_assets)

        pcg_component = actor.get_component_by_class(unreal.PCGComponent)
        assert pcg_component is not None, "PCGComponent not found in actor."
        pcg_component.generate(force=True)

        return Responses.actor_to_json(actor)
