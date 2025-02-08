__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

from bs4 import BeautifulSoup

from amazonorders.entity.order import Order
from tests.unittestcase import UnitTestCase


class TestOrder(UnitTestCase):
    def test_order_currency_stripped(self):
        # GIVEN
        html = """
<div id="orderDetails">
<div class="a-section a-spacing-large a-spacing-top-small">
<ul class="a-unordered-list a-vertical breadcrumbs">
<li class="breadcrumbs__crumb"><span class="a-list-item">
<a class="a-link-normal" href="/gp/css/homepage.html/ref=ppx_od_dt_b_ya_link" title="Return to Your Account">
                Your Account
            </a>
</span></li>
<li class="breadcrumbs__crumb breadcrumbs__crumb--divider"><span class="a-list-item">›</span></li>
<li class="breadcrumbs__crumb"><span class="a-list-item">
<a class="a-link-normal" href="/gp/your-account/order-history/ref=ppx_od_dt_b_oh_link" title="Return to Your Orders">
                Your Orders
            </a>
</span></li>
<li class="breadcrumbs__crumb breadcrumbs__crumb--divider"><span class="a-list-item">›</span></li>
<li class="breadcrumbs__crumb breadcrumbs__crumb--current"><span class="a-list-item">
<span class="a-color-state">
                Order Details
            </span>
</span></li>
</ul>
</div>
<h1>Order Details</h1>
<div class="a-row a-spacing-base">
<div class="a-column a-span9 a-spacing-top-mini">
<div class="a-row a-spacing-none">
<span class="order-date-invoice-item">
                Ordered on December 7, 2023
                <i class="a-icon a-icon-text-separator" role="img"></i>
</span>
<span class="order-date-invoice-item">
                Order#
                <bdi dir="ltr">112-9685975-5907428</bdi>
</span>
</div>
</div>
<div class="a-column a-span3 a-text-right a-spacing-top-none hide-if-no-js a-span-last">
<div class="a-row a-spacing-none">
<span class="a-button a-button-base"><span class="a-button-inner"><a class="a-button-text"
href="/gp/css/summary/print.html/ref=ppx_od_dt_b_invoice?ie=UTF8&amp;orderID=112-9685975-5907428" role="button">
        View or Print invoice
    </a></span></span>
</div>
</div>
</div>
<div class="a-row a-spacing-base hide-if-js">
<div class="a-column a-span12 a-spacing-top-mini">
<ul class="a-unordered-list a-nostyle a-vertical">
<li><span class="a-list-item">
<a class="a-link-normal"
 href="/gp/css/summary/print.html/ref=ppx_od_dt_b_invoice?ie=UTF8&amp;orderID=112-9685975-5907428">
    View or Print invoice
</a>
</span></li>
</ul>
</div>
</div>
<div class="a-box-group a-spacing-base">
<div class="a-box a-first"><div class="a-box-inner">
<div class="a-fixed-right-grid"><div class="a-fixed-right-grid-inner" style="padding-right:260px">
<div class="a-fixed-right-grid-col a-col-left" style="padding-right:0%;float:left;">
<div class="a-row">
<div class="a-column a-span5">
<div class="a-section a-spacing-none od-shipping-address-container">
<h5 class="a-spacing-micro">
        Shipping Address
    </h5>
<div class="a-row a-spacing-micro">
<div class="displayAddressDiv">
<ul class="displayAddressUL">
<li class="displayAddressLI displayAddressFullName">Alex Laird</li>
<li class="displayAddressLI displayAddressAddressLine1">555 My Road</li>
<li class="displayAddressLI displayAddressCityStateOrRegionPostalCode">Chicago, IL 60007</li>
<li class="displayAddressLI displayAddressCountryName">United States</li>
</ul>
</div>
</div>
</div>
                    </div>
<div class="a-column a-span7 a-span-last">
<div class="a-section a-spacing-base">
</div>
</div>
</div>
</div>
<div class="a-fixed-right-grid-col a-col-right" id="od-subtotals" style="width:260px;margin-right:-260px;float:left;">
<h5 class="a-spacing-micro a-text-left">
    Order Summary
</h5>
<div class="a-row">
<div class="a-column a-span7 a-text-left">
<span class="a-color-base">
            Item(s) Subtotal:
        </span>
</div>
<div class="a-column a-span5 a-text-right a-span-last">
<span class="a-color-base">
        $1,111.99
    </span>
</div>
</div>
<div class="a-row">
<div class="a-column a-span7 a-text-left">
<span class="a-color-base">
            Shipping &amp; Handling:
        </span>
</div>
<div class="a-column a-span5 a-text-right a-span-last">
<span class="a-color-base">
        $2,222.99
    </span>
</div>
</div>
<div class="a-row a-spacing-mini">
</div>
<div class="a-row">
<div class="a-column a-span7 a-text-left">
<span class="a-color-base">
            Total before tax:
        </span>
</div>
<div class="a-column a-span5 a-text-right a-span-last">
<span class="a-color-base">
        $3,333.99
    </span>
</div>
</div>
<div class="a-row">
<div class="a-column a-span7 a-text-left">
<span class="a-color-base">
            Estimated tax to be collected:
        </span>
</div>
<div class="a-column a-span5 a-text-right a-span-last">
<span class="a-color-base">
        $4,444.99
    </span>
</div>
</div>
<div class="a-row a-spacing-mini">
</div>
<div class="a-row">
<div class="a-column a-span7 a-text-left">
<span class="a-color-base a-text-bold">
            Grand Total:
        </span>
</div>
<div class="a-column a-span5 a-text-right a-span-last">
<span class="a-color-base a-text-bold">
        $7,777.99
    </span>
</div>
</div>
</div>
</div></div>
</div></div>
<div class="a-box a-last"><div class="a-box-inner">
<div aria-live="polite" class="a-row a-expander-container a-expander-inline-container show-if-no-js">
<a class="a-expander-header a-declarative a-expander-inline-header a-link-expander"
data-a-expander-toggle='{"allowLinkDefault":true, "expand_prompt":"", "collapse_prompt":""}'
data-action="a-expander-toggle" href="javascript:void(0)"><i class="a-icon a-icon-expand"></i>
<span class="a-expander-prompt">
        Transactions
    </span></a>
<div aria-expanded="false" class="a-expander-content a-expander-inline-content a-expander-inner" style="display:none">
<div class="a-row">
<span class="a-color-secondary">
        Items shipped:
    </span>
<span>
        December 7, 2023
        -
        AmericanExpress ending in 1234:
        $1,222.99
    </span>
</div>
<br/>
        Total:
        $1,234.99
    </div>
</div>
</div></div>
</div>
<div class="a-box-group od-shipments">
<div class="a-box a-first a-box-title"><div class="a-box-inner">
<h4>
        1 Shipment
    </h4>
</div></div>
<div class="a-box shipment shipment-is-delivered"><div class="a-box-inner">
<div class="a-row shipment-top-row js-shipment-info-container">
<div style="margin-right:220px; padding-right:20px">
<div class="a-row">
<span class="a-size-medium a-color-base a-text-bold">
    Delivered Dec 9, 2023
</span>
</div>
<div class="a-row">
<div class="a-row">
                Your package was left near the front door or porch.
            </div>
<span class="js-shipment-info aok-hidden" data-isstatuswithwarning="0" data-yodeliveryestimate="Delivered Dec 9, 2023"
data-yoshortstatuscode="DELIVERED" data-yostatusstring="">
</span>
</div>
</div>
<div class="actions" style="width:220px;">
<div class="a-row">
<div class="a-button-stack">
<span class="a-declarative" data-action="set-shipment-info-cookies" data-set-shipment-info-cookies="{}">
</div>
</div>
</div>
</div>
<div class="a-fixed-right-grid a-spacing-top-medium"><div class="a-fixed-right-grid-inner a-grid-vertical-align
 a-grid-top">
<div class="a-fixed-right-grid-col a-col-left" style="padding-right:3.2%;float:left;">
<div class="a-row">
<div class="a-fixed-left-grid a-spacing-none"><div class="a-fixed-left-grid-inner" style="padding-left:100px">
<div class="a-text-center a-fixed-left-grid-col a-col-left" style="width:100px;margin-left:-100px;float:left;">
<div class="item-view-left-col-inner">
<a class="a-link-normal" href="/gp/product/B0CLJ9KGRV/ref=ppx_od_dt_b_asin_image_s00?ie=UTF8&amp;psc=1">
<img alt="" aria-hidden="true" class="yo-critical-feature"
data-a-hires="https://m.media-amazon.com/images/I/41ZiqpN4uvL._SY180_.jpg" height="90"
onload="if (typeof uet == 'function') { uet('cf'); uet('af'); } if (typeof event === 'object' &amp;&amp; event.target)
{
              var el = event.target;
              if (('' + el.tagName).toLowerCase() == 'img' &amp;&amp; !el.getAttribute('data-already-flushed-csm')) {
                  el.setAttribute('data-already-flushed-csm', 'true');
                  if (typeof ue == 'object' &amp;&amp; ue.isl &amp;&amp; typeof uet == 'function' &amp;&amp;
                  typeof uex == 'function') {
                      var scope = 'imgonload-' + (+new Date) + '-';
                      uet('ld', scope + 'cf', {}, ue.t0);
                      uet('cf', scope + 'cf', {}, ue.t0);
                      uet('af', scope + 'cf', {}, ue.t0);
                      uex('at', scope + 'cf');
                      uex('ld', scope + 'ld');
                  }
              }
          }" src="https://m.media-amazon.com/images/I/41ZiqpN4uvL._SY90_.jpg" title="Cadeya Egg Cleaning Brush
          Silicone, Egg Scrubber for Fresh Eggs, Reusable Cleaning Tools for Egg Washer (Pink)" width="90"/>
</a>
</div>
</div>
<div class="a-fixed-left-grid-col yohtmlc-item a-col-right" style="padding-left:1.5%;float:left;">
<div class="a-row">
<a class="a-link-normal" href="/gp/product/B07YQDD94M/ref=ppx_od_dt_b_asin_title_s01?ie=UTF8&amp;psc=1">
        Swiffer WetJet Hardwood and Floor Spray Mop Cleaner Starter Kit, Includes: 1 Power Mop, 10 Pads, Cleaning
        Solution, Batteries
    </a>
</div>
<div class="a-row">
<span class="a-size-small a-color-secondary">

    Sold by:

        Amazon.com Services, Inc



</span>
</div>
<div class="a-row">
<span class="a-size-small">
<div class="a-row a-size-small">Return eligible through Jan 31, 2024</div>
</span>
</div>
<div class="a-row">
<span class="a-size-small a-color-price">
    $9,999.11
</span>
</div>
<div class="a-row">
<span class="a-color-secondary a-text-bold">
        Condition:
    </span>
<span class="a-color-secondary">
        New
    </span>
</div>
<div class="a-row">
<span class="a-declarative" data-action="bia_button" data-bia_button="{}">
<span class="a-button a-spacing-mini a-button-primary yohtmlc-buy-it-again"><span class="a-button-inner">
<a aria-label="Buy it again" class="a-button-text"
href="/gp/buyagain/ref=ppx_od_dt_b_bia?ie=UTF8&amp;ats=eyJZXMiOiJCMDdZ%0AUUREOTRNIn0%3D%0A" role="button">
<div class="reorder-modal-trigger-text">
<i class="reorder-modal-trigger-icon"></i>
                Buy it again
            </div>
</a></span></span>
</span>
</div>
</div>
</div></div>
</div>
</div>
<div class="a-fixed-right-grid-col a-col-right" style="width:220px;margin-right:-220px;float:left;">
<div class="a-row">
<div class="a-button-stack yohtmlc-shipment-level-connections">
</div>
</div>
</div>
</div></div>
</div></div>
</div>
<script type="text/javascript">
    if (ue) {
        uet('fn');
    }
</script>
<script type="text/javascript">
    if (ue) {
        uet('af');
    }
</script>
<div class="a-section a-spacing-large a-spacing-top-large">
</link></div>
</div>
"""
        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.subtotal, 1111.99)
        self.assertEqual(order.shipping_total, 2222.99)
        self.assertEqual(order.total_before_tax, 3333.99)
        self.assertEqual(order.estimated_tax, 4444.99)
        # self.assertEqual(order.refund_total, 5555.99)
        # self.assertEqual(order.subscription_discount, 6666.99)
        self.assertEqual(order.grand_total, 7777.99)

    def test_order_promotion_applied(self):
        # GIVEN
        html = """
<div id="orderDetails" class="a-section dynamic-width">
<div class="a-cardui-deck" data-a-remove-top-gutter=""
data-a-remove-bottom-gutter="">
<div class="a-teaser-describedby-collapsed a-hidden">Brief content
visible, double tap to read full content.</div>
<div class="a-teaser-describedby-expanded a-hidden">Full content
visible, double tap to read brief content.</div>
<div class="a-cardui" data-a-card-type="basic">
<div class="a-cardui-body">
<div class="" data-component="default">
<div class="" data-component="debugBanner"></div>
<div class="" data-component="aapiDebug"></div>
<div class="" data-component="ddtDebug"></div>
<div class="" data-component="breadcrumb">
<div class="a-section a-spacing-base">
<ul class="a-unordered-list a-horizontal od-breadcrumbs">
<li class="od-breadcrumbs__crumb"><span class=
"a-list-item"><a class="a-link-normal" title=
"Return to Your Account" href=
"/gp/css/homepage.html/ref=ppx_hzod_bc_dt_b_ya_link">Your
Account</a></span></li>
<li class="od-breadcrumbs__crumb od-breadcrumbs__crumb--divider">
<span class="a-list-item">›</span></li>
<li class="od-breadcrumbs__crumb"><span class=
"a-list-item"><a class="a-link-normal" title=
"Return to Your Orders" href=
"/gp/your-account/order-history/ref=ppx_hzod_bc_dt_b_oh_link">Your
Orders</a></span></li>
<li class="od-breadcrumbs__crumb od-breadcrumbs__crumb--divider">
<span class="a-list-item">›</span></li>
<li class="od-breadcrumbs__crumb od-breadcrumbs__crumb--current">
<span class="a-list-item"><span class="a-color-state">Order
Details</span></span></li>
</ul>
</div>
</div>
<div class="" data-component="teensBanner"></div>
<div class="" data-component="banner"></div>
<div class="" data-component="alerts"></div>
<div class="" data-component="returnsBanner"></div>
<div class="" data-component="archivedMessage"></div>
<div class="" data-component="title">
<div class="a-section">
<div class="a-row">
<div class="" data-component="titleLeftGrid">
<div class="a-column a-span6">
<div class="" data-component="orderDetailsTitle">
<h1>Order Details</h1>
</div>
</div>
</div>
<div class="" data-component="titleRightGrid">
<div class="a-column a-span6 a-text-right a-span-last">
<div class="" data-component="brandLogo"></div>
</div>
</div>
</div>
</div>
</div>
<div class="" data-component="orderDateInvoice">
<div class="a-row a-spacing-base">
<div class="a-column a-span9 a-spacing-top-mini">
<div class="a-row a-spacing-none"><span class=
"order-date-invoice-item">Ordered on January 30, 2025</span>
<span class="order-date-invoice-item">Order# <bdi dir=
"ltr">111-9450008-0781820</bdi></span></div>
</div>
<div class=
"a-column a-span3 a-text-right a-spacing-top-none hide-if-no-js a-span-last">
<div class="a-row a-spacing-none"><span class=
"a-button a-button-base"><span class="a-button-inner"><a href=
"/gp/css/summary/print.html/ref=ppx_od_dt_b_invoice?ie=UTF8&amp;orderID=111-9450008-0781820"
class="a-button-text" role="button">View or Print
invoice</a></span></span></div>
</div>
</div>
<div class="a-row a-spacing-base hide-if-js">
<div class="a-column a-span12 a-spacing-top-mini">
<ul class="a-unordered-list a-nostyle a-vertical">
<li><span class="a-list-item"><a class="a-link-normal" href=
"/gp/css/summary/print.html/ref=ppx_od_dt_b_invoice?ie=UTF8&amp;orderID=111-9450008-0781820">
View or Print invoice</a></span></li>
</ul>
</div>
</div>
</div>
<div class="" data-component="briefOrderInfoInvoice"></div>
<div class="" data-component="mfaMessage"></div>
<div class="" data-component="orderSummary">
<div class="a-box-group a-spacing-base">
<div class="a-box">
<div class="a-box-inner">
<div class="a-fixed-right-grid">
<div class="a-fixed-right-grid-inner" style="padding-right:260px">
<div class="a-fixed-right-grid-col a-col-left" style=
"padding-right:0%;float:left;">
<div class="a-row">
<div class="a-column a-span5">
<div class="" data-component="rawShippingAddress">
<div class=
"a-section a-spacing-none od-shipping-address-container">
<h5 class="a-spacing-micro">Shipping Address</h5>
<div class="a-row a-spacing-micro">
<div class="displayAddressDiv">
<ul class="displayAddressUL">
<li class="displayAddressLI displayAddressFullName">John Doe</li>
<li class="displayAddressLI displayAddressAddressLine1">555 My Place</li>
<li class=
"displayAddressLI displayAddressCityStateOrRegionPostalCode">
BELMONT, MI 49306-9452</li>
<li class="displayAddressLI displayAddressCountryName">United
States</li>
</ul>
</div>
</div>
</div>
</div>
</div>
<div class="a-column a-span7 a-span-last">
<div class="a-section a-spacing-base">
<div class="" data-component="paymentMethod">
<div data-pmts-component-id="pp-KrIo0s-1" class=
"a-row pmts-portal-root-JeXB2VJCsunF pmts-portal-component pmts-portal-components-pp-KrIo0s-1">
<div class=
"a-column a-span12 pmts-payment-instrument-billing-address">
<div data-pmts-component-id="pp-KrIo0s-2" class=
"a-row a-spacing-small pmts-portal-component pmts-portal-components-pp-KrIo0s-2">
<div class="a-row pmts-payments-instrument-header">
<h5>Payment method</h5>
</div>
<div class="a-row pmts-payments-instrument-details">
<ul class=
"a-unordered-list a-nostyle a-vertical no-bullet-list pmts-payments-instrument-list">
<li class=
"a-spacing-micro pmts-payments-instrument-detail-box-paystationpaymentmethod">
<span class="a-list-item"><img alt="Visa" src=
"https://m.media-amazon.com/images/G/01/payments-portal/r1/issuer-images/visa._CB604017185_.gif"
class="pmts-payment-credit-card-instrument-logo" height="23px"
width="34px">Visa<span class="a-color-base">ending in
9621</span></span></li>
</ul>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
<div id="od-subtotals" class="a-fixed-right-grid-col a-col-right"
style="width:260px;margin-right:-260px;float:left;">
<div class="" data-component="orderSubtotals">
<h5 class="a-spacing-micro a-text-left">Order Summary</h5>
<div class="a-row">
<div class="a-column a-span7 a-text-left"><span class=
"a-color-base">Item(s) Subtotal:</span></div>
<div class="a-column a-span5 a-text-right a-span-last"><span class=
"a-color-base">$4.68</span></div>
</div>
<div class="a-row">
<div class="a-column a-span7 a-text-left"><span class=
"a-color-base">Shipping & Handling:</span></div>
<div class="a-column a-span5 a-text-right a-span-last"><span class=
"a-color-base">$2.99</span></div>
</div>
<div class="a-row">
<div class="a-column a-span7 a-text-left"><span class=
"a-color-base">Promotion Applied:</span></div>
<div class="a-column a-span5 a-text-right a-span-last"><span class=
"a-color-base">-$0.05</span></div>
</div>
<div class="a-row a-spacing-mini"></div>
<div class="a-row">
<div class="a-column a-span7 a-text-left"><span class=
"a-color-base">Total before tax:</span></div>
<div class="a-column a-span5 a-text-right a-span-last"><span class=
"a-color-base">$7.62</span></div>
</div>
<div class="a-row">
<div class="a-column a-span7 a-text-left"><span class=
"a-color-base">Estimated tax to be collected:</span></div>
<div class="a-column a-span5 a-text-right a-span-last"><span class=
"a-color-base">$0.28</span></div>
</div>
<div class="a-row a-spacing-mini"></div>
<div class="a-row">
<div class="a-column a-span7 a-text-left"><span class=
"a-color-base a-text-bold">Grand Total:</span></div>
<div class="a-column a-span5 a-text-right a-span-last"><span class=
"a-color-base a-text-bold">$7.90</span></div>
</div>
</div>
<div class="" data-component="chargeSummary"></div>
<div class="" data-component="primeWardrobeChargeMessage"></div>
</div>
</div>
</div>
<div class="" data-component="financialOfferBonus"></div>
<div class="" data-component="wirelessDeposits"></div>
</div>
</div>
</div>
</div>
<div class="" data-component="orderCard">
<div class="" data-component="shipments">
<div class="a-box-group">
<div class="a-box">
<div class="a-box-inner">
<div class="a-fixed-right-grid">
<div class="a-fixed-right-grid-inner" style="padding-right:220px">
<div class="" data-component="shipmentsLeftGrid">
<div class="a-fixed-right-grid-col a-col-left" style=
"padding-right:3.2%;float:left;">
<div class="" data-component="shipmentStatus">
<div id="shipment-top-row" class="a-row">
<div class="a-section">
<div class="a-row">
<h4 class="a-color-base od-status-message"><span class=
"a-text-bold">Delivered</span> <span class=
"a-text-bold a-nowrap">January 30</span></h4>
</div>
<div class="a-row"><span>Your package was left near the front door
or porch.</span></div>
<div class="a-row"></div>
</div>
</div>
</div>
<div class="" data-component="purchasedItems">
<div class="a-row a-spacing-top-base">
<div class="a-fixed-left-grid">
<div class="a-fixed-left-grid-inner" style="padding-left:100px">
<div class="" data-component="purchasedItemsLeftGrid">
<div class="a-fixed-left-grid-col a-col-left" style=
"width:100px;margin-left:-100px;float:left;">
<div class="" data-component="itemImage">
<div style="position: relative"><a class="a-link-normal" href=
"/dp/B000R4OGZE?ref_=ppx_hzod_image_dt_b_fed_asin_title_0_0"><img alt="foo"
src="https://m.media-amazon.com/images/I/71jC4dTp2QS._SS284_.jpg"
height="90" width="90" data-a-hires=
"https://m.media-amazon.com/images/I/71jC4dTp2QS._SS568_.jpg"></a></div>
</div>
</div>
</div>
<div class="" data-component="purchasedItemsRightGrid">
<div class="a-fixed-left-grid-col a-col-right" style=
"padding-left:1.5%;float:left;">
<div class="" data-component="itemTitle">
<div class="a-row"><a class="a-link-normal" href=
"/dp/B000R4OGZE?ref_=ppx_hzod_title_dt_b_fed_asin_title_0_0">Plastic
Treasure Map Party Accessory (1 count) (1/Pkg)</a></div>
</div>
<div class="" data-component="orderedMerchant"><span class=
"a-size-small a-color-secondary">Sold by: <a class="a-link-normal"
href="/gp/aag/main?ie=UTF8&amp;seller=A1TWYVWG4QDVKK">Hour
Loop</a></span></div>
<div class="" data-component="itemReturnEligibility">
<div class="a-row"><span class="a-size-small">Return or replace
items: Eligible through March 1, 2025</span></div>
</div>
<div class="" data-component="serviceAppointmentStatus"></div>
<div class="" data-component="unitPrice"><span class=
"a-price a-text-price" data-a-size="s" data-a-color=
"base"><span class="a-offscreen">$4.68</span><span aria-hidden=
"true">$4.68</span></span></div>
<div class="" data-component="deliveryFrequency"></div>
<div class="" data-component="customizedItemDetails">
<div class="a-row"></div>
</div>
<div class="" data-component="purchasedVariationDetails"></div>
<div class="" data-component="giftcardsSender"></div>
<div class="" data-component="itemConnections">
<div class="a-row a-spacing-top-mini"><span class=
"a-button a-button-normal a-spacing-mini a-button-primary"><span class="a-button-inner">
<a href=
"/gp/buyagain?ats=eyJjdXN0b21lcklkIjoiQTNIN0Q5VFpSUTRXViIsImV4cGxpY2l0Q2FuZGlkYXRlcyI6IkIwMDBSNE9HWkUifQ%3D%3D&amp;ref_=ppx_hzod_itemconns_dt_b_bia_item_0_0"
class="a-button-text">
<div class='od-buy-it-again-button__icon'></div>
<div class='od-buy-it-again-button__text'><span class=
"a-button a-button-normal a-spacing-mini a-button-primary">Buy it
again</span></div>
</a></span></span> <span class=
"a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner">
<a href=
"/your-orders/pop?orderId=111-9450008-0781820&amp;shipmentId=BB4lRDKg2&amp;lineItemId=jijmrpjnnkptsups&amp;packageId=1&amp;asin=B000R4OGZE&amp;ref_=ppx_hzod_itemconns_dt_b_pop_0_0"
class="a-button-text">View your item</a></span></span></div>
</div>
<div class="" data-component="giftCardDetails"></div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
<div class="" data-component="shipmentsRightGrid">
<div class="a-fixed-right-grid-col a-col-right" style=
"width:220px;margin-right:-220px;float:left;">
<div class="" data-component="shipmentConnections">
<div class="a-button-stack a-spacing-mini"><span class=
"a-button a-button-normal a-spacing-mini a-button-primary"><span class="a-button-inner">
<a href=
"/ps/product-support/order?orderId=111-9450008-0781820&amp;ref_=ppx_hzod_shipconns_dt_b_prod_support_0"
class="a-button-text">Get product support</a></span></span>
<span class=
"a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner">
<a href=
"/gp/your-account/ship-track?itemId=jijmrpjnnkptsup&amp;orderId=111-9450008-0781820&amp;shipmentId=BB4lRDKg2&amp;packageIndex=0&amp;ref_=ppx_hzod_shipconns_dt_b_track_package_0"
class="a-button-text">Track package</a></span></span> <span class=
"a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner">
<a href=
"/spr/returns/cart?orderId=111-9450008-0781820&amp;ref_=ppx_hzod_shipconns_dt_b_return_replace_0"
class="a-button-text">Return or replace items</a></span></span>
<span class=
"a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner">
<a href=
"/gcx/-/ty/gr/111-9450008-0781820/shipment?ref_=ppx_hzod_shipconns_dt_b_gift_receipt_0"
class="a-button-text">Share gift receipt</a></span></span>
<span class=
"a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner">
<a href=
"/gp/help/contact/contact.html?assistanceType=order&amp;subject=2&amp;step=submitEntry&amp;marketplaceId=ATVPDKIKX0DER&amp;orderId=111-9450008-0781820&amp;recipientId=A1TWYVWG4QDVKK&amp;ref_=ppx_hzod_shipconns_dt_b_prod_question_0"
class="a-button-text">Ask Product Question</a></span></span>
<span class=
"a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner">
<a href=
"/hz/feedback?sellerID=A1TWYVWG4QDVKK&amp;orderID=111-9450008-0781820&amp;ref_=ppx_hzod_shipconns_dt_b_seller_feedback_0"
class="a-button-text">Leave seller feedback</a></span></span>
<span class=
"a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner">
<a href=
"/review/review-your-purchases?asins=B000R4OGZE&amp;channel=YAcc-wr&amp;ref_=ppx_hzod_shipconns_dt_b_rev_prod_0"
class="a-button-text">Write a product
review</a></span></span></div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
<div class="" data-component="shipments"></div>
<div class="" data-component="deliveries"></div>
<div class="" data-component="returns"></div>
</div>
<div class="" data-component="cancelled"></div>
</div>
</div>

<!--&&&Portal&Delimiter&&&-->
<!-- sp:end-feature:host-atf -->
<!-- sp:feature:nav-btf -->
<!-- NAVYAAN BTF START -->

<!-- NAVYAAN BTF END -->
<!-- sp:end-feature:nav-btf -->
<!-- sp:feature:host-btf -->
<div class="" data-component="personalization">
<div class="a-cardui" data-a-card-type="basic">
<div class="a-cardui-body">
<div class="a-section">
<div id=
'desktop-yo-orderdetails_ALL_desktop-yo-orderdetails_0_container'>

<div class='widget-html-container'>
<div style='height: 350px;'></div>
</div>
</div>
<link rel="stylesheet" href=
"https://images-na.ssl-images-amazon.com/images/I/01FvA6+tfcL.css?AUIClients/DramAssets">
</div>
</div>
</div>
</div>
</div>
</div>
</div>
<!-- sp:end-feature:host-btf -->
<!-- sp:feature:aui-preload -->
<!-- sp:end-feature:aui-preload -->
<!-- sp:feature:nav-footer -->
<!-- NAVYAAN FOOTER START -->
<!-- WITH MOZART -->
<div id='rhf' class='copilot-secure-display' style='clear: both;'
role='complementary' aria-label=
'Your recently viewed items and featured recommendations'>
<div class='rhf-frame' style='display: none;'><br>
<div id='rhf-container'>
<div class='rhf-loading-outer'>
<table class='rhf-loading-middle'>
<tr>
<td class='rhf-loading-inner'><img src=
'https://m.media-amazon.com/images/G/01/personalization/ybh/loading-4x-gray._CB485916920_.gif'></td>
</tr>
</table>
</div>
<div id='rhf-context'>
</div>
</div>
<noscript>
<div class='rhf-border'>
<div class='rhf-header'>Your recently viewed items and featured
recommendations</div>
<div class='rhf-footer'>
<div class='rvi-container'>
<div class='ybh-edit'>
<div class='ybh-edit-arrow'>›</div>
<div class='ybh-edit-link'><a href='/gp/history'>View or edit your
browsing history</a></div>
</div>
<span class='no-rvi-message'>After viewing product detail pages,
look here to find an easy way to navigate back to pages you are
interested in.</span></div>
</div>
</div>
</noscript>
<div id='rhf-error' style='display: none;'>
<div class='rhf-border'>
<div class='rhf-header'>Your recently viewed items and featured
recommendations</div>
<div class='rhf-footer'>
<div class='rvi-container'>
<div class='ybh-edit'>
<div class='ybh-edit-arrow'>›</div>
<div class='ybh-edit-link'><a href='/gp/history'>View or edit your
browsing history</a></div>
</div>
<span class='no-rvi-message'>After viewing product detail pages,
look here to find an easy way to navigate back to pages you are
interested in.</span></div>
</div>
</div>
</div>
<br></div>
</div>
<div class="navLeftFooter nav-sprite-v1" id="navFooter"><a href=
"javascript:void(0)" id="navBackToTop" aria-label="Back to top">
<div class="navFooterBackToTop"><span class=
"navFooterBackToTopText">Back to top</span></div>
</a>
<div class="navFooterVerticalColumn navAccessibility" role=
"presentation">
<div class="navFooterVerticalRow navAccessibility" style=
"display: table-row;">
<div class="navFooterLinkCol navAccessibility">
<div class="navFooterColHead" role="heading" aria-level="6">Get to
Know Us</div>
<ul>
<li class="nav_first"><a href="https://www.amazon.jobs" class=
"nav_a">Careers</a></li>
<li><a href=
"https://email.aboutamazon.com/l/637851/2020-10-29/pd87g?utm_source=gateway&amp;utm_medium=amazonfooters&amp;utm_campaign=newslettersubscribers&amp;utm_content=amazonnewssignup"
class="nav_a">Amazon Newsletter</a></li>
<li><a href=
"https://www.aboutamazon.com/?utm_source=gateway&amp;utm_medium=footer&amp;token=about"
class="nav_a">About Amazon</a></li>
<li><a href="https://www.amazon.com/b?node=15701038011&amp;ie=UTF8"
class="nav_a">Accessibility</a></li>
<li><a href=
"https://sustainability.aboutamazon.com/?utm_source=gateway&amp;utm_medium=footer&amp;ref_=susty_footer"
class="nav_a">Sustainability</a></li>
<li><a href="https://www.amazon.com/pr" class="nav_a">Press
Center</a></li>
<li><a href="https://www.amazon.com/ir" class="nav_a">Investor
Relations</a></li>
<li><a href=
"/gp/browse.html?node=2102313011&amp;ref_=footer_devices" class=
"nav_a">Amazon Devices</a></li>
<li class="nav_last"><a href="https://www.amazon.science" class=
"nav_a">Amazon Science</a></li>
</ul>
</div>
<div class="navFooterColSpacerInner navAccessibility"></div>
<div class="navFooterLinkCol navAccessibility">
<div class="navFooterColHead" role="heading" aria-level="6">Make
Money with Us</div>
<ul>
<li class="nav_first"><a href=
"https://sell.amazon.com/?ld=AZFSSOA_FTSELL-C&amp;ref_=footer_soa"
class="nav_a">Sell on Amazon</a></li>
<li><a href="https://developer.amazon.com" class="nav_a">Sell apps
on Amazon</a></li>
<li><a href="https://supply.amazon.com" class="nav_a">Supply to
Amazon</a></li>
<li><a href=
"https://sell.amazon.com/brand-registry?ld=AZUSSOA_ABR-FT" class=
"nav_a">Protect & Build Your Brand</a></li>
<li><a href="https://affiliate-program.amazon.com/" class=
"nav_a">Become an Affiliate</a></li>
<li><a href=
"https://www.fountain.com/jobs/amazon-delivery-service-partner?utm_source=amazon.com&amp;utm_medium=footer"
class="nav_a">Become a Delivery Driver</a></li>
<li><a href=
"https://logistics.amazon.com/marketing?utm_source=amzn&amp;utm_medium=footer&amp;utm_campaign=home"
class="nav_a">Start a Package Delivery Business</a></li>
<li><a href="https://advertising.amazon.com/?ref=ext_amzn_ftr"
class="nav_a">Advertise Your Products</a></li>
<li><a href=
"/gp/seller-account/mm-summary-page.html?ld=AZFooterSelfPublish&amp;topic=200260520&amp;ref_=footer_publishing"
class="nav_a">Self-Publish with Us</a></li>
<li><a href="https://www.amazon.com/b/?node=120788043011" class=
"nav_a">Become an Amazon Hub Partner</a></li>
<li class="nav_last nav_a_carat"><span class="nav_a_carat"
aria-hidden="true">›</span><a href=
"/b/?node=18190131011&amp;ld=AZUSSOA-seemore&amp;ref_=footer_seemore"
class="nav_a">See More Ways to Make Money</a></li>
</ul>
</div>
<div class="navFooterColSpacerInner navAccessibility"></div>
<div class="navFooterLinkCol navAccessibility">
<div class="navFooterColHead" role="heading" aria-level="6">Amazon
Payment Products</div>
<ul>
<li class="nav_first"><a href=
"/iss/credit/rewardscardmember?plattr=CBFOOT&amp;ref_=footer_cbcc"
class="nav_a">Amazon Visa</a></li>
<li><a href=
"/credit/storecard/member?plattr=PLCCFOOT&amp;ref_=footer_plcc"
class="nav_a">Amazon Store Card</a></li>
<li><a href=
"/gp/product/B084KP3NG6?plattr=SCFOOT&amp;ref_=footer_ACB" class=
"nav_a">Amazon Secured Card</a></li>
<li><a href="/dp/B07984JN3L?plattr=ACOMFO&amp;ie=UTF-8" class=
"nav_a">Amazon Business Card</a></li>
<li><a href="https://www.amazon.com/hp/shopwithpoints/servicing"
class="nav_a">Shop with Points</a></li>
<li><a href="/gp/browse.html?node=3561432011&amp;ref_=footer_ccmp"
class="nav_a">Credit Card Marketplace</a></li>
<li><a href=
"/gp/browse.html?node=10232440011&amp;ref_=footer_reload_us" class=
"nav_a">Reload Your Balance</a></li>
<li><a href=
"https://www.amazon.com/b/?node=2238192011&amp;ref=shop_footer_payments_gc_desktop"
class="nav_a">Gift Cards</a></li>
<li><a href="/gp/browse.html?node=388305011&amp;ref_=footer_tfx"
class="nav_a">Amazon Currency Converter</a></li>
<li class="nav_last"><a href=
"/gp/browse.html?node=20533023011&amp;ref_=footer_afd_fin" class=
"nav_a">Promotional Financing</a></li>
</ul>
</div>
<div class="navFooterColSpacerInner navAccessibility"></div>
<div class="navFooterLinkCol navAccessibility">
<div class="navFooterColHead" role="heading" aria-level="6">Let Us
Help You</div>
<ul>
<li class="nav_first"><a href=
"https://www.amazon.com/gp/css/homepage.html?ref_=footer_ya" class=
"nav_a">Your Account</a></li>
<li><a href=
"https://www.amazon.com/gp/css/order-history?ref_=footer_yo" class=
"nav_a">Your Orders</a></li>
<li><a href=
"/gp/help/customer/display.html?nodeId=468520&amp;ref_=footer_shiprates"
class="nav_a">Shipping Rates & Policies</a></li>
<li><a href="/gp/prime?ref_=footer_prime" class="nav_a">Amazon
Prime</a></li>
<li><a href="/gp/css/returns/homepage.html?ref_=footer_hy_f_4"
class="nav_a">Returns & Replacements</a></li>
<li><a href="/hz/mycd/myx?ref_=footer_myk" class="nav_a">Manage
Your Content and Devices</a></li>
<li><a href=
"https://www.amazon.com/product-safety-alerts?ref_=footer_bsx_ypsa"
class="nav_a">Recalls and Product Safety Alerts</a></li>
<li><a href="/registries?ref_=nav_footer_registry_giftlist_desktop"
class="nav_a">Registry & Gift List</a></li>
<li class="nav_last"><a href=
"/gp/help/customer/display.html?nodeId=508510&amp;ref_=footer_gw_m_b_he"
class="nav_a">Help</a></li>
</ul>
</div>
</div>
</div>
<div class="nav-footer-line"></div>
<div class="navFooterLine navFooterLinkLine navFooterPadItemLine">
<div class="navFooterLine navFooterLogoLine"><span><a aria-label=
"Amazon US Home" href="/?ref_=footer_logo">
<div class="nav-logo-base nav-sprite"></div>
</a></span></div>
<div class="navFooterLine"><span class=
"icp-container-desktop"><a href=
"/customer-preferences/edit?ie=UTF8&amp;preferencesReturnUrl=%2F&amp;ref_=footer_lang"
role="button" aria-haspopup="true" aria-label=
"Choose a language for shopping. Current selection is English."
aria-owns="nav-flyout-icp-footer-flyout" class="icp-button" id=
"icp-touch-link-language">
<div class="icp-nav-globe-img-2 icp-button-globe-2"></div>
<span class="icp-color-base">English</span></a></span><a href=
"/customer-preferences/country?ie=UTF8&amp;preferencesReturnUrl=%2F&amp;ref_=footer_icp_cp"
role="button" aria-label=
"Choose a country/region for shopping. The current selection is United States."
class="icp-button" id="icp-touch-link-country"><span class=
"icp-color-base">United States</span></a></div>
</div>
<div class="navFooterLine navFooterLinkLine navFooterDescLine"
role="navigation" aria-label="More on Amazon">
<div class="navFooterMoreOnAmazon navFooterMoreOnAmazonWrapper"
aria-label="More on Amazon">
<ul>
<li class="navFooterDescItem"><a href=
"https://music.amazon.com?ref=dm_aff_amz_com" class="nav_a">
<h5 class="navFooterDescItem_heading">Amazon Music</h5>
<span class="navFooterDescText">Stream millions<br>
of songs</span></a></li>
<li class="navFooterDescItem"><a href=
"https://advertising.amazon.com/?ref=footer_advtsing_amzn_com"
class="nav_a">
<h5 class="navFooterDescItem_heading">Amazon Ads</h5>
<span class="navFooterDescText">Reach customers<br>
wherever they<br>
spend their time</span></a></li>
<li class="navFooterDescItem"><a href="https://www.6pm.com" class=
"nav_a">
<h5 class="navFooterDescItem_heading">6pm</h5>
<span class="navFooterDescText">Score deals<br>
on fashion brands</span></a></li>
<li class="navFooterDescItem"><a href="https://www.abebooks.com"
class="nav_a">
<h5 class="navFooterDescItem_heading">AbeBooks</h5>
<span class="navFooterDescText">Books, art<br>
& collectibles</span></a></li>
<li class="navFooterDescItem"><a href="https://www.acx.com/" class=
"nav_a">
<h5 class="navFooterDescItem_heading">ACX</h5>
<span class="navFooterDescText">Audiobook Publishing<br>
Made Easy</span></a></li>
<li class="navFooterDescItem"><a href=
"https://sell.amazon.com/?ld=AZUSSOA-footer-aff&amp;ref_=footer_sell"
class="nav_a">
<h5 class="navFooterDescItem_heading">Sell on Amazon</h5>
<span class="navFooterDescText">Start a Selling
Account</span></a></li>
<li class="navFooterDescItem"><a href=
"https://www.veeqo.com/?utm_source=amazon&amp;utm_medium=website&amp;utm_campaign=footer"
class="nav_a">
<h5 class="navFooterDescItem_heading">Veeqo</h5>
<span class="navFooterDescText">Shipping Software<br>
Inventory Management</span></a></li>
</ul>
<ul>
<li class="navFooterDescItem"><a href=
"/business?ref_=footer_retail_b2b" class="nav_a">
<h5 class="navFooterDescItem_heading">Amazon Business</h5>
<span class="navFooterDescText">Everything For<br>
Your Business</span></a></li>
<li class="navFooterDescItem"><a href=
"/alm/storefront?almBrandId=QW1hem9uIEZyZXNo&amp;ref_=footer_aff_fresh"
class="nav_a">
<h5 class="navFooterDescItem_heading">Amazon Fresh</h5>
<span class="navFooterDescText">Groceries & More<br>
Right To Your Door</span></a></li>
<li class="navFooterDescItem"><a href=
"/gp/browse.html?node=230659011&amp;ref_=footer_amazonglobal"
class="nav_a">
<h5 class="navFooterDescItem_heading">AmazonGlobal</h5>
<span class="navFooterDescText">Ship Orders<br>
Internationally</span></a></li>
<li class="navFooterDescItem"><a href=
"/services?ref_=footer_services" class="nav_a">
<h5 class="navFooterDescItem_heading">Home Services</h5>
<span class="navFooterDescText">Experienced Pros<br>
Happiness Guarantee</span></a></li>
<li class="navFooterDescItem"><a href=
"https://aws.amazon.com/what-is-cloud-computing/?sc_channel=EL&amp;sc_campaign=amazonfooter"
class="nav_a">
<h5 class="navFooterDescItem_heading">Amazon Web Services</h5>
<span class="navFooterDescText">Scalable Cloud<br>
Computing Services</span></a></li>
<li class="navFooterDescItem"><a href="https://www.audible.com"
class="nav_a">
<h5 class="navFooterDescItem_heading">Audible</h5>
<span class="navFooterDescText">Listen to Books & Original<br>
Audio Performances</span></a></li>
<li class="navFooterDescItem"><a href=
"https://www.boxofficemojo.com/?ref_=amzn_nav_ftr" class="nav_a">
<h5 class="navFooterDescItem_heading">Box Office Mojo</h5>
<span class="navFooterDescText">Find Movie<br>
Box Office Data</span></a></li>
</ul>
<ul>
<li class="navFooterDescItem"><a href="https://www.goodreads.com"
class="nav_a">
<h5 class="navFooterDescItem_heading">Goodreads</h5>
<span class="navFooterDescText">Book reviews<br>
& recommendations</span></a></li>
<li class="navFooterDescItem"><a href="https://www.imdb.com" class=
"nav_a">
<h5 class="navFooterDescItem_heading">IMDb</h5>
<span class="navFooterDescText">Movies, TV<br>
& Celebrities</span></a></li>
<li class="navFooterDescItem"><a href=
"https://pro.imdb.com?ref_=amzn_nav_ftr" class="nav_a">
<h5 class="navFooterDescItem_heading">IMDbPro</h5>
<span class="navFooterDescText">Get Info Entertainment<br>
Professionals Need</span></a></li>
<li class="navFooterDescItem"><a href="https://kdp.amazon.com"
class="nav_a">
<h5 class="navFooterDescItem_heading">Kindle Direct Publishing</h5>
<span class="navFooterDescText">Indie Digital & Print
Publishing<br>
Made Easy</span></a></li>
<li class="navFooterDescItem"><a href=
"/gp/browse.html?node=13234696011&amp;ref_=_gno_p_foot" class=
"nav_a">
<h5 class="navFooterDescItem_heading">Amazon Photos</h5>
<span class="navFooterDescText">Unlimited Photo Storage<br>
Free With Prime</span></a></li>
<li class="navFooterDescItem"><a href=
"https://videodirect.amazon.com/home/landing" class="nav_a">
<h5 class="navFooterDescItem_heading">Prime Video Direct</h5>
<span class="navFooterDescText">Video Distribution<br>
Made Easy</span></a></li>
<li class="navFooterDescItem"><a href="https://www.shopbop.com"
class="nav_a">
<h5 class="navFooterDescItem_heading">Shopbop</h5>
<span class="navFooterDescText">Designer<br>
Fashion Brands</span></a></li>
</ul>
<ul>
<li class="navFooterDescItem"><a href=
"/gp/browse.html?node=10158976011&amp;ref_=footer_wrhsdls" class=
"nav_a">
<h5 class="navFooterDescItem_heading">Amazon Resale</h5>
<span class="navFooterDescText">Great Deals on<br>
Quality Used Products</span></a></li>
<li class="navFooterDescItem"><a href=
"https://www.wholefoodsmarket.com" class="nav_a">
<h5 class="navFooterDescItem_heading">Whole Foods Market</h5>
<span class="navFooterDescText">America’s Healthiest<br>
Grocery Store</span></a></li>
<li class="navFooterDescItem"><a href="https://www.woot.com/"
class="nav_a">
<h5 class="navFooterDescItem_heading">Woot!</h5>
<span class="navFooterDescText">Deals and<br>
Shenanigans</span></a></li>
<li class="navFooterDescItem"><a href="https://www.zappos.com"
class="nav_a">
<h5 class="navFooterDescItem_heading">Zappos</h5>
<span class="navFooterDescText">Shoes &<br>
Clothing</span></a></li>
<li class="navFooterDescItem"><a href="https://ring.com" class=
"nav_a">
<h5 class="navFooterDescItem_heading">Ring</h5>
<span class="navFooterDescText">Smart Home<br>
Security Systems</span></a></li>
<li class="navFooterDescItem"><a href="https://eero.com/" class=
"nav_a">
<h5 class="navFooterDescItem_heading">eero WiFi</h5>
<span class="navFooterDescText">Stream 4K Video<br>
in Every Room</span></a></li>
<li class="navFooterDescItem"><a href=
"https://blinkforhome.com/?ref=nav_footer" class="nav_a">
<h5 class="navFooterDescItem_heading">Blink</h5>
<span class="navFooterDescText">Smart Security<br>
for Every Home</span></a></li>
</ul>
<ul>
<li class="navFooterDescItem" aria-hidden="true">&nbsp;</li>
<li class="navFooterDescItem"><a href=
"https://shop.ring.com/pages/neighbors-app" class="nav_a">
<h5 class="navFooterDescItem_heading">Neighbors App</h5>
<span class="navFooterDescText">Real-Time Crime<br>
& Safety Alerts</span></a></li>
<li class="navFooterDescItem"><a href=
"/gp/browse.html?node=14498690011&amp;ref_=amzn_nav_ftr_swa" class=
"nav_a">
<h5 class="navFooterDescItem_heading">Amazon Subscription
Boxes</h5>
<span class="navFooterDescText">Top subscription boxes – right to
your door</span></a></li>
<li class="navFooterDescItem"><a href="https://www.pillpack.com"
class="nav_a">
<h5 class="navFooterDescItem_heading">PillPack</h5>
<span class="navFooterDescText">Pharmacy Simplified</span></a></li>
<li class="navFooterDescItem"><a href=
"/gp/browse.html?node=12653393011&amp;ref_=footer_usrenew" class=
"nav_a">
<h5 class="navFooterDescItem_heading">Amazon Renewed</h5>
<span class="navFooterDescText">Like-new products<br>
you can trust</span></a></li>
<li class="navFooterDescItem" aria-hidden="true">&nbsp;</li>
<li class="navFooterDescItem" aria-hidden="true">&nbsp;</li>
</ul>
</div>
</div>
<div class=
"navFooterLine navFooterLinkLine navFooterPadItemLine navFooterCopyright">
<ul>
<li class="nav_first"><a href=
"/gp/help/customer/display.html?nodeId=508088&amp;ref_=footer_cou"
id="" class="nav_a">Conditions of Use</a></li>
<li><a href=
"/gp/help/customer/display.html?nodeId=468496&amp;ref_=footer_privacy"
id="" class="nav_a">Privacy Notice</a></li>
<li><a href=
"/gp/help/customer/display.html?ie=UTF8&amp;nodeId=TnACMrGVghHocjL8KB&amp;ref_=footer_consumer_health_data_privacy"
id="" class="nav_a">Consumer Health Data Privacy
Disclosure</a></li>
<li><a href="/privacyprefs?ref_=footer_iba" id="" class=
"nav_a">Your Ads Privacy Choices</a></li>
<li class="nav_last"><span id="nav-icon-ccba" class=
"nav-sprite"></span></li>
</ul>
<span>© 1996-2025, Amazon.com, Inc. or its affiliates</span></div>
</div>
<div id="sis_pixel_r2" aria-hidden="true" style=
"height:1px; position: absolute; left: -1000000px; top: -1000000px;">
</div>
 <!-- NAVYAAN FOOTER END -->
 <!-- sp:end-feature:nav-footer -->
<!-- sp:feature:configured-sitewide-assets -->

 <!-- sp:end-feature:configured-sitewide-assets -->
<!-- sp:feature:customer-behavior-js -->


<!-- sp:end-feature:customer-behavior-js -->
<!-- sp:feature:csm:body-close -->
<div id='be' style="display:none;visibility:hidden;">
<form name='ue_backdetect' action="get" id="ue_backdetect">
<input type="hidden" name='ue_back' value='1'></form>
</div>
<noscript><img height="1" width="1" style=
'display:none;visibility:hidden;' src=
'//fls-na.amazon.com/1/batch/1/OP/ATVPDKIKX0DER:133-3026301-1853324:6DVGTAH94T3XF2JJ2WW2$uedata=s:%2Frd%2Fuedata%3Fnoscript%26id%3D6DVGTAH94T3XF2JJ2WW2:0'
alt=""></noscript>
<!-- sp:end-feature:csm:body-close --></div>
"""
        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.promotion_applied, -0.05)
