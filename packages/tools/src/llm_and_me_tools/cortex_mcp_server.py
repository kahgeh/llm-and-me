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
        from .cortex_tools.get_descendent_teams import get_descendant_teams
        from .cortex_tools.get_entity_docs import get_cortex_entity_docs
        from .cortex_tools.get_team_components import get_team_components
        from .cortex_tools.list_components import save_cortex_components_private
        from .cortex_tools.list_team_relationships import (
            save_cortex_team_relationships_private,
        )
        from .cortex_tools.list_teams import save_cortex_teams_private

    except ImportError as e:
        print(f"Error importing Cortex tool functions: {e}", file=sys.stderr)
        print(
            "Ensure the 'cortex_tools' subdirectory exists and contains the required tool modules.",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp = FastMCP(
        "Cortex Tools",
        description="Provides tools for interacting with Cortex API.",
    )

    # Add the two new tools instead of the old combined one
    # Team tools
    mcp.add_tool(save_cortex_teams_private)
    mcp.add_tool(save_cortex_team_relationships_private)
    mcp.add_tool(save_cortex_components_private)
    mcp.add_tool(get_descendant_teams)
    mcp.add_tool(get_team_components)
    mcp.add_tool(get_cortex_entity_docs)
    mcp.run()


if __name__ == "__main__":
    print(f"Attempting to start Cortex MCP server ({__file__})...")
    main()
