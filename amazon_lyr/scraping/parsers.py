"""HTML → normalized dicts for search, product, reviews, cart, orders, wishlist.

All parsers are defensive: missing selectors yield None / [] instead of raising,
so partial data beats a crashed tool.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup, Tag

_PRICE_RE = re.compile(r"[\d,]+\.?\d*")
_ORDER_ID_RE = re.compile(r"\d{3}-\d{7}-\d{7}")


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _text(node: Tag | None) -> str | None:
    if node is None:
        return None
    text = node.get_text(" ", strip=True)
    return text or None


def _parse_price(text: str | None) -> float | None:
    if not text:
        return None
    match = _PRICE_RE.search(text.replace("\u00a0", " "))
    if not match:
        return None
    try:
        return float(Decimal(match.group(0).replace(",", "")))
    except InvalidOperation:
        return None


def _rating_from_text(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d(?:\.\d)?)\s*(?:out of|/)\s*5", text)
    return float(match.group(1)) if match else None


# ── search ───────────────────────────────────────────────────────────────


def parse_search(html: str, page: int = 1) -> dict:
    soup = _soup(html)
    results: list[dict] = []
    for card in soup.select('div[data-component-type="s-search-result"]'):
        asin = card.get("data-asin", "")
        if not asin:
            continue
        title = _text(card.select_one("h2 span"))
        price_node = card.select_one(".a-price .a-offscreen")
        price = _text(price_node)
        rating_text = _text(
            card.select_one("span.a-icon-alt") or card.select_one("i.a-icon-star-small")
        )
        ratings_count = _text(card.select_one('span[aria-label$="ratings"]'))
        if not ratings_count:
            rc = card.select_one("a.s-underline-link span")
            m = re.search(r"[\d,]+", rc.get_text() if rc else "")
            ratings_count = m.group(0) if m else None
        img = card.select_one("img.s-image")
        results.append(
            {
                "asin": asin,
                "title": title,
                "price": price,
                "price_value": _parse_price(price),
                "currency": price[:1]
                if price and price[:1].isascii() and not price[:1].isdigit()
                else None,
                "rating": _rating_from_text(rating_text),
                "ratings_count": ratings_count,
                "sponsored": bool(
                    card.select_one(
                        'div[data-component-type="sp-sponsored-result"], .puis-label-popover-default + .a-color-secondary'
                    )
                ),
                "image_url": img.get("src") if img else None,
            }
        )
    total_text = _text(soup.select_one('h2[class*="widget-header"] span, .s-breadcrumb span'))
    return {"query_page": page, "total_results_text": total_text, "results": results}


# ── product page ─────────────────────────────────────────────────────────


def _product_features(soup: BeautifulSoup) -> list[str]:
    bullets = soup.select("#feature-bullets li:not(.aok-hidden) span.a-list-item")
    return [t for t in (_text(li) for li in bullets) if t]


def _product_details(soup: BeautifulSoup) -> dict:
    details: dict[str, str] = {}
    for row in soup.select(
        "#detailBullets_feature_div li, #prodDetails tr, #productDetails_techSpec_section_1 tr"
    ):
        key = _text(row.select_one(".a-text-bold, th"))
        val = _text(row.select_one("span:not(.a-text-bold), td"))
        if key and val:
            details[key.strip().rstrip(":").strip()] = val
    for row in soup.select("#productOverview_feature_div tr, table.a-keyvalue tr"):
        key = _text(row.select_one("td.a-span3, th"))
        val = _text(row.select_one("td.a-span9, td:last-child"))
        if key and val:
            details[key.rstrip(":")] = val
    return details


def parse_product(html: str, asin: str) -> dict:
    soup = _soup(html)
    title = _text(soup.select_one("#productTitle"))
    price = _text(
        soup.select_one(".a-price .a-offscreen, #corePriceDisplay_desktop_feature_div .a-offscreen")
    )
    list_price = _text(soup.select_one(".basisPrice .a-offscreen, .a-text-price .a-offscreen"))
    rating_text = _text(
        soup.select_one("#acrPopover .a-icon-alt") or soup.select_one("#acrPopover")
    )
    ratings_count_text = _text(soup.select_one("#acrCustomerReviewText"))

    availability = _text(soup.select_one("#availability")) or _text(
        soup.select_one("#availabilityInsideBuyBox_feature_div")
    )
    seller = _text(soup.select_one("#sellerProfileTriggerId"))
    brand = _text(soup.select_one("#bylineInfo"))

    images: list[str] = []
    for img in soup.select("#altImages img[src]")[:8]:
        src = str(img.get("src", ""))
        # Thumbnails are small; upscale the size segment.
        images.append(re.sub(r"\._[^_]+_\.", "._AC_SL1000_.", src))

    return {
        "asin": asin,
        "title": title,
        "brand": brand,
        "byline": brand,
        "price": price,
        "price_value": _parse_price(price),
        "list_price": list_price,
        "list_price_value": _parse_price(list_price),
        "rating": _rating_from_text(rating_text),
        "reviews_count": int(ratings_count_text.split()[0].replace(",", ""))
        if ratings_count_text and ratings_count_text.split()[0].replace(",", "").isdigit()
        else None,
        "availability": availability,
        "buybox_seller": seller,
        "features": _product_features(soup),
        "details": _product_details(soup),
        "images": images,
    }


# ── reviews ──────────────────────────────────────────────────────────────


def parse_reviews(html: str, asin: str) -> dict:
    soup = _soup(html)
    reviews: list[dict] = []
    for block in soup.select('div[data-hook="review"]'):
        review_id = block.get("id", "")
        title = _text(
            block.select_one(
                'a[data-hook="review-title"] span:last-child, [data-hook="review-title"]'
            )
        )
        body = _text(block.select_one('span[data-hook="review-body"]'))
        rating_text = _text(
            block.select_one(
                "[data-hook=review-star-rating] .a-icon-alt, [data-hook=cmps-review-star-rating] .a-icon-alt"
            )
        )
        date = _text(block.select_one("[data-hook=review-date]"))
        author_node = block.select_one(".a-profile-name")
        verified = bool(block.select_one('[data-hook="avp-badge"]'))
        reviews.append(
            {
                "id": review_id,
                "rating": _rating_from_text(rating_text),
                "title": title,
                "body": body[:2000] if body else None,
                "date": date,
                "author": _text(author_node),
                "verified_purchase": verified,
            }
        )

    histogram: dict[str, int | None] = {}
    for row in soup.select('table[data-hook="histogramTable"] tr'):
        star_text = _text(row.select_one("td.a-text-right"))
        pct_text = _text(row.select_one("span[aria-hidden], td.a-text-right + td"))
        if star_text and pct_text:
            pct_match = re.search(r"(\d+)%", pct_text)
            histogram[star_text.strip()] = int(pct_match.group(1)) if pct_match else None

    return {
        "asin": asin,
        "total_reviews_on_page": len(reviews),
        "rating_histogram_percent": histogram or None,
        "reviews": reviews,
    }


# ── cart ─────────────────────────────────────────────────────────────────


def parse_cart(html: str) -> dict:
    soup = _soup(html)
    items: list[dict] = []
    for block in soup.select(
        'div.sc-list-item-content, div[data-name="Active Items"] .sc-list-item'
    ):
        form_input = block.select_one('input[name^="submit.delete."]')
        qty_input = block.select_one(
            'input[name^="quantityBox."], select[name^="quantityBox."] option[selected]'
        )
        qty_raw = qty_input.get("value") if qty_input else None
        name = _text(block.select_one(".sc-product-link, h4 a, span.a-truncate-full"))
        price_text = _text(block.select_one(".sc-product-price, .sc-price"))
        items.append(
            {
                "key": form_input.get("name") if form_input else None,
                "name": name,
                "price": price_text,
                "price_value": _parse_price(price_text),
                "quantity": int(str(qty_raw)) if qty_raw and str(qty_raw).isdigit() else None,
            }
        )

    subtotal = _text(
        soup.select_one(
            "#sc-subtotal-amount-buybox .sc-price, #sc-active-cart .sc-subtotal .sc-price"
        )
    )
    empty = bool(soup.select_one("#sc-empty-cart, .sc-your-amazon-empty-cart-message-container"))

    return {
        "empty": empty,
        "item_count": len(items),
        "items": items,
        "subtotal": subtotal,
        "subtotal_value": _parse_price(subtotal),
    }


# ── orders ───────────────────────────────────────────────────────────────


def parse_orders(html: str) -> dict:
    soup = _soup(html)
    orders: list[dict] = []
    for card in soup.select("div.order-card, div.js-order-card"):
        text_blob = card.get_text(" ", strip=True)
        order_id_match = _ORDER_ID_RE.search(text_blob)
        placed = _text(card.select_one(".order-info span.label")) or None
        header_cols = [_text(c) for c in card.select(".order-header .a-column span")]
        total = next((t for t in header_cols if t and "$" in t), None)
        items: list[dict] = []
        for item in card.select(".yohtmlc-item a, .a-fixed-left-grid .yohtmlc-product-title"):
            name = _text(item)
            if name:
                items.append({"name": name})
        status = _text(
            card.select_one(
                ".delivery-box .yohtmlc-delivery-status, .shipment .js-shipment-status, [data-testid='primary-status']"
            )
        )
        orders.append(
            {
                "order_id": order_id_match.group(0) if order_id_match else None,
                "placed_label": placed,
                "placed_date": header_cols[0] if len(header_cols) > 0 else None,
                "total": total,
                "ship_to": header_cols[-1] if len(header_cols) > 2 else None,
                "status": status
                or (
                    "Delivered"
                    if "delivered" in text_blob.lower()
                    else "Shipped"
                    if "shipped" in text_blob.lower()
                    else None
                ),
                "items": items[:5],
            }
        )
    return {"order_count": len(orders), "orders": orders}


# ── wishlist ─────────────────────────────────────────────────────────────


def parse_wishlist(html: str) -> dict:
    soup = _soup(html)
    items: list[dict] = []
    for block in soup.select("div.g-item-block"):
        link = block.select_one('a[id^="itemName_"]')
        price_text = _text(
            block.select_one("span.a-price .a-offscreen, .itemPriceRow .a-color-price")
        )
        asin_match = re.search(r"itemName_([A-Z0-9]{10})", str(link.get("id")) if link else "")
        items.append(
            {
                "asin": asin_match.group(1) if asin_match else None,
                "name": _text(link),
                "price": price_text,
                "price_value": _parse_price(price_text),
            }
        )
    signed_in = soup.select_one("#nav-link-accountList-nav-line-1") is not None
    return {
        "item_count": len(items),
        "items": items,
        "note": None if signed_in else "Wishlist may be empty or require sign-in cookies.",
    }
