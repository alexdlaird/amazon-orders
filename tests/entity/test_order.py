__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

from bs4 import BeautifulSoup

from amazonorders.entity.order import Order
from tests.testcase import TestCase


class TestOrder(TestCase):
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
<span class="a-button a-button-base"><span class="a-button-inner"><a class="a-button-text" href="/gp/css/summary/print.html/ref=ppx_od_dt_b_invoice?ie=UTF8&amp;orderID=112-9685975-5907428" role="button">
        View or Print invoice
    </a></span></span>
</div>
</div>
</div>
<div class="a-row a-spacing-base hide-if-js">
<div class="a-column a-span12 a-spacing-top-mini">
<ul class="a-unordered-list a-nostyle a-vertical">
<li><span class="a-list-item">
<a class="a-link-normal" href="/gp/css/summary/print.html/ref=ppx_od_dt_b_invoice?ie=UTF8&amp;orderID=112-9685975-5907428">
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
<script type="text/javascript">//<![CDATA[
(function(){"undefined"===typeof PaymentsPortal2&&(PaymentsPortal2={toString:function(){return"PaymentsPortal2"}});"undefined"===typeof APX&&(APX=PaymentsPortal2);if(!PaymentsPortal2.modules){var n=function(){};"undefined"!==typeof console&&console.error&&(n=function(){console.error(Array.prototype.slice.call(arguments,0).join(" "))});var l=function(){function l(b,a){var d;d=0<a.length&&"."===a.charAt(0)?b.split(/\/+/).concat(a.split(/\/+/)):a.split(/\/+/);for(var e=[],f=0,k=d.length;f<k;f++){var h=
d[f];""!==h&&"."!==h&&(".."===h?e.pop():e.push(h))}return e.join("/")}function s(b,a){for(var d=[],e=0,f=a.length;e<f;e++)d.push(l(b,a[e]));return d}function g(b,c){delete a._loading[b];a._modules[b]=c;if(a._waiting[b]){var d=a._waiting[b];delete a._waiting[b];for(var e=0,f=d.length;e<f;e++)try{d[e](c)}catch(k){n("Callback waiting on module ["+b+"] failed: "+k)}}}function p(b){if(a._modules[b])return a._modules[b];if(a._loading[b]||!a._definitions[b])return null;var c=a._definitions[b];a._loading[b]=
{start_time:Date.now()};m(s(b,c.deps),function(){var a=Array.prototype.slice.call(arguments,0),a=c.factory.apply(null,a);g(b,a)})}function t(b,c){a._modules[b]?c(a._modules[b]):(a._waiting[b]||(a._waiting[b]=[]),a._waiting[b].push(c),p(b))}function q(b,c){a._definitions[b]&&c.call(c)}function m(b,c,d){function e(a){return function(d){k[a]=d;f++;f>=b.length&&!h&&(h=!0,c.apply(c,k))}}if(0===b.length)c.call(c);else{for(var f=0,k=[],h=!1,g=0,l=b.length;g<l;g++){var m=b[g];k.push(null);t(m,e(g))}!0===
d&&window.setTimeout(function(){h||(h=!0,c.apply(c,k))},a._waitMilliseconds)}}function r(b,c,d){if(a._definitions[b])return!1;a._definitions[b]={id:b,deps:c,factory:d};a._waiting[b]&&p(b)}var a=this;a._waitMilliseconds=7E3;a._modules={};a._definitions={};a._waiting={};a._loading={};g("modules",a);g("when",m);g("define",r);g("isDefined",q);a.when=m;a.define=r;a.isDefined=q};PaymentsPortal2.ModuleSystem=l;PaymentsPortal2.modules=new l}})();
//]]></script>
<script type="text/javascript">//<![CDATA[
PaymentsPortal2.widgetStartTime = (new Date()).getTime();
//]]></script>
<script type="text/javascript">//<![CDATA[
PaymentsPortal2.modules.when(['clog'],function(clog){clog.setConfiguration({"sushiEelSourceGroup":"com.amazon.eel.ApertureService.NA.Prod.ClientSideMetricsData","isPmetLoggingOn":true,"foresterEndpoint":"https://fls-na.amazon.com/","defaultClient":"chainedLoggingClient","sushiEelEndPoint":"https://unagi-na.amazon.com/","pmetPostBackChannel":"/1/action-impressions/1/OP/payments-portal/action/","timberLoggingChannel":"/1/payments-portal-log/1/OP/","isTimberLoggingOn":true,"isSushiEelLoggingOn":true});clog.setPmetHeaders({"method":"ViewPaymentPlanSummary","marketplaceId":"ATVPDKIKX0DER","service":"PaymentsPortalWidgetService","client":"YA:OD","session":"142-6865106-8155502","requestId":"0JP0ZC5XBACDNBHJYDDK","marketplace":"ATVPDKIKX0DER"});});
//]]></script>
<div class="a-row pmts-portal-root-pYSRRc1MwC2h pmts-portal-component pmts-portal-components-pp-emTOEN-1" data-pmts-component-id="pp-emTOEN-1"><div class="a-column a-span12 pmts-payment-instrument-billing-address"><div class="a-row a-spacing-small pmts-portal-component pmts-portal-components-pp-emTOEN-2" data-pmts-component-id="pp-emTOEN-2"><div class="a-row pmts-payments-instrument-header"><span class="a-text-bold">Payment method</span></div> <div class="a-row pmts-payments-instrument-details"><ul class="a-unordered-list a-nostyle a-vertical no-bullet-list pmts-payments-instrument-list"><li class="a-spacing-micro pmts-payments-instrument-detail-box-paystationpaymentmethod"><span class="a-list-item"><img alt="American Express" class="pmts-payment-credit-card-instrument-logo" height="23px" src="https://m.media-amazon.com/images/G/01/payments-portal/r1/issuer-images/amex._CB606661317_.gif" width="34px"/><span class="a-letter-space"></span>AMEX<span class="a-letter-space"></span><span class="a-color-base">ending in 1234</span></span></li></ul></div></div></div></div><link href="https://m.media-amazon.com/images/I/11STWhdvr1L._RC|01tEjLkP-OL.css,01bbZVzSQNL.css,01vdkF9Z76L.css,116LWdTN6UL.css,01cq16REt9L.css,01qk4TdW33L.css,01cxjPaaTNL.css,01SJRGuZivL.css,21jGj3aJ6ZL.css,11HEveYPS1L.css,01hOHsbn7OL.css,01IsDXoRrML.css,01hIZRtcaHL.css,01NGxBoTbmL.css,01Mv8eppKAL.css,21wNB3CrHWL.css,01uakdML80L.css,01uHZesS5LL.css,01+yNs7ZU5L.css,01rKSjRRIdL.css,018M3caCSzL.css,01Rgr3O5jgL.css,61dr2UXxtuL.css,01xniGkbKHL.css,01BUQQ2AAFL.css,11+KVSh5kaL.css,018GGCZ05rL.css,01RVwf5E26L.css,018QFljl9NL.css,012HRkWTMYL.css,01zEhgDPWUL.css,01le4Wlx71L.css,01NfyFypiAL.css,01x1gcd+b6L.css,21zTvWgvN9L.css,117QsyrFaLL.css,01rOyQsKCBL.css,216l1X8P-IL.css,01X3lCf9VVL.css,01K72ZPRhdL.css,01Kz8HcbaSL.css,1192eqsMCTL.css,01R2fuBKvbL.css,01W9cE2pBBL.css,31-bDOHdCwL.css,01ENy2AhhHL.css,01I7irLLHyL.css,01i7-FZ2dbL.css,017jTRPN3cL.css,01NDW5IRowL.css,01Jrep1-A8L.css,013mx6I5MjL.css,01DR-IGztZL.css,01oed2b7XHL.css,21WyWpnsGQL.css,01-BlL5QIGL.css,01dkJYlUMlL.css,013gNYW5EZL.css,01Xbi2zDI3L.css,01B8WX2PjrL.css,01Z42xKR4FL.css,01JRZxD87IL.css,01Gtbyceb8L.css,0167aosbt1L.css_.css" rel="stylesheet" type="text/css"/><script crossorigin="anonymous" src="https://m.media-amazon.com/images/I/01F0eSdeFgL._RC|01xmHR8sKWL.js,01iU5FKX41L.js,919nou8O27L.js,11shczZNLZL.js,41OK+4Lm-iL.js,11T-3FJmE9L.js,01qEgqz5vWL.js,21qTjCFVqIL.js,11F9QyGQPnL.js,01BjMuhuoeL.js,018z02DgcjL.js,11KS4xFurNL.js,219vNzbHRgL.js,01fxQjpFtZL.js,01QPv-sKbXL.js,71WMILgvsLL.js,51BHs8h9KnL.js,11+tQLDZ-IL.js,01KeVI9xAiL.js,01XLCeEHWjL.js,01xfr089i8L.js,21gewC-zDDL.js,01CUisRJf+L.js,31mNdxdUlgL.js,216HiRnakKL.js,312wNDcgKsL.js,11FFV0G8zZL.js,11XbKUK-ArL.js,01WyXDgSamL.js,31dsVwu8CwL.js,31cVytUMlWL.js,31U4-Br3oPL.js,11aY1lQF82L.js,01roLdTw9jL.js,01Mhun3p1rL.js,016FFR4UHfL.js,01ghTmZWxzL.js,410+Csn2ZyL.js,31FyjWJQV-L.js,11ruTNcrLiL.js,01hC7uSyu5L.js,01m2evVOkML.js,11FLRVpft9L.js,21SrQ2-brNL.js,01RRCzTIGEL.js,01mKFj6urxL.js,01i9sd1tlLL.js,01-m7UpNfBL.js,01Bc-x2JZsL.js,11591L2Cy4L.js,01ABJiWqfwL.js,71LTwtyi+UL.js,31-x88yHigL.js,1174-niYaEL.js,01ZUNUWYXsL.js,01A7H8lWDrL.js,01lxWznRyaL.js,017+AeYdZuL.js,11cGKqPukkL.js,018dSiL9euL.js,01UQyGktSML.js,01xxApHnfyL.js,01E3k-v-atL.js,01iFWiaisVL.js,116TX+5+a2L.js,31wf7sMeZHL.js,11EFMf+dQ8L.js,416XJa2aeLL.js,01-aaq0fL6L.js,514YwzMMKBL.js,415sUFyMqqL.js,01MO6nvtT1L.js,01LLJS-ZZLL.js,01e+LXgUv6L.js,21lqO+lmeiL.js,01qC+NC256L.js,01jLz4OklDL.js,21INoH2rvoL.js,01zrYLlEn5L.js,01j3UbDYoSL.js,41lV5whFKQL.js,415NKG0t2LL.js,31xh9aiCUuL.js,21O8cpr6qsL.js,51FTWgWbK8L.js,015faUVD0cL.js_.js" type="text/javascript"></script>
<script type="text/javascript">//<![CDATA[
(function() {
        PaymentsPortal2.modules.when(['widget-factory'], function(wf) {
          var options = {"testAjaxAuthenticationRequired":"false","clientId":"YA:OD","serializedState":"4-MS282udtQVYSXJsVo-_4koqNamon4sYUxSndkdH2dcOfAQk-lV92T08Q86LrBUYzfrqwcfxxcEN3nsRhAHq3Y7txlOlnkjBDXoXo3uj_myGmd-984TGbrtyg1U53BZdp3UBH0Gpdoqk0dWtID7QDQpHa924UITU4WrUlh_N7JWJKchZw25ZKxYTksMX2Sj3slihCW5G2PnnjcxUMy0WWDxXwxlRODx9jougohblA0GW1Tw5w05E_6m55Rgj_eHDpY7jnZArauu1BMYNHQMXjwH3sFOy2n_lpkpFpW6jz_7BGvBjTVTs0DbrS9dkyhCJ4cZIEZETazZ6ZJ0fBUpciSEPV_YUQLmj2ZkE8gluh-1Eimc38oz0zQ929lOFmi0P4rmyU2dITDc0WwFEMujJ7zdstjeemAiyCeCZTApoz2O8KG6fu9XENE2Ga6BkCzwC64L7i1n2XhttrXn4Te1CkUoVnGRpX9_r1xxt3339tlnzqpd7TUQZhjU5Q4YJxovFqIInSzNSsTP0kuEePupS1ZrXERGBF-bypEDUpAqcYqfKPClvwmuqgHfd3NEztSkmeYJ6pYWrqNiBc0TvJ6Ii0fQufK9XeCpUs5gYcG17L4qXv5AuZ0pAl93Y7lHBfewCLxQvgBRAZ8KxU8RQHH770o_dRfsnK9E_22HtI5mL3tg1PTuKp3zsUK9dDg0KXWm-XSwN--L1zTwc2O4LeAuJiRol3rsVbTkVCDSvaUZR7xWWW-VOjo-gGHuYsN4on0G90wD-Je4squQKoBxk2uZd1PnMKqAyJdNorVyJULmj9jpvLQu0CT5uWnNd-YaGEy-gyerKBpU1tPQ82l0QBRccqF8HdN9wLzRRTAG9ZtmqZ-OXJB4rT8xU8VW4VZg8QA0g9F2Bb_ZzE6f7jrTWsOptsBvmEqqRdV2SLmmZKEQQ6GgYYpsYS17w9m-f9InBF0tIgHy0gcQbeflhAzd1nzapV3lhSBEvL6pgt-oLuRLTcIKbFruSCsZWyj649cifOZtBc3yZPV_MGP01WdH0rb9gkN_4JXNExTx0mzwZmNImKo7XXtRTpTgljTsc_4Z5uof66Viovk5P5vcX5KsJtupcpSwr6d1Ks1i4_R0ZmnVObsLRwg1cQQyOVrSPSos6Ef3pbP7yuzhAIAdacq8MdnDD6nTVgL-dTFQEYvaxtKPvorO7LFk--kDzip6SU2EZjhOI7dbzutQdC5qbaGUzupOHc-NfR1m44nT6kofrEUSo","marketplaceId":"ATVPDKIKX0DER","deviceType":"desktop","locale":"en_US","customerId":"A2860EUOMMG06V","sessionId":"142-6865106-8155502","requestId":"0JP0ZC5XBACDNBHJYDDK","widgetInstanceId":"pYSRRc1MwC2h","continueRequestAjaxSubstitutionEnabled":true,"clientLoggingWeblabEnabledValue":"false"};
          var data = [{"elementReferences":{},"elementDOMEventMethodBindings":[],"data":{},"id":"pp-emTOEN-2","elementReferenceTagType":{},"type":"PaymentInstrumentComponent"}];
          var localizedStrings = {};
          var widgetCreationEpochMilliseconds = 1705435639584;

          wf.create('ViewPaymentPlanSummary', options, data, localizedStrings, widgetCreationEpochMilliseconds);
        });
      }());
//]]></script>
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
<a class="a-expander-header a-declarative a-expander-inline-header a-link-expander" data-a-expander-toggle='{"allowLinkDefault":true, "expand_prompt":"", "collapse_prompt":""}' data-action="a-expander-toggle" href="javascript:void(0)"><i class="a-icon a-icon-expand"></i><span class="a-expander-prompt">
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
<span class="js-shipment-info aok-hidden" data-isstatuswithwarning="0" data-yodeliveryestimate="Delivered Dec 9, 2023" data-yoshortstatuscode="DELIVERED" data-yostatusstring="">
</span>
</div>
</div>
<div class="actions" style="width:220px;">
<div class="a-row">
<div class="a-button-stack">
<span class="a-declarative" data-action="set-shipment-info-cookies" data-set-shipment-info-cookies="{}">
<span class="a-button a-button-base track-package-button"><span class="a-button-inner"><a class="a-button-text" href="/progress-tracker/package/ref=ppx_od_dt_b_track_package?_encoding=UTF8&amp;itemId=rgjglontrkkvsn&amp;orderId=112-9685975-5907428&amp;packageIndex=0&amp;shipmentId=X42HwBr10&amp;vt=ORDER_DETAILS" role="button">
            Track package
        </a></span></span>
</span>
</div>
</div>
</div>
</div>
<div class="a-fixed-right-grid a-spacing-top-medium"><div class="a-fixed-right-grid-inner a-grid-vertical-align a-grid-top">
<div class="a-fixed-right-grid-col a-col-left" style="padding-right:3.2%;float:left;">
<div class="a-row">
<div class="a-fixed-left-grid a-spacing-none"><div class="a-fixed-left-grid-inner" style="padding-left:100px">
<div class="a-text-center a-fixed-left-grid-col a-col-left" style="width:100px;margin-left:-100px;float:left;">
<div class="item-view-left-col-inner">
<a class="a-link-normal" href="/gp/product/B0CLJ9KGRV/ref=ppx_od_dt_b_asin_image_s00?ie=UTF8&amp;psc=1">
<img alt="" aria-hidden="true" class="yo-critical-feature" data-a-hires="https://m.media-amazon.com/images/I/41ZiqpN4uvL._SY180_.jpg" height="90" onload="if (typeof uet == 'function') { uet('cf'); uet('af'); } if (typeof event === 'object' &amp;&amp; event.target) {
              var el = event.target;
              if (('' + el.tagName).toLowerCase() == 'img' &amp;&amp; !el.getAttribute('data-already-flushed-csm')) {
                  el.setAttribute('data-already-flushed-csm', 'true');
                  if (typeof ue == 'object' &amp;&amp; ue.isl &amp;&amp; typeof uet == 'function' &amp;&amp; typeof uex == 'function') {
                      var scope = 'imgonload-' + (+new Date) + '-';
                      uet('ld', scope + 'cf', {}, ue.t0);
                      uet('cf', scope + 'cf', {}, ue.t0);
                      uet('af', scope + 'cf', {}, ue.t0);
                      uex('at', scope + 'cf');
                      uex('ld', scope + 'ld');
                  }
              }
          }" src="https://m.media-amazon.com/images/I/41ZiqpN4uvL._SY90_.jpg" title="Cadeya Egg Cleaning Brush Silicone, Egg Scrubber for Fresh Eggs, Reusable Cleaning Tools for Egg Washer (Pink)" width="90"/>
</a>
</div>
</div>
<div class="a-fixed-left-grid-col yohtmlc-item a-col-right" style="padding-left:1.5%;float:left;">
<div class="a-row">
<a class="a-link-normal" href="/gp/product/B07YQDD94M/ref=ppx_od_dt_b_asin_title_s01?ie=UTF8&amp;psc=1">
        Swiffer WetJet Hardwood and Floor Spray Mop Cleaner Starter Kit, Includes: 1 Power Mop, 10 Pads, Cleaning Solution, Batteries
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
<span class="a-button a-spacing-mini a-button-primary yohtmlc-buy-it-again"><span class="a-button-inner"><a aria-label="Buy it again" class="a-button-text" href="/gp/buyagain/ref=ppx_od_dt_b_bia?ie=UTF8&amp;ats=eyJjdXN0b21lcklkIjoiQTI4NjBFVU9NTUcwNlYiLCJleHBsaWNpdENhbmRpZGF0ZXMiOiJCMDdZ%0AUUREOTRNIn0%3D%0A" role="button">
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
<span class="a-button a-button-normal a-spacing-mini a-button-primary"><span class="a-button-inner"><a class="a-button-text" href="/ps/product-support/resolutions?_encoding=UTF8&amp;itemId=rgjglontrkkvwn&amp;orderId=112-9685975-5907428&amp;ref_=ppx_od_dt_b_prod_support_single_item_s01&amp;shipmentId=Xtn5lYRx0" id="Get-product-support_2" role="button">
            Get product support
        </a></span></span>
<span class="a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner"><a class="a-button-text" href="/spr/returns/cart?_encoding=UTF8&amp;orderId=112-9685975-5907428&amp;ref_=ppx_od_dt_b_return_replace_s01" id="Return-or-replace-items_2" role="button">
            Return or replace items
        </a></span></span>
<span class="a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner"><a class="a-button-text" href="/gcx/-/ty/gr/112-9685975-5907428/Xtn5lYRx0/ref=ppx_od_dt_b_gift_receipt_s01" id="Share-gift-receipt_2" role="button">
            Share gift receipt
        </a></span></span>
<span class="a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner"><a class="a-button-text" href="/review/review-your-purchases/ref=ppx_od_dt_b_rev_prod_s01?_encoding=UTF8&amp;asins=B07YQDD94M&amp;channel=YAcc-wr" id="Write-a-product-review_2" role="button">
            Write a product review
        </a></span></span>
<span class="a-declarative" data-a-modal='{"width":600,"name":"archive-order-modal","url":"/gp/css/order-history/archive/archiveModal.html?orderId=112-9685975-5907428&amp;shellOrderId=","header":"Archive this order"}' data-action="a-modal">
<span class="a-button a-button-normal a-spacing-mini a-button-base"><span class="a-button-inner"><a class="a-button-text" href="/gp/css/order-history/archive/ref=ppx_od_dt_b_archive_order_s01?ie=UTF8&amp;archiveRequest=1&amp;orderIds=112-9685975-5907428&amp;token=142-6865106-8155502" id="Archive-order_2" role="button">
            Archive order
        </a></span></span>
</span>
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
<script type="text/javascript">
    if (ue) {
        uet('cf');
    }
</script>
<script type="text/javascript">(function(f) {var _np=(window.P._namespace(""));if(_np.guardFatal){_np.guardFatal(f)(_np);}else{f(_np);}}(function(P) {
    window.P && P.register('sp.load.js');
}));</script>
<div class="a-section a-spacing-large a-spacing-top-large">
<div id="desktop-yo-orderdetails_ALL_desktop-yo-orderdetails_0_container"><script>(window.AmazonUIPageJS ? AmazonUIPageJS : P).when('A', 'dram-lazy-load-widget', 'ready').execute(function(A) {A.trigger('dram:register-lazy-load-widget', '#desktop-yo-orderdetails_ALL_desktop-yo-orderdetails_0_container',2500, 'desktop-yo-orderdetails_desktop', true);});</script><script class="json-content" type="application/json">{"encryptedLazyLoadRenderRequest":"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"}</script><div class="widget-html-container"><div style="height: 350px;"><span class="lazy-load-spinner"></span></div></div></div><link href="https://images-na.ssl-images-amazon.com/images/I/01FvA6+tfcL.css?AUIClients/DramAssets" rel="stylesheet">
<script>
  (window.AmazonUIPageJS ? AmazonUIPageJS : P).load.js('https://images-na.ssl-images-amazon.com/images/I/01UiZXT0lxL.js?AUIClients/DramAssets');
</script>
</link></div>
</div>
"""
        parsed = BeautifulSoup(html, "html.parser")

        # WHEN
        order = Order(parsed, full_details=True)

        # THEN
        self.assertEqual(order.subtotal, 1111.99)
        self.assertEqual(order.shipping_total, 2222.99)
        self.assertEqual(order.total_before_tax, 3333.99)
        self.assertEqual(order.estimated_tax, 4444.99)
        # self.assertEqual(order.refund_total, 5555.99)
        # self.assertEqual(order.subscription_discount, 6666.99)
        self.assertEqual(order.grand_total, 7777.99)
