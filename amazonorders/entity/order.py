__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import logging
from datetime import date, timedelta
from typing import Any, List, Optional, TypeVar, Union

from bs4 import BeautifulSoup, Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.item import Item
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.recipient import Recipient
from amazonorders.entity.shipment import Shipment
from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)

OrderEntity = TypeVar("OrderEntity", bound="Order")


class Order(Parsable):
    """
    An Amazon Order. If desired fields are populated as ``None``, ensure ``full_details`` is ``True`` when
    retrieving the Order (for instance, with :func:`~amazonorders.orders.AmazonOrders.get_order_history`), since
    by default it is ``False`` (it will slow down querying).
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig,
                 full_details: bool = False,
                 clone: Optional[OrderEntity] = None,
                 index: Optional[int] = None) -> None:
        super().__init__(parsed, config)

        #: If the Orders full details were populated from its details page.
        self.full_details: bool = full_details

        #: Where the Order appeared in the history when it was queried. This will inevitably change (ex. when a new
        #: order is placed, all indexes will then be off by one), but is still captured as it may be applicable in
        #: various use-cases. Only set when the Order is populated through
        #: :func:`~amazonorders.orders.AmazonOrders.get_order_history` (use ``start_index`` to correlate).
        self.index: Optional[int] = index

        #: The Order Shipments.
        self.shipments: List[Shipment] = clone.shipments if clone else self._parse_shipments()
        #: The Order Items.
        self.items: List[Item] = clone.items if clone and not full_details else self._parse_items()
        self.title: str = " + ".join(str(item) for item in self.items) if self.items else ""
        self.item_quantity: int = len(self.items)
        #: The Order number.
        self.order_id: str = clone.order_id if clone else self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ORDER_NUMBER_SELECTOR,
            required=True,
            prefix_split="#",
            prefix_split_fuzzy=True)
        self.payment_reference_id: str = self.order_id
        #: The Order details link.
        self.order_details_link: Optional[str] = clone.order_details_link if clone else self.safe_parse(
            self._parse_order_details_link)
        #: The Order grand total.
        self.grand_total: float = clone.grand_total if clone else self.safe_parse(self._parse_grand_total)
        self.item_net_total: float = self.grand_total
        self.payment_amount: float = self.grand_total
        #: The Order placed date.
        self.order_date: date = clone.order_date if clone else self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ORDER_PLACED_DATE_SELECTOR,
            suffix_split="Order #",
            suffix_split_fuzzy=True,
            parse_date=True)
        self.payment_date: date = self.order_date + timedelta(days=1)
        #: The Order Recipients.
        self.recipient: Recipient = clone.recipient if clone else self.safe_parse(self._parse_recipient)

        # Fields below this point are only populated if `full_details` is True

        #: The Order payment method. Only populated when ``full_details`` is ``True``.
        self.payment_method: Optional[str] = self._if_full_details(
            self.safe_simple_parse(selector=self.config.selectors.FIELD_ORDER_PAYMENT_METHOD_SELECTOR,
                                   attr_name="alt"))
        #: The Order payment method's last 4 digits. Only populated when ``full_details`` is ``True``.
        self.payment_method_last_4: Optional[str] = self._if_full_details(
            self.safe_simple_parse(selector=self.config.selectors.FIELD_ORDER_PAYMENT_METHOD_LAST_4_SELECTOR,
                                   prefix_split="ending in"))
        #: The Order item_subtotal. Only populated when ``full_details`` is ``True``.
        self.item_subtotal: Optional[float] = self._if_full_details(self._parse_currency("subtotal")) or 0.0
        #: The Order shipping total. Only populated when ``full_details`` is ``True``.
        self.shipping_total: Optional[float] = self._if_full_details(self._parse_currency("shipping")) or 0.0
        #: The Order free shipping. Only populated when ``full_details`` is ``True``.
        self.free_shipping: Optional[float] = self._if_full_details(self._parse_currency("free shipping")) or 0.0
        self.item_shipping_and_handling: Optional[float] = (self.shipping_total or 0.0) - (self.free_shipping or 0.0)
        #: The Order promotion applied. Only populated when ``full_details`` is ``True``.
        self.item_promotion: Optional[float] = self._if_full_details(
            self._parse_currency("promotion", combine_multiple=True)) or 0.0
        #: The Order coupon savings. Only populated when ``full_details`` is ``True``.
        self.coupon_savings: Optional[float] = self._if_full_details(
            self._parse_currency("coupon", combine_multiple=True)) or 0.0
        #: The Order Subscribe & Save discount. Only populated when ``full_details`` is ``True``.
        self.subscription_discount: Optional[float] = self._if_full_details(self._parse_currency("subscribe")) or 0.0
        #: The Order total before tax. Only populated when ``full_details`` is ``True``.
        self.total_before_tax: Optional[float] = self._if_full_details(self._parse_currency("total before tax"))
        #: The Order estimated tax. Only populated when ``full_details`` is ``True``.
        self.estimated_tax: Optional[float] = self._if_full_details(self._parse_currency("estimated tax"))
        #: The Order estimated tax. Only populated when ``full_details`` is ``True``.
        self.item_federal_tax: Optional[float] = self._if_full_details(self._parse_currency("hst")) or 0.0
        #: The Order estimated tax. Only populated when ``full_details`` is ``True``.
        self.item_provincial_tax: Optional[float] = self._if_full_details(self._parse_currency("pst")) or 0.0
        self.item_regulatory_fee: Optional[float] = self._if_full_details(self._parse_currency("fee")) or 0.0
        #: The Order refund total. Only populated when ``full_details`` is ``True``.
        self.refund_total: Optional[float] = self._if_full_details(self._parse_currency("refund total"))

        self.amazon_internal_product_category: Optional[str] = ""
        self.amazon_class: Optional[str] = ""
        self.amazon_commodity: Optional[str] = ""

    def __repr__(self) -> str:
        return f"<Order #{self.order_id}: \"{self.items}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Order #{self.order_id}: {self.items}"

    def _parse_shipments(self) -> List[Shipment]:
        if not self.parsed or len(util.select(self.parsed, self.config.selectors.ORDER_SKIP_ITEMS)) > 0:
            return []

        shipments: List[Shipment] = [self.config.shipment_cls(x, self.config)
                                     for x in util.select(self.parsed,
                                                          self.config.selectors.SHIPMENT_ENTITY_SELECTOR)]
        shipments.sort()
        return shipments

    def _parse_items(self) -> List[Item]:
        if not self.parsed or len(util.select(self.parsed, self.config.selectors.ORDER_SKIP_ITEMS)) > 0:
            return []

        items: List[Item] = [self.config.item_cls(x, self.config)
                             for x in util.select(self.parsed,
                                                  self.config.selectors.ITEM_ENTITY_SELECTOR)]
        items.sort()
        return items

    def _parse_order_details_link(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_ORDER_DETAILS_LINK_SELECTOR, attr_name="href")

        if not value and self.order_id:
            value = f"{self.config.constants.ORDER_DETAILS_URL}?orderID={self.order_id}"

        return value

    def _parse_grand_total(self) -> float:
        value = self.simple_parse(self.config.selectors.FIELD_ORDER_GRAND_TOTAL_SELECTOR)

        total_str = "total"

        if not value:
            value = self._parse_currency("grand total")
        elif value.lower().startswith(total_str):
            value = value[len(total_str):].strip()

        value = self.to_currency(value)

        if value is None:
            raise AmazonOrdersError(
                "Order.grand_total did not populate, but it's required. "
                "Check if Amazon changed the HTML."
            )  # pragma: no cover

        return value

    def _parse_recipient(self) -> Optional[Recipient]:
        # At least for now, we don't populate Recipient data for digital orders
        if util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_GIFT_CARD_INSTANCE_SELECTOR):
            return None

        value = util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_ADDRESS_SELECTOR)

        if not value:
            value = util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_ADDRESS_FALLBACK_1_SELECTOR)

            if value:
                data_popover = value.get("data-a-popover", {})  # type: ignore[arg-type, var-annotated]
                inline_content = data_popover.get("inlineContent")  # type: ignore[union-attr]
                if inline_content:
                    value = BeautifulSoup(json.loads(inline_content), self.config.bs4_parser)

        if not value:
            # TODO: there are multiple shipToData tags, we should double check we're picking the right one
            #  associated with the order; should also be able to eliminate the use of find_parent() here with
            #  a better CSS selector, we just need to make sure we have good test coverage around this path first
            parsed_parent = self.parsed.find_parent()

            if parsed_parent is None:
                raise AmazonOrdersError(
                    "Recipient parent not found, but it's required. "
                    "Check if Amazon changed the HTML."
                )  # pragma: no cover

            parent_tag = util.select_one(
                parsed_parent,
                self.config.selectors.FIELD_ORDER_ADDRESS_FALLBACK_2_SELECTOR
            )

            if parent_tag:
                value = BeautifulSoup(str(parent_tag.contents[0]).strip(), self.config.bs4_parser)

        if not value:
            return None

        return Recipient(value, self.config)

    def _parse_currency(self, contains, combine_multiple=False) -> Optional[float]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
            if (contains in tag.text.lower() and
                    not util.select_one(tag,
                                        self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_POPOVER_PRELOAD_SELECTOR)):
                inner_tag = util.select_one(tag, self.config.selectors.FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR)
                if inner_tag:
                    currency = self.to_currency(inner_tag.text)
                    if currency is not None:
                        if value is None:
                            value = 0.0
                        value += currency

                    if not combine_multiple:
                        break

        return value

    def _if_full_details(self,
                         value: Any) -> Union[Any, None]:
        return value if self.full_details else None
