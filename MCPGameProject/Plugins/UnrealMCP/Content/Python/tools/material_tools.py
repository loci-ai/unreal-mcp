import unreal
from mcp.server.fastmcp import FastMCP, Context
import os
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
        material = unreal.load_asset(material_path)
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

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def create_material_from_texture_image(
        ctx: Context,
        texture_image_path: str,
        material_name: str,
        material_path: str = "/Game/Materials/",
    ) -> dict[str, Any]:
        """
        Creates a new material from a texture image.

        Args:
            ctx (Context): The MCP context.
            texture_image_path (str): The Unreal asset path to the texture image (e.g. '/Game/Textures/MyImage').
            material_name (str): The name of the new material.
            material_path (str, optional): The path where the material will be saved. Defaults to "/Game/Materials/".

        Returns:
            dict[str, Any]: A dictionary containing the success status and info about the created material.
        """
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        # Create the full material asset path
        material_asset_path = os.path.join(material_path, material_name)

        # Load the texture asset
        texture = unreal.EditorAssetLibrary.load_asset(texture_image_path)
        if not texture or not isinstance(texture, unreal.Texture2D):
            return {
                "success": False,
                "error": f"Texture not found or invalid: {texture_image_path}",
            }

        # Create a new material asset
        material_factory = unreal.MaterialFactoryNew()
        material = asset_tools.create_asset(
            material_name, material_path, unreal.Material, material_factory
        )

        # Create a texture sample expression
        texture_sample = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionTextureSample, -384, 0
        )
        texture_sample.set_editor_property("texture", texture)

        # Check texture compression format to determine alpha channel availability
        has_alpha = False
        compression_settings = texture.get_editor_property("compression_settings")

        if compression_settings in [
            # unreal.TextureCompressionSettings.TC_DXT5,
            unreal.TextureCompressionSettings.TC_BC7,
            # unreal.TextureCompressionSettings.TC_DEFAULT_ALLOW_ALPHA_COVERAGE,
        ]:
            has_alpha = True

        # Connect the texture to material properties
        unreal.MaterialEditingLibrary.connect_material_property(
            texture_sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
        )

        # If texture has alpha, connect it to opacity
        if has_alpha:
            unreal.MaterialEditingLibrary.connect_material_property(
                texture_sample, "A", unreal.MaterialProperty.MP_OPACITY
            )

        # Set material properties
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
        material.set_editor_property(
            "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT
        )

        # For translucent materials, set appropriate properties
        # if blend_mode == unreal.BlendMode.BLEND_TRANSLUCENT:
        #     material.set_editor_property(
        #         "translucency_lighting_mode",
        #         unreal.TranslucencyLightingMode.TLM_SURFACE_PERVERTEX_DIRECTIONAL,
        #     )

        # Compile the material
        unreal.MaterialEditingLibrary.recompile_material(material)

        # Save the material
        unreal.EditorAssetLibrary.save_asset(material_asset_path)

        unreal.log(f"Created material: {material_asset_path}")

        return {
            "success": True,
            "message": f"Material '{material_name}' created and linked with texture '{texture_image_path}'.",
            "material_path": f"{material_asset_path}",
        }
