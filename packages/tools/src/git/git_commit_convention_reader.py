#!/usr/bin/env python3
"""
Tool to read commit conventions from the project's conventions/commit.md file.
"""

from __future__ import annotations

import os
import sys


def find_project_root(start_path: str, marker: str = ".git", max_levels: int = 10) -> str:
    """
    Helper function to find the project root directory marked by a specific file/directory.
    Searches upwards from start_path, stopping after max_levels.
    """
    current_path = os.path.abspath(start_path)
    levels_checked = 0
    while levels_checked < max_levels:
        # Check if the marker (specifically .git directory) exists
        if os.path.isdir(os.path.join(current_path, marker)):
            return current_path

        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            # Reached the filesystem root without finding the marker
            break

        current_path = parent_path
        levels_checked += 1

    # If the loop finishes without finding the marker
    raise FileNotFoundError(
        f"Could not find project root containing '{marker}' within {max_levels} levels "
        f"up from '{start_path}'"
    )


def get_commit_conventions() -> str:
    """
    Reads commit conventions from the conventions/commit.md file in the project root.

    Returns:
        The content of the conventions/commit.md file as a string,
        or an error message if the file cannot be found or read.
    """
    try:
        # Find project root starting from this file's directory
        project_root = find_project_root(os.path.dirname(__file__))
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
