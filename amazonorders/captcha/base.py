"""
Base class for CAPTCHA solver implementations.
"""

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from abc import ABC, abstractmethod
from typing import Dict, Optional


class CaptchaSolver(ABC):
    """
    Abstract base class for CAPTCHA solving service integrations.

    Subclasses must implement :meth:`solve_amazon_waf` to handle
    Amazon WAF CAPTCHA challenges.
    """

    def __init__(self, api_key: str):
        """
        Initialize the CAPTCHA solver.

        :param api_key: API key for the CAPTCHA solving service
        """
        self.api_key = api_key

    @abstractmethod
    def solve_amazon_waf(
        self,
        sitekey: str,
        iv: str,
        context: str,
        page_url: str,
        challenge_script: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Solve an Amazon WAF CAPTCHA challenge.

        :param sitekey: Value of 'key' from window.gokuProps
        :param iv: Value of 'iv' from window.gokuProps
        :param context: Value of 'context' from window.gokuProps
        :param page_url: Full URL of the page with the CAPTCHA
        :param challenge_script: URL of challenge.js script (optional)
        :return: Dict containing at minimum 'existing_token' (the aws-waf-token cookie value)
        :raises Exception: If solving fails or times out
        """
        pass
