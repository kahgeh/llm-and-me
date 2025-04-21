import yaml
import json
import sys


def generate_api_tree(openapi_spec):
    """Generates a tree structure of API paths from an OpenAPI specification."""
    paths = openapi_spec.get("paths", {})
    tree = {}
    for path, methods in paths.items():
        segments = [segment for segment in path.split("/") if segment]
        current_level = tree
        for segment in segments:
            if segment not in current_level:
                current_level[segment] = {}
            current_level = current_level[segment]
        for method in methods:
            current_level[f"[{method.upper()}]"] = None  # Mark as a leaf node

    return tree


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
                openapi_spec = yaml.safe_load(f)
            elif openapi_file.endswith(".json"):
                openapi_spec = json.load(f)
            else:
                print(
                    "Error: Unsupported file format. Please provide a YAML or JSON OpenAPI specification."
                )
                sys.exit(1)

        if not isinstance(openapi_spec, dict) or "paths" not in openapi_spec:
            print(
                "Error: Invalid OpenAPI specification format. Missing 'paths' section."
            )
            sys.exit(1)

        api_tree = generate_api_tree(openapi_spec)

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
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

