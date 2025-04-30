__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from datetime import date

from bs4 import BeautifulSoup

from amazonorders.entity.transaction import Transaction
from tests.unittestcase import UnitTestCase


class TestTransaction(UnitTestCase):
    def test_parse(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transaction-snippet.html"), "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        transaction = Transaction(parsed, self.test_config, date(2024, 1, 1))

        # THEN
        self.assertEqual(transaction.completed_date, date(2024, 1, 1))
        self.assertEqual(transaction.payment_method, "My Payment Method")
        self.assertEqual(transaction.order_number, "123-4567890-1234567")
        self.assertEqual(transaction.order_details_link,
                         "https://www.amazon.com/gp/css/summary/edit.html?orderID=123-4567890-1234567")  # noqa
        self.assertEqual(transaction.seller, "AMZN Mktp COM")
        self.assertEqual(transaction.grand_total, -12.34)
        self.assertEqual(transaction.is_refund, False)
        self.assertEqual(str(transaction), "Transaction 2024-01-01: Order #123-4567890-1234567, Grand Total: -12.34")
        self.assertEqual(
            repr(transaction), '<Transaction 2024-01-01: "Order #123-4567890-1234567, Grand Total: -12.34">'
        )

    def test_parse_refund(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transaction-refund-snippet.html"), "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        transaction = Transaction(parsed, self.test_config, date(2024, 1, 1))

        # THEN
        self.assertEqual(transaction.completed_date, date(2024, 1, 1))
        self.assertEqual(transaction.payment_method, "My Payment Method")
        self.assertEqual(transaction.order_number, "123-4567890-1234567")
        self.assertEqual(transaction.order_details_link,
                         "https://www.amazon.com/gp/css/summary/edit.html?orderID=123-4567890-1234567")  # noqa
        self.assertEqual(transaction.seller, "AMZN Mktp COM")
        self.assertEqual(transaction.grand_total, 12.34)
        self.assertEqual(transaction.is_refund, True)
        self.assertEqual(str(transaction), "Transaction 2024-01-01: Order #123-4567890-1234567, Grand Total: 12.34")
        self.assertEqual(
            repr(transaction), '<Transaction 2024-01-01: "Order #123-4567890-1234567, Grand Total: 12.34">'
        )
