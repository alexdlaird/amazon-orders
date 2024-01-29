import logging
from typing import Optional

from bs4 import Tag

from amazonorders import constants
from amazonorders.entity.parsable import Parsable

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"

logger = logging.getLogger(__name__)


class Seller(Parsable):
    """
    An Amazon Seller of an Amazon `~amazonorders.entity.item.Item`.
    """

    def __init__(self,
                 parsed: Tag) -> None:
        super().__init__(parsed)

        #: The Seller name.
        self.name: str = self.safe_parse(self._parse_name)
        #: The Seller link.
        self.link: Optional[str] = self.safe_basic_parse(selector=constants.ENTITY_SELLER_LINK_SELECTOR, link=True)

    def __repr__(self) -> str:
        return "<Seller: \"{}\">".format(self.name)

    def __str__(self) -> str:  # pragma: no cover
        return "Seller: {}".format(self.name)

    def _parse_name(self) -> str:
        value = self.basic_parse(constants.ENTITY_SELLER_NAME_SELECTOR)

        if "Sold by:" in value:
            value = value.split("Sold by:")[1]
        return value.strip()
