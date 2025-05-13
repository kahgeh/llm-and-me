import sys

from fastmcp import FastMCP

try:
    from .processing_history_tools.get_last_processing_entry import (
        get_last_processing_entry,
    )
    from .processing_history_tools.save_processing_entry import save_processing_entry
except ImportError as e:
    print(f"Error importing processing history tool functions: {e}", file=sys.stderr)
    print(
        "Ensure 'processing_history_tools/get_last_processing_entry.py' and "
        "'processing_history_tools/save_processing_entry.py' exist in the llm_and_me_tools package "
        "and contain the required functions and Pydantic models.",
        file=sys.stderr,
    )
    sys.exit(1)

# Create FastMCP instance


def main():
    mcp = FastMCP(
        "Processing History Tools",
        description="Provides tools for processing history.",
    )
    mcp.add_tool(get_last_processing_entry)
    mcp.add_tool(save_processing_entry)

    """Runs the FastMCP server for processing history tools."""
    mcp.run()


if __name__ == "__main__":
    main()
