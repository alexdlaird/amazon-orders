__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import importlib
import logging
import re
from datetime import date, datetime
from typing import List, Union, Optional, Callable, Any

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

    def __init__(self, response: Response, bs4_parser: str) -> None:
        #: The request's response object.
        self.response: Response = response
        #: The parsed HTML from the response.
        self.parsed: Tag = BeautifulSoup(self.response.text, bs4_parser)


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
