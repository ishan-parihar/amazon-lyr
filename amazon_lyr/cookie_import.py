"""Cookie import: obscura-core browser extractor (optional) with JSON fallback.

Primary path is explicit JSON (`AMAZON_COOKIES` env var or `--login --cookies-file`),
which always works. Browser extraction uses obscura-core when the optional extra
is installed.
"""

from __future__ import annotations

from amazon_lyr.logging_config import logger

SUPPORTED_BROWSERS = ["chrome", "brave", "firefox", "edge", "zen"]


def import_from_browser(browser: str | None = None) -> dict[str, str]:
    """Extract Amazon cookies from an installed browser via obscura-core.

    Raises ImportError with setup instructions if obscura-core is not installed.
    """
    try:
        from obscura_core import BrowserCookieExtractor  # noqa: PLC0415
    except ImportError as e:
        raise ImportError(
            "Browser extraction needs the optional obscura extra. Install with "
            "`uv sync --extra obscura` or `pip install 'amazon-lyr[obscura]'`. "
            "Alternatively export cookies as JSON and run "
            "`amazon-lyr --login --cookies-file cookies.json`."
        ) from e

    target = browser or "chrome"
    logger.info("Extracting amazon.com cookies from %s…", target)
    cookies = BrowserCookieExtractor.extract(domain="amazon.com", browser=target, validate=False)
    return {k: v for k, v in cookies.items() if v}
