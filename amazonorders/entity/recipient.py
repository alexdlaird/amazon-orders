import logging
from typing import Optional

from bs4 import Tag

from amazonorders import constants
from amazonorders.entity.parsable import Parsable

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"

logger = logging.getLogger(__name__)


class Recipient(Parsable):
    """
    The person receiving an Amazon `~amazonorders.entity.order.Order`.
    """

    def __init__(self,
                 parsed: Tag) -> None:
        super().__init__(parsed)

        #: The Recipient name.
        self.name: str = self.safe_simple_parse(selector=constants.FIELD_RECIPIENT_NAME_SELECTOR, required=True)
        #: The Recipient address.
        self.address: Optional[str] = self.safe_parse(self._parse_address)

    def __repr__(self) -> str:
        return "<Recipient: \"{}\">".format(self.name)

    def __str__(self) -> str:  # pragma: no cover
        return "Recipient: {}".format(self.name)

    def _parse_address(self) -> Optional[str]:
        value = self.simple_parse(constants.FIELD_RECIPIENT_ADDRESS1_SELECTOR)

        if value:
            values = [
                value,
                self.simple_parse(constants.FIELD_RECIPIENT_ADDRESS2_SELECTOR),
                self.simple_parse(constants.FIELD_RECIPIENT_ADDRESS_CITY_STATE_POSTAL_SELECTOR),
                self.simple_parse(constants.FIELD_RECIPIENT_ADDRESS_COUNTRY_SELECTOR),
            ]
            value = "\n".join(filter(None, values))
        else:
            value = self.simple_parse(constants.FIELD_RECIPIENT_ADDRESS_FALLBACK_SELECTOR)

        return value
