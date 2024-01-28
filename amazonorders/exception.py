__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"


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


class AmazonOrderEntityError(AmazonOrdersError):
    """
    Raised when an ``amazon-orders`` entity parsing error has occurred.
    """
    pass
