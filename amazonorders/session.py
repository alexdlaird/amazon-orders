__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonauth import session as amazonauth_session

from amazonorders.conf import AmazonOrdersConfig

__all__ = [
    "AmazonSession",
]


class AmazonSession(amazonauth_session.AmazonSession):
    #: The config class built when no ``config`` is given.
    CONFIG_CLASS = AmazonOrdersConfig

    config: AmazonOrdersConfig
