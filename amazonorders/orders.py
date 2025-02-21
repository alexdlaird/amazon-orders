__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
from typing import List, Optional

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.order import Order
from amazonorders.exception import AmazonOrdersError, AmazonOrdersNotFoundError
from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)


class AmazonOrders:
    """
    Using an authenticated :class:`~amazonorders.session.AmazonSession`, can be used to query Amazon
    for Order details and history.
    """

    def __init__(self,
                 amazon_session: AmazonSession,
                 debug: Optional[bool] = None,
                 config: Optional[AmazonOrdersConfig] = None) -> None:
        if not debug:
            debug = amazon_session.debug
        if not config:
            config = amazon_session.config

        #: The AmazonSession to use for requests.
        self.amazon_session: AmazonSession = amazon_session
        #: The AmazonOrdersConfig to use.
        self.config: AmazonOrdersConfig = config

        #: Set logger ``DEBUG`` and send output to ``stderr``.
        self.debug: bool = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    def get_order_history(self,
                          year: int = datetime.date.today().year,
                          start_index: Optional[int] = None,
                          full_details: bool = False) -> List[Order]:
        """
        Get the Amazon order history for the given year.

        :param year: The year for which to get history.
        :param start_index: The index to start at within the history.
        :param full_details: Will execute an additional request per Order in the retrieved history to fully
            populate it.
        :return: A list of the requested Orders.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        self.amazon_session.get(self.config.constants.ORDER_HISTORY_LANDING_URL)

        orders = []
        optional_start_index = f"&startIndex={start_index}" if start_index else ""
        next_page: Optional[str] = (
            "{url}?{query_param}=year-{year}{optional_start_index}"
        ).format(
            url=self.config.constants.ORDER_HISTORY_URL,
            query_param=self.config.constants.HISTORY_FILTER_QUERY_PARAM,
            year=year,
            optional_start_index=optional_start_index
        )

        while next_page:
            self.amazon_session.get(next_page)
            response_parsed = self.amazon_session.last_response_parsed

            for order_tag in util.select(response_parsed, self.config.selectors.ORDER_HISTORY_ENTITY_SELECTOR):
                order: Order = self.config.order_cls(order_tag, self.config)

                if full_details:
                    if not order.order_details_link:
                        logger.warning(f"Order {order.order_number} was partially populated, "
                                       f"since order_details_link was not found.")
                    elif len(util.select(order.parsed, self.config.selectors.ORDER_SKIP_ITEMS)) > 0:
                        logger.warning(f"Order {order.order_number} was partially populated, "
                                       f"since it is an unsupported Order type.")
                    else:
                        self.amazon_session.get(order.order_details_link)
                        order_details_tag = util.select_one(self.amazon_session.last_response_parsed,
                                                            self.config.selectors.ORDER_DETAILS_ENTITY_SELECTOR)
                        order = self.config.order_cls(order_details_tag, self.config, full_details=True, clone=order)

                orders.append(order)

            next_page = None
            if start_index is None:
                next_page_tag = util.select_one(response_parsed, self.config.selectors.NEXT_PAGE_LINK_SELECTOR)
                if next_page_tag:
                    next_page = str(next_page_tag["href"])
                    if not next_page.startswith("http"):
                        next_page = f"{self.config.constants.BASE_URL}{next_page}"
                else:
                    logger.debug("No next page")
            else:
                logger.debug("start_index is given, not paging")

        return orders

    def get_order(self,
                  order_id: str) -> Order:
        """
        Get the Amazon order represented by the ID.

        :param order_id: The Amazon Order ID to lookup.
        :return: The requested Order.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        self.amazon_session.get(f"{self.config.constants.ORDER_DETAILS_URL}?orderID={order_id}")
        if not self.amazon_session.last_response.url.startswith(self.config.constants.ORDER_DETAILS_URL):
            raise AmazonOrdersNotFoundError(f"Amazon redirected, which likely means Order {order_id} was not found.")

        order_details_tag = util.select_one(self.amazon_session.last_response_parsed,
                                            self.config.selectors.ORDER_DETAILS_ENTITY_SELECTOR)
        order: Order = self.config.order_cls(order_details_tag, self.config, full_details=True)

        return order
