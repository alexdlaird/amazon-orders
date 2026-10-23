__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from datetime import date
from typing import Optional

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.item import Item
from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersEntityError

logger = logging.getLogger(__name__)


class OrderSearchResult(Parsable):
    """
    An Item of an Order that matched an Order search. The Order search page lists each matching Item, with its
    Order's number and date, from every year of the Order history. The Order itself is fetched by
    :attr:`order_number` with :func:`~amazonorders.orders.AmazonOrders.get_order`.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(parsed, config)

        #: The Order details link. ``None`` if the result has none.
        self.order_details_link: Optional[str] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ORDER_DETAILS_LINK_SELECTOR,
            attr_name="href")
        #: The number of the Order the Item is in, from :attr:`order_details_link`.
        self.order_number: Optional[str] = self.safe_parse(self._parse_order_number)
        #: The date the Order was placed.
        self.order_placed_date: Optional[date] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ORDER_SEARCH_RESULT_DATE_SELECTOR,
            prefix_split=self.config.selectors.FIELD_ORDER_SEARCH_RESULT_DATE_PREFIX,
            parse_date=True)
        #: The matching Item, built with the config's ``item_class``. The search page shows its title, link, image,
        #: and quantity (only when more than one was ordered), not its price or Seller.
        self.item: Item = self.config.item_cls(self.parsed, self.config)

    def __repr__(self) -> str:
        return f"<OrderSearchResult #{self.order_number}: \"{self.item.title}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"OrderSearchResult #{self.order_number} ({self.order_placed_date}): {self.item.title}"

    def _parse_order_number(self) -> Optional[str]:
        link = self.order_details_link
        order_number = self.config.constants.parse_order_number(link) if link else None

        if order_number is None:
            err_msg = ("OrderSearchResult.order_number could not be parsed, but it's required. "
                       "Check if Amazon changed the HTML")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersEntityError(f"{err_msg} or set warn_on_missing_required_field=True in config.")

            logger.warning(f"{err_msg}.")

        return order_number
