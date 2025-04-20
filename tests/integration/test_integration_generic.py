__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
import unittest

from amazonorders.exception import AmazonOrdersNotFoundError
from tests.integrationtestcase import IntegrationTestCase


class TestIntegrationGeneric(IntegrationTestCase):
    """
    These integration tests run generically against any Amazon account. The only requirement is that the
    account in question has at least one order in the year ``INTEGRATION_TEST_YEAR`` (defaults to the
    current year). The only assertions done on the fields populated are ``isNotNone``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.year = os.environ.get("INTEGRATION_TEST_YEAR", datetime.date.today().year)
        if os.environ.get("START_INDEX"):
            cls.start_index = os.environ.get("START_INDEX")
        else:
            cls.start_index = None
        if os.environ.get("TRANSACTIONS_DAYS"):
            cls.transactions_days = os.environ.get("TRANSACTIONS_DAYS")
        else:
            cls.transactions_days = 90

    def test_get_order_history(self):
        # WHEN
        orders = self.amazon_orders.get_order_history(year=self.year,
                                                      start_index=self.start_index)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], False)
        self.assertIsNotNone(orders[0].index)
        self.assert_orders_list_index(orders)

    def test_get_order_history_full_details(self):
        # WHEN
        orders = self.amazon_orders.get_order_history(year=self.year,
                                                      start_index=self.start_index,
                                                      full_details=True)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], True)
        self.assertIsNotNone(orders[0].index)
        self.assert_orders_list_index(orders)

    @unittest.skipUnless(os.environ.get("LOAD_TEST_FULL_DETAILS") is not None,
                         reason="Skipped, to load test full details, set environment variable "
                                "LOAD_TEST_FULL_DETAILS=x, where x is the number of times to run the test")
    def test_get_order_history_full_details_load(self):
        for i in range(int(os.environ.get("LOAD_TEST_FULL_DETAILS"))):
            # WHEN
            orders = self.amazon_orders.get_order_history(year=self.year,
                                                          start_index=self.start_index,
                                                          full_details=True)

            # THEN
            self.assertGreaterEqual(len(orders), 1)
            self.assert_populated_generic(orders[0], True)
            self.assertIsNotNone(orders[0].index)
            self.assert_orders_list_index(orders)

    def test_get_order_history_single_page(self):
        # WHEN
        orders = self.amazon_orders.get_order_history(year=self.year,
                                                      keep_paging=False)

        # THEN
        self.assertLessEqual(len(orders), 10)

    def test_get_order(self):
        # GIVEN
        orders = self.amazon_orders.get_order_history(year=self.year,
                                                      start_index=self.start_index,
                                                      keep_paging=False)
        self.assertGreaterEqual(len(orders), 1)
        self.assertIsNotNone(orders[0].order_number)
        order_id = orders[0].order_number

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_populated_generic(order, True)
        self.assertIsNone(order.index)

    def test_get_order_does_not_exist(self):
        # GIVEN
        order_id = "1234-fake-id"

        # WHEN
        with self.assertRaises(AmazonOrdersNotFoundError):
            self.amazon_orders.get_order(order_id)

    def test_get_transactions(self):
        # WHEN
        transactions = self.amazon_transactions.get_transactions(self.transactions_days)

        # THEN
        self.assertGreaterEqual(len(transactions), 1)
        transaction = transactions[0]
        self.assertIsNotNone(transaction.completed_date)
        self.assertIsNotNone(transaction.payment_method)
        self.assertIsNotNone(transaction.grand_total)
        self.assertIsNotNone(transaction.is_refund)
        self.assertIsNotNone(transaction.order_number)
        self.assertIsNotNone(transaction.order_details_link)
        self.assertIsNotNone(transaction.seller)
