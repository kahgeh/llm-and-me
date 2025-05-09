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
    # Import the function that returns the API path tree as a string
    from .openapi_tools.openapi_to_tree import get_openapi_path_tree_as_string
    # Import the new function to save OpenAPI spec to SQLite
    from .openapi_tools.openapi_to_sqlite import save_openapi_spec_to_sqlite
except ImportError as e:
    print(f"Error importing OpenAPI tool functions: {e}", file=sys.stderr)
    print(
        "Ensure 'openapi_tools/openapi_to_tree.py' and 'openapi_tools/openapi_to_sqlite.py' exist and contain the required functions.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    mcp = FastMCP(
        "OpenAPI Tools",
        description="Provides tools for processing OpenAPI specifications.",
    )

    # Add the tool function that returns the tree as a string
    mcp.add_tool(get_openapi_path_tree_as_string)
    # Add the new tool function to save OpenAPI spec to SQLite
    mcp.add_tool(save_openapi_spec_to_sqlite)
    mcp.run()


if __name__ == "__main__":
    print(f"Attempting to start OpenAPI MCP server ({__file__})...")
    main()
