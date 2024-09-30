__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

import json
import logging
from datetime import date, datetime
from typing import List, Optional, TypeVar
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.item import Item
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.recipient import Recipient
from amazonorders.entity.shipment import Shipment

logger = logging.getLogger(__name__)

Entity = TypeVar('Entity', bound='Order')


class Order(Parsable):
    """
    An Amazon Order.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig,
                 full_details: bool = True,
                 clone: Optional[Entity] = None) -> None:
        super().__init__(parsed, config)

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
        self.recipient: Recipient = clone.recipient if clone else self.safe_parse(self._parse_recipient, parsed=parsed)

        # Fields below this point are only populated if `full_details` is True

        #: The Order payment method. Only populated when ``full_details`` is ``True``.
        self.payment_method: Optional[str] = self._if_full_details(self._parse_payment_method())
        #: The Order payment method's last 4 digits. Only populated when ``full_details`` is ``True``.
        self.payment_method_last_4: Optional[str] = self._if_full_details(self._parse_payment_method_last_4())
        #: The Order subtotal. Only populated when ``full_details`` is ``True``.
        self.subtotal: Optional[float] = self._if_full_details(self._parse_subtotal())
        #: The Order shipping total. Only populated when ``full_details`` is ``True``.
        self.shipping_total: Optional[float] = self._if_full_details(self._parse_shipping_total())
        #: The Order Subscribe & Save discount. Only populated when ``full_details`` is ``True``.
        self.subscription_discount: Optional[float] = self._if_full_details(self._parse_subscription_discount())
        #: The Order total before tax. Only populated when ``full_details`` is ``True``.
        self.total_before_tax: Optional[float] = self._if_full_details(self._parse_total_before_tax())
        #: The Order estimated tax. Only populated when ``full_details`` is ``True``.
        self.estimated_tax: Optional[float] = self._if_full_details(self._parse_estimated_tax())
        #: The Order refund total. Only populated when ``full_details`` is ``True``.
        self.refund_total: Optional[float] = self._if_full_details(self._parse_refund_total())
        #: The Order shipped date. Only populated when ``full_details`` is ``True``.
        self.order_shipped_date: Optional[date] = self._if_full_details(self._parse_order_shipping_date())
        #: The Order refund total. Only populated when ``full_details`` is ``True``.
        self.refund_completed_date: Optional[date] = self._if_full_details(self._parse_refund_completed_date())

    def __repr__(self) -> str:
        return f"<Order #{self.order_number}: \"{self.items}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Order #{self.order_number}: {self.items}"

    def _parse_shipments(self) -> List[Shipment]:
        shipments = [Shipment(x, self.config) for x in util.select(self.parsed,
                                                                   self.config.selectors.SHIPMENT_ENTITY_SELECTOR)]
        shipments.sort()
        return shipments

    def _parse_items(self) -> List[Item]:
        items = [Item(x, self.config) for x in util.select(self.parsed, self.config.selectors.ITEM_ENTITY_SELECTOR)]
        items.sort()
        return items

    def _parse_order_details_link(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_ORDER_DETAILS_LINK_SELECTOR, link=True)

        if not value and self.order_number:
            value = f"{self.config.constants.ORDER_DETAILS_URL}?orderID={self.order_number}"

        return value

    def _parse_order_number(self) -> str:
        try:
            order_details_link = self._parse_order_details_link()
        except Exception:
            # We're not using safe_parse here because it's fine if this fails, no need for noise
            order_details_link = None

        if order_details_link:
            parsed_url = urlparse(order_details_link)
            value = parse_qs(parsed_url.query)["orderID"][0]
        else:
            value = self.simple_parse(self.config.selectors.FIELD_ORDER_NUMBER_SELECTOR, required=True)

        return value

    def _parse_grand_total(self) -> float:
        value = self.simple_parse(self.config.selectors.FIELD_ORDER_GRAND_TOTAL_SELECTOR)

        if not value:
            for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
                if "grand total" in tag.text.lower():
                    inner_tag = util.select_one(tag, self.config.selectors.FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR)
                    if inner_tag:
                        value = inner_tag.text.strip()
                        break
        else:
            if value.lower().startswith("total"):
                value = value[5:].strip()

        value = self.to_currency(value)

        return value

    def _parse_order_placed_date(self) -> date:
        value = self.simple_parse(self.config.selectors.FIELD_ORDER_PLACED_DATE_SELECTOR)

        if value and "Ordered on" in value:
            split_str = "Ordered on"
        else:
            split_str = "Order placed"

        value = value.split(split_str)[1].strip()
        value = datetime.strptime(value, "%B %d, %Y").date()

        return value

    def _parse_recipient(self, parsed):
        # Implement the parsing logic here
        pass

    def _parse_payment_method(self) -> Optional[str]:
        value = None

        tag = util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_PAYMENT_METHOD_SELECTOR)
        if tag:
            value = tag["alt"]

        return value

    def _parse_payment_method_last_4(self) -> Optional[str]:
        value = None

        tag = util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_PAYMENT_METHOD_LAST_4_SELECTOR)
        if tag:
            ending_sibling = tag.find_next_siblings()[-1]
            split_str = "ending in"
            if split_str in ending_sibling.text:
                value = ending_sibling.text.split(split_str)[1].strip()

        return value

    def _parse_subtotal(self) -> Optional[float]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
            if "subtotal" in tag.text.lower():
                inner_tag = util.select_one(tag, self.config.selectors.FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR)
                if inner_tag:
                    value = self.to_currency(inner_tag.text)
                    break

        return value

    def _parse_shipping_total(self) -> Optional[float]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
            if "shipping" in tag.text.lower():
                inner_tag = util.select_one(tag, self.config.selectors.FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR)
                if inner_tag:
                    value = self.to_currency(inner_tag.text)
                    break

        return value

    def _parse_subscription_discount(self) -> Optional[float]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
            if "subscribe" in tag.text.lower():
                inner_tag = util.select_one(tag, self.config.selectors.FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR)
                if inner_tag:
                    value = self.to_currency(inner_tag.text)
                    break

        return value

    def _parse_total_before_tax(self) -> Optional[float]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
            if "before tax" in tag.text.lower():
                inner_tag = util.select_one(tag, self.config.selectors.FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR)
                if inner_tag:
                    value = self.to_currency(inner_tag.text)
                    break

        return value

    def _parse_estimated_tax(self) -> Optional[float]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
            if "estimated tax" in tag.text.lower():
                inner_tag = util.select_one(tag, self.config.selectors.FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR)
                if inner_tag:
                    value = self.to_currency(inner_tag.text)
                    break

        return value

    def _parse_refund_total(self) -> Optional[float]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
            if "refund total" in tag.text.lower() and "tax refund" not in tag.text.lower():
                inner_tag = util.select_one(tag, self.config.selectors.FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR)
                if inner_tag:
                    value = self.to_currency(inner_tag.text)
                    break

        return value

    def _parse_order_shipping_date(self) -> Optional[date]:
        value = self.simple_parse(self.config.selectors.FIELD_ORDER_SHIPPED_DATE_SELECTOR,
                                  prefix_split="Items shipped:")

        if value:
            date_str = value.split("-")[0].strip()
            value = datetime.strptime(date_str, "%B %d, %Y").date()

        return value

    def _parse_refund_completed_date(self) -> Optional[date]:
        value = self.simple_parse(self.config.selectors.FIELD_ORDER_REFUND_COMPLETED_DATE,
                                  prefix_split="Refund: Completed")

        if value:
            date_str = value.split("-")[0].strip()
            value = datetime.strptime(date_str, "%B %d, %Y").date()

        return value

    def _if_full_details(self, value):
        return value if self.full_details else None
