__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from urllib.parse import urlencode

from amazonorders.constants import Constants


class AustralianConstants(Constants):
    """
    Constants specifically optimized for Amazon Australia (amazon.com.au).
    
    This class extends the base Constants class with Australia-specific configurations
    including proper headers, currency symbols, and authentication parameters.
    
    Usage:
        from amazonorders.conf import AmazonOrdersConfig
        
        config = AmazonOrdersConfig(data={
            "constants_class": "amazonorders.constants_au.AustralianConstants"
        })
        
        # Or set environment variable
        os.environ["AMAZON_BASE_URL"] = "https://www.amazon.com.au"
    """

    def __init__(self, base_url: str = None):
        # Use provided base_url or default to Australian Amazon
        if not base_url:
            base_url = "https://www.amazon.com.au"
        
        # Initialize parent class with Australian URL
        super().__init__(base_url=base_url)

    @property
    def BASE_URL(self):
        """Force Australian URL for this class."""
        return os.environ.get("AMAZON_BASE_URL", "https://www.amazon.com.au")
        
    # Australian-specific authentication cookies that may be set
    COOKIES_SET_WHEN_AUTHENTICATED = ["x-main", "session-id", "session-id-time"]
        
    @property 
    def SIGN_IN_QUERY_PARAMS(self):
        """Australian-specific query parameters for sign-in."""
        return {
            "openid.pape.max_auth_age": "0",
            "openid.return_to": f"{self.BASE_URL}/?ref_=nav_custrec_signin",
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.assoc_handle": "auflex",  # AU-specific handle
            "openid.mode": "checkid_setup",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.ns": "http://specs.openid.net/auth/2.0"
        }

    def _get_accept_language(self):
        """Override to always return Australian English for this class."""
        return "en-AU,en;q=0.9,en-US;q=0.8"

    @property
    def currency_symbol(self):
        """Override to return Australian dollar symbol."""
        # Still respect environment variable override
        env_symbol = os.environ.get("AMAZON_CURRENCY_SYMBOL")
        if env_symbol:
            return env_symbol
        return "A$"

    @property
    def base_headers(self):
        """Australian-optimized headers."""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                      "application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-AU,en;q=0.9,en-US;q=0.8",
            "Cache-Control": "max-age=0",
            "Device-Memory": "8",
            "Downlink": "10",
            "Dpr": "2",
            "Ect": "4g",
            "Origin": self.BASE_URL,
            "Host": self.BASE_URL.strip("https://").strip("http://"),
            "Priority": "u=0, i",
            "Referer": f"{self.SIGN_IN_URL}?{urlencode(self.SIGN_IN_QUERY_PARAMS)}",
            "Rtt": "0",
            "Sec-Ch-Device-Memory": "8",
            "Sec-Ch-Dpr": "2",
            "Sec-Ch-Ua": "\"Chromium\";v=\"130\", \"Google Chrome\";v=\"130\", \"Not?A_Brand\";v=\"99\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Ch-Ua-Platform-Version": "\"15.0.0\"",
            "Sec-Ch-Viewport-Width": "1512",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/130.0.0.0 Safari/537.36",
            "Viewport-Width": "1512"
        }