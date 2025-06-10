__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import asyncio
import concurrent.futures
import datetime
import logging
import os
from typing import List, Optional, Any, Callable

from bs4 import Tag

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

    def get_order(self,
                  order_id: str) -> Order:
        """
        Get the full details for a given Amazon order ID.

        :param order_id: The Amazon Order ID to lookup.
        :return: The requested Order.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        order_details_response = self.amazon_session.get(
            f"{self.config.constants.ORDER_DETAILS_URL}?orderID={order_id}")
        if order_details_response.response.url.startswith(self.config.constants.SIGN_IN_URL):
            self.amazon_session.raise_expired_session()

        if not order_details_response.response.url.startswith(self.config.constants.ORDER_DETAILS_URL):
            raise AmazonOrdersNotFoundError(f"Amazon redirected, which likely means Order {order_id} was not found.")

        order_details_tag = util.select_one(order_details_response.parsed,
                                            self.config.selectors.ORDER_DETAILS_ENTITY_SELECTOR)
        order: Order = self.config.order_cls(order_details_tag, self.config, full_details=True)

        return order

    def get_order_history(self,
                          year: int = datetime.date.today().year,
                          start_index: Optional[int] = None,
                          full_details: bool = False,
                          keep_paging: bool = True) -> List[Order]:
        """
        Get the Amazon order history for a given year.

        :param year: The year for which to get history.
        :param start_index: The index of the Order from which to start fetching in the history. Also see
            Order's :attr:`~amazonorders.entity.order.Order.index`.
        :param full_details: Get the full details for each order in the history. This will execute an additional
            request per Order.
        :param keep_paging: ``False`` if only one page should be fetched.
        :return: A list of the requested Orders.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        optional_start_index = f"&startIndex={start_index}" if start_index else ""
        next_page: Optional[str] = (
            "{url}?{query_param}=year-{year}{optional_start_index}"
        ).format(
            url=self.config.constants.ORDER_HISTORY_URL,
            query_param=self.config.constants.HISTORY_FILTER_QUERY_PARAM,
            year=year,
            optional_start_index=optional_start_index
        )

        current_index = int(start_index) if start_index else 0

        return asyncio.run(self._build_orders_async(next_page, keep_paging, full_details, current_index))

    async def _build_orders_async(self,
                                  next_page: Optional[str],
                                  keep_paging: bool,
                                  full_details: bool,
                                  current_index: int) -> List[Order]:
        order_tasks = []

        while next_page:
            page_response = self.amazon_session.get(next_page)
            if page_response.response.url.startswith(self.config.constants.SIGN_IN_URL):
                self.amazon_session.raise_expired_session()

            for order_tag in util.select(page_response.parsed,
                                         self.config.selectors.ORDER_HISTORY_ENTITY_SELECTOR):
                order_tasks.append(self._async_wrapper(self._build_order, order_tag, full_details, current_index))

                current_index += 1

            next_page = None
            if keep_paging:
                next_page_tag = util.select_one(page_response.parsed,
                                                self.config.selectors.NEXT_PAGE_LINK_SELECTOR)
                if next_page_tag:
                    next_page = str(next_page_tag["href"])
                    if not next_page.startswith("http"):
                        next_page = f"{self.config.constants.BASE_URL}{next_page}"
                else:
                    logger.debug("No next page")
            else:
                logger.debug("keep_paging is False, not paging")

        return await asyncio.gather(*order_tasks)

    def _build_order(self,
                     order_tag: List[Tag],
                     full_details: bool,
                     current_index: int) -> Order:
        order: Order = self.config.order_cls(order_tag, self.config, index=current_index)

        if full_details:
            if not order.order_details_link:
                logger.warning(f"Order {order.order_id} was partially populated, "
                               f"since order_details_link was not found.")
            elif len(util.select(order.parsed, self.config.selectors.ORDER_SKIP_ITEMS)) > 0:
                logger.warning(f"Order {order.order_id} was partially populated, "
                               f"since it is an unsupported Order type.")
            elif order.grand_total == 0:
                logger.warning(f"Order {order.order_id} was ignored for full details "
                               f"since grand_total was not found.")
            else:
                # TODO: be on the lookout for if this causes rate limit issues with Amazon, or races with the
                #  URL connection pool. If so, we may need to implement some retry logic here.
                order_details_response = self.amazon_session.get(order.order_details_link)
                if order_details_response.response.url.startswith(self.config.constants.SIGN_IN_URL):
                    self.amazon_session.raise_expired_session()
                order_details_tag = util.select_one(order_details_response.parsed,
                                                    self.config.selectors.ORDER_DETAILS_ENTITY_SELECTOR)
                if order_details_tag is None:
                    raise AmazonOrdersNotFoundError(f"Amazon redirected, which likely means Order {order.index} {order.order_id} {order_details_tag} \n"
                                                    f"\t was not found. details_link: {order.order_details_link} \n"
                                                    f"\t response_url: {order_details_response.response.url} \n"
                                                    # f"\t response_text: {order_details_response.response.text} \n"
                                                    f"\t response_status_code: {order_details_response.response.status_code} \n"
                                                    f"\t selector: {self.config.selectors.ORDER_DETAILS_ENTITY_SELECTOR} \n")
                                                    # f"response.parsed: {order_details_response.parsed}"
                
                order = self.config.order_cls(order_details_tag, self.config, full_details=True, clone=order,
                                              index=current_index)

        return order

    async def _async_wrapper(self,
                             func: Callable,
                             *args: Any) -> Order:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.thread_pool_size) as pool:
            result = await loop.run_in_executor(pool, func, *args)
        return result

    def download_invoice(self,
                         order_id: str,
                         order_date: datetime.date,
                         output_dir: str,
                         invoice_link: Optional[str] = None) -> List[str]:
        """Download invoice PDFs for the given order ID."""
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        invoice_urls: List[str] = []

        if invoice_link and "invoice.html" in invoice_link:
            if not invoice_link.startswith("http"):
                invoice_link = f"{self.config.constants.BASE_URL}{invoice_link}"
            menu_response = self.amazon_session.get(invoice_link)
            link_tags = util.select(
                menu_response.parsed,
                self.config.selectors.FIELD_ORDER_INVOICE_PDF_LINK_SELECTOR,
            )
            if not link_tags:
                link_tags = util.select(
                    menu_response.parsed,
                    self.config.selectors.FIELD_ORDER_INVOICE_PRINT_LINK_SELECTOR,
                )
            for tag in link_tags:
                href = tag.get("href")
                if href:
                    if not href.startswith("http"):
                        href = f"{self.config.constants.BASE_URL}{href}"
                    invoice_urls.append(href)

        if not invoice_urls:
            if invoice_link and "print" in invoice_link:
                invoice_urls.append(invoice_link)
            else:
                invoice_urls.append(
                    f"{self.config.constants.ORDER_INVOICE_URL}?orderID={order_id}"
                )

        file_paths: List[str] = []
        index = 1
        for invoice_url in invoice_urls:
            if not invoice_url.startswith("http"):
                invoice_url = f"{self.config.constants.BASE_URL}{invoice_url}"

            response = self.amazon_session.get(invoice_url, headers={"Accept": "application/pdf"})
            if response.response.status_code != 200:
                raise AmazonOrdersError(
                    f"Failed to download invoice: {response.response.status_code}"
                )

            base = f"AmazonInvoice_{order_date.strftime('%Y%m%d')}_{order_id}"
            if len(invoice_urls) > 1:
                file_path = os.path.join(output_dir, f"{base}_{index}.pdf")
            else:
                file_path = os.path.join(output_dir, f"{base}.pdf")
            with open(file_path, "wb") as f:
                f.write(response.response.content)
            file_paths.append(file_path)
            index += 1

        return file_paths
