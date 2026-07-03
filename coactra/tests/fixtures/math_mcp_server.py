import os

os.environ.setdefault("FASTMCP_LOG_LEVEL", "ERROR")
os.environ.setdefault("FASTMCP_SHOW_SERVER_BANNER", "false")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("coactra-math")


@mcp.tool()
async def add_numbers(a: int, b: int) -> int:
    return a + b


if __name__ == "__main__":
    mcp.run("stdio")
