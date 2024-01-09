__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


class Order:
    def __init__(self, order_card_parsed) -> None:
        self.order_card_parsed = order_card_parsed

        self.title = self.order_card_parsed.find("div", {"class": "yohtmlc-item"}).find("a").text.strip()

    def __repr__(self) -> str:
        return "<Order: \"{}\">".format(self.title)

    def __str__(self) -> str:  # pragma: no cover
        return self.title
