# General

- Avoid code block nesting, where possible
- Avoid the else construct, return early instead

# Tools

## Ensure each tool is implemented in such a way that it can be called directly as a script

- Provide the `if __name__ == "__main__"` block, which implements command line argument parsing if required

## Describe the tool close to the function

- Import and add the tool function
  e.g.

```
  try:
      from .openapi_tools.openapi_to_tree import get_openapi_path_tree_as_string
      from .openapi_tools.openapi_to_sqlite import save_openapi_spec_to_sqlite
  except ImportError as e:
      print(f"Error importing OpenAPI tool functions: {e}", file=sys.stderr)
      print(
          "Ensure 'openapi_tools/openapi_to_tree.py' and 'openapi_tools/openapi_to_sqlite.py' exist and contain the required functions.",
          file=sys.stderr,
      )
      sys.exit(1)

  mcp.add_tool(get_openapi_path_tree_as_string)
  mcp.add_tool(save_openapi_spec_to_sqlite)
```
