__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"


class Selectors:
    ##########################################################################
    # CSS selectors for AuthForms
    ##########################################################################

    SIGN_IN_FORM_SELECTOR = "form[name='signIn']"
    MFA_DEVICE_SELECT_FORM_SELECTOR = "form#auth-select-device-form"
    MFA_DEVICE_SELECT_INPUT_SELECTOR = "input[name='otpDeviceContext']"
    MFA_DEVICE_SELECT_INPUT_SELECTOR_VALUE = "value"
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

    ORDER_HISTORY_ENTITY_SELECTOR = ["div.order", "div.order-card"]
    ORDER_DETAILS_ENTITY_SELECTOR = ["div#orderDetails", "div#ordersContainer", "[data-component='orderCard']"]
    ITEM_ENTITY_SELECTOR = ["div:has(> div.yohtmlc-item)", ".item-box", "[data-component='purchasedItems']"]
    SHIPMENT_ENTITY_SELECTOR = ["div.shipment", "div.delivery-box", "[data-component='shipments']"]

    #####################################
    # CSS selectors for Item fields
    #####################################

    FIELD_ITEM_IMG_LINK_SELECTOR = "a img"
    FIELD_ITEM_QUANTITY_SELECTOR = ["span.item-view-qty", "span.product-image__qty", "[data-component='itemQuantity']"]
    FIELD_ITEM_TITLE_SELECTOR = [".yohtmlc-item a", ".yohtmlc-product-title", "[data-component='itemTitle']"]
    FIELD_ITEM_LINK_SELECTOR = [".yohtmlc-item a", "a:has(> .yohtmlc-product-title)", "[data-component='itemTitle'] a"]
    FIELD_ITEM_TAG_ITERATOR_SELECTOR = [".yohtmlc-item div", "[data-component='purchasedItemsRightGrid']"]

    #####################################
    # CSS selectors for Order fields
    #####################################

    FIELD_ORDER_DETAILS_LINK_SELECTOR = "a.yohtmlc-order-details-link"
    FIELD_ORDER_NUMBER_SELECTOR = ["bdi[dir='ltr']", "span[dir='ltr']"]
    FIELD_ORDER_GRAND_TOTAL_SELECTOR = ["div.yohtmlc-order-total span.value", "div.order-header div.a-column.a-span2"]
    FIELD_ORDER_PLACED_DATE_SELECTOR = ["span.order-date-invoice-item",
                                        "div.a-span3"]
    FIELD_ORDER_PAYMENT_METHOD_SELECTOR = "img.pmts-payment-credit-card-instrument-logo"
    FIELD_ORDER_PAYMENT_METHOD_LAST_4_SELECTOR = "img.pmts-payment-credit-card-instrument-logo"
    FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR = ["div#od-subtotals div.a-row", "[data-component='orderSubtotals']"]
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
    FIELD_SHIPMENT_DELIVERY_STATUS_SELECTOR = ["div.js-shipment-info-container div.a-row",
                                               "span.delivery-box__primary-text"]

    #####################################
    # CSS selectors for Recipient fields
    #####################################

    FIELD_RECIPIENT_NAME_SELECTOR = ["li.displayAddressFullName",
                                     "div:nth-child(1)"]
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
