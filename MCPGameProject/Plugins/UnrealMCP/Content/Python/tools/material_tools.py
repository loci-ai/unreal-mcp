import unreal
from mcp.server.fastmcp import FastMCP, Context

from runner import GameThreadRunner
from typing import Any


def register_material_tools(mcp: FastMCP):
    """Register actor tools with the MCP server."""

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def get_all_assets_in_content_browser() -> dict[str, Any]:
        """
        Retrieves all assets (e.g meshes, materials etc) in the content browser.

        Returns:
            dict[str, Any]: A dictionary containing the success status and info about the assets in the content browser.
        """

        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        assets = asset_registry.get_assets_by_path(
            "/Game", recursive=True, include_only_on_disk_assets=False
        )
        if not assets:
            return {
                "success": False,
                "error": "No assets found in the content browser.",
            }
        asset_info = [
            {
                "path": str(asset.package_path) + "/" + str(asset.asset_name),
                "class": str(asset.asset_class_path.asset_name),
            }
            for asset in assets
        ]

        return {"success": True, "assets": asset_info}

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def set_material_on_static_mesh_actor(
        path_name: str, material_path: str, material_slot_index: int = 0
    ):
        """
        Sets a material on a specific material slot of a StaticMeshActor in the current level.

        Args:
            path_name (str): The path_name of the StaticMeshActor to apply the material to.
            material_path (str): The full Unreal asset path to the material (e.g., "/Game/Materials/MyMaterial").
            material_slot_index (int, optional): The index of the material slot to assign the material to. Defaults to 0.

        Returns:
            None
        """
        # Get the actor reference
        actor = unreal.EditorLevelLibrary.get_actor_reference(path_name)
        if not actor:
            return {"success": False, "error": "Actor not found"}

        # Load the material asset
        material = unreal.load_asset("/Game/Developers/jack/Collections/Metal")
        if not material:
            print(f"Material '{material_path}' could not be loaded.")
            return {"success": False, "error": "Material not found"}

        # Get the static mesh component and assign the material
        mesh_component = actor.static_mesh_component
        mesh_component.set_material(material_slot_index, material)

        return {
            "success": True,
            "message": f"Material '{material.get_name()}' applied to '{path_name}' at slot {material_slot_index}.",
        }

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def set_material_on_landscape(
        landscape_name: str, material_path: str
    ) -> dict[str, Any]:
        """
        Sets the material of a Landscape actor in the current level.

        Args:
            landscape_name (str): Name of the Landscape actor.
            material_path (str): Full Unreal asset path to the material.

        Returns:
            dict[str, Any]: Status message.
        """
        # Find the Landscape actor
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        landscape = next(
            (
                a
                for a in actors
                if a.get_name() == landscape_name
                and a.get_class().get_name() == "Landscape"
            ),
            None,
        )

        if not landscape:
            return {
                "success": False,
                "error": f"Landscape '{landscape_name}' not found in the level.",
            }

        # Load material
        material = unreal.EditorAssetLibrary.load_asset(material_path)
        if not material:
            return {"success": False, "error": f"Material '{material_path}' not found."}

        # Apply material
        try:
            landscape.set_editor_property("landscape_material", material)
            return {
                "success": True,
                "message": f"Material '{material.get_name()}' applied to Landscape '{landscape_name}'.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
