from bs4 import BeautifulSoup

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"


class Recipient:
    def __init__(self, script) -> None:
        self.parsed = BeautifulSoup(str(script.contents[0]).strip(), "html.parser")

        self.name = self.parsed.find_all("div")[1].text.strip()
        self.address = self.parsed.find_all("div")[2].text.strip()
        self.country = self.parsed.find_all("div")[3].text.strip()

    def __repr__(self) -> str:
        return "<Recipient: \"{}\">".format(self.name)

    def __str__(self) -> str:  # pragma: no cover
        return self.name
