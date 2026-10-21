__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from typing import Optional

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersError

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

        #: The number of the Order the Item is in.
        self.order_number: Optional[str] = self.safe_parse(self._parse_order_number)
        #: The Order details link. ``None`` when :attr:`order_number` is ``None``.
        self.order_details_link: Optional[str] = self.safe_parse(self._parse_order_details_link)
        #: The date the Order was placed.
        self.order_placed_date: Optional[date] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ORDER_SEARCH_RESULT_DATE_SELECTOR,
            prefix_split=self.config.selectors.FIELD_ORDER_SEARCH_RESULT_DATE_PREFIX,
            parse_date=True)
        #: The Item's title.
        self.title: Optional[str] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ORDER_SEARCH_RESULT_TITLE_SELECTOR)
        #: The Item's product link.
        self.link: Optional[str] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_ORDER_SEARCH_RESULT_TITLE_SELECTOR,
            attr_name="href")
        #: The product ASIN, derived from :attr:`link`; ``None`` when the link is not a product page.
        self.asin: Optional[str] = self.safe_parse(self._parse_asin)
        #: The quantity of the Item ordered. Amazon shows it only when it's more than one, so it's ``1`` otherwise.
        self.quantity: int = self.safe_parse(self._parse_quantity) or 1

    def __repr__(self) -> str:
        return f"<OrderSearchResult #{self.order_number}: \"{self.title}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"OrderSearchResult #{self.order_number} ({self.order_placed_date}): {self.title}"

    def _parse_order_number(self) -> Optional[str]:
        link = self.simple_parse(self.config.selectors.FIELD_ORDER_SEARCH_RESULT_ORDER_DETAILS_LINK_SELECTOR,
                                 attr_name="href")
        order_number = self.config.constants.parse_order_number(link) if link else None

        if order_number is None:
            err_msg = ("OrderSearchResult.order_number could not be parsed, but it's required. "
                       "Check if Amazon changed the HTML")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(f"{err_msg} or set warn_on_missing_required_field=True in config.")

            logger.warning(f"{err_msg}.")

        return order_number

    def _parse_order_details_link(self) -> Optional[str]:
        if not self.order_number:
            return None

        constants = self.config.constants
        return f"{constants.ORDER_DETAILS_URL}?{constants.ORDER_ID_QUERY_PARAM}={self.order_number}"

    def _parse_asin(self) -> Optional[str]:
        if not self.link:
            return None

        match = re.search(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})(?:[/?]|$)", self.link)
        return match.group(1) if match else None

    def _parse_quantity(self) -> Optional[int]:
        tag = self.parsed.select_one(self.config.selectors.FIELD_ORDER_SEARCH_RESULT_QUANTITY_SELECTOR)

        return self.config.constants.parse_count(tag.text, r"^\s*{count}\s*$") if tag else None
