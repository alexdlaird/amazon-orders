__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


class AmazonOrdersError(Exception):
    """
    Raised when a general ``amazon-orders`` error has occurred.
    """
    pass


class AmazonOrdersAuthError(AmazonOrdersError):
    """
    Raised when an ``amazon-orders`` authentication error has occurred.
    """
    pass
