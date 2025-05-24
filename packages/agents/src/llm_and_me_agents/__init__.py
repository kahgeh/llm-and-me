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

# current_agent_spec, active_mcp_servers, and agent will be initialized in main()
current_agent_spec: Optional[AgentSpecification] = None
active_mcp_servers: List = []
agent: Optional[Agent] = None
# --- End Agent Initialization ---


async def main(cli_args: argparse.Namespace):
    """
    Main async function for the agent.

    Args:
        cli_args: Optional pre-parsed command-line arguments.
                  If None, arguments will be parsed internally.
    """
    global private_mode
    global current_agent_spec
    global active_mcp_servers
    global agent

    vi_mode = False
    cursor_shape = SimpleCursorShapeConfig(CursorShape.BLINKING_BEAM)
    if cli_args and cli_args.vi:
        print("vim motion mode enabled.")
        vi_mode = True
        cursor_shape = ModalCursorShapeConfig()

    next_agent_spec_to_run: Optional[AgentSpecification] = agent_specifications[0]

    while next_agent_spec_to_run:
        current_agent_spec = next_agent_spec_to_run
        print(f"\nInitializing agent: {current_agent_spec.name} ({current_agent_spec.description})")

        active_mcp_servers = []
        for server_name in current_agent_spec.mcp_servers:
            server_instance = ALL_MCP_SERVERS.get(server_name)
            if server_instance:
                active_mcp_servers.append(server_instance)
            else:
                print(f"Warning: MCP Server '{server_name}' defined in agent spec '{current_agent_spec.name}' but not found in ALL_MCP_SERVERS.")

        agent = Agent(
            model=current_agent_spec.llm_model_name,
            base_url=current_agent_spec.base_url,
            instrument=True,
            mcp_servers=active_mcp_servers,
            system_prompt=current_agent_spec.system_prompt,
        )

        message_history = []
        history = InMemoryHistory()
        session = PromptSession(history=history, vi_mode=vi_mode, cursor=cursor_shape)

        async with agent.run_mcp_servers():
            print(f"Agent '{current_agent_spec.name}' started.")
            print("Type '/reset' to clear history, '/list-agents' to see available agents,")
            print("'/use-agent <agentname>' to switch, '/edit' for multi-line input, or '/exit' to quit.")

            while True:  # Inner loop for prompts with the current agent
                try:
                    user_input = (
                        await session.prompt_async(f"\n({current_agent_spec.name}) > ", enable_open_in_editor=True)
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting...")
                    next_agent_spec_to_run = None  # Signal to exit outer loop
                    break  # Exit inner_loop

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    command_parts = user_input[1:].split(" ", 1)
                    command = command_parts[0].lower()
                    cmd_args = command_parts[1] if len(command_parts) > 1 else None

                    if command == "exit":
                        print("Exiting...")
                        next_agent_spec_to_run = None  # Signal to exit outer loop
                        break  # Exit inner_loop

                    elif command == "reset":
                        message_history = []
                        print("Message history cleared.")
                        continue

                    elif command == "edit":
                        session.default_buffer.reset()
                        session.default_buffer.open_in_editor()
                        continue

                    elif command == "toggle-privacy":
                        private_mode = not private_mode
                        if private_mode:
                            os.environ["LLM_AND_ME_PRIVATE_MODE"] = "1"
                            print("Private mode enabled. Tool outputs may be saved locally instead of displayed.")
                            if "**Private mode disabled**" in message_history:
                                message_history.remove("**Private mode disabled**")
                            if "**Private mode enabled**" not in message_history:
                                message_history.append("**Private mode enabled**")
                        else:
                            os.environ.pop("LLM_AND_ME_PRIVATE_MODE", None)
                            print("Private mode disabled.")
                            if "**Private mode enabled**" in message_history:
                                message_history.remove("**Private mode enabled**")
                            if "**Private mode disabled**" not in message_history:
                                message_history.append("**Private mode disabled**")
                        continue

                    elif command == "list-agents":
                        print("Available agents:")
                        for spec in agent_specifications:
                            print(f"- {spec.name}: {spec.description}")
                        continue

                    elif command == "use-agent":
                        if not cmd_args:
                            print("Usage: /use-agent <agentname>")
                            continue

                        agent_name_to_switch = cmd_args.strip()
                        found_spec = next((s for s in agent_specifications if s.name == agent_name_to_switch), None)

                        if not found_spec:
                            print(f"Agent '{agent_name_to_switch}' not found. Use '/list-agents' to see available agents.")
                            continue

                        if found_spec.name == current_agent_spec.name:
                            print(f"Agent '{found_spec.name}' is already active.")
                            continue

                        print(f"Switching to agent: {found_spec.name}...")
                        next_agent_spec_to_run = found_spec
                        break  # Exit inner_loop to switch agent in outer_loop
                    else:
                        print(f"Unknown command: {user_input}")
                        continue
                
                if agent is None: # Should ideally not happen
                    print("Error: Agent not initialized. Please restart.")
                    next_agent_spec_to_run = None
                    break

                result = await agent.run(user_input, message_history=message_history)
                print(f"\n{result.output}")
                message_history.extend(result.new_messages())
            # Inner loop ended
            if not next_agent_spec_to_run: # If inner loop broke due to /exit or Ctrl+C
                break # Exit outer_loop (async with agent.run_mcp_servers())
        # async with ended
        if not next_agent_spec_to_run: # If outer_loop should terminate
            break
    # Outer while loop ended
    print("Agent application terminated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LLM and Me agent.")
    parser.add_argument(
        "--vi", action="store_true", help="Enable Vi key bindings for input."
    )
    # Use parse_known_args if running directly, in case other args exist
    cli_args, _ = parser.parse_known_args()

    asyncio.run(main(cli_args))
