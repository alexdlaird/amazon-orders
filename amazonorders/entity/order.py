import logging
from datetime import datetime
from urllib.parse import urlparse
from urllib.parse import parse_qs

from bs4 import BeautifulSoup

from amazonorders.entity.recipient import Recipient
from amazonorders.entity.shipment import Shipment
from amazonorders.entity.item import Item
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"

logger = logging.getLogger(__name__)


class Order:
    def __init__(self, parsed, clone=None) -> None:
        self.parsed = parsed

        if clone:
            self.shipments = clone.shipments
            self.items = clone.items
            self.order_details_link = clone.order_details_link
            self.order_number = clone.order_number
            self.grand_total = clone.grand_total
            self.order_placed_date = clone.order_placed_date
            self.recipient = clone.recipient
        else:
            self.shipments = self._parse_shipments()
            self.items = self._parse_items()
            self.order_details_link = self._parse_order_details_link()
            self.order_number = self._parse_order_number()
            self.grand_total = self._parse_grand_total()
            self.order_placed_date = self._parse_order_placed_date()
            self.recipient = self._parse_recipient()

        # These fields will only be populated from the full order details page
        # TODO: populate these
        self.payment_method = None
        self.payment_method_last_4 = None
        self.subtotal = None
        self.shipping_total = None
        self.total_before_tax = None
        self.estimated_tax = None
        self.sold_by = None
        self.sold_by_link = None
        self.condition = None
        self.order_shipped_date = None
        self.tracking_link = None
        # This should just be a boolean
        self.delivered = None

    def __repr__(self) -> str:
        return "<Order: \"{}\">".format(self.items)

    def __str__(self) -> str:  # pragma: no cover
        return str(self.items)

    def _parse_shipments(self):
        return [Shipment(x, self) for x in self.parsed.find_all("div", {"class": "shipment"})]

    def _parse_items(self):
        return [Item(x) for x in self.parsed.find_all("div", {"class": "yohtmlc-item"})]

    def _parse_order_details_link(self):
        try:
            tag = self.parsed.find("a", {"class": "yohtmlc-order-details-link"})
            return "{}{}".format(BASE_URL, tag.attrs["href"])
        except AttributeError:
            logger.warning("When building Order, `order_details_link` could not be parsed.", exc_info=True)

    def _parse_order_number(self):
        if not self.order_details_link:
            # TODO: Upgrade this to a lib-specific exception
            raise Exception("Order._parse_order_link() must be called first.")

        try:
            parsed_url = urlparse(self.order_details_link)
            return parse_qs(parsed_url.query)["orderID"][0]
        except (AttributeError, IndexError):
            logger.warning("When building Order, `order_number` could not be parsed.", exc_info=True)

    def _parse_grand_total(self):
        try:
            tag = self.parsed.find("div", {"class": "yohtmlc-order-total"})
            return tag.text.strip().strip("$")
        except AttributeError:
            logger.warning("When building Order, `grand_total` could not be parsed.", exc_info=True)

    def _parse_order_placed_date(self):
        try:
            tag = self.parsed.find("div", {"class": "a-span3"}).find_all("span")
            date_str = tag[1].text.strip()
            return datetime.strptime(date_str, "%B %d, %Y").date()
        except (AttributeError, IndexError):
            logger.warning("When building Order, `order_placed_date` could not be parsed.", exc_info=True)

    def _parse_recipient(self):
        try:
            script_id = self.parsed.find("div",
                                         id=lambda value: value and value.startswith("shipToInsertionNode")).attrs["id"]
            tag = self.parsed.find("script",
                                   id="shipToData-shippingAddress-{}".format(script_id.split("-")[2]))
            script_parsed = BeautifulSoup(str(tag.contents[0]).strip(), "html.parser")
            return Recipient(script_parsed)
        except (AttributeError, IndexError):
            logger.warning("When building Order, `recipient` could not be parsed.", exc_info=True)
