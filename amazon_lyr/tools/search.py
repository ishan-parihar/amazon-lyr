from typing import Literal

from fastmcp import FastMCP

from amazon_lyr.dependencies import get_amazon_client
from amazon_lyr.error_handler import handle_api_error


def register_search_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def search_products(
        query: str,
        department: str | None = None,  # e.g. "electronics", "books", "stripbooks"
        sort: Literal[
            "relevanceblends", "price-asc-rank", "price-desc-rank", "review-rank", "date-desc-rank"
        ]
        | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        min_rating: int | None = None,
        page: int = 1,
    ) -> dict:
        """Search Amazon products with filters (department, price range, min rating).

        Returns per item: asin, title, price, rating, ratings_count, image_url.
        Use get_product(asin) for full details on a result.
        """
        try:
            if not query.strip():
                raise ValueError("query must not be empty")
            client = get_amazon_client()
            return await client.search_products(
                query,
                department=department,
                sort=sort,
                price_min=price_min,
                price_max=price_max,
                min_rating=min_rating,
                page=max(1, page),
            )
        except Exception as e:
            handle_api_error(e)
