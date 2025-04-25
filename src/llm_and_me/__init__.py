import argparse
import asyncio
import sys

try:
    from llm_and_me_agents import main as agent_main
except ImportError as e:
    print(f"Error importing agent main function: {e}", file=sys.stderr)
    print(
        "Ensure the agent package is structured correctly and dependencies are installed.",
        file=sys.stderr,
    )
    sys.exit(1)


def run_agent():
    """Synchronous wrapper to run the main async agent function."""
    parser = argparse.ArgumentParser(
        description="Run the LLM and Me agent.",
        # Allow unknown args to be passed to the agent's main parser
        # This prevents conflicts if both parsers define the same arg,
        # though currently only --vi is defined in the agent.
        # If more args are added, consider a more robust sharing mechanism.
        allow_abbrev=False,
    )
    parser.add_argument(
        "--vi", action="store_true", help="Enable Vi key bindings for input."
    )
    # Parse known args, leave the rest for the agent's parser if needed
    args, unknown = parser.parse_known_args()

    try:
        # Pass the parsed args object to the agent's main function
        asyncio.run(agent_main(args))
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    run_agent()
