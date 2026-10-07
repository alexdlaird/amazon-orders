__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from datetime import date
from typing import Optional, Union

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)


class GiftCardActivity(Parsable):
    """
    An entry in the Amazon Gift Card activity ledger, such as a Gift Card applied to an Order, a claim
    code redemption, a Reload, or a refund.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(parsed, config)

        #: The GiftCardActivity date.
        self.activity_date: Optional[date] = self.safe_parse(self._parse_activity_date)
        #: The GiftCardActivity description.
        self.description: Optional[str] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_GIFT_CARD_ACTIVITY_DESCRIPTION_SELECTOR)
        #: The GiftCardActivity amount, negative when the balance was debited and positive when it was credited.
        self.amount: Optional[float] = self.safe_parse(self._parse_amount)
        #: The GiftCardActivity credited the balance or not.
        self.is_credit: bool = bool(self.amount and self.amount > 0)
        #: The Gift Card balance after this GiftCardActivity.
        self.closing_balance: Optional[float] = self.safe_parse(self._parse_closing_balance)
        #: The Order number the GiftCardActivity references, or ``None`` when the row links no Order.
        self.order_number: Optional[str] = self.safe_parse(self._parse_order_number)
        #: The Order details link, or ``None`` when the row links no Order.
        self.order_details_link: Optional[str] = self.safe_parse(self._parse_order_details_link)

    def __repr__(self) -> str:
        return f"<GiftCardActivity {self.activity_date}: \"{self.description}, Amount: {self.amount}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"GiftCardActivity {self.activity_date}: {self.description}, Amount: {self.amount}"

    def _parse_activity_date(self) -> Optional[date]:
        value = self.simple_parse(self.config.selectors.FIELD_GIFT_CARD_ACTIVITY_DATE_SELECTOR, parse_date=True)

        if value is None:
            err_msg = ("GiftCardActivity.activity_date could not be parsed, but it's required. "
                       "Check if Amazon changed the HTML")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(f"{err_msg} or set warn_on_missing_required_field=True in config.")

            logger.warning(f"{err_msg}.")

        return value

    def _parse_amount(self) -> Union[float, int, None]:
        value = self.to_currency(self.simple_parse(self.config.selectors.FIELD_GIFT_CARD_ACTIVITY_AMOUNT_SELECTOR))

        if value is None:
            err_msg = ("GiftCardActivity.amount could not be parsed, but it's required. "
                       "Check if Amazon changed the HTML")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(f"{err_msg} or set warn_on_missing_required_field=True in config.")

            logger.warning(f"{err_msg}.")

        return value

    def _parse_closing_balance(self) -> Union[float, int, None]:
        return self.to_currency(
            self.simple_parse(self.config.selectors.FIELD_GIFT_CARD_ACTIVITY_CLOSING_BALANCE_SELECTOR))

    def _parse_order_number(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_GIFT_CARD_ACTIVITY_ORDER_NUMBER_SELECTOR)

        if not value:
            return None

        order_number = self.config.constants.parse_order_number(value)
        if not order_number:
            logger.warning(f"GiftCardActivity.order_number found but not an Order number: {value!r}. "
                           f"Check if Amazon changed the HTML.")

        return order_number

    def _parse_order_details_link(self) -> Optional[str]:
        if not self.order_number:
            return None

        return self.simple_parse(self.config.selectors.FIELD_GIFT_CARD_ACTIVITY_ORDER_LINK_SELECTOR,
                                 attr_name="href")
