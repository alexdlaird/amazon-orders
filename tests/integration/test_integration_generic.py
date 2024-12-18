__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

import datetime
import os

from amazonorders.exception import AmazonOrdersNotFoundError
from tests.integrationtestcase import IntegrationTestCase


class TestIntegrationGeneric(IntegrationTestCase):
    """
    These integration tests run generically against any Amazon account. The only requirement is that the
    account in question has at least one order in the year ``INTEGRATION_TEST_YEAR`` (defaults to the
    current year). The only assertions done on the fields populated are ``isNotNoneNone``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.year = os.environ.get("INTEGRATION_TEST_YEAR", datetime.date.today().year)
        if os.environ.get("START_INDEX"):
            cls.start_index = os.environ.get("START_INDEX")
        else:
            cls.start_index = None
        if os.environ.get("START_INDEX_FULL_HISTORY"):
            cls.start_index_full_history = os.environ.get("START_INDEX_FULL_HISTORY")
        else:
            cls.start_index_full_history = None

    def test_get_order_history(self):
        # WHEN
        orders = self.amazon_orders.get_order_history(year=self.year,
                                                      start_index=self.start_index)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], False)

    def test_get_order_history_full_details(self):
        # WHEN
        orders = self.amazon_orders.get_order_history(year=self.year,
                                                      start_index=self.start_index_full_history,
                                                      full_details=True)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], True)

    def test_get_order(self):
        # GIVEN
        orders = self.amazon_orders.get_order_history(year=self.year,
                                                      start_index=self.start_index)
        self.assertGreaterEqual(len(orders), 1)
        self.assertIsNotNone(orders[0].order_number)
        order_id = orders[0].order_number

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_populated_generic(order, True)

    def test_get_order_does_not_exist(self):
        # GIVEN
        order_id = "1234-fake-id"

        # WHEN
        with self.assertRaises(AmazonOrdersNotFoundError):
            self.amazon_orders.get_order(order_id)
