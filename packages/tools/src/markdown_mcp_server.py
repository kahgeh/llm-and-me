import sys
import os
from fastmcp import FastMCP

# --- Start: Add project root to sys.path ---
# Get the absolute path of the current script file
current_file_path = os.path.abspath(__file__)
# Navigate up four levels to get the project root directory
# (src -> tools -> packages -> my-ai-and-me)
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End: Add project root to sys.path ---

# Import the tool function using the full path now that sys.path is set
try:
    from packages.tools.src.md_splitter import split_markdown
except ImportError as e:
    print(f"Error importing 'split_markdown': {e}")
    print(f"Project root added to sys.path: {project_root}")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1) # Exit if import fails

mcp = FastMCP(
    "Markdown Service",
    description="Provides tools for manipulating Markdown files. Splits based on the auto-detected highest header level.",
)

# Register the tool. FastMCP will introspect the updated signature.
# but direct MCP calls might need specific handling for optional params.
# The core functionality via input_file remains.
mcp.add_tool(split_markdown)

if __name__ == "__main__":
    print(f"Attempting to start Markdown MCP server ({__file__})...")
    mcp.run()
