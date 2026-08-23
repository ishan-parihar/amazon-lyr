"""Client behavior tests with a FakeSession (no network)."""

import pytest

from amazon_lyr.exceptions import CaptchaError, SessionExpiredError
from amazon_lyr.scraping.api_client import AmazonClient


class FakeResponse:
    def __init__(self, text="", status_code=200, url="https://www.amazon.com/s?k=x"):
        self.text = text
        self.status_code = status_code
        self.url = url
        self.headers = {}

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, responses):
        self._responses = responses if isinstance(responses, list) else [responses]
        self.calls = []

    async def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": str(url), **kwargs})
        resp = self._responses[min(len(self.calls) - 1, len(self._responses) - 1)]
        if isinstance(resp, Exception):
            raise resp
        return resp

    async def close(self):
        pass


def _client_with(monkeypatch, responses, cookies=None):
    client = AmazonClient(cookies=cookies or {"at-main": "t"})
    fake = FakeSession(responses)
    monkeypatch.setattr(client, "_get_session", _async_returning(fake))
    return client, fake


def _async_returning(value):
    async def _get():
        return value

    return _get


async def test_captcha_detected(monkeypatch):
    captcha_html = "<html><title>Robot Check</title>Enter the characters you see below</html>"
    client, _ = _client_with(monkeypatch, FakeResponse(captcha_html))
    with pytest.raises(CaptchaError):
        await client.search_products("laptop")


async def test_signin_redirect_detected(monkeypatch):
    resp = FakeResponse("<html></html>", url="https://www.amazon.com/ap/signin?openid=x")
    client, _ = _client_with(monkeypatch, resp)
    with pytest.raises(SessionExpiredError):
        await client.view_cart()


async def test_503_maps_to_captcha(monkeypatch):
    class StatusError(Exception):
        def __init__(self):
            super().__init__("503")
            self.code = 503

    client, _ = _client_with(monkeypatch, StatusError())
    with pytest.raises(CaptchaError):
        await client.get_product("B0X")


async def test_search_passes_query_params(monkeypatch):
    ok = FakeResponse("<html><body></body></html>")
    client, fake = _client_with(monkeypatch, ok)
    await client.search_products("mech keyboard", sort="price-asc-rank", page=2)
    call = fake.calls[0]
    params = call["params"] or {}
    assert params["k"] == "mech keyboard"
    assert params["s"] == "price-asc-rank"
    assert params["page"] == "2"


async def test_add_to_cart_posts_form(monkeypatch):
    ok = FakeResponse('<div id="sc-empty-cart"></div>')
    client, fake = _client_with(monkeypatch, ok)
    result = await client.add_to_cart("B0TESTASIN", quantity=2)
    call = fake.calls[0]
    assert call["method"] == "POST"
    assert "gp/aws/cart/add.html" in call["url"]
    assert call["data"]["ASIN.1"] == "B0TESTASIN"
    assert call["data"]["quantity.1"] == "2"
    assert result["requested"]["asin"] == "B0TESTASIN"


async def test_cookies_set_on_session():

    client = AmazonClient(cookies={"at-main": "abc", "ubid-main": "123"})
    session = await client._get_session()
    try:
        jar_names = {c.name: c.value for c in session.cookies.jar}
        assert jar_names["at-main"] == "abc"
        assert jar_names["ubid-main"] == "123"
    finally:
        await client.close()
