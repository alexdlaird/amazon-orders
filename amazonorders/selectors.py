__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Optional


class Selector:
    """
    Can be used to extend the definition of a CSS selector, allowing for programmatic inspection
    of the selections results before determining if selector matches.
    """

    def __init__(self,
                 css_selector: str,
                 text: Optional[str] = None,
                 text_contains: Optional[str] = None) -> None:
        #: The CSS selector.
        self.css_selector: str = css_selector
        #: The text within the tag that must match exactly (after stripping).
        self.text: Optional[str] = text
        #: A substring within the tag's text that must be present (case-insensitive). Evaluated only when
        #: :attr:`text` is not set.
        self.text_contains: Optional[str] = text_contains


class Selectors:
    """
    A class containing CSS selectors. Extend and override with ``selectors_class`` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"selectors_class": "my_module.MySelectors"})
    """

    ##########################################################################
    # CSS selectors for Pages
    ##########################################################################

    BAD_INDEX_SELECTOR = "html.a-tablet"

    ##########################################################################
    # CSS selectors for AuthForms
    ##########################################################################

    ACIC_CHALLENGE_SELECTOR = "#aa-challenge-page-captcha-container"
    ACIC_VISUAL_CAPTCHA_MODAL_SELECTOR = ".amzn-captcha-modal"
    ACIC_VISUAL_CAPTCHA_CANVAS_SELECTOR = ".amzn-captcha-modal canvas"
    ACIC_VISUAL_CAPTCHA_QUESTION_SELECTOR = ".amzn-captcha-modal em"
    ACIC_VISUAL_CAPTCHA_VERIFY_SELECTOR = "#amzn-btn-verify-internal"
    AWS_WAF_CHALLENGE_SCRIPT_SELECTOR = 'script[src*="awswaf.com"]'

    SIGN_IN_FORM_SELECTOR = "form[name='signIn']"
    CLAIM_FORM_SELECTOR = "form[name='signIn'].auth-validate-form"
    INTENT_FORM_SELECTOR = "form#intent-confirmation-form"
    INTENT_MESSAGE_SELECTOR = "div#intent-confirmation-container"
    MFA_DEVICE_SELECT_FORM_SELECTOR = "form#auth-select-device-form"
    MFA_DEVICE_SELECT_INPUT_SELECTOR = "input[name='otpDeviceContext']"
    MFA_DEVICE_SELECT_INPUT_SELECTOR_VALUE = "value"
    MFA_FORM_SELECTOR = "form#auth-mfa-form"
    CAPTCHA_1_FORM_SELECTOR = "form.cvf-widget-form-captcha"
    CAPTCHA_2_FORM_SELECTOR = ["form:has(input[id^='captchacharacters'])", "form[action$='validateCaptcha']"]
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
    ORDER_HISTORY_COUNT_SELECTOR = ".js-yo-container span.num-orders"
    ORDER_DETAILS_ENTITY_SELECTOR = ["div#orderDetails",
                                     "div#ordersContainer",
                                     "div#odp-main-section"]
    # A history card renders an Item three ways, by how many the Shipment holds: ``.item-box`` on its
    # own, a static thumbnail grid of ``.yo-enhanced-flex-card``'s for a few, and a scrolling
    # ``.yo-enhanced-item-carousel`` of ``.yo-enhanced-card``'s for more. One Order mixes them freely,
    # a Shipment apiece.
    ITEM_ENTITY_SELECTOR = ["[data-component='purchasedItems'] .a-fixed-left-grid",
                            "div:has(> div.yohtmlc-item)",
                            ".item-box, .yo-enhanced-flex-card, .yo-enhanced-card",
                            # WFM in-store line items
                            "div.a-row.a-spacing-base:has(img.ufpo-itemListWidget-image)"]
    SHIPMENT_ENTITY_SELECTOR = ["[data-component='orderCard'] [data-component='shipments'] .a-box",
                                "div.shipment",
                                "div.delivery-box"]
    # Selectors defined here mean we don't have a reliable way to parse all details in an Order, so Items and
    # Shipments will be skipped
    ORDER_SKIP_ITEMS = [
        # Identifies an Amazon Fresh order (also matched by WFM in-store; distinguished via ORDER_WHOLE_FOODS)
        ".brand-info-box .brand-logo img",
        # Identifies a Whole Foods Market receipt order
        "a.yohtmlc-order-details-link[href^='/wholefoodsmarket']",
        # Identifies an order from a physical Amazon store
        Selector("div.yohtmlc-shipment-status-primaryText", "Purchased at Amazon")
    ]
    # Selectors identifying a Whole Foods Market purchase. Unlike ORDER_SKIP_ITEMS entries, WFM orders
    # expose a grand_total (and often item_count) on the history page, so those fields are populated.
    ORDER_WHOLE_FOODS = [
        "a[href*='/wholefoodsmarket/receipts/order/']",
        "a[href*='/fopo/order-details']",
        Selector("div.yohtmlc-shipment-status-primaryText", text_contains="Whole Foods Market"),
        "img.ufpo-itemListWidget-image"
    ]
    # Selectors defined here mean the Order will not have parsable totals
    ORDER_SKIP_TOTALS = [
        # Identifies a cancelled order on the history page
        Selector("div.yohtmlc-shipment-status-primaryText", "Cancelled"),
        # Identifies a cancelled order on the details page
        Selector("h4.a-alert-heading", text_contains="cancelled")
    ]

    #####################################
    # CSS selectors for Item fields
    #####################################

    # Last entry matches WFM in-store line items
    FIELD_ITEM_IMG_LINK_SELECTOR = ["a img",
                                    "img.ufpo-itemListWidget-image"]
    FIELD_ITEM_QUANTITY_SELECTOR = [".od-item-view-qty",
                                    "span.item-view-qty",
                                    "span.product-image__qty"]
    # WFM items render "Qty: N" or "Qty: 0.31 lb"; extracted in Item._parse_quantity
    FIELD_ITEM_WHOLE_FOODS_QUANTITY_SELECTOR = ["span.a-size-small"]
    FIELD_ITEM_TITLE_SELECTOR = ["[data-component='itemTitle']",
                                 ".yohtmlc-item a", ".yohtmlc-product-title",
                                 "div.a-column.a-span10 > a",
                                 # ASINLESS WFM items render the title in a span rather than a link
                                 "div.a-column.a-span10 > span",
                                 # Grid and carousel items on a history card
                                 ".yo-enhanced-title a"]
    FIELD_ITEM_LINK_SELECTOR = ["[data-component='itemTitle'] a",
                                ".yohtmlc-item a",
                                "a:has(> .yohtmlc-product-title)",
                                ".yohtmlc-product-title a",
                                "div.a-column.a-span10 > a",
                                # Grid and carousel items on a history card
                                ".yo-enhanced-title a"]
    FIELD_ITEM_TAG_ITERATOR_SELECTOR = [".yohtmlc-item div"]
    FIELD_ITEM_PRICE_SELECTOR = ["[data-component='unitPrice'] .a-text-price :not(.a-offscreen)",
                                 ".yohtmlc-item .a-color-price",
                                 "div.a-section.a-text-right span.a-size-small"]
    FIELD_ITEM_SELLER_SELECTOR = ["[data-component='orderedMerchant']"] + FIELD_ITEM_TAG_ITERATOR_SELECTOR
    FIELD_ITEM_RETURN_SELECTOR = (["[data-component='itemReturnEligibility']", ".yo-enhanced-return"]
                                  + FIELD_ITEM_TAG_ITERATOR_SELECTOR)

    #####################################
    # CSS selectors for Order fields
    #####################################

    FIELD_ORDER_DETAILS_LINK_SELECTOR = ["a.yohtmlc-order-details-link",
                                         # Would like to use this or similar, but not yet sure how consistent it is
                                         # ".order-header__header-link-list-item:first-of-type a"
                                         # WFM receipt and FOPO orders link to dedicated pages, not standard endpoint
                                         "a[href*='/wholefoodsmarket/receipts/order/']",
                                         "a[href*='/fopo/order-details']"]
    FIELD_ORDER_NUMBER_SELECTOR = ["[data-component='orderId']",
                                   "[data-component='briefOrderInfo'] div.a-column",
                                   ".order-date-invoice-item :is(bdi, span)[dir='ltr']",
                                   ".yohtmlc-order-id :is(bdi, span)[dir='ltr']",
                                   ":is(bdi, span)[dir='ltr']"]
    FIELD_ORDER_GRAND_TOTAL_SELECTOR = ["div.yohtmlc-order-total span.value",
                                        "div.order-header div.a-column.a-span2",
                                        "div.order-header div.a-col-left .a-span9",
                                        "#wfm-grand-total-amount"]
    # WFM in-store (FOPO) details page amounts
    FIELD_ORDER_WHOLE_FOODS_SUBTOTAL_SELECTOR = "#wfm-subtotal-amount"
    FIELD_ORDER_WHOLE_FOODS_TAX_SELECTOR = "#wfm-tax-total-amount"
    FIELD_ORDER_WHOLE_FOODS_PAYMENT_METHOD_SELECTOR = "#wfm-0-card-brand"
    FIELD_ORDER_WHOLE_FOODS_PAYMENT_LAST_4_SELECTOR = "#wfm-0-card-tail"
    FIELD_ORDER_PLACED_DATE_SELECTOR = ["[data-component='orderDate']",
                                        "span.order-date-invoice-item",
                                        "[data-component='briefOrderInfo'] div.a-column",
                                        "div:is(.a-span3, .a-span12)"]
    FIELD_ORDER_PAYMENT_METHOD_SELECTOR = "img.pmts-payment-credit-card-instrument-logo"
    FIELD_ORDER_PAYMENT_METHOD_LAST_4_SELECTOR = "span:has(img.pmts-payment-credit-card-instrument-logo):last-child"
    FIELD_ORDER_SUBTOTALS_TAG_ITERATOR_SELECTOR = ["[data-component='orderSubtotals'] div.a-row",
                                                   "div#od-subtotals div.a-row",
                                                   "[data-component='chargeSummary'] div.od-line-item-row"]
    FIELD_ORDER_SUBTOTALS_TAG_POPOVER_PRELOAD_SELECTOR = ".a-popover-preload"
    FIELD_ORDER_SUBTOTALS_INNER_TAG_SELECTOR = "div.a-span-last"
    FIELD_ORDER_ADDRESS_SELECTOR = ["div.displayAddressDiv", "[data-component='shippingAddress']"]
    FIELD_ORDER_ADDRESS_FALLBACK_1_SELECTOR = "div.recipient span.a-declarative"
    FIELD_ORDER_ADDRESS_FALLBACK_2_SELECTOR = "script[id^='shipToData']"
    FIELD_ORDER_GIFT_CARD_INSTANCE_SELECTOR = ".gift-card-instance"
    FIELD_ORDER_ITEM_COUNT_SELECTOR = ["div.a-fixed-left-grid-col.a-col-right span",
                                       "span"]

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
                                     "div:nth-child(1)",
                                     "li:nth-child(1)"]
    FIELD_RECIPIENT_ADDRESS1_SELECTOR = "li.displayAddressAddressLine1"
    FIELD_RECIPIENT_ADDRESS2_SELECTOR = "li.displayAddressAddressLine2"
    FIELD_RECIPIENT_ADDRESS_CITY_STATE_POSTAL_SELECTOR = "li.displayAddressCityStateOrRegionPostalCode"
    FIELD_RECIPIENT_ADDRESS_COUNTRY_SELECTOR = "li.displayAddressCountryName"
    FIELD_RECIPIENT_ADDRESS_FALLBACK_SELECTOR = ["div:nth-child(2)",
                                                 "li:nth-child(2)"]

    #####################################
    # CSS selectors for Seller fields
    #####################################

    FIELD_SELLER_NAME_SELECTOR = ["a", "span"]
    FIELD_SELLER_LINK_SELECTOR = "a"

    #####################################
    # CSS selectors for Transaction fields
    #####################################

    TRANSACTION_HISTORY_FORM_SELECTOR = "form:has(input[name='ppw-widgetState'])"
    TRANSACTION_HISTORY_CONTAINER_SELECTOR = ".pmts-portal-component"
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
