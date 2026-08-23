"""Cookie persistence: env var (inline JSON or file path) > stored file.

Storage location respects XDG_CONFIG_HOME; default ~/.config/amazon-lyr/cookies.json.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from amazon_lyr.logging_config import logger


def get_cookies_path() -> Path:
    base = os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / "amazon-lyr" / "cookies.json"


def load_cookies() -> dict[str, str]:
    """Load cookies. Precedence: AMAZON_COOKIES env var > stored file.

    Raises ValueError on malformed env input (fail loud, don't silently fall back).
    """
    raw = os.getenv("AMAZON_COOKIES", "").strip()
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Not inline JSON — treat as a path to a JSON file.
            try:
                data = json.loads(Path(raw).read_text())
            except FileNotFoundError:
                raise ValueError(
                    f"AMAZON_COOKIES is neither valid JSON nor an existing file: {raw!r}"
                ) from None
        if not isinstance(data, dict):
            raise ValueError("AMAZON_COOKIES must be a JSON object mapping cookie names to values")
        return {str(k): str(v) for k, v in data.items()}
    path = get_cookies_path()
    if not path.exists():
        return {}
    try:
        return {str(k): str(v) for k, v in json.loads(path.read_text()).items()}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read cookies at %s: %s", path, e)
        return {}


def save_cookies(cookies: dict[str, str]) -> Path:
    path = get_cookies_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cookies, indent=2))
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
    logger.info("Saved %d cookies to %s", len(cookies), path)
    return path


def clear_cookies() -> bool:
    path = get_cookies_path()
    if path.exists():
        path.unlink()
        return True
    return False
