import json
import os
import unittest
from datetime import datetime

from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.testcase import TestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.4"

PRIVATE_RESOURCES_DIR = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(__file__)),
                 "private-resources"))


@unittest.skipIf(os.environ.get("INTEGRATION_TEST_JSON", "False") != "True",
                 "Skipping, INTEGRATION_TEST_JSON=True was not set in the environment")
class TestIntegrationJSON(TestCase):
    """
    Document here what the JSON needs to look like for it to be loaded properly in to this test class.
    """
    amazon_session = None

    def __init__(self, method_name, data=None):
        super(TestIntegrationJSON, self).__init__(method_name)

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

    def run_test(self):
        # GIVEN
        year = self.data["year"]
        start_index = self.data["start_index"]
        index_on_page = self.data["index_on_page"]
        order_json = self.data["order"]

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index)

        # THEN
        order = orders[index_on_page]
        self.assert_json_items(order, order_json)

    def assert_json_items(self, entity, json_dict):
        for key, value in json_dict.items():
            attr = getattr(entity, key)
            if value == "None":
                self.assertIsNone(attr)
            elif value == "isNotNone":
                self.assertIsNotNone(attr)
            elif isinstance(value, dict):
                self.assert_json_items(attr, value)
            else:
                try:
                    self.assertEqual(
                        datetime.strptime(value, "%Y-%m-%d").date(), attr)
                except (TypeError, ValueError):
                    self.assertEqual(value, attr)


def load_tests(loader, tests, pattern):
    test_cases = unittest.TestSuite()
    for filename in os.listdir(PRIVATE_RESOURCES_DIR):
        with open(os.path.join(PRIVATE_RESOURCES_DIR, filename), "r",
                  encoding="utf-8") as f:
            data = json.loads(f.read())
            test_cases.addTest(TestIntegrationJSON('run_test', data))
    return test_cases
