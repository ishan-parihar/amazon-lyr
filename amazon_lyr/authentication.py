"""Session validation against stored cookies."""

from __future__ import annotations

from amazon_lyr.constants import REQUIRED_COOKIES, WRITE_COOKIES
from amazon_lyr.session_state import load_cookies


def validate_session() -> bool:
    """True if at least one login cookie is present."""
    cookies = load_cookies()
    return any(c in cookies for c in REQUIRED_COOKIES)


def validate_write_session() -> bool:
    """Writes (cart/wishlist) need at-main plus session/ubid context cookies."""
    cookies = load_cookies()
    has_login = any(c in cookies for c in REQUIRED_COOKIES)
    has_context = any(c in cookies for c in WRITE_COOKIES)
    return has_login and has_context


def get_auth_status() -> dict:
    cookies = load_cookies()
    if not cookies:
        return {"authenticated": False, "mode": "none", "cookies_count": 0}
    has_login = any(c in cookies for c in REQUIRED_COOKIES)
    has_context = any(c in cookies for c in WRITE_COOKIES)
    mode = "full" if has_login and has_context else "reads_only" if has_login else "degraded"
    return {
        "authenticated": has_login,
        "mode": mode,
        "cookies_count": len(cookies),
        "has_at_main": "at-main" in cookies,
        "has_session_id": "session-id" in cookies,
        "has_ubid_main": "ubid-main" in cookies,
    }
