"""Order lifecycle tools: details, tracking, returns/refunds, cancellation.

Mutating tools are deliberately MCP-only (no raw CLI flags): returns and
cancellations move real money and deserve conversational confirmation.
"""

from typing import Literal

from fastmcp import FastMCP

from amazon_lyr.dependencies import get_amazon_client
from amazon_lyr.error_handler import handle_api_error
from amazon_lyr.tools.shopping import _require_write_session

RETURN_REASON = Literal[
    "no-longer-needed",
    "defective",
    "damaged",
    "wrong-item",
    "missing-parts",
    "better-price",
    "not-as-described",
    "arrived-too-late",
    "size-fit-issue",
    "accidental-order",
]


def register_order_mgmt_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    async def get_order_details(order_id: str) -> dict:
        """Full detail for one order: items+prices, totals, payment method,
        ship-to address, status, tracking numbers, invoice URL, cancel link."""
        try:
            client = get_amazon_client()
            return await client.get_order_details(order_id)
        except Exception as e:
            handle_api_error(e)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def track_shipment(order_id: str) -> dict:
        """Shipment status + tracking numbers for an order."""
        try:
            client = get_amazon_client()
            return await client.track_shipment(order_id)
        except Exception as e:
            handle_api_error(e)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def list_returns() -> dict:
        """List returns/refunds from the Returns Center: order ids, items,
        statuses (Refund issued / Return received / …), refund amounts."""
        try:
            client = get_amazon_client()
            return await client.list_returns()
        except Exception as e:
            handle_api_error(e)

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False})
    async def initiate_return(
        order_id: str,
        reason: RETURN_REASON = "no-longer-needed",
        asin_hint: str | None = None,
    ) -> dict:
        """Start a return/refund for an order. Multi-item orders: set asin_hint
        to the ASIN (or part of the item name) to pick the right line. Reason is
        a friendly code like 'defective' or 'wrong-item'. Verify afterwards with
        list_returns; if Amazon demands an extra step, finish in the Returns Center."""
        try:
            _require_write_session()
            client = get_amazon_client()
            return await client.initiate_return(order_id, asin=asin_hint, reason=reason)
        except Exception as e:
            handle_api_error(e)

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False})
    async def cancel_order(order_id: str) -> dict:
        """Cancel an unshipped order entirely. Only works before shipment;
        check get_order_details first. Verify with get_orders afterwards."""
        try:
            _require_write_session()
            client = get_amazon_client()
            return await client.cancel_order(order_id)
        except Exception as e:
            handle_api_error(e)
