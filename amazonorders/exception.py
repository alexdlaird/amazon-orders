__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"


class AmazonOrdersError(Exception):
    """
    Raised when a general ``amazon-orders`` error has occurred.
    """
    pass


class AmazonOrdersNotFoundError(AmazonOrdersError):
    """
    Raised when an Amazon page is not found.
    """
    pass


class AmazonOrdersAuthError(AmazonOrdersError):
    """
    Raised when an ``amazon-orders`` authentication error has occurred.
    """
    pass


class AmazonOrdersEntityError(AmazonOrdersError):
    """
    Raised when an ``amazon-orders`` entity parsing error has occurred.
    """
    pass
