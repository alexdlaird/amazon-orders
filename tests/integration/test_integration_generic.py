__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

import datetime
import os

from tests.integrationtestcase import IntegrationTestCase


class TestIntegrationGeneric(IntegrationTestCase):
    """
    These integration tests run generically against any Amazon account. The only requirement is that the
    account in question has at least one order in the year ``INTEGRATION_TEST_YEAR`` (defaults to the
    current year). The only assertions done on the fields populated are ``isNotNoneNone``.
    """

    @classmethod
    def setUpClass(cls, flask_port_offset=1):
        super().setUpClass(flask_port_offset)

        cls.year = os.environ.get("INTEGRATION_TEST_YEAR", datetime.date.today().year)

    def test_get_order_history(self):
        # WHEN
        orders = self.amazon_orders.get_order_history(year=self.year)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], False)

    def test_get_order_history_full_details(self):
        # WHEN
        orders = self.amazon_orders.get_order_history(year=self.year, full_details=True)

        # THEN
        self.assertGreaterEqual(len(orders), 1)
        self.assert_populated_generic(orders[0], True)

    def test_get_order(self):
        # GIVEN
        orders = self.amazon_orders.get_order_history(year=self.year)
        self.assertGreaterEqual(len(orders), 1)
        self.assertIsNotNone(orders[0].order_number)
        order_id = orders[0].order_number

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_populated_generic(order, True)
