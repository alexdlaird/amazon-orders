__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import logging
import re
from datetime import date
from typing import Any, List, Optional, TypeVar, Union

from bs4 import BeautifulSoup, Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.item import Item
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.recipient import Recipient
from amazonorders.entity.shipment import Shipment
from amazonorders.exception import AmazonOrdersEntityError, AmazonOrdersError

logger = logging.getLogger(__name__)

OrderEntity = TypeVar("OrderEntity", bound="Order")


class Order(Parsable):
    """
    An Amazon Order. If desired fields are populated as ``None``, ensure ``full_details`` is ``True`` when
    retrieving the Order (for instance, with :func:`~amazonorders.orders.AmazonOrders.get_order_history`), since
    by default it is ``False`` (enabling slows down querying).
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig,
                 full_details: bool = False,
                 clone: Optional[OrderEntity] = None,
                 index: Optional[int] = None,
                 order_number: Optional[str] = None) -> None:
        super().__init__(parsed, config)

        #: If the Orders full details were populated from its details page.
        self.full_details: bool = full_details

        #: Where the Order appeared in the history when it was queried. This will inevitably change (e.g. when a new
        #: Order is placed, all indexes will then be off by one), but is still captured as it may be applicable in
        #: various use-cases. Populated when the Order was fetched through
        #: :func:`~amazonorders.orders.AmazonOrders.get_order_history` (use ``start_index`` to correlate), or when
        #: the ``clone`` has its ``index`` set.
        self.index: Optional[int] = index if index is not None else (clone.index if clone else None)

        #: ``True`` if the Order was cancelled. When ``True``, fields like ``grand_total`` and the totals on the
        #: details page may be ``None`` because Amazon stops rendering them.
        self.cancelled: bool = clone.cancelled if clone else self._parse_cancelled()

        #: ``True`` if this is a Whole Foods Market purchase (an in-store/FOPO purchase or a Whole Foods receipt
        #: order). Unlike other unsupported order types, these expose a :attr:`grand_total` and (often) an
        #: :attr:`item_count` on the history page, so those fields are populated.
        self.is_whole_foods: bool = clone.is_whole_foods if clone else bool(
            self.parsed and util.select(self.parsed, self.config.selectors.ORDER_WHOLE_FOODS))

        #: The Order Shipments.
        self.shipments: List[Shipment] = clone.shipments if clone else self._parse_shipments()
        #: The Order Items.
        self.items: List[Item] = clone.items if clone and not full_details else self._parse_items()
        # `required` is relaxed only when `order_number` is explicitly supplied (the `get_order()` path), so the
        # fallback is never silently applied when parsing the history list, where the parsed value must be present.
        _parsed_order_number = None if clone else self.safe_parse(
            self._parse_order_number,
            required=not self.cancelled and order_number is None)
        if _parsed_order_number is None and order_number is not None:
            logger.debug(f"Order number could not be parsed from the page; "
                         f"using supplied order_number={order_number}.")
        #: The Order number. May be ``None`` only when the Order is :attr:`cancelled` and Amazon stripped the order
        #: number from the details page (the ``order_number`` parameter is used as a fallback in that case).
        self.order_number: Optional[str] = clone.order_number if clone else _parsed_order_number or order_number
        #: The Order details link.
        self.order_details_link: Optional[str] = clone.order_details_link if clone else self.safe_parse(
            self._parse_order_details_link)
        #: The Order grand total.
        self.grand_total: Optional[float] = clone.grand_total if clone else self.safe_parse(self._parse_grand_total)
        #: The Order placed date.
        self.order_placed_date: date = clone.order_placed_date if clone else self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ORDER_PLACED_DATE_SELECTOR,
            suffix_split=self.config.selectors.FIELD_ORDER_PLACED_DATE_SUFFIX,
            suffix_split_fuzzy=True,
            parse_date=True)
        #: The Order Recipients.
        self.recipient: Optional[Recipient] = clone.recipient if clone else self.safe_parse(self._parse_recipient)
        #: The number of items in the purchase, when Amazon summarizes the count instead of listing the items
        #: (e.g. Whole Foods Market orders show "N items in this purchase"). ``None`` when no such summary is shown.
        self.item_count: Optional[int] = clone.item_count if clone else self.safe_parse(self._parse_item_count)

        # Fields below this point are only populated if `full_details` is True

        #: The Order payment method. Only populated when ``full_details`` is ``True``. For Whole Foods Market
        #: orders this is the card brand of the first payment method on the receipt (e.g. "Visa").
        self.payment_method: Optional[str] = self._if_full_details(self._parse_payment_method())
        #: The Order payment method's last 4 digits, preserved verbatim so leading zeros are not lost.
        #: Only populated when ``full_details`` is ``True``.
        self.payment_method_last_4: Optional[str] = self._if_full_details(
            self.safe_parse(self._parse_payment_method_last_4))
        #: The Order subtotal. Only populated when ``full_details`` is ``True``.
        self.subtotal: Optional[float] = self._if_full_details(self._parse_subtotal())
        #: The Order shipping total. Only populated when ``full_details`` is ``True``.
        self.shipping_total: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_SHIPPING_TOTAL_LABELS))
        #: The Order free shipping. Only populated when ``full_details`` is ``True``.
        self.free_shipping: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_FREE_SHIPPING_LABELS))
        #: The Order promotion applied. Only populated when ``full_details`` is ``True``.
        self.promotion_applied: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_PROMOTION_APPLIED_LABELS,
                                         combine_multiple=True))
        #: The Order coupon savings. Only populated when ``full_details`` is ``True``.
        self.coupon_savings: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_COUPON_SAVINGS_LABELS,
                                         combine_multiple=True))
        #: The Order reward points. Only populated when ``full_details`` is ``True``.
        self.reward_points: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_REWARD_POINTS_LABELS,
                                         combine_multiple=True))
        #: The Order Subscribe & Save discount. Only populated when ``full_details`` is ``True``.
        self.subscription_discount: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_SUBSCRIPTION_DISCOUNT_LABELS))
        #: The Order total before tax. Only populated when ``full_details`` is ``True``.
        self.total_before_tax: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_TOTAL_BEFORE_TAX_LABELS))
        #: The Order estimated tax. Only populated when ``full_details`` is ``True``. For Whole Foods Market
        #: orders this is the "Tax and Fees" total from the receipt.
        self.estimated_tax: Optional[float] = self._if_full_details(self._parse_estimated_tax())
        #: The Order refund total. Only populated when ``full_details`` is ``True``.
        self.refund_total: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_REFUND_TOTAL_LABELS))
        #: The Multibuy discount. Only populated when ``full_details`` is ``True``.
        self.multibuy_discount: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_MULTIBUY_DISCOUNT_LABELS))
        #: The Amazon discount. Only populated when ``full_details`` is ``True``.
        self.amazon_discount: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_AMAZON_DISCOUNT_LABELS))
        #: The Gift Card total (rendered as "Gift Card" on digital order details pages). Only
        #: populated when ``full_details`` is ``True``.
        self.gift_card: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_GIFT_CARD_LABELS))
        #: The Gift Wrap total. Only populated when ``full_details`` is ``True``.
        self.gift_wrap: Optional[float] = self._if_full_details(
            self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_GIFT_WRAP_LABELS))

    def __repr__(self) -> str:
        return f"<Order #{self.order_number}: \"{self.items}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Order #{self.order_number}: {self.items}"

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

    def _parse_order_number(self,
                            required: bool) -> Optional[str]:
        selectors = self.config.selectors.FIELD_ORDER_NUMBER_SELECTOR
        for selector in [selectors] if isinstance(selectors, str) else selectors:
            tag = util.select_one(self.parsed, selector)
            order_number = self.config.constants.parse_order_number(tag.text) if tag else None
            if order_number:
                return order_number

        if required:
            raise AmazonOrdersEntityError(
                "When building {name}, field for selector `{selector}` was None, but this is not allowed.".format(
                    name=self.__class__.__name__,
                    selector=selectors))

        return None

    def _parse_order_details_link(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_ORDER_DETAILS_LINK_SELECTOR, attr_name="href")

        if not value and self.order_number:
            value = f"{self.config.constants.ORDER_DETAILS_URL}?orderID={self.order_number}"

        return value

    def _parse_cancelled(self) -> bool:
        if not self.parsed:
            return False

        if util.select(self.parsed, self.config.selectors.ORDER_SKIP_TOTALS):
            return True

        statuses = util.select(self.parsed, self.config.selectors.ORDER_SHIPMENT_STATUS_SELECTOR)
        cancelled_statuses = util.select(self.parsed, self.config.selectors.ORDER_SHIPMENT_CANCELLED_SELECTOR)

        return bool(statuses) and len(cancelled_statuses) == len(statuses)

    def _parse_grand_total(self) -> Optional[float]:
        # Skip totals parsing for cancelled orders
        if self.cancelled:
            return None

        # Skip totals parsing for unsupported order types (Amazon Fresh, physical stores). Whole Foods Market
        # orders also match ORDER_SKIP_ITEMS, but they expose a grand total on the history page, so parse it.
        if not self.is_whole_foods and len(util.select(self.parsed, self.config.selectors.ORDER_SKIP_ITEMS)) > 0:
            return None

        value = self.simple_parse(self.config.selectors.FIELD_ORDER_GRAND_TOTAL_SELECTOR)

        total_prefix = self.config.selectors.FIELD_ORDER_GRAND_TOTAL_PREFIX

        if not value:
            value = self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_GRAND_TOTAL_LABELS)
        elif value.lower().startswith(total_prefix.lower()):
            value = value[len(total_prefix):].strip()

        value = self.to_currency(value)

        if value is None:  # pragma: no cover
            err_msg = (f"Order {getattr(self, 'order_number', 'UNKNOWN')} grand_total could not be parsed, but it's "
                       f"required. Check if Amazon changed the HTML")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(f"{err_msg} or set warn_on_missing_required_field=True in config.")
            else:
                logger.warning(f"{err_msg}.")

        return value

    def _parse_whole_foods_amount(self,
                                  selector: str) -> Optional[float]:
        return self.to_currency(self.simple_parse(selector))

    def _parse_payment_method(self) -> Optional[str]:
        if self.is_whole_foods:
            return self.safe_simple_parse(
                selector=self.config.selectors.FIELD_ORDER_WHOLE_FOODS_PAYMENT_METHOD_SELECTOR)
        tag = util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_PAYMENT_METHOD_SELECTOR)
        if tag is None:
            return None
        return tag.attrs.get("alt") or tag.text.strip()

    def _parse_masked_digits(self,
                             selector: Union[str, list],
                             pattern: str) -> Optional[str]:
        for tag in util.select(self.parsed, selector):
            match = re.search(pattern, tag.text)
            if match:
                return match.group(1)

        return None

    def _parse_payment_method_last_4(self) -> Optional[str]:
        if self.is_whole_foods:
            return self._parse_masked_digits(
                self.config.selectors.FIELD_ORDER_WHOLE_FOODS_PAYMENT_LAST_4_SELECTOR, r"\*\s*(\d+)")
        return self._parse_masked_digits(self.config.selectors.FIELD_ORDER_PAYMENT_METHOD_LAST_4_SELECTOR,
                                         self.config.selectors.FIELD_ORDER_PAYMENT_METHOD_LAST_4_REGEX)

    def _parse_subtotal(self) -> Optional[float]:
        if self.is_whole_foods:
            return self._parse_whole_foods_amount(self.config.selectors.FIELD_ORDER_WHOLE_FOODS_SUBTOTAL_SELECTOR)
        return self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_SUBTOTAL_LABELS)

    def _parse_estimated_tax(self) -> Optional[float]:
        if self.is_whole_foods:
            return self._parse_whole_foods_amount(self.config.selectors.FIELD_ORDER_WHOLE_FOODS_TAX_SELECTOR)
        return self._parse_labeled_currency(self.config.selectors.FIELD_ORDER_ESTIMATED_TAX_LABELS)

    def _parse_item_count(self) -> Optional[int]:
        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_ITEM_COUNT_SELECTOR):
            item_count = self.config.constants.parse_count(tag.text,
                                                           self.config.selectors.FIELD_ORDER_ITEM_COUNT_REGEX)
            if item_count is not None:
                return item_count

        return None

    def _parse_recipient(self) -> Optional[Recipient]:
        # At least for now, we don't populate Recipient data for digital orders
        if util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_GIFT_CARD_INSTANCE_SELECTOR):
            return None

        value = util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_ADDRESS_SELECTOR)

        if not value:
            value = util.select_one(self.parsed, self.config.selectors.FIELD_ORDER_ADDRESS_FALLBACK_1_SELECTOR)

            if value:
                data_popover = json.loads(str(value.get("data-a-popover", "{}")))
                inline_content = data_popover.get("inlineContent")
                if inline_content:
                    value = BeautifulSoup(inline_content, self.config.bs4_parser)

        if not value:
            ship_to_tag = util.select_one(self.parsed,
                                          self.config.selectors.FIELD_ORDER_ADDRESS_FALLBACK_2_SELECTOR)

            if not ship_to_tag:
                ship_to_tag = self._parse_enclosing_ship_to()

            if ship_to_tag:
                value = BeautifulSoup(str(ship_to_tag.contents[0]).strip(), self.config.bs4_parser)

        if not value:
            return None

        return Recipient(value, self.config)

    def _parse_enclosing_ship_to(self) -> Optional[Tag]:
        """Finds this Order's shipping address when a page renders it alongside the Order instead of within it."""
        parsed_parent = self.parsed.find_parent()

        if parsed_parent is None:
            err_msg = ("Recipient parent not found, but it's required. "
                       "Check if Amazon changed the HTML.")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(err_msg)
            else:
                logger.warning(err_msg)

                return None

        # A container wrapping every Order on the page would give back whichever address Amazon rendered first
        # TODO: capture a page that renders the shipping address outside the Order, to verify this path
        if len(util.select(parsed_parent, self.config.selectors.ORDER_HISTORY_ENTITY_SELECTOR)) > 1:
            logger.debug(f"Order {self.order_number} shipping address could not be attributed to it, "
                         f"so Recipient was left unpopulated.")

            return None

        return util.select_one(parsed_parent, self.config.selectors.FIELD_ORDER_ADDRESS_FALLBACK_2_SELECTOR)

    def _parse_currency(self,
                        contains: Union[str, "re.Pattern[str]"],
                        combine_multiple: bool = False) -> Optional[float]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR):
            row_text = tag.text.lower()
            label_matches = (bool(contains.search(row_text)) if isinstance(contains, re.Pattern)
                             else contains in row_text)
            if (label_matches and
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

    def _parse_labeled_currency(self,
                                labels: List[Union[str, "re.Pattern[str]"]],
                                combine_multiple: bool = False) -> Optional[float]:
        for label in labels:
            value = self._parse_currency(label, combine_multiple)
            if value is not None:
                return value

        return None

    def _if_full_details(self,
                         value: Any) -> Union[Any, None]:
        return value if self.full_details else None
