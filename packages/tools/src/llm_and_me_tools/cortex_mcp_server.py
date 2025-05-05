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
        )
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
    mcp.add_tool(get_cortex_teams_public)
    mcp.add_tool(save_cortex_teams_private)
    mcp.add_tool(get_cortex_team_relationships)
    mcp.run()


if __name__ == "__main__":
    print(f"Attempting to start Cortex MCP server ({__file__})...")
    main()
