import logging

from amazonorders.entity.item import Item
from amazonorders.entity.parsable import Parsable

from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"

logger = logging.getLogger(__name__)


class Shipment(Parsable):
    def __init__(self,
                 parsed,
                 order) -> None:
        super().__init__(parsed)

        self.order = order

        self.items = self._parse_items()
        self.delivery_status = self._safe_parse(self._parse_delivery_status)
        self.tracking_link = self._safe_parse(self._parse_tracking_link)

    def __repr__(self) -> str:
        return "<Shipment: \"{}\">".format(self.items)

    def __str__(self) -> str:  # pragma: no cover
        return "Shipment: \"{}\"".format(self.items)

    def _parse_items(self):
        return [Item(x) for x in self.parsed.find_all("div", {"class": "yohtmlc-item"})]

    def _parse_delivery_status(self):
        tag = self.parsed.find("div", {"class": "js-shipment-info-container"})
        if tag:
            tag = tag.find("div", {"class": "a-row"})
            return tag.text.strip()

    def _parse_tracking_link(self):
        tag = self.parsed.find("span", {"class": "track-package-button"})
        if tag:
            link_tag = tag.find("a")
            return "{}{}".format(BASE_URL, link_tag.attrs["href"])
