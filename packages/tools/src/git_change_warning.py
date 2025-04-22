#!/usr/bin/env python3
"""
Simple CLI that warns when a Git diff exceeds a configurable size.

Usage
-----
    git-change-warning                     # compare working tree against HEAD
    git-change-warning -f 30 -l 800        # custom thresholds
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Optional, Tuple

default_file_threshold = 8


def run(cmd: list[str]) -> str:
    "Run command and return stdout, fail loudly on error"
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def diff_stats() -> Tuple[int, int]:
    """
    Return (files_changed, total_lines_changed) for diff against HEAD.
    Unstaged and staged changes are included.
    """
    # --numstat: tab‑separated added, removed, file
    output = run(["git", "diff", "--numstat", "HEAD"])
    files = 0
    lines = 0
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, removed, _ = parts
        # Handle binary files which show '-' in place of counts
        if added.isdigit():
            lines += int(added)
        if removed.isdigit():
            lines += int(removed)
        files += 1
    return files, lines


def check_change_size(
    files: int, lines: int, file_threshold: Optional[int] = None, line_threshold: Optional[int] = None
) -> Optional[str]:
    """
    Return a warning string if specified thresholds are exceeded, otherwise None.
    If no thresholds are provided, defaults to checking against a file threshold of 8.
    """
    effective_file_threshold = file_threshold
    effective_line_threshold = line_threshold

    # Apply default file threshold if none are specified
    if effective_file_threshold is None and effective_line_threshold is None:
        effective_file_threshold = default_file_threshold

    should_warn = False
    messages: list[str] = []

    if effective_file_threshold is not None and files >= effective_file_threshold:
        # Consistent message formatting
        messages.append(f"{files} files (threshold {effective_file_threshold})")
        should_warn = True
    if effective_line_threshold is not None and lines >= effective_line_threshold:
        messages.append(f"{lines} lines (threshold {effective_line_threshold})")
        should_warn = True

    if not should_warn:
        return None # Return None if no warning needed

    joined = ", ".join(messages)
    return f"⚠️ Large change detected: {joined}" # Return the warning string


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warn when a Git diff is large.")
    parser.add_argument(
        "-f",
        "--file-threshold",
        type=int,
        required=False,
        help=f"Warn when at least this many files change. Defaults to {default_file_threshold} if no thresholds are specified.",
    )
    parser.add_argument(
        "-l",
        "--line-threshold",
        type=int,
        required=False,
        help="Warn when at least this many total lines change.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    file_thresh = args.file_threshold
    line_thresh = args.line_threshold

    # Apply default file threshold if none are specified
    if file_thresh is None and line_thresh is None:
        file_thresh = default_file_threshold

    changed_files, changed_lines = diff_stats()
    # Call the function which now handles defaults internally
    warning_message = check_change_size(changed_files, changed_lines, file_thresh, line_thresh)
    if warning_message:
        print(warning_message, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
