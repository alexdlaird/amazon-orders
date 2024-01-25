import os
import unittest

from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.testcase import TestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.4"


@unittest.skipIf(os.environ.get("INTEGRATION_TEST_GENERIC", "False") != "True",
                 "Skipping, INTEGRATION_TEST_GENERIC=True was not set in the environment")
class TestIntegrationGeneric(TestCase):
    """
    These integration tests run generically against any Amazon account. The only requirement is that the
    account in question has at least one order in the year ``INTEGRATION_TEST_YEAR`` (defaults to the
    current year). The only assertions done on the fields populated are ``isNotNoneNone``.
    """
    amazon_session = None

    @classmethod
    def setUpClass(cls):
        cls.credentials_found = os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")
        cls.year_found = os.environ.get("INTEGRATION_TEST_YEAR")

        cls.amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"),
                                           os.environ.get("AMAZON_PASSWORD"))
        cls.amazon_session.login()

        cls.amazon_orders = AmazonOrders(cls.amazon_session)

    def setUp(self):
        if not self.credentials_found:
            self.fail("AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")
        if not self.year_found:
            self.fail("INTEGRATION_TEST_YEAR environment variables not set")

        self.assertTrue(self.amazon_session.is_authenticated)

    def test_get_order_history(self):
        # GIVEN
        year = int(os.environ.get("INTEGRATION_TEST_YEAR"))

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], False)

    def test_get_order_history_full_details(self):
        # GIVEN
        year = int(os.environ.get("INTEGRATION_TEST_YEAR"))

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, full_details=True)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], True)

    def test_get_order(self):
        # GIVEN
        year = int(os.environ.get("INTEGRATION_TEST_YEAR"))
        orders = self.amazon_orders.get_order_history(year=year)
        self.assertGreaterEqual(len(orders), 1)
        self.assertIsNotNone(orders[0].order_number)
        order_id = orders[0].order_number

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_populated_generic(order, True)
