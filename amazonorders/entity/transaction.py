__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from typing import Any, Dict, Optional, Type, TypeVar, Union

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersError
from amazonorders.localization import EnUS

logger = logging.getLogger(__name__)

TransactionEntity = TypeVar("TransactionEntity", bound="Transaction")

#: An Order number within a Transaction's Order description.
_ORDER_NUMBER_RE = re.compile(r"\b(\d{3}-\d{7}-\d{7}|D\d{2}-\d{7}-\d{7})\b")


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
        #: The Transaction payment method's last digits, parsed from :attr:`payment_method`.
        #: ``None`` if no masked digits.
        self.payment_method_last_4: Optional[str] = self.safe_parse(self._parse_payment_method_last_4)
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

    @classmethod
    def from_data(cls: Type[TransactionEntity],
                  data: Dict[str, Any],
                  config: AmazonOrdersConfig,
                  completed_date: date) -> TransactionEntity:
        """
        Build a Transaction from the JSON data that some Amazon domains (e.g. amazon.de) embed in the
        Transactions page, rather than from its HTML.

        :param data: A Transaction of the page's ``transactionList``.
        :param config: The config to use.
        :param completed_date: The Transaction completed date.
        :return: The Transaction.
        """
        transaction = cls.__new__(cls)
        Parsable.__init__(transaction, None, config)  # type: ignore[arg-type]

        payment_data = data.get("paymentMethodDisplayStringData") or {}
        payment_method_name = payment_data.get("paymentMethodName")
        last_digits = (payment_data.get("paymentMethodNumber") or {}).get("lastDigits")
        # Amazon renders the amount in en-US format regardless of the domain's locale (e.g. "-€22.73")
        grand_total = EnUS().parse_currency(data.get("formattedAmount") or "")
        # When a Transaction covers more than one Order, only the first one is used
        order_data = (data.get("orderData") or [{}])[0]
        order_number_match = _ORDER_NUMBER_RE.search(order_data.get("orderDisplayString") or "")

        transaction.completed_date = completed_date
        transaction.payment_method = f"{payment_method_name} ****{last_digits}" \
            if payment_method_name and last_digits else payment_method_name  # type: ignore[assignment]
        transaction.payment_method_last_4 = last_digits
        transaction.grand_total = grand_total  # type: ignore[assignment]
        transaction.is_refund = grand_total is not None and grand_total > 0
        transaction.order_number = order_number_match.group(1) if order_number_match else None  # type: ignore
        transaction.order_details_link = order_data.get("orderDetailsUrl") or (
            f"{config.constants.ORDER_DETAILS_URL}?orderID={transaction.order_number}"
            if transaction.order_number else None)  # type: ignore[assignment]
        transaction.seller = data.get("statementDescriptor")  # type: ignore[assignment]

        return transaction

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

    def _parse_payment_method_last_4(self) -> Optional[str]:
        if not self.payment_method:
            return None

        match = re.search(r"\*+(\d+)$", self.payment_method)

        return match.group(1) if match else None
