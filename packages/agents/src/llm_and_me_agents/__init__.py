import argparse
import asyncio
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.cursor_shapes import (CursorShape, ModalCursorShapeConfig,
                                          SimpleCursorShapeConfig)
from prompt_toolkit.history import InMemoryHistory
from pydantic_ai import Agent

from .initialisations import (AgentSpecification, initialise_mcp_servers,
                              load_agent_specifications)

load_dotenv()


# --- Privacy Mode State ---
private_mode = False
# --- End Privacy Mode State ---


ALL_MCP_SERVERS = initialise_mcp_servers()
# --- End MCP Server Definitions ---

# --- Agent Initialization ---
agent_specifications: List[AgentSpecification] = load_agent_specifications()
if not agent_specifications:
    print("No agent specifications loaded. Exiting.")
    sys.exit(1)

# Use the first agent specification as the default/initial agent
current_agent_spec = agent_specifications[0]
print(f"Initialising with agent: {current_agent_spec.name} ({current_agent_spec.description})")

active_mcp_servers = []
for server_name in current_agent_spec.mcp_servers:
    server_instance = ALL_MCP_SERVERS.get(server_name)
    if server_instance:
        active_mcp_servers.append(server_instance)
    else:
        print(f"Warning: MCP Server '{server_name}' defined in agent spec but not found in ALL_MCP_SERVERS.")

agent = Agent(
    model=current_agent_spec.llm_model_name,
    base_url=current_agent_spec.base_url,
    instrument=True,
    mcp_servers=active_mcp_servers,
    system_prompt=current_agent_spec.system_prompt,
)
# --- End Agent Initialization ---


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

    message_history = []  # initialise empty message history
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

                if command == "list-agents":
                    print("Available agents:")
                    for spec in agent_specifications:
                        print(f"- {spec.name}: {spec.description}")
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
