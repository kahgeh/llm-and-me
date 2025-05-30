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
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from .initialisations import initialise_mcp_servers, load_agent_specifications
from .models import AgentSpecification

load_dotenv()


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

public_message_history_snapshot: List = [] # Snapshot for public agent history

async def main(cli_args: argparse.Namespace):
    """
    Main async function for the agent.

    Args:
        cli_args: Optional pre-parsed command-line arguments.
                  If None, arguments will be parsed internally.
    """
    global current_agent_spec
    global active_mcp_servers
    global agent
    global public_message_history_snapshot

    vi_mode = False
    cursor_shape = SimpleCursorShapeConfig(CursorShape.BLINKING_BEAM)
    if cli_args and cli_args.vi:
        print("vim motion mode enabled.")
        vi_mode = True
        cursor_shape = ModalCursorShapeConfig()

    next_agent_spec_to_run: Optional[AgentSpecification] = agent_specifications[0]
    message_history: List = [] # Initialize message history for the first agent session

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

        print(f"current_agent_spec={current_agent_spec}")
        if current_agent_spec.base_url:
            # If base_url is provided, assume it's for an OpenAI-compatible provider
            openai_compatible_model= OpenAIModel( 
                model_name=current_agent_spec.llm_model_name,
                provider=OpenAIProvider(
                base_url=current_agent_spec.base_url,
            ))
            agent = Agent(
                openai_compatible_model,
                instrument=True,
                mcp_servers=active_mcp_servers,
                instructions=current_agent_spec.instructions,
            )
        else:
            # Default behavior if no base_url is specified
            agent = Agent(
                model=current_agent_spec.llm_model_name,
                instrument=True,
                mcp_servers=active_mcp_servers,
                instructions=current_agent_spec.instructions,
            )

        # message_history is now managed by the switching logic / initial setup
        history = InMemoryHistory()
        # Populate history for prompt_toolkit if message_history has content (e.g., after restoring)
        for msg_idx, msg_content in enumerate(message_history):
            # Assuming user messages are at even indices and AI at odd, or just add all for context
            # This might need refinement based on how message_history is structured by Pydantic-AI
            if isinstance(msg_content, str): # Basic check
                 history.append_string(msg_content)
            elif hasattr(msg_content, 'content') and isinstance(msg_content.content, str): # Pydantic-AI Message
                 history.append_string(msg_content.content)


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
                        
                        print(f"Switching from agent '{current_agent_spec.name}' to '{found_spec.name}'...")

                        prev_is_public = current_agent_spec.data_classification == "public"
                        next_is_public = found_spec.data_classification == "public"
                        
                        # By default, retain the current message history for the next agent.
                        # This will be overridden only when switching from a Non-Public to a Public agent.
                        new_message_history_for_next_agent: List = list(message_history)

                        if prev_is_public and not next_is_public:
                            # Switching from Public to Non-Public:
                            # Snapshot the public history. The current message history is retained.
                            public_message_history_snapshot = list(message_history)
                            print("Snapshotted public history. Current history retained for non-public session.")
                        elif not prev_is_public and next_is_public:
                            # Switching from Non-Public to Public:
                            # Replace current non-public history with the previously snapshotted public history.
                            new_message_history_for_next_agent = list(public_message_history_snapshot)
                            print("Reloading public history snapshot for public session.")
                        # else: # Public -> Public or Non-Public -> Non-Public
                            # History is retained (due to default initialization of new_message_history_for_next_agent).
                            # No specific message is printed for these transitions to reduce verbosity.
                        
                        message_history = new_message_history_for_next_agent # Update history for the next agent
                        
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
