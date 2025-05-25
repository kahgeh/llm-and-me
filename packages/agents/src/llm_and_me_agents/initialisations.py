import os
import sys
from typing import List
import tomllib # Changed from toml

from logfire import configure
from pydantic_ai.mcp import MCPServerHTTP, MCPServerStdio

from .models import AgentSpecification


def load_agent_specifications(file_path: str = "packages/agents/agents.toml") -> List[AgentSpecification]:
    try:
        with open(file_path, "rb") as f: # Changed to "rb" for tomllib
            data = tomllib.load(f) # Changed from toml.load(f)
        # Validate and parse agent specifications
        specs_data = data.get("agents", [])
        print(f"Loaded {len(specs_data)} agent specifications from '{file_path}'.")
        print(f"Agent specifications: {specs_data}")
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

# --- MCP Server Definitions and Mapping ---
def initialise_mcp_servers() -> dict:
    """initialises and returns a dictionary of all MCP servers."""
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

    return {
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
