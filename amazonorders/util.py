__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"


def select(tag, selector):
    """
    TODO: document

    :param tag:
    :param selector:
    :return:
    """

    if isinstance(selector, str):
        selector = [selector]

    for s in selector:
        next_tag = tag.select(s)
        if next_tag:
            return next_tag

    return []


def select_one(tag, selector):
    """
    TODO: document

    :param tag:
    :param selector:
    :return:
    """

    if isinstance(selector, str):
        selector = [selector]

    for s in selector:
        next_tag = tag.select_one(s)
        if next_tag:
            return next_tag
