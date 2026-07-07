__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from typing import Optional, TypeVar

from bs4 import Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.seller import Seller

logger = logging.getLogger(__name__)

ItemEntity = TypeVar("ItemEntity", bound="Item")


class Item(Parsable):
    """
    An Item in an Amazon :class:`~amazonorders.entity.order.Order`. If desired fields are populated as ``None``,
    ensure ``full_details`` is ``True`` when retrieving the Order (for instance, with
    :func:`~amazonorders.orders.AmazonOrders.get_order_history`), since by default it is ``False`` (it will slow
    down querying).
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(parsed, config)

        #: The Item title.
        self.title: str = self.safe_simple_parse(selector=self.config.selectors.FIELD_ITEM_TITLE_SELECTOR,
                                                 required=True)
        #: The Item link. ``None`` for items without an Amazon detail page (e.g. ASINLESS Whole Foods
        #: Market line items).
        self.link: Optional[str] = self.safe_simple_parse(selector=self.config.selectors.FIELD_ITEM_LINK_SELECTOR,
                                                          attr_name="href")
        #: The Item price.
        self.price: Optional[float] = self.to_currency(
            self.safe_simple_parse(selector=self.config.selectors.FIELD_ITEM_PRICE_SELECTOR)
        )
        #: The Item Seller.
        self.seller: Optional[Seller] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ITEM_SELLER_SELECTOR,
            text_contains="Sold by:",
            wrap_tag=Seller)
        #: The Item condition.
        self.condition: Optional[str] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ITEM_TAG_ITERATOR_SELECTOR,
            prefix_split="Condition:")
        #: The Item return eligible date.
        self.return_eligible_date: Optional[date] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ITEM_RETURN_SELECTOR,
            text_contains="Return",
            parse_date=True)
        #: The Item image URL.
        self.image_link: Optional[str] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ITEM_IMG_LINK_SELECTOR,
            attr_name="src")
        #: The Item quantity. For items sold by weight (e.g. Whole Foods Market produce priced per
        #: pound, rendered as "Qty: 0.31 lb"), which have no whole-unit count, this is ``None``.
        self.quantity: Optional[int] = self.safe_parse(self._parse_quantity)

    def __repr__(self) -> str:
        return f"<Item: \"{self.title}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Item: {self.title}"

    def __lt__(self,
               other: ItemEntity) -> bool:
        return self.title < other.title

    def _parse_quantity(self) -> Optional[int]:
        value = self.simple_parse(self.config.selectors.FIELD_ITEM_QUANTITY_SELECTOR)
        if isinstance(value, int):
            return value

        # Whole Foods Market line items render quantity as "Qty: 1" (a whole count) or "Qty: 0.31 lb"
        # (sold by weight, which has no integer quantity).
        for tag in util.select(self.parsed, self.config.selectors.FIELD_ITEM_WHOLE_FOODS_QUANTITY_SELECTOR):
            match = re.fullmatch(r"Qty:\s*(\d+)", tag.get_text(strip=True))
            if match:
                return int(match.group(1))

        return None
