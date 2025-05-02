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
    def import_file(
        ctx: Context,
        file_path: str,
        asset_category: Optional[str] = None,
        destination_root: str = "/Game/ImportedAssets/",
    ) -> Dict[str, Any]:
        """
        Imports a GLB, FBX, or image file (PNG, JPG, etc.) into Unreal Engine.
        Args:
            file_path (str): The source file path on disk.
            asset_category (Optional[str]): Optional subfolder under the destination path.
            destination_root (str): Base destination path in the Content Browser.
        Returns:
            A dict with the imported Unreal asset path or an error.
        """

        if not os.path.isfile(file_path):
            raise ValueError(f"File does not exist: {file_path}")

        # Determine file type
        extension = unreal.Paths.get_extension(file_path, False).lower()
        is_gltf = extension in ("glb", "gltf")
        is_fbx = extension == "fbx"
        is_image = extension in ("png", "jpg", "jpeg", "tga", "bmp", "exr", "psd")

        # Build destination path
        asset_name = unreal.Paths.get_base_filename(file_path)
        destination_path = destination_root
        if asset_category:
            destination_path += f"{asset_category}/"
        destination_path += asset_name

        if is_gltf or is_fbx:
            # Enable FBX Interchange if necessary
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

            default_pipeline = (
                "/Interchange/Pipelines/DefaultGLTFAssetsPipeline"
                if is_gltf
                else "/Interchange/Pipelines/DefaultAssetsPipeline"
            )

            pipeline = editor_asset_subsystem.duplicate_asset(
                default_pipeline, transient_pipeline_path
            )

            pipeline.mesh_pipeline.combine_static_meshes = True
            pipeline.material_pipeline.import_materials = True
            pipeline.material_pipeline.texture_pipeline.import_textures = True

            source_data = unreal.InterchangeManager.create_source_data(file_path)

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
            success = interchange_manager.import_asset(
                destination_path, source_data, import_asset_parameters
            )

            editor_asset_subsystem.delete_directory(transient_path)

            if not success:
                return {"success": False, "error": "Failed to import GLB/FBX asset."}

            return {"success": True, "imported_path": destination_path}

        elif is_image:
            # Use AssetImportTask for images
            task = unreal.AssetImportTask()
            task.filename = file_path
            task.destination_path = os.path.dirname(destination_path)
            task.automated = True
            task.save = True
            task.replace_existing = True

            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

            imported_paths = task.get_editor_property("imported_object_paths")
            if not imported_paths:
                return {"success": False, "error": "Failed to import image file."}

            return {"success": True, "imported_path": imported_paths[0]}

        else:
            return {"success": False, "error": f"Unsupported file type: {extension}"}

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def view_image(ctx: Context, image_path: str):
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
