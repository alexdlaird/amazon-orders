__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


class Order:
    def __init__(self, soup) -> None:
        self.soup = soup

    def __repr__(self) -> str:
        return self.soup.find("div", {"class": "yohtmlc-product-title"}).text

    def __str__(self) -> str:  # pragma: no cover
        return self.soup.find("div", {"class": "yohtmlc-product-title"}).text
