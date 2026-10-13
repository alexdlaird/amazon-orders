__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from typing import Optional

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable

logger = logging.getLogger(__name__)


class Invoice(Parsable):
    """
    An invoice document (a PDF) of an Amazon :class:`~amazonorders.entity.order.Order`, such as an invoice or a credit
    note, parsed from the Order's invoice list. See :func:`~amazonorders.orders.AmazonOrders.get_invoices`, and
    :func:`~amazonorders.orders.AmazonOrders.download_invoice` for the document itself.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig,
                 order_number: Optional[str] = None) -> None:
        super().__init__(parsed, config)

        #: The Order number the document belongs to.
        self.order_number: Optional[str] = order_number
        #: The document's name, as Amazon lists it, e.g. ``Invoice``, ``Invoice 2``, or ``Credit note``.
        self.name: Optional[str] = self.safe_parse(self._parse_name)
        #: The link to download the document. Amazon generates a new one on each request, so don't store it, get the
        #: Order's invoices again instead.
        self.link: Optional[str] = self.safe_parse(self._parse_link)
        #: ``True`` if the document is a credit note (a refund) rather than an invoice.
        self.credit_note: bool = self.safe_parse(self._parse_credit_note) or False

    def __repr__(self) -> str:
        return f"<Invoice #{self.order_number}: \"{self.name}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Invoice #{self.order_number}: {self.name}\n  Link: {self.link}"

    def _parse_name(self) -> Optional[str]:
        return " ".join(self.parsed.text.split()) or None

    def _parse_link(self) -> Optional[str]:
        href = self.parsed.get("href")
        if not href:
            return None

        return self.with_base_url(str(href))

    def _parse_credit_note(self) -> bool:
        if not self.name:
            return False

        return self.config.selectors.FIELD_INVOICE_CREDIT_NOTE_TEXT.lower() in self.name.lower()
