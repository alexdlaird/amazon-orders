import logging
from amazonorders.entity.parsable import Parsable

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"

logger = logging.getLogger(__name__)


class Recipient(Parsable):
    def __init__(self,
                 parsed) -> None:
        super().__init__(parsed)

        self.name = self._safe_parse(self._parse_name)
        self.address = self._safe_parse(self._parse_address)

    def __repr__(self) -> str:
        return "<Recipient: \"{}\">".format(self.name)

    def __str__(self) -> str:  # pragma: no cover
        return "Recipient: \"{}\"".format(self.name)

    def _parse_name(self):
        tag = self.parsed.find("li", {"class": "displayAddressFullName"})
        if not tag:
            tag = self.parsed.find_all("div")[1]
        return tag.text.strip()

    def _parse_address(self):
        tag = self.parsed.find("li", {"class": "displayAddressAddressLine1"})
        if tag:
            value = tag.text.strip()
            next_tag = self.parsed.find("li", {"class": "displayAddressAddressLine2"})
            if next_tag:
                value += "{}\n{}".format(tag.text.strip(), next_tag)
            next_tag = self.parsed.find("li", {"class": "displayAddressCityStateOrRegionPostalCode"})
            if next_tag:
                value += "\n{}".format(next_tag.text.strip())
            next_tag = self.parsed.find("li", {"class": "displayAddressCountryName"})
            if next_tag:
                value += "\n{}".format(next_tag.text.strip())
        else:
            value = self.parsed.find_all("div")[2].text
        return value.strip()
