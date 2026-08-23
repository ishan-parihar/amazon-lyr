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

## Tools (10)

| Tool | Description |
|------|-------------|
| `search_products` | Search with department/price/rating filters |
| `get_product` | Full details by ASIN (price, rating, features, specs) |
| `compare_products` | Compare up to 5 ASINs side-by-side |
| `get_reviews` | Reviews with star filter + sort (recent/helpful) |
| `add_to_cart` | Add an item (needs full session) |
| `view_cart` | Cart contents + per-item delete keys |
| `remove_from_cart` | Remove item by key |
| `get_wishlist` | List wishlist items |
| `get_orders` | Order history with status filters |
| `get_session_status` | Check auth state (none/degraded/reads_only/full) |

## Authentication

```bash
# Browser extraction (needs obscura extra)
uv sync --extra obscura && amazon-lyr login --browser chrome

# Or JSON file export
amazon-lyr login --cookies-file cookies.json

# Check status
amazon-lyr status
```

Reads need at-main; cart/wishlist/orders also need session-id + ubid-main.

## Notes

- Amazon serves CAPTCHAs aggressively. On `CaptchaError`, wait a few minutes
  or refresh the session in your browser, then re-import cookies.
- No auto-checkout by design — purchases stay human-approved.
