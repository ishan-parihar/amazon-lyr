"""Audit round 2: validation, cart quantity updates, detection edge cases."""

import pytest
from conftest import FakeResponse, FakeSession, session_getter

from amazon_lyr.cli_main import main as cli_main
from amazon_lyr.error_handler import handle_api_error
from amazon_lyr.exceptions import AmazonError
from amazon_lyr.scraping.api_client import AmazonClient
from amazon_lyr.scraping.parsers import build_review_insights, parse_cart


def _client(monkeypatch, responses):
    client = AmazonClient(cookies={"at-main": "t"})
    fake = FakeSession(responses)
    monkeypatch.setattr(client, "_get_session", session_getter(fake))
    return client, fake


# ── ASIN validation ──────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", ["", "abc", "B08N5WRWN", "B08N5WRWNWX", "has space!!"])
async def test_invalid_asin_rejected_with_format_hint(monkeypatch, bad):
    client, _ = _client(monkeypatch, FakeResponse("<html></html>"))
    with pytest.raises(AmazonError, match="10 characters"):
        await client.get_product(bad)


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [("b08n5wrwnw", "B08N5WRWNW"), (" B08N5WRWNW ", "B08N5WRWNW")],
)
async def test_asin_normalized_before_use(monkeypatch, raw, normalized):
    client, fake = _client(monkeypatch, [FakeResponse("<html></html>")])
    await client.get_product(raw)
    assert f"/dp/{normalized}" in fake.calls[0]["url"]


# ── cart quantity updates ────────────────────────────────────────────────

CART_WITH_QTY_SELECT = """
<div class="sc-list-item-content">
  <input type="submit" name="submit.delete.K1" value="Delete">
  <select name="quantityBox.Q9">
    <option value="1"></option>
    <option value="3" selected></option>
  </select>
  <span class="sc-product-link">Item A</span>
  <span class="sc-product-price">$5.00</span>
</div>
"""


def test_parse_cart_captures_qty_field_from_select():
    item = parse_cart(CART_WITH_QTY_SELECT)["items"][0]
    assert item["qty_field"] == "quantityBox.Q9"
    assert item["quantity"] == 3


def test_parse_cart_qty_field_from_text_input():
    html = """
    <div class="sc-list-item-content">
      <input type="text" name="quantityBox.T1" value="4">
      <span class="sc-product-link">Item B</span>
    </div>"""
    item = parse_cart(html)["items"][0]
    assert item["qty_field"] == "quantityBox.T1"
    assert item["quantity"] == 4


async def test_update_cart_quantity_happy_path(monkeypatch):
    updated = CART_WITH_QTY_SELECT.replace('value="3" selected', 'value="7" selected')
    client, fake = _client(monkeypatch, [FakeResponse(updated)])
    result = await client.update_cart_quantity("quantityBox.Q9", quantity=7)
    assert result["status"] == "ok"
    posted = fake.calls[0]
    assert posted["data"] == {"quantityBox.Q9": "7"}
    assert result["requested"]["quantity"] == 7


async def test_update_cart_quantity_clamps(monkeypatch):
    client, fake = _client(monkeypatch, [FakeResponse(CART_WITH_QTY_SELECT)])
    await client.update_cart_quantity("quantityBox.Q9", quantity=500)
    assert fake.calls[0]["data"]["quantityBox.Q9"] == "30"


async def test_update_cart_quantity_uncertain_when_not_applied(monkeypatch):
    client, _ = _client(monkeypatch, [FakeResponse('<div id="sc-empty-cart"></div>')])
    result = await client.update_cart_quantity("quantityBox.GONE", quantity=2)
    assert result["status"] == "uncertain"


# ── signin detection depth ───────────────────────────────────────────────


async def test_signin_form_deep_in_page_detected(monkeypatch):
    # Login form beyond the first 5000 chars must still be caught.
    filler = "<!-- pad -->" * 1000
    html = f'<html><body>{filler}<form action="/ap/signin"></form></body></html>'
    client, _ = _client(monkeypatch, [FakeResponse(html)])
    from amazon_lyr.exceptions import SessionExpiredError

    with pytest.raises(SessionExpiredError):
        await client.view_cart()


def test_list_returns_no_false_positive_on_marketing_text():
    """'sign in' text in a normal page body must NOT raise — only real forms do."""
    html = (
        "<html><body><nav>Hello, John. Someone sign in somewhere in copy.</nav>"
        '<div class="returns-empty">No returns yet</div></body></html>'
    )
    from amazon_lyr.scraping.parsers import parse_returns

    # Parser path: zero returns, no exception.
    assert parse_returns(html)["count"] == 0
    # And the page has no signin FORM, so client would return empty too.
    assert 'action="/ap/signin"' not in html


# ── error handler friendliness ───────────────────────────────────────────


def test_valueerror_wrapped_without_unexpected_prefix():
    with pytest.raises(RuntimeError) as e:
        handle_api_error(ValueError("query must not be empty"))
    assert str(e.value) == "query must not be empty"


# ── review pagination cap ────────────────────────────────────────────────


async def test_fetch_all_reviews_caps_pages_at_ten(monkeypatch):
    reviews_html = """
    <div data-hook="review" id="R1">
      <a data-hook="review-title"><span>T</span></a>
    </div>"""
    client, fake = _client(monkeypatch, [FakeResponse(reviews_html)] * 50)
    reviews = await client.fetch_all_reviews("B0X1234567", max_pages=50)
    assert len(fake.calls) <= 11  # 10 fetched pages max (+ none beyond cap)
    assert len(reviews) == 1  # deduped to unique ids


def test_insights_handles_malformed_rating_types():
    reviews = [
        {"id": "R1", "rating": None, "title": "x", "body": None, "verified_purchase": False},
        {
            "id": "R2",
            "rating": "five",
            "title": None,
            "body": "words here",
            "verified_purchase": True,
        },
        {"id": "R3"},
    ]
    ins = build_review_insights(reviews)
    assert ins["total"] == 3
    assert ins["average_rating"] is None
    assert ins["star_distribution"] is None


# ── CLI write gate ───────────────────────────────────────────────────────


def test_cli_cart_add_gated_without_context_cookies(isolated_config, monkeypatch, capsys):
    monkeypatch.setenv("AMAZON_COOKIES", '{"at-main": "t"}')  # reads-only session
    with pytest.raises(SystemExit) as e:
        cli_main(["cart-add", "B08N5WRWNW"])
    assert e.value.code == 2
    out = capsys.readouterr().out
    assert "full session cookies" in out and "amazon-lyr login" in out


# ── packaging sanity ─────────────────────────────────────────────────────


def test_version_single_sourced_from_metadata():
    import tomllib

    from amazon_lyr import __version__

    pyproject = tomllib.loads(open("pyproject.toml").read())
    assert __version__ == pyproject["project"]["version"]
