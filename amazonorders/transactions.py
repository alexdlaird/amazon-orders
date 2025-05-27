__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any

from bs4 import Tag
from dateutil import parser

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.transaction import Transaction
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)


def _parse_transaction_form_tag(form_tag: Tag,
                                config: AmazonOrdersConfig) \
        -> Tuple[List[Transaction], Optional[Dict[str, str]]]:
    transactions = []
    date_container_tags = util.select(form_tag, config.selectors.TRANSACTION_DATE_CONTAINERS_SELECTOR)
    for date_container_tag in date_container_tags:
        date_tag = util.select_one(date_container_tag, config.selectors.FIELD_TRANSACTION_COMPLETED_DATE_SELECTOR)
        if not date_tag:
            logger.warning("Could not find date tag in Transaction form.")
            continue

        date_str = date_tag.text
        date = parser.parse(date_str).date()

        transactions_container_tag = date_container_tag.find_next_sibling(
            config.selectors.TRANSACTIONS_CONTAINER_SELECTOR)
        if not isinstance(transactions_container_tag, Tag):
            logger.warning("Could not find Transactions container tag in Transaction form.")
            continue

        transaction_tags = util.select(transactions_container_tag, config.selectors.TRANSACTIONS_SELECTOR)
        for transaction_tag in transaction_tags:
            transaction = Transaction(transaction_tag, config, date)
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

    def get_transactions(self,
                         days: int = 365,
                         next_page_data: Optional[Dict[str, Any]] = None,
                         keep_paging: bool = True) -> List[Transaction]:
        """
        Get Amazon Transaction history for a given number of days.

        :param days: The number of days worth of Transactions to get.
        :param next_page_data: If a call to this method previously errored out, passing the exception's
            :attr:`~amazonorders.exception.AmazonOrdersError.meta` will continue paging where it left off.
        :param keep_paging: ``False`` if only one page should be fetched.
        :return: A list of the requested Transactions.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        min_date = datetime.date.today() - datetime.timedelta(days=days)

        transactions: List[Transaction] = []
        first_page = True
        while first_page or keep_paging:
            first_page = False

            page_response = self.amazon_session.post(self.config.constants.TRANSACTION_HISTORY_URL,
                                                     data=next_page_data)
            self.amazon_session.check_response(page_response, meta=next_page_data)

            form_tag = util.select_one(page_response.parsed,
                                       self.config.selectors.TRANSACTION_HISTORY_FORM_SELECTOR)

            if not form_tag:
                transaction_container = util.select_one(page_response.parsed,
                                                        self.config.selectors.TRANSACTION_HISTORY_CONTAINER_SELECTOR)
                if transaction_container and "don't have any transactions" in transaction_container.text:
                    break
                else:
                    raise AmazonOrdersError("Could not parse Transaction history. Check if Amazon changed the HTML.")

            loaded_transactions, next_page_data = (
                _parse_transaction_form_tag(form_tag, self.config)
            )

            for transaction in loaded_transactions:
                if transaction.completed_date >= min_date:
                    transactions.append(transaction)
                else:
                    next_page_data = None
                    break

            if not next_page_data:
                keep_paging = False

        return transactions
