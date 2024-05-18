__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

from bs4 import BeautifulSoup

from amazonorders.entity.item import Item
from tests.testcase import TestCase


class TestItem(TestCase):
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
        parsed = BeautifulSoup(html, "html.parser")

        # WHEN
        item = Item(parsed)

        # THEN
        self.assertEqual(item.title, "Item Title")
        self.assertEqual(item.price, 1234.99)
