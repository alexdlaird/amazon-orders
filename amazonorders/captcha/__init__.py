"""
CAPTCHA solving integration for Amazon WAF challenges.

This module provides built-in support for 2captcha CAPTCHA solving service.
Usage is opt-in - simply pass your API key to AmazonSession.

Example::

    from amazonorders.session import AmazonSession

    session = AmazonSession(
        "email@example.com",
        "password",
        captcha_solver="2captcha",
        captcha_api_key="your-api-key"
    )
    session.login()
"""

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from typing import TYPE_CHECKING

from amazonorders.captcha.base import CaptchaSolver

if TYPE_CHECKING:
    from amazonorders.captcha.twocaptcha import TwoCaptchaSolver

logger = logging.getLogger(__name__)

# Lazy-loaded solver class
_TwoCaptchaSolver = None


def _get_twocaptcha_solver():
    """Lazily import and return TwoCaptchaSolver class."""
    global _TwoCaptchaSolver
    if _TwoCaptchaSolver is None:
        from amazonorders.captcha.twocaptcha import TwoCaptchaSolver
        _TwoCaptchaSolver = TwoCaptchaSolver
    return _TwoCaptchaSolver


def get_solver(service: str, api_key: str) -> CaptchaSolver:
    """
    Get a CAPTCHA solver instance for the specified service.

    :param service: Service name (currently only ``"2captcha"`` is supported)
    :param api_key: API key for the service
    :return: CaptchaSolver instance
    :raises ValueError: If service is not supported
    :raises ImportError: If required library is not installed
    """
    if service in {"2captcha"}:
        solver_class = _get_twocaptcha_solver()
        return solver_class(api_key)
    else:
        raise ValueError(
            f"Unsupported CAPTCHA solver '{service}'. Supported: 2captcha"
        )


def __getattr__(name):
    """Module-level __getattr__ for lazy loading of solver classes."""
    if name == "TwoCaptchaSolver":
        return _get_twocaptcha_solver()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
