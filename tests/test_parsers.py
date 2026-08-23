"""Parser tests against minimal real-Amazon-shaped HTML fixtures."""

from amazon_lyr.scraping.parsers import (
    _parse_price,
    _rating_from_text,
    parse_cart,
    parse_orders,
    parse_product,
    parse_reviews,
    parse_search,
)

SEARCH_HTML = """
<div id="search">
  <div data-component-type="s-search-result" data-asin="B08N5WRWNW">
    <h2><span>Echo Dot (5th Gen) smart speaker</span></h2>
    <span class="a-price"><span class="a-offscreen">$39.99</span></span>
    <i class="a-icon-star-small"><span class="a-icon-alt">4.7 out of 5 stars</span></i>
    <span aria-label="12,345 ratings">12,345</span>
    <img class="s-image" src="https://m.media-amazon.com/images/I/71._AC_UY218_.jpg">
  </div>
  <div data-component-type="s-search-result" data-asin=""></div>
</div>
"""

PRODUCT_HTML = """
<div id="dp">
  <h1 id="productTitle">Anker Soundcore Bluetooth Speaker, Black</h1>
  <div class="a-price"><span class="a-offscreen">$29.99</span></div>
  <span class="basisPrice"><span class="a-offscreen">$49.99</span></span>
  <div id="acrPopover" title="4.6 out of 5 stars"><span class="a-icon-alt">4.6 out of 5 stars</span></div>
  <span id="acrCustomerReviewText">88,213 ratings</span>
  <div id="availability"><span>In Stock</span></div>
  <a id="sellerProfileTriggerId">AnkerDirect</a>
  <div id="feature-bullets">
    <ul><li><span class="a-list-item">24-hour battery</span></li>
    <li class="aok-hidden"><span class="a-list-item">hidden bullet</span></li></ul>
  </div>
  <div id="detailBullets_feature_div">
    <ul>
      <li><span class="a-text-bold"> Brand :</span> <span>Anker</span></li>
      <li><span class="a-text-bold"> Model :</span> <span>A3102</span></li>
    </ul>
  </div>
</div>
"""

REVIEWS_HTML = """
<table data-hook="histogramTable">
  <tr><td class="a-text-right">5 star</td><td><span aria-hidden="70%">70%</span></td></tr>
</table>
<div data-hook="review" id="R1">
  <a data-hook="review-title"><span>Great sound</span></a>
  <span data-hook="review-body">Sounds amazing for the price.</span>
  <span data-hook="review-star-rating"><i class="a-icon-star"><span class="a-icon-alt">5.0 out of 5 stars</span></i></span>
  <span data-hook="review-date">Reviewed on August 1, 2026</span>
  <span class="a-profile-name">jane_d</span>
  <span data-hook="avp-badge">Verified Purchase</span>
</div>
"""

CART_HTML = """
<div id="sc-active-cart">
  <div class="sc-list-item-content">
    <input type="submit" name="submit.delete.ABC123" value="Delete">
    <select name="quantityBox.XYZ"><option selected value="2"></option></select>
    <span class="sc-product-link">USB-C Cable 6ft</span>
    <span class="sc-product-price">$9.99</span>
  </div>
  <span id="sc-subtotal-amount-buybox"><span class="sc-price">$19.98</span></span>
</div>
"""

ORDERS_HTML = """
<div class="order-card js-order-card">
  <div class="order-header">
    <div class="a-column"><span>Order placed<br>August 10, 2026</span></div>
    <div class="a-column"><span>Total $42.50</span></div>
    <div class="a-column"><span>Ship to John D</span></div>
    <div class="a-box"><span>#111-2223334-5556667</span></div>
  </div>
  <div class="delivery-box"><span class="yohtmlc-delivery-status">Delivered Aug 14</span></div>
  <div class="yohtmlc-item"><a class="yohtmlc-product-title">Phone Case Matte Black</a></div>
</div>
"""


def test_price_and_rating_helpers():
    assert _parse_price("$1,234.56") == 1234.56
    assert _parse_price(None) is None
    assert _parse_price("no price here") is None
    assert _rating_from_text("4.7 out of 5 stars") == 4.7
    assert _rating_from_text("garbage") is None


def test_parse_search():
    data = parse_search(SEARCH_HTML, page=2)
    assert len(data["results"]) == 1
    item = data["results"][0]
    assert item["asin"] == "B08N5WRWNW"
    assert item["title"].startswith("Echo Dot")
    assert item["price_value"] == 39.99
    assert item["rating"] == 4.7
    assert item["ratings_count"] == "12,345"


def test_parse_product():
    p = parse_product(PRODUCT_HTML, asin="B0TESTASIN")
    assert p["asin"] == "B0TESTASIN"
    assert p["title"] == "Anker Soundcore Bluetooth Speaker, Black"
    assert p["price_value"] == 29.99
    assert p["list_price_value"] == 49.99
    assert p["rating"] == 4.6
    assert p["reviews_count"] == 88213
    assert p["availability"] == "In Stock"
    assert p["buybox_seller"] == "AnkerDirect"
    assert p["features"] == ["24-hour battery"]
    assert p["details"]["Brand"] == "Anker"


def test_parse_reviews():
    r = parse_reviews(REVIEWS_HTML, asin="B0TESTASIN")
    assert r["asin"] == "B0TESTASIN"
    assert len(r["reviews"]) == 1
    rev = r["reviews"][0]
    assert rev["id"] == "R1"
    assert rev["rating"] == 5.0
    assert rev["author"] == "jane_d"
    assert rev["verified_purchase"] is True
    assert r["rating_histogram_percent"] == {"5 star": 70}


def test_parse_cart():
    c = parse_cart(CART_HTML)
    assert c["empty"] is False
    assert c["item_count"] == 1
    item = c["items"][0]
    assert item["key"] == "submit.delete.ABC123"
    assert item["quantity"] == 2
    assert item["price_value"] == 9.99
    assert c["subtotal_value"] == 19.98


def test_parse_orders():
    o = parse_orders(ORDERS_HTML)
    assert o["order_count"] == 1
    order = o["orders"][0]
    assert order["order_id"] == "111-2223334-5556667"
    assert order["total"] == "Total $42.50"
    assert order["status"] and "Delivered" in order["status"]
    assert order["items"][0]["name"] == "Phone Case Matte Black"


def test_empty_pages_do_not_crash():
    for parser in (parse_search,):
        assert parser("<html><body></body></html>")["results"] == []
    assert parse_product("<html></html>", "X")["title"] is None
    assert parse_orders("<html></html>")["orders"] == []
    assert parse_cart('<div id="sc-empty-cart"></div>')["empty"] is True
