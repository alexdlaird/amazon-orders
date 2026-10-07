__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import os
import re
from datetime import date
from typing import Dict, Optional, TYPE_CHECKING, Union
from urllib.parse import urlencode, urlparse

from amazonorders import util

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

#: ``CURRENCY_SYMBOL`` values for Amazon sites whose prices use a symbol other than ``$``, each verified
#: against the site's own pages. amazon.ca, amazon.com.au, and amazon.com.mx render prices as plain ``$``,
#: so they keep the default and are intentionally omitted here. Skipped when ``AMAZON_CURRENCY_SYMBOL`` is
#: set, or when a ``constants_class`` override sets ``CURRENCY_SYMBOL``.
_REGION_CURRENCIES = {
    "ae": "AED",
    "co.jp": "¥",
    "co.uk": "£",
    "com.be": "€",
    "com.br": "R$",
    "com.tr": "TL",
    "de": "€",
    "eg": "EGP",
    "es": "€",
    "ie": "€",
    "in": "₹",
    "it": "€",
    "nl": "€",
    "pl": "zł",
    "sa": "SAR",
    "se": "kr",
    "sg": "S$",
}

#: Currency symbols whose amounts are rendered without decimals (yen has no minor unit).
_ZERO_DECIMAL_CURRENCY_SYMBOLS = ["¥", "￥"]

#: ``openid.assoc_handle`` values for Amazon sign-in, keyed by the TLD suffix that follows
#: ``amazon.``. Amazon rejects the sign-in request (HTTP 404) when the handle does not match
#: the storefront's region. Applied only when ``SIGN_IN_QUERY_PARAMS`` still has the default
#: ``usflex``, so a ``constants_class`` override wins. Unknown TLDs keep the default.
_REGION_ASSOC_HANDLES = {
    "ca": "caflex",
    "co.jp": "jpflex",
    "co.uk": "gbflex",
    "com.au": "auflex",
    "de": "deflex",
    "in": "inflex",
}

#: The cookie that marks an authenticated session on regional Amazon sites, keyed by the TLD
#: suffix that follows ``amazon.``. Applied only when ``COOKIES_SET_WHEN_AUTHENTICATED`` still
#: has the default ``x-main``, so a ``constants_class`` override wins. Unknown TLDs keep the default.
_REGION_AUTH_COOKIES = {
    "ca": "x-acbca",
    "co.jp": "x-acbjp",
    "co.uk": "x-acbuk",
    "com.au": "x-acbau",
    "de": "x-acbde",
    "in": "x-acbin",
}


class Constants:
    """
    A class containing useful constants. Extend and override with ``constants_class`` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"constants_class": "my_module.MyConstants"})

    URLs and the URL-shaped headers (``Origin``, ``Host``, ``Referer``) are derived from the active
    Amazon domain. ``Accept-Language``, ``CURRENCY_SYMBOL``, the sign-in ``openid.assoc_handle``, and
    ``COOKIES_SET_WHEN_AUTHENTICATED`` are adjusted for a small set of known TLDs (``CURRENCY_SYMBOL``
    only when ``AMAZON_CURRENCY_SYMBOL`` is unset; ``CURRENCY_SYMBOL``, ``openid.assoc_handle``, and
    ``COOKIES_SET_WHEN_AUTHENTICATED`` only when a subclass has not overridden them). The domain is
    resolved in this precedence order:

    1. The ``domain`` key on :class:`~amazonorders.conf.AmazonOrdersConfig`.
    2. The ``AMAZON_BASE_URL`` environment variable.
    3. The default, ``amazon.com``.

    ``amazon-orders`` core supports the English ``.com`` site; subclass and set ``constants_class`` to override any
    value another site requires.
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
    # URLs for Gift Cards
    ##########################################################################

    GIFT_CARD_BALANCE_ROUTE = "/gc/balance"
    GIFT_CARD_BALANCE_URL = f"{BASE_URL}{GIFT_CARD_BALANCE_ROUTE}"

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
    SIGNED_OUT_TEXT = "Hello, sign in"
    JS_ROBOT_TEXT_REGEX = r"[.\s\S]*verify that you're not a robot[.\s\S]*Enable JavaScript[.\s\S]*"
    GOKU_PROPS_REGEX = r"window\.gokuProps\s*=\s*(\{.*?\});"
    ACIC_CHALLENGE_PATH = "/ax/aaut/verify/ap/challenge"

    ##########################################################################
    # Formats
    ##########################################################################

    DECIMAL_SEPARATOR = "."
    THOUSANDS_SEPARATOR = ","
    #: The symbol :func:`format_currency` renders, adjusted for a small set of known TLDs. For an Amazon
    #: site without a known symbol, the ``AMAZON_CURRENCY_SYMBOL`` environment variable sets it without a
    #: ``constants_class`` subclass (e.g. for the CLI).
    CURRENCY_SYMBOL = os.environ.get("AMAZON_CURRENCY_SYMBOL", "$")
    CURRENCY_FORMAT = "{symbol}{amount}"
    CURRENCY_FREE_TEXT = "free"
    #: Order numbers by shape: ``111-…`` and digital ``D01-…`` IDs, older ``4000-…`` IDs (still listed on
    #: Gift Card activity from around 2015), and 19-digit IDs.
    ORDER_NUMBER_REGEX = r"(?<![A-Z0-9-])(?:[A-Z0-9]{3}-\d{7}-\d{7}|\d{4}-\d{6}-\d{7}|\d{19})(?![A-Z0-9-])"

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
        Apply browser-specific header overrides for the given browser engine. A header a subclass changed from
        the default keeps its value.

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
            if headers.get(key) != Constants.BASE_HEADERS.get(key):
                continue
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
        base_url = self._normalize_base_url(domain)

        host = urlparse(base_url).netloc.lower().split(":")[0]
        if host.startswith("www."):
            host = host[len("www."):]
        tld = host[len("amazon."):] if host.startswith("amazon.") else ""

        # Build from the instance-level BASE_HEADERS if _apply_browser has already set it;
        # otherwise fall back to the class-level definition.
        sign_in_query_params = dict(type(self).SIGN_IN_QUERY_PARAMS)
        sign_in_query_params["openid.return_to"] = f"{base_url}/?ref_=nav_custrec_signin"
        if (tld in _REGION_ASSOC_HANDLES and
                sign_in_query_params["openid.assoc_handle"] == Constants.SIGN_IN_QUERY_PARAMS["openid.assoc_handle"]):
            sign_in_query_params["openid.assoc_handle"] = _REGION_ASSOC_HANDLES[tld]

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
        self.GIFT_CARD_BALANCE_URL = f"{base_url}{self.GIFT_CARD_BALANCE_ROUTE}"

        headers = dict(vars(self).get("BASE_HEADERS", type(self).BASE_HEADERS))
        headers["Origin"] = base_url
        headers["Host"] = urlparse(base_url).netloc
        headers["Referer"] = f"{sign_in_url}?{urlencode(sign_in_query_params)}"
        if (tld in _REGION_LANGUAGES and
                type(self).BASE_HEADERS.get("Accept-Language") == Constants.BASE_HEADERS.get("Accept-Language")):
            headers["Accept-Language"] = _REGION_LANGUAGES[tld]
        self.BASE_HEADERS = headers

        if (not os.environ.get("AMAZON_CURRENCY_SYMBOL") and tld in _REGION_CURRENCIES and
                type(self).CURRENCY_SYMBOL == Constants.CURRENCY_SYMBOL):
            self.CURRENCY_SYMBOL = _REGION_CURRENCIES[tld]

        if (tld in _REGION_AUTH_COOKIES and
                type(self).COOKIES_SET_WHEN_AUTHENTICATED == Constants.COOKIES_SET_WHEN_AUTHENTICATED):
            self.COOKIES_SET_WHEN_AUTHENTICATED = [_REGION_AUTH_COOKIES[tld]]

    @staticmethod
    def _normalize_base_url(value: str) -> str:
        value = value.strip().rstrip("/")
        if value.startswith(("http://", "https://")):
            return value
        if value.startswith("www."):
            return f"https://{value}"
        return f"https://www.{value}"

    def format_currency(self,
                        amount: float) -> str:
        """
        Format an amount for display, using ``CURRENCY_SYMBOL``, ``DECIMAL_SEPARATOR``,
        ``THOUSANDS_SEPARATOR``, and the ``CURRENCY_FORMAT`` template (which places the
        ``{symbol}`` and ``{amount}``, e.g. ``"{amount} {symbol}"`` renders ``1.234,56 €``). A
        negative amount is prefixed with ``-``.

        :param amount: The amount to format.
        :return: The formatted amount.
        """
        decimals = 0 if self.CURRENCY_SYMBOL in _ZERO_DECIMAL_CURRENCY_SYMBOLS else 2
        integer, _, fraction = "{amount:,.{decimals}f}".format(amount=abs(amount), decimals=decimals).partition(".")
        formatted_number = integer.replace(",", self.THOUSANDS_SEPARATOR)
        if fraction:
            formatted_number += f"{self.DECIMAL_SEPARATOR}{fraction}"
        formatted_amt = self.CURRENCY_FORMAT.format(symbol=self.CURRENCY_SYMBOL, amount=formatted_number)
        if round(amount, decimals) < 0:
            return f"-{formatted_amt}"
        return formatted_amt

    def parse_currency(self,
                       value: Union[str, int, float]) -> Union[int, float, None]:
        """
        Parse a currency amount as rendered on the page, stripping non-numeric values and returning it
        as a primitive.

        Strips any currency symbol (e.g. ``$``, ``€``, or the fullwidth ``￥`` used by amazon.co.jp) and
        currency-code letters (e.g. ``CDN$``, ``AED``, or ``zł``), accepts accounting-style negatives in
        parentheses (e.g. ``($1.99)``), and treats :attr:`CURRENCY_FREE_TEXT` as ``0.0``. Either decimal mark
        is accepted: a trailing ``.`` or ``,`` followed by one or two digits is the decimal mark, and other
        ``.``, ``,``, ``'``, and space separators group thousands (e.g. ``1,234.56``, ``1.234,56 €``, or
        ``12,99 €``).

        :param value: The currency to parse.
        :return: The currency as a primitive, or ``None`` if it could not be parsed.
        """
        if isinstance(value, (int, float)):
            return value

        if not value:
            return None

        value = value.strip()

        if value.casefold() == self.CURRENCY_FREE_TEXT.casefold():
            return 0.0

        if value.startswith("(") and value.endswith(")"):
            value = "-" + value[1:-1]

        value = util.strip_currency_text(value.replace("\u2212", "-"))
        currency = util.to_type(util.to_decimal_point(value))

        if isinstance(currency, str):
            return None

        return currency

    def parse_date(self,
                   value: Optional[str],
                   fuzzy: bool = False) -> Optional[date]:
        """
        Parse a date as rendered on the page. Delegates to :func:`~amazonorders.util.to_date`.

        :param value: The date string to parse.
        :param fuzzy: Whether to ignore unknown tokens when parsing.
        :return: The parsed ``date``, or ``None`` if it could not be parsed.
        """
        return util.to_date(value, fuzzy=fuzzy)

    def parse_count(self,
                    value: str,
                    pattern: str = r"^\s*{count}") -> Optional[int]:
        """
        Parse a whole number as rendered on the page. Delegates to :func:`~amazonorders.util.to_count`.

        :param value: The text containing the number.
        :param pattern: A regex locating the number, with ``{count}`` marking where it appears. Defaults to a
            number at the start of the text.
        :return: The number, or ``None`` if ``pattern`` does not match.
        """
        return util.to_count(value, pattern)

    def parse_order_number(self,
                           value: str) -> Optional[str]:
        """
        Find an Order number, as matched by :attr:`ORDER_NUMBER_REGEX`, in text from the page.

        :param value: The text containing the Order number.
        :return: The Order number, or ``None`` if the text does not contain one.
        """
        match = re.search(self.ORDER_NUMBER_REGEX, value)
        return match.group(0) if match else None
