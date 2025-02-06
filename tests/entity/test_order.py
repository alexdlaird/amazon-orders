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
