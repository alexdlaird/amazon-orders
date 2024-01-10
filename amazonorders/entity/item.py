__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"


class Item:
    def __init__(self, parsed) -> None:
        self.parsed = parsed

        self.title = self.parsed.find("a").text.strip()
        # TODO: this is shown on the page but isn't within the parsed div we have here
        self.return_eligible_date = None

    def __repr__(self) -> str:
        return "<Item: \"{}\">".format(self.title)

    def __str__(self) -> str:  # pragma: no cover
        return self.title
