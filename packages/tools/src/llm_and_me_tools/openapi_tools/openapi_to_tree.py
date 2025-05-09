import yaml
import json
import sys


def generate_api_tree(openapi_spec: dict) -> dict:
    """Generates a tree structure of API paths from an OpenAPI specification dictionary."""
    paths = openapi_spec.get("paths", {})
    tree = {}
    for path, methods in paths.items():
        segments = [segment for segment in path.split("/") if segment]
        current_level = tree
        for segment in segments:
            if segment not in current_level:
                current_level[segment] = {}
            current_level = current_level[segment]
        for method_key in methods: # methods is a dict, method_key is e.g. 'get', 'post'
            current_level[f"[{method_key.upper()}]"] = None  # Mark as a leaf node
    return tree


def get_openapi_path_tree_from_content(openapi_content: str, content_type: str = "yaml") -> dict:
    """
    Parses OpenAPI content (YAML or JSON string) and generates a tree of API paths.
    content_type can be 'yaml' or 'json'.
    """
    spec: dict

    normalized_content_type = content_type.lower()

    if normalized_content_type == "yaml":
        try:
            spec = yaml.safe_load(openapi_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML content: {e}") from e
    elif normalized_content_type == "json":
        try:
            spec = json.loads(openapi_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON content: {e}") from e
    else:
        raise ValueError("Unsupported content_type. Use 'yaml' or 'json'.")

    if not isinstance(spec, dict):
        raise ValueError(
            "Parsed OpenAPI content did not result in a dictionary. "
            "Please ensure the content is valid."
        )

    if "paths" not in spec:
        raise ValueError(
            "Invalid OpenAPI specification format. Missing 'paths' section."
        )

    return generate_api_tree(spec)


def print_tree(tree, prefix="", is_last=True):
    """Prints the tree structure to the console."""
    items = list(tree.keys())
    num_items = len(items)
    for i, key in enumerate(items):
        is_last_item = i == num_items - 1
        marker = "└── " if is_last_item else "├── "
        print(prefix + marker + key)

        subtree = tree[key]
        if subtree is not None and isinstance(subtree, dict) and len(subtree) > 0:
            new_prefix = prefix + ("    " if is_last_item else "│   ")
            print_tree(subtree, new_prefix, is_last_item)


def main():
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <openapi_file>")
        sys.exit(1)

    openapi_file = sys.argv[1]

    try:
        with open(openapi_file, "r") as f:
            if openapi_file.endswith((".yaml", ".yml")):
                openapi_spec_content = f.read()
                api_tree = get_openapi_path_tree_from_content(openapi_spec_content, "yaml")
            elif openapi_file.endswith(".json"):
                openapi_spec_content = f.read()
                api_tree = get_openapi_path_tree_from_content(openapi_spec_content, "json")
            else:
                print(
                    "Error: Unsupported file format. Please provide a YAML or JSON OpenAPI specification."
                )
                sys.exit(1)

        if api_tree:
            print("paths/")
            branches = list(api_tree.keys())
            num_branches = len(branches)
            for i, branch in enumerate(branches):
                is_last_branch = i == num_branches - 1
                print_tree({branch: api_tree[branch]}, "", is_last_branch)
        else:
            print("No API paths found in the specification.")

    except FileNotFoundError:
        print(f"Error: File not found: {openapi_file}")
        sys.exit(1)
    except ValueError as e: # Catch parsing errors from get_openapi_path_tree_from_content
        print(f"Error processing OpenAPI content: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
