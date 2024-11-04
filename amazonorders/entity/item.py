__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

import logging
from datetime import date
from typing import Optional, TypeVar

from bs4 import Tag
from dateutil import parser

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.seller import Seller

logger = logging.getLogger(__name__)

ItemEntity = TypeVar("ItemEntity", bound="Item")


class Item(Parsable):
    """
    An Item in an Amazon :class:`~amazonorders.entity.order.Order`.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(parsed, config)

        #: The Item title.
        self.title: str = self.safe_simple_parse(selector=self.config.selectors.FIELD_ITEM_TITLE_SELECTOR,
                                                 required=True)
        #: The Item link.
        self.link: str = self.safe_simple_parse(selector=self.config.selectors.FIELD_ITEM_LINK_SELECTOR,
                                                attr_name="href", required=True)
        #: The Item price.
        self.price: Optional[float] = self.to_currency(
            self.safe_simple_parse(selector=self.config.selectors.FIELD_ITEM_PRICE_SELECTOR,
                                   prefix_split="$"))
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
        self.return_eligible_date: Optional[date] = self.safe_parse(self._parse_return_eligible_date)
        #: The Item image URL.
        self.image_link: Optional[str] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ITEM_IMG_LINK_SELECTOR,
            attr_name="src")
        #: The Item quantity.
        self.quantity: Optional[int] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ITEM_QUANTITY_SELECTOR)

    def __repr__(self) -> str:
        return f"<Item: \"{self.title}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Item: {self.title}"

    def __lt__(self,
               other: ItemEntity) -> bool:
        return self.title < other.title

    def _parse_return_eligible_date(self) -> Optional[date]:
        value = None

        for tag in util.select(self.parsed, self.config.selectors.FIELD_ITEM_RETURN_SELECTOR):
            if "Return" in tag.text:
                value = parser.parse(tag.text, fuzzy=True).date()
                break

        return value
