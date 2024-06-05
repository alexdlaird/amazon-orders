__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

from typing import List, Union

from bs4 import Tag


def select(parsed: Tag,
           selector: List[str]) -> List[Tag]:
    """
    This is a helper function that extends BeautifulSoup's `select() <https://www.crummy.com/software/
    BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_ method to allow for multiple selectors.
    The ``selector`` can be either a ``str`` or a ``list``. If a ``list`` is given, each selector in the list will be
    tried until one is found to return a populated list of ``Tag``'s, and that value will be returned.

    :param parsed: The ``Tag`` from which to attempt selection.
    :param selector: The CSS selector(s) for the field.
    :return: The selected tag.
    """

    if isinstance(selector, str):
        selector = [selector]

    for s in selector:
        tag = parsed.select(s)
        if tag:
            return tag

    return []


def select_one(parsed: Tag,
               selector: List[str]) -> Tag:
    """
    This is a helper function that extends BeautifulSoup's `select_one() <https://www.crummy.com/software/
    BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_ method to allow for multiple selectors.
    The ``selector`` can be either a ``str`` or a ``list``. If a ``list`` is given, each selector in the list will be
    tried until one is found to return a populated ``Tag``, and that value will be returned.

    :param parsed: The ``Tag`` from which to attempt selection.
    :param selector: The CSS selector(s) for the field.
    :return:
    """

    if isinstance(selector, str):
        selector = [selector]

    for s in selector:
        tag = parsed.select_one(s)
        if tag:
            return tag


def to_type(value: str) -> Union[int, float, bool, str, None]:
    """
    Attempt to convert ``value`` to its primitive type of ``int``, ``float``, or ``bool``.

    If ``value`` is an empty string, ``None`` will be returned.

    :param value: The value to convert.
    :return: The converted value.
    """
    if not value or value == "":
        return None

    try:
        value = int(value)
    except ValueError:
        try:
            value = float(value)
        except ValueError:
            pass

    if isinstance(value, str):
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False

    return value
