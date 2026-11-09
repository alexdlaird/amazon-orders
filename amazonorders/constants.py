__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from typing import Dict, List, Optional, Union

from amazonauth.constants import AuthConstants
from amazonauth.region_data import REGION_SITES

from amazonorders import util

logger = logging.getLogger(__name__)


class Constants(AuthConstants):
    """
    A class containing useful constants. Extend and override with ``constants_class`` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"constants_class": "my_module.MyConstants"})

    URLs and the URL-shaped headers (``Origin``, ``Referer``) are derived from the active
    Amazon domain. ``REQUEST_COOKIES``, ``Accept-Language``, ``CURRENCY_SYMBOL``, the sign-in
    ``openid.assoc_handle``, and ``COOKIES_SET_WHEN_AUTHENTICATED`` are adjusted for known Amazon sites
    (each only when a subclass has not overridden it). The domain is resolved in this precedence order:

    1. The ``domain`` key on :class:`~amazonorders.conf.AmazonOrdersConfig`.
    2. The default, ``amazon.com``.

    ``amazon-orders`` reads Amazon's pages in English, and requests them from any site known to offer English. To
    read a site in another language, use a language package; subclass and set ``constants_class`` to override any
    value a site requires.
    """

    ##########################################################################
    # URLs for Orders
    ##########################################################################

    ORDER_HISTORY_URL = f"{AuthConstants.BASE_URL}/your-orders/orders"
    ORDER_DETAILS_URL = f"{AuthConstants.BASE_URL}/gp/your-account/order-details"
    ORDER_INVOICE_URL = f"{AuthConstants.BASE_URL}/gp/css/summary/print.html"
    HISTORY_FILTER_QUERY_PARAM = "timeFilter"
    ORDER_FILTER_QUERY_PARAM = "orderFilter"
    FAMILY_MEMBER_QUERY_PARAM = "householdMembers"
    HISTORY_PAGE_QUERY_PARAM = "page"
    HISTORY_START_INDEX_QUERY_PARAM = "startIndex"
    # Amazon's no-JavaScript fallback, which renders encrypted Order cards readable
    DISABLE_CSD_QUERY_PARAM = "disableCsd"
    DISABLE_CSD_NO_JS = "no-js"
    ORDER_ID_QUERY_PARAM = "orderID"
    LAST_30_DAYS_TIME_FILTER = "last30"
    LAST_3_MONTHS_TIME_FILTER = "months-3"
    YEAR_TIME_FILTER_PREFIX = "year-"
    ORDER_HISTORY_PAGE_SIZE = 10
    WHOLE_FOODS_DETAILS_ROUTES = ["/fopo/order-details", "/wholefoodsmarket/receipts/order/"]
    TRACKING_ROUTE = "/progress-tracker/package"
    TRACKING_URL = f"{AuthConstants.BASE_URL}{TRACKING_ROUTE}"
    TRACKING_ORDER_ID_QUERY_PARAM = "orderId"
    SHIPMENT_ID_QUERY_PARAM = "shipmentId"
    TRACKING_PACKAGE_INDEX_QUERY_PARAM = "packageIndex"
    INVOICES_ROUTE = "/your-orders/invoice/popover"
    INVOICES_URL = f"{AuthConstants.BASE_URL}{INVOICES_ROUTE}"
    INVOICES_ORDER_ID_QUERY_PARAM = "orderId"
    INVOICE_PDF_CONTENT_TYPE = "application/pdf"
    INVOICE_HTML_FORMAT = "html"
    INVOICE_PDF_FORMAT = "pdf"
    ORDER_SEARCH_ROUTE = "/your-orders/search"
    ORDER_SEARCH_URL = f"{AuthConstants.BASE_URL}{ORDER_SEARCH_ROUTE}"
    ORDER_SEARCH_QUERY_PARAM = "search"
    ORDER_SEARCH_PAGE_QUERY_PARAM = "page"

    ##########################################################################
    # URLs for Prime
    ##########################################################################

    PRIME_PAYMENTS_ROUTE = "/mc/payments"
    PRIME_PAYMENTS_URL = f"{AuthConstants.BASE_URL}{PRIME_PAYMENTS_ROUTE}"

    ##########################################################################
    # URLs for Transactions
    ##########################################################################

    TRANSACTION_HISTORY_ROUTE = "/cpe/yourpayments/transactions"
    TRANSACTION_HISTORY_URL = f"{AuthConstants.BASE_URL}{TRANSACTION_HISTORY_ROUTE}"
    TRANSACTION_DATA_ROUTE = "/payments-portal/data/iris/live/v1/data/manage/get-transactions"
    TRANSACTION_DATA_URL = f"{AuthConstants.BASE_URL}{TRANSACTION_DATA_ROUTE}"
    #: The widget further pages of Transactions are requested for, when the page doesn't name it (e.g. amazon.de).
    TRANSACTION_DATA_WIDGET_NAME = "ViewTransactions"

    ##########################################################################
    # URLs for Gift Cards
    ##########################################################################

    GIFT_CARD_BALANCE_ROUTE = "/gc/balance"
    GIFT_CARD_BALANCE_URL = f"{AuthConstants.BASE_URL}{GIFT_CARD_BALANCE_ROUTE}"

    ##########################################################################
    # Formats
    ##########################################################################

    DECIMAL_SEPARATOR = "."
    THOUSANDS_SEPARATOR = ","
    #: The symbol :func:`format_currency` renders. Each known Amazon site sets its own; this is the fallback.
    CURRENCY_SYMBOL = "$"
    #: ``CURRENCY_SYMBOL`` for each site by the TLD that follows ``amazon.``, taking precedence over its region data.
    REGION_CURRENCY_OVERRIDES: Dict[str, str] = {}
    ZERO_DECIMAL_CURRENCY_SYMBOLS: List[str] = ["¥", "￥"]
    CURRENCY_FORMAT = "{symbol}{amount}"
    CURRENCY_FREE_TEXT = "free"
    #: Order numbers by shape: ``111-…`` and digital ``D01-…`` IDs, older ``4000-…`` IDs (still listed on
    #: Gift Card activity from around 2015), and 19-digit IDs.
    ORDER_NUMBER_REGEX = r"(?<![A-Z0-9-])(?:[A-Z0-9]{3}-\d{7}-\d{7}|\d{4}-\d{6}-\d{7}|\d{19})(?![A-Z0-9-])"

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
        decimals = 0 if self.CURRENCY_SYMBOL in self.ZERO_DECIMAL_CURRENCY_SYMBOLS else 2
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

    @classmethod
    def region_currency_symbol(cls,
                               tld: str) -> Optional[str]:
        """
        The currency symbol an Amazon site's prices are shown with: its ``REGION_CURRENCY_OVERRIDES`` entry, if it
        has one, otherwise its region data.

        :param tld: The TLD suffix that follows ``amazon.`` (e.g. ``co.uk``).
        :return: The currency symbol, or ``None`` if the site's isn't known.
        """
        site = REGION_SITES.get(tld)
        return cls.REGION_CURRENCY_OVERRIDES.get(tld) or (site.currency_symbol if site else None)

    def _apply_domain(self,
                      domain: str) -> None:
        """
        Override the URL-derived attributes for the given Amazon domain, on top of the sign-in and session values the
        base class applies, and ``CURRENCY_SYMBOL`` from its region data. ``CURRENCY_SYMBOL`` is applied only when a
        subclass hasn't overridden it, and a site that isn't known keeps the default.

        :param domain: The Amazon domain (e.g. ``amazon.com.au``) or full URL (e.g. ``https://www.amazon.com.au``).
        """
        super()._apply_domain(domain)

        base_url = self._normalize_base_url(domain)
        tld = self._tld(base_url)

        self.ORDER_HISTORY_URL = f"{base_url}/your-orders/orders"
        self.ORDER_DETAILS_URL = f"{base_url}/gp/your-account/order-details"
        self.ORDER_INVOICE_URL = f"{base_url}/gp/css/summary/print.html"
        self.TRACKING_URL = f"{base_url}{self.TRACKING_ROUTE}"
        self.INVOICES_URL = f"{base_url}{self.INVOICES_ROUTE}"
        self.ORDER_SEARCH_URL = f"{base_url}{self.ORDER_SEARCH_ROUTE}"
        self.PRIME_PAYMENTS_URL = f"{base_url}{self.PRIME_PAYMENTS_ROUTE}"
        self.TRANSACTION_HISTORY_URL = f"{base_url}{self.TRANSACTION_HISTORY_ROUTE}"
        self.TRANSACTION_DATA_URL = f"{base_url}{self.TRANSACTION_DATA_ROUTE}"
        self.GIFT_CARD_BALANCE_URL = f"{base_url}{self.GIFT_CARD_BALANCE_ROUTE}"

        currency_symbol = self.region_currency_symbol(tld)
        if currency_symbol and type(self).CURRENCY_SYMBOL == Constants.CURRENCY_SYMBOL:
            self.CURRENCY_SYMBOL = currency_symbol
