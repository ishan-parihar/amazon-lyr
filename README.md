<!-- T2I HERO SPEC — Subject: an Amazon shopping research engine — product cards (orange smile-arrow motif) flowing through a curl_cffi pipeline into structured JSON for agents; a CAPTCHA wall as a gate on one path. Composition: search grid → funnel → JSON output, cart icon at the end. Palette: amazon orange #ff9900 → deep navy → off-white cards. Style: dark flat vector, smile-arrow motif, no text. 16:9. -->

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-2b6cb0?style=flat&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/license-MIT-059669?style=flat" alt="MIT">
  <img src="https://img.shields.io/badge/mcp-1.0-c026d3?style=flat&logo=modelcontextprotocol&logoColor=white" alt="MCP 1.0">
</p>

<h1 align="center">amazon-lyr</h1>

<p align="center">
  <strong>An Amazon research &amp; shopping MCP server for AI agents</strong> —
  search products, dig into details and reviews, manage the cart, and track
  orders through your own logged-in browser session. No PA-API keys.
</p>

<p align="center">
  <code>curl -sSL https://raw.githubusercontent.com/ishan-parihar/amazon-lyr/main/install.sh | bash</code>
</p>

---

## What it is

| Layer | Description |
|-------|-------------|
| **Core** | `AmazonClient` — async, curl_cffi Chrome impersonation, captcha-aware |
| **MCP Server** | 17 tools: research, reviews analytics, cart, orders, returns, cancellation |
| **CLI** | `amazon-lyr search`, `amazon-lyr product B0…`, `order`, `track`, `returns` (TOON output) |

---

## Quick start

```bash
# Install (or: uv sync --extra dev)
curl -sSL https://raw.githubusercontent.com/ishan-parihar/amazon-lyr/main/install.sh | bash

# Auth: import cookies from your browser (one-time)
amazon-lyr login --browser chrome        # needs: uv sync --extra obscura
amazon-lyr login --cookies-file cookies.json   # or explicit JSON export

# Research from the shell
amazon-lyr search "mechanical keyboard" --json
amazon-lyr product B08N5WRWNW

# MCP server for agents
amazon-lyr serve
```

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

---

## MCP Tools (17)

| Category | Tools |
|----------|-------|
| **Search** | `search_products` (department, price range, min-rating filters) |
| **Product** | `get_product` (price, rating, features, specs), `compare_products` (up to 5 ASINs) |
| **Reviews** | `get_reviews`, `review_insights`, `search_in_reviews` |
| **Cart** | `add_to_cart`, `view_cart`, `remove_from_cart` |
| **Wishlist** | `get_wishlist` |
| **Orders** | `get_orders`, `get_order_details`, `track_shipment` |
| **Returns** | `list_returns`, `initiate_return` (friendly reason codes) |
| **Danger zone** | `cancel_order` — destructive, user-confirmed only |
| **Session** | `get_session_status` |

Reads work with login cookies (`at-main`). Cart/wishlist/orders/returns/cancel
also want `session-id` + `ubid-main` — the login flow imports whatever the
browser has.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     amazon_lyr                              │
├──────────┬──────────┬──────────────┬───────────────────────┤
│  Auth    │  Client  │   Parsers    │   FastMCP Tools       │
│ (cookies)│(curl_cffi│  (bs4 HTML → │   (17 tools,          │
│ obscura/ │  chrome, │  normalized  │   readOnly/destructive│
│ JSON     │  captcha │  dicts)      │   annotations)        │
│          │  aware)  │              │                       │
└──────────┴──────────┴──────────────┴───────────────────────┘
```

Bot-wall handling is first-class: CAPTCHA pages raise `CaptchaError`,
sign-in redirects raise `SessionExpiredError`, and both carry agent-facing
hints via the shared error handler. Silent soft-throttles are flagged via
`possibly_throttled` so agents retry instead of trusting empty grids.

---

## Example: Agent researching a purchase

```
1. search_products("noise cancelling headphones", max_price=300, min_rating=4)
2. compare_products(["ASIN1", "ASIN2", "ASIN3"])
3. review_insights("ASIN2")                            # star spread + keyword themes
4. search_in_reviews("ASIN2", query="broke")           # what breaks?
5. add_to_cart("ASIN2", quantity=1)
6. get_orders()                                        # later: did it land?
7. get_order_details("111-2223334-5556667")            # totals + invoice
8. initiate_return("111-2223334-5556667", reason="defective", asin_hint="ASIN2")
9. list_returns()                                      # confirm refund status
```

Checkout stays human — no auto-buy by design, and `cancel_order` /
`initiate_return` move real money, so agents must confirm with the user first.

---

## Development

```bash
uv sync --extra dev
uv run ruff check . && uv run pytest -q
```

See [AGENTS.md](AGENTS.md) for architecture notes and release process.

## License

MIT © Ishan Parihar
