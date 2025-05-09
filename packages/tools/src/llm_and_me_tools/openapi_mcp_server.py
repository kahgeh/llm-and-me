import sys

try:
    from fastmcp import FastMCP
except ImportError:
    print(
        "Error: FastMCP not found. Please install the required dependencies.",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    # Import the function that handles string content parsing and tree generation
    from .openapi_tools.openapi_to_tree import get_openapi_path_tree_from_content
except ImportError as e:
    print(f"Error importing OpenAPI tool functions: {e}", file=sys.stderr)
    print(
        "Ensure 'openapi_tools/openapi_to_tree.py' exists and contains 'get_openapi_path_tree_from_content'.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    mcp = FastMCP(
        "OpenAPI Tools",
        description="Provides tools for processing OpenAPI specifications.",
    )

    # Add the tool function directly
    mcp.add_tool(get_openapi_path_tree_from_content)
    mcp.run()


if __name__ == "__main__":
    print(f"Attempting to start OpenAPI MCP server ({__file__})...")
    main()
