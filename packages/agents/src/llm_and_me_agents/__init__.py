import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from logfire import configure
from prompt_toolkit import PromptSession
from prompt_toolkit.cursor_shapes import (
    CursorShape,
    ModalCursorShapeConfig,
    SimpleCursorShapeConfig,
)
from prompt_toolkit.history import InMemoryHistory
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

load_dotenv()
configure(token=os.getenv("LOGFIRE_TOKEN"))
print(sys.executable)

markdown_server = MCPServerStdio(
    "uv",
    args=["run", "markdown-mcp-server"],
)

macos_system_server = MCPServerStdio(
    "uv",
    args=["run", "macos-mcp-server"],
)

custom_git_server = MCPServerStdio(
    "uv",
    args=["run", "git-tools-mcp-server"],
)

# Assuming mcp-server-git is already a command provided by the mcp-server-fetch package
main_git_server = MCPServerStdio(
    "mcp-server-git",
    args=[],
)


# Prompt the user to choose the foundation model before creating the agent.
def select_model() -> str:
    models = [
        "deepseek:deepseek-chat",
        "openai:gpt-4o-mini",
        "openai:gpt-4o",
        "google-gla:gemini-2.0-flash",
        "google-gla:gemini-2.5-pro-preview-03-25",
    ]
    print("Select a model:")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model}")
    while True:
        choice = input("> ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            return models[int(choice) - 1]
        print("Invalid selection, try again.")


selected_model = select_model()
agent = Agent(
    selected_model,
    instrument=True,
    mcp_servers=[
        markdown_server,
        macos_system_server,
        custom_git_server,
        main_git_server,
    ],
    system_prompt="You are a software engineering assistant, using en-AU locale. Do not try more than 3 times. If the user asks for json, return plain json text, nothing more",
)


async def main(cli_args: argparse.Namespace):
    """
    Main async function for the agent.

    Args:
        cli_args: Optional pre-parsed command-line arguments.
                  If None, arguments will be parsed internally.
    """

    vi_mode = False
    cursor_shape = SimpleCursorShapeConfig(CursorShape.BLINKING_BEAM)
    if cli_args and cli_args.vi:
        print("vim motion mode enabled.")
        vi_mode = True
        cursor_shape = ModalCursorShapeConfig()

    message_history = []  # Initialize empty message history
    history = InMemoryHistory()
    session = PromptSession(history=history, vi_mode=vi_mode, cursor=cursor_shape)

    async with agent.run_mcp_servers():
        print("Agent started. Type '/reset' to clear history, '/exit' to quit.")
        while True:
            try:
                user_input = (
                    await session.prompt_async("\n> ", enable_open_in_editor=True)
                ).strip()
            except (EOFError, KeyboardInterrupt):  # Handle Ctrl+D/Ctrl+C gracefully
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                command = user_input[1:].lower()
                if command == "exit":
                    break

                if command == "reset":
                    message_history = []
                    print("Message history cleared.")
                    continue
                else:
                    print(f"Unknown command: {user_input}")
                    continue

            result = await agent.run(user_input, message_history=message_history)
            print(f"\n{result.output}")
            message_history.extend(result.new_messages())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LLM and Me agent.")
    parser.add_argument(
        "--vi", action="store_true", help="Enable Vi key bindings for input."
    )
    # Use parse_known_args if running directly, in case other args exist
    cli_args, _ = parser.parse_known_args()

    asyncio.run(main(cli_args))
