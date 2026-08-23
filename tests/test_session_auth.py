"""Session state, auth matrix, and cookie-import edge cases."""

import json
import stat
import sys
import types

import pytest

from amazon_lyr.authentication import get_auth_status, validate_session, validate_write_session
from amazon_lyr.cookie_import import import_from_browser
from amazon_lyr.session_state import clear_cookies, get_cookies_path, load_cookies, save_cookies

# ── load_cookies precedence + validation ─────────────────────────────────


def test_load_none(isolated_config):
    assert load_cookies() == {}


def test_env_inline_json(isolated_config, monkeypatch):
    monkeypatch.setenv("AMAZON_COOKIES", '{"at-main": "t", "ubid-main": 123}')
    cookies = load_cookies()
    assert cookies == {"at-main": "t", "ubid-main": "123"}  # non-strings coerced


def test_env_file_path(isolated_config, tmp_path, monkeypatch):
    f = tmp_path / "c.json"
    f.write_text('{"at-main": "x"}')
    monkeypatch.setenv("AMAZON_COOKIES", str(f))
    assert load_cookies() == {"at-main": "x"}


def test_env_malformed_json_raises(isolated_config, monkeypatch):
    monkeypatch.setenv("AMAZON_COOKIES", "{not json")
    with pytest.raises(ValueError, match="neither valid JSON nor an existing file"):
        load_cookies()


def test_env_json_array_raises(isolated_config, monkeypatch):
    monkeypatch.setenv("AMAZON_COOKIES", '["not", "an", "object"]')
    with pytest.raises(ValueError, match="JSON object"):
        load_cookies()


def test_disk_corrupted_file_warns_and_returns_empty(isolated_config):
    path = get_cookies_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{corrupted")
    assert load_cookies() == {}


def test_save_roundtrip_and_permissions(isolated_config):
    save_cookies({"at-main": "secret"})
    path = get_cookies_path()
    assert path.exists()
    assert load_cookies() == {"at-main": "secret"}
    mode = stat.S_IMODE(path.stat().st_mode)
    assert not (mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH))


def test_clear_cookies_true_false(isolated_config):
    assert clear_cookies() is False
    save_cookies({"a": "b"})
    assert clear_cookies() is True


# ── auth status matrix ───────────────────────────────────────────────────


def _with(monkeypatch, **cookies):
    monkeypatch.setenv("AMAZON_COOKIES", json.dumps(cookies))


def test_auth_matrix(monkeypatch, isolated_config):
    cases = [
        ({}, False, False, "none"),
        ({"ubid-main": "1"}, False, False, "degraded"),
        ({"session-id": "1"}, False, False, "degraded"),
        ({"at-main": "t"}, True, False, "reads_only"),
        ({"at-main": "t", "ubid-main": "1"}, True, True, "full"),
        ({"at-main": "t", "session-id": "s"}, True, True, "full"),
        ({"at-main": "t", "ubid-main": "u", "session-id": "s"}, True, True, "full"),
    ]
    for cookies, authed, can_write, mode in cases:
        _with(monkeypatch, **cookies)
        status = get_auth_status()
        assert status["mode"] == mode, f"{cookies} → {status}"
        assert status["authenticated"] == authed
        assert validate_session() == authed
        assert validate_write_session() == can_write


# ── cookie import ────────────────────────────────────────────────────────


def test_browser_import_without_obscura(monkeypatch):
    monkeypatch.setitem(sys.modules, "obscura_core", None)
    with pytest.raises(ImportError, match="obscura"):
        import_from_browser("chrome")


def test_browser_import_success_filters_empty(monkeypatch):
    fake = types.ModuleType("obscura_core")

    class FakeExtractor:
        @staticmethod
        def extract(domain=None, browser=None, validate=False):
            assert domain == "amazon.com"
            assert browser == "chrome"
            return {"at-main": "keep", "junk": "", "empty": None}

    fake.BrowserCookieExtractor = FakeExtractor
    monkeypatch.setitem(sys.modules, "obscura_core", fake)
    assert import_from_browser("chrome") == {"at-main": "keep"}
