import logging
from datetime import datetime
from urllib.parse import urlparse
from urllib.parse import parse_qs

from bs4 import BeautifulSoup

from amazonorders.entity.recipient import Recipient
from amazonorders.entity.seller import Seller
from amazonorders.entity.shipment import Shipment
from amazonorders.entity.item import Item
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"

logger = logging.getLogger(__name__)


class Order:
    def __init__(self,
                 parsed,
                 full_details=False,
                 clone=None) -> None:
        self.parsed = parsed
        self.full_details = full_details

        # TODO: add support for this to be parsed from the order-details page as well (not just through a clone)
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

        if self.full_details:
            self.payment_method = self._parse_payment_method()
            self.payment_method_last_4 = self._parse_payment_method_last_4()
            self.subtotal = self._parse_subtotal()
            self.shipping_total = self._parse_shipping_total()
            self.total_before_tax = self._parse_total_before_tax()
            self.estimated_tax = self._parse_estimated_tax()
            self.seller = self._parse_seller()
            self.condition = self._parse_condition()
            self.order_shipped_date = self._parse_order_shipping_date()
            self.tracking_link = self._parse_tracking_link()
            self.delivered = self._parse_delivered()

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
            tag = self.parsed.find("div", {"class": "yohtmlc-order-total"}).find("span", {"class": "value"})
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

    def _parse_payment_method(self):
        try:
            tag = self.parsed.find("img", {"class": "pmts-payment-credit-card-instrument-logo"})
            if tag:
                return tag.attrs["alt"]
        except (AttributeError, IndexError):
            logger.warning("When building Order, `payment_method` could not be parsed.", exc_info=True)

    def _parse_payment_method_last_4(self):
        try:
            tag = self.parsed.find("img", {"class": "pmts-payment-credit-card-instrument-logo"})
            if tag:
                ending_sibling = tag.find_next_siblings()[-1]
                return ending_sibling.text.split("ending in")[1].strip()
        except (AttributeError, IndexError):
            logger.warning("When building Order, `payment_method_last_4` could not be parsed.", exc_info=True)

    def _parse_subtotal(self):
        try:
            tag = self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"})
            return tag[0].find("div", {"class": "a-span-last"}).text.strip().strip("$")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `subtotal` could not be parsed.", exc_info=True)

    def _parse_shipping_total(self):
        try:
            tag = self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"})
            return tag[1].find("div", {"class": "a-span-last"}).text.strip().strip("$")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `shipping_total` could not be parsed.", exc_info=True)

    def _parse_total_before_tax(self):
        try:
            tag = self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"})
            return tag[3].find("div", {"class": "a-span-last"}).text.strip().strip("$")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `total_before_tax` could not be parsed.", exc_info=True)

    def _parse_estimated_tax(self):
        try:
            tag = self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"})
            return tag[4].find("div", {"class": "a-span-last"}).text.strip().strip("$")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `estimated_tax` could not be parsed.", exc_info=True)

    def _parse_seller(self):
        try:
            for tag in self.parsed.find("div", {"class": "yohtmlc-item"}).find_all("div"):
                if "Sold by:" in tag.text:
                    return Seller(tag, order=self)
        except (AttributeError, IndexError):
            logger.warning("When building Order, `seller` could not be parsed.", exc_info=True)

    def _parse_condition(self):
        try:
            for tag in self.parsed.find("div", {"class": "yohtmlc-item"}).find_all("div"):
                if "Condition:" in tag.text:
                    return tag.text.split("Condition:")[1].strip()
        except (AttributeError, IndexError):
            logger.warning("When building Order, `condition` could not be parsed.", exc_info=True)

    def _parse_order_shipping_date(self):
        try:
            # TODO: find a better way to do this
            if "Items shipped:" in self.parsed.text:
                date_str = self.parsed.text.split("Items shipped:")[1].strip().split("-")[0].strip()
                return datetime.strptime(date_str, "%B %d, %Y").date()
        except (AttributeError, IndexError):
            logger.warning("When building Order, `order_shipping_date` could not be parsed.", exc_info=True)

    def _parse_tracking_link(self):
        try:
            tag = self.parsed.find("span", {"class": "track-package-button"}).find("a")
            if tag:
                return "{}{}".format(BASE_URL, tag.attrs["href"])
        except (AttributeError, IndexError):
            logger.warning("When building Order, `tracking_link` could not be parsed.", exc_info=True)

    def _parse_delivered(self):
        # This should just be a boolean
        try:
            tag = self.parsed.find("div", {"class": "js-shipment-info-container"})
            return "Delivered" in tag.text
        except (AttributeError, IndexError):
            logger.warning("When building Order, `delivered` could not be parsed.", exc_info=True)
