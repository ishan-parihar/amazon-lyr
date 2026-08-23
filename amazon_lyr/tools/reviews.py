from typing import Literal

from fastmcp import FastMCP

from amazon_lyr.dependencies import get_amazon_client
from amazon_lyr.error_handler import handle_api_error


def register_review_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def get_reviews(
        asin: str,
        filter_by_star: Literal[
            "five_stars", "four_stars", "three_stars", "two_stars", "one_star", "positive", "critical"
        ]
        | None = None,
        sort_by: Literal["recent", "helpful"] = "helpful",
        page: int = 1,
    ) -> dict:
        """Get customer reviews for a product with star filtering and sort options."""
        try:
            client = get_amazon_client()
            return await client.get_reviews(asin, filter_by_star=filter_by_star, sort_by=sort_by, page=page)
        except Exception as e:
            handle_api_error(e)

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def review_insights(asin: str, max_pages: int = 3) -> dict:
        """Aggregate review research for a product (up to max_pages of reviews):
        star distribution, computed average, verified-purchase %, top keyword
        themes overall AND specifically in critical (1-3★) reviews — the fastest
        way to learn what actually breaks or disappoints buyers."""
        try:
            client = get_amazon_client()
            return await client.review_insights(asin, max_pages=max_pages)
        except Exception as e:
            handle_api_error(e)

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def search_in_reviews(asin: str, query: str, max_pages: int = 3) -> dict:
        """Scan up to max_pages of reviews and return only those mentioning
        `query` (e.g. 'battery', 'return', 'broke'). Includes match count,
        average rating of matches, and the matched reviews themselves."""
        try:
            client = get_amazon_client()
            return await client.search_in_reviews(asin, query, max_pages=max_pages)
        except Exception as e:
            handle_api_error(e)
