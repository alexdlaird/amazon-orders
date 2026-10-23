__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.orders import AmazonOrders
from tests.unittestcase import UnitTestCase


class TestAmazonUk(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.uk_config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "domain": "amazon.co.uk",
        })

    def test_order_history(self):
        # WHEN
        orders = self.given_order_history("2025-0")

        # THEN
        self.assertEqual(["026-0000000-0000001", "026-0000000-0000002", "206-0000000-0000003"],
                         [order.order_number for order in orders])
        self.assertEqual([datetime.date(2025, 11, 28), datetime.date(2025, 10, 14), datetime.date(2025, 3, 6)],
                         [order.order_placed_date for order in orders])
        self.assertEqual([None, 91.29, 21.94], [order.grand_total for order in orders])
        order = orders[1]
        self.assertEqual(1, len(order.shipments))
        self.assertEqual(2, len(order.items))
        self.assertEqual("Example Notebook A5, Lined, 80 Sheets - Pack of 3", order.items[1].title)
        self.assertEqual("https://www.amazon.co.uk/dp/B000000002?ref=ppx_yo2ov_dt_b_fed_asin_title",
                         order.items[1].link)

    def test_order_history_recipient(self):
        # WHEN
        orders = self.given_order_history("2025-0")

        # THEN
        self.assertEqual("Jane Doe", orders[1].recipient.name)
        self.assertEqual("Example House\n1 Example Street\nLondon EC1A1BB\nUnited Kingdom",
                         orders[1].recipient.address)
        self.assertEqual("John Smith", orders[2].recipient.name)
        self.assertEqual("2 Sample Road\nExampletown, Example County 1234\nIreland", orders[2].recipient.address)

    def test_order_history_cancelled(self):
        # WHEN
        order = self.given_order_history("2025-0")[0]

        # THEN
        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
        self.assertIsNone(order.recipient)
        self.assertEqual("Cancelled", order.shipments[0].delivery_status)

    def test_order_history_delivered_months_ago_has_no_delivery_status(self):
        # WHEN
        orders = self.given_order_history("2025-0")

        # THEN
        self.assertEqual([None, None], [order.shipments[0].delivery_status for order in orders[1:]])

    def test_order_details(self):
        # WHEN
        order = self.given_order_details("026-0000000-0000002")

        # THEN
        self.assertEqual(datetime.date(2025, 10, 14), order.order_placed_date)
        self.assertEqual(91.29, order.grand_total)
        self.assertEqual(76.08, order.subtotal)
        self.assertEqual(3.99, order.shipping_total)
        self.assertEqual(80.07, order.total_before_tax)
        self.assertEqual(16.01, order.estimated_tax)
        self.assertEqual(-4.79, order.promotion_applied)
        self.assertEqual("Visa", order.payment_method)
        self.assertEqual("0000", order.payment_method_last_4)
        self.assertEqual("Jane Doe", order.recipient.name)
        self.assertEqual("Example House\n1 Example Street\nLondon EC1A1BB\nUnited Kingdom", order.recipient.address)
        self.assertEqual(1, len(order.shipments))
        self.assertIsNone(order.shipments[0].delivery_status)
        self.assertEqual([58.19, 33.1], [item.price for item in order.items])
        self.assertEqual(["Example Seller", "Another Example Seller"], [item.seller.name for item in order.items])
        self.assertEqual(datetime.date(2025, 11, 16), order.items[0].return_eligible_date)

    def test_order_details_postage(self):
        # WHEN
        order = self.given_order_details("206-0000000-0000003")

        # THEN
        self.assertEqual(21.94, order.grand_total)
        self.assertEqual(7.2, order.subtotal)
        self.assertEqual(12.95, order.shipping_total)
        self.assertEqual(20.15, order.total_before_tax)
        self.assertEqual(1.79, order.estimated_tax)
        self.assertEqual("John Smith", order.recipient.name)
        self.assertEqual("2 Sample Road\nExampletown, Example County 1234\nIreland", order.recipient.address)
        self.assertEqual(8.64, order.items[0].price)
        self.assertEqual("Example Seller", order.items[0].seller.name)

    def test_order_details_cancelled(self):
        # WHEN
        order = self.given_order_details("026-0000000-0000001")

        # THEN
        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
        self.assertIsNone(order.subtotal)
        self.assertIsNone(order.recipient)
        self.assertEqual(datetime.date(2025, 11, 28), order.order_placed_date)
        self.assertEqual("Cancelled", order.shipments[0].delivery_status)
        self.assertEqual(29.99, order.items[0].price)
        self.assertEqual("Amazon.co.uk", order.items[0].seller.name)

    def given_resource(self, *path):
        with open(os.path.join(self.RESOURCES_DIR, *path), "r", encoding="utf-8") as f:
            return f.read()

    def given_order_history(self, name):
        return AmazonOrders.parse_order_history(self.given_resource("orders", "uk", f"order-history-{name}.html"),
                                                self.uk_config)

    def given_order_details(self, order_number):
        return AmazonOrders.parse_order_details(
            self.given_resource("orders", "uk", f"order-details-{order_number}.html"), self.uk_config)
