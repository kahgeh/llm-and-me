# Tasks for Implementing Agent Switching

## 1. Define Agent Specification
- **Task:** Define a Pydantic model or a dictionary structure for an "Agent Specification".
  - `name`: str (unique identifier for the agent)
  - `description`: str (user-friendly description)
  - `llm_model_name`: str (e.g., "gpt-4", "claude-3-opus-20240229")
  - `base_url`: Optional[str] (for local LLM models)
  - `mcp_servers`: List[str] (list of MCP server identifiers/names that this agent uses)
- **Task:** Implement loading of agent specifications from a TOML configuration file (e.g., `agents.toml`). This file will contain an array of agent specifications, adhering to the defined Pydantic model.
  - Example (illustrating the data structure for the list of agents, which will be loaded from `agents.toml`):
    ```python
    AGENT_SPECIFICATIONS = [
        {
            "name": "Engineering Assitant",
            "description": "A general-purpose coding assistant.",
            "llm_model_name": "gpt-4o",
            "base_url": None,
            "mcp_servers":[ "markdown_server",
                            "macos_system_server",
                            "custom_git_server",
                            "main_git_server",
                            "cortex_server",
                            "newrelic_server",
                            "openapi_server",
                            "filesystem_server",
                            "fetch_server",
                            "search_server",
                            "sqlite_server",
                            "processing_history_server",
                            "datetime_server",
                            "rag_crawler_server" ]
 
        }
    ]
    ```

## 2. Implement `/list-agents` Command
- **Task:** Modify the agent's command processing logic to recognize `/list-agents`.
- **Task:** When `/list-agents` is invoked:
    - Iterate through the `AGENT_SPECIFICATIONS`.
    - For each agent, extract its `name` and `description`.
    - Format and return this list to the user.
    - Example output:
      ```
      Available agents:
      - general_coder: A general-purpose coding assistant.
      - newrelic_expert: An assistant specialized in New Relic tasks.
      ```

## 3. Implement `/use-agent <agentname>` Command
- **Task:** Modify the agent's command processing logic to recognize `/use-agent <agentname>`.
- **Task:** When `/use-agent <agentname>` is invoked:
    - Find the agent specification matching `<agentname>` in `AGENT_SPECIFICATIONS`.
    - If not found, return an error message to the user.
    - If found:
        - **Sub-task:** Update the currently active agent configuration. This will likely involve:
            - Storing the current agent's name/specification.
            - Re-initializing the `Agent` instance  with the new:
                - LLM model .
                - Set of MCP servers (`mcp_servers`). This might involve stopping existing MCP servers (if they are not shared or needed by the new agent) and starting new ones.
        - **Sub-task:** Persist the choice of the active agent (e.g., in a state file or environment variable) so it's remembered across sessions (optional, for later improvement).
        - Return a confirmation message to the user (e.g., "Switched to agent: newrelic_expert").

## 4. Agent State Management
- **Task:** Determine where and how the list of `AGENT_SPECIFICATIONS` will be stored and accessed. (e.g., a dedicated `config.py` or within `packages/agents/src/llm_and_me_agents/__init__.py`).
- **Task:** Determine how the currently active agent's specification is tracked within the application.
- **Task:** Refactor `packages/agents/src/llm_and_me_agents/__init__.py`:
    - **Sub-task:** Modify `select_model()` (or its callers) to ensure the LLM model (`llm_model_name` and `base_url`) is taken **exclusively** from the active agent's specification. Deprecate any existing mechanisms (e.g., command-line arguments for model selection, global defaults not tied to an agent spec) that allow specifying the LLM model independently of the selected agent. The primary role of `select_model()` will be to return the model name configured in the current agent's specification.
    - **Sub-task:** Modify the `Agent` instantiation. The `model` and `mcp_servers` arguments will come from the first agent in the array of agents 

## 5. MCP Server Management
- **Task:** Review how MCP servers are defined and initialized in `packages/agents/src/llm_and_me_agents/__init__.py`.
- **Task:** Develop a mechanism to selectively activate/deactivate MCP servers based on the `mcp_servers` list in the chosen agent's specification.
    - This might involve creating a dictionary of all available MCP server initializers/configurations.
    - When switching agents, the `Agent` would be configured with only the MCP servers listed in the new agent's spec.
    - Ensure that MCP servers are properly started and stopped if they are managed as separate processes (like `MCPServerStdio` or `MCPServerHTTP`).

