# System Overview

The platform is a monorepo containing three concentric layers:

- Tool layer: individual scripts/functions wrapped as FastMCP tools.
- MCP Service layer: each tool becomes a FastAPI route; combined into my-ai-and-me‑server.
- Agent layer: long‑running processes (or CLI) that call the MCP server.

# Technology Stack

| Component                            | Choice                                                  | Notes |
| ------------------------------------ | ------------------------------------------------------- | ----- |
| Agent runtime                        | Python                                                  |       |
| Agent framework                      | Pydantic AI                                             |       |
| Quick tool prototype with llm access | [llm](https://github.com/simonw/llm) + prompt templates |

## Module Design

/tools – small focus tools built with python, so that it can easily use pydantic AI Agent class and also to easily be able to evolve to an MCP server or be included part of an MCP server using FastMCP.

/templates – prompt templates used with llm cli, typically to build out command line tools or for prototyping tools that need an llm

/agents – package for agent logic (start with CodingAgent).
