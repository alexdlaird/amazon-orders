import json
import logging
from datetime import datetime, date
from typing import List, Optional, TypeVar
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, Tag

from amazonorders import constants
from amazonorders.entity.item import Item
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.recipient import Recipient
from amazonorders.entity.shipment import Shipment

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"

logger = logging.getLogger(__name__)

Entity = TypeVar('Entity', bound='Order')


class Order(Parsable):
    """
    An Amazon Order.
    """

    def __init__(self,
                 parsed: Tag,
                 full_details: bool = False,
                 clone: Optional[Entity] = None) -> None:
        super().__init__(parsed)

        #: If the Orders full details were populated from its details page.
        self.full_details: bool = full_details

        #: The Order Shipments.
        self.shipments: List[Shipment] = clone.shipments if clone else self._parse_shipments()
        #: The Order Items.
        self.items: List[Item] = clone.items if clone and not full_details else self._parse_items()
        #: The Order number.
        self.order_number: str = clone.order_number if clone else self.safe_parse(self._parse_order_number)
        #: The Order details link.
        self.order_details_link: Optional[str] = clone.order_details_link if clone else self.safe_parse(
            self._parse_order_details_link)
        #: The Order grand total.
        self.grand_total: float = clone.grand_total if clone else self.safe_parse(self._parse_grand_total)
        #: The Order placed date.
        self.order_placed_date: date = clone.order_placed_date if clone else self.safe_parse(
            self._parse_order_placed_date)
        #: The Order Recipients.
        self.recipient: Recipient = clone.recipient if clone else self.safe_parse(self._parse_recipient)

        # Fields below this point are only populated if `full_details` is True

        #: The Order payment method.
        self.payment_method: Optional[str] = self._parse_payment_method() if self.full_details else None
        #: The Order payment method's last 4 digits.
        self.payment_method_last_4: Optional[str] = self._parse_payment_method_last_4() if self.full_details else None
        #: The Order subtotal.
        self.subtotal: Optional[float] = self._parse_subtotal() if self.full_details else None
        #: The Order shipping total.
        self.shipping_total: Optional[float] = self._parse_shipping_total() if self.full_details else None
        #: The Order Subscribe & Save discount.
        self.subscription_discount: Optional[float] = self._parse_subscription_discount() if self.full_details else None
        #: The Order total before tax.
        self.total_before_tax: Optional[float] = self._parse_total_before_tax() if self.full_details else None
        #: The Order estimated tax.
        self.estimated_tax: Optional[float] = self._parse_estimated_tax() if self.full_details else None
        #: The Order refund total.
        self.refund_total: Optional[float] = self._parse_refund_total() if self.full_details else None
        #: The Order shipped date.
        self.order_shipped_date: Optional[date] = self._parse_order_shipping_date() if self.full_details else None
        #: The Order refund total.
        self.refund_completed_date: Optional[date] = self._parse_refund_completed_date() if self.full_details else None

    def __repr__(self) -> str:
        return "<Order #{}: \"{}\">".format(self.order_number, self.items)

    def __str__(self) -> str:  # pragma: no cover
        return "Order #{}: {}".format(self.order_number, self.items)

    def _parse_shipments(self) -> List[Shipment]:
        shipments = [Shipment(x) for x in self.parsed.select(constants.ENTITY_ORDER_SHIPMENT_SELECTOR)]
        shipments.sort()
        return shipments

    def _parse_items(self) -> List[Item]:
        items = [Item(x) for x in self.parsed.select(constants.ITEM_SELECTOR)]
        items.sort()
        return items

    def _parse_order_details_link(self) -> Optional[str]:
        value = self.basic_parse(constants.ENTITY_ORDER_DETAILS_LINK_SELECTOR, link=True)

        if not value and self.order_number:
            value = "{}?orderID={}".format(constants.ORDER_DETAILS_URL, self.order_number)

        return value

    def _parse_order_number(self) -> str:
        try:
            order_details_link = self._parse_order_details_link()
        except:
            # We're not using safe_parse here because it's fine if this fails, no need for noise
            order_details_link = None
        if order_details_link:
            parsed_url = urlparse(order_details_link)
            return parse_qs(parsed_url.query)["orderID"][0]
        else:
            return self.basic_parse(constants.ENTITY_ORDER_NUMBER_SELECTOR, required=True)

    def _parse_grand_total(self) -> float:
        value = self.basic_parse(constants.ENTITY_ORDER_TOTAL_SELECTOR)

        if not value:
            for tag in self.parsed.select(constants.ENTITY_ORDER_SUBTOTALS_DIV_ITERATOR_SELECTOR):
                if "grand total" in tag.text.lower():
                    value = tag.select_one("div.a-span-last").text.strip()
                    break

        return float(value.replace("$", ""))

    def _parse_order_placed_date(self) -> date:
        tag = self.parsed.select_one(constants.ENTITY_ORDER_PLACED_DATE_SELECTOR)
        if tag:
            date_str = tag.text.split("Ordered on")[1].strip()
        else:
            tag = self.parsed.select("div.a-span3 span")
            # TODO: using nth-child here isn't working, investigate
            date_str = tag[1].text.strip()
        return datetime.strptime(date_str, "%B %d, %Y").date()

    def _parse_recipient(self) -> Recipient:
        tag = self.parsed.select_one("div.displayAddressDiv")
        if not tag:
            tag = self.parsed.select_one("div.recipient span.a-declarative")
            if tag:
                inline_content = tag.get("data-a-popover", {}).get("inlineContent")
                if inline_content:
                    tag = BeautifulSoup(json.loads(inline_content), "html.parser")

            if not tag:
                # TODO: there are multiple shipToData tags, we should double check we're picking the right one associated with the order
                parent_tag = self.parsed.find_parent().select_one("script[id^='shipToData']")
                tag = BeautifulSoup(str(parent_tag.contents[0]).strip(), "html.parser")
        return Recipient(tag)

    def _parse_payment_method(self) -> Optional[str]:
        tag = self.parsed.select_one(constants.ENTITY_ORDER_PAYMENT_METHOD_SELECTOR)
        if tag:
            return tag["alt"]
        else:
            return None

    def _parse_payment_method_last_4(self) -> Optional[str]:
        tag = self.parsed.select_one(constants.ENTITY_ORDER_PAYMENT_METHOD_SELECTOR)
        if tag:
            ending_sibling = tag.find_next_siblings()[-1]
            return ending_sibling.text.split("ending in")[1].strip()
        else:
            return None

    def _parse_subtotal(self) -> Optional[float]:
        for tag in self.parsed.select(constants.ENTITY_ORDER_SUBTOTALS_DIV_ITERATOR_SELECTOR):
            if "subtotal" in tag.text.lower():
                return float(tag.select_one("div.a-span-last").text.strip().replace("$", ""))

        return None

    def _parse_shipping_total(self) -> Optional[float]:
        for tag in self.parsed.select(constants.ENTITY_ORDER_SUBTOTALS_DIV_ITERATOR_SELECTOR):
            if "shipping" in tag.text.lower():
                return float(tag.select_one("div.a-span-last").text.strip().replace("$", ""))

        return None

    def _parse_subscription_discount(self) -> Optional[float]:
        for tag in self.parsed.select(constants.ENTITY_ORDER_SUBTOTALS_DIV_ITERATOR_SELECTOR):
            if "subscribe" in tag.text.lower():
                return float(tag.select_one("div.a-span-last").text.strip().replace("$", ""))

        return None

    def _parse_total_before_tax(self) -> Optional[float]:
        for tag in self.parsed.select(constants.ENTITY_ORDER_SUBTOTALS_DIV_ITERATOR_SELECTOR):
            if "before tax" in tag.text.lower():
                return float(tag.select_one("div.a-span-last").text.strip().replace("$", ""))

        return None

    def _parse_estimated_tax(self) -> Optional[float]:
        for tag in self.parsed.select(constants.ENTITY_ORDER_SUBTOTALS_DIV_ITERATOR_SELECTOR):
            if "estimated tax" in tag.text.lower():
                return float(tag.select_one("div.a-span-last").text.strip().replace("$", ""))

        return None

    def _parse_refund_total(self) -> Optional[float]:
        for tag in self.parsed.select(constants.ENTITY_ORDER_SUBTOTALS_DIV_ITERATOR_SELECTOR):
            if "refund total" in tag.text.lower() and "tax refund" not in tag.text.lower():
                return float(tag.select_one("div.a-span-last").text.strip().replace("$", ""))

        return None

    def _parse_order_shipping_date(self) -> Optional[date]:
        # TODO: find a better way to do this
        if "Items shipped:" in self.parsed.text:
            date_str = self.parsed.text.split("Items shipped:")[1].strip().split("-")[0].strip()
            return datetime.strptime(date_str, "%B %d, %Y").date()
        else:
            return None

    def _parse_refund_completed_date(self) -> Optional[date]:
        # TODO: find a better way to do this
        if "Refund: Completed" in self.parsed.text:
            date_str = self.parsed.text.split("Refund: Completed")[1].strip().split("-")[0].strip()
            return datetime.strptime(date_str, "%B %d, %Y").date()
        else:
            return None
