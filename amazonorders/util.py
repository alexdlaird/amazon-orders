__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import importlib
import logging
import re
from datetime import date
from typing import List, Union, Optional, Callable, Any

from bs4 import Tag, BeautifulSoup
from dateutil import parser
from requests import Response

from amazonorders.selectors import Selector

logger = logging.getLogger(__name__)

#: Matches the Japanese ``年``/``月``/``日`` date notation used by amazon.co.jp (e.g.
#: ``2024年8月23日``), which ``dateutil`` cannot parse.
_JAPANESE_DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


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
                    tag += t
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
            t = parsed.select_one(s.css_selector)
            if t and _selector_text_matches(t, s):
                tag = t
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


def to_date(value: str,
            fuzzy: bool = False) -> Optional[date]:
    """
    Parse a date string into a :class:`datetime.date`.

    In addition to the formats understood by ``dateutil``, this recognizes the Japanese
    ``年``/``月``/``日`` notation used by amazon.co.jp (e.g. ``2024年8月23日``), which
    ``dateutil`` cannot parse and would otherwise silently misinterpret when ``fuzzy`` is
    enabled.

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
        return parser.parse(value, fuzzy=fuzzy).date()
    except (ValueError, OverflowError):
        return None


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
