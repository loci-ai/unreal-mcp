"""
Editor Tools for Unreal MCP.

This module provides tools for controlling the Unreal Editor viewport and other editor functionality.
"""

import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

# Get logger
logger = logging.getLogger("UnrealMCP")


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
        from unreal_mcp_server import get_unreal_connection

        try:
            params = {}
            if target:
                params["target"] = target
            elif location:
                params["location"] = location

            if distance:
                params["distance"] = distance

            if orientation:
                params["orientation"] = orientation

            unreal = get_unreal_connection()
            response = unreal.send_command("focus_viewport", params)
            return response or {}

        except Exception as e:
            logger.error(f"Error focusing viewport: {e}")
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    def import_asset(
        ctx: Context, asset_path: str, asset_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import an asset into Unreal Engine.
        Args:
            asset_path (str): The path to the asset to import.
            asset_category (str | None): Asset Category (can be anything eg. "Tree").
            If provided, the asset will be put in a subfolder with this name.
        Returns:
            Path to the imported asset
        """
        from unreal_mcp_server import get_unreal_connection, UNREAL_PYTHON_PORT

        try:
            params = {"asset_path": asset_path}
            if asset_category:
                params["asset_category"] = asset_category

            unreal = get_unreal_connection(port=UNREAL_PYTHON_PORT)
            response = unreal.send_command(
                "import_asset", params, port=UNREAL_PYTHON_PORT
            )
            return response or {}

        except Exception as e:
            logger.error(f"Error importing asset: {e}")
            return {"status": "error", "message": str(e)}

    logger.info("Editor tools registered successfully")
