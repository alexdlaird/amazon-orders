__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from typing import Optional

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable

logger = logging.getLogger(__name__)


class Recipient(Parsable):
    """
    The person receiving an Amazon :class:`~amazonorders.entity.order.Order`.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(parsed, config)

        #: The Recipient name.
        self.name: str = self.safe_simple_parse(selector=self.config.selectors.FIELD_RECIPIENT_NAME_SELECTOR,
                                                required=True)
        #: The Recipient address.
        self.address: Optional[str] = self.safe_parse(self._parse_address)

    def __repr__(self) -> str:
        return f"<Recipient: \"{self.name}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Recipient: {self.name}"

    def _parse_address(self) -> Optional[str]:
        value = self.simple_parse(self.config.selectors.FIELD_RECIPIENT_ADDRESS1_SELECTOR)

        if value:
            values = [
                value,
                self.simple_parse(self.config.selectors.FIELD_RECIPIENT_ADDRESS2_SELECTOR),
                self.simple_parse(self.config.selectors.FIELD_RECIPIENT_ADDRESS_CITY_STATE_POSTAL_SELECTOR),
                self.simple_parse(self.config.selectors.FIELD_RECIPIENT_ADDRESS_COUNTRY_SELECTOR),
            ]
            value = "\n".join(filter(None, values))
        else:
            value = self.simple_parse(self.config.selectors.FIELD_RECIPIENT_ADDRESS_FALLBACK_SELECTOR)

        return value
