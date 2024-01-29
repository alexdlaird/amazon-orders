import logging
from typing import Callable, Any, Optional, Type, Union

from bs4 import Tag

from amazonorders.constants import BASE_URL
from amazonorders.exception import AmazonOrdersError, AmazonOrderEntityError

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"

logger = logging.getLogger(__name__)


class Parsable:
    """
    A base class that contains a parsed representation of the entity in ``parsed``.
    """

    def __init__(self,
                 parsed: Tag) -> None:
        #: Parsed HTML data that can be used to populate the fields of the entity.
        self.parsed: Tag = parsed

    def safe_parse(self,
                   parse_function: Callable[..., Any],
                   **kwargs: Any) -> Any:
        """
        Execute the given parse function, handling any common parse exceptions and passing them as
        warnings to the logger, suppressing them as exceptions.

        :param parse_function: The parse function to attempt safe execution.
        :param kwargs: The ``kwargs`` will be passed to ``parse_function``.
        :return: The return value from ``parse_function``.
        """
        if not parse_function.__name__.startswith("_parse_") and parse_function.__name__ != "basic_parse":
            raise AmazonOrdersError("The name of the `parse_function` passed to this method must start with `_parse_`")

        try:
            return parse_function(**kwargs)
        except (AttributeError, IndexError, ValueError):
            logger.warning("When building {}, `{}` could not be parsed.".format(self.__class__.__name__,
                                                                                parse_function.__name__.split(
                                                                                    "_parse_")[1]),
                           exc_info=True)

    def basic_parse(self,
                    selector: Union[str, list],
                    link: bool = False,
                    return_type: Optional[Type] = None,
                    required: bool = False) -> Any:
        """
        This function will attempt to extract the text value of the given CSS selector(s), and is suitable
        for most basic functionality on a well-formed page.

        :param selector: The CSS selector of the element (``str`` to try a single element, or ``list`` to try a series of selectors).
        :param link: If a link, the value of ``src`` or ``href`` will be returned.
        :param return_type: Specify ``int`` or ``float`` to return a value other than ``str``.
        :param required: If required, an exception will be thrown instead of returning ``None``.
        :return: The cleaned up return value from the parsed ``selector``.
        """
        if isinstance(selector, str):
            selector = [selector]

        for s in selector:
            tag = self.parsed.select_one(s)
            if tag:
                if link:
                    key = "href"
                    if "src" in tag.attrs:
                        key = "src"
                    value = self.with_base_url(tag.attrs[key])
                else:
                    value = tag.text.strip()
                    # TODO: is there a dynamic way to accomplish this?
                    if return_type == float:
                        value = float(value)
                    elif return_type == int:
                        value = int(value)
                return value

        # None of the selectors were found
        if required:
            raise AmazonOrderEntityError(
                "When building {}, field for selector `{}` was None, but this is not allowed.".format(
                    self.__class__.__name__, selector))
        else:
            return None

    def safe_basic_parse(self,
                         selector: Union[str, list],
                         **kwargs) -> Any:
        """
        A helper function that uses :func:`basic_parse` as the ``parse_function()`` passed to :func:`safe_parse`.

        :param selector: The selector to pass to :func:`basic_parse`.
        :param kwargs: The ``kwargs`` will be passed to ``parse_function``.
        :return: The return value from :func:`basic_parse`.
        """
        return self.safe_parse(self.basic_parse, selector=selector, **kwargs)

    def with_base_url(self, url):
        """
        If the given URL is relative, the ``BASE_URL`` will be prepended.

        :param url: The URL to check.
        :return: The fully qualified URL.
        """
        if not url.startswith("http"):
            url = "{}{}".format(BASE_URL, url)
        return url
