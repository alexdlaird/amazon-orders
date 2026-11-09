__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings
from typing import Any

from amazonauth import session as amazonauth_session

from amazonorders.conf import AmazonOrdersConfig

__all__ = [
    "AmazonSession",
]


class AmazonSession(amazonauth_session.AmazonSession):
    #: The config class built when no ``config`` is given.
    CONFIG_CLASS = AmazonOrdersConfig

    config: AmazonOrdersConfig


def __getattr__(name: str) -> Any:
    if name in ("IODefault",):
        warnings.warn(f"amazonorders.session.{name} is deprecated and will be removed in 6.0. Use "
                      f"amazonauth.session.{name} instead.", DeprecationWarning, stacklevel=2)
        return getattr(amazonauth_session, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
