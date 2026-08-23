from fastmcp import FastMCP

from amazon_lyr.authentication import get_auth_status
from amazon_lyr.error_handler import handle_api_error


def register_session_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    async def get_session_status() -> dict:
        """Check cookie/auth state: none, degraded (login only), reads_only, or full."""
        try:
            return get_auth_status()
        except Exception as e:
            handle_api_error(e)
