__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os

from bs4 import BeautifulSoup

from amazonorders.orders import AmazonOrders
from tests.unittestcase import UnitTestCase


class TestShipment(UnitTestCase):
    def given_order_details_html(self):
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-details-112-5234348-8033063.html"),
                  "r",
                  encoding="utf-8") as f:
            return f.read()

    def test_shipment_tracking_link_current_order_details_layout(self):
        # GIVEN
        html = self.given_order_details_html()

        # WHEN
        order = AmazonOrders.parse_order_details(html, self.test_config, order_number="112-5234348-8033063")

        # THEN
        self.assertEqual(1, len(order.shipments))
        self.assertTrue(order.shipments[0].tracking_link.startswith(
            f"{self.test_config.constants.BASE_URL}/progress-tracker/package?orderId=112-5234348-8033063"))

    def test_shipment_cancel_items_link_is_not_a_tracking_link(self):
        # GIVEN
        parsed = BeautifulSoup(self.given_order_details_html(), self.test_config.bs4_parser)
        for link in parsed.select("a[href^='/progress-tracker/package?']"):
            link.decompose()
        self.assertTrue(parsed.select("a[href*='/progress-tracker/package/preship/cancel-items']"),
                        "With its Track package link removed, the Shipment should still have its cancel-items link")

        # WHEN
        order = AmazonOrders.parse_order_details(str(parsed), self.test_config, order_number="112-5234348-8033063")

        # THEN
        self.assertIsNone(order.shipments[0].tracking_link)
