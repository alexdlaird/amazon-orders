import logging
from datetime import datetime, date
from typing import Optional

from bs4 import Tag

from amazonorders import constants
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.seller import Seller

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"

logger = logging.getLogger(__name__)


class Item(Parsable):
    """
    An Item in an Amazon `~amazonorders.entity.order.Order`.
    """

    def __init__(self,
                 parsed: Tag) -> None:
        super().__init__(parsed)

        #: The Item title.
        self.title: str = self.safe_simple_parse(selector=constants.FIELD_ITEM_TITLE_SELECTOR, required=True)
        #: The Item link.
        self.link: str = self.safe_simple_parse(selector=constants.FIELD_ITEM_LINK_SELECTOR, link=True, required=True)
        #: The Item price.
        self.price: Optional[float] = self.safe_parse(self._parse_price)
        #: The Item Seller.
        self.seller: Optional[Seller] = self.safe_parse(self._parse_seller)
        #: The Item condition.
        self.condition: Optional[str] = self.safe_parse(self._parse_condition)
        #: The Item return eligible date.
        self.return_eligible_date: Optional[date] = self.safe_parse(self._parse_return_eligible_date)
        #: The Item image URL.
        self.image_link: Optional[str] = self.safe_simple_parse(selector=constants.FIELD_ITEM_IMG_LINK_SELECTOR,
                                                                link=True)
        #: The Item quantity.
        self.quantity: Optional[int] = self.safe_simple_parse(selector=constants.FIELD_ITEM_QUANTITY_SELECTOR,
                                                              return_type=int)

    def __repr__(self) -> str:
        return "<Item: \"{}\">".format(self.title)

    def __str__(self) -> str:  # pragma: no cover
        return "Item: {}".format(self.title)

    def __lt__(self, other):
        return self.title < other.title

    def _parse_price(self) -> Optional[float]:
        value = None

        for tag in self.parsed.select(constants.FIELD_ITEM_TAG_ITERATOR_SELECTOR):
            price = tag.text.strip()
            if price.startswith("$"):
                value = float(price.replace("$", ""))

        return value

    def _parse_seller(self) -> Optional[Seller]:
        value = None

        for tag in self.parsed.select(constants.FIELD_ITEM_TAG_ITERATOR_SELECTOR):
            if "Sold by:" in tag.text:
                value = Seller(tag)

        return value

    def _parse_condition(self) -> Optional[str]:
        value = None

        for tag in self.parsed.select(constants.FIELD_ITEM_TAG_ITERATOR_SELECTOR):
            split_str = "Condition:"
            if split_str in tag.text:
                value = tag.text.split(split_str)[1].strip()

        return value

    def _parse_return_eligible_date(self) -> Optional[date]:
        value = None

        for tag in self.parsed.select(constants.FIELD_ITEM_TAG_ITERATOR_SELECTOR):
            if "Return" in tag.text:
                tag_str = tag.text.strip()
                split_str = "through "
                if "closed on " in tag.text:
                    split_str = "closed on "
                if split_str in tag_str:
                    date_str = tag_str.split(split_str)[1]
                    value = datetime.strptime(date_str, "%b %d, %Y").date()

        return value
