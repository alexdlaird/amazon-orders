__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonorders.conf import AmazonOrdersConfig
from bs4 import BeautifulSoup

from amazonorders.entity.item import Item
from tests.unittestcase import UnitTestCase


class TestItem(UnitTestCase):
    def test_price_stripped(self):
        # GIVEN
        html = """
<div class="a-fixed-left-grid-col yohtmlc-item a-col-right" style="padding-left:1.5%;float:left;">
<div class="a-row">
<a class="a-link-normal" href="/gp/product/B0018CJYCO/ref=ppx_od_dt_b_asin_title_s00?ie=UTF8&amp;psc=1">
        Item Title
    </a>
</div>
<div class="a-row">
<span class="a-size-small">
<div class="a-row a-size-small">Return window closed on Feb 2, 2019</div>
</span>
</div>
<div class="a-row">
<span class="a-size-small a-color-price">
    $1,234.99
</span>
</div>
</div>
</div>
"""
        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        # WHEN
        item = Item(parsed, self.test_config)

        # THEN
        self.assertEqual(item.title, "Item Title")
        self.assertEqual(item.price, 1234.99)

    def test_price_from_order_details_unit_price_offscreen(self):
        # GIVEN
        html = """
<div class="a-fixed-left-grid a-spacing-none">
    <div data-component="itemTitle">
        <a href="/dp/B0CFPJYX7P?ref_=ppx_hzod_title_dt_b_fed_asin_title_0_0">
            All-new Amazon Kindle Paperwhite
        </a>
    </div>
    <div data-component="unitPrice">
        <span class="a-price a-text-price" data-a-size="s" data-a-color="base">
            <span class="a-offscreen">$99.99</span>
            <span aria-hidden="true">$99.99</span>
        </span>
    </div>
</div>
"""
        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        # WHEN
        item = Item(parsed, self.test_config)

        # THEN
        self.assertEqual(item.title, "All-new Amazon Kindle Paperwhite")
        self.assertEqual(item.price, 99.99)

    def test_title_and_link_from_history_image_card(self):
        # GIVEN
        html = """
<div class="a-fixed-right-grid-col item-box" style="float:left;">
    <div class="product-grid-image">
        <a class="a-link-normal" href="/dp/B0CFPJYX7P?ref=ppx_yo2ov_dt_b_fed_asin_title" tabindex="-1">
            <img alt="All-new Amazon Kindle Paperwhite"
                 src="https://m.media-amazon.com/images/I/example._SS142_.jpg" />
        </a>
    </div>
</div>
"""
        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        # WHEN
        item = Item(parsed, self.test_config)

        # THEN
        self.assertEqual(item.title, "All-new Amazon Kindle Paperwhite")
        self.assertEqual(
            item.link,
            "https://www.amazon.com/dp/B0CFPJYX7P?ref=ppx_yo2ov_dt_b_fed_asin_title")

    def test_title_starts_with_ampersand_use_lxml(self):
        # GIVEN
        lxml_config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "bs4_parser": "lxml"
        })
        html = """
<div class="a-fixed-left-grid-col yohtmlc-item a-col-right" style="padding-left:1.5%;float:left;">
<div class="a-row">
    <a class="a-link-normal" href="/dp/B0CW5Y6PKG?ref_=ppx_hzod_title_dt_b_fed_asin_title_0_0">&And Per Se Lined</a>
</div>
</div>
"""
        parsed = BeautifulSoup(html, lxml_config.bs4_parser)

        # WHEN
        item = Item(parsed, lxml_config)

        # THEN
        self.assertEqual(item.title, "&And Per Se Lined")
