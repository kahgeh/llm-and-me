import argparse
import asyncio
import os
import sys
import toml # Added
from typing import List, Optional # Added

from dotenv import load_dotenv
from logfire import configure
from prompt_toolkit import PromptSession
from prompt_toolkit.cursor_shapes import (CursorShape, ModalCursorShapeConfig,
                                          SimpleCursorShapeConfig)
from prompt_toolkit.history import InMemoryHistory
from pydantic import BaseModel # Added
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP, MCPServerStdio

load_dotenv()


# --- Agent Specification ---
class AgentSpecification(BaseModel):
    name: str
    description: str
    llm_model_name: str
    base_url: Optional[str] = None
    mcp_servers: List[str]


def load_agent_specifications(file_path: str = "packages/agents/agents.toml") -> List[AgentSpecification]:
    try:
        with open(file_path, "r") as f:
            data = toml.load(f)
        # Validate and parse agent specifications
        specs_data = data.get("agents", [])
        if not specs_data:
            print(f"Warning: No agents found in '{file_path}'.")
            return []
        return [AgentSpecification(**spec) for spec in specs_data]
    except FileNotFoundError:
        print(f"Error: Agent configuration file '{file_path}' not found.")
        print("Please ensure 'agents.toml' exists and is correctly formatted.")
        sys.exit(1)
    except Exception as e: # Includes toml.TomlDecodeError and pydantic.ValidationError
        print(f"Error loading or parsing agent specifications from '{file_path}': {e}")
        sys.exit(1)
# --- End Agent Specification ---

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

datetime_server = MCPServerStdio(
    "uv",
    args=["run", "datetime-mcp-server"],
)

main_git_server = MCPServerStdio(
   "uvx",
    args=["mcp-server-git" ],
)

filesystem_server = MCPServerStdio(
    "npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
)

sqlite_server = MCPServerStdio(
    "uvx",
    args=["mcp-server-sqlite" ],
)

fetch_server = MCPServerStdio(
    "uvx",
    args=["mcp-server-fetch" ],
)

brave_api_key = os.getenv("BRAVE_API_KEY", "")
search_server = MCPServerStdio(
    "sh",
    args=["-c", f"BRAVE_API_KEY='{brave_api_key}' npx -y @modelcontextprotocol/server-brave-search"],
)

rag_crawler_server = MCPServerHTTP(url='http://localhost:8051/sse')

# --- MCP Server Definitions and Mapping ---
ALL_MCP_SERVERS = {
    "markdown_server": markdown_server,
    "macos_system_server": macos_system_server,
    "custom_git_server": custom_git_server,
    "main_git_server": main_git_server,
    "cortex_server": cortex_server,
    "newrelic_server": newrelic_server,
    "openapi_server": openapi_server,
    "filesystem_server": filesystem_server,
    "fetch_server": fetch_server,
    "search_server": search_server,
    "sqlite_server": sqlite_server,
    "processing_history_server": processing_history_server,
    "datetime_server": datetime_server,
    "rag_crawler_server": rag_crawler_server,
}
# --- End MCP Server Definitions ---

# --- Agent Initialization ---
agent_specifications = load_agent_specifications()
if not agent_specifications:
    print("No agent specifications loaded. Exiting.")
    sys.exit(1)

# Use the first agent specification as the default/initial agent
current_agent_spec = agent_specifications[0]
print(f"Initializing with agent: {current_agent_spec.name} ({current_agent_spec.description})")

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
    system_prompt="You are a software engineering assistant, using en-AU locale. If the user asks for json, return plain json text, nothing more",
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
