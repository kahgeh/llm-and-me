from fastapi_mcp import MCPToolServer
from .newrelic_tools import get_application_metrics
from .newrelic_tools.get_apm_entity_by_tag import get_apm_entities_by_component_tag

# Instantiate the server
server = MCPToolServer(
    title="New Relic MCP Server",
    description="MCP server for New Relic tools.",
    version="0.1.0",
)

# Add tools to the server
# The tool's name, title, description, input_model, and output_model
# will be inferred by fastapi-mcp from the function's properties.
server.add_tool(get_application_metrics)
server.add_tool(get_apm_entities_by_component_tag)

def main():
    server.run()

if __name__ == "__main__":
    main()
