__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import json
import os
from datetime import date
from unittest.mock import patch

import responses
from bs4 import BeautifulSoup

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.item import Item
from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders, _parse_order_count
from amazonorders.session import AmazonSession
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

    def test_item_return_eligible_date_next_to_replacement_date(self):
        for rows in (["Artikel ersetzen: Möglich bis zum 6. September 2027",
                      "Zeitraum für Rückgabe endet am 18. September 2026"],
                     ["Zeitraum für Rückgabe endet am 18. September 2026",
                      "Artikel ersetzen: Möglich bis zum 6. September 2027"]):
            html = ("<div><div data-component='itemTitle'>Testartikel</div>"
                    "<div data-component='itemReturnEligibility'>"
                    + "".join(f"<div class='a-row'>{row}</div>" for row in rows)
                    + "</div></div>")

            item = Item(BeautifulSoup(html, "html.parser"), self.de_config)

            self.assertEqual(date(2026, 9, 18), item.return_eligible_date)

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
        with self.assertNoLogs("amazonorders.transactions", level="WARNING"):
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

    def _mock_transactions(self):
        responses.add(responses.POST, self.de_config.constants.TRANSACTION_HISTORY_URL,
                      body=self._read("transactions", "transactions.html"), status=200)
        page_2 = responses.add(responses.POST, self.de_config.constants.TRANSACTION_HISTORY_API_URL,
                               body=self._read("transactions", "transactions-api-page-2.json"), status=200,
                               content_type="application/json")
        page_3 = responses.add(responses.POST, self.de_config.constants.TRANSACTION_HISTORY_API_URL,
                               body=self._read("transactions", "transactions-api-page-3.json"), status=200,
                               content_type="application/json")
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.de_config)
        amazon_session.is_authenticated = True

        return AmazonTransactions(amazon_session), page_2, page_3

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_paginated(self, mock_today):
        mock_today.date.today.return_value = date(2026, 9, 23)
        amazon_transactions, page_2, page_3 = self._mock_transactions()

        transactions = amazon_transactions.get_transactions()

        # 20 on the page, 3 from the second page, and 1 from the third page before the 365 day window ends
        self.assertEqual(24, len(transactions))
        self.assertEqual(date(2026, 7, 15), transactions[20].completed_date)
        self.assertEqual(date(2026, 6, 20), transactions[23].completed_date)
        self.assertEqual(1, page_2.call_count)
        self.assertEqual(1, page_3.call_count)
        request = page_2.calls[0].request
        self.assertEqual("REDACTED", request.headers["x-amzn-upx-token"])
        body = json.loads(request.body)
        self.assertEqual("GetTransactions", body["type"])
        self.assertEqual("de_DE", body["locale"])
        self.assertEqual("ViewTransactions", body["widgetName"])
        self.assertEqual("REDACTED", body["exclusiveStartKey"])
        self.assertEqual("REDACTED-PAGE-3", json.loads(page_3.calls[0].request.body)["exclusiveStartKey"])

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_within_first_page(self, mock_today):
        mock_today.date.today.return_value = date(2026, 9, 23)
        amazon_transactions, page_2, page_3 = self._mock_transactions()

        transactions = amazon_transactions.get_transactions(days=60)

        self.assertEqual(16, len(transactions))
        self.assertEqual(date(2026, 7, 27), transactions[-1].completed_date)
        self.assertEqual(0, page_2.call_count)
        self.assertEqual(0, page_3.call_count)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_single_page(self, mock_today):
        mock_today.date.today.return_value = date(2026, 9, 23)
        amazon_transactions, page_2, page_3 = self._mock_transactions()

        transactions = amazon_transactions.get_transactions(keep_paging=False)

        self.assertEqual(20, len(transactions))
        self.assertEqual(0, page_2.call_count)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_api_changed(self, mock_today):
        mock_today.date.today.return_value = date(2026, 9, 23)
        responses.add(responses.POST, self.de_config.constants.TRANSACTION_HISTORY_URL,
                      body=self._read("transactions", "transactions.html"), status=200)
        responses.add(responses.POST, self.de_config.constants.TRANSACTION_HISTORY_API_URL,
                      json={"type": "GetTransactions", "responseCode": "success"}, status=200)
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.de_config)
        amazon_session.is_authenticated = True

        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonTransactions(amazon_session).get_transactions()

        self.assertEqual("REDACTED", cm.exception.meta["request"]["exclusiveStartKey"])
