import datetime

from fastmcp import FastMCP


def get_current_utc_datetime_iso() -> str:
    """
    Returns the current UTC datetime in ISO8601 format, using 'Z' for UTC.
    e.g. 2023-10-27T10:30:00Z or 2023-10-27T10:30:00.123456Z
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # isoformat() on a timezone-aware datetime includes the offset.
    # For UTC, this is +00:00. We replace it with 'Z'.
    return now_utc.isoformat().replace("+00:00", "Z")


def main():
    mcp = FastMCP("Datetime service", description="Datetime Tools MCP Server")
    mcp.add_tool(get_current_utc_datetime_iso)
    mcp.run()


if __name__ == "__main__":
    main()
