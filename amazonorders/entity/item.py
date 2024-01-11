import logging
from datetime import datetime

from amazonorders.entity.seller import Seller
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"

logger = logging.getLogger(__name__)


class Item:
    def __init__(self,
                 parsed) -> None:
        self.parsed = parsed

        self.title = self._parse_title()
        self.link = self._parse_link()
        self.price = self._parse_price()
        self.seller = self._parse_seller()
        self.condition = self._parse_condition()
        self.return_eligible_date = self._parse_return_eligible_date()

    def __repr__(self) -> str:
        return "<Item: \"{}\">".format(self.title)

    def __str__(self) -> str:  # pragma: no cover
        return "Item: \"{}\"".format(self.title)

    def _parse_title(self):
        try:
            tag = self.parsed.find("a")
            return tag.text.strip()
        except AttributeError:
            logger.warning("When building Item, `title` could not be parsed.", exc_info=True)

    def _parse_link(self):
        try:
            tag = self.parsed.find("a")
            return "{}{}".format(BASE_URL, tag.attrs["href"])
        except AttributeError:
            logger.warning("When building Item, `link` could not be parsed.", exc_info=True)

    def _parse_price(self):
        try:
            for tag in self.parsed.find_all("div"):
                if tag.text.strip().startswith("$"):
                    return tag.text.strip().replace("$", "")
        except (AttributeError, IndexError):
            logger.warning("When building Item, `price` could not be parsed.", exc_info=True)

    def _parse_seller(self):
        try:
            for tag in self.parsed.find_all("div"):
                if "Sold by:" in tag.text:
                    return Seller(tag, order=self)
        except (AttributeError, IndexError):
            logger.warning("When building Order, `seller` could not be parsed.", exc_info=True)

    def _parse_condition(self):
        try:
            for tag in self.parsed.find_all("div"):
                if "Condition:" in tag.text:
                    return tag.text.split("Condition:")[1].strip()
        except (AttributeError, IndexError):
            logger.warning("When building Order, `condition` could not be parsed.", exc_info=True)

    def _parse_return_eligible_date(self):
        try:
            for tag in self.parsed.find_all("div"):
                if "Return" in tag.text:
                    split_str = "through "
                    if "closed on " in tag.text:
                        split_str = "closed on "
                    date_str = tag.text.strip().split(split_str)[1]
                    return datetime.strptime(date_str, "%b %d, %Y").date()
        except (AttributeError, IndexError):
            logger.warning("When building Item, `return_eligible_date` could not be parsed.", exc_info=True)
