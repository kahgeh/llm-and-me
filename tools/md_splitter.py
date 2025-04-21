import re
import os
import argparse
from fastmcp.server.server import FastMCP

md_mcp = FastMCP("Markdown Service")


@md_mcp.tool()
def split_markdown(input_file, output_dir, top_level_header_level):
    """
    Splits a Markdown file into multiple files based on the specified top-level header level.

    Args:
        input_file (str): The path to the input Markdown file.
        output_dir (str): The directory where the output files will be created.
        top_level_header_level (int): The level of the header to be considered as the top level (e.g., 1 for #, 2 for ##).
    """
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            markdown_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}")
        return
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    # Create the output directory if it doesn't exist
    # Check if output_dir is not empty before trying to create it
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        except OSError as e:
            print(f"Error creating output directory: {e}")
            return
    elif (
        not output_dir
    ):  # Handle case where output_dir might be empty string if input is in current dir
        output_dir = "."  # Use current directory

    # Construct the regex pattern for identifying headers of the specified level
    # Matches lines starting with the specified number of '#' followed by space and captures the header text.
    header_pattern = rf"^(#{{{top_level_header_level}}})\s+(.*?)$"

    # Find all top-level headers and their positions
    matches = list(re.finditer(header_pattern, markdown_content, flags=re.MULTILINE))

    # Handle content before the first header (introduction)
    first_header_start = matches[0].start() if matches else len(markdown_content)
    intro_content = markdown_content[:first_header_start].strip()
    if intro_content:
        intro_filename = "introduction.md"
        intro_filepath = os.path.join(output_dir, intro_filename)
        try:
            with open(intro_filepath, "w", encoding="utf-8") as outfile:
                outfile.write(intro_content)
            print(f"Created file: {intro_filepath}")
        except Exception as e:
            print(f"Error writing introduction file: {e}")

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
            print(f"Created file: {filepath}")
        except Exception as e:
            print(f"Error writing to file {filepath}: {e}")

    if not matches and not intro_content:
        print(
            "Warning: No headers found at the specified level and no introductory content detected."
        )


def main():
    """
    Main function to parse command line arguments and call the split_markdown function.
    """
    parser = argparse.ArgumentParser(
        description="Splits a Markdown file into multiple files based on top-level headers."
    )
    parser.add_argument("input_file", help="Path to the input Markdown file.")
    parser.add_argument(
        "top_level_header_level",
        type=int,
        help="The level of the header to split by (e.g., 1 for #, 2 for ##).",
    )
    # Make output_dir optional
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Directory for output files (defaults to the input file's directory).",
    )

    args = parser.parse_args()

    # Validate the top_level_header_level
    if not 1 <= args.top_level_header_level <= 6:
        print("Error: top_level_header_level must be between 1 and 6 (inclusive).")
        return

    # Determine the output directory
    if args.output_dir is None:
        # Default to the directory of the input file
        output_dir = os.path.dirname(os.path.abspath(args.input_file))
    else:
        output_dir = args.output_dir

    # Get absolute path for input file to handle relative paths correctly
    input_file_abs = os.path.abspath(args.input_file)

    if not os.path.isfile(input_file_abs):
        print(f"Error: Input file not found: {args.input_file}")
        return

    split_markdown(input_file_abs, output_dir, args.top_level_header_level)


if __name__ == "__main__":
    main()
