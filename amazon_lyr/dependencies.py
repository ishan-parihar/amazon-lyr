"""Shared client accessor for tools. One client per process; cookies loaded lazily."""

from __future__ import annotations

from amazon_lyr.exceptions import AuthenticationError
from amazon_lyr.scraping.api_client import AmazonClient
from amazon_lyr.session_state import load_cookies

_client: AmazonClient | None = None


def get_amazon_client() -> AmazonClient:
    global _client
    if _client is None:
        cookies = load_cookies()
        if not any(c in cookies for c in ("at-main",)):
            raise AuthenticationError(
                "No Amazon login cookies found. Run `amazon-lyr --login` first "
                "(or set the AMAZON_COOKIES env var with your session JSON)."
            )
        _client = AmazonClient(cookies=cookies)
    return _client


def reset_client() -> None:
    """Drop the cached client (after cookie re-import)."""
    global _client
    _client = None
