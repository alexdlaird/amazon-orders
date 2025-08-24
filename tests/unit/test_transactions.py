__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
from unittest.mock import patch

import responses
from bs4 import BeautifulSoup

from amazonorders.exception import AmazonOrdersError, AmazonOrdersAuthRedirectError
from amazonorders.session import AmazonSession
from amazonorders.transactions import AmazonTransactions, _parse_transaction_form_tag
from tests.unittestcase import UnitTestCase


class TestTransactions(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com",
                                            "some-password",
                                            config=self.test_config)

        self.amazon_transactions = AmazonTransactions(self.amazon_session)

    def test_get_transactions_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_transactions.get_transactions()

        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    @responses.activate
    def test_get_transactions_session_expires(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        auth_redirect_response = self.given_authenticated_url_renders_login(method=responses.POST)
        signout_response = self.given_logout_response_success()

        # WHEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            self.amazon_transactions.get_transactions(keep_paging=False)

        self.assertIn("Amazon redirected to login.", str(cm.exception))
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(1, auth_redirect_response.call_count)
        self.assertEqual(1, signout_response.call_count)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2024, 10, 11)
        days = 1
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "get-transactions-snippet.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days, keep_paging=False)

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
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_transactions_errors_with_meta(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = responses.add(
            responses.POST,
            f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
            status=503,
        )
        next_page_data = {"some": "meta"}

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_transactions.get_transactions(next_page_data=next_page_data, keep_paging=False)

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertEqual(cm.exception.meta, next_page_data)

    @responses.activate
    def test_get_transactions_invalid_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "500.html"), "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_transactions.get_transactions(keep_paging=False)

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertIn("Could not parse Transaction history.", str(cm.exception))

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_refunded_empty_order_link(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2025, 2, 28)
        days = 30
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-refunded.html"),
                  "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days, keep_paging=False)

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
        self.assertEqual(1, resp.call_count)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_paginated(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2025, 5, 27)
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-with-next-page.html"),
                  "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-in-progress.html"),
                  "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions()

        # THEN
        self.assertEqual(40, len(transactions))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_with_pending(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2025, 2, 13)
        days = 30
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-in-progress.html"),
                  "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days, keep_paging=False)

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
        self.assertEqual(1, resp.call_count)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_get_transactions_grand_total_blank(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2025, 2, 19)
        days = 30
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-grand-total-blank.html"),
                  "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days, keep_paging=False)

        # THEN
        self.assertEqual(19, len(transactions))
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_transactions_zero_transactions(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transactions-zero-transactions.html"),
                  "r",
                  encoding="utf-8") as f:
            responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(keep_paging=False)

        # THEN
        self.assertEqual(0, len(transactions))

    def test_parse_transaction_form_tag(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transaction-form-tag.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)
            form_tag = parsed.select_one("form")

        # WHEN
        transactions, next_page_data = _parse_transaction_form_tag(
            form_tag, self.test_config
        )

        # THEN
        self.assertEqual(len(transactions), 2)
        self.assertEqual(
            next_page_data,
            {
                "ppw-widgetState": "the-ppw-widgetState",
                "ie": "UTF-8",
                'ppw-widgetEvent:DefaultNextPageNavigationEvent:{"nextPageKey":"key"}': "",
            },
        )
