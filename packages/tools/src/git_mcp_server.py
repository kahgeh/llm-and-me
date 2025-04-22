#!/usr/bin/env python3
"""
MCP Server exposing Git related tools.
"""

import os
import sys
from typing import Optional

# Add the src directory to the Python path
# This allows importing modules from the same directory when run as a script
current_file_path = os.path.abspath(__file__)
src_dir = os.path.dirname(current_file_path)
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Determine project root assuming script is in packages/tools/src
project_root = os.path.dirname(os.path.dirname(os.path.dirname(src_dir)))

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
    from git_diff import get_git_diff

    # Import both diff_stats and the renamed check function
    from git_change_warning import (
        diff_stats,
        check_change_size as check_git_change_size_logic,
    )
except ImportError as e:
    print(f"Error importing Git tool functions: {e}", file=sys.stderr)
    print(
        "Ensure git_diff.py and git_change_warning.py are in the same directory.",
        file=sys.stderr,
    )
    sys.exit(1)


mcp = FastMCP(
    "Git Tools",
    description="Provides tools for interacting with Git repositories.",
    project_root=project_root,
)

# Add the imported functions directly as tools
# Ensure the imported functions have appropriate docstrings for the agent to understand
mcp.add_tool(get_git_diff)
mcp.add_tool(check_git_change_size_logic)


# Entry point for running the server directly (e.g., for testing)
if __name__ == "__main__":
    # This allows running the server via `python packages/tools/src/git_mcp_server.py`
    # It requires FastMCP's CLI handling or a simple runner.
    print(f"Attempting to start Git MCP server ({__file__})...")
    mcp.run()
