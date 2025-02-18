__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
from typing import Dict, List, Optional, Tuple

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
        -> Tuple[List[Transaction], Optional[str], Optional[Dict[str, str]]]:
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
            logger.warning("Could not find transactions container tag in Transaction form.")
            continue

        transaction_tags = util.select(transactions_container_tag, config.selectors.TRANSACTIONS_SELECTOR)
        for transaction_tag in transaction_tags:
            transaction = Transaction(transaction_tag, config, date)
            transactions.append(transaction)

    form_state_input = util.select_one(form_tag, config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_STATE_SELECTOR)
    form_ie_input = util.select_one(form_tag, config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_IE_SELECTOR)
    next_page_input = util.select_one(form_tag, config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_SELECTOR)
    if not next_page_input or not form_state_input or not form_ie_input:
        return transactions, None, None

    next_page_post_url = str(form_tag["action"])
    next_page_post_data = {
        "ppw-widgetState": str(form_state_input["value"]),
        "ie": str(form_ie_input["value"]),
        str(next_page_input["name"]): "",
    }

    return transactions, next_page_post_url, next_page_post_data


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

        #: The AmazonSession to use for requests.
        self.amazon_session: AmazonSession = amazon_session
        #: The AmazonOrdersConfig to use.
        self.config: AmazonOrdersConfig = config

        #: Set logger ``DEBUG`` and send output to ``stderr``.
        self.debug: bool = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    def get_transactions(self,
                         days: int = 365) -> List[Transaction]:
        """
        Get the Amazon Transactions for the given number of days.

        :param days: The number of days worth of transactions to get.
        :return: A list of the requested Transactions.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        min_date = datetime.date.today() - datetime.timedelta(days=days)

        self.amazon_session.get(self.config.constants.TRANSACTION_HISTORY_LANDING_URL)
        if not self.amazon_session.last_response_parsed:
            raise AmazonOrdersError("Could not get transaction history landing page.")

        form_tag = util.select_one(self.amazon_session.last_response_parsed,
                                   self.config.selectors.TRANSACTION_HISTORY_FORM_SELECTOR)

        transactions: List[Transaction] = []
        while form_tag:
            loaded_transactions, next_page_post_url, next_page_post_data = (
                _parse_transaction_form_tag(form_tag, self.config)
            )
            for transaction in loaded_transactions:
                if transaction.completed_date >= min_date:
                    transactions.append(transaction)
                else:
                    return transactions

            if next_page_post_url is None:
                return transactions

            self.amazon_session.post(next_page_post_url, data=next_page_post_data)
            if not self.amazon_session.last_response_parsed:
                raise AmazonOrdersError("Could not get next transaction history page.")

            form_tag = util.select_one(self.amazon_session.last_response_parsed,
                                       self.config.selectors.TRANSACTION_HISTORY_FORM_SELECTOR)

        return transactions
