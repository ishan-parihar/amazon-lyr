"""CLI error paths: exit codes, TOON errors, login flows."""

import json

import pytest

from amazon_lyr.cli_main import main as cli_main


def test_unknown_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as e:
        cli_main(["definitely-not-a-command"])
    assert e.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_logout_with_no_cookies(isolated_config, capsys):
    cli_main(["logout"])
    assert "logged_out: false" in capsys.readouterr().out


def test_login_from_valid_file(isolated_config, tmp_path, capsys):
    f = tmp_path / "cookies.json"
    f.write_text(json.dumps({"at-main": "t", "ubid-main": "u", "session-id": "s"}))
    cli_main(["login", "--cookies-file", str(f)])
    out = capsys.readouterr().out
    assert "mode: full" in out


def test_login_file_missing_at_main(isolated_config, tmp_path, capsys):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"foo": "bar"}))
    with pytest.raises(SystemExit) as e:
        cli_main(["login", "--cookies-file", str(f)])
    assert e.value.code == 2
    assert "at-main" in capsys.readouterr().out


def test_login_nonexistent_file(isolated_config, capsys):
    with pytest.raises(SystemExit) as e:
        cli_main(["login", "--cookies-file", "/nope/missing.json"])
    assert e.value.code == 2
    assert "Could not read cookies file" in capsys.readouterr().out


def test_product_command_without_cookies_hints_login(isolated_config, capsys):
    with pytest.raises(SystemExit) as e:
        cli_main(["product", "B08N5WRWNW"])
    assert e.value.code == 2
    assert "amazon-lyr login" in capsys.readouterr().out


def test_home_view_full_auth_suggests_search(isolated_config, monkeypatch, capsys):
    monkeypatch.setenv("AMAZON_COOKIES", '{"at-main": "t"}')
    cli_main([])
    out = capsys.readouterr().out
    assert "auth: reads_only" in out
    assert 'search "' in out


def test_search_empty_query_fails_loud(isolated_config, monkeypatch, capsys):
    monkeypatch.setenv("AMAZON_COOKIES", '{"at-main": "t"}')

    import amazon_lyr.dependencies as deps

    class FakeClient:
        async def search_products(self, *a, **k):
            raise ValueError("query must not be empty")

    monkeypatch.setattr(deps, "get_amazon_client", lambda: FakeClient())
    with pytest.raises(SystemExit) as e:
        cli_main(["search", "   "])
    assert e.value.code == 2
    assert "query must not be empty" in capsys.readouterr().out
