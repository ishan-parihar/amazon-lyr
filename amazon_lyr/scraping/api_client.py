"""Amazon HTML client on curl_cffi with captcha/signin detection and retries."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from amazon_lyr.constants import (
    ACCEPT_LANGUAGE,
    CART_ADD_PATH,
    CART_VIEW_PATH,
    DEFAULT_MARKETPLACE,
    DEFAULT_USER_AGENT,
    MAX_RETRIES,
    ORDERS_PATH,
    PRODUCT_PATH,
    REQUEST_INTERVAL,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    REVIEWS_PATH,
    SEARCH_PATH,
    SIGNIN_MARKER,
    WISHLIST_PATH,
)
from amazon_lyr.exceptions import (
    AmazonError,
    AuthenticationError,
    CaptchaError,
    NotFoundError,
    SessionExpiredError,
)
from amazon_lyr.ratelimit import RateLimiter
from amazon_lyr.scraping.parsers import (
    parse_cart,
    parse_orders,
    parse_product,
    parse_reviews,
    parse_search,
    parse_wishlist,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class AmazonClient:
    def __init__(self, cookies: dict[str, str] | None = None, marketplace: str | None = None):
        self._cookies = cookies or {}
        self._base = (marketplace or DEFAULT_MARKETPLACE).rstrip("/")
        self._session: AsyncSession | None = None
        self._rate_limiter = RateLimiter(min_interval=REQUEST_INTERVAL)

    # ── transport ────────────────────────────────────────────────────────

    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSession(impersonate="chrome", timeout=REQUEST_TIMEOUT)
            for name, value in self._cookies.items():
                self._session.cookies.set(name, value, domain=".amazon.com")
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    def _check_page(self, resp) -> None:
        """Raise mapped errors for captcha / signin / 404 responses."""
        body = resp.text[:20000]
        final_url = str(getattr(resp, "url", ""))
        if any(
            marker in body
            for marker in (
                "Enter the characters you see below",
                "Robot Check",
                "api-services-support@amazon.com",
            )
        ):
            raise CaptchaError("Amazon served a CAPTCHA page")
        if "To discuss automated access to Amazon data please contact" in resp.text:
            raise CaptchaError("Amazon served an automated-access block")
        if SIGNIN_MARKER in final_url or 'action="/ap/signin"' in resp.text[:5000]:
            raise SessionExpiredError("Amazon redirected to sign-in")
        if resp.status_code == 404:
            raise NotFoundError("Page not found (404)")

    async def _request(self, method: str, path_or_url: str, **kwargs) -> Any:
        session = await self._get_session()
        url = path_or_url if path_or_url.startswith("http") else urljoin(self._base, path_or_url)
        headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept-Language": ACCEPT_LANGUAGE}
        kwargs.setdefault("headers", {}).update(headers)

        await self._rate_limiter.acquire()
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await session.request(method, url, allow_redirects=True, **kwargs)
                self._check_page(resp)
                return resp
            except (AuthenticationError, SessionExpiredError, CaptchaError, NotFoundError):
                raise
            except Exception as e:  # noqa: BLE001 - retry then wrap
                last_err = e
                status = getattr(e, "code", None) or getattr(
                    getattr(e, "response", None), "status_code", None
                )
                if status == 503:
                    raise CaptchaError(f"Amazon returned 503 (likely bot-wall): {e}") from e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF * (attempt + 1))
                    continue
        raise AmazonError(f"Request failed after {MAX_RETRIES} attempts: {last_err}")

    async def get_html(self, path: str, params: dict | None = None) -> str:
        resp = await self._request("GET", path, params=params)
        return resp.text

    async def post_form(self, path: str, data: dict, referer: str | None = None) -> str:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if referer:
            headers["Referer"] = referer
        resp = await self._request("POST", path, data=data, headers=headers)
        return resp.text

    # ── reads (research) ─────────────────────────────────────────────────

    async def search_products(
        self,
        query: str,
        department: str | None = None,
        sort: str | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        min_rating: int | None = None,
        page: int = 1,
    ) -> dict:
        params: dict[str, Any] = {"k": query, "page": str(page)}
        if department:
            params["i"] = department
        if sort:
            params["s"] = sort  # e.g. price-asc-rank, price-desc-rank, review-rank, date-desc-rank
        low_high = "&".join(
            p
            for p in (
                f"low-price={price_min}" if price_min else "",
                f"high-price={price_max}" if price_max else "",
            )
            if p
        )
        if low_high:
            params["rh"] = f"p_36:{low_high}"
        if min_rating:
            base_rh = params.get("rh", "")
            star_map = {4: "p72:1254471011", 3: "p72:1254477011"}
            params["rh"] = f"{base_rh}&{star_map.get(min_rating, star_map[4])}"
        html = await self.get_html(SEARCH_PATH, params=params)
        return parse_search(html, page=page)

    async def get_product(self, asin: str) -> dict:
        html = await self.get_html(f"{PRODUCT_PATH}/{asin}", params=None)
        return parse_product(html, asin=asin)

    async def get_reviews(
        self,
        asin: str,
        filter_by_star: str
        | None = None,  # one_star|two_stars|three_stars|four_stars|five_stars|critical|positive
        sort_by: str = "recent",  # recent|helpful
        page: int = 1,
    ) -> dict:
        params: dict[str, Any] = {"sortBy": sort_by, "pageNumber": str(page)}
        if filter_by_star:
            params["filterByStar"] = filter_by_star
        html = await self.get_html(f"{REVIEWS_PATH}/{asin}", params=params)
        return parse_reviews(html, asin=asin)

    async def get_wishlist(self, wishlist_id: str | None = None) -> dict:
        params = {"cid": wishlist_id} if wishlist_id else None
        html = await self.get_html(WISHLIST_PATH, params=params)
        return parse_wishlist(html)

    async def get_orders(self, status_filter: str | None = None) -> dict:
        params = {}
        if status_filter:
            params = {"orderFilter": status_filter}  # e.g. last30, months-3, pending, shipped
        html = await self.get_html(ORDERS_PATH, params=params)
        return parse_orders(html)

    # ── writes (shopping) ────────────────────────────────────────────────

    async def add_to_cart(self, asin: str, quantity: int = 1) -> dict:
        data = {
            "ASIN.1": asin,
            "quantity.1": str(quantity),
            "submit.addToCart": "Add to Cart",
        }
        html = await self.post_form(CART_ADD_PATH, data=data)
        cart = parse_cart(html)
        return {"status": "ok", "requested": {"asin": asin, "quantity": quantity}, "cart": cart}

    async def view_cart(self) -> dict:
        html = await self.get_html(CART_VIEW_PATH)
        return parse_cart(html)

    async def remove_from_cart(self, item_key: str) -> dict:
        # item_key comes from view_cart() items[].key (e.g. submit.delete.<ID>)
        data = {item_key: "Delete"}
        html = await self.post_form(CART_VIEW_PATH, data=data)
        cart = parse_cart(html)
        removed = all(i.get("key") != item_key for i in cart.get("items", []))
        return {"status": "ok" if removed else "uncertain", "cart": cart}

    async def add_to_wishlist(self, asin: str) -> dict:
        raise AmazonError(
            "add_to_wishlist is not reliably supported via scraping "
            "(registry endpoints require per-session tokens). Use add_to_cart instead."
        )
