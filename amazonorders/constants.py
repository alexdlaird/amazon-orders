__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"

##########################################################################
# General URL
##########################################################################

BASE_URL = "https://www.amazon.com"

##########################################################################
# URLs for AmazonSession
##########################################################################

SIGN_IN_URL = "{}/gp/sign-in.html".format(BASE_URL)
SIGN_IN_REDIRECT_URL = "{}/ap/signin".format(BASE_URL)
SIGN_OUT_URL = "{}/gp/sign-out.html".format(BASE_URL)

##########################################################################
# URLs for AmazonOrders
##########################################################################

ORDER_HISTORY_LANDING_URL = "{}/gp/css/order-history".format(BASE_URL)
ORDER_HISTORY_URL = "{}/your-orders/orders".format(BASE_URL)
ORDER_DETAILS_URL = "{}/gp/your-account/order-details".format(BASE_URL)
HISTORY_FILTER_QUERY_PARAM = "timeFilter"

##########################################################################
# Headers
##########################################################################

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
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
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

##########################################################################
# CSS selectors for AuthForms
##########################################################################

SIGN_IN_FORM_SELECTOR = "form[name='signIn']"
MFA_DEVICE_SELECT_FORM_SELECTOR = "form#auth-select-device-form"
MFA_DEVICE_SELECT_INPUT_SELECTOR = "input[name='otpDeviceContext']"
MFA_FORM_SELECTOR = "form#auth-mfa-form"
CAPTCHA_1_FORM_SELECTOR = "form.cvf-widget-form-captcha"
CAPTCHA_2_FORM_SELECTOR = "form:has(input[id^='captchacharacters'])"
CAPTCHA_OTP_FORM_SELECTOR = "form#verification-code-form"
DEFAULT_ERROR_TAG_SELECTOR = "div#auth-error-message-box"
CAPTCHA_1_ERROR_SELECTOR = "div.cvf-widget-alert"
CAPTCHA_2_ERROR_SELECTOR = "div.a-alert-info"

##########################################################################
# CSS selectors for pagination
##########################################################################

NEXT_PAGE_LINK_SELECTOR = "ul.a-pagination li.a-last a"

##########################################################################
# CSS selectors for Entities and Fields
#
# A ``FIELD_`` selector can be either a ``str`` or a ``list``. If a
# ``list`` is given, each selector in the list will be tried. The
# ``Parsable`` contains helper functions for parsing fields, including
# ``simple_parse()``, which is suitable for most fields when a ``FIELD_``
# is passed.
##########################################################################

ORDER_HISTORY_ENTITY_SELECTOR = "div.order"
ORDER_DETAILS_ENTITY_SELECTOR = "div#orderDetails"
ITEM_ENTITY_SELECTOR = "div:has(> div.yohtmlc-item)"
SHIPMENT_ENTITY_SELECTOR = "div.shipment"

#####################################
# CSS selectors for Item fields
#####################################

FIELD_ITEM_IMG_LINK_SELECTOR = "a img"
FIELD_ITEM_QUANTITY_SELECTOR = "span.item-view-qty"
FIELD_ITEM_TITLE_SELECTOR = ".yohtmlc-item a"
FIELD_ITEM_LINK_SELECTOR = ".yohtmlc-item a"
FIELD_ITEM_TAG_ITERATOR_SELECTOR = ".yohtmlc-item div"

#####################################
# CSS selectors for Order fields
#####################################

FIELD_ORDER_DETAILS_LINK_SELECTOR = "a.yohtmlc-order-details-link"
FIELD_ORDER_NUMBER_SELECTOR = "bdi[dir='ltr']"
FIELD_ORDER_GRAND_TOTAL_SELECTOR = "div.yohtmlc-order-total span.value"
FIELD_ORDER_PLACED_DATE_SELECTOR = ["span.order-date-invoice-item", "div.a-span3"]
FIELD_ORDER_PAYMENT_METHOD_SELECTOR = "img.pmts-payment-credit-card-instrument-logo"
FIELD_ORDER_PAYMENT_METHOD_LAST_4_SELECTOR = "img.pmts-payment-credit-card-instrument-logo"
FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR = "div#od-subtotals div.a-row"
FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR = "div.a-span-last"
FIELD_ORDER_ADDRESS_SELECTOR = "div.displayAddressDiv"
FIELD_ORDER_ADDRESS_FALLBACK_1_SELECTOR = "div.recipient span.a-declarative"
FIELD_ORDER_ADDRESS_FALLBACK_2_SELECTOR = "script[id^='shipToData']"
FIELD_ORDER_SHIPPED_DATE_SELECTOR = "#orderDetails div.a-box.a-last div div div.a-row:not(.a-color-success)"
FIELD_ORDER_REFUND_COMPLETED_DATE = "#orderDetails div.a-box.a-last div div div.a-row.a-color-success"

#####################################
# CSS selectors for Shipment fields
#####################################

FIELD_SHIPMENT_TRACKING_LINK_SELECTOR = "span.track-package-button a"
FIELD_SHIPMENT_DELIVERY_STATUS_SELECTOR = "div.js-shipment-info-container div.a-row"

#####################################
# CSS selectors for Recipient fields
#####################################

FIELD_RECIPIENT_NAME_SELECTOR = ["li.displayAddressFullName", "div:nth-child(1)"]
FIELD_RECIPIENT_ADDRESS1_SELECTOR = "li.displayAddressAddressLine1"
FIELD_RECIPIENT_ADDRESS2_SELECTOR = "li.displayAddressAddressLine2"
FIELD_RECIPIENT_ADDRESS_CITY_STATE_POSTAL_SELECTOR = "li.displayAddressCityStateOrRegionPostalCode"
FIELD_RECIPIENT_ADDRESS_COUNTRY_SELECTOR = "li.displayAddressCountryName"
FIELD_RECIPIENT_ADDRESS_FALLBACK_SELECTOR = "div:nth-child(2)"

#####################################
# CSS selectors for Seller fields
#####################################

FIELD_SELLER_NAME_SELECTOR = ["a", "span"]
FIELD_SELLER_LINK_SELECTOR = "a"
