__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"


class Address:
    def __init__(self, parsed) -> None:
        self.parsed = parsed

        # TODO: this needs to be parsed out from JS using the div ID

        self.name = None
        self.street_address = None
        self.city = None
        self.zip_code = None
        self.country = None

    def __repr__(self) -> str:
        return "<Address: \"{}\">".format(self.name)

    def __str__(self) -> str:  # pragma: no cover
        return self.name
