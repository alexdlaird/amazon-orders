__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

from typing import List

from bs4 import Tag


def select(parsed: Tag,
           selector: List[str]) -> Tag:
    """
    This is a helper function that extends BeautifulSoup's `select() <https://www.crummy.com/software/
    BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_ method to allow for multiple selectors. It will
    iterate through the list of ``selectors`` until one is found to return a populated list of ``Tag``'s, then
    return that.

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
    BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_ method to allow for multiple selectors. It will
    iterate through the list of ``selectors`` until one is found to return a populated single ``Tag``, then
    return that.

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
