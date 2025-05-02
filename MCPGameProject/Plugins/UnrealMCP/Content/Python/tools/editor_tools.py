"""
Editor Tools for Unreal MCP.

This module provides tools for controlling the Unreal Editor viewport and other editor functionality.
"""

import unreal

import os
from os.path import join
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

from .utils.responses import Responses
from runner import GameThreadRunner


def import_file_if_required(
    file_path: str,
    asset_category: Optional[str] = None,
    destination_root: str = "/Game/ImportedAssets/",
) -> str:
    """
    Imports a GLB, or image file (PNG, JPG, etc.) into Unreal Engine.
    Args:
        file_path (str): The source file path on disk.
        asset_category (Optional[str]): Optional subfolder under the destination path.
        destination_root (str): Base destination path in the Content Browser.
    Returns:
        A dict with the imported Unreal asset path or an error.
    """
    if file_path.startswith("/Game"):
        return file_path

    if not os.path.isfile(file_path):
        raise ValueError(f"File does not exist: {file_path}")

    if asset_category is not None:
        destination_root = join(destination_root, asset_category)

    # Ensure the extension is correct
    extension = os.path.splitext(file_path)[1].lower()

    is_glb = extension in [".glb"]
    is_image = extension in [".png", ".jpg"]
    asset_name = os.path.splitext(os.path.basename(file_path))[0]

    # Ensure destination path ends with a slash
    if not destination_root.endswith("/"):
        destination_root = destination_root + "/"
    if is_glb:

        # Get asset name from file path

        import_task = unreal.AssetImportTask()
        import_task.filename = file_path
        import_task.destination_path = destination_root
        import_task.destination_name = asset_name
        import_task.replace_existing = True
        import_task.automated = True
        import_task.save = True

        # Import the asset using the asset tools
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        asset_tools.import_asset_tasks([import_task])

        # Get the imported object paths
        imported_paths = import_task.get_editor_property("imported_object_paths")

        # Check if import was successful
        if not imported_paths:
            unreal.log_error(f"Failed to import GLB file: {file_path}")
            return None

        # Find the static mesh in the imported objects
        static_mesh_path = None
        editor_asset_subsystem = unreal.get_editor_subsystem(
            unreal.EditorAssetSubsystem
        )

        for path in imported_paths:
            asset = editor_asset_subsystem.load_asset(path)
            if isinstance(asset, unreal.StaticMesh):
                static_mesh_path = path
                break

        if not static_mesh_path:
            unreal.log_warning(
                f"No static mesh was found in the imported assets. Paths: {imported_paths}"
            )
            # Return the first path if no specific static mesh was found
            return imported_paths[0] if imported_paths else None

        return static_mesh_path
    elif is_image:
        # Use AssetImportTask for images
        task = unreal.AssetImportTask()
        task.filename = file_path
        task.destination_path = join(destination_root, asset_name)
        task.destination_name = asset_name
        task.automated = True
        task.save = True
        task.replace_existing = True

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        # Get the imported object paths
        imported_paths = task.get_editor_property("imported_object_paths")
        if not imported_paths:
            raise Exception("Failed to import image file.")

        # Return the actual imported path
        return imported_paths[0]

    else:
        raise Exception(f"Unsupported file type: {extension}")


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
    def view_asset(ctx: Context, asset_path: str):
        """
        View an asset (e.g. static mesh, image, material etc) in the editor.
        Args:
            ctx: The MCP context
            asset_path: The file path to the asset.
        """
        asset_path = import_file_if_required(asset_path)
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is None:
            unreal.log_error(f"Failed to load asset at path: {asset_path}")
            return {"sucess": False, "error": "Asset not found"}

        editor_subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        if editor_subsystem:
            editor_subsystem.open_editor_for_assets([asset])
            unreal.log("Image viewed successfully.")
            return {"sucess": True}

        unreal.log_error("Could not get AssetEditorSubsystem")
        return {"sucess": False, "error": "Editor subsystem unavailable"}
