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
    account in question has at least one order in the year ``AMAZON_INTEGRATION_TEST_YEAR`` (defaults to the
    current year). The only assertions done on the fields populated are ``isNotNone``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if os.environ.get("AMAZON_INTEGRATION_TEST_YEAR"):
            cls.year = os.environ.get("AMAZON_INTEGRATION_TEST_YEAR")
        else:
            cls.year = datetime.date.today().year
        if os.environ.get("AMAZON_START_INDEX"):
            cls.start_index = os.environ.get("AMAZON_START_INDEX")
        else:
            cls.start_index = None
        if os.environ.get("AMAZON_TRANSACTIONS_DAYS"):
            cls.transactions_days = os.environ.get("AMAZON_TRANSACTIONS_DAYS")
        else:
            cls.transactions_days = 90
        if os.environ.get("AMAZON_FULL_DETAILS_LOOP_COUNT"):
            cls.full_details_loop_count = int(os.environ.get("AMAZON_FULL_DETAILS_LOOP_COUNT"))
        else:
            cls.full_details_loop_count = 1

    @unittest.skip("Even though the form submissions suggest tha Amazon should not re-prompt for OTP, it often does. "
                   "Further investigation needs to be done, perhaps in to deviceId, for this test to pass.")
    def test_logout_login_no_otp_reprompt(self):
        # GIVEN
        with open(self.test_config.cookie_jar_path, "r") as f:
            logged_in_persisted_cookies = f.read()

        # WHEN
        self.amazon_session.logout()

        # THEN
        with open(self.test_config.cookie_jar_path, "r") as f:
            logged_out_persisted_cookies = f.read()
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertNotEqual(logged_in_persisted_cookies, logged_out_persisted_cookies)

        # GIVEN
        self.amazon_session.otp_secret_key = None

        # WHEN
        # If the test is not automated (ie. prompts for OTP here), consider that a failure
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)

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
        # The environment variable FULL_DETAILS_LOOP_COUNT can be set to a higher number to put
        # more successive request pressure on Amazon, which helps ensure the async concurrency that exists when
        # building Order history won't cause issues with rate limiting, etc.
        for i in range(self.full_details_loop_count):
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
