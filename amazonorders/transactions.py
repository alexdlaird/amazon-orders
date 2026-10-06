__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any

from bs4 import BeautifulSoup, Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.transaction import Transaction
from amazonorders.exception import AmazonOrdersEntityError, AmazonOrdersError
from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)


class TransactionsPage:
    """
    Fetches and parses one page of Transaction history. Extend and override with ``transactions_page_class`` in
    the config, for an Amazon site that structures its Transactions page differently (for instance, one that
    renders it from embedded data, or loads further pages from an API):

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"transactions_page_class": "my_module.MyTransactionsPage"})

    :func:`get_page` is used when fetching Transactions with a session, and :func:`parse_page` when parsing an
    already-fetched page. Each Transaction is built with the
    :class:`~amazonorders.entity.transaction.Transaction` class in use (``transaction_class`` in the config).
    """

    def __init__(self,
                 config: AmazonOrdersConfig) -> None:
        #: The config to use.
        self.config: AmazonOrdersConfig = config

    def get_page(self,
                 amazon_session: AmazonSession,
                 url: str,
                 next_page_data: Optional[Dict[str, Any]] = None) \
            -> Tuple[List[Transaction], Optional[Dict[str, Any]]]:
        """
        Fetch and parse a page of Transaction history.

        :param amazon_session: The authenticated session to fetch the page with.
        :param url: The Transaction history URL.
        :param next_page_data: The data to request the next page with, as returned for the previous page, or
            ``None`` for the first page.
        :return: The page's Transactions, and the data to request the next page with (``None`` if this is the
            last page).
        """
        page_response = amazon_session.post(url, data=next_page_data)
        amazon_session.check_response(page_response, meta=next_page_data)

        return self.parse_page(page_response.parsed)

    def parse_page(self,
                   parsed: Tag) -> Tuple[List[Transaction], Optional[Dict[str, Any]]]:
        """
        Parse a page of Transaction history.

        :param parsed: The parsed Transaction history page.
        :return: The page's Transactions, and the data to request the next page with (``None`` if this is the
            last page).
        :raises AmazonOrdersError: If the page could not be parsed.
        """
        form_tag = util.select_one(parsed, self.config.selectors.TRANSACTION_HISTORY_FORM_SELECTOR)

        if not form_tag:
            container_tag = util.select_one(parsed, self.config.selectors.TRANSACTION_HISTORY_CONTAINER_SELECTOR)
            if container_tag and self.config.selectors.TRANSACTION_HISTORY_EMPTY_TEXT in container_tag.text:
                return [], None

            raise AmazonOrdersError("Could not parse Transaction history. Check if Amazon changed the HTML.")

        return self._parse_transaction_form_tag(form_tag)

    def _parse_transaction_form_tag(self,
                                    form_tag: Tag) -> Tuple[List[Transaction], Optional[Dict[str, Any]]]:
        config = self.config
        transactions = []
        date_container_tags = util.select(form_tag, config.selectors.TRANSACTION_DATE_CONTAINERS_SELECTOR)
        for date_container_tag in date_container_tags:
            date_tag = util.select_one(date_container_tag, config.selectors.FIELD_TRANSACTION_COMPLETED_DATE_SELECTOR)
            if not date_tag:
                logger.warning("Could not find date tag in Transaction form.")
                continue

            date_str = date_tag.text
            date = config.constants.parse_date(date_str)
            if date is None:
                err_msg = (f"Transaction date {date_str!r} could not be parsed, but it's required. Check if "
                           f"Amazon changed the HTML")
                if not config.warn_on_missing_required_field:
                    raise AmazonOrdersEntityError(f"{err_msg} or set warn_on_missing_required_field=True in config.")

                logger.warning(f"{err_msg}.")
                continue

            transactions_container_tag = date_container_tag.find_next_sibling(
                config.selectors.TRANSACTIONS_CONTAINER_SELECTOR)
            if not isinstance(transactions_container_tag, Tag):
                logger.warning("Could not find Transactions container tag in Transaction form.")
                continue

            transaction_tags = util.select(transactions_container_tag, config.selectors.TRANSACTIONS_SELECTOR)
            for transaction_tag in transaction_tags:
                transaction = config.transaction_cls(transaction_tag, config, date)
                transactions.append(transaction)

        form_state_input = util.select_one(form_tag, config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_STATE_SELECTOR)
        form_ie_input = util.select_one(form_tag, config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_IE_SELECTOR)
        next_page_input = util.select_one(form_tag, config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_SELECTOR)
        if not next_page_input or not form_state_input or not form_ie_input:
            return transactions, None

        next_page_data = {
            "ppw-widgetState": str(form_state_input["value"]),
            "ie": str(form_ie_input["value"]),
            str(next_page_input["name"]): "",
        }

        return transactions, next_page_data


class AmazonTransactions:
    """
    Using an authenticated :class:`~amazonorders.session.AmazonSession`, can be used to query Amazon
    for Transaction details and history.
    """

    def __init__(self,
                 amazon_session: AmazonSession,
                 debug: Optional[bool] = None,
                 config: Optional[AmazonOrdersConfig] = None) -> None:
        if not debug:
            debug = amazon_session.debug
        if not config:
            config = amazon_session.config

        #: The session to use for requests.
        self.amazon_session: AmazonSession = amazon_session
        #: The config to use.
        self.config: AmazonOrdersConfig = config

        #: Setting logger to ``DEBUG`` will send output to ``stderr``.
        self.debug: bool = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    @staticmethod
    def parse_transactions(html: str,
                           config: AmazonOrdersConfig) -> List[Transaction]:
        """
        Parse an already-fetched Amazon Transactions page into Transactions, without a session driving
        the fetch. Useful for parsing HTML obtained elsewhere (a browser, a proxy, a fixture) and for
        network-free testing. Only the Transactions on the given page are returned; paging is a fetch
        concern.

        :param html: The Transactions page HTML to parse.
        :param config: The config providing the selectors used for parsing.
        :return: A list of the parsed Transactions.
        """
        parsed = BeautifulSoup(html, config.bs4_parser)
        transactions, _ = config.transactions_page_cls(config).parse_page(parsed)

        return transactions

    def get_transactions(self,
                         days: int = 365,
                         next_page_data: Optional[Dict[str, Any]] = None,
                         keep_paging: bool = True,
                         order_id: Optional[str] = None) -> List[Transaction]:
        """
        Get Amazon Transaction history for a given number of days, or for a single Order.

        :param days: The number of days worth of Transactions to get. Ignored when ``order_id`` is given.
        :param next_page_data: If a call to this method previously errored out, passing the exception's
            :attr:`~amazonorders.exception.AmazonOrdersError.meta` will continue paging where it left off.
        :param keep_paging: ``False`` if only one page should be fetched.
        :param order_id: If given, only Transactions for this Amazon Order ID are returned, scoped
            server-side via Amazon's ``transactionTag`` filter (the ``days`` window does not apply).
        :return: A list of the requested Transactions.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        url = self.config.constants.TRANSACTION_HISTORY_URL
        if order_id:
            url = f"{url}?transactionTag={order_id}"
        else:
            min_date = datetime.date.today() - datetime.timedelta(days=days)

        transactions_page = self.config.transactions_page_cls(self.config)
        transactions: List[Transaction] = []
        first_page = True
        while first_page or keep_paging:
            first_page = False

            loaded_transactions, next_page_data = transactions_page.get_page(self.amazon_session, url, next_page_data)

            for transaction in loaded_transactions:
                if order_id or transaction.completed_date >= min_date:
                    transactions.append(transaction)
                else:
                    next_page_data = None
                    break

            if not next_page_data:
                keep_paging = False

        return transactions
