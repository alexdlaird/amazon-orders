import logging
from typing import List, Optional

from bs4 import Tag

from amazonorders.entity.item import Item
from amazonorders.entity.parsable import Parsable
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.5"

logger = logging.getLogger(__name__)


class Shipment(Parsable):
    """
    An Amazon Shipment, which should contain one or more :class:`~amazonorders.entity.item.Item`'s.
    """

    def __init__(self,
                 parsed: Tag) -> None:
        super().__init__(parsed)

        #: The Shipment Items.
        self.items: List[Item] = self._parse_items()
        #: The Shipment delivery status.
        self.delivery_status: Optional[str] = self.safe_parse(self._parse_delivery_status)
        #: The Shipment tracking link.
        self.tracking_link: Optional[str] = self.safe_parse(self._parse_tracking_link)

    def __repr__(self) -> str:
        return "<Shipment: \"{}\">".format(self.items)

    def __str__(self) -> str:  # pragma: no cover
        return "Shipment: {}".format(self.items)

    def __lt__(self, other):
        if self.delivery_status:
            return self.delivery_status < other.delivery_status
        else:
            return str(self.items) < str(other.items)

    def _parse_items(self) -> List[Item]:
        items = [Item(x) for x in self.parsed.find_all("div", {"class": "yohtmlc-item"})]
        items.sort()
        return items

    def _parse_delivery_status(self) -> Optional[str]:
        tag = self.parsed.find("div", {"class": "js-shipment-info-container"})
        if tag:
            tag = tag.find("div", {"class": "a-row"})
            return tag.text.strip()
        else:
            return None

    def _parse_tracking_link(self) -> Optional[str]:
        tag = self.parsed.find("span", {"class": "track-package-button"})
        if tag:
            link_tag = tag.find("a")
            return "{}{}".format(BASE_URL, link_tag.attrs["href"])
        else:
            return None
