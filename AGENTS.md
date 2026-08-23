# AGENTS.md — Agent Developer Guide for amazon-lyr

## Project Overview

- **Project**: amazon-lyr — Amazon research & shopping MCP server + CLI (search, product details, reviews, cart, orders)
- **Language**: Python 3.11+
- **Package Manager**: uv
- **Repository**: https://github.com/ishan-parihar/amazon-lyr
- **Family**: part of the `-lyr` series (reddit-lyr, twitter-lyr, threads-lyr…) — browser-cookie auth, no official API keys

## Build, Lint, and Test Commands

```bash
uv sync --extra dev          # install deps
uv run ruff check .          # lint
uv run ruff format --check . # format check
uv run pytest -q             # tests (no live Amazon calls; fixtures only)
uv run amazon-lyr            # CLI home view
uv run amazon-lyr serve      # MCP server (stdio)
```

Run one test: `uv run pytest tests/test_parsers.py::test_parse_search -v`

## Code Style

- Line length 100; ruff rules E/F/I/B/UP (see pyproject)
- `from __future__ import annotations` at top of all modules
- snake_case functions, PascalCase classes, UPPER_SNAKE constants
- Custom exceptions in `exceptions.py`, base `AmazonError(RuntimeError)`
- Tools wrap client calls in `try/except → handle_api_error(e)` (returns NoReturn)
- Read tools annotated `{"readOnlyHint": True}`; destructive ones set `destructiveHint`

## Architecture

```
amazon_lyr/
├── cli_main.py        # argparse entry; subcommands; TOON default output
├── cli_actions.py     # command dispatch + TOON/JSON formatting
├── server.py          # create_mcp_server() — FastMCP assembly
├── dependencies.py    # singleton AmazonClient accessor
├── authentication.py  # validate_session / get_auth_status
├── cookie_import.py   # obscura-core extractor (optional extra) / JSON file
├── session_state.py   # cookie persistence (~/.config/amazon-lyr/cookies.json)
├── constants.py       # endpoints, captcha markers, retry policy
├── exceptions.py, error_handler.py, ratelimit.py, logging_config.py
├── scraping/
│   ├── api_client.py  # curl_cffi chrome impersonation; captcha/signin detection
│   └── parsers.py     # HTML → normalized dicts (bs4, defensive)
└── tools/
    ├── search.py, product.py, reviews.py   # reads (readOnlyHint=True)
    ├── shopping.py                          # cart/wishlist/orders
    └── session.py                           # auth status tool
```

Key invariants:

- `_check_page()` must raise `CaptchaError` on bot-wall markers and
  `SessionExpiredError` on `/ap/signin` redirects — never parse those pages.
- Parsers are defensive: missing selectors yield None/[], never raise.
- Writes (`cart-add`, `remove_from_cart`) gate on `validate_write_session()`.
- Tests never hit live Amazon — fixture HTML strings or FakeSession.

## Release Process

No CI release. Installs are source-based via `install.sh`; **pushing to main is the release**.

```bash
git checkout main && git pull
uv version --bump patch
uv run ruff check . && uv run pytest -q
git commit -m "chore(release): vX.Y.Z" && git push origin main
```

Conventional commits: `type(scope): subject` (<50 chars, imperative).
PRs: branch `feature/<short-desc>`, include model attribution, no squash.
