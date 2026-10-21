__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.orders import AmazonOrders
from tests.unittestcase import UnitTestCase


class TestAmazonEs(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.es_config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "domain": "amazon.es",
        })

    def test_order_history(self):
        # WHEN
        orders = self.given_order_history("2026-0")

        # THEN
        self.assertEqual(8, len(orders))
        order = orders[0]
        self.assertEqual("405-0000000-0000001", order.order_number)
        self.assertEqual(datetime.date(2026, 7, 2), order.order_placed_date)
        self.assertFalse(order.cancelled)
        self.assertEqual("https://www.amazon.es/gp/your-account/order-details?orderID=405-0000000-0000001",
                         order.order_details_link)
        self.assertEqual("https://www.amazon.es/-/en/dp/B000000008?ref=ppx_yo2ov_dt_b_fed_asin_title",
                         order.items[0].link)
        self.assertEqual([23.9, 16.45, None, None, 10.89, 66.2, 66.2, 32.5], [o.grand_total for o in orders])
        self.assertEqual("171-0000000-0000008", orders[7].order_number)
        self.assertEqual(datetime.date(2026, 4, 16), orders[7].order_placed_date)

    def test_order_history_recipient(self):
        # WHEN
        order = self.given_order_history("2026-0")[0]

        # THEN
        self.assertEqual("Juan Pérez", order.recipient.name)
        self.assertEqual("Calle de Ejemplo, Portal 1\nEdificio Ejemplo\nMadrid, Madrid 28001\nSpain",
                         order.recipient.address)

    def test_order_history_cancelled(self):
        # WHEN
        orders = self.given_order_history("2026-0")

        # THEN
        self.assertEqual([False, False, True, True, False, False, False, False], [o.cancelled for o in orders])
        order = orders[2]
        self.assertIsNone(order.grand_total)
        self.assertIsNone(order.recipient)
        self.assertEqual("Cancelled", order.shipments[0].delivery_status)
        self.assertEqual(2, order.items[0].quantity)

    def test_order_history_delivered_months_ago_has_no_delivery_status(self):
        # WHEN
        orders = self.given_order_history("2026-0")

        # THEN
        self.assertEqual([None] * 6, [o.shipments[0].delivery_status for o in orders if not o.cancelled])

    def test_order_details(self):
        # WHEN
        order = self.given_order_details("402-0000000-0000005")

        # THEN
        self.assertEqual(datetime.date(2026, 4, 28), order.order_placed_date)
        self.assertEqual(10.89, order.grand_total)
        self.assertEqual(9.0, order.subtotal)
        self.assertEqual(0.0, order.shipping_total)
        self.assertEqual(9.0, order.total_before_tax)
        self.assertEqual(1.89, order.estimated_tax)
        self.assertEqual("Visa", order.payment_method)
        self.assertEqual("0000", order.payment_method_last_4)
        self.assertEqual("Juan Pérez", order.recipient.name)
        self.assertEqual("Calle de Ejemplo, Portal 1\nEdificio Ejemplo\nMadrid, Madrid 28001\nSpain",
                         order.recipient.address)
        self.assertIsNone(order.shipments[0].delivery_status)
        self.assertEqual(10.89, order.items[0].price)
        self.assertEqual("Example Seller", order.items[0].seller.name)
        self.assertEqual(datetime.date(2026, 5, 29), order.items[0].return_eligible_date)

    def test_order_details_vat(self):
        # WHEN
        order = self.given_order_details("171-0000000-0000008")

        # THEN
        self.assertEqual(32.5, order.grand_total)
        self.assertEqual(26.86, order.subtotal)
        self.assertEqual(26.86, order.total_before_tax)
        self.assertEqual(5.64, order.estimated_tax)
        self.assertEqual(32.5, order.items[0].price)

    def test_order_details_cancelled(self):
        # WHEN
        order = self.given_order_details("402-0000000-0000003")

        # THEN
        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
        self.assertIsNone(order.recipient)
        self.assertEqual(datetime.date(2026, 5, 5), order.order_placed_date)
        self.assertEqual("Cancelled", order.shipments[0].delivery_status)
        self.assertEqual(13.49, order.items[0].price)
        self.assertEqual(2, order.items[0].quantity)
        self.assertEqual("Amazon.es", order.items[0].seller.name)

    def given_resource(self, *path):
        with open(os.path.join(self.RESOURCES_DIR, *path), "r", encoding="utf-8") as f:
            return f.read()

    def given_order_history(self, name):
        return AmazonOrders.parse_order_history(self.given_resource("orders", "es", f"order-history-{name}.html"),
                                                self.es_config)

    def given_order_details(self, order_number):
        return AmazonOrders.parse_order_details(
            self.given_resource("orders", "es", f"order-details-{order_number}.html"), self.es_config)
