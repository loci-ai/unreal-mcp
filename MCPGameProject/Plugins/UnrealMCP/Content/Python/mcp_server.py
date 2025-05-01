"""
Unreal Engine MCP Server

A simple MCP server for interacting with Unreal Engine.
"""

import json
import unreal

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, CallToolResult
from tools import register_all_tools


class FastMCPSafe(FastMCP):
    async def call_tool(self, name, arguments):
        try:
            unreal.log(f"Calling tool {name}")
            response = await super().call_tool(name, arguments)
            unreal.log(f"Tool {name} response: {response}")
        except Exception as e:
            unreal.log(f"Error calling tool {name}: {repr(e)}")
            response = [TextContent(type="text", text=json.dumps({"Error": repr(e)}))]
        return CallToolResult(content=response)


def create_mcp_server():
    # Initialize server
    mcp = FastMCPSafe(
        "UnrealMCP", description="Unreal Engine integration via Model Context Protocol"
    )

    # Register tools
    register_all_tools(mcp)

    @mcp.prompt()
    def unreal_best_practices():
        """Best practices for working with Unreal MCP."""
        return """
        
        ## Best Practices
        ### Actor Creation and Management
        - Check if the actor already exists before creating a new one, especially landscapes
        - Location is specified as [x, y, z] in Unreal units
        - Rotation is specified as [pitch, yaw, roll] in degrees
        - Scale is specified as [x, y, z] multipliers (1.0 is default scale)
        - Always clean up temporary actors when no longer needed
        - Landscape is created with a size of 1009x1009 where x goes from 0 to 1008 and y goes 0 to 1008
        
        ### Blueprint Development
        - Always compile Blueprints after making changes
        - Use meaningful names for variables and functions
        - Organize nodes in the graph for better readability
        - Test Blueprint functionality in a controlled environment
        - Use proper variable types for different data needs
        - Consider performance implications when adding nodes
        
        ### Node Graph Management
        - Position nodes logically to maintain graph readability
        - Use appropriate node types for different operations
        - Connect nodes with proper pin types
        - Document complex node setups with comments
        - Test node connections before finalizing
        
        ### Input Mapping
        - Use descriptive names for input actions
        - Consider platform-specific input needs
        - Test input mappings thoroughly
        - Document input bindings for team reference
        
        ### Error Handling
        - Always check command responses for success status
        - Handle error cases gracefully
        - Log important operations and errors
        - Validate parameters before sending commands
        - Clean up resources in error cases
        """

    return mcp
