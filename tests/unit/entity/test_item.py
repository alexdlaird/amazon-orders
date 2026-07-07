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
        self.assertEqual(item.asin, "B0018CJYCO")

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
        self.assertEqual(item.asin, "B0CW5Y6PKG")

    def test_asin_none_when_link_not_a_product_page(self):
        # GIVEN an item whose link is not a product detail page (e.g. a "Buy it again" URL)
        html = """
<div class="a-fixed-left-grid-col yohtmlc-item a-col-right">
<div class="a-row">
<a class="a-link-normal" href="/gp/buyagain?ie=UTF8&amp;ref_=ppx_od_dt_b_buy_again">Item Title</a>
</div>
</div>
"""
        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        # WHEN
        item = Item(parsed, self.test_config)

        # THEN
        self.assertEqual(item.title, "Item Title")
        self.assertIsNone(item.asin)

    def test_quantity_parsed_from_qty_element(self):
        # GIVEN an item with a whole-number quantity element
        html = """
<div class="a-fixed-left-grid-col yohtmlc-item a-col-right">
<div class="a-row">
<a class="a-link-normal" href="/dp/B0018CJYCO/ref=x">Item Title</a>
</div>
<div class="od-item-view-qty">3</div>
</div>
"""
        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        # WHEN
        item = Item(parsed, self.test_config)

        # THEN
        self.assertEqual(3, item.quantity)
