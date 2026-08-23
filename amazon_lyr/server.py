from fastmcp import FastMCP

from amazon_lyr.logging_config import logger
from amazon_lyr.tools.product import register_product_tools
from amazon_lyr.tools.reviews import register_review_tools
from amazon_lyr.tools.search import register_search_tools
from amazon_lyr.tools.session import register_session_tools
from amazon_lyr.tools.shopping import (
    register_cart_tools,
    register_order_tools,
    register_wishlist_tools,
)


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        "amazon-lyr",
        instructions=(
            "Amazon research & shopping via browser cookies. Read tools (search_products, "
            "get_product, get_reviews, compare_products) work with login cookies; write "
            "tools (cart/wishlist/orders) need full session cookies via `amazon-lyr --login`."
        ),
    )

    # Reads first — the research surface.
    register_search_tools(mcp)
    register_product_tools(mcp)
    register_review_tools(mcp)
    # Writes + account.
    register_cart_tools(mcp)
    register_wishlist_tools(mcp)
    register_order_tools(mcp)
    register_session_tools(mcp)

    logger.info("amazon-lyr MCP server created with all tools registered")
    return mcp
