import logging

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"

logger = logging.getLogger(__name__)


class Recipient:
    def __init__(self,
                 parsed) -> None:
        self.parsed = parsed

        self.name = self._parse_name()
        self.address = self._parse_address()

    def __repr__(self) -> str:
        return "<Recipient: \"{}\">".format(self.name)

    def __str__(self) -> str:  # pragma: no cover
        return "Recipient: \"{}\"".format(self.name)

    def _parse_name(self):
        try:
            tag = self.parsed.find("li", {"class": "displayAddressFullName"})
            if not tag:
                tag = self.parsed.find_all("div")[1]
            return tag.text.strip()
        except (AttributeError, IndexError):
            logger.warning("When building Recipient, `name` could not be parsed.", exc_info=True)

    def _parse_address(self):
        try:
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
        except (AttributeError, IndexError):
            logger.warning("When building Recipient, `address` could not be parsed.", exc_info=True)
