__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import datetime
import os

from tests.integrationtestcase import IntegrationTestCase


class TestIntegrationOrdersFullDetails(IntegrationTestCase):
    """
    These integration tests get the full details of every Order in ``AMAZON_INTEGRATION_TEST_YEAR``, a request per
    Order made concurrently, so they run last: Amazon throttles some pages, like the Prime payments, for a few minutes
    after that many requests. ``AMAZON_FULL_DETAILS_LOOP_COUNT`` can be set to a higher number to repeat it, which
    helps ensure the async concurrency that exists when building Order history won't cause issues with rate limiting,
    etc.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.year = os.environ.get("AMAZON_INTEGRATION_TEST_YEAR")
        if not cls.year:
            cls.year = datetime.date.today().year
        cls.start_index = os.environ.get("AMAZON_START_INDEX")
        if os.environ.get("AMAZON_FULL_DETAILS_LOOP_COUNT"):
            cls.full_details_loop_count = int(os.environ.get("AMAZON_FULL_DETAILS_LOOP_COUNT"))
        else:
            cls.full_details_loop_count = 1

    def test_get_orders_full_details(self):
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
