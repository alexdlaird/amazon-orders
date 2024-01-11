import logging

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
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
            tag = self.parsed.find_all("div")
            return tag[1].text.strip()
        except (AttributeError, IndexError):
            logger.warning("When building Recipient, `name` could not be parsed.", exc_info=True)

    def _parse_address(self):
        try:
            tag = self.parsed.find_all("div")
            return tag[2].text.strip()
        except (AttributeError, IndexError):
            logger.warning("When building Recipient, `address` could not be parsed.", exc_info=True)
