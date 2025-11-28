__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from typing import Union, Optional

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)


class Transaction(Parsable):
    """
    An Amazon Transaction.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig,
                 completed_date: date) -> None:
        super().__init__(parsed, config)

        #: The Transaction completed date.
        self.completed_date: date = completed_date
        #: The Transaction payment method.
        self.payment_method: str = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_TRANSACTION_PAYMENT_METHOD_SELECTOR
        )
        #: The Transaction grand total.
        self.grand_total: float = self.safe_parse(self._parse_grand_total)
        #: The Transaction was a refund or not.
        self.is_refund: bool = self.grand_total > 0
        #: The Transaction Order number.
        self.order_number: str = self.safe_parse(self._parse_order_number)
        #: The Transaction Order details link.
        self.order_details_link: str = self.safe_parse(self._parse_order_details_link)
        #: The Transaction seller name.
        self.seller: str = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_TRANSACTION_SELLER_NAME_SELECTOR
        )

    def __repr__(self) -> str:
        return f"<Transaction {self.completed_date}: \"Order #{self.order_number}, Grand Total: {self.grand_total}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Transaction {self.completed_date}: Order #{self.order_number}, Grand Total: {self.grand_total}"

    def _parse_grand_total(self) -> Union[float, int, None]:
        value = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_GRAND_TOTAL_SELECTOR)

        value = self.to_currency(value)

        if value is None:  # pragma: no cover
            err_msg = ("Order.grand_total did not populate, but it's required. "
                       "Check if Amazon changed the HTML.")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(err_msg)
            else:
                logger.warning(err_msg)

        return value

    def _parse_order_number(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_ORDER_NUMBER_SELECTOR)

        if value is None:  # pragma: no cover
            err_msg = ("Transaction.order_number did not populate, but it's required. "
                       "Check if Amazon changed the HTML.")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(err_msg)
            else:
                logger.warning(err_msg)

                return None

        match = re.match(".*#([0-9-]+)$", value)
        value = match.group(1) if match else ""

        return value

    def _parse_order_details_link(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_ORDER_LINK_SELECTOR, attr_name="href")

        if not value and self.order_number:
            value = f"{self.config.constants.ORDER_DETAILS_URL}?orderID={self.order_number}"

        return value
