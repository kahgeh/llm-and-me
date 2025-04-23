#!/usr/bin/env python3
"""
Tool to find the project root directory based on a marker file/directory.
"""

import os


def get_repo_root(max_levels: int = 10) -> str:
    """
    Gets git repository path by searching upwards for the .git folder, stopping after max_levels.

    Args:
        max_levels: The maximum number of parent directories to search upwards (default: 10).

    Returns:
        The absolute path to the determined project root directory.

    Raises:
        FileNotFoundError: If the project root containing the marker cannot be found.
    """
    marker = ".git"
    # Start searching from the current working directory
    start_path = os.getcwd()
    current_path = start_path
    levels_checked = 0
    while levels_checked < max_levels:
        # Check if the marker exists
        marker_path = os.path.join(current_path, marker)
        if marker == ".git" and os.path.isdir(marker_path):
            return current_path
        elif marker != ".git" and os.path.exists(marker_path):
            return current_path

        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            # Reached the filesystem root
            break

        current_path = parent_path
        levels_checked += 1

    # If the loop finishes without finding the marker
    raise FileNotFoundError(
        f"Could not find project root containing '{marker}' within {max_levels} levels "
        f"up from '{start_path}'"
    )


# Example usage if run directly (for testing)
if __name__ == "__main__":
    try:
        root = get_repo_root()
        print(f"Project root found: {root}")
    except FileNotFoundError as e:
        print(e)
