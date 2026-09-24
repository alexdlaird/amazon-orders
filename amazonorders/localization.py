__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional, Type, Union

from amazonorders import util
from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)


class Locale:
    """
    The language- and format-dependent behavior used when parsing Amazon pages. The base class is the
    ``en-US`` behavior of amazon.com, so a subclass only overrides what differs for its storefront.

    The active Locale is :attr:`~amazonorders.constants.Constants.LOCALE`. It is looked up from the domain's
    TLD (see :data:`LOCALES_BY_TLD`) and can be overridden with the ``locale`` config key (e.g. ``de-DE``).
    """

    #: The Locale's tag, as used for the ``locale`` config key.
    TAG = "en-US"

    #: Text matched on the landing page to tell a signed-out session apart from a signed-in one.
    SIGNED_OUT_TEXT = "Hello, sign in"
    #: Text shown on the Transactions page when there are no Transactions.
    NO_TRANSACTIONS_TEXT = "don't have any transactions"

    #: The suffix that follows the Order placed date, when both share a tag.
    ORDER_PLACED_DATE_SUFFIX = "Order #"
    #: The label that precedes the grand total on the Order history page.
    GRAND_TOTAL_PREFIX = "total"
    #: Labels of the Order history card header, used to find a value by its label rather than its column.
    #: ``None`` keeps the column-based selectors.
    HISTORY_HEADER_ORDER_PLACED_LABEL: Optional[str] = None
    HISTORY_HEADER_GRAND_TOTAL_LABEL: Optional[str] = None

    #: The text that precedes the Seller's name.
    SOLD_BY_PREFIX = "Sold by:"
    #: Text Amazon appends to the Seller's name, which is not part of it.
    SELLER_NAME_SUFFIXES: List[str] = []
    #: The text that precedes the Item's condition.
    CONDITION_PREFIX = "Condition:"
    #: Text contained in the Item's return eligibility.
    RETURN_TEXT = "Return"
    #: The text that precedes the Item's return eligible date, when the return eligibility lists more than one
    #: date (one per line). ``None`` if the whole return eligibility text is parsed as the date.
    RETURN_DATE_PREFIX: Optional[str] = None
    #: The text that precedes an Item's Subscribe & Save delivery frequency. ``None`` if not rendered.
    SUBSCRIPTION_FREQUENCY_PREFIX: Optional[str] = None
    #: ``True`` if the Recipient address is returned line by line (separated by ``\n``), without the Recipient's
    #: name. ``False`` keeps the flattened text of the address block.
    MULTILINE_ADDRESS = False
    #: Shipment delivery statuses starting with any of these mark the Shipment as cancelled. If every Shipment
    #: of an Order is cancelled, so is the Order. Empty if cancelled Orders are identified by selectors only.
    CANCELLED_STATUS_PREFIXES: List[str] = []

    #: Labels of the Order subtotal rows, keyed by the ``en-US`` label that
    #: :func:`~amazonorders.entity.order.Order._parse_currency` looks up. Missing keys are matched as-is.
    SUBTOTAL_LABELS: Dict[str, List[str]] = {}

    #: Lower-cased month names and abbreviations, mapped to the month number (``1`` to ``12``). Useful for dates
    #: that :func:`parse_date` rejects because they have no year. Empty if the Locale does not define them.
    MONTHS: Mapping[str, int] = MappingProxyType({})

    def subtotal_matches(self,
                         key: str,
                         text: str) -> bool:
        """
        Whether the text of an Order subtotal row is the one for the given key.

        :param key: The ``en-US`` label of the subtotal (e.g. ``grand total``).
        :param text: The lower-cased text of the subtotal row.
        :return: ``True`` if the row is the subtotal for the key.
        """
        return key in text

    def parse_date(self,
                   value: str) -> Optional[date]:
        """
        Parse a date as it is rendered on the storefront.

        :param value: The text containing the date.
        :return: The parsed date, or ``None`` if it could not be parsed.
        """
        return util.to_date(value, fuzzy=True)

    def parse_currency(self,
                       value: str) -> Union[int, float, None]:
        """
        Parse a currency amount as it is rendered on the storefront.

        Recognizes the ``$``, ``£``, ``€``, ``₹``, and ``¥`` symbols (including the fullwidth
        ``￥`` used by amazon.co.jp, and leading currency-code letters such as ``A$`` or
        ``CDN$``), accepts accounting-style negatives in parentheses (e.g. ``($1.99)``), and
        treats a literal ``FREE`` as ``0.0``.

        :param value: The text containing the amount.
        :return: The amount, or ``None`` if it could not be parsed.
        """
        value = value.strip()

        if value.lower() == "free":
            return 0.0

        if value.startswith("(") and value.endswith(")"):
            value = "-" + value[1:-1]

        value = re.sub("[a-zA-Z$£€₹¥￥,]+", "", value)
        currency = util.to_type(value)

        if isinstance(currency, str):
            return None

        return currency

    def format_currency(self,
                        amount: float,
                        currency_symbol: str,
                        decimals: int = 2) -> str:
        """
        Format a currency amount as it is rendered on the storefront.

        :param amount: The amount to format.
        :param currency_symbol: The currency symbol.
        :param decimals: The number of decimals the currency is rendered with.
        :return: The formatted amount.
        """
        formatted_amt = "{currency_symbol}{amount:,.{decimals}f}".format(currency_symbol=currency_symbol,
                                                                         amount=abs(amount),
                                                                         decimals=decimals)
        if round(amount, decimals) < 0:
            return f"-{formatted_amt}"
        return formatted_amt


class EnUS(Locale):
    """
    The ``en-US`` Locale of amazon.com, which is also the default for any storefront without its own Locale.
    """


_GERMAN_MONTHS = {
    "januar": 1, "jan": 1, "jänner": 1,
    "februar": 2, "feb": 2,
    "märz": 3, "mär": 3, "mrz": 3,
    "april": 4, "apr": 4,
    "mai": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}

#: A German date such as ``6. September 2026``, ``06. Sept. 2026``, or ``6. September`` (no year).
_GERMAN_TEXT_DATE_RE = re.compile(
    r"(?<!\d)(\d{1,2})\.\s*(" + "|".join(sorted(_GERMAN_MONTHS, key=len, reverse=True)) + r")\.?(?![a-zäöü])"
    r"(?:\s+(\d{4}))?(?!\d)",
    re.IGNORECASE)
#: A numeric German date such as ``06.09.2026``.
_GERMAN_NUMERIC_DATE_RE = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.(\d{4})(?![\d.])")
#: A German amount such as ``1.234,56``, ``25,29``, or ``7``.
_GERMAN_AMOUNT_RE = re.compile(r"-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?")


class DeDE(Locale):
    """
    The ``de-DE`` Locale of amazon.de.
    """

    TAG = "de-DE"

    SIGNED_OUT_TEXT = "Hallo, anmelden"
    # TODO: capture the Transactions page of an account without Transactions to verify this text
    NO_TRANSACTIONS_TEXT = "keine Transaktionen"

    GRAND_TOTAL_PREFIX = "summe"
    HISTORY_HEADER_ORDER_PLACED_LABEL = "Bestellung aufgegeben"
    HISTORY_HEADER_GRAND_TOTAL_LABEL = "Summe"

    SOLD_BY_PREFIX = "Verkauf durch:"
    SELLER_NAME_SUFFIXES = ["Preise inkl. MwSt."]
    # TODO: capture an Order with a used Item to verify this text
    CONDITION_PREFIX = "Zustand:"
    RETURN_TEXT = "Rückgabe"
    # e.g. "Zeitraum für Rückgabe endet am 18. September 2026", next to "Artikel ersetzen: Möglich bis zum ..."
    RETURN_DATE_PREFIX = "Rückgabe endet am"
    SUBSCRIPTION_FREQUENCY_PREFIX = "Automatisch zugestellt:"
    MULTILINE_ADDRESS = True
    CANCELLED_STATUS_PREFIXES = ["Storniert", "Service storniert"]
    MONTHS = MappingProxyType(_GERMAN_MONTHS)

    # Matched against the start of the row, since German labels are compounds of one another (e.g.
    # "Zwischensumme" and "Summe").
    SUBTOTAL_LABELS = {
        "subtotal": ["zwischensumme", "artikel-zwischensumme"],
        "shipping": ["verpackung & versand", "versand"],
        "free shipping": [],
        "promotion": [],
        "coupon": ["gutschein eingelöst"],
        "reward": ["prämienpunkte"],
        "subscribe": ["spar-abo"],
        "subscription": [],
        "before tax": ["gesamt vor ust", "summe ohne mwst", "gesamtbetrag vor steuern"],
        "estimated tax": ["geschätzte ust", "anzurechnende mwst", "mwst:"],
        "tax collected": [],
        "refund total": ["summe der erstattung"],
        "multibuy discount": [],
        "amazon discount": [],
        "gift card amount": [],
        "gift card": ["geschenkgutschein"],
        "gift wrap": ["geschenkverpackung"],
        "grand total": ["gesamtsumme"],
        "total for this order": ["gesamtbetrag für diese bestellung", "summe:"],
    }

    def subtotal_matches(self,
                         key: str,
                         text: str) -> bool:
        text = text.strip()
        return any(text.startswith(label) for label in self.SUBTOTAL_LABELS.get(key, []))

    def parse_date(self,
                   value: str) -> Optional[date]:
        """
        Parse a German date (e.g. ``6. September 2026`` or ``06.09.2026``) from the given text. The
        date is never guessed: if the text has no year, or more than one distinct date, ``None`` is
        returned and a warning is logged.

        :param value: The text containing the date.
        :return: The parsed date, or ``None`` if it could not be parsed unambiguously.
        """
        if not value:
            return None

        found = set()
        for day, month_name, year in _GERMAN_TEXT_DATE_RE.findall(value):
            if not year:
                logger.warning(f"Date {value!r} has no year, so it was not parsed.")
                return None
            found.add((int(year), _GERMAN_MONTHS[month_name.lower()], int(day)))
        for day, month, year in _GERMAN_NUMERIC_DATE_RE.findall(value):
            found.add((int(year), int(month), int(day)))

        if not found:
            logger.debug(f"No date found in {value!r}.")
            return None
        if len(found) > 1:
            logger.warning(f"Date {value!r} contains more than one date, so it was not parsed.")
            return None

        year, month, day = found.pop()
        try:
            return date(year, month, day)
        except ValueError:
            logger.warning(f"Date {value!r} is not a valid date, so it was not parsed.")
            return None

    def parse_currency(self,
                       value: str) -> Union[int, float, None]:
        """
        Parse a German amount (e.g. ``1.234,56 €`` or ``-39,93 €``) from the given text.

        :param value: The text containing the amount.
        :return: The amount, or ``None`` if it could not be parsed.
        """
        value = value.replace(" ", " ").replace("−", "-").strip()

        if value.lower() in ["kostenlos", "gratis"]:
            return 0.0

        value = re.sub(r"\s+", "", re.sub(r"€|EUR", "", value))
        if not _GERMAN_AMOUNT_RE.fullmatch(value):
            logger.warning(f"Amount {value!r} is not a German amount, so it was not parsed.")
            return None

        return util.to_type(value.replace(".", "").replace(",", "."))  # type: ignore[return-value]

    def format_currency(self,
                        amount: float,
                        currency_symbol: str,
                        decimals: int = 2) -> str:
        formatted_amt = "{amount:,.{decimals}f}".format(amount=abs(amount), decimals=decimals)
        formatted_amt = formatted_amt.replace(",", "_").replace(".", ",").replace("_", ".")
        if round(amount, decimals) < 0:
            return f"-{formatted_amt} {currency_symbol}"
        return f"{formatted_amt} {currency_symbol}"


#: The Locale of each storefront, keyed by the TLD suffix that follows ``amazon.``. Storefronts not
#: listed here use :class:`EnUS`.
LOCALES_BY_TLD: Dict[str, Type[Locale]] = {
    "de": DeDE,
}

#: The Locales by their tag, for the ``locale`` config key.
LOCALES_BY_TAG: Dict[str, Type[Locale]] = {
    EnUS.TAG: EnUS,
    DeDE.TAG: DeDE,
}


def get_locale(tag: str) -> Locale:
    """
    Get the Locale for the given tag.

    :param tag: The Locale's tag (e.g. ``de-DE``), case-insensitive.
    :return: The Locale.
    :raises ValueError: If no Locale exists for the tag.
    """
    for locale_tag, locale_class in LOCALES_BY_TAG.items():
        if locale_tag.lower() == tag.lower():
            return locale_class()

    raise AmazonOrdersError(f"Unknown locale {tag!r}; valid values are: {', '.join(LOCALES_BY_TAG)}.")
