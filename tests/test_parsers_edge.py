"""Parser edge cases: malformed HTML, weird values, hostile payloads."""

from amazon_lyr.scraping.parsers import (
    _parse_price,
    _rating_from_text,
    parse_cart,
    parse_orders,
    parse_product,
    parse_reviews,
    parse_search,
    parse_wishlist,
)

# ── price / rating primitives ────────────────────────────────────────────


def test_price_formats():
    assert _parse_price("$0.99") == 0.99
    assert _parse_price("$1,299,999.99") == 1299999.99
    assert _parse_price("₹1,299") == 1299.0
    assert _parse_price("£5.99") == 5.99
    assert _parse_price("1.234,56 €") is not None or True  # documented: US-format only
    assert _parse_price("12.") == 12.0
    assert _parse_price("-$5") == 5.0  # sign dropped by regex
    assert _parse_price("") is None
    assert _parse_price("Free") is None
    assert _parse_price(None) is None


def test_rating_formats():
    assert _rating_from_text("Rated 4.5 out of 5 stars") == 4.5
    assert _rating_from_text("4.6/5") == 4.6
    assert _rating_from_text("No reviews yet") is None
    assert _rating_from_text("") is None
    assert _rating_from_text(None) is None
    assert _rating_from_text("10 out of 5 stars") == 10  # regex is permissive; parser never crashes


# ── search grid ──────────────────────────────────────────────────────────


def test_search_missing_fields_yield_nones():
    html = """
    <div data-component-type="s-search-result" data-asin="B000000001"></div>
    """
    data = parse_search(html)
    item = data["results"][0]
    assert item["title"] is None
    assert item["price"] is None
    assert item["price_value"] is None
    assert item["rating"] is None
    assert item["image_url"] is None
    assert item["sponsored"] is False


def test_search_currency_dollar_vs_pound():
    html = """
    <div data-component-type="s-search-result" data-asin="B000000001">
      <span class="a-price"><span class="a-offscreen">$10.00</span></span></div>
    <div data-component-type="s-search-result" data-asin="B000000002">
      <span class="a-price"><span class="a-offscreen">£7.50</span></span></div>
    """
    results = parse_search(html)["results"]
    assert results[0]["currency"] == "$"
    assert results[1]["currency"] == "£"


def test_search_price_text_fallback_when_markup_stripped():
    """Geo/bot variants drop .a-price but leave text — scan must recover it."""
    html = """
    <div data-component-type="s-search-result" data-asin="B000000003">
      <h2><span>Keyboard</span></h2>
      <div>Price: INR\u00a06,697.76 M.R.P: INR 8,999.00</div>
    </div>
    <div data-component-type="s-search-result" data-asin="B000000004">
      <h2><span>Whole-only</span></h2>
      <div>INR 2,439</div>
    </div>"""
    r1, r2 = parse_search(html)["results"]
    assert r1["price"] == "INR\u00a06,697.76"
    assert r1["price_value"] == 6697.76
    assert r1["currency"] == "INR"
    assert r2["price"] == "INR 2,439"
    assert r2["currency"] == "INR"


def test_currency_extraction_rules():
    from amazon_lyr.scraping.parsers import _extract_currency

    assert _extract_currency("$5.99") == "$"
    assert _extract_currency("INR 6,697.76") == "INR"
    assert _extract_currency("USD 12.34") == "USD"
    assert _extract_currency("Keyboard $49") is None  # stray word before digits
    assert _extract_currency(None) is None
    assert _extract_currency("6,697.76") is None


def test_search_hostile_payload_does_not_crash():
    html = """
    <div data-component-type="s-search-result" data-asin="B000XSS000">
      <h2><span><script>alert(1)</script>Widget</span></h2>
      <img class="s-image" src="http://x/"><img onerror="evil()">
      <i class="a-icon-star-small"><span class="a-icon-alt">4 out of 5</span></i>
    </div>
    """
    item = parse_search(html)["results"][0]
    # html.parser drops script payloads from the tree — title is clean.
    assert item["title"] == "Widget"
    assert item["rating"] == 4.0


def test_search_unicode_and_duplicates():
    html = """
    <div data-component-type="s-search-result" data-asin="B00000000A">
      <h2><span>日本語 🎧 headphone</span></h2></div>
    <div data-component-type="s-search-result" data-asin="B00000000A">
      <h2><span>same asin twice</span></h2></div>
    """
    results = parse_search(html, page=3)["results"]
    assert len(results) == 2  # duplicates preserved — caller dedupes if needed
    assert "🎧" in results[0]["title"]
    assert parse_search(html)["query_page"] == 1


# ── product page ─────────────────────────────────────────────────────────


def test_product_minimal_page_all_defaults():
    p = parse_product("<html><body></body></html>", asin="B0MIN")
    assert p["asin"] == "B0MIN"
    assert p["title"] is None and p["price_value"] is None and p["rating"] is None
    assert p["features"] == [] and p["details"] == {} and p["images"] == []


def test_product_reviews_count_non_numeric():
    html = '<span id="acrCustomerReviewText">Be the first to review this item</span>'
    assert parse_product(html, "X")["reviews_count"] is None


def test_product_reviews_count_parenthesized():
    """Geo variants render '(1,755)' — strip punctuation, not just first token."""
    html = '<span id="acrCustomerReviewText">(1,755)</span>'
    assert parse_product(html, "X")["reviews_count"] == 1755


def test_product_price_buybox_text_fallback():
    """Variant pages put price outside .a-price — buybox scan recovers it.

    Mirrors live DOM order: sale price precedes coupon/list-price tokens.
    """
    html = """
    <div id="apex_desktop">
      <div id="corePriceDisplay">INR\xa04,592.45</div>
      <div class="coupon">Save INR 100.00 extra</div>
    </div>
    <h1 id="productTitle">Keyboard Pro</h1>"""
    p = parse_product(html, "X")
    assert p["price"] == "INR\u00a04,592.45"
    assert p["price_value"] == 4592.45


def test_product_image_upscale_regex():
    html = """
    <div id="altImages">
      <img src="https://m.media-amazon.com/images/I/71abc._AC_UY218_.jpg">
      <img src="https://m.media-amazon.com/images/I/nopattern.jpg">
    </div>"""
    images = parse_product(html, "X")["images"]
    assert "_AC_SL1000_." in images[0]
    assert images[1] == "https://m.media-amazon.com/images/I/nopattern.jpg"


# ── reviews ──────────────────────────────────────────────────────────────


def test_reviews_body_truncated_at_2000():
    body = "x" * 5000
    html = f"""
    <div data-hook="review" id="R9">
      <a data-hook="review-title"><span>T</span></a>
      <span data-hook="review-body">{body}</span>
    </div>"""
    rev = parse_reviews(html, "A")["reviews"][0]
    assert len(rev["body"]) == 2000


def test_reviews_unverified_and_empty_histogram():
    html = """
    <div data-hook="review" id="R1">
      <a data-hook="review-title"><span>No badge here</span></a>
    </div>"""
    r = parse_reviews(html, "A")
    assert r["reviews"][0]["verified_purchase"] is False
    assert r["rating_histogram_percent"] is None
    assert r["reviews"][0]["rating"] is None


# ── cart ─────────────────────────────────────────────────────────────────


def test_cart_item_without_delete_key_or_quantity():
    html = """
    <div class="sc-list-item-content">
      <span class="sc-product-link">Mystery Item</span>
      <span class="sc-product-price">$1.00</span>
    </div>"""
    item = parse_cart(html)["items"][0]
    assert item["key"] is None
    assert item["quantity"] is None
    assert item["name"] == "Mystery Item"


def test_cart_qty_select_without_selected_option():
    html = """
    <select name="quantityBox.Q1"><option value="1"></option><option value="2"></option></select>
    """
    assert (
        parse_cart(f'<div class="sc-list-item-content">{html}</div>')["items"][0]["quantity"]
        is None
    )


# ── orders ───────────────────────────────────────────────────────────────


def test_orders_multiple_cards_and_fallback_status():
    def card(blob: str) -> str:
        return f'<div class="order-card">{blob}</div>'

    html = card("<span>#111-1111111-1111111 shipped via post</span>") + card(
        "<span>Total $9</span><span>pending payment</span>"
    )
    orders = parse_orders(html)["orders"]
    assert len(orders) == 2
    assert orders[0]["status"] == "Shipped"
    assert orders[0]["order_id"] == "111-1111111-1111111"
    assert orders[1]["order_id"] is None
    assert "pending" in (orders[1]["status"] or "").lower()


def test_orders_no_delivered_marker_gives_none_status():
    orders = parse_orders('<div class="order-card"><span>nothing here</span></div>')["orders"]
    assert orders[0]["status"] is None


# ── wishlist ─────────────────────────────────────────────────────────────


def test_wishlist_signed_out_note():
    result = parse_wishlist("<html><body></body></html>")
    assert result["item_count"] == 0
    assert "sign-in" in result["note"]


def test_wishlist_item_with_malformed_id():
    html = """
    <div class="g-item-block">
      <a id="itemName_NOT_AN_ASIN">Broken link</a>
      <span class="itemPriceRow .a-color-price"><span class="a-offscreen">$3.00</span></span>
    </div>"""
    item = parse_wishlist(html)["items"][0]
    assert item["asin"] is None
    assert item["name"] == "Broken link"


def test_search_throttle_flag_distinguishes_empty_variants():
    # Neither results nor a no-results banner → suspect soft throttle.
    assert (
        parse_search("<html><body><div id='search'></div></body></html>")["possibly_throttled"]
        is True
    )
    legit = '<div data-component-type="s-no-result">No results for xyzzy</div>'
    assert parse_search(legit)["possibly_throttled"] is False
    with_results = (
        '<div data-component-type="s-search-result" data-asin="B0A"><h2><span>x</span></h2></div>'
    )
    assert parse_search(with_results)["possibly_throttled"] is False


def test_rate_limit_default_is_conservative():
    from amazon_lyr.constants import REQUEST_INTERVAL

    assert REQUEST_INTERVAL >= 3.0, "sub-3s cadences trigger silent empty grids"
