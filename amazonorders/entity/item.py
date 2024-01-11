import logging
from datetime import datetime
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"

logger = logging.getLogger(__name__)


class Item:
    def __init__(self,
                 parsed) -> None:
        self.parsed = parsed

        self.title = self._parse_title()
        self.link = self.parse_link()
        self.return_eligible_date = self._parse_return_eligible_date()

    def __repr__(self) -> str:
        return "<Item: \"{}\">".format(self.title)

    def __str__(self) -> str:  # pragma: no cover
        return self.title

    def _parse_title(self):
        try:
            tag = self.parsed.find("a")
            return tag.text.strip()
        except AttributeError:
            logger.warning("When building Item, `title` could not be parsed.", exc_info=True)

    def parse_link(self):
        try:
            tag = self.parsed.find("a")
            return "{}{}".format(BASE_URL, tag.attrs["href"])
        except AttributeError:
            logger.warning("When building Item, `link` could not be parsed.", exc_info=True)

    def _parse_return_eligible_date(self):
        try:
            tag = self.parsed.find_all("div", {"class": "a-row"})
            return_str = tag[2].text.strip()
            if return_str.startswith("Return eligible"):
                date_str = return_str.split("through ")[1]
                return datetime.strptime(date_str, "%b %d, %Y").date()
        except (AttributeError, IndexError):
            logger.warning("When building Item, `return_eligible_date` could not be parsed.", exc_info=True)
