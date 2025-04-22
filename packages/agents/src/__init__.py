import os
import sys

from dotenv import load_dotenv
from logfire import configure
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

load_dotenv()
configure(token=os.getenv("LOGFIRE_TOKEN"))
print(sys.executable)

macos_system_server = MCPServerStdio(
    "uv",
    args=[
        "run",
        "packages/tools/src/macos_system_mcp_server.py",
    ],
)

markdown_server = MCPServerStdio(
    "uv",
    args=[
        "run",
        "packages/tools/src/markdown_mcp_server.py",
    ],
)

git_server = MCPServerStdio(
    "uv",
    args=[
        "run",
        "packages/tools/src/git_mcp_server.py",
    ],
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
    mcp_servers=[markdown_server, macos_system_server, git_server],
    system_prompt="You are a software engineering assistant, using en-AU locale. Do not try more than 3 times. If the user asks for json, return plain json text, nothing more",
)


async def main():
    async with agent.run_mcp_servers():
        result = await agent.run("hello")
        while True:
            print(f"\n{result.output}")
            user_input = input("\n> ")
            if user_input.lower() == "exit":
                break
            result = await agent.run(user_input, message_history=result.new_messages())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
# This file makes the 'src' directory under 'agents' a Python package.
