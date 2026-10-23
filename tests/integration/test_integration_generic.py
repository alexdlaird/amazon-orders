__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os

import pytest
from parameterized import parameterized

from amazonorders.exception import AmazonOrdersNotFoundError, AmazonOrdersUnavailableError
from amazonorders.paging import PagedResults
from tests.integrationtestcase import IntegrationTestCase


skip_unless_digital_orders = pytest.mark.skipif(
    not os.environ.get("AMAZON_INTEGRATION_TEST_DIGITAL_ORDERS", "False") == "True",
    reason="This test needs at least one digital Order in AMAZON_INTEGRATION_TEST_YEAR. Set "
           "AMAZON_INTEGRATION_TEST_DIGITAL_ORDERS=True explicitly to run.")
skip_unless_family_members = pytest.mark.skipif(
    not os.environ.get("AMAZON_INTEGRATION_TEST_FAMILY_MEMBERS", "False") == "True",
    reason="This test needs an Amazon Household member, like a linked Teen account. Set "
           "AMAZON_INTEGRATION_TEST_FAMILY_MEMBERS=True explicitly to run.")


class TestIntegrationGeneric(IntegrationTestCase):
    """
    These integration tests run generically against any Amazon account. The only requirement is that the
    account in question have more than one page of Orders in the year ``AMAZON_INTEGRATION_TEST_YEAR`` (defaults to
    the current year), of Transactions in ``AMAZON_TRANSACTIONS_DAYS``, and of Gift Card activity, so paging is
    tested. The only assertions done on the fields populated are to test if values are set generically, not
    asserting on specific values. Tests that need more from the account are enabled with an
    ``AMAZON_INTEGRATION_TEST_*`` variable (see the ``skip_unless_*`` decorators).
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
    def test_get_invoices_does_not_exist(self, _, order_id):
        # WHEN
        with self.assertRaises((AmazonOrdersNotFoundError, AmazonOrdersUnavailableError)) as cm:
            self.amazon_orders.get_invoices(order_id)

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

    def test_get_orders_page_with_cursor(self):
        # WHEN
        first_page = self.amazon_orders.get_orders_page(year=self.year, limit=1)

        # THEN
        self.assertIsInstance(first_page, PagedResults)
        self.assertGreaterEqual(len(first_page.items), 1)
        self.assert_populated_generic(first_page.items[0], False)
        self.assertTrue(first_page.has_more)

        # WHEN
        next_page = self.amazon_orders.get_orders_page(cursor=first_page.cursor, limit=1)

        # THEN
        self.assertGreaterEqual(len(next_page.items), 1)
        self.assertFalse({order.order_number for order in first_page.items} &
                         {order.order_number for order in next_page.items})

    @skip_unless_digital_orders
    def test_get_orders_digital(self):
        # WHEN
        orders = self.amazon_orders.get_orders(year=self.year, order_filter="digital-orders", keep_paging=False)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        for order in orders:
            self.assertIsNotNone(order.order_number)
            self.assertIsNotNone(order.order_placed_date)

    def test_search_orders(self):
        # GIVEN
        orders = self.amazon_orders.get_orders(year=self.year, keep_paging=False)
        order = next(order for order in orders if order.items and order.items[0].title)
        query = max(order.items[0].title.split(), key=len)

        # WHEN
        results = self.amazon_orders.search_orders(query, keep_paging=False)

        # THEN
        self.assertGreaterEqual(len(results), 1)
        for result in results:
            self.assertIsNotNone(result.order_number)
            self.assertIsNotNone(result.item.title)
        self.assert_populated_on_any(results, "order_placed_date")

    def test_get_invoices(self):
        # GIVEN
        order_id = self.amazon_orders.get_orders(year=self.year, keep_paging=False)[0].order_number

        # WHEN
        invoices = self.amazon_orders.get_invoices(order_id)

        # THEN
        self.assertGreaterEqual(len(invoices), 1)
        summary = invoices[0]
        self.assertEqual("html", summary.format)
        self.assertEqual(order_id, summary.order_number)
        self.assertIsNotNone(summary.name)
        self.assertIsNotNone(summary.link)
        for invoice in invoices[1:]:
            self.assertEqual("pdf", invoice.format)
            self.assertIsNotNone(invoice.link)

        # WHEN
        content = self.amazon_orders.download_invoice(summary)

        # THEN
        self.assertIn(order_id.encode(), content)

    @skip_unless_family_members
    def test_get_family_members(self):
        # WHEN
        members = self.amazon_orders.get_family_members()

        # THEN
        self.assertGreaterEqual(len(members), 1)
        for member in members:
            self.assertIsNotNone(member.id)
            self.assertIsNotNone(member.name)

    def test_get_gift_cards(self):
        # WHEN
        gift_cards = self.amazon_gift_cards.get_gift_cards(keep_paging=False)

        # THEN
        self.assertIsNotNone(gift_cards.balance)
        for entry in gift_cards.items:
            self.assertIsNotNone(entry.activity_date)
            self.assertIsNotNone(entry.amount)

    def test_get_gift_cards_page_with_cursor(self):
        # WHEN
        first_page = self.amazon_gift_cards.get_gift_cards_page(days=36500, limit=1)

        # THEN
        self.assertIsNotNone(first_page.balance)
        self.assertGreaterEqual(len(first_page.items), 1)
        self.assertTrue(first_page.has_more)

        # WHEN
        next_page = self.amazon_gift_cards.get_gift_cards_page(cursor=first_page.cursor, limit=1)

        # THEN
        self.assertGreaterEqual(len(next_page.items), 1)

    def test_get_gift_cards_balance_only(self):
        # WHEN
        gift_cards = self.amazon_gift_cards.get_gift_cards(days=0)

        # THEN
        self.assertIsNotNone(gift_cards.balance)

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

    def test_get_transactions_page_with_cursor(self):
        # WHEN
        first_page = self.amazon_transactions.get_transactions_page(days=self.transactions_days, limit=1)

        # THEN
        self.assertGreaterEqual(len(first_page.items), 1)
        self.assertIsNotNone(first_page.items[0].completed_date)
        self.assertTrue(first_page.has_more)

        # WHEN
        next_page = self.amazon_transactions.get_transactions_page(cursor=first_page.cursor, limit=1)

        # THEN
        self.assertGreaterEqual(len(next_page.items), 1)
