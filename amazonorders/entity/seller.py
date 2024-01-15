import logging

from amazonorders.entity.parsable import Parsable
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"

logger = logging.getLogger(__name__)


class Seller(Parsable):
    def __init__(self,
                 parsed,
                 item=None,
                 order=None) -> None:
        super().__init__(parsed)

        self.item = item
        self.order = order

        self.name = self._safe_parse(self._parse_name)
        self.link = self._safe_parse(self._parse_link)

    def __repr__(self) -> str:
        return "<Seller: \"{}\">".format(self.name)

    def __str__(self) -> str:  # pragma: no cover
        return "Seller: \"{}\"".format(self.name)

    def _parse_name(self):
        tag = self.parsed.find("a")
        if not tag:
            tag = self.parsed.find("span")
        value = tag.text
        if "Sold by:" in value:
            value = value.split("Sold by:")[1]
        return value.strip()

    def _parse_link(self):
        tag = self.parsed.find("a")
        if tag:
            return "{}{}".format(BASE_URL, tag.attrs["href"])
