"""Map internal exceptions to agent-friendly tool errors."""

from __future__ import annotations

from typing import NoReturn

from amazon_lyr.exceptions import AmazonError, CaptchaError, SessionExpiredError
from amazon_lyr.logging_config import logger

_HINTS: dict[type[Exception], str] = {
    SessionExpiredError: "Run `amazon-lyr --login` to import fresh browser cookies.",
    CaptchaError: (
        "Amazon flagged this request as automated. Wait a few minutes, then try again; "
        "if it persists, log in to Amazon in your browser once so the session looks human."
    ),
}


def handle_api_error(e: Exception) -> NoReturn:
    """Log the failure and re-raise with a hint attached for the calling agent."""
    hint = _HINTS.get(type(e))
    if isinstance(e, AmazonError):
        msg = f"{e}" + (f" Hint: {hint}" if hint else "")
        logger.warning("Tool failed: %s", msg)
        raise RuntimeError(msg) from e
    if isinstance(e, ValueError):
        # Agent-supplied input problems are expected, not "unexpected".
        logger.warning("Bad tool input: %s", e)
        raise RuntimeError(str(e)) from e
    logger.exception("Unexpected tool failure")
    raise RuntimeError(f"Unexpected error: {e}") from e
