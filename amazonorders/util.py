__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import importlib
import logging
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from typing import Iterable, List, Union, Optional, Callable, Any
from urllib.parse import SplitResult, urljoin, urlsplit

from bs4 import Tag, BeautifulSoup
from dateutil import parser
from requests import Response

from amazonorders.selectors import Selector

logger = logging.getLogger(__name__)


#: Matches the Japanese ``年``/``月``/``日`` date notation used by amazon.co.jp (e.g.
#: ``2024年8月23日``), which ``dateutil`` cannot parse.
_JAPANESE_DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")

#: Two fallback dates that differ in every component, so parsing against both reveals whether
#: ``dateutil`` would have filled in a day, month, or year missing from the text.
_DATE_DEFAULTS = [datetime(2001, 1, 1), datetime(2002, 2, 2)]


class AmazonSessionResponse:
    """
    A wrapper for the :class:`requests.Response` object, which also contains the parsed HTML.
    """

    def __init__(self, response: Response, bs4_parser: str, binary: bool = False) -> None:
        #: The request's response object.
        self.response: Response = response
        #: The parsed HTML from the response, which is empty if the response is ``binary``.
        self.parsed: Tag = BeautifulSoup("" if binary else self.response.text, bs4_parser)


def _selector_text_matches(tag: Tag, selector: Selector) -> bool:
    if selector.text is not None:
        return tag.text.strip() == selector.text
    if selector.text_contains is not None:
        return selector.text_contains.lower() in tag.text.lower()
    return False


def select(parsed: Tag, selector: Union[List[Union[str, Selector]], Union[str, Selector]]) -> List[Tag]:
    """
    This is a helper function that extends BeautifulSoup's `select() <https://www.crummy.com/software/
    BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_ method to allow for multiple selectors.
    The ``selector`` can be either a ``str`` or a ``list``. If a ``list`` is given, each selector in the list will be
    tried until one is found to return a populated list of ``Tag``'s, and that value will be returned.

    :param parsed: The ``Tag`` from which to attempt selection.
    :param selector: The CSS selector(s) for the field.
    :return: The selected tag.
    """
    if isinstance(selector, str) or isinstance(selector, Selector):
        selector = [selector]

    for s in selector:
        tag: list = []

        if isinstance(s, Selector):
            for t in parsed.select(s.css_selector):
                if t and _selector_text_matches(t, s):
                    tag.append(t)
        elif isinstance(s, str):
            tag = parsed.select(s)
        else:
            raise TypeError(f"Invalid selector type: {type(s)}")

        if tag:
            return tag

    return []


def select_one(parsed: Tag,
               selector: Union[List[Union[str, Selector]], Union[str, Selector]]) -> Optional[Tag]:
    """
    This is a helper function that extends BeautifulSoup's `select_one() <https://www.crummy.com/software/
    BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_ method to allow for multiple selectors.
    The ``selector`` can be either a ``str`` or a ``list``. If a ``list`` is given, each selector in the list will be
    tried until one is found to return a populated ``Tag``, and that value will be returned.

    :param parsed: The ``Tag`` from which to attempt selection.
    :param selector: The CSS selector(s) for the field.
    :return: The selection tag.
    """
    if isinstance(selector, str) or isinstance(selector, Selector):
        selector = [selector]

    for s in selector:
        tag: Optional[Tag] = None

        if isinstance(s, Selector):
            for t in parsed.select(s.css_selector):
                if t and _selector_text_matches(t, s):
                    tag = t
                    break
        elif isinstance(s, str):
            tag = parsed.select_one(s)
        else:
            raise TypeError(f"Invalid selector type: {type(s)}")

        if tag:
            return tag

    return None


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


def load_class(package: List[str], clazz: str) -> Union[Callable, Any]:
    """
    Import the given class from the given package, and return it.

    :param package: The package.
    :param clazz: The class to import.
    :return: The return class.
    """
    constants_mod = importlib.import_module(".".join(package))
    return getattr(constants_mod, clazz)


def has_display() -> bool:
    """
    Check whether a browser window can be opened here, as signing in with a browser window needs. On Linux, that
    needs a display (``DISPLAY`` or ``WAYLAND_DISPLAY``), which a server or a container usually doesn't have. Other
    platforms always have one.

    :return: Whether there's a display.
    """
    return not sys.platform.startswith("linux") or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


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


def cleanup_html_text(text: str) -> str:
    """
    Cleanup excessive whitespace within text that comes from an HTML block.

    :param text: The text to clean up.
    :return: The cleaned up text.
    """
    # First get rid of leading and trailing whitespace
    text = text.strip()
    # Reduce duplicated line returns, then replace line returns with periods
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = text.replace("\n", ". ")
    # Remove remaining duplicated whitespace of any kind
    text = re.sub(r"\s\s+", " ", text)
    # Remove duplicate periods at end of text.
    text = re.sub("\\.+($|\\s)", r".\1", text)
    if not text.endswith("."):
        text += "."
    return text


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
