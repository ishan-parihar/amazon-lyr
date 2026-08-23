"""Central constants: endpoints, cookies, retry policy."""

from __future__ import annotations

DEFAULT_MARKETPLACE = "https://www.amazon.com"

SEARCH_PATH = "/s"
PRODUCT_PATH = "/dp"
REVIEWS_PATH = "/product-reviews"
ORDERS_PATH = "/gp/your-orders/orders"
CART_ADD_PATH = "/gp/aws/cart/add.html"
CART_VIEW_PATH = "/gp/cart/view.html"
WISHLIST_PATH = "/hz/wishlist/ls"
SIGNIN_MARKER = "/ap/signin"

# Captcha page markers (Amazon bot-wall responses).
CAPTCHA_MARKERS = (
    "Enter the characters you see below",
    "Robot Check",
    "api-services-support@amazon.com",
    "To discuss automated access to Amazon data please contact",
)

# at-main is the login token; the others make writes (cart/wishlist) reliable.
REQUIRED_COOKIES = ["at-main"]
WRITE_COOKIES = ["ubid-main", "session-id"]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
ACCEPT_LANGUAGE = "en-US,en;q=0.9"

MAX_RETRIES = 3
RETRY_BACKOFF = 1.5
REQUEST_INTERVAL = 1.5  # seconds between requests — Amazon has no rate headers
REQUEST_TIMEOUT = 30
