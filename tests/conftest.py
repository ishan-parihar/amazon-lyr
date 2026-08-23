"""Shared fixtures: isolate config dir + env so tests never touch real cookies."""

import pytest


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Point XDG_CONFIG_HOME at a temp dir and clear cookie env vars."""
    xdg = tmp_path / "xdg-config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("AMAZON_COOKIES", raising=False)
    return tmp_path


@pytest.fixture(autouse=True)
def _reset_client_singleton():
    """Keep the process-wide client singleton from leaking between tests."""
    from amazon_lyr import dependencies

    dependencies._client = None
    yield
    dependencies._client = None
