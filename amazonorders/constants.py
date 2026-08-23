__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import os
from typing import Dict, Optional, TYPE_CHECKING
from urllib.parse import urlencode, urlparse

if TYPE_CHECKING:
    from amazonorders.conf import AmazonOrdersConfig

logger = logging.getLogger(__name__)

#: Browser-specific header overrides applied on top of the class-level ``BASE_HEADERS``
#: (which already reflects the Chromium fingerprint). A ``None`` value removes the key
#: (used to strip headers absent in that engine). ``Accept-Language`` here is the browser
#: default; domain-specific TLD overrides still apply on top via :func:`~Constants._apply_domain`.
_BROWSER_PRESETS: Dict[str, Dict[str, Optional[str]]] = {
    "chromium": {},  # BASE_HEADERS already reflects the Chromium fingerprint; no overrides needed.
    "firefox": {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Sec-Ch-Ua": None,
        "Sec-Ch-Ua-Mobile": None,
        "Sec-Ch-Ua-Platform": None,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
    },
}

#: ``Accept-Language`` values for English-locale Amazon sites, keyed by the TLD suffix that
#: follows ``amazon.``. Looked up dynamically from the user-supplied domain; unknown TLDs keep
#: the base ``en-US`` value. This map only governs the ``Accept-Language`` header — it is not
#: a list of supported sites and does not affect any other authentication behavior.
_REGION_LANGUAGES = {
    "ca": "en-CA,en;q=0.9,en-US;q=0.8",
    "co.uk": "en-GB,en;q=0.9,en-US;q=0.8",
    "com.au": "en-AU,en;q=0.9,en-US;q=0.8",
    "in": "en-IN,en;q=0.9,en-US;q=0.8",
    "sg": "en-SG,en;q=0.9,en-US;q=0.8",
}

#: ``CURRENCY_SYMBOL`` values for English-locale Amazon sites where the storefront actually
#: prefixes prices with a non-``$`` symbol. amazon.com.au and amazon.ca render prices as
#: plain ``$`` (single-currency context), so they keep the default and are intentionally
#: omitted here. Skipped when ``AMAZON_CURRENCY_SYMBOL`` is set.
_REGION_CURRENCIES = {
    "co.uk": "£",
    "co.jp": "¥",
    "in": "₹",
    "sg": "S$",
}


def _normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("www."):
        return f"https://{value}"
    return f"https://www.{value}"


class Constants:
    """
    A class containing useful constants. Extend and override with ``constants_class`` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"constants_class": "my_module.MyConstants"})

    URLs and the URL-shaped headers (``Origin``, ``Host``, ``Referer``) are derived from the active
    Amazon domain. ``Accept-Language`` and ``CURRENCY_SYMBOL`` are adjusted for a small set of
    English-locale TLDs (``CURRENCY_SYMBOL`` only when ``AMAZON_CURRENCY_SYMBOL`` is unset). The
    domain is resolved in this precedence order:

    1. The ``domain`` key on :class:`~amazonorders.conf.AmazonOrdersConfig`.
    2. The ``AMAZON_BASE_URL`` environment variable.
    3. The default, ``amazon.com``.

    Only the English, ``.com`` site is officially supported. Other domains may work, but values like
    ``openid.assoc_handle`` are not adjusted automatically — subclass and set ``constants_class`` to
    override them if a non-``.com`` site requires it.
    """

    ##########################################################################
    # General URL (defaults; overridden in ``__init__`` when a domain is set)
    ##########################################################################

    BASE_URL = "https://www.amazon.com"

    ##########################################################################
    # URLs for AmazonSession
    ##########################################################################

    SIGN_IN_URL = f"{BASE_URL}/ap/signin"
    SIGN_IN_QUERY_PARAMS = {"openid.pape.max_auth_age": "0",
                            "openid.return_to": f"{BASE_URL}/?ref_=nav_custrec_signin",
                            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
                            "openid.assoc_handle": "usflex",
                            "openid.mode": "checkid_setup",
                            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
                            "openid.ns": "http://specs.openid.net/auth/2.0"}
    SIGN_IN_CLAIM_URL = f"{BASE_URL}/ax/claim"
    SIGN_OUT_URL = f"{BASE_URL}/gp/flex/sign-out.html"

    ##########################################################################
    # URLs for Orders
    ##########################################################################

    ORDER_HISTORY_URL = f"{BASE_URL}/your-orders/orders"
    ORDER_DETAILS_URL = f"{BASE_URL}/gp/your-account/order-details"
    ORDER_INVOICE_URL = f"{BASE_URL}/gp/css/summary/print.html"
    HISTORY_FILTER_QUERY_PARAM = "timeFilter"
    ORDER_FILTER_QUERY_PARAM = "orderFilter"
    WHOLE_FOODS_DETAILS_ROUTES = ["/fopo/order-details", "/wholefoodsmarket/receipts/order/"]

    ##########################################################################
    # URLs for Transactions
    ##########################################################################

    TRANSACTION_HISTORY_ROUTE = "/cpe/yourpayments/transactions"
    TRANSACTION_HISTORY_URL = f"{BASE_URL}{TRANSACTION_HISTORY_ROUTE}"

    ##########################################################################
    # Headers
    ##########################################################################

    BASE_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Host": urlparse(BASE_URL).netloc,
        "Origin": BASE_URL,
        "Referer": f"{SIGN_IN_URL}?{urlencode(SIGN_IN_QUERY_PARAMS)}",
        "Sec-Ch-Ua": '"Chromium";v="149", "Google Chrome";v="149", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",  # noqa: E501
    }

    ##########################################################################
    # Authentication
    ##########################################################################

    COOKIES_SET_WHEN_AUTHENTICATED = ["x-main"]
    JS_ROBOT_TEXT_REGEX = r"[.\s\S]*verify that you're not a robot[.\s\S]*Enable JavaScript[.\s\S]*"
    GOKU_PROPS_REGEX = r"window\.gokuProps\s*=\s*(\{.*?\});"
    ACIC_CHALLENGE_PATH = "/ax/aaut/verify/ap/challenge"

    ##########################################################################
    # Currency
    ##########################################################################

    CURRENCY_SYMBOL = os.environ.get("AMAZON_CURRENCY_SYMBOL", "$")

    def __init__(self,
                 config: Optional["AmazonOrdersConfig"] = None) -> None:
        domain = None
        browser = None
        if config is not None:
            domain = config._data.get("domain")
            browser = config._data.get("browser")
        if not domain:
            domain = os.environ.get("AMAZON_BASE_URL")
        if not browser:
            browser = os.environ.get("AMAZON_BROWSER")
        self._apply_browser(browser or "chromium")
        if domain:
            self._apply_domain(domain)

    def _apply_browser(self,
                       browser: str) -> None:
        """
        Apply browser-specific header overrides for the given browser engine.

        :param browser: Browser engine name — ``"firefox"`` or ``"chromium"``. Unknown values
            log a warning and leave ``BASE_HEADERS`` unchanged.
        """
        preset = _BROWSER_PRESETS.get(browser)
        if preset is None:
            logger.warning(
                f"Unknown browser value {browser!r}; "
                f"valid values are: {', '.join(_BROWSER_PRESETS)}. Using default headers."
            )
            return
        headers = dict(type(self).BASE_HEADERS)
        for key, value in preset.items():
            if value is None:
                headers.pop(key, None)
            else:
                headers[key] = value
        self.BASE_HEADERS = headers

    def _apply_domain(self,
                      domain: str) -> None:
        """
        Override the URL-derived attributes for the given Amazon domain.

        :param domain: The Amazon domain (e.g. ``amazon.com.au``) or full URL (e.g. ``https://www.amazon.com.au``).
        """
        base_url = _normalize_base_url(domain)

        # Build from the instance-level BASE_HEADERS if _apply_browser has already set it;
        # otherwise fall back to the class-level definition.
        sign_in_query_params = dict(type(self).SIGN_IN_QUERY_PARAMS)
        sign_in_query_params["openid.return_to"] = f"{base_url}/?ref_=nav_custrec_signin"

        sign_in_url = f"{base_url}/ap/signin"

        self.BASE_URL = base_url
        self.SIGN_IN_URL = sign_in_url
        self.SIGN_IN_QUERY_PARAMS = sign_in_query_params
        self.SIGN_IN_CLAIM_URL = f"{base_url}/ax/claim"
        self.SIGN_OUT_URL = f"{base_url}/gp/flex/sign-out.html"
        self.ORDER_HISTORY_URL = f"{base_url}/your-orders/orders"
        self.ORDER_DETAILS_URL = f"{base_url}/gp/your-account/order-details"
        self.ORDER_INVOICE_URL = f"{base_url}/gp/css/summary/print.html"
        self.TRANSACTION_HISTORY_URL = f"{base_url}{self.TRANSACTION_HISTORY_ROUTE}"

        host = urlparse(base_url).netloc.lower().split(":")[0]
        if host.startswith("www."):
            host = host[len("www."):]
        tld = host[len("amazon."):] if host.startswith("amazon.") else ""

        headers = dict(vars(self).get("BASE_HEADERS", type(self).BASE_HEADERS))
        headers["Origin"] = base_url
        headers["Host"] = urlparse(base_url).netloc
        headers["Referer"] = f"{sign_in_url}?{urlencode(sign_in_query_params)}"
        if tld in _REGION_LANGUAGES:
            headers["Accept-Language"] = _REGION_LANGUAGES[tld]
        self.BASE_HEADERS = headers

        if not os.environ.get("AMAZON_CURRENCY_SYMBOL") and tld in _REGION_CURRENCIES:
            self.CURRENCY_SYMBOL = _REGION_CURRENCIES[tld]

    def format_currency(self,
                        amount: float) -> str:
        formatted_amt = "{currency_symbol}{amount:,.2f}".format(currency_symbol=self.CURRENCY_SYMBOL,
                                                                amount=abs(amount))
        if round(amount, 2) < 0:
            return f"-{formatted_amt}"
        return formatted_amt
