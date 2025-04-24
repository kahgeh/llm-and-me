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
    try:
        asyncio.run(agent_main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    run_agent()
