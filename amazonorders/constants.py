__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os


class Constants:
    """
    A class containing useful constants. Extend and override with `constants_class` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"constants_class": "my_module.MyConstants"})
    """

    ##########################################################################
    # General URL
    ##########################################################################

    BASE_URL = os.environ.get("AMAZON_BASE_URL", "https://www.amazon.com")

    ##########################################################################
    # URLs for AmazonSession
    ##########################################################################

    SIGN_IN_URL = f"{BASE_URL}/gp/sign-in.html"
    SIGN_IN_REDIRECT_URL = f"{BASE_URL}/ap/signin"
    SIGN_OUT_URL = f"{BASE_URL}/gp/sign-out.html"

    ##########################################################################
    # URLs for orders
    ##########################################################################

    ORDER_HISTORY_LANDING_URL = f"{BASE_URL}/gp/css/order-history"
    ORDER_HISTORY_URL = f"{BASE_URL}/your-orders/orders"
    ORDER_DETAILS_URL = f"{BASE_URL}/gp/your-account/order-details"
    HISTORY_FILTER_QUERY_PARAM = "timeFilter"

    ##########################################################################
    # URLs for transactions
    ##########################################################################

    TRANSACTION_HISTORY_LANDING_ROUTE = "/cpe/yourpayments/transactions"
    TRANSACTION_HISTORY_LANDING_URL = f"{BASE_URL}{TRANSACTION_HISTORY_LANDING_ROUTE}"

    ##########################################################################
    # Headers
    ##########################################################################

    BASE_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                  "application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": BASE_URL,
        "Referer": SIGN_IN_REDIRECT_URL,
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "macOS",
        "Sec-Ch-Viewport-Width": "1393",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Viewport-Width": "1393",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/130.0.0.0 Safari/537.36",
    }

    def format_currency(self, amount):
        formatted_amt = "${:,.2f}".format(abs(amount))
        if round(amount, 2) < 0:
            return f"-{formatted_amt}"
        return formatted_amt
