import sys


def main():
    try:
        from fastmcp import FastMCP
    except ImportError:
        print(
            "Error: FastMCP not found. Please install the required dependencies.",
            file=sys.stderr,
        )
        # Example: print("Try running: pip install fastmcp", file=sys.stderr)
        sys.exit(1)

    try:
        # Import the new specific functions
        from .cortex_tools.list_teams import (
             get_cortex_teams_public,
             save_cortex_teams_private,
        )
        from .cortex_tools.get_team_relationships import (
            get_cortex_team_relationships,
            save_cortex_team_relationships_private, # Assuming this exists and should be added
        )
        # Import component listing and saving functions
        from .cortex_tools.list_components import (
            list_cortex_components,
            save_cortex_components_private as save_cortex_components_private_func, # Alias to avoid name clash if needed elsewhere
        )
        # Import the team component filtering function
        from .cortex_tools.get_team_components import get_team_components
        # Import the entity documentation function
        from .cortex_tools.get_entity_docs import get_cortex_entity_docs
    except ImportError as e:
        print(f"Error importing Cortex tool functions: {e}", file=sys.stderr)
        print(
            "Ensure the 'cortext_tools' subdirectory exists and contains the required tool modules.",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp = FastMCP(
        "Cortex Tools",
        description="Provides tools for interacting with Cortex API.",
    )

    # Add the two new tools instead of the old combined one
    # Team tools
    mcp.add_tool(get_cortex_teams_public)
    mcp.add_tool(save_cortex_teams_private)
    # Relationship tools
    mcp.add_tool(get_cortex_team_relationships)
    # mcp.add_tool(save_cortex_team_relationships_private) # Uncomment if this tool exists and is desired
    # Component tools
    mcp.add_tool(list_cortex_components)
    mcp.add_tool(save_cortex_components_private_func)
    mcp.add_tool(get_team_components)  # Tool to filter components by team hierarchy
    # Entity documentation tool
    mcp.add_tool(get_cortex_entity_docs)
    mcp.run()


if __name__ == "__main__":
    print(f"Attempting to start Cortex MCP server ({__file__})...")
    main()
