import unreal
from mcp.server.fastmcp import FastMCP, Context

from runner import GameThreadRunner


def register_material_tools(mcp: FastMCP):
    """Register actor tools with the MCP server."""

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def get_all_material_paths() -> list[str]:
        """
        Retrieves all materials and material instances from the Content Browser.

        Returns:
            List[str]: A list of full asset paths to materials and material instances.
        """
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

        # Search for both Material and MaterialInstance assets
        material_assets = asset_registry.get_assets_by_class("Material", True)
        material_instance_assets = asset_registry.get_assets_by_class(
            "MaterialInstanceConstant", True
        )

        all_assets = material_assets + material_instance_assets

        # Extract full paths (e.g., "/Game/StarterContent/Materials/M_Metal_Gold")
        material_paths = [asset.object_path.string() for asset in all_assets]
        return material_paths

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
        actor = unreal.EditorLevelLibrary.get_actor_reference(path_name)
        if not actor:
            return {"success": False, "error": "Actor not found"}

        # Load the material asset
        material = unreal.load_asset(material_path)
        if not material:
            print(f"Material '{material_path}' could not be loaded.")
            return

        # Get the static mesh component and assign the material
        mesh_component = actor.static_mesh_component
        mesh_component.set_material(material_slot_index, material)

        print(
            f"Material '{material.get_name()}' applied to '{path_name}' at slot {material_slot_index}."
        )
