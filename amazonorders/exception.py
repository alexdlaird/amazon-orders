__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Union, Optional, Dict, Any


class AmazonOrdersError(Exception):
    """
    Raised when a general ``amazon-orders`` error has occurred.
    """

    def __init__(self,
                 error: Union[str, BaseException],
                 meta: Optional[Dict[str, Any]] = None) -> None:
        super(AmazonOrdersError, self).__init__(error)

        #: Metadata for context around when the error was raised.
        self.meta = meta


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
