import argparse
import os
import re
from typing import Optional


def split_markdown(
    output_dir: Optional[str] = None,
    input_file: Optional[str] = None,
    markdown_content: Optional[str] = None,
):
    """
    Splits a Markdown file or content string into multiple files based on the highest-level header found (e.g., H1 before H2).

    Provide either `input_file` or `markdown_content`.

    Args:
        output_dir (Optional[str]): The directory for output files. Defaults to the input file's directory if input_file is provided, otherwise defaults to the current directory (".").
        input_file (Optional[str]): The path to the input Markdown file. Used if markdown_content is None.
        markdown_content (Optional[str]): The Markdown content as a string. Takes precedence over input_file.

    Returns:
        str: A message indicating the completion status or errors.
    """
    messages = []

    if markdown_content is None:
        if input_file is None:
            return "Error: Must provide either input_file or markdown_content."
        try:
            # Ensure input file path is absolute for reliable reading
            abs_input_file = os.path.abspath(input_file)
            with open(abs_input_file, "r", encoding="utf-8") as f:
                markdown_content = f.read()
        except FileNotFoundError:
            return f"Error: Input file not found: {abs_input_file}"
        except Exception as e:
            return f"Error reading input file {abs_input_file}: {e}"
    elif not isinstance(markdown_content, str):
        return "Error: markdown_content must be a string."

    if not markdown_content:
        return "Error: Markdown content is empty."

    # Determine default output directory if not provided
    if output_dir is None:
        if input_file:
            output_dir = os.path.dirname(os.path.abspath(input_file))
        else:
            # If only content is provided, default to current directory
            output_dir = "."

    # --- Auto-detect top header level ---
    top_level_header_level = 0
    # Regex to find the first header line (up to H6)
    first_header_match = re.search(
        r"^(#{1,6})\s+.*$", markdown_content, flags=re.MULTILINE
    )
    if first_header_match:
        top_level_header_level = len(
            first_header_match.group(1)
        )  # Count the '#' characters
        messages.append(f"Auto-detected top header level: H{top_level_header_level}")
    else:
        return (
            "Error: No markdown headers found in the content to determine split level."
        )
    # --- End auto-detect ---

    # Create the output directory if it doesn't exist
    # Check if output_dir is not empty before trying to create it
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            messages.append(f"Created output directory: {output_dir}")
        except OSError as e:
            return f"Error creating output directory: {e}"
    elif (
        not output_dir
    ):  # Handle case where output_dir might be empty string if input is in current dir
        output_dir = "."  # Use current directory

    # Construct the regex pattern for identifying headers of the specified level
    # Matches lines starting with the specified number of '#' followed by space and captures the header text.
    header_pattern = rf"^(#{{{top_level_header_level}}})\s+(.*?)$"

    # Find all top-level headers and their positions
    matches = list(re.finditer(header_pattern, markdown_content, flags=re.MULTILINE))

    # Iterate through the matches to split the content
    for i, match in enumerate(matches):
        header_hashes = match.group(1)  # e.g., "##"
        header_text = match.group(2).strip()

        # Determine the start and end of the content for this section
        start_index = match.end()
        end_index = (
            matches[i + 1].start() if i + 1 < len(matches) else len(markdown_content)
        )
        content = markdown_content[start_index:end_index].strip()

        # Create a safe filename from the header text. Replace non-alphanumeric characters with underscores.
        # Keep spaces for readability, replace others.
        safe_header_text = re.sub(r"[^\w\-\. ]", "_", header_text)
        # Replace multiple consecutive underscores/spaces with a single underscore
        safe_header_text = re.sub(r"[_ ]+", "_", safe_header_text)
        filename = f"{safe_header_text}.md"
        filepath = os.path.join(output_dir, filename)

        # Prepend the original header to the content.
        file_content = f"{header_hashes} {header_text}\n\n{content}"

        try:
            with open(filepath, "w", encoding="utf-8") as outfile:
                outfile.write(file_content)
            messages.append(f"Created file: {filepath}")
        except Exception as e:
            messages.append(f"Error writing to file {filepath}: {e}")

    # Return a summary message for the MCP tool execution
    if any("Error" in msg for msg in messages):
        return "\n".join(messages)
    elif not messages:
        return "No actions taken. Input might be empty or lack specified headers."
    else:
        return "Markdown splitting completed.\n" + "\n".join(messages)


def main():
    """
    Main function to parse command line arguments and call the split_markdown function.
    """
    parser = argparse.ArgumentParser(
        description="Splits a Markdown file into multiple files based on the automatically detected highest-level header."
    )
    # Make output_dir optional
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Directory for output files (defaults to the input file's directory).",
        required=False,
    )

    parser.add_argument("-i", "--input-file", help="Path to the input Markdown file.")
    parser.add_argument(
        "-c",
        "--markdown-content",
        help="Markdown content as a string. If provided, input-file is ignored.",
        required=False,
    )

    args = parser.parse_args()

    # Get absolute path for input file if provided
    input_file_abs = None
    if args.input_file:
        input_file_abs = os.path.abspath(args.input_file)
        if not os.path.isfile(input_file_abs):
            print(f"Error: Input file not found: {args.input_file}")
            return
    elif not args.markdown_content:
        print("Error: Must provide either --input-file or --markdown-content.")
        return


    # Call split_markdown. output_dir defaulting is handled inside.
    result = split_markdown(
        output_dir=args.output_dir,  # Pass None if not provided, function handles default
        input_file=input_file_abs,
        markdown_content=args.markdown_content,
    )
    # Print the result message for CLI feedback
    print(result)


if __name__ == "__main__":
    main()
