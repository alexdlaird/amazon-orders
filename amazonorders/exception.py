__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonauth.exception import (
    AmazonAuthBrowserNotInstalledError as AmazonOrdersBrowserNotInstalledError,
    AmazonAuthChallengeUnsolvedError as AmazonOrdersChallengeUnsolvedError,
    AmazonAuthError as AmazonOrdersError,
    AmazonAuthRedirectError as AmazonOrdersAuthRedirectError,
    AmazonAuthSignInError as AmazonOrdersAuthError,
    AmazonAuthWafSolverError as AmazonOrdersWafSolverError,
)

__all__ = [
    "AmazonOrdersError",
    "AmazonOrdersNotFoundError",
    "AmazonOrdersUnavailableError",
    "AmazonOrdersAuthError",
    "AmazonOrdersAuthRedirectError",
    "AmazonOrdersEntityError",
    "AmazonOrdersEncryptedPageError",
    "AmazonOrdersChallengeUnsolvedError",
    "AmazonOrdersWafSolverError",
    "AmazonOrdersBrowserNotInstalledError",
]


class AmazonOrdersNotFoundError(AmazonOrdersError):
    """
    Raised when an Amazon page is not found.
    """
    pass


class AmazonOrdersUnavailableError(AmazonOrdersError):
    """
    Raised when Amazon shows a page saying it could not load what was requested. Amazon shows this page both when
    what was requested does not exist and when Amazon had an issue on their end, so trying again later may succeed.
    ``meta["amazon_message"]`` is the text Amazon's page showed.
    """
    pass


class AmazonOrdersEntityError(AmazonOrdersError):
    """
    Raised when an ``amazon-orders`` entity parsing error has occurred.
    """
    pass


class AmazonOrdersEncryptedPageError(AmazonOrdersError):
    """
    Raised when Amazon serves an Order history page with its Order cards encrypted. The same URL with
    ``disableCsd=no-js`` renders them readable, which ``get_orders()`` requests itself before raising this.
    """
    pass
