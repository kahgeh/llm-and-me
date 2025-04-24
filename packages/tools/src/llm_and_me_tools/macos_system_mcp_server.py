import sys
from fastmcp import FastMCP


def main():
    try:
        from .macos_clipboard_reader import read_clipboard
    except ImportError as e:
        print(f"Error importing 'read_clipboard': {e}")
        sys.exit(1)

    mcp = FastMCP(
        "macOS System Tools",
        description="Provides tools for interacting with the macOS system.",
    )

    mcp.add_tool(read_clipboard)
    mcp.run()


# This allows running the server directly or using fastmcp CLI commands.
if __name__ == "__main__":
    print(f"Attempting to start macOS System MCP server ({__file__})...")
    main()
