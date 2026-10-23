__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os

from parameterized import parameterized

from amazonorders.exception import AmazonOrdersNotFoundError, AmazonOrdersUnavailableError
from tests.integrationtestcase import IntegrationTestCase


class TestIntegrationGeneric(IntegrationTestCase):
    """
    These integration tests run generically against any Amazon account. The only requirement is that the
    account in question have at least one Order and one Transaction in the year ``AMAZON_INTEGRATION_TEST_YEAR``
    (defaults to the current year). The only assertions done on the fields populated are to test if values are
    set generically, not asserting on specific values.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.year = os.environ.get("AMAZON_INTEGRATION_TEST_YEAR")
        if not cls.year:
            cls.year = datetime.date.today().year
        cls.start_index = os.environ.get("AMAZON_START_INDEX")
        cls.transactions_days = os.environ.get("AMAZON_TRANSACTIONS_DAYS")
        if not cls.transactions_days:
            cls.transactions_days = 90
        if os.environ.get("AMAZON_FULL_DETAILS_LOOP_COUNT"):
            cls.full_details_loop_count = int(os.environ.get("AMAZON_FULL_DETAILS_LOOP_COUNT"))
        else:
            cls.full_details_loop_count = 1

    def test_get_order_after_get_orders_single_page(self):
        # WHEN
        orders = self.amazon_orders.get_orders(year=self.year,
                                               keep_paging=False)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assertLessEqual(len(orders), 10)

        # GIVEN
        self.assertIsNotNone(orders[0].order_number)
        order_id = orders[0].order_number

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_populated_generic(order, True)
        self.assertIsNone(order.index)

    @parameterized.expand([
        ("malformed", "1234-fake-id"),
        ("well_formed", "112-0000000-0000000"),
        ("well_formed_digital", "D01-0000000-0000000"),
    ])
    def test_get_order_does_not_exist(self, _, order_id):
        # WHEN
        with self.assertRaises((AmazonOrdersNotFoundError, AmazonOrdersUnavailableError)) as cm:
            self.amazon_orders.get_order(order_id)

        # THEN
        self.assertIn(order_id, str(cm.exception))

    @parameterized.expand([
        ("malformed", "1234-fake-id", "fake-id"),
        ("well_formed", "112-0000000-0000000", "AbCdEfGhI"),
    ])
    def test_get_tracking_does_not_exist(self, _, order_id, shipment_id):
        # WHEN
        with self.assertRaises((AmazonOrdersNotFoundError, AmazonOrdersUnavailableError)) as cm:
            self.amazon_orders.get_tracking(order_id, shipment_id)

        # THEN
        self.assertIn(shipment_id, str(cm.exception))

    @parameterized.expand([
        ("malformed", "1234-fake-id"),
        ("well_formed", "112-0000000-0000000"),
    ])
    def test_get_invoice_does_not_exist(self, _, order_id):
        # WHEN
        with self.assertRaises((AmazonOrdersNotFoundError, AmazonOrdersUnavailableError)) as cm:
            self.amazon_orders.get_invoice(order_id)

        # THEN
        self.assertIn(order_id, str(cm.exception))

    def test_get_orders(self):
        # WHEN
        orders = self.amazon_orders.get_orders(year=self.year,
                                               start_index=self.start_index)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], False)
        self.assertIsNotNone(orders[0].index)
        self.assert_orders_list_index(orders)

    def test_get_orders_full_details(self):
        # The environment variable FULL_DETAILS_LOOP_COUNT can be set to a higher number to put
        # more successive request pressure on Amazon, which helps ensure the async concurrency that exists when
        # building Order history won't cause issues with rate limiting, etc.
        for i in range(self.full_details_loop_count):
            # WHEN
            orders = self.amazon_orders.get_orders(year=self.year,
                                                   start_index=self.start_index,
                                                   full_details=True)

            # THEN
            self.assertGreaterEqual(len(orders), 1)
            self.assert_populated_generic(orders[0], True)
            self.assertIsNotNone(orders[0].index)
            self.assert_orders_list_index(orders)
            self.assert_populated_on_any([item for order in orders for item in order.items], "asin")

    def test_get_gift_cards(self):
        # WHEN
        balance = self.amazon_gift_cards.get_balance()
        activity = self.amazon_gift_cards.get_gift_card_activity(keep_paging=False)

        # THEN
        self.assertIsNotNone(balance)
        for entry in activity:
            self.assertIsNotNone(entry.activity_date)
            self.assertIsNotNone(entry.amount)

    def test_get_transactions(self):
        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=self.transactions_days)

        # THEN
        self.assertGreaterEqual(len(transactions), 1)
        transaction = transactions[0]
        self.assertIsNotNone(transaction.completed_date)
        self.assertIsNotNone(transaction.payment_method)
        self.assertIsNotNone(transaction.grand_total)
        self.assertIsNotNone(transaction.is_refund)
        self.assert_populated_on_any(transactions, "order_number")
        self.assert_populated_on_any(transactions, "order_details_link")
        self.assert_populated_on_any(transactions, "seller")
