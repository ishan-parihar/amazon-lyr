from contextlib import asynccontextmanager

from fastmcp import FastMCP

from amazon_lyr import dependencies
from amazon_lyr.logging_config import logger
from amazon_lyr.tools.order_mgmt import register_order_mgmt_tools
from amazon_lyr.tools.product import register_product_tools
from amazon_lyr.tools.reviews import register_review_tools
from amazon_lyr.tools.search import register_search_tools
from amazon_lyr.tools.session import register_session_tools
from amazon_lyr.tools.shopping import (
    register_cart_tools,
    register_order_tools,
    register_wishlist_tools,
)


@asynccontextmanager
async def _lifespan(_: FastMCP):
    """Close the shared HTTP session cleanly on server shutdown."""
    yield
    client = dependencies._client
    if client is not None:
        await client.close()
        dependencies._client = None
        logger.info("amazon-lyr HTTP session closed")


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        "amazon-lyr",
        instructions=(
            "Amazon research & shopping via browser cookies. Research: search_products, "
            "get_product, get_reviews, review_insights, search_in_reviews, compare_products. "
            "Shopping: add_to_cart/view_cart/remove_from_cart. Orders: get_orders, "
            "get_order_details, track_shipment, list_returns; mutating initiate_return and "
            "cancel_order require full session cookies (`amazon-lyr --login`) and move real "
            "money — confirm with the user before calling them."
        ),
        lifespan=_lifespan,
    )

    # Reads first — the research surface.
    register_search_tools(mcp)
    register_product_tools(mcp)
    register_review_tools(mcp)
    # Shopping.
    register_cart_tools(mcp)
    register_wishlist_tools(mcp)
    # Order lifecycle (history + details/tracking/returns/cancellation).
    register_order_tools(mcp)
    register_order_mgmt_tools(mcp)
    # Session introspection.
    register_session_tools(mcp)

    logger.info("amazon-lyr MCP server created with all tools registered")
    return mcp
