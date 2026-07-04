__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from typing import Optional, TypeVar

from bs4 import Tag

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
        #: The Item link.
        self.link: str = self.safe_simple_parse(selector=self.config.selectors.FIELD_ITEM_LINK_SELECTOR,
                                                attr_name="href", required=True)
        #: The Item's ASIN (Amazon Standard Identification Number), a best-effort derivation from :attr:`link`.
        #: ``None`` when the link does not point at a product page (e.g. a "Buy it again" or offer-listing
        #: URL). Parsing never raises; a failure yields ``None``.
        self.asin: Optional[str] = self.safe_parse(self._parse_asin)
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

    def _parse_asin(self) -> Optional[str]:
        # Amazon's order pages don't expose the ASIN in a keyed element (no ``data-asin``); it lives in the
        # item's product link, as the canonical ``/dp/<ASIN>`` or ``/gp/product/<ASIN>`` path segment -- a URL
        # form Amazon has used for 20+ years. Encapsulated here so it can adopt a structured source if one ever
        # appears on these pages. Any link that isn't a product page (or an empty one) simply yields no match.
        match = re.search(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})(?:[/?]|$)", self.link)
        return match.group(1) if match else None
