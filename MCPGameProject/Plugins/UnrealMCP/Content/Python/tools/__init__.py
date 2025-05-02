from .fab_tools import (
    register_fab_tools,
)
from .actor_tools import register_actor_tools
from .viewport_tools import register_viewport_tools
from .material_tools import register_material_tools
from .genai_tools import register_genai_tools

from .editor_tools import register_editor_tools

# from .fab_tools import register_fab_tools
# from .placement_tools import register_placement_tools


def register_all_tools(mcp_server):
    """Register all tools with the MCP server."""
    register_actor_tools(mcp_server)
    register_viewport_tools(mcp_server)
    register_material_tools(mcp_server)
    register_genai_tools(mcp_server)
    register_editor_tools(mcp_server)
    register_fab_tools(mcp_server)
    # register_placement_tools(mcp_server)
