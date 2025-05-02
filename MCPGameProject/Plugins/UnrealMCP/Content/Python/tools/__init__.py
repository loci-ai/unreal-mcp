from .actor_tools import register_actor_tools
from .blueprint_tools import register_blueprint_tools
from .editor_tools import register_editor_tools
from .fab_tools import register_fab_tools
from .genai_tools import register_genai_tools
from .node_tools import register_blueprint_node_tools
from .placement_tools import register_placement_tools
from .pcg_tools import register_pcg_tools


def register_all_tools(mcp_server):
    """Register all tools with the MCP server."""
    register_actor_tools(mcp_server)
    register_editor_tools(mcp_server)
    register_blueprint_tools(mcp_server)
    register_blueprint_node_tools(mcp_server)
    register_fab_tools(mcp_server)
    register_placement_tools(mcp_server)
    register_genai_tools(mcp_server)
    register_pcg_tools(mcp_server)