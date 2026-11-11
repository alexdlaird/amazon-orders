__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
import unicodedata
from datetime import date, datetime
from typing import Iterable, Optional, Union
from urllib.parse import SplitResult, parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from dateutil import parser


logger = logging.getLogger(__name__)

__all__ = [
    "to_type",
    "to_decimal_point",
    "strip_currency_text",
    "to_count",
    "to_date",
    "resolve_site_url",
    "with_query_param",
    "attribute_text",
]


#: Matches the Japanese ``年``/``月``/``日`` date notation used by amazon.co.jp (e.g.
#: ``2024年8月23日``), which ``dateutil`` cannot parse.
_JAPANESE_DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")

#: Two fallback dates that differ in every component, so parsing against both reveals whether
#: ``dateutil`` would have filled in a day, month, or year missing from the text.
_DATE_DEFAULTS = [datetime(2001, 1, 1), datetime(2002, 2, 2)]


def to_type(value: str) -> Union[int, float, bool, str, None]:
    """
    Attempt to convert ``value`` to its primitive type of ``int``, ``float``, or ``bool``.

    If ``value`` is an empty string, ``None`` will be returned.

    :param value: The value to convert.
    :return: The converted value.
    """
    if not value or value == "":
        return None

    rv: Union[int, float, bool, str] = value

    try:
        rv = int(rv)
    except ValueError:
        try:
            rv = float(rv)
        except ValueError:
            pass

    if isinstance(rv, str):
        if rv.lower() == "true":
            rv = True
        elif rv.lower() == "false":
            rv = False

    return rv


def to_decimal_point(value: str) -> str:
    """
    Normalize a number written with either decimal mark to use ``.``, removing thousands separators.
    A trailing ``.`` or ``,`` followed by one or two digits is the decimal mark, and any other ``.``,
    ``,``, or ``'`` groups thousands (e.g. ``1,234.56``, ``1.234,56``, and ``1'234.56`` all become
    ``1234.56``, and ``1,234`` becomes ``1234``).

    :param value: The number to normalize.
    :return: The number with a ``.`` decimal mark and no thousands separators.
    """
    decimal_mark = re.search(r"[.,](\d{1,2})$", value)
    whole = re.sub(r"[.,']", "", value[:decimal_mark.start()] if decimal_mark else value)
    return f"{whole}.{decimal_mark.group(1)}" if decimal_mark else whole


def strip_currency_text(value: str) -> str:
    """
    Remove the currency symbols (e.g. ``$``, ``€``, or ``￥``), currency-code letters (e.g. ``CDN`` or ``zł``), and
    whitespace from an amount, leaving its digits, sign, and separators.

    :param value: The amount to strip.
    :return: The amount without its currency text.
    """
    return "".join(character for character in value
                   if not (character.isalpha() or character.isspace() or unicodedata.category(character) == "Sc"))


def to_count(value: str,
             pattern: str = r"^\s*{count}") -> Optional[int]:
    """
    Parse a whole number from text, allowing ``,``, ``.``, ``'``, or space thousands separators (e.g.
    ``1,234``, ``1.234``, or ``1 234``).

    :param value: The text containing the number.
    :param pattern: A regex locating the number, with ``{count}`` marking where it appears. Defaults to a
        number at the start of the text.
    :return: The number, or ``None`` if ``pattern`` does not match.
    """
    match = re.search(pattern.replace("{count}", r"(?P<count>\d+(?:[.,'\s]\d{3})*)"), value)
    return int(re.sub(r"\D", "", match["count"])) if match else None


def to_date(value: Optional[str],
            fuzzy: bool = False) -> Optional[date]:
    """
    Parse a date string into a :class:`datetime.date`.

    In addition to the formats understood by ``dateutil``, this recognizes the Japanese
    ``年``/``月``/``日`` notation used by amazon.co.jp (e.g. ``2024年8月23日``), which
    ``dateutil`` cannot parse and would otherwise silently misinterpret when ``fuzzy`` is
    enabled. A date missing its day, month, or year is not parsed, rather than completed from
    today's date.

    :param value: The date string to parse.
    :param fuzzy: Whether to let ``dateutil`` ignore unknown tokens when parsing.
    :return: The parsed ``date``, or ``None`` if it could not be parsed.
    """
    if not value:
        return None

    match = _JAPANESE_DATE_RE.search(value)
    if match:
        year, month, day = (int(group) for group in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    try:
        parsed_dates = {parser.parse(value, fuzzy=fuzzy, default=default).date() for default in _DATE_DEFAULTS}
    except (ValueError, OverflowError):
        return None

    if len(parsed_dates) > 1:
        logger.debug(f"Date {value!r} is missing a day, month, or year, so it was not parsed.")
        return None

    return parsed_dates.pop()


def _site_host(host: Optional[str]) -> str:
    return (host or "").lower().removeprefix("www.")


def _effective_port(url: SplitResult) -> Optional[int]:
    return url.port or {"http": 80, "https": 443}.get(url.scheme)


def _is_same_site_url(url: SplitResult, base_url: SplitResult) -> bool:
    return (url.scheme == base_url.scheme and
            url.username is None and url.password is None and
            bool(url.hostname) and _site_host(url.hostname) == _site_host(base_url.hostname) and
            _effective_port(url) == _effective_port(base_url))


def resolve_site_url(url: str, base_url: str) -> Optional[str]:
    """
    Resolve a link found on a page against ``base_url``, but only if it stays on the same Amazon site (with or
    without ``www.``), so the session's cookies are never sent to another host.

    :param url: The link, relative or absolute.
    :param base_url: The Amazon site's base URL.
    :return: The resolved URL, or ``None`` if it's malformed or on another site.
    """
    try:
        resolved_url = urljoin(base_url, url)
        same_site = _is_same_site_url(urlsplit(resolved_url), urlsplit(base_url))
    except ValueError:
        same_site = False

    if not same_site:
        logger.warning(f"Ignoring a link to another site: {url}")
        return None

    return resolved_url


def with_query_param(url: str, name: str, value: Optional[str]) -> str:
    """
    Set a query parameter on a URL, replacing any value it already has, or remove it when ``value`` is ``None``.

    :param url: The URL.
    :param name: The query parameter's name.
    :param value: The query parameter's value, or ``None`` to remove it.
    :return: The URL with the query parameter set, or removed. Removing one the URL doesn't have returns it unchanged.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    kept = [(key, val) for key, val in query if key != name]
    if value is None and len(kept) == len(query):
        return url

    if value is not None:
        kept.append((name, value))

    return urlunsplit(parts._replace(query=urlencode(kept)))


def attribute_text(value: Union[str, Iterable[str]]) -> str:
    """
    Get a ``<tag>`` attribute's value as text. BeautifulSoup gives multi-valued attributes, like ``class``, as a
    list, which is joined with spaces, as they're written in the HTML.

    :param value: The attribute's value.
    :return: The attribute's value as text.
    """
    if isinstance(value, str):
        return value

    return " ".join(value)
