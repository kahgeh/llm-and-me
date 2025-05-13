from fastmcp import FastMCP

from .newrelic_tools.api_key_selector import get_sorted_newrelic_apikey_accounts
from .newrelic_tools.get_apm_entity_by_tag import get_prod_apm_entities_by_component_tag
from .newrelic_tools.get_application_metrics import get_application_metrics
from .newrelic_tools.save_application_metrics_to_sqlite import (
    save_application_metrics_to_sqlite,
)


def main():
    mcp = FastMCP("New Relic MCP Server", description="MCP server for New Relic tools.")

    mcp.add_tool(get_application_metrics)
    mcp.add_tool(get_prod_apm_entities_by_component_tag)
    mcp.add_tool(save_application_metrics_to_sqlite)
    mcp.add_tool(get_sorted_newrelic_apikey_accounts)
    mcp.run()


if __name__ == "__main__":
    print(f"Attempting to start Newrelic MCP server ({__file__})...")
    main()
