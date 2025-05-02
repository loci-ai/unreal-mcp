"""
Editor Tools for Unreal MCP.

This module provides tools for controlling the Unreal Editor viewport and other editor functionality.
"""

import unreal

import os
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

from .utils.responses import Responses
from runner import GameThreadRunner


def register_editor_tools(mcp: FastMCP):
    """Register editor tools with the MCP server."""

    @mcp.tool()
    def focus_viewport(
        ctx: Context,
        target: str = None,
        location: List[float] = None,
        distance: float = 1000.0,
        orientation: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Focus the viewport on a specific actor or location.

        Args:
            target: Name of the actor to focus on (if provided, location is ignored)
            location: [X, Y, Z] coordinates to focus on (used if target is None)
            distance: Distance from the target/location
            orientation: Optional [Pitch, Yaw, Roll] for the viewport camera

        Returns:
            Response from Unreal Engine
        """
        params = {}
        if target:
            params["target"] = target
        elif location:
            params["location"] = location

        if distance:
            params["distance"] = distance

        if orientation:
            params["orientation"] = orientation

        response = GameThreadRunner.run_cpp_command("focus_viewport", params)
        return response or {}

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def import_asset(
        ctx: Context, asset_path: str, asset_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import a GLB of FBX asset into Unreal Engine.
        Args:
            asset_path (str): The path to the asset to import.
            asset_category (str | None): Asset Category (can be anything eg. "Tree").
            If provided, the asset will be put in a subfolder with this name.
        Returns:
            Path to the imported asset
        """
        import_extension = unreal.Paths.get_extension(asset_path, False)

        is_gltf = import_extension == "glb" or import_extension == "gltf"

        is_fbx = import_extension == "fbx"

        if is_fbx:
            level_editor_subsystem = unreal.get_editor_subsystem(
                unreal.LevelEditorSubsystem
            )
            unreal.SystemLibrary.execute_console_command(
                level_editor_subsystem.get_world(),
                "Interchange.FeatureFlags.Import.FBX true",
            )

        editor_asset_subsystem = unreal.get_editor_subsystem(
            unreal.EditorAssetSubsystem
        )

        transient_path = "/Interchange/Pipelines/Transient/"
        transient_pipeline_path = transient_path + "MyAutomationPipeline"

        editor_asset_subsystem.delete_directory(transient_path)

        if is_gltf:
            pipeline = editor_asset_subsystem.duplicate_asset(
                "/Interchange/Pipelines/DefaultGLTFAssetsPipeline",
                transient_pipeline_path,
            )
        else:
            pipeline = editor_asset_subsystem.duplicate_asset(
                "/Interchange/Pipelines/DefaultAssetsPipeline",
                transient_pipeline_path,
            )

        # combine static mesh
        pipeline.mesh_pipeline.combine_static_meshes = True
        pipeline.material_pipeline.import_materials = True
        pipeline.material_pipeline.texture_pipeline.import_textures = True

        source_data = unreal.InterchangeManager.create_source_data(asset_path)
        import_asset_parameters = unreal.ImportAssetParameters()
        import_asset_parameters.is_automated = True

        import_asset_parameters.override_pipelines.append(
            unreal.SoftObjectPath(transient_pipeline_path + ".MyAutomationPipeline")
        )
        if is_gltf:
            import_asset_parameters.override_pipelines.append(
                unreal.SoftObjectPath("/Interchange/Pipelines/DefaultGLTFPipeline")
            )

        interchange_manager = (
            unreal.InterchangeManager.get_interchange_manager_scripted()
        )
        destination_path = "/Game/ImportedGLB/"
        if asset_category:
            destination_path += f"{asset_category}/"
        destination_path += unreal.Paths.get_base_filename(asset_path)
        success = interchange_manager.import_asset(
            destination_path, source_data, import_asset_parameters
        )
        if not success:
            raise Exception("Failed to import asset.")

        editor_asset_subsystem.delete_directory(transient_path)
        return Responses.create_success_response({"import_dest_path": destination_path})

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def view_image(ctx: Context, image_path: str):
        if not image_path.startswith(
            ("Game", "/Game")
        ):  # image has not been imported into UE yet
            unreal.log(f"Importing image into UE")
            response = import_asset(ctx=ctx, asset_path=image_path)
            import_dest_path = response["import_dest_path"]
            unreal.log(f"import_dest_path: {import_dest_path}")
            filename = os.path.basename(import_dest_path).split(".")[0]
            image_path = f"{import_dest_path}/{filename}.{filename}"

        asset = unreal.EditorAssetLibrary.load_asset(image_path)
        if asset is None:
            unreal.log_error(f"Failed to load asset at path: {image_path}")
            return {"sucess": False, "error": "Asset not found"}

        editor_subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        if editor_subsystem:
            editor_subsystem.open_editor_for_assets([asset])
            unreal.log("Image viewed successfully.")
            return {"sucess": True}

        unreal.log_error("Could not get AssetEditorSubsystem")
        return {"sucess": False, "error": "Editor subsystem unavailable"}
