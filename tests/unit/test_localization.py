__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import ast
import datetime
import glob
import os
import re
from unittest.mock import patch

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.selectors import Selectors
from amazonorders.transactions import AmazonTransactions
from tests.unit import example_language_package
from tests.unittestcase import UnitTestCase

_PACKAGE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "amazonorders"))
_PARSING_MODULES = (sorted(glob.glob(os.path.join(_PACKAGE_DIR, "entity", "*.py"))) +
                    [os.path.join(_PACKAGE_DIR, name) for name in ("orders.py", "transactions.py", "session.py",
                                                                   "forms.py", "gift_cards.py")])
_MESSAGE_CALLS = {"debug", "info", "warning", "error", "exception", "critical", "echo", "prompt", "input"}
_DISPLAY_METHODS = {"__repr__", "__str__"}
_PLUMBING_LITERALS = {
    "", "\n", " ", " - (redirected) ", "&", "&startIndex=", "']", ".", "/",
    "/(?:dp|gp/product|product)/([A-Z0-9]{10})(?:[/?]|$)", ": ", "://", "=", "?", "?orderID=", "?transactionTag=",
    "AMAZON_OTP_SECRET_KEY", "AMAZON_PASSWORD", "AMAZON_USERNAME", "GET", "POST", "\\*+(\\d+)$", "\\*\\s*(\\d+)",
    "^\\s*{count}\\s*$", "_parse_", "aa-challenge-page-captcha-container", "action", "alt", "choices", "config",
    "cvf_captcha_input", "data", "data-a-popover", "deviceId", "domain", "email", "field-keywords", "headers",
    "href", "http", "https://", "ie", "img", "index", "inlineContent", "input", "input[name='", "last30", "method",
    "months-3", "name", "nav-item-signout", "next_page_url", "not solved", "otpCode", "otpDeviceContext", "params",
    "parsed", "password", "ppw-widgetState", "r", "rememberDevice", "rememberMe", "simple_parse", "src", "timeout",
    "true", "utf-8", "value", "w", "year-", "{page_name}_{index}.html", "{url}/{path}",
    "{url}?{query_param}={filter_value}{optional_order_filter}{optional_start_index}", "{}",
}

_ENGLISH_TO_LOREM_MONTHS = {
    "January": "Lorem", "February": "Ipsum", "March": "Dolor", "April": "Amet", "May": "Elit", "June": "Magna",
    "July": "Enim", "August": "Minim", "September": "Quis", "October": "Nisi", "November": "Duis",
    "December": "Irure", "Jan": "Lorem", "Feb": "Ipsum", "Mar": "Dolor", "Apr": "Amet", "Jun": "Magna",
    "Jul": "Enim", "Aug": "Minim", "Sep": "Quis", "Oct": "Nisi", "Nov": "Duis", "Dec": "Irure",
}
_CONSTANTS_HOOKS = ["SIGNED_OUT_TEXT", "JS_ROBOT_TEXT_REGEX", "CURRENCY_FREE_TEXT", "ORDER_NUMBER_REGEX",
                    "parse_currency", "parse_date", "parse_count", "parse_order_number"]


class TestLocalization(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.example_config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "language_package": "tests.unit.example_language_package",
        })

    def test_parsing_modules_have_no_page_text_literals(self):
        # WHEN
        literals = self._page_text_literals()

        # THEN
        self.assertEqual([], literals,
                         "Page text belongs on Selectors or Constants, so a language package can override it. "
                         "Move these, or add genuine plumbing (field names, attributes, URL parts) to "
                         "_PLUMBING_LITERALS.")

    def test_example_language_package_overrides_every_hook(self):
        # GIVEN
        page_text_hooks = {name for name in dir(Selectors) if re.search(r"_(LABELS|PREFIX|SUFFIX|TEXT|REGEX)$", name)}

        # WHEN
        overridden = {name for name in vars(example_language_package.Selectors) if name.isupper()}

        # THEN
        self.assertEqual(page_text_hooks, overridden)
        for name in _CONSTANTS_HOOKS:
            self.assertIn(name, vars(example_language_package.Constants))
        for name in ["get_page", "parse_page"]:
            self.assertIn(name, vars(example_language_package.TransactionsPage))

    def test_example_language_package_parses_translated_order_details(self):
        # GIVEN
        html = self.given_resource("orders", "order-subscriptions-and-reward-points-snippet.html")
        lorem_html = self._translate(html, {
            "Item(s) Subtotal:": "Consectetur:",
            "Shipping &amp; Handling:": "Adipiscing:",
            "Free Shipping:": "Eiusmod:",
            "Your Coupon Savings:": "Tempor:",
            "Subscription saving:": "Incididunt:",
            "Total before tax:": "Labore:",
            "Estimated tax to be collected:": "Aliqua:",
            "Rewards Points:": "Veniam:",
            "Grand Total:": "Nostrud:",
            "Refund Total": "Exercitation",
            "Sold by:": "Ullamco:",
            "Return window closed on": "Commodo consequat",
            "ending in": "mollit anim",
        })

        # WHEN
        example_constants_class = type(self.example_config.constants)
        with patch.object(example_constants_class, "parse_count", autospec=True,
                          side_effect=example_constants_class.parse_count) as parse_count:
            order = AmazonOrders.parse_order_details(lorem_html, self.example_config)

        # THEN
        expected = AmazonOrders.parse_order_details(html, self.test_config)
        self.assertEqual(expected.to_dict(), order.to_dict())
        self.assertEqual(-5.98, order.reward_points)
        self.assertEqual(-2.99, order.free_shipping)
        self.assertEqual(datetime.date(2025, 3, 15), order.order_placed_date)
        self.assertEqual(datetime.date(2025, 4, 14), order.items[0].return_eligible_date)
        self.assertEqual("LUMlNlZE", order.items[0].seller.name)
        self.assertTrue(parse_count.called)
        with self.assertRaises(AmazonOrdersError):
            AmazonOrders.parse_order_details(lorem_html, self.test_config)

    def test_example_language_package_parses_translated_order_history(self):
        # GIVEN
        html = self.given_resource("orders", "order-history-2018-0.html")
        lorem_html = re.sub(r"^(\s*)Total$", r"\1Officia", html, flags=re.MULTILINE)
        lorem_html = re.sub(r"^(\s*)Order #$", r"\1Deserunt", lorem_html, flags=re.MULTILINE)
        lorem_html = self._translate(lorem_html, {"Return window closed on": "Commodo consequat"})

        # WHEN
        orders = AmazonOrders.parse_order_history(lorem_html, self.example_config)

        # THEN
        expected = AmazonOrders.parse_order_history(html, self.test_config)
        self.assertEqual([o.to_dict() for o in expected], [o.to_dict() for o in orders])
        self.assertEqual(71.90, orders[0].grand_total)
        self.assertEqual(datetime.date(2018, 12, 30), orders[0].order_placed_date)

    def test_example_language_package_strips_translated_grand_total_prefix(self):
        # GIVEN
        html = self.given_resource("orders", "order-history-2024-0.html")
        lorem_html = re.sub(r"^(\s*)Total$", r"\1Officia", html.replace(">Total</span>", ">Officia</span>"),
                            flags=re.MULTILINE)
        example_constants_class = type(self.example_config.constants)

        # WHEN
        with patch.object(example_constants_class, "parse_currency", autospec=True,
                          side_effect=example_constants_class.parse_currency) as parse_currency:
            orders = AmazonOrders.parse_order_history(lorem_html, self.example_config)

        # THEN
        expected = AmazonOrders.parse_order_history(html, self.test_config)
        self.assertEqual([o.grand_total for o in expected], [o.grand_total for o in orders])
        self.assertFalse([call for call in parse_currency.call_args_list if "officia" in str(call.args[1]).lower()])

    def test_example_language_package_parses_translated_transactions(self):
        # GIVEN
        html = self.given_resource("transactions", "get-transactions-snippet.html")
        lorem_html = self._translate(html, {"Order #": "Deserunt "})

        # WHEN
        transactions = AmazonTransactions.parse_transactions(lorem_html, self.example_config)

        # THEN
        expected = AmazonTransactions.parse_transactions(html, self.test_config)
        self.assertEqual([t.to_dict() for t in expected], [t.to_dict() for t in transactions])
        self.assertEqual("123-4567890-1234567", transactions[0].order_number)
        self.assertEqual(-45.19, transactions[0].grand_total)
        self.assertEqual(datetime.date(2024, 10, 11), transactions[0].completed_date)

    def test_example_language_package_parses_translated_empty_transactions(self):
        # GIVEN
        html = self.given_resource("transactions", "transactions-zero-transactions.html")
        lorem_html = html.replace("You don&#39;t have any transactions yet.", "Lorem laborum.")

        # WHEN
        transactions = AmazonTransactions.parse_transactions(lorem_html, self.example_config)

        # THEN
        self.assertEqual([], transactions)

    def test_example_language_package_parses_translated_cancelled_orders(self):
        # GIVEN
        history_html = self.given_resource("orders", "order-history-canceled-order.html")
        details_html = self.given_resource("orders", "order-details-cancelled-by-seller.html")
        phrases = {">Cancelled<": ">Velit<", "was cancelled": "was velit"}

        # WHEN
        orders = AmazonOrders.parse_order_history(self._translate(history_html, phrases), self.example_config)
        order = AmazonOrders.parse_order_details(self._translate(details_html, phrases), self.example_config)

        # THEN
        expected_orders = AmazonOrders.parse_order_history(history_html, self.test_config)
        self.assertEqual([o.cancelled for o in expected_orders], [o.cancelled for o in orders])
        self.assertTrue(orders[0].cancelled)
        self.assertTrue(order.cancelled)
        with self.assertRaises(AmazonOrdersError):
            AmazonOrders.parse_order_details(self._translate(details_html, phrases), self.test_config)

    def test_example_language_package_parses_translated_store_and_whole_foods_orders(self):
        # GIVEN
        store_html = self.given_resource("orders", "order-history-amazon-store.html")
        whole_foods_html = self.given_resource("orders", "order-history-wholefoods.html")

        # WHEN
        store_orders = AmazonOrders.parse_order_history(
            store_html.replace("Purchased at Amazon", "Sint culpa"), self.example_config)
        whole_foods_orders = AmazonOrders.parse_order_history(
            whole_foods_html.replace("Whole Foods Market", "Anim id est"), self.example_config)

        # THEN
        expected_store = AmazonOrders.parse_order_history(store_html, self.test_config)
        expected_whole_foods = AmazonOrders.parse_order_history(whole_foods_html, self.test_config)
        self.assertEqual([len(o.items) for o in expected_store], [len(o.items) for o in store_orders])
        self.assertEqual([o.is_whole_foods for o in expected_whole_foods],
                         [o.is_whole_foods for o in whole_foods_orders])
        self.assertTrue(any(o.is_whole_foods for o in whole_foods_orders))

    def test_example_language_package_overrides_currency_free_text(self):
        # WHEN / THEN
        self.assertEqual(0.0, self.example_config.constants.parse_currency("Nulla"))
        self.assertIsNone(self.test_config.constants.parse_currency("Nulla"))
        self.assertEqual(0.0, self.test_config.constants.parse_currency("FREE"))

    def given_resource(self, *path):
        with open(os.path.join(self.RESOURCES_DIR, *path), "r", encoding="utf-8") as f:
            return f.read()

    def _to_lorem_dates(self, html):
        months = "|".join(sorted(_ENGLISH_TO_LOREM_MONTHS, key=len, reverse=True))
        return re.sub(r"\b(" + months + r")\.? (\d{1,2}), (\d{4})",
                      lambda m: f"{m.group(2)} {_ENGLISH_TO_LOREM_MONTHS[m.group(1)]} {m.group(3)}", html)

    def _to_trailing_minus_amounts(self, html):
        return re.sub(r"-((?:[A-Z]{1,3})?\$[\d,]+\.\d{2})", r"\1-", html)

    def _translate(self, html, phrases):
        for english, lorem in phrases.items():
            html = html.replace(english, lorem)
        return self._to_trailing_minus_amounts(self._to_lorem_dates(html))

    def _parents(self, tree):
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

    def _is_message_context(self, node):
        while node is not None:
            parent = getattr(node, "parent", None)
            if isinstance(node, ast.Raise):
                return True
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                if name in _MESSAGE_CALLS or name.endswith(("Error", "Exception")) or name == "TypeVar":
                    return True
            if isinstance(node, ast.Assign) and any("msg" in getattr(target, "id", "") or
                                                    getattr(target, "id", "").startswith("__")
                                                    for target in node.targets):
                return True
            if isinstance(node, ast.AugAssign) and "msg" in getattr(node.target, "id", ""):
                return True
            if isinstance(node, ast.FunctionDef) and node.name in _DISPLAY_METHODS:
                return True
            if isinstance(parent, ast.Expr) and isinstance(node, ast.Constant):
                return True
            if isinstance(parent, (ast.arg, ast.AnnAssign)) and node is parent.annotation:
                return True
            if isinstance(parent, ast.FunctionDef) and node is parent.returns:
                return True
            node = parent
        return False

    def _page_text_literals(self):
        found = []
        for path in _PARSING_MODULES:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            self._parents(tree)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str) and
                        node.value not in _PLUMBING_LITERALS and not self._is_message_context(node)):
                    found.append(f"{os.path.relpath(path, _PACKAGE_DIR)}:{node.lineno}: {node.value!r}")
        return found
