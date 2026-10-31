__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import os

from bs4 import BeautifulSoup

from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersError
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
        self.assertEqual(parsable.to_currency("52,34\u00a0zł"), 52.34)
        self.assertEqual(parsable.to_currency("\u20ba1.299,00"), 1299.0)
        self.assertIsNone(parsable.to_currency("not currency"))

    def test_safe_parse_degrades_json_shaped_failures(self):
        # GIVEN
        parsable = Parsable(BeautifulSoup("<html />", self.test_config.bs4_parser), self.test_config)

        def _parse_deep():
            return json.loads("[" * 100000 + "]" * 100000)

        def _parse_wrong_shape():
            return BeautifulSoup(json.loads("[[]]"), self.test_config.bs4_parser)

        # WHEN
        with self.assertLogs("amazonorders.entity.parsable", level="WARNING") as logs:
            deep = parsable.safe_parse(_parse_deep)
            wrong_shape = parsable.safe_parse(_parse_wrong_shape)

        # THEN
        self.assertIsNone(deep)
        self.assertIsNone(wrong_shape)
        self.assertEqual(2, len(logs.records))
        self.assertIn("`deep` could not be parsed", logs.output[0])
        self.assertIn("`wrong_shape` could not be parsed", logs.output[1])
        self.assertEqual(["deep", "wrong_shape"], parsable.parse_failures)

    def test_safe_simple_parse_failure_names_the_selector(self):
        # GIVEN
        parsable = Parsable(BeautifulSoup("<span class='total'>$1.00</span>", self.test_config.bs4_parser),
                            self.test_config)

        class Unparseable:
            def __init__(self, tag, config):
                raise ValueError("unexpected markup")

        # WHEN
        with self.assertLogs("amazonorders.entity.parsable", level="WARNING") as logs:
            value = parsable.safe_simple_parse(selector=["span.missing", "span.total"], wrap_tag=Unparseable)

        # THEN
        self.assertIsNone(value)
        self.assertIn("`span.missing, span.total` could not be parsed", logs.output[0])
        self.assertEqual(["span.missing, span.total"], parsable.parse_failures)

    def test_parse_failure_listed_once_until_the_field_parses(self):
        # GIVEN
        parsable = Parsable(BeautifulSoup("<html />", self.test_config.bs4_parser), self.test_config)
        results = [ValueError("unexpected markup"), ValueError("unexpected markup"), 1.0]

        def _parse_total():
            result = results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        # WHEN
        with self.assertLogs("amazonorders.entity.parsable", level="WARNING"):
            parsable.safe_parse(_parse_total)
            parsable.safe_parse(_parse_total)
        failures = list(parsable.parse_failures)
        total = parsable.safe_parse(_parse_total)

        # THEN
        self.assertEqual(["total"], failures)
        self.assertEqual(1.0, total)
        self.assertEqual([], parsable.parse_failures)

    def test_safe_parse_propagates_library_errors(self):
        # GIVEN
        parsable = Parsable(BeautifulSoup("<html />", self.test_config.bs4_parser), self.test_config)

        def _parse_required():
            raise AmazonOrdersError("required field did not populate")

        # WHEN / THEN
        with self.assertRaises(AmazonOrdersError):
            parsable.safe_parse(_parse_required)

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
            order = AmazonOrders.parse_orders(f.read(), self.test_config)[3]

        # WHEN
        serialized = order.to_dict()

        # THEN
        self.assertNotIn("parsed", serialized)
        self.assertNotIn("config", serialized)
        self.assertNotIn("parse_failures", serialized)
        self.assertEqual("112-0399923-3070642", serialized["order_number"])
        self.assertEqual(json.loads(json.dumps(serialized)), serialized)

    def test_to_dict_converts_dates_and_nested_entities(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r",
                  encoding="utf-8") as f:
            order = AmazonOrders.parse_orders(f.read(), self.test_config)[3]

        # WHEN
        serialized = order.to_dict()

        # THEN
        self.assertEqual("2018-12-21", serialized["order_placed_date"])
        self.assertIsInstance(serialized["recipient"], dict)
        self.assertEqual("Alex Laird", serialized["recipient"]["name"])
        self.assertIsInstance(serialized["items"], list)
        self.assertIsInstance(serialized["items"][0], dict)
        self.assertIsInstance(serialized["shipments"][0]["items"][0]["title"], str)

    def test_to_dict_exclude_none_drops_only_none(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r",
                  encoding="utf-8") as f:
            order = AmazonOrders.parse_orders(f.read(), self.test_config)[3]
        order.subscription_discount = None
        order.free_shipping = 0.0
        order.full_details = False
        order.shipments[0].items[0].price = None

        # WHEN
        serialized = order.to_dict(exclude_none=True)

        # THEN
        self.assertNotIn("subscription_discount", serialized)
        self.assertEqual(0.0, serialized["free_shipping"])
        self.assertFalse(serialized["full_details"])
        self.assertNotIn("price", serialized["shipments"][0]["items"][0])
        self.assertEqual(order.to_dict()["order_number"], serialized["order_number"])
        self.assert_no_none_values(serialized)

    def test_to_dict_keeps_none_by_default(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r",
                  encoding="utf-8") as f:
            order = AmazonOrders.parse_orders(f.read(), self.test_config)[3]
        order.subscription_discount = None

        # WHEN
        serialized = order.to_dict()

        # THEN
        self.assertIn("subscription_discount", serialized)
        self.assertIsNone(serialized["subscription_discount"])

    def test_to_dict_exclude_none_keeps_empty_lists(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r",
                  encoding="utf-8") as f:
            order = AmazonOrders.parse_orders(f.read(), self.test_config)[3]
        order.items = []

        # WHEN
        serialized = order.to_dict(exclude_none=True)

        # THEN
        self.assertEqual([], serialized["items"])

    def assert_no_none_values(self, value):
        self.assertIsNotNone(value)
        children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
        for child in children:
            self.assert_no_none_values(child)

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
