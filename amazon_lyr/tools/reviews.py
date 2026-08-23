from typing import Literal

from fastmcp import FastMCP

from amazon_lyr.dependencies import get_amazon_client
from amazon_lyr.error_handler import handle_api_error


def register_review_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def get_reviews(
        asin: str,
        filter_by_star: Literal[
            "five_stars",
            "four_stars",
            "three_stars",
            "two_stars",
            "one_star",
            "positive",
            "critical",
        ]
        | None = None,
        sort_by: Literal["recent", "helpful"] = "helpful",
        page: int = 1,
    ) -> dict:
        """Get customer reviews for a product with star filtering and sort options."""
        try:
            client = get_amazon_client()
            return await client.get_reviews(
                asin, filter_by_star=filter_by_star, sort_by=sort_by, page=page
            )
        except Exception as e:
            handle_api_error(e)
