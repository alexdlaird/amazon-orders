import logging

from amazonorders.entity.item import Item

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"

from amazonorders.session import BASE_URL

logger = logging.getLogger(__name__)


class Shipment:
    def __init__(self,
                 parsed,
                 order) -> None:
        self.parsed = parsed
        self.order = order

        self.items = self._parse_items()
        self.delivery_status = self._parse_delivery_status()
        self.tracking_link = self._parse_tracking_link()

    def __repr__(self) -> str:
        return "<Shipment: \"{}\">".format(self.items)

    def __str__(self) -> str:  # pragma: no cover
        return "Shipment: \"{}\"".format(self.items)

    def _parse_items(self):
        return [Item(x) for x in self.parsed.find_all("div", {"class": "yohtmlc-item"})]

    def _parse_tracking_link(self):
        try:
            tag = self.parsed.find("span", {"class": "track-package-button"})
            if tag:
                link_tag = tag.find("a")
                return "{}{}".format(BASE_URL, link_tag.attrs["href"])
        except (AttributeError, IndexError):
            logger.warning("When building Shipment, `tracking_link` could not be parsed.", exc_info=True)

    def _parse_delivery_status(self):
        try:
            tag = self.parsed.find("div", {"class": "js-shipment-info-container"}).find("div", {"class": "a-row"})
            return tag.text.strip()
        except (AttributeError, IndexError):
            logger.warning("When building Shipment, `delivery_status` could not be parsed.", exc_info=True)
