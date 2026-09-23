__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from datetime import date

from bs4 import BeautifulSoup

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.orders import AmazonOrders, _parse_order_count
from amazonorders.transactions import AmazonTransactions
from tests.unittestcase import UnitTestCase


class TestAmazonDe(UnitTestCase):
    """
    Parse the anonymized amazon.de fixtures in ``tests/resources/de``.
    """

    def setUp(self):
        super().setUp()

        self.de_config = AmazonOrdersConfig(data={
            "domain": "amazon.de",
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
        })

    def _read(self, *path):
        with open(os.path.join(self.RESOURCES_DIR, "de", *path), "r", encoding="utf-8") as f:
            return f.read()

    def _details(self, order_number):
        return AmazonOrders.parse_order_details(self._read("orders", f"order-details-{order_number}.html"),
                                                self.de_config)

    def test_order_history(self):
        orders = AmazonOrders.parse_order_history(self._read("orders", "order-history-2026-0.html"), self.de_config)

        self.assertEqual(3, len(orders))
        order = orders[0]
        self.assertEqual("305-2331968-2925732", order.order_number)
        self.assertEqual(date(2026, 9, 6), order.order_placed_date)
        self.assertEqual(7.43, order.grand_total)
        self.assertFalse(order.cancelled)
        self.assertEqual("Max Mustermann", order.recipient.name)
        self.assertEqual("Musterstraße 1\n10115 Berlin\nDeutschland", order.recipient.address)
        self.assertEqual("Zustellung: 15. September", order.shipments[0].delivery_status)
        self.assertEqual("Testartikel 1", order.items[0].title)
        self.assertEqual(30.36, orders[2].grand_total)

    def test_order_history_later_page(self):
        orders = AmazonOrders.parse_order_history(self._read("orders", "order-history-2026-10.html"), self.de_config)

        self.assertEqual([0.0, 199.94, 24.46], [order.grand_total for order in orders])
        self.assertEqual([date(2026, 7, 27), date(2026, 7, 16), date(2026, 7, 12)],
                         [order.order_placed_date for order in orders])

    def test_order_count(self):
        self.assertEqual(229, _parse_order_count(BeautifulSoup("<b>229 Bestellungen</b>", "html.parser").b))
        self.assertEqual(1213, _parse_order_count(BeautifulSoup("<b>1.213 Bestellungen</b>", "html.parser").b))

    def test_order_details(self):
        order = self._details("305-4666232-2538376")

        self.assertEqual("305-4666232-2538376", order.order_number)
        self.assertEqual(date(2026, 8, 18), order.order_placed_date)
        self.assertEqual(30.36, order.grand_total)
        self.assertEqual(25.51, order.subtotal)
        self.assertEqual(0.0, order.shipping_total)
        self.assertEqual(25.51, order.total_before_tax)
        self.assertEqual(4.85, order.estimated_tax)
        self.assertEqual("Amazon Visa", order.payment_method)
        self.assertEqual("1234", order.payment_method_last_4)
        self.assertEqual("Musterstraße 1\n10115 Berlin\nDeutschland", order.recipient.address)
        item = order.items[0]
        self.assertEqual(30.36, item.price)
        self.assertEqual("Amazon.de", item.seller.name)
        self.assertEqual(date(2026, 9, 25), item.return_eligible_date)
        self.assertIsNone(item.subscription_frequency)

    def test_order_details_subscribe_and_save(self):
        order = self._details("303-3777441-6449677")

        self.assertEqual(53.32, order.grand_total)
        self.assertEqual(-5.92, order.coupon_savings)
        item = order.items[0]
        self.assertEqual("Jeden Monat", item.subscription_frequency)
        self.assertEqual(19.75, item.price)
        self.assertEqual(3, item.quantity)

    def test_order_details_refund(self):
        order = self._details("302-1027899-2645350")

        self.assertEqual(199.94, order.grand_total)
        self.assertEqual(27.1, order.refund_total)
        self.assertEqual(5, len(order.shipments))
        self.assertEqual(11, len(order.items))

    def test_order_details_gift_card(self):
        order = self._details("302-4747566-2416972")

        self.assertEqual(0.0, order.grand_total)
        self.assertEqual(39.93, order.subtotal)
        self.assertEqual(-39.93, order.gift_card)
        self.assertEqual(0.0, order.estimated_tax)
        self.assertEqual("Amazon-Geschenkgutschein", order.payment_method)
        self.assertIsNone(order.payment_method_last_4)

    def test_order_details_digital(self):
        order = self._details("D01-1151337-3109897")

        self.assertEqual(54.99, order.grand_total)
        self.assertEqual(46.21, order.subtotal)
        self.assertEqual(46.21, order.total_before_tax)
        self.assertEqual(8.78, order.estimated_tax)
        self.assertEqual("Max Mustermann", order.recipient.name)
        self.assertIsNone(order.recipient.address)
        self.assertEqual("Amazon Digital Germany GmbH", order.items[0].seller.name)

    def test_order_details_cancelled_by_seller(self):
        order = self._details("302-2246127-7908429")

        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
        self.assertEqual(date(2026, 5, 15), order.order_placed_date)
        self.assertEqual("Beispielhändler GmbH", order.items[0].seller.name)
        self.assertEqual(25.29, order.items[0].price)

    def test_order_details_cancelled_service(self):
        order = self._details("305-8658493-2112126")

        self.assertTrue(order.cancelled)
        self.assertEqual(0.0, order.grand_total)
        self.assertEqual(date(2026, 6, 8), order.order_placed_date)
        self.assertEqual("Musterstraße 1\n10115\nGermany", order.recipient.address)

    def test_order_details_with_return(self):
        order = self._details("305-6241404-1528010")

        self.assertFalse(order.cancelled)
        self.assertEqual(21.98, order.grand_total)
        self.assertEqual(21.98, order.refund_total)
        self.assertEqual("Rücksendung abgeschlossen", order.shipments[0].delivery_status)

    def test_transactions(self):
        with self.assertLogs("amazonorders.transactions", level="WARNING"):
            transactions = AmazonTransactions.parse_transactions(self._read("transactions", "transactions.html"),
                                                                 self.de_config)

        self.assertEqual(20, len(transactions))
        transaction = transactions[0]
        self.assertEqual(date(2026, 9, 7), transaction.completed_date)
        self.assertEqual(-22.73, transaction.grand_total)
        self.assertFalse(transaction.is_refund)
        self.assertEqual("305-9767931-8351126", transaction.order_number)
        self.assertEqual("Amazon Visa ****1234", transaction.payment_method)
        self.assertEqual("1234", transaction.payment_method_last_4)
        self.assertEqual("AMAZON", transaction.seller)
        self.assertEqual("https://www.amazon.de/gp/css/summary/edit.html?orderID=305-9767931-8351126",
                         transaction.order_details_link)
        self.assertEqual("Santander-Punkte", transactions[1].payment_method)
        self.assertIsNone(transactions[1].payment_method_last_4)
        self.assertEqual(date(2026, 7, 31), transactions[12].completed_date)
