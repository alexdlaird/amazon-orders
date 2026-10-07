__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from datetime import date
from typing import Optional, Union

from bs4 import Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersError
from amazonorders.selectors import Selector

logger = logging.getLogger(__name__)


class PrimePayment(Parsable):
    """
    A charge in the Prime membership payment history: the membership fee Amazon billed on a sign-up or
    renewal date.

    Each charge is a digital Order (a ``D01-`` ID) that neither the Order history nor the Digital Orders tab
    lists, so this entity is the index to it. The Order itself is fetched by :attr:`order_number` with
    :func:`~amazonorders.orders.AmazonOrders.get_order`, which renders the standard Order details layout for
    these IDs.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(parsed, config)

        #: The date the membership fee was charged, not the start of the membership period it covers.
        self.payment_date: Optional[date] = self.safe_simple_parse(
            selector=self.config.selectors.FIELD_PRIME_PAYMENT_DATE_SELECTOR,
            parse_date=True)
        #: The amount charged, tax included.
        self.total: Optional[float] = self.safe_parse(self._parse_total)
        #: The digital Order number (``D01-…``) of the charge.
        self.order_number: Optional[str] = self.safe_parse(self._parse_order_number)
        #: The Order details link. ``None`` when :attr:`order_number` is ``None``.
        self.order_details_link: Optional[str] = self.safe_parse(self._parse_order_details_link)
        #: The "View Receipt" link, the digital Order summary's print view. ``None`` when the card has none.
        self.receipt_link: Optional[str] = self.safe_parse(self._parse_receipt_link)

    def __repr__(self) -> str:
        return f"<PrimePayment {self.payment_date}: \"Order #{self.order_number}, Total: {self.total}\">"

    def __str__(self) -> str:
        return f"PrimePayment {self.payment_date}: Order #{self.order_number}, Total: {self.total}"

    def _parse_labeled_row(self,
                           label_selector: Selector) -> Optional[Tag]:
        label_tag = util.select_one(self.parsed, label_selector)

        return label_tag.parent if label_tag else None

    def _parse_labeled_value(self,
                             label_selector: Selector) -> Optional[str]:
        row_tag = self._parse_labeled_row(label_selector)
        value_tag = util.select_one(row_tag, self.config.selectors.FIELD_PRIME_PAYMENT_VALUE_SELECTOR) \
            if row_tag else None

        return value_tag.text.strip() if value_tag else None

    def _parse_total(self) -> Union[float, int, None]:
        text = self._parse_labeled_value(self.config.selectors.FIELD_PRIME_PAYMENT_TOTAL_LABEL_SELECTOR)
        value = self.to_currency(text) if text else None

        if value is None:
            err_msg = ("PrimePayment.total could not be parsed, but it's required. "
                       "Check if Amazon changed the HTML or set warn_on_missing_required_field=True in config.")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(err_msg)

            logger.warning(err_msg)

        return value

    def _parse_order_number(self) -> Optional[str]:
        value = self._parse_labeled_value(self.config.selectors.FIELD_PRIME_PAYMENT_ORDER_NUMBER_LABEL_SELECTOR)
        order_number = self.config.constants.parse_order_number(value) if value else None

        if order_number is None:
            err_msg = ("PrimePayment.order_number could not be parsed, but it's required. "
                       "Check if Amazon changed the HTML or set warn_on_missing_required_field=True in config.")
            if not self.config.warn_on_missing_required_field:
                raise AmazonOrdersError(err_msg)

            logger.warning(err_msg)

        return order_number

    def _parse_order_details_link(self) -> Optional[str]:
        if not self.order_number:
            return None

        return f"{self.config.constants.ORDER_DETAILS_URL}?orderID={self.order_number}"

    def _parse_receipt_link(self) -> Optional[str]:
        row_tag = self._parse_labeled_row(self.config.selectors.FIELD_PRIME_PAYMENT_RECEIPTS_LABEL_SELECTOR)
        link_tag = util.select_one(row_tag, self.config.selectors.FIELD_PRIME_PAYMENT_RECEIPT_LINK_SELECTOR) \
            if row_tag else None

        return self.with_base_url(str(link_tag["href"])) if link_tag else None
