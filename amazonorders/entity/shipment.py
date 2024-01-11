from amazonorders.entity.item import Item

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"


class Shipment:
    def __init__(self,
                 parsed,
                 order) -> None:
        self.parsed = parsed
        self.order = order

        self.items = self._parse_items()

    def __repr__(self) -> str:
        return "<Shipment: \"{}\">".format(self.items)

    def __str__(self) -> str:  # pragma: no cover
        return str(self.items)

    def _parse_items(self):
        return [Item(x) for x in self.parsed.find_all("div", {"class": "yohtmlc-item"})]
