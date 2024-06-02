__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"


def select(parsed, selector):
    """
    TODO: document

    :param parsed: The ``Tag`` from which to attempt selection.
    :param selector: The CSS selector(s) for the field.
    :return: The selected tag
    """

    if isinstance(selector, str):
        selector = [selector]

    for s in selector:
        tag = parsed.select(s)
        if tag:
            return tag

    return []


def select_one(parsed, selector):
    """
    TODO: document

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
