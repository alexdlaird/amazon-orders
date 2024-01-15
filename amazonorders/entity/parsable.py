import logging

from amazonorders.exception import AmazonOrdersError

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"

logger = logging.getLogger(__name__)


class Parsable:
    def __init__(self,
                 parsed):
        self.parsed = parsed

    def _safe_parse(self, parse_function):
        if not parse_function.__name__.startswith("_parse_"):
            raise AmazonOrdersError("This name of the `parse_function` passed to this method must start with `_parse_`")

        try:
            return parse_function()
        except (AttributeError, IndexError):
            logger.warning("When building {}, `{}` could not be parsed.".format(self.__class__.__name__,
                                                                                parse_function.__name__.split(
                                                                                    "_parse_")[1]),
                           exc_info=True)
