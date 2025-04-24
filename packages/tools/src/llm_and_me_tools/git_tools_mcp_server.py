#!/usr/bin/env python3
"""
MCP Server exposing Git related tools.
"""

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
        from .git_tools.git_diff import get_git_diff
        from .git_tools.git_change_warning import (
            check_change_size as check_git_change_size_logic,
        )
        from .git_tools.git_commit_convention_reader import (
            get_commit_conventions,
        )
        from .git_tools.repo_root_finder import get_repo_root
    except ImportError as e:
        print(f"Error importing Git tool functions: {e}", file=sys.stderr)
        print(
            "Ensure the 'git_tools' subdirectory exists and contains the required tool modules.",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp = FastMCP(
        "Git Tools",
        description="Provides tools for interacting with Git repositories.",
    )

    # Add the imported functions and the locally defined tool
    # Ensure the imported functions have appropriate docstrings for the agent to understand
    mcp.add_tool(get_git_diff)
    mcp.add_tool(check_git_change_size_logic)
    mcp.add_tool(get_commit_conventions)
    mcp.add_tool(get_repo_root)

    """Main function to run the MCP server."""
    mcp.run()


# Entry point for running the server directly (e.g., for testing or via script)
if __name__ == "__main__":
    print(f"Attempting to start Git MCP server ({__file__})...")
    main()
