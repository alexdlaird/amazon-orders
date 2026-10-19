__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import json
import logging
import os
from unittest.mock import patch

import responses

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersEntityError, AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from amazonorders.transactions import AmazonTransactions
from tests.unittestcase import UnitTestCase


class TestAmazonDe(UnitTestCase):
    """
    Parse the amazon.de pages in ``tests/resources/*/de``, requested in English, which uses British English labels.
    """

    def setUp(self):
        super().setUp()

        self.de_config = self.given_de_config()

    def test_order_history(self):
        # WHEN
        orders = self.given_order_history("2026-0")

        # THEN
        self.assertEqual(4, len(orders))
        order = orders[0]
        self.assertEqual("302-1023958-8934207", order.order_number)
        self.assertEqual(datetime.date(2026, 9, 7), order.order_placed_date)
        self.assertFalse(order.cancelled)
        self.assertEqual("Max Mustermann", order.recipient.name)
        self.assertEqual(2, len(order.shipments))
        self.assertEqual("Test Item 1", order.items[0].title)
        self.assertEqual("Delivered 01 September", orders[3].shipments[0].delivery_status)
        self.assertEqual([14.37, 0.0, 45.76, 22.52], [o.grand_total for o in orders])

    def test_order_history_older_year(self):
        # WHEN
        orders = self.given_order_history("2024-0")

        # THEN
        self.assertEqual([datetime.date(2024, 12, 8), datetime.date(2024, 12, 7), datetime.date(2024, 12, 6)],
                         [order.order_placed_date for order in orders])
        self.assertEqual([25.73, 0.0, 9.45], [order.grand_total for order in orders])

    def test_order_history_cancelled(self):
        # WHEN
        order = self.given_order_history("2026-140")[0]

        # THEN
        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
        self.assertEqual(datetime.date(2026, 3, 27), order.order_placed_date)
        self.assertEqual("Cancelled", order.shipments[0].delivery_status)

    def test_order_history_service_cancelled(self):
        # WHEN
        order = self.given_order_history("2026-60")[0]

        # THEN
        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
        self.assertEqual("Service cancelled", order.shipments[0].delivery_status)

    def test_order_history_digital(self):
        # WHEN
        order = self.given_order_history("2026-120")[0]

        # THEN
        self.assertEqual("D01-7485423-1791348", order.order_number)
        self.assertEqual(54.49, order.grand_total)
        self.assertIsNone(order.recipient)

    def test_order_details(self):
        # WHEN
        order = self.given_order_details("305-1022088-4781474")

        # THEN
        self.assertEqual(datetime.date(2026, 8, 31), order.order_placed_date)
        self.assertEqual(22.52, order.grand_total)
        self.assertEqual(19.23, order.subtotal)
        # Rendered as "Postage & Packing"
        self.assertEqual(0.0, order.shipping_total)
        # Rendered as "Estimated VAT"
        self.assertEqual(3.65, order.estimated_tax)
        self.assertEqual("Amazon Visa", order.payment_method)
        self.assertEqual("1234", order.payment_method_last_4)
        self.assertEqual("Max Mustermann", order.recipient.name)
        self.assertEqual("Musterstraße 1\n10115 Berlin\nGermany", order.recipient.address)
        self.assertEqual(22.88, order.items[0].price)
        self.assertEqual("Example Seller GmbH", order.items[0].seller.name)

    def test_order_details_promotion(self):
        # WHEN
        order = self.given_order_details("306-9272323-1520652")

        # THEN
        self.assertEqual(45.76, order.grand_total)
        self.assertEqual(-11.43, order.promotion_applied)
        self.assertEqual(9.13, order.estimated_tax)
        self.assertEqual(3, order.items[0].quantity)
        self.assertEqual("Amazon.de", order.items[0].seller.name)

    def test_order_details_multiple_shipments_and_gift_card(self):
        # WHEN
        order = self.given_order_details("302-1023958-8934207")

        # THEN
        self.assertEqual(14.37, order.grand_total)
        self.assertEqual(-13.52, order.gift_card)
        self.assertEqual(2, len(order.shipments))
        # Paid with a Gift Card and a card, the card is the payment method, like its last digits are
        self.assertEqual("Amazon Visa", order.payment_method)
        self.assertEqual("1234", order.payment_method_last_4)

    def test_order_details_refund(self):
        # WHEN
        order = self.given_order_details("305-9788051-7308445")

        # THEN
        self.assertEqual(4.84, order.refund_total)
        self.assertIsNone(order.recipient)
        self.assertEqual(datetime.date(2026, 5, 20), order.items[0].return_eligible_date)

    def test_order_details_digital(self):
        # WHEN
        order = self.given_order_details("D01-7485423-1791348")

        # THEN
        self.assertEqual(54.49, order.grand_total)
        self.assertEqual(45.79, order.subtotal)
        self.assertEqual(45.79, order.total_before_tax)
        self.assertEqual("Max Mustermann", order.recipient.name)
        self.assertIsNone(order.recipient.address)
        self.assertEqual("Amazon Digital Germany GmbH", order.items[0].seller.name)

    def test_order_details_cancelled(self):
        # WHEN
        order = self.given_order_details("305-1086546-4564812")

        # THEN
        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
        self.assertEqual(datetime.date(2026, 3, 27), order.order_placed_date)
        self.assertEqual([21.3, 17.54], [item.price for item in order.items])

    def test_order_details_service_cancelled(self):
        # WHEN
        order = self.given_order_details("305-1455896-8790496")

        # THEN
        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
        self.assertEqual("Service cancelled", order.shipments[0].delivery_status)
        # Rendered inline and separated by commas
        self.assertEqual("Musterstraße 1\n10115\nGermany", order.recipient.address)

    def test_transactions(self):
        # WHEN
        with self.assertLogs("amazonorders", level="WARNING") as cm:
            transactions = AmazonTransactions.parse_transactions(self.given_transactions_html(), self.de_config)
            # assertNoLogs() needs Python 3.10, so log a marker that has to be the only warning
            logging.getLogger("amazonorders").warning("marker")

        # THEN
        self.assertEqual(["WARNING:amazonorders:marker"], cm.output)
        self.assertEqual(20, len(transactions))
        transaction = transactions[0]
        self.assertEqual(datetime.date(2026, 9, 7), transaction.completed_date)
        self.assertEqual(-14.37, transaction.grand_total)
        self.assertFalse(transaction.is_refund)
        self.assertEqual("302-1023958-8934207", transaction.order_number)
        self.assertEqual("Amazon Visa ****1234", transaction.payment_method)
        self.assertEqual("1234", transaction.payment_method_last_4)
        self.assertEqual("AMZN Mktp DE", transaction.seller)
        self.assertEqual("https://www.amazon.de/gp/css/summary/edit.html?orderID=302-1023958-8934207",
                         transaction.order_details_link)
        self.assertEqual("Amazon Gift Card", transactions[8].payment_method)
        self.assertIsNone(transactions[8].payment_method_last_4)
        self.assertEqual("Example Bank Points", transactions[11].payment_method)
        self.assertEqual(datetime.date(2026, 8, 4), transactions[19].completed_date)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_paginated(self, mock_datetime):
        # GIVEN
        mock_datetime.date.today.return_value = datetime.date(2026, 9, 23)
        amazon_transactions, page_2 = self.given_transaction_pages()

        # WHEN
        transactions = amazon_transactions.get_transactions(days=70)

        # THEN
        # The 20 on the page, and those of the second page within the 70 day window
        self.assertEqual(datetime.date(2026, 7, 18), min(t.completed_date for t in transactions))
        self.assertEqual(datetime.date(2026, 8, 4), transactions[20].completed_date)
        self.assertEqual(1, page_2.call_count)
        request = page_2.calls[0].request
        self.assertEqual("REDACTED", request.headers["x-amzn-upx-token"])
        body = json.loads(request.body)
        self.assertEqual("GetTransactions", body["type"])
        self.assertEqual("en_GB", body["locale"])
        # amazon.de's page doesn't name its widget, so the default is sent
        self.assertEqual("ViewTransactions", body["widgetName"])
        self.assertEqual("REDACTED", body["exclusiveStartKey"])

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_last_page(self, mock_datetime):
        # GIVEN
        mock_datetime.date.today.return_value = datetime.date(2026, 9, 23)
        last_page = self.given_transactions_api_page_2().replace('"lastEvaluatedKey":"REDACTED"',
                                                                 '"other":"REDACTED"')
        amazon_transactions, page_2 = self.given_transaction_pages(last_page)

        # WHEN
        transactions = amazon_transactions.get_transactions()

        # THEN
        self.assertEqual(40, len(transactions))
        self.assertEqual(1, page_2.call_count)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_within_first_page(self, mock_datetime):
        # GIVEN
        mock_datetime.date.today.return_value = datetime.date(2026, 9, 23)
        amazon_transactions, page_2 = self.given_transaction_pages()

        # WHEN
        transactions = amazon_transactions.get_transactions(days=30)

        # THEN
        self.assertEqual(datetime.date(2026, 8, 31), transactions[-1].completed_date)
        self.assertEqual(0, page_2.call_count)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_api_changed(self, mock_datetime):
        # GIVEN
        mock_datetime.date.today.return_value = datetime.date(2026, 9, 23)
        amazon_transactions, _ = self.given_transaction_pages(
            json.dumps({"type": "GetTransactions", "responseCode": "success"}))

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            amazon_transactions.get_transactions()

        # THEN
        self.assertEqual("REDACTED", cm.exception.meta["exclusiveStartKey"])

    def test_transactions_date_that_cannot_be_parsed_raises(self):
        # GIVEN
        html = self.given_transactions_html().replace('"formattedDate":"07 Sept 2026"', '"formattedDate":"Today"', 1)

        # WHEN
        with self.assertRaises(AmazonOrdersEntityError) as cm:
            AmazonTransactions.parse_transactions(html, self.de_config)

        # THEN
        self.assertIn("'Today'", str(cm.exception))

    def given_de_config(self, **data):
        return AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "domain": "amazon.de",
            **data,
        })

    def given_resource(self, *path):
        with open(os.path.join(self.RESOURCES_DIR, *path), "r", encoding="utf-8") as f:
            return f.read()

    def given_order_history(self, name):
        return AmazonOrders.parse_order_history(self.given_resource("orders", "de", f"order-history-{name}.html"),
                                                self.de_config)

    def given_order_details(self, order_number):
        return AmazonOrders.parse_order_details(
            self.given_resource("orders", "de", f"order-details-{order_number}.html"), self.de_config)

    def given_transactions_html(self):
        return self.given_resource("transactions", "de", "transactions.html")

    def given_transactions_api_page_2(self):
        return self.given_resource("transactions", "de", "transactions-api-page-2.json")

    def given_transaction_pages(self, page_2_body=None):
        responses.add(responses.POST, self.de_config.constants.TRANSACTION_HISTORY_URL,
                      body=self.given_transactions_html(), status=200)
        page_2 = responses.add(responses.POST, self.de_config.constants.TRANSACTION_DATA_URL,
                               body=page_2_body or self.given_transactions_api_page_2(), status=200,
                               content_type="application/json")

        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.de_config)
        amazon_session.is_authenticated = True

        return AmazonTransactions(amazon_session), page_2
