import logging
from datetime import datetime

from amazonorders.entity.parsable import Parsable
from amazonorders.entity.seller import Seller
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"

logger = logging.getLogger(__name__)


class Item(Parsable):
    def __init__(self,
                 parsed) -> None:
        super().__init__(parsed)

        self.title = self._safe_parse(self._parse_title)
        self.link = self._safe_parse(self._parse_link)
        self.price = self._safe_parse(self._parse_price)
        self.seller = self._safe_parse(self._parse_seller)
        self.condition = self._safe_parse(self._parse_condition)
        self.return_eligible_date = self._safe_parse(self._parse_return_eligible_date)

    def __repr__(self) -> str:
        return "<Item: \"{}\">".format(self.title)

    def __str__(self) -> str:  # pragma: no cover
        return "Item: \"{}\"".format(self.title)

    def _parse_title(self):
        tag = self.parsed.find("a")
        return tag.text.strip()

    def _parse_link(self):
        tag = self.parsed.find("a")
        return "{}{}".format(BASE_URL, tag.attrs["href"])

    def _parse_price(self):
        for tag in self.parsed.find_all("div"):
            if tag.text.strip().startswith("$"):
                return tag.text.strip().replace("$", "")

    def _parse_seller(self):
        for tag in self.parsed.find_all("div"):
            if "Sold by:" in tag.text:
                return Seller(tag, order=self)

    def _parse_condition(self):
        for tag in self.parsed.find_all("div"):
            if "Condition:" in tag.text:
                return tag.text.split("Condition:")[1].strip()

    def _parse_return_eligible_date(self):
        for tag in self.parsed.find_all("div"):
            if "Return" in tag.text:
                split_str = "through "
                if "closed on " in tag.text:
                    split_str = "closed on "
                date_str = tag.text.strip().split(split_str)[1]
                return datetime.strptime(date_str, "%b %d, %Y").date()
