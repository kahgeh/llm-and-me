import subprocess
import sys


def read_clipboard():
    """
    Reads the content of the macOS system clipboard using the 'pbpaste' command.

    Returns:
        str: The content of the clipboard, or an error message if not on macOS
             or if 'pbpaste' fails.
    """
    if sys.platform != "darwin":
        return "Error: This tool only works on macOS."

    try:
        # Execute pbpaste and capture its output
        result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, check=True, encoding="utf-8"
        )
        return result.stdout
    except FileNotFoundError:
        return "Error: 'pbpaste' command not found. Ensure macOS clipboard utilities are installed."
    except subprocess.CalledProcessError as e:
        # Handle errors during command execution (e.g., non-zero exit code)
        error_message = f"Error executing 'pbpaste': {e}"
        if e.stderr:
            error_message += f"\nStderr: {e.stderr.strip()}"
        return error_message
    except Exception as e:
        # Catch any other unexpected errors
        return f"An unexpected error occurred: {e}"


def main():
    """
    Main function for potential CLI usage. Prints the clipboard content or error.
    """
    clipboard_content = read_clipboard()
    print(clipboard_content)


if __name__ == "__main__":
    main()
