from urllib.parse import urlparse
from urllib.parse import parse_qs

from amazonorders.entity.address import Address
from amazonorders.entity.shipment import Shipment
from amazonorders.entity.item import Item

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"


class Order:
    def __init__(self, parsed) -> None:
        self.parsed = parsed

        self.shipments = [Shipment(x, self) for x in self.parsed.find_all("div", {"class": "shipment"})]
        self.items = [Item(x) for x in self.parsed.find_all("div", {"class": "yohtmlc-item"})]
        self.order_details_link = self.parsed.find("a", {"class": "yohtmlc-order-details-link"}).attrs["href"]
        self.order_number = parse_qs(urlparse(self.order_details_link).query)["orderID"][0]
        self.total = self.parsed.find("div", {"class": "yohtmlc-order-total"}).text.strip().strip("$")
        self.order_placed_date = self.parsed.find("div", {"class": "a-span3"}).find("div", {"value"})
        self.ship_to = Address(self.parsed.find("div", {"class": "recipient"}))

    def __repr__(self) -> str:
        return "<Order: \"{}\">".format(self.items)

    def __str__(self) -> str:  # pragma: no cover
        return str(self.items)
