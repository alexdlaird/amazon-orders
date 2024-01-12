import logging
from datetime import datetime
from urllib.parse import urlparse
from urllib.parse import parse_qs

from bs4 import BeautifulSoup

from amazonorders.entity.recipient import Recipient
from amazonorders.entity.shipment import Shipment
from amazonorders.entity.item import Item
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"

logger = logging.getLogger(__name__)


class Order:
    def __init__(self,
                 parsed,
                 full_details=False,
                 clone=None) -> None:
        self.parsed = parsed
        self.full_details = full_details

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
            self.items = self._parse_items()
            self.payment_method = self._parse_payment_method()
            self.payment_method_last_4 = self._parse_payment_method_last_4()
            self.subtotal = self._parse_subtotal()
            self.shipping_total = self._parse_shipping_total()
            self.subscription_discount = self._parse_subscription_discount()
            self.total_before_tax = self._parse_total_before_tax()
            self.estimated_tax = self._parse_estimated_tax()
            self.refund_total = self._parse_refund_total()
            self.order_shipped_date = self._parse_order_shipping_date()
            self.refund_completed_date = self._parse_refund_completed_date()

    def __repr__(self) -> str:
        return "<Order #{}: \"{}\">".format(self.order_number, self.items)

    def __str__(self) -> str:  # pragma: no cover
        return "Order #{}: \"{}\"".format(self.order_number, self.items)

    def _parse_shipments(self):
        return [Shipment(x, self) for x in self.parsed.find_all("div", {"class": "shipment"})]

    def _parse_items(self):
        return [Item(x) for x in self.parsed.find_all("div", {"class": "yohtmlc-item"})]

    def _parse_order_details_link(self):
        try:
            tag = self.parsed.find("a", {"class": "yohtmlc-order-details-link"})
            if tag:
                return "{}{}".format(BASE_URL, tag.attrs["href"])
        except AttributeError:
            logger.warning("When building Order, `order_details_link` could not be parsed.", exc_info=True)

    def _parse_order_number(self):
        try:
            if self.order_details_link:
                parsed_url = urlparse(self.order_details_link)
                return parse_qs(parsed_url.query)["orderID"][0]
            else:
                tag = self.parsed.find("bdi", dir="ltr")
                return tag.text.strip()
        except (AttributeError, IndexError):
            # TODO: refactor entities to all extend a base entity, which has this base parse function with this except
            logger.warning("When building Order, `order_number` could not be parsed.", exc_info=True)

    def _parse_grand_total(self):
        try:
            tag = self.parsed.find("div", {"class": "yohtmlc-order-total"})
            if tag:
                tag = tag.find("span", {"class": "value"})
            else:
                for tag in self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"}):
                    if "grand total" in tag.text.lower():
                        tag = tag.find("div", {"class": "a-span-last"})
            return tag.text.strip().replace("$", "")
        except AttributeError:
            logger.warning("When building Order, `grand_total` could not be parsed.", exc_info=True)

    def _parse_order_placed_date(self):
        try:
            tag = self.parsed.find("span", {"class": "order-date-invoice-item"})
            if tag:
                date_str = tag.text.split("Ordered on")[1].strip()
            else:
                tag = self.parsed.find("div", {"class": "a-span3"}).find_all("span")
                date_str = tag[1].text.strip()
            return datetime.strptime(date_str, "%B %d, %Y").date()
        except (AttributeError, IndexError):
            logger.warning("When building Order, `order_placed_date` could not be parsed.", exc_info=True)

    def _parse_recipient(self):
        try:
            tag = self.parsed.find("div", {"class": "displayAddressDiv"})
            if not tag:
                script_id = self.parsed.find("div",
                                             id=lambda value: value and value.startswith("shipToInsertionNode")).attrs["id"]
                tag = self.parsed.find("script",
                                       id="shipToData-shippingAddress-{}".format(script_id.split("-")[2]))
                tag = BeautifulSoup(str(tag.contents[0]).strip(), "html.parser")
            return Recipient(tag)
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
            for tag in self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"}):
                if "subtotal" in tag.text.lower():
                    return tag.find("div", {"class": "a-span-last"}).text.strip().replace("$", "")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `subtotal` could not be parsed.", exc_info=True)

    def _parse_shipping_total(self):
        try:
            for tag in self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"}):
                if "shipping" in tag.text.lower():
                    return tag.find("div", {"class": "a-span-last"}).text.strip().replace("$", "")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `shipping_total` could not be parsed.", exc_info=True)

    def _parse_subscription_discount(self):
        try:
            for tag in self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"}):
                if "subscribe" in tag.text.lower():
                    return tag.find("div", {"class": "a-span-last"}).text.strip().replace("$", "")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `subscription_discount` could not be parsed.", exc_info=True)

    def _parse_total_before_tax(self):
        try:
            for tag in self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"}):
                if "before tax" in tag.text.lower():
                    return tag.find("div", {"class": "a-span-last"}).text.strip().replace("$", "")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `total_before_tax` could not be parsed.", exc_info=True)

    def _parse_estimated_tax(self):
        try:
            for tag in self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"}):
                if "estimated tax" in tag.text.lower():
                    return tag.find("div", {"class": "a-span-last"}).text.strip().replace("$", "")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `estimated_tax` could not be parsed.", exc_info=True)

    def _parse_refund_total(self):
        try:
            for tag in self.parsed.find("div", id="od-subtotals").find_all("div", {"class": "a-row"}):
                if "refund total" in tag.text.lower() and "tax refund" not in tag.text.lower():
                    return tag.find("div", {"class": "a-span-last"}).text.strip().replace("$", "")
        except (AttributeError, IndexError):
            logger.warning("When building Order, `refund_total` could not be parsed.", exc_info=True)

    def _parse_order_shipping_date(self):
        try:
            # TODO: find a better way to do this
            if "Items shipped:" in self.parsed.text:
                date_str = self.parsed.text.split("Items shipped:")[1].strip().split("-")[0].strip()
                return datetime.strptime(date_str, "%B %d, %Y").date()
        except (AttributeError, IndexError):
            logger.warning("When building Order, `order_shipping_date` could not be parsed.", exc_info=True)

    def _parse_refund_completed_date(self):
        try:
            # TODO: find a better way to do this
            if "Refund: Completed" in self.parsed.text:
                date_str = self.parsed.text.split("Refund: Completed")[1].strip().split("-")[0].strip()
                return datetime.strptime(date_str, "%B %d, %Y").date()
        except (AttributeError, IndexError):
            logger.warning("When building Order, `refund_completed_date` could not be parsed.", exc_info=True)
