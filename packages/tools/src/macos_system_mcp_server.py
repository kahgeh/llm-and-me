import sys
import os
from fastmcp import FastMCP

# --- Start: Add project root to sys.path ---
# Get the absolute path of the current script file
current_file_path = os.path.abspath(__file__)
# Navigate up four levels to get the project root directory
# (src -> tools -> packages -> my-ai-and-me)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))))
# Prepend the project root to sys.path if it's not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End: Add project root to sys.path ---

# Import the tool function from the macos_clipboard_reader module
# This relies on the sys.path modification above
try:
    from packages.tools.src.macos_clipboard_reader import read_clipboard
except ImportError as e:
    print(f"Error importing 'read_clipboard': {e}")
    print(f"Project root added to sys.path: {project_root}")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1) # Exit if import fails, as the server can't function


# Create the FastMCP server instance
mcp = FastMCP(
    "macOS System Tools",
    description="Provides tools for interacting with the macOS system.",
    # Add dependencies if any tool requires them
    # dependencies=[]
)

# Register the imported function as an MCP tool.
# FastMCP will introspect the function signature and docstring.
mcp.add_tool(read_clipboard)

# This allows running the server directly or using fastmcp CLI commands.
if __name__ == "__main__":
    print(f"Attempting to start macOS System MCP server ({__file__})...")
    mcp.run()
