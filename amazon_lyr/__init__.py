"""amazon-lyr — Amazon research & shopping MCP server via browser cookies."""

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("amazon-lyr")
except Exception:  # noqa: BLE001 - running from a source tree without install metadata
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
