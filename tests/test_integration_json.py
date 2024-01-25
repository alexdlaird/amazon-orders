import json
import os
import unittest
from datetime import datetime

from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.testcase import TestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.5"

PRIVATE_RESOURCES_DIR = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(__file__)),
                 "private-resources"))


@unittest.skipIf(os.environ.get("INTEGRATION_TEST_JSON", "False") != "True",
                 "Skipping, INTEGRATION_TEST_JSON=True was not set in the environment")
class TestIntegrationJSON(TestCase):
    """
    The two JSON files committed to "private-resources" are provided as examples of the syntax. Any other
    files created in "private-resources" will be ignored by ``.gitignore``.

    The starting JSON of a test description is:

    .. code:: json

        {
            "func": "<some_AmazonOrders_function>"
        }

    Field assertion values can be as follows:

    * Primitives and literals (ex. 23.43, "some string")
    * Dates formatted YYYY-MM-DD (ex. 2023-12-15)
    * isNone
    * isNotNone
    * Nested values (ex. a list / dict, if a corresponding list / object exists in the entity

    Details
    =======
    In a ``get_order`` test, any top-level field (other than ``func``) in the JSON will be asserted on
    the ``Order`` (including nested fields). So, for example, if we want to assert the ``Order`` was
    placed on 2023-12-15 by "John Doe", the minimal test would be:

    .. code:: json

        {
            "func": "get_order",
            "order_placed_date": "2023-12-15",
            "recipient": {
                "name": "John Doe"
            }
        }

    History
    =======
    In a ``get_order_history`` test, additional top-level fields are needed to define the test, and they are:

    .. code:: json

        {
            "year": <map to AmazonOrders.get_order_history(year)>,
            "start_index": <map to AmazonOrders.get_order_history(start_index)>,
            "full_details": <map to AmazonOrders.get_order_history(full_details)>,
            "orders_len": <the expected response list length>,
            "orders": {
                "3": {
                    # ... The Order at index 3
                },
                "7": {
                    # ... The Order at index 7
                }
            }
        }

    With this syntax, multiple ``Orders`` from the response can be asserted against. The indexed dictionaries under
    the ``orders`` key then match the assertion functionality when testing against a single order, meaning you
    define here the fields and values under the ``Order`` that you want to assert on.


    """
    amazon_session = None

    def __init__(self, method_name, filename=None, data=None):
        super(TestIntegrationJSON, self).__init__(method_name)

        self.filename = filename
        self.data = data

    @classmethod
    def setUpClass(cls):
        cls.credentials_found = os.environ.get(
            "AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")

        cls.amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"),
                                           os.environ.get("AMAZON_PASSWORD"))
        cls.amazon_session.login()

        cls.amazon_orders = AmazonOrders(cls.amazon_session)

    def setUp(self):
        if not self.credentials_found:
            self.fail(
                "AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")

        self.assertTrue(self.amazon_session.is_authenticated)

    def run_json_test(self):
        print("Info: Dynamic test is running from JSON file {}".format(self.filename))

        # GIVEN
        func = self.data.pop("func")

        if func == "get_order_history":
            order_len = self.data.pop("orders_len")
            orders_json = self.data.pop("orders")
            full_details = self.data.get("full_details")

            # WHEN
            orders = self.amazon_orders.get_order_history(**self.data)

            # THEN
            self.assertEqual(order_len, len(orders))
            for index, order_json in orders_json.items():
                order = orders[int(index)]
                self.assertEqual(order.full_details, full_details)
                self.assert_json_items(order, order_json)
        elif func == "get_order":
            order_json = self.data
            order_id = order_json["order_number"]

            # WHEN
            order = self.amazon_orders.get_order(order_id)

            # THEN
            self.assertEqual(order.full_details, True)
            self.assert_json_items(order, order_json)
        else:
            self.fail(
                "Unknown function AmazonOrders.{}, check JSON in test file {}".format(
                    func, self.filename))

    def assert_json_items(self, entity, json_dict):
        for json_key, json_value in json_dict.items():
            entity_attr = getattr(entity, json_key)
            if json_value == "isNone":
                self.assertIsNone(entity_attr)
            elif json_value == "isNotNone":
                self.assertIsNotNone(entity_attr)
            elif isinstance(json_value, list):
                i = 0
                for element in json_value:
                    self.assert_json_items(entity_attr[i], element)
                    i += 1
            elif isinstance(json_value, dict):
                self.assert_json_items(entity_attr, json_value)
            else:
                try:
                    self.assertEqual(
                        datetime.strptime(json_value, "%Y-%m-%d").date(), entity_attr)
                except (TypeError, ValueError):
                    self.assertEqual(json_value, entity_attr)


def load_tests(loader, tests, pattern):
    test_cases = unittest.TestSuite()
    if os.path.exists(PRIVATE_RESOURCES_DIR):
        for filename in os.listdir(PRIVATE_RESOURCES_DIR):
            if filename == ".gitignore":
                continue

            with open(os.path.join(PRIVATE_RESOURCES_DIR, filename), "r",
                      encoding="utf-8") as f:
                data = json.loads(f.read())
                test_cases.addTest(
                    TestIntegrationJSON("run_json_test", filename, data))
    return test_cases
