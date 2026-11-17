import re
from datetime import date
from typing import Optional

from amazonauth.selectors import Selector, SelectorsFromText

from amazonorders import constants, selectors


_POLISH_MONTHS = {
    "stycznia": 1,
    "lutego": 2,
    "marca": 3,
    "kwietnia": 4,
    "maja": 5,
    "czerwca": 6,
    "lipca": 7,
    "sierpnia": 8,
    "września": 9,
    "października": 10,
    "listopada": 11,
    "grudnia": 12,
}
_POLISH_DATE = re.compile(r"(?<!\d)(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})(?!\d)")


def _parse_polish_date(value: Optional[str], fuzzy: bool) -> tuple[Optional[date], bool]:
    if not isinstance(value, str):
        return None, False

    value = value.strip()
    matches = list(_POLISH_DATE.finditer(value))
    if fuzzy and len(matches) > 1:
        return None, True
    if len(matches) != 1:
        return None, False

    match = matches[0]
    if not fuzzy and match.group(0) != value:
        return None, False

    month = _POLISH_MONTHS.get(match[2].casefold())
    if month is None:
        return None, False

    try:
        return date(int(match[3]), month, int(match[1])), True
    except ValueError:
        return None, True


class Constants(constants.Constants):
    CURRENCY_SYMBOL = "zł"
    DECIMAL_SEPARATOR = ","
    THOUSANDS_SEPARATOR = "."
    CURRENCY_FORMAT = "{amount} {symbol}"

    def parse_date(self, value: Optional[str], fuzzy: bool = False) -> Optional[date]:
        parsed, handled = _parse_polish_date(value, fuzzy)
        return parsed if handled else super().parse_date(value, fuzzy=fuzzy)


class Selectors(selectors.Selectors):
    ORDER_CANCELLED_TEXT = "Anulowane"
    ORDER_SHIPMENT_CANCELLED_SELECTOR = SelectorsFromText(
        lambda status_selector, cancelled_text: Selector(status_selector, text=cancelled_text),
        "ORDER_SHIPMENT_STATUS_SELECTOR", "ORDER_CANCELLED_TEXT")
    FIELD_ORDER_GRAND_TOTAL_LABELS = [re.compile(r"^\s*łączna kwota\s*:")]
    FIELD_ORDER_SUBTOTAL_LABELS = [re.compile(r"^\s*produkty\s*:")]
    FIELD_ORDER_SHIPPING_TOTAL_LABELS = [re.compile(r"^\s*pakowanie i wysyłka\s*:")]
    FIELD_ORDER_FREE_SHIPPING_LABELS = [re.compile(r"^\s*darmowa dostawa\s*:")]
    FIELD_ORDER_REFUND_TOTAL_LABELS = [re.compile(r"^\s*łączna kwota zwrotu\s*:?(?=\s*[-+−]?\d)")]
