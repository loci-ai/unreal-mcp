import unreal
from mcp.server.fastmcp import FastMCP, Context

from runner import GameThreadRunner


def register_viewport_tools(mcp: FastMCP):
    """Register actor tools with the MCP server."""

    @mcp.tool()
    @GameThreadRunner.run_on_main_thread
    def focus_viewport_on_actor(path_name: str):
        """Focus the viewport on the specified actor.
        Args:
            path_name: The path name of the actor to focus on.
        """

        # Select the actor
        actor = unreal.EditorLevelLibrary.get_actor_reference(path_name)

        unreal.EditorLevelLibrary.set_selected_level_actors([actor])
        # Focus viewport on selection
        unreal.SystemLibrary.execute_console_command(
            unreal.EditorLevelLibrary.get_editor_world(), "CAMERA ALIGN"
        )

        return {
            "status": "success",
            "message": f"Focused viewport on actor: {path_name}",
        }
