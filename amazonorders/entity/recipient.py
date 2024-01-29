import logging
from typing import Optional

from bs4 import Tag

from amazonorders import constants
from amazonorders.entity.parsable import Parsable

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"

logger = logging.getLogger(__name__)


class Recipient(Parsable):
    """
    The person receiving an Amazon `~amazonorders.entity.order.Order`.
    """

    def __init__(self,
                 parsed: Tag) -> None:
        super().__init__(parsed)

        #: The Recipient name.
        self.name: str = self.safe_basic_parse(selector=constants.ENTITY_RECIPIENT_NAME_SELECTOR, required=True)
        #: The Recipient address.
        self.address: Optional[str] = self.safe_parse(self._parse_address)

    def __repr__(self) -> str:
        return "<Recipient: \"{}\">".format(self.name)

    def __str__(self) -> str:  # pragma: no cover
        return "Recipient: {}".format(self.name)

    def _parse_address(self) -> Optional[str]:
        tag = self.parsed.select_one("li.displayAddressAddressLine1")
        if tag:
            value = tag.text.strip()
            next_tag = self.parsed.select_one("li.displayAddressAddressLine2")
            if next_tag:
                value += "{}\n{}".format(tag.text.strip(), next_tag)
            next_tag = self.parsed.select_one("li.displayAddressCityStateOrRegionPostalCode")
            if next_tag:
                value += "\n{}".format(next_tag.text.strip())
            next_tag = self.parsed.select_one("li.displayAddressCountryName")
            if next_tag:
                value += "\n{}".format(next_tag.text.strip())
        else:
            value = self.parsed.select_one("div:nth-child(2)").text
        return value.strip()
