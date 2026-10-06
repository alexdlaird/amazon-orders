__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from datetime import date
from typing import Optional, Type, TypeVar, Union

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)

TransactionEntity = TypeVar("TransactionEntity", bound="Transaction")


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
        self.payment_method: Optional[str] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_TRANSACTION_PAYMENT_METHOD_SELECTOR
        )
        #: The Transaction payment method's last digits, parsed from :attr:`payment_method`.
        #: ``None`` if no masked digits.
        self.payment_method_last_4: Optional[str] = self.safe_parse(self._parse_payment_method_last_4)
        #: The Transaction grand total.
        self.grand_total: float = self.safe_parse(self._parse_grand_total)
        #: The Transaction was a refund or not.
        self.is_refund: bool = self.grand_total > 0
        #: The Transaction Order number, or ``None`` when the row carries no Order number.
        self.order_number: Optional[str] = self.safe_parse(self._parse_order_number)
        #: The Transaction Order details link.
        self.order_details_link: Optional[str] = self.safe_parse(self._parse_order_details_link)
        #: The Transaction seller name, or ``None`` when the row carries none.
        self.seller: Optional[str] = self.safe_parse(self._parse_seller)

    @classmethod
    def from_fields(cls: Type[TransactionEntity],
                    config: AmazonOrdersConfig,
                    completed_date: date,
                    grand_total: float,
                    payment_method: Optional[str] = None,
                    payment_method_last_4: Optional[str] = None,
                    order_number: Optional[str] = None,
                    order_details_link: Optional[str] = None,
                    seller: Optional[str] = None) -> TransactionEntity:
        """
        Build a Transaction from values already read off the page, for an Amazon site that renders its
        Transactions as data rather than HTML (for instance, as embedded JSON). :attr:`is_refund`, and a
        missing :attr:`payment_method_last_4` or :attr:`order_details_link`, are derived the same way as when parsing
        HTML.

        :param config: The config to use.
        :param completed_date: The Transaction completed date.
        :param grand_total: The Transaction grand total.
        :param payment_method: The Transaction payment method, with any masked digits (e.g. ``Visa ****1234``).
        :param payment_method_last_4: The payment method's last digits, if the page gives them separately from
            :attr:`payment_method`.
        :param order_number: The Transaction Order number.
        :param order_details_link: The Transaction Order details link.
        :param seller: The Transaction seller name.
        :return: The Transaction.
        """
        transaction = cls.__new__(cls)
        Parsable.__init__(transaction, None, config)  # type: ignore[arg-type]

        transaction.completed_date = completed_date
        transaction.payment_method = payment_method
        transaction.payment_method_last_4 = payment_method_last_4 or transaction._parse_payment_method_last_4()
        transaction.grand_total = grand_total
        transaction.is_refund = grand_total > 0
        transaction.order_number = order_number
        transaction.order_details_link = order_details_link or transaction._order_details_link_fallback()
        transaction.seller = seller

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

        order_number = self.config.constants.parse_order_number(value)
        if not order_number:
            logger.warning(f"Transaction.order_number found but not an Order number: {value!r}. "
                           f"Check if Amazon changed the HTML.")

            return None

        return order_number

    def _parse_seller(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_SELLER_NAME_SELECTOR)

        if value and value == self.order_number:
            return None

        return value

    def _parse_order_details_link(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_TRANSACTION_ORDER_LINK_SELECTOR, attr_name="href")

        if not value:
            value = self._order_details_link_fallback()

        return value

    def _order_details_link_fallback(self) -> Optional[str]:
        if not self.order_number:
            return None

        return f"{self.config.constants.ORDER_DETAILS_URL}?orderID={self.order_number}"

    def _parse_payment_method_last_4(self) -> Optional[str]:
        if not self.payment_method:
            return None

        match = re.search(r"\*+(\d+)$", self.payment_method)

        return match.group(1) if match else None
