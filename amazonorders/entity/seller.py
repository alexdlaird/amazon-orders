__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from typing import Optional

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable

logger = logging.getLogger(__name__)


class Seller(Parsable):
    """
    An Amazon Seller of an Amazon :class:`~amazonorders.entity.item.Item`.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(parsed, config)

        #: The Seller name.
        self.name: str = self.safe_simple_parse(self.config.selectors.FIELD_SELLER_NAME_SELECTOR,
                                                prefix_split="Sold by:")
        #: The Seller link.
        self.link: Optional[str] = self.safe_simple_parse(selector=self.config.selectors.FIELD_SELLER_LINK_SELECTOR,
                                                          attr_name="href")

    def __repr__(self) -> str:
        return f"<Seller: \"{self.name}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"Seller: {self.name}"
