__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
from unittest.mock import Mock, patch

import responses
from bs4 import BeautifulSoup

from amazonorders.session import AmazonSession
from amazonorders.transactions import AmazonTransactions, _parse_transaction_form_tag
from tests.unittestcase import UnitTestCase


class TestTransactions(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession(
            "some-username", "some-password", config=self.test_config
        )

        self.amazon_transactions = AmazonTransactions(self.amazon_session)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2024, 10, 11)
        days = 1
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "get-transactions-snippet.html"),
                  "r",
                  encoding="utf-8") as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.TRANSACTION_HISTORY_LANDING_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days)

        # THEN
        self.assertEqual(1, len(transactions))
        transaction = transactions[0]
        self.assertEqual(transaction.completed_date, datetime.date(2024, 10, 11))
        self.assertEqual(transaction.payment_method, "Visa ****1234")
        self.assertEqual(transaction.grand_total, -45.19)
        self.assertFalse(transaction.is_refund)
        self.assertEqual(transaction.order_number, "123-4567890-1234567")
        self.assertEqual(transaction.order_details_link,
                         "https://www.amazon.ca/gp/css/summary/edit.html?orderID=123-4567890-1234567")
        self.assertEqual(transaction.seller, "AMZN Mktp CA")

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_refunded_empty_order_link(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2025, 2, 28)
        days = 30
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-refunded.html"),
                  "r",
                  encoding="utf-8") as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.TRANSACTION_HISTORY_LANDING_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days)

        # THEN
        self.assertEqual(19, len(transactions))
        transaction = transactions[0]
        self.assertEqual(transaction.completed_date, datetime.date(2025, 2, 28))
        self.assertEqual(transaction.payment_method, "WELLS FARGO BANK NATIONAL ASSOCIATION ***863")
        self.assertEqual(transaction.grand_total, 55.96)
        self.assertTrue(transaction.is_refund)
        self.assertEqual(transaction.order_number, "0000000019080621061")
        self.assertEqual(transaction.order_details_link,
                         "https://www.amazon.com/gp/your-account/order-details?orderID=0000000019080621061")
        self.assertIsNone(transaction.seller)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_with_pending(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2025, 2, 13)
        days = 30
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-in-progress.html"),
                  "r",
                  encoding="utf-8") as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.TRANSACTION_HISTORY_LANDING_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days)

        # THEN
        self.assertEqual(20, len(transactions))
        transaction = transactions[0]
        self.assertEqual(transaction.completed_date, datetime.date(2025, 2, 12))
        self.assertEqual(transaction.payment_method, "Prime Visa ****1111")
        self.assertEqual(transaction.grand_total, -26.29)
        self.assertFalse(transaction.is_refund)
        self.assertEqual(transaction.order_number, "234-8832881-7100260")
        self.assertEqual(transaction.order_details_link,
                         "https://www.amazon.com/gp/css/summary/edit.html?orderID=234-8832881-7100260")
        self.assertEqual(transaction.seller, "AMZN Mktp US")
        transaction = transactions[1]
        self.assertEqual(transaction.completed_date, datetime.date(2025, 2, 7))
        self.assertEqual(transaction.payment_method, "Prime Visa ****1111")
        self.assertEqual(transaction.grand_total, 43.94)
        self.assertTrue(transaction.is_refund)
        self.assertEqual(transaction.order_number, "234-3017692-4601031")
        self.assertEqual(transaction.order_details_link,
                         "https://www.amazon.com/gp/css/summary/edit.html?orderID=234-3017692-4601031")
        self.assertEqual(transaction.seller, "AMZN Mktp US")

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_grand_total_blank(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2025, 2, 19)
        days = 30
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-grand-total-blank.html"),
                  "r",
                  encoding="utf-8") as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.TRANSACTION_HISTORY_LANDING_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days)

        # THEN
        self.assertEqual(19, len(transactions))

    def test_parse_transaction_form_tag(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transaction-form-tag.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)
            form_tag = parsed.select_one("form")

        # WHEN
        transactions, next_page_url, next_page_data = _parse_transaction_form_tag(
            form_tag, self.test_config
        )

        # THEN
        self.assertEqual(len(transactions), 2)
        self.assertEqual(
            next_page_url, "https://www.amazon.com:443/cpe/yourpayments/transactions"
        )
        self.assertEqual(
            next_page_data,
            {
                "ppw-widgetState": "the-ppw-widgetState",
                "ie": "UTF-8",
                'ppw-widgetEvent:DefaultNextPageNavigationEvent:{"nextPageKey":"key"}': "",
            },
        )
