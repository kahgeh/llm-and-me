#!/usr/bin/env python3

import os

# Import the centralized function for finding the repo root
from .repo_root_finder import get_repo_root


def get_commit_conventions() -> str:
    """
    Reads commit conventions from the conventions/commit.md file in the project root.

    Returns:
        The content of the conventions/commit.md file as a string,
        or an error message if the file cannot be found or read.
    """
    try:
        # Find project root using the imported function
        # Note: get_repo_root determines the start path internally based on its own location
        project_root = get_repo_root()
        convention_file_path = os.path.join(project_root, "conventions", "commit.md")

        if not os.path.exists(convention_file_path):
            return "Error: conventions/commit.md file not found in the project root."

        with open(convention_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return "Info: conventions/commit.md exists but is empty."
            return content
    except FileNotFoundError as e:
        # Handle cases where project root or the convention file isn't found
        return f"Error: {e}"
    except IOError as e:
        return f"Error reading conventions/commit.md: {e}"
    except Exception as e:
        # Catch any other unexpected errors
        return f"An unexpected error occurred while reading commit conventions: {e}"


def main() -> None:
    """Prints the commit conventions to standard output."""
    conventions = get_commit_conventions()
    print(conventions)


if __name__ == "__main__":
    main()
