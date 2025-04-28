# canada.py

from amazonorders.constants import Constants as BaseConstants
from amazonorders.selectors import Selectors as BaseSelectors

class CanadaConstants(BaseConstants):
    # Override the base domain and order-history path
    BASE_DOMAIN = "www.amazon.ca"
    ORDER_HISTORY_PATH = "/gp/your-account/order-history"

class CanadaSelectors(BaseSelectors):
    # Update any URL regex patterns if needed
    ORDER_HISTORY_URL = rf"https://{CanadaConstants.BASE_DOMAIN}{CanadaConstants.ORDER_HISTORY_PATH}\?.*"

    # Override the CSS selector that matches each order row on Amazon.ca
    # (Inspect amazon.ca's “Your Orders” page to verify the correct class/ID.)
    ORDER_TAG = "div.your-orders-content .order-row"  

    # Similarly adjust other selectors:
    ORDER_DATE_TAG      = ".order-info .order-date"
    ORDER_NUMBER_TAG    = ".order-info .order-number"
    ORDER_TOTAL_TAG     = ".order-info .order-total"
    ORDER_LINK_TAG      = ".order-info a[href*='/gp/your-account/view-receipt']"
