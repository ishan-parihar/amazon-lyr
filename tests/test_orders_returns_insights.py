"""Order details / returns / cancel-form parser + review-insights edge cases."""

import pytest

from amazon_lyr.exceptions import ParseError
from amazon_lyr.scraping.parsers import (
    build_review_insights,
    parse_cancel_form,
    parse_order_details,
    parse_return_form,
    parse_returns,
)

ORDER_DETAILS_HTML = """
<div id="orderDetails">
  <span data-test-id='order-status'>Shipped</span>
  <div class="yo-item-block">
    <a class="yohtmlc-product-title">USB-C Hub 7-in-1</a>
    <span class="yohtmlc-item-price">$34.99</span>
    <span>Qty: 2</span>
  </div>
  <table class="od-subtotals">
    <tr><td>Subtotal:</td><td>$69.98</td></tr>
    <tr><td>Shipping:</td><td>$0.00</td></tr>
    <tr><td>Total:</td><td>$73.47</td></tr>
  </table>
  <div id="payment-method">Visa ending 4242</div>
  <div id="primaryShipToAddr">John D, 12 Main St</div>
  <div class="tracking-number"><a>TBA123456789</a></div>
  <a href="/gp/aw/invoice?orderID=111-2223334-5556667">View invoice</a>
  <a href="/gp/cancel-your-orders?orderID=111-2223334-5556667">Cancel items</a>
  <span>Order # 111-2223334-5556667</span>
</div>
"""

RETURN_FORM_HTML = """
<form method="post" action="/gp/orc/return/step2">
  <input type="hidden" name="anti-csrftoken-a2z" value="tok123">
  <input type="hidden" name="orderID" value="111-2223334-5556667">
  <div><input type="checkbox" name="itemSelector" value="B0AAA">
    <span class="a-label-bold">USB-C Hub</span></div>
  <div><input type="checkbox" name="itemSelector" value="B0BBB">
    <span class="a-label-bold">Cable Pack</span></div>
  <select name="reasonSelectId">
    <option value="NO_LONGER_NEED">No longer needed</option>
    <option value="DEFECTIVE_ITEM">Defective</option>
  </select>
</form>
"""


def test_parse_order_details_full():
    d = parse_order_details(ORDER_DETAILS_HTML)
    assert d["order_id"] == "111-2223334-5556667"
    assert d["status"] == "Shipped"
    assert len(d["items"]) == 1
    assert d["items"][0]["quantity"] == 2
    assert d["items"][0]["price_value"] == 34.99
    assert d["totals"]["Total"] == 73.47
    assert d["payment_method"] == "Visa ending 4242"
    assert "John D" in (d["ship_to"] or "")
    assert d["tracking_numbers"][0]["number"] == "TBA123456789"
    assert "/gp/aw/invoice" in d["invoice_url"]
    assert "/gp/cancel-your-orders" in d["cancel_url"]


def test_parse_order_details_empty_page_all_nones():
    d = parse_order_details("<html></html>", order_id="999-0000000-0000000")
    assert d["items"] == []
    assert d["totals"] is None
    assert d["status"] is None
    assert d["cancel_url"] is None


def test_parse_returns():
    html = """
    <div class="return-item">
      <span class="yohtmlc-product-title">Keyboard</span>
      <span>Refund issued: INR\u00a04,592.45 Order # 111-2223334-5556667</span>
    </div>
    <div class="return-item"><span>Replacement sent</span></div>"""
    r = parse_returns(html)
    assert r["count"] == 2
    assert r["returns"][0]["status"] == "Refund issued"
    assert r["returns"][0]["refund_amount"] == "INR 4,592.45"
    assert r["returns"][1]["status"] == "Replacement sent"
    assert r["returns"][1]["order_id"] is None


def test_parse_return_form_extracts_everything():
    f = parse_return_form(RETURN_FORM_HTML)
    assert f["action"] == "/gp/orc/return/step2"
    assert f["fields"]["anti-csrftoken-a2z"] == "tok123"
    assert len(f["items"]) == 2
    assert f["items"][1]["label"] == "Cable Pack"
    assert {"value": "NO_LONGER_NEED", "label": "No longer needed"} in f["reason_options"]


def test_parse_return_form_missing_raises_with_guidance():
    with pytest.raises(ParseError, match="returns/orders"):
        parse_return_form("<html><body>No form here</body></html>")


def test_parse_cancel_form_and_missing_form():
    good = """
    <form method="post" action="/cancel/confirm">
      <input type="hidden" name="token" value="t">
      <input type="checkbox" name="checkedItems" value="item1">
      <h1>Cancel your items?</h1>
    </form>"""
    c = parse_cancel_form(good)
    assert c["fields"] == {"token": "t"}
    assert c["item_checkboxes"][0]["value"] == "item1"
    with pytest.raises(ParseError):
        parse_cancel_form("<html></html>")


# ── review insights (pure function) ──────────────────────────────────────

def _rev(rating, body, verified=True):
    return {"id": "R", "rating": rating, "title": "", "body": body, "verified_purchase": verified}


def test_insights_empty():
    ins = build_review_insights([])
    assert ins["total"] == 0
    assert ins["average_rating"] is None
    assert ins["critical_keywords"] == []


def test_insights_aggregation():
    reviews = [
        _rev(5, "Great battery life and sound quality", True),
        _rev(4, "Battery lasts long, decent sound", True),
        _rev(2, "Battery died within a week, poor quality control", False),
        _rev(1, "Broke immediately. Poor build quality", False),
        _rev(3, None, True),
    ]
    ins = build_review_insights(reviews)
    assert ins["total"] == 5
    assert ins["average_rating"] == 3.0
    assert ins["star_distribution"] == {"5star": 1, "4star": 1, "2star": 1, "1star": 1, "3star": 1}
    assert ins["verified_percent"] == 60
    words = {k["word"] for k in ins["top_keywords"]}
    assert "battery" in words and "quality" in words
    crit_words = {k["word"] for k in ins["critical_keywords"]}
    assert "poor" in crit_words
    # Stopwords excluded.
    assert "the" not in words and "and" not in words


def test_insights_keyword_counts_ranked():
    reviews = [_rev(5, "battery battery battery great")] * 3
    ins = build_review_insights(reviews)
    top = ins["top_keywords"][0]
    assert top["word"] == "battery" and top["count"] == 9  # 3 reviews × 3 mentions
