---
name: amazon-mcp
description: >
  Search Amazon, research products and reviews, manage the cart and track
  orders via MCP. Uses browser cookies and TLS fingerprinting — no PA-API
  keys required.
---

# Amazon MCP Skill

Amazon research & shopping for agents: search, product details, review
analysis, cart management, and order tracking through your own browser
session.

## Quick Start

```bash
# Import cookies from your browser (one-time)
amazon-lyr login --browser chrome

# Run the MCP server
amazon-lyr serve

# Or with HTTP transport
amazon-lyr serve --transport streamable-http --port 8000
```

## MCP Configuration

```json
{
  "mcpServers": {
    "amazon": {
      "command": "amazon-lyr",
      "args": ["serve"]
    }
  }
}
```

## Tools (21)

| Category | Tools |
|------|-------------|
| **Search** | `search_products` (department/price/rating filters) |
| **Product** | `get_product` (price, rating, features, specs), `compare_products` (up to 5 ASINs) |
| **Reviews** | `get_reviews`, `review_insights` (star distribution, verified %, keyword themes incl. critical reviews), `search_in_reviews` (keyword scan across pages) |
| **Cart** | `add_to_cart`, `view_cart`, `update_cart_quantity`, `remove_from_cart` (need full session) |
| **Wishlist** | `get_wishlist`, `add_to_wishlist` (idempotent) |
| **Orders** | `get_orders`, `get_order_details` (items/totals/payment/invoice), `track_shipment` |
| **Returns** | `list_returns`, `initiate_return` (reason codes like `defective`, `wrong-item`) |
| **Buying** | `checkout_preview` (safe walk-through), `place_order` — REQUIRES confirm='PLACE_ORDER' after explicit user approval |
| **Danger zone** | `cancel_order`, `place_order` — destructive/charges money; always confirm with the user first |
| **Session** | `get_session_status` |

## Authentication

```bash
# Browser extraction (needs obscura extra)
uv sync --extra obscura && amazon-lyr login --browser chrome

# Or JSON file export
amazon-lyr login --cookies-file cookies.json

# Check status
amazon-lyr status
```

Reads need at-main; cart/wishlist/orders/returns/cancel also need
session-id + ubid-main.

## Notes

- Amazon serves CAPTCHAs aggressively. On `CaptchaError`, wait a few minutes
  or refresh the session in your browser, then re-import cookies.
- Rapid successive calls get silent empty grids — responses carry
  `possibly_throttled: true` when that's suspected; back off and retry.
- The return wizard may demand an extra confirmation step; when it does,
  `initiate_return` reports `in_progress` with a manual fallback URL.
  Always verify outcomes with `list_returns`.
- No auto-checkout by design — purchases stay human-approved.
