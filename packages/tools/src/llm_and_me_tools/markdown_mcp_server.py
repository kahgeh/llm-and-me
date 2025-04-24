import sys
from fastmcp import FastMCP


def main():
    try:
        from .md_splitter import split_markdown
    except ImportError as e:
        print(f"Error importing 'split_markdown': {e}")
        sys.exit(1)  # Exit if import fails

    mcp = FastMCP(
        "Markdown Service",
        description="Provides tools for manipulating Markdown files. Splits based on the auto-detected highest header level.",
    )
    mcp.add_tool(split_markdown)
    mcp.run()


if __name__ == "__main__":
    print(f"Attempting to start Markdown MCP server ({__file__})...")
    main()
