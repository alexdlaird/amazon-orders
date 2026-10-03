__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import os

from bs4 import BeautifulSoup

from amazonorders.entity.parsable import Parsable
from amazonorders.orders import AmazonOrders
from amazonorders.transactions import AmazonTransactions
from tests.unittestcase import UnitTestCase


class TestItem(UnitTestCase):
    def test_to_currency(self):
        # GIVEN
        html = "<html />"
        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        # WHEN
        parsable = Parsable(parsed, self.test_config)

        # THEN
        self.assertIsNone(parsable.to_currency(None))
        self.assertIsNone(parsable.to_currency(""))
        self.assertEqual(parsable.to_currency(1234.99), 1234.99)
        self.assertEqual(parsable.to_currency(1234), 1234)
        self.assertEqual(parsable.to_currency("1,234.99"), 1234.99)
        self.assertEqual(parsable.to_currency("$1,234.99"), 1234.99)
        self.assertEqual(parsable.to_currency("¥1,980"), 1980)
        self.assertEqual(parsable.to_currency("￥1,980"), 1980)
        self.assertEqual(parsable.to_currency("-¥1,980"), -1980)
        self.assertEqual(parsable.to_currency("(¥1,980)"), -1980)
        self.assertIsNone(parsable.to_currency("not currency"))

    def test_to_currency_decimal_comma(self):
        # GIVEN
        parsable = Parsable(BeautifulSoup("<html />", self.test_config.bs4_parser), self.test_config)

        # WHEN / THEN
        self.assertEqual(parsable.to_currency("12,99 €"), 12.99)
        self.assertEqual(parsable.to_currency("25,29€"), 25.29)
        self.assertEqual(parsable.to_currency("€ 0,50"), 0.50)
        self.assertEqual(parsable.to_currency("\u221239,93 €"), -39.93)

    def test_to_currency_dot_thousands_with_decimal_comma(self):
        # GIVEN
        parsable = Parsable(BeautifulSoup("<html />", self.test_config.bs4_parser), self.test_config)

        # WHEN / THEN
        self.assertEqual(parsable.to_currency("1.234,56 €"), 1234.56)
        self.assertEqual(parsable.to_currency("1.234,56\u00a0€"), 1234.56)
        self.assertEqual(parsable.to_currency("EUR 1.234.567,89"), 1234567.89)
        self.assertEqual(parsable.to_currency("(1.234,50 €)"), -1234.50)

    def test_to_currency_space_and_apostrophe_thousands(self):
        # GIVEN
        parsable = Parsable(BeautifulSoup("<html />", self.test_config.bs4_parser), self.test_config)

        # WHEN / THEN
        self.assertEqual(parsable.to_currency("1 234,56 €"), 1234.56)
        self.assertEqual(parsable.to_currency("1\u202f234,56 €"), 1234.56)
        self.assertEqual(parsable.to_currency("CHF 1'234.50"), 1234.50)

    def test_to_currency_three_trailing_digits_are_thousands(self):
        # GIVEN
        parsable = Parsable(BeautifulSoup("<html />", self.test_config.bs4_parser), self.test_config)

        # WHEN / THEN
        self.assertEqual(parsable.to_currency("$1,234"), 1234)
        self.assertEqual(parsable.to_currency("1.234 €"), 1234)
        self.assertEqual(parsable.to_currency("-€7.63"), -7.63)

    def test_to_dict_excludes_unserializable_fields(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r",
                  encoding="utf-8") as f:
            order = AmazonOrders.parse_order_history(f.read(), self.test_config)[3]

        # WHEN
        serialized = order.to_dict()

        # THEN
        self.assertNotIn("parsed", serialized)
        self.assertNotIn("config", serialized)
        self.assertEqual("112-0399923-3070642", serialized["order_number"])
        self.assertEqual(json.loads(json.dumps(serialized)), serialized)

    def test_to_dict_converts_dates_and_nested_entities(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r",
                  encoding="utf-8") as f:
            order = AmazonOrders.parse_order_history(f.read(), self.test_config)[3]

        # WHEN
        serialized = order.to_dict()

        # THEN
        self.assertEqual("2018-12-21", serialized["order_placed_date"])
        self.assertIsInstance(serialized["recipient"], dict)
        self.assertEqual("Alex Laird", serialized["recipient"]["name"])
        self.assertIsInstance(serialized["items"], list)
        self.assertIsInstance(serialized["items"][0], dict)
        self.assertIsInstance(serialized["shipments"][0]["items"][0]["title"], str)

    def test_to_dict_on_transaction(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "get-transactions-snippet.html"), "r",
                  encoding="utf-8") as f:
            transaction = AmazonTransactions.parse_transactions(f.read(), self.test_config)[0]

        # WHEN
        serialized = transaction.to_dict()

        # THEN
        self.assertNotIn("parsed", serialized)
        self.assertNotIn("config", serialized)
        self.assertEqual(json.loads(json.dumps(serialized)), serialized)
        self.assertIsInstance(serialized["completed_date"], str)
