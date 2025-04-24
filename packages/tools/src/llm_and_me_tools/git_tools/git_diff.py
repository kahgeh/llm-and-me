#!/usr/bin/env python3
"""
Simple CLI tool that prints the output of 'git diff'.
"""

from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> str:
    "Run command and return stdout, fail loudly on error"
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def get_git_diff() -> str:
    """
    Return the output of 'git diff'.
    Includes unstaged and staged changes against HEAD.
    """
    return run(["git", "diff", "HEAD"])


def main() -> None:
    """Prints the git diff output."""
    try:
        diff_output = get_git_diff()
        print(diff_output)
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff: {e}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in your PATH?", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
