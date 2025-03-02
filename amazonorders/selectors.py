__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"


class Selectors:
    """
    A class containing CSS selectors. Extend and override with `selectors_class` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"selectors_class": "my_module.MyConstants"})
    """

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

    ORDER_HISTORY_ENTITY_SELECTOR = ["div.order-card",
                                     "div.order"]
    ORDER_DETAILS_ENTITY_SELECTOR = ["div#orderDetails",
                                     "div#ordersContainer"]
    ITEM_ENTITY_SELECTOR = ["[data-component='purchasedItems'] .a-fixed-left-grid",
                            "div:has(> div.yohtmlc-item)",
                            ".item-box"]
    SHIPMENT_ENTITY_SELECTOR = ["[data-component='orderCard'] [data-component='shipments'] .a-box",
                                "div.shipment",
                                "div.delivery-box"]
    # Selectors defined here mean we don't have a reliable way to parse all details in an Order, so Items and
    # Shipments will be skipped
    ORDER_SKIP_ITEMS = [
        # Identifies an Amazon Fresh order
        ".brand-info-box .brand-logo img",
        # Identifies a Whole Foods Market order
        "a.yohtmlc-order-details-link[href^='/wholefoodsmarket']"
    ]

    #####################################
    # CSS selectors for Item fields
    #####################################

    FIELD_ITEM_IMG_LINK_SELECTOR = "a img"
    FIELD_ITEM_QUANTITY_SELECTOR = [".od-item-view-qty",
                                    "span.item-view-qty",
                                    "span.product-image__qty"]
    FIELD_ITEM_TITLE_SELECTOR = ["[data-component='itemTitle']",
                                 ".yohtmlc-item a", ".yohtmlc-product-title"]
    FIELD_ITEM_LINK_SELECTOR = ["[data-component='itemTitle'] a",
                                ".yohtmlc-item a",
                                "a:has(> .yohtmlc-product-title)",
                                ".yohtmlc-product-title a"]
    FIELD_ITEM_TAG_ITERATOR_SELECTOR = [".yohtmlc-item div"]
    FIELD_ITEM_PRICE_SELECTOR = ["[data-component='unitPrice'] .a-text-price :not(.a-offscreen)",
                                 ".yohtmlc-item .a-color-price"]
    FIELD_ITEM_SELLER_SELECTOR = ["[data-component='orderedMerchant']"] + FIELD_ITEM_TAG_ITERATOR_SELECTOR
    FIELD_ITEM_RETURN_SELECTOR = ["[data-component='itemReturnEligibility']"] + FIELD_ITEM_TAG_ITERATOR_SELECTOR

    #####################################
    # CSS selectors for Order fields
    #####################################

    FIELD_ORDER_DETAILS_LINK_SELECTOR = ["a.yohtmlc-order-details-link",
                                         # Would like to use this or similar, but not yet sure how consisten it is
                                         # ".order-header__header-link-list-item:first-of-type a"
                                         ]
    FIELD_ORDER_NUMBER_SELECTOR = ["[data-component='orderId']",
                                   "[data-component='briefOrderInfo'] div.a-column",
                                   ".order-date-invoice-item bdi[dir='ltr']",
                                   "bdi[dir='ltr']",
                                   "span[dir='ltr']"]
    FIELD_ORDER_GRAND_TOTAL_SELECTOR = ["div.yohtmlc-order-total span.value",
                                        "div.order-header div.a-column.a-span2",
                                        "div.order-header div.a-col-left .a-span9"]
    FIELD_ORDER_PLACED_DATE_SELECTOR = ["[data-component='orderDate']",
                                        "span.order-date-invoice-item",
                                        "[data-component='briefOrderInfo'] div.a-column",
                                        "div.a-span3"]
    FIELD_ORDER_PAYMENT_METHOD_SELECTOR = "img.pmts-payment-credit-card-instrument-logo"
    FIELD_ORDER_PAYMENT_METHOD_LAST_4_SELECTOR = "span:has(img.pmts-payment-credit-card-instrument-logo):last-child"
    FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR = ["[data-component='orderSubtotals'] div.a-row",
                                                   "div#od-subtotals div.a-row"]
    FIELD_ORDER_SUBTOTALS_TAG_POPOVER_PRELOAD_SELECTOR = ".a-popover-preload"
    FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR = "div.a-span-last"
    FIELD_ORDER_ADDRESS_SELECTOR = "div.displayAddressDiv"
    FIELD_ORDER_ADDRESS_FALLBACK_1_SELECTOR = "div.recipient span.a-declarative"
    FIELD_ORDER_ADDRESS_FALLBACK_2_SELECTOR = "script[id^='shipToData']"
    FIELD_ORDER_GIFT_CARD_INSTANCE_SELECTOR = ".gift-card-instance"

    #####################################
    # CSS selectors for Shipment fields
    #####################################

    FIELD_SHIPMENT_TRACKING_LINK_SELECTOR = ["span.track-package-button a",
                                             "a[href*='ship-track?itemId=']"]
    FIELD_SHIPMENT_DELIVERY_STATUS_SELECTOR = ["div.js-shipment-info-container div.a-row",
                                               "span.delivery-box__primary-text",
                                               ".yohtmlc-shipment-status-primaryText",
                                               ".od-status-message"]

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

    #####################################
    # CSS selectors for Transaction fields
    #####################################

    TRANSACTION_HISTORY_FORM_SELECTOR = "form:has(input[name='ppw-widgetState'])"
    TRANSACTION_DATE_CONTAINERS_SELECTOR = "div.apx-transaction-date-container"
    TRANSACTIONS_CONTAINER_SELECTOR = "div"
    TRANSACTIONS_SELECTOR = "div.apx-transactions-line-item-component-container:has(*)"

    TRANSACTIONS_NEXT_PAGE_INPUT_SELECTOR = [
        "input[type='submit'][name^='ppw-widgetEvent:DefaultNextPageNavigationEvent']"]
    TRANSACTIONS_NEXT_PAGE_INPUT_STATE_SELECTOR = "input[name='ppw-widgetState']"
    TRANSACTIONS_NEXT_PAGE_INPUT_IE_SELECTOR = "input[name='ie']"

    FIELD_TRANSACTION_COMPLETED_DATE_SELECTOR = "span"
    FIELD_TRANSACTION_PAYMENT_METHOD_SELECTOR = [
        "div.apx-transactions-line-item-component-container > div:nth-child(1) span.a-size-base"]
    FIELD_TRANSACTION_GRAND_TOTAL_SELECTOR = [
        "div.apx-transactions-line-item-component-container > div:nth-child(1) span.a-size-base-plus"]
    FIELD_TRANSACTION_ORDER_NUMBER_SELECTOR = [
        "div.apx-transactions-line-item-component-container div .a-span12"]
    FIELD_TRANSACTION_ORDER_LINK_SELECTOR = [
        "div.apx-transactions-line-item-component-container a.a-link-normal"]
    FIELD_TRANSACTION_SELLER_NAME_SELECTOR = [
        "div.apx-transactions-line-item-component-container :has(a.a-link-normal) + div"]
