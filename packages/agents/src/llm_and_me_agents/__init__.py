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

# --- Privacy Mode State ---
private_mode = False
# --- End Privacy Mode State ---
if os.getenv("LOGFIRE_TOKEN") is not None:
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

cortex_server = MCPServerStdio(
    "uv",
    args=["run", "cortex-mcp-server"],
)

openapi_server = MCPServerStdio(
    "uv",
    args=["run", "openapi-mcp-server"],
)

newrelic_server = MCPServerStdio(
    "uv",
    args=["run", "newrelic-mcp-server"],
)

processing_history_server = MCPServerStdio(
    "uv",
    args=["run", "processing-history-mcp-server"],
)

# Assuming mcp-server-git is already a command provided by the mcp-server-fetch package
main_git_server = MCPServerStdio(
    "mcp-server-git",
    args=[],
)

filesystem_server = MCPServerStdio(
    "npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
)

sqlite_server = MCPServerStdio(
    "docker",
    args=[
        "run",
        "--rm",
        "-i",
        "-v",
        f"{os.getcwd()}/data:/mcp",
        "mcp/sqlite",
        "--db-path",
        "/mcp/all.db",
    ],
)


# Prompt the user to choose the foundation model before creating the agent.
def select_model() -> str:
    models = [
        "deepseek:deepseek-chat",
        "openai:gpt-4o-mini",
        "openai:gpt-4o",
        "google-gla:gemini-2.0-flash",
        "google-gla:gemini-2.5-pro-preview-05-06",
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
        cortex_server,
        newrelic_server,
        openapi_server,
        filesystem_server,
        sqlite_server,
        processing_history_server,
    ],
    system_prompt="You are a software engineering assistant, using en-AU locale. If the user asks for json, return plain json text, nothing more",
)


async def main(cli_args: argparse.Namespace):
    """
    Main async function for the agent.

    Args:
        cli_args: Optional pre-parsed command-line arguments.
                  If None, arguments will be parsed internally.
    """
    global private_mode  # Allow modification of the global state

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

                if command == "edit":
                    session.default_buffer.reset()
                    session.default_buffer.open_in_editor()
                    continue

                if command == "toggle-privacy":
                    private_mode = not private_mode
                    if private_mode:
                        os.environ["LLM_AND_ME_PRIVATE_MODE"] = "1"
                        print(
                            "Private mode enabled. Tool outputs may be saved locally instead of displayed."
                        )
                        message_history.extend("**Private mode enabled**")
                    else:
                        # Use pop to remove the key if it exists, avoiding KeyError
                        os.environ.pop("LLM_AND_ME_PRIVATE_MODE", None)
                        message_history.remove("**Private mode disabled**")
                        print("Private mode disabled.")
                    continue  # Skip sending the command to the agent

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
