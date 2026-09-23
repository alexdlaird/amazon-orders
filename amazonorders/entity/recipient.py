__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import re
from typing import List, Optional

from bs4 import Tag

from amazonorders import util
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
        if self.config.constants.LOCALE.MULTILINE_ADDRESS:
            return self._parse_address_lines()

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

    def _parse_address_lines(self) -> Optional[str]:
        lines: List[str] = []
        for tag in util.select(self.parsed, self.config.selectors.FIELD_RECIPIENT_ADDRESS_LINES_SELECTOR):
            # Lines are separated by <br> or, when Amazon renders the address inline, by commas
            for line in re.split(r"[\n,]", tag.get_text("\n")):
                line = re.sub(r"\s+", " ", line).strip()
                if line:
                    lines.append(line)

        return "\n".join(lines) or None
