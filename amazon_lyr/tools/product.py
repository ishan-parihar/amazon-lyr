from fastmcp import FastMCP

from amazon_lyr.dependencies import get_amazon_client
from amazon_lyr.error_handler import handle_api_error


def register_product_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def get_product(asin: str) -> dict:
        """Get full product details by ASIN: title, brand, price, list price, rating,
        review count, availability, buy-box seller, features, spec details, images."""
        try:
            client = get_amazon_client()
            return await client.get_product(asin)
        except Exception as e:
            handle_api_error(e)

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def compare_products(asins: list[str]) -> dict:
        """Compare up to 5 products side-by-side on title, price, rating, and availability."""
        if not 1 <= len(asins) <= 5:
            raise ValueError("Provide between 1 and 5 ASINs")
        try:
            client = get_amazon_client()
            products = [await client.get_product(a) for a in asins]
            return {
                "comparison": [
                    {
                        "asin": p.get("asin"),
                        "title": p.get("title"),
                        "price": p.get("price_value"),
                        "rating": p.get("rating"),
                        "reviews_count": p.get("reviews_count"),
                        "availability": p.get("availability"),
                    }
                    for p in products
                ]
            }
        except Exception as e:
            handle_api_error(e)
