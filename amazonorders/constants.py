__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from urllib.parse import urlencode


class Constants:
    """
    A class containing useful constants. Extend and override with ``constants_class`` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"constants_class": "my_module.MyConstants"})
    """

    def __init__(self, base_url: str = None):
        """
        Initialize constants with an optional base URL.
        
        :param base_url: The Amazon base URL (e.g., "https://www.amazon.com.au").
                        If None, defaults to US Amazon or environment variable.
        """
        # Set the base URL - either from parameter or environment variable at initialization time
        if base_url:
            self._base_url = base_url
        else:
            # Capture environment variable at initialization time (like original static behavior)
            self._base_url = os.environ.get("AMAZON_BASE_URL", "https://www.amazon.com")
        
        # Initialize all URLs and headers at construction time (static behavior)
        self._initialize_constants()

    def _initialize_constants(self):
        """Initialize all constants based on the base URL (mimicking original static behavior)."""
        # Set URLs
        self.BASE_URL = self._base_url
        self.SIGN_IN_URL = f"{self.BASE_URL}/ap/signin"
        self.SIGN_IN_CLAIM_URL = f"{self.BASE_URL}/ax/claim"
        self.SIGN_OUT_URL = f"{self.BASE_URL}/gp/flex/sign-out.html"
        self.ORDER_HISTORY_URL = f"{self.BASE_URL}/your-orders/orders"
        self.ORDER_DETAILS_URL = f"{self.BASE_URL}/gp/your-account/order-details"
        self.TRANSACTION_HISTORY_URL = f"{self.BASE_URL}{self.TRANSACTION_HISTORY_ROUTE}"
        
        # Set association handle based on site (like original static logic would)
        assoc_handle = "usflex"  # Default for US
        if "amazon.com.au" in self.BASE_URL:
            assoc_handle = "auflex"
        elif "amazon.co.uk" in self.BASE_URL:
            assoc_handle = "ukflex"
        elif "amazon.ca" in self.BASE_URL:
            assoc_handle = "caflex"

        
        # Set sign-in query params
        self.SIGN_IN_QUERY_PARAMS = {
            "openid.pape.max_auth_age": "0",
            "openid.return_to": f"{self.BASE_URL}/?ref_=nav_custrec_signin",
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.assoc_handle": assoc_handle,
            "openid.mode": "checkid_setup",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.ns": "http://specs.openid.net/auth/2.0"
        }
        
        # Set language
        accept_language = "en-US,en;q=0.9"  # Default
        if "amazon.com.au" in self.BASE_URL:
            accept_language = "en-AU,en;q=0.9,en-US;q=0.8"
        elif "amazon.co.uk" in self.BASE_URL:
            accept_language = "en-GB,en;q=0.9,en-US;q=0.8"
        elif "amazon.ca" in self.BASE_URL:
            accept_language = "en-CA,en;q=0.9,fr-CA;q=0.8,en-US;q=0.7"
            
        # Set static headers (like original)
        self.BASE_HEADERS = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                      "application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": accept_language,
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
        
        # Set currency symbol based on Amazon site
        currency_symbol = "$"  # Default
        env_symbol = os.environ.get("AMAZON_CURRENCY_SYMBOL")
        if env_symbol:
            currency_symbol = env_symbol
        elif "amazon.com.au" in self.BASE_URL:
            currency_symbol = "A$"
        elif "amazon.co.uk" in self.BASE_URL:
            currency_symbol = "£"
        elif "amazon.ca" in self.BASE_URL:
            currency_symbol = "C$"
            
        self.CURRENCY_SYMBOL = currency_symbol    ##########################################################################
    # General URL
    ##########################################################################

    ##########################################################################
    # URLs for AmazonSession
    ##########################################################################
    
    # These are now set in _initialize_constants() as static attributes
    
    ##########################################################################
    # URLs for Orders
    ##########################################################################

    HISTORY_FILTER_QUERY_PARAM = "timeFilter"

    ##########################################################################
    # URLs for Transactions
    ##########################################################################

    TRANSACTION_HISTORY_ROUTE = "/cpe/yourpayments/transactions"

    ##########################################################################
    # Headers
    ##########################################################################
    
    # BASE_HEADERS is now set in _initialize_constants() as a static attribute

    # Maintain backward compatibility
    @property
    def base_headers(self):
        """Backward compatibility property for base_headers."""
        return self.BASE_HEADERS

    ##########################################################################
    # Authentication
    ##########################################################################

    COOKIES_SET_WHEN_AUTHENTICATED = ["x-main"]
    JS_ROBOT_TEXT_REGEX = r"[.\s\S]*verify that you're not a robot[.\s\S]*Enable JavaScript[.\s\S]*"

    ##########################################################################
    # Currency
    ##########################################################################
    
    # CURRENCY_SYMBOL is now set in _initialize_constants() as a static attribute

    # Maintain backward compatibility - currency_symbol is now available directly as CURRENCY_SYMBOL
    @property
    def currency_symbol(self):
        """Backward compatibility property for currency_symbol."""
        return self.CURRENCY_SYMBOL

    def format_currency(self,
                        amount: float) -> str:
        formatted_amt = "{currency_symbol}{amount:,.2f}".format(currency_symbol=self.currency_symbol,
                                                                amount=abs(amount))
        if round(amount, 2) < 0:
            return f"-{formatted_amt}"
        return formatted_amt
