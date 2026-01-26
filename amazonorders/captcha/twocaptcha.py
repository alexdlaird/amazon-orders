"""
2captcha.com CAPTCHA solver implementation using official 2captcha-python library.

This module provides integration with 2captcha.com for solving Amazon WAF CAPTCHAs.
See https://2captcha.com/2captcha-api#amazon_waf for API documentation.
"""

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import json
from typing import Dict, Optional

from amazonorders.captcha.base import CaptchaSolver
from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)

# Try to import the official library
try:
    from twocaptcha import TwoCaptcha as OfficialTwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False
    OfficialTwoCaptcha = None


class TwoCaptchaSolver(CaptchaSolver):
    """
    CAPTCHA solver using 2captcha.com service via official 2captcha-python library.

    Example::

        from amazonorders.captcha import TwoCaptchaSolver

        solver = TwoCaptchaSolver("your-api-key")
        result = solver.solve_amazon_waf(
            sitekey="AQIDAHjcYu...",
            iv="CgAHazE...",
            context="aaaa...",
            page_url="https://www.amazon.com/..."
        )
        # result["existing_token"] contains the aws-waf-token cookie value
    """

    def __init__(self, api_key: str):
        """
        Initialize the 2captcha solver.

        :param api_key: 2captcha API key
        """
        super().__init__(api_key)
        
        if not TWOCAPTCHA_AVAILABLE:
            raise ImportError(
                "2captcha-python library is required for 2captcha support. "
                "Install with: pip install amazon-orders[twocaptcha]"
            )
        
        self.solver = OfficialTwoCaptcha(api_key)

    def solve_amazon_waf(
        self,
        sitekey: str,
        iv: str,
        context: str,
        page_url: str,
        challenge_script: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Solve Amazon WAF CAPTCHA via 2captcha.com using official library.

        :param sitekey: Value of 'key' from window.gokuProps
        :param iv: Value of 'iv' from window.gokuProps
        :param context: Value of 'context' from window.gokuProps
        :param page_url: Full URL of the page with the CAPTCHA
        :param challenge_script: URL of challenge.js script (optional but recommended)
        :return: Dict with 'captcha_voucher' and 'existing_token'
        :raises Exception: If submission fails or solving times out
        """
        logger.debug(f"Submitting Amazon WAF CAPTCHA to 2captcha for {page_url}")
        
        try:
            # Convert parameters to the format expected by the official library
            # Map our parameter names to the official library parameter names
            kwargs = {}
            if challenge_script:
                kwargs['challenge_script'] = challenge_script
            
            result = self.solver.amazon_waf(
                sitekey=sitekey,
                iv=iv,
                context=context,
                url=page_url,
                **kwargs
            )
            
            logger.debug("CAPTCHA solved successfully by 2captcha")
            
            # The official library returns the solution directly, we need to format it
            # to match the expected return format
            return {
                "existing_token": json.loads(result.get("code", "{}")).get("existing_token")
            }
            
        except Exception as e:
            logger.error(f"2captcha solving failed: {str(e)}")
            raise AmazonOrdersError(f"2captcha solving failed: {str(e)}")
